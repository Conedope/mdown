# mdown

A small, dependency-free Markdown → HTML converter for Python 3.9+. It ships
both a library (`mdown.render`) and a command line tool (`mdown`).

The parser is a **line-based state machine** (line scanner + block dispatch),
not a pile of regular expressions, so the behavior is deliberate and testable.
Only the clearly documented subset below is supported; everything else is
rendered as escaped literal text.

**Header / convenience API**

```python
from mdown import markdown_to_html, MarkdownRenderer

html = markdown_to_html("# Hi")      # "<h1>Hi</h1>\n"
html = markdown_to_html('"hi" ...')  # smart punctuation is on by default
html = MarkdownRenderer(smart=False).render(text)
```

## Install

```sh
python3 -m pip install -e .
mdown --version
```

## CLI

```sh
mdown file.md                 # print HTML to stdout
mdown file.md -o out.html     # write to a file
cat file.md | mdown           # read from stdin
mdown --no-smart file.md      # disable smart punctuation
mdown --version
```

Errors (missing file, unwritable output) are reported on stderr and the
process exits with status 1.

Output always ends with exactly one trailing newline.

## Supported subset

| Feature                | Markdown                                     | HTML output                                       |
| ---------------------- | -------------------------------------------- | ------------------------------------------------- |
| ATX headings           | `#` … `######` (optional closing `#`s)        | `<h1>…</h1>` … `<h6>…</h6>`                      |
| Paragraphs             | text separated by blank lines                 | `<p>…</p>`                                        |
| Unordered lists        | `- ` / `* `                                  | `<ul><li>…</li></ul>`                             |
| Ordered lists          | `1. ` `2. ` … (numbers ignored)              | `<ol><li>…</li></ol>`                             |
| Nested lists           | 4-space indented markers                      | one extra `<ul>`/`<ol>` level inside `<li>`        |
| Fenced code blocks     | ```` ```lang … ``` ````                       | `<pre><code class="language-lang">…</code></pre>` |
| Inline code            | `` `x` ``                                    | `<code>x</code>`                                  |
| Bold                   | `**x**`                                      | `<strong>x</strong>`                              |
| Italic                 | `*x*` / `_x_`                                | `<em>x</em>`                                      |
| Links                  | `[text](url "title")`                        | `<a href="url" title="title">text</a>`            |
| Images                 | `![alt](url "title")`                        | `<img src="url" alt="alt" title="title" />`       |
| Autolinks              | `<https://example.com>`                      | `<a href="https://example.com">…</a>`             |
| Blockquotes            | `> line` (recursively nestable)               | `<blockquote>…</blockquote>`                      |
| Thematic break         | `---`, `***`, `_ _ _`                        | `<hr />`                                          |
| Smart punctuation      | on by default (`--smart` / `--no-smart`)       | `"text"` → `“text”`, `---` → `—`, `--` → `–`, `...` → `…` |

### Documented decisions and edge cases

* **Raw HTML is deliberately escaped and never passed through.** Text is
  escaped (`&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`); attribute/code values
  are escaped the same way. `<script>` cannot survive the converter.
* Soft line breaks inside a paragraph are joined with a single space.
* Runs of blank lines collapse; a single blank line is enough to split blocks.
* A fenced code block with **no closing fence extends to the end of the input**
  (still rendered as a code block).
* Fences use three or more backticks and must start at column 0. Only the
  first token after the opening fence becomes the language class.
* Lists require markers at column 0. A blank line ends a list. Ordered list
  numbers are ignored. Only one nested level is generated: a line indented by
  **4 spaces** starts a nested item, and anything indented deeper becomes text
  of the parent item.
* Emphasis and code can be nested inside each other inside link text, but
  **combined nesting** of emphasis (e.g. `***x***`) is not supported.
* Links cannot contain nested brackets or spaces in the URL; a `]` ends the
  link text. Autolinks accept only `http://`, `https://`, `ftp://` and
  `mailto:` schemes and must contain no spaces.
* A heading requires whitespace after the `#` run.
* Backslash escapes are not supported.
* Block-level constructs (headings, fences, blockquotes) inside a list item
  other than a nested list are not supported.

## Examples

Input (`example.md`):

````markdown
# mdown demo

A paragraph with **bold**, _italic_, `inline code`, a [link](https://example.com "[title]")
and an image: ![logo](logo.png "Logo").

## Lists

- alpha
- beta
    - beta.1
        - this goes too deep, so it stays in the parent item

1. first
2. second

## Code

```python
def greet(name):
    print(f"hi {name}")  # <sarcasm>
```

## Quote

> Two roads diverged in a wood, and I —
> I took the one less traveled by.

---

An &amp; ampersand, a <tag> and a literal <https://example.com> autolink.
````

Output (`mdown example.md`, smart punctuation **on**):

```html
<h1>mdown demo</h1>
<p>A paragraph with <strong>bold</strong>, <em>italic</em>, <code>inline code</code>, a <a href="https://example.com" title="A Title">link</a> and an image: <img src="logo.png" alt="logo" title="Logo" />.</p>
<h2>Lists</h2>
<ul>
  <li>alpha</li>
  <li>beta - this goes too deep, so it stays in the parent item
    <ul>
      <li>beta.1</li>
    </ul>
  </li>
</ul>
<ol>
  <li>first</li>
  <li>second</li>
</ol>
<h2>Code</h2>
<pre><code class="language-python">def greet(name):
    print(f"hi {name}")  # &lt;sarcasm&gt;
</code></pre>
<h2>Quote</h2>
<blockquote>
  <p>Two roads diverged in a wood, and I — I took the one less traveled by.</p>
</blockquote>
<hr />
<p>An &amp;amp; ampersand, a &lt;tag&gt; and a literal <a href="https://example.com">https://example.com</a> autolink.</p>
```

The hostile `<tag>` line is escaped; `<script>` and friends are equally neutralized.

## Out of scope (intentionally)

Tables, footnotes, task lists, definition lists, HTML passthrough / raw HTML,
reference-style links, multi-level nesting, deeper block constructs inside
list items, hard line breaks, backslash escapes, CommonMark full compliance.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

## License

MIT © 2026 Conedope. See `LICENSE`.