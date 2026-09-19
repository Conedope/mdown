"""Core Markdown to HTML rendering for mdown.

This module implements a small, documented subset of CommonMark using a
line-based state machine (line scanner + block type dispatch) rather than a
single monolithic regular expression. All HTML is generated from scratch:
raw HTML in the input is never passed through; text, attributes and code are
always escaped.

Supported subset (see README for the authoritative table):

* ATX headings ``#`` .. ``######`` with optional closing hashes
* paragraphs separated by blank lines (runs of blank lines collapse, soft
  line breaks join with a single space)
* unordered (``-`` / ``*``) and ordered (``1.``) lists with a single extra
  nesting level triggered by 4-space indentation
* fenced code blocks ````` ```lang ````` with an optional language class
* inline code spans, ``**bold**``, ``*italic*`` / ``_italic_``
* inline links ``[text](url "title")``, images ``![alt](url "title")`` and
  bare autolinks ``<https://example.com>``
* blockquotes (``> `` lines), recursively
* thematic breaks (``---``, ``***``)
"""

from __future__ import annotations

__all__ = ["MarkdownRenderer", "markdown_to_html"]

_SPECIAL = set("`*_[<!")

_BLOCKQUOTE_START = ">"


def _escape(s: str) -> str:
    """Escape text content so it is safe to place inside an element body."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attr(s: str) -> str:
    """Escape a value so it is safe to place inside a double-quoted attribute."""
    return _escape(s).replace('"', "&quot;")


def _apply_smart(text: str) -> str:
    """Smarten a chunk of plain text: curly quotes, dashes and ellipsis.

    Applied only to free text, never to code spans, code blocks or
    attribute values.
    """
    text = text.replace("...", "\u2026")
    text = text.replace("---", "\u2014")
    text = text.replace("--", "\u2013")
    out = []
    double_open = False
    n = len(text)
    for i, ch in enumerate(text):
        nxt = text[i + 1] if i + 1 < n else ""
        if ch == '"':
            if not double_open:
                double_open = True
                out.append("\u201c")
            else:
                double_open = False
                out.append("\u201d")
        elif ch == "'":
            before = text[i - 1] if i > 0 else ""
            if i == 0 or before in " \t\n([{\u2013\u2014":
                if nxt and not nxt.isspace():
                    out.append("\u2018")
                else:
                    out.append("\u2019")
            else:
                out.append("\u2019")
        else:
            out.append(ch)
    return "".join(out)


class MarkdownRenderer:
    """Convert a Markdown subset to HTML.

    ``smart`` controls smart punctuation (curly quotes, em/en dashes,
    ellipsis). It never applies inside code spans or code blocks.
    """

    def __init__(self, smart: bool = True) -> None:
        self.smart = smart

    def render(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")
        blocks = self._parse_blocks(list(lines))
        out = self._render_blocks(blocks, 0)
        return "\n".join(out) + "\n"

    # ------------------------------------------------------------------
    # Block scanning
    # ------------------------------------------------------------------

    def _parse_blocks(self, lines):
        """Parse a list of source lines into a list of block dicts."""
        blocks = []
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            if _is_blank(line):
                i += 1
                continue

            quote = self._match_quote(line)
            if quote is not None:
                inner = []
                while i < n:
                    q = self._match_quote(lines[i])
                    if q is None:
                        break
                    inner.append(q)
                    i += 1
                blocks.append({"type": "quote", "blocks": self._parse_blocks(inner)})
                continue

            fence = self._match_fence(line)
            if fence is not None:
                run, lang = fence
                j = i + 1
                code = []
                closed = False
                while j < n:
                    if self._is_fence_close(lines[j], run):
                        closed = True
                        break
                    code.append(lines[j])
                    j += 1
                blocks.append({"type": "code", "lang": lang, "lines": code})
                i = j + 1 if closed else n
                continue

            heading = self._match_heading(line)
            if heading is not None:
                level, content = heading
                blocks.append({"type": "heading", "level": level, "text": content})
                i += 1
                continue

            if self._is_hr(line):
                blocks.append({"type": "hr"})
                i += 1
                continue

            marker = self._match_list_item(line)
            if marker is not None:
                list_type, items, new_i = self._parse_list(lines, i)
                blocks.append({"type": list_type, "items": items})
                i = new_i
                continue

            para = []
            while i < n:
                ln = lines[i]
                if _is_blank(ln):
                    break
                if self._match_quote(ln) is not None:
                    break
                if self._match_fence(ln) is not None:
                    break
                if self._match_heading(ln) is not None:
                    break
                if self._is_hr(ln):
                    break
                if self._match_list_item(ln) is not None:
                    break
                para.append(ln)
                i += 1
            blocks.append({"type": "paragraph", "lines": para})
        return blocks

    def _parse_list(self, lines, start):
        """Parse a list starting at ``lines[start]`` (a marker line).

        Returns ``(list_type, items, next_index)``. A blank line or a
        non-marker, non-indented line ends the list. Indented (4 spaces)
        marker lines become a single nested list level inside the
        preceding item; other indented lines are appended to the parent
        item's text.
        """
        n = len(lines)
        i = start
        items = []
        list_type = None
        while i < n:
            line = lines[i]
            if _is_blank(line):
                break
            marker = self._match_list_item(line)
            if marker is None:
                break
            lt, text = marker
            if list_type is None:
                list_type = lt
            elif lt != list_type:
                break

            parts = [text]
            i += 1
            region = []
            while i < n and not _is_blank(lines[i]) and lines[i].startswith("    ") and lines[i].strip():
                region.append(lines[i][4:])
                i += 1

            item = {"text": "", "lists": []}
            k = 0
            while k < len(region):
                rm = self._match_list_item(region[k])
                if rm is not None:
                    stype, _ = rm
                    subitems = []
                    while k < len(region):
                        mm = self._match_list_item(region[k])
                        if mm is None or mm[0] != stype:
                            break
                        subitems.append({"text": mm[1], "lists": []})
                        k += 1
                    item["lists"].append({"type": stype, "items": subitems})
                else:
                    parts.append(region[k].lstrip())
                    k += 1
            item["text"] = " ".join(parts)
            items.append(item)
        return list_type, items, i

    # ------------------------------------------------------------------
    # Block helpers
    # ------------------------------------------------------------------

    def render_inline(self, text: str) -> str:
        return self._render_inline(text)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_blocks(self, blocks, indent):
        pad = "  " * indent
        out = []
        for b in blocks:
            t = b["type"]
            if t == "hr":
                out.append(pad + "<hr />")
            elif t == "heading":
                out.append(
                    pad + "<h%d>%s</h%d>" % (b["level"], self._render_inline(b["text"]), b["level"])
                )
            elif t == "paragraph":
                text = " ".join(b["lines"])
                out.append(pad + "<p>" + self._render_inline(text) + "</p>")
            elif t == "code":
                lang = b.get("lang") or ""
                cls = ' class="language-%s"' % _escape_attr(lang) if lang else ""
                if not b["lines"]:
                    out.append(pad + "<pre><code%s></code></pre>" % cls)
                else:
                    out.append(pad + "<pre><code%s>%s" % (cls, _escape(b["lines"][0])))
                    for c in b["lines"][1:]:
                        out.append(_escape(c))
                    out.append(pad + "</code></pre>")
            elif t == "quote":
                if not b["blocks"]:
                    out.append(pad + "<blockquote></blockquote>")
                else:
                    out.append(pad + "<blockquote>")
                    out.extend(self._render_blocks(b["blocks"], indent + 1))
                    out.append(pad + "</blockquote>")
            elif t in ("ul", "ol"):
                out.append(pad + "<%s>" % t)
                pad1 = pad + "  "
                for it in b["items"]:
                    nested = it.get("lists") or []
                    if not nested:
                        out.append(pad1 + "<li>" + self._render_inline(it["text"]) + "</li>")
                    else:
                        out.append(pad1 + "<li>" + self._render_inline(it["text"]))
                        sub = [{"type": sl["type"], "items": sl["items"]} for sl in nested]
                        out.extend(self._render_blocks(sub, indent + 2))
                        out.append(pad1 + "</li>")
                out.append(pad + "</%s>" % t)
            else:  # pragma: no cover - defensive
                raise ValueError("unknown block type: %r" % t)
        return out

    # ------------------------------------------------------------------
    # Inline scanning
    # ------------------------------------------------------------------

    def _render_inline(self, text: str) -> str:
        smart = self.smart
        out = []
        i = 0
        n = len(text)
        while i < n:
            c = text[i]
            if c == "`":
                run = 1
                while i + run < n and text[i + run] == "`":
                    run += 1
                target = "`" * run
                k = text.find(target, i + run)
                if k == -1:
                    out.append(self._text(text[i : i + run]))
                    i += run
                else:
                    content = text[i + run : k]
                    if (
                        content.startswith(" ")
                        and content.endswith(" ")
                        and content.strip(" ") != ""
                    ):
                        content = content[1:-1]
                    out.append("<code>" + _escape(content) + "</code>")
                    i = k + run
            elif c == "*":
                if text.startswith("**", i):
                    k = text.find("**", i + 2)
                    if k == -1 or k == i + 2:
                        out.append(self._text("**"))
                        i += 2
                    else:
                        out.append("<strong>" + self._render_inline(text[i + 2 : k]) + "</strong>")
                        i = k + 2
                else:
                    k = text.find("*", i + 1)
                    if k == -1:
                        out.append(self._text("*"))
                        i += 1
                    else:
                        out.append("<em>" + self._render_inline(text[i + 1 : k]) + "</em>")
                        i = k + 1
            elif c == "_":
                k = text.find("_", i + 1)
                if k == -1:
                    out.append(self._text("_"))
                    i += 1
                else:
                    out.append("<em>" + self._render_inline(text[i + 1 : k]) + "</em>")
                    i = k + 1
            elif c == "[" or (c == "!" and i + 1 < n and text[i + 1] == "["):
                img = c == "!"
                label_start = i + 2 if img else i + 1
                cb = text.find("]", label_start)
                if cb == -1 or cb + 1 >= n or text[cb + 1] != "(":
                    out.append(self._text(text[i : i + (2 if img else 1)]))
                    i += 2 if img else 1
                    continue
                eb = text.find(")", cb + 2)
                if eb == -1:
                    out.append(self._text(text[i : i + (2 if img else 1)]))
                    i += 2 if img else 1
                    continue
                inside = text[cb + 2 : eb]
                url, title = self._split_target(inside)
                label = text[label_start:cb]
                if img:
                    attrs = 'src="%s" alt="%s"' % (_escape_attr(url), _escape_attr(label))
                    if title:
                        attrs += ' title="%s"' % _escape_attr(title)
                    out.append("<img %s />" % attrs)
                else:
                    rendered = self._render_inline(label)
                    if title:
                        out.append(
                            '<a href="%s" title="%s">%s</a>'
                            % (_escape_attr(url), _escape_attr(title), rendered)
                        )
                    else:
                        out.append('<a href="%s">%s</a>' % (_escape_attr(url), rendered))
                i = eb + 1
            elif c == "<":
                k = text.find(">", i + 1)
                if k != -1 and self._is_autolink(text[i + 1 : k]):
                    target = text[i + 1 : k]
                    out.append(
                        '<a href="%s">%s</a>' % (_escape_attr(target), _escape(target))
                    )
                    i = k + 1
                else:
                    out.append(self._text("<"))
                    i += 1
            else:
                j = i
                while j < n and text[j] not in _SPECIAL:
                    j += 1
                if j == i:
                    out.append(self._text(text[i]))
                    i += 1
                else:
                    out.append(self._text(text[i:j]))
                    i = j
        return "".join(out)

    def _text(self, s: str) -> str:
        if self.smart:
            return _escape(_apply_smart(s))
        return _escape(s)

    def _split_target(self, raw: str):
        raw = raw.strip()
        title = None
        if " " in raw:
            parts = raw.split(None, 1)
            url = parts[0]
            if len(parts) > 1:
                t = parts[1].strip()
                if len(t) >= 2 and t[0] in "\"'" and t[-1] == t[0]:
                    title = t[1:-1]
                    return url, title
        url = raw
        if len(url) >= 2 and url.startswith("<") and url.endswith(">"):
            url = url[1:-1]
        return url, title

    def _is_autolink(self, s: str) -> bool:
        if not s or any(ch.isspace() for ch in s):
            return False
        if s.startswith("mailto:"):
            return True
        for scheme in ("http", "https", "ftp"):
            if s.startswith(scheme + "://") and len(s) > len(scheme) + 3:
                return True
        return False

    # ------------------------------------------------------------------
    # Line matchers
    # ------------------------------------------------------------------

    def _match_quote(self, line: str):
        if line == _BLOCKQUOTE_START:
            return ""
        if line.startswith(_BLOCKQUOTE_START + " "):
            return line[2:]
        if line.startswith(_BLOCKQUOTE_START):
            return line[1:]
        return None

    def _match_fence(self, line: str):
        if not line.startswith("```"):
            return None
        run = 0
        while run < len(line) and line[run] == "`":
            run += 1
        rest = line[run:]
        rest = rest.strip()
        lang = rest.split(None, 1)[0] if rest else ""
        return run, lang

    def _is_fence_close(self, line: str, run: int) -> bool:
        stripped = line.rstrip()
        if not stripped.startswith("`" * run):
            return False
        return stripped[run:].strip() == ""

    def _match_heading(self, line: str):
        level = 0
        while level < len(line) and line[level] == "#":
            level += 1
        if level == 0 or level > 6:
            return None
        rest = line[level:]
        if rest and not rest.startswith(" "):
            return None
        content = rest.strip()
        if content.endswith("#"):
            idx = len(content) - 1
            while idx >= 0 and content[idx] == "#":
                idx -= 1
            before = content[: idx + 1]
            if before.endswith(" "):
                content = before.rstrip()
        return level, content

    def _is_hr(self, line: str) -> bool:
        compact = "".join(line.split())
        if len(compact) < 3:
            return False
        return len(set(compact)) == 1 and compact[0] in "-*_"

    def _match_list_item(self, line: str):
        if line.startswith("- ") or line.startswith("* "):
            return ("ul", line[2:].lstrip())
        if line == "-" or line == "*":
            return ("ul", "")
        i = 0
        n = len(line)
        while i < n and line[i].isdigit():
            i += 1
        if i == 0 or i >= n or line[i] != ".":
            return None
        j = i + 1
        if j < n:
            if line[j] != " ":
                return None
            return ("ol", line[j + 1 :].lstrip())
        return ("ol", "")


def _is_blank(line: str) -> bool:
    return line.strip() == ""


def markdown_to_html(text: str, smart: bool = True) -> str:
    """Render a Markdown string to an HTML string.

    ``smart`` enables smart punctuation (curly quotes, ``--``/``---``
    dashes, ``...`` ellipsis) in free text. It is never applied to code
    spans, code blocks or attribute values.
    """
    return MarkdownRenderer(smart=smart).render(text)