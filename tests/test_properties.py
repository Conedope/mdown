import re
import unittest

from mdown import markdown_to_html

HOSTILE_INPUTS = [
    "<script>alert(1)</script>",
    "<script src='https://evil.example/x'></script>",
    "&amp;",
    "&lt; &gt; &amp;",
    "a < b & c > d",
    "<<<<<",
    ">&<",
    "<img src=x onerror=alert(1)>",
    "<a href='https://evil.example'>click</a>",
    "just text",
    "1 < 2 & 3 > 2",
]

TAG_START = re.compile(r"<([^a-zA-Z/!])")


class TestNoEscapedContentLeaks(unittest.TestCase):
    def helper(self, text):
        html = markdown_to_html(text)
        for m in re.finditer(r"&(?!amp;|lt;|gt;|quot;)", html):
            self.fail("unescaped '&' in output %r for input %r" % (html, text))
        for m in TAG_START.finditer(html):
            self.fail("raw/non-tag '<' in output %r for input %r" % (html, text))
        self.assertNotIn("<script", html.lower())
        self.assertNotIn("</script>", html.lower())
        return html

    def test_hostile_inputs_are_safe(self):
        for source in HOSTILE_INPUTS:
            self.helper(source)

    def test_hostile_inputs_inside_document(self):
        for source in HOSTILE_INPUTS:
            self.helper("# t\n\n%s\n\n- item\n\n> %s\n" % (source, source))


class TestStructure(unittest.TestCase):
    def test_paragraph_wrapping(self):
        self.assertEqual(
            markdown_to_html("a\nb\nc\nd"), "<p>a b c d</p>\n"
        )

    def test_blank_runs_collapse(self):
        for glyph in ("\n\n", "\n\n\n", "\n\n\n\n\n"):
            self.assertEqual(
                markdown_to_html("a" + glyph + "b"),
                "<p>a</p>\n<p>b</p>\n",
            )

    def test_nested_list_indentation(self):
        html = markdown_to_html("- top\n    - mid\n        - deep")
        # only one extra nesting level: the 8-space line is parent text
        self.assertEqual(
            html,
            "<ul>\n"
            "  <li>top - deep\n"
            "    <ul>\n"
            "      <li>mid</li>\n"
            "    </ul>\n"
            "  </li>\n"
            "</ul>\n",
        )

    def test_tags_balanced_on_kitchen_sink(self):
        source = (
            "# Title\n\n"
            "Some **bold**, *italic* and `code` with a [link](https://e.com) "
            "and an ![img](p.png).\n\n"
            "- a\n    - b\n\n"
            "1. one\n2. two\n\n"
            "> quote line\n> second line\n\n"
            "```py\nprint(1)\n```\n\n"
            "---\n"
        )
        html = markdown_to_html(source)
        for tag in ("p", "ul", "ol", "li", "blockquote", "h1", "pre", "code"):
            opens = len(re.findall(r"<%s(?:\s|>)" % re.escape(tag), html))
            closes = html.count("</%s>" % tag)
            self.assertEqual(opens, closes, "unbalanced <%s>" % tag)
        self.assertEqual(html.count("<strong>"), html.count("</strong>"))
        self.assertEqual(html.count("<em>"), html.count("</em>"))
        self.assertEqual(html.count("<a "), html.count("</a>"))

    def test_output_stable_trailing_newline(self):
        html = markdown_to_html("a\n")
        self.assertTrue(html.endswith("\n"))
        self.assertFalse(html.endswith("\n\n"))


if __name__ == "__main__":
    unittest.main()