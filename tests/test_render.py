import unittest

from mdown import markdown_to_html
from mdown.render import MarkdownRenderer


class TestHeadings(unittest.TestCase):
    def test_h1(self):
        self.assertEqual(markdown_to_html("# Hello"), "<h1>Hello</h1>\n")

    def test_all_levels(self):
        for level in range(1, 7):
            self.assertEqual(
                markdown_to_html("#" * level + " x"),
                "<h%d>x</h%d>\n" % (level, level),
            )

    def test_closing_hashes(self):
        self.assertEqual(markdown_to_html("## Title ##"), "<h2>Title</h2>\n")

    def test_closing_hashes_multi(self):
        self.assertEqual(markdown_to_html("# Hi ###"), "<h1>Hi</h1>\n")

    def test_closing_hash_needs_space(self):
        self.assertEqual(markdown_to_html("# foo#"), "<h1>foo#</h1>\n")

    def test_no_space_not_heading(self):
        self.assertEqual(markdown_to_html("#nospace"), "<p>#nospace</p>\n")

    def test_seven_hashes_is_paragraph(self):
        self.assertEqual(markdown_to_html("####### x"), "<p>####### x</p>\n")

    def test_excessive_heading_is_h6(self):
        self.assertEqual(markdown_to_html("###### x"), "<h6>x</h6>\n")

    def test_two_headings(self):
        self.assertEqual(markdown_to_html("# A\n## B"), "<h1>A</h1>\n<h2>B</h2>\n")

    def test_heading_inline_emphasis(self):
        self.assertEqual(markdown_to_html("# *hi*"), "<h1><em>hi</em></h1>\n")


class TestParagraphs(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(markdown_to_html("hi"), "<p>hi</p>\n")

    def test_wrapping(self):
        self.assertEqual(markdown_to_html("one\ntwo\nthree"), "<p>one two three</p>\n")

    def test_separate_paragraphs(self):
        self.assertEqual(markdown_to_html("a\n\nb"), "<p>a</p>\n<p>b</p>\n")

    def test_blank_lines_collapse(self):
        self.assertEqual(
            markdown_to_html("a\n\n\n\n\nb\n\n\nc"), "<p>a</p>\n<p>b</p>\n<p>c</p>\n"
        )

    def test_crlf_normalised(self):
        self.assertEqual(markdown_to_html("a\r\n\r\nb"), "<p>a</p>\n<p>b</p>\n")

    def test_trailing_blank_is_ignored(self):
        self.assertEqual(markdown_to_html("a\n"), "<p>a</p>\n")


class TestEscaping(unittest.TestCase):
    def test_amp(self):
        self.assertEqual(markdown_to_html("a & b"), "<p>a &amp; b</p>\n")

    def test_lt_gt(self):
        self.assertEqual(markdown_to_html("a < b > c"), "<p>a &lt; b &gt; c</p>\n")

    def test_amp_entity_escaped_again(self):
        self.assertEqual(markdown_to_html("&amp;"), "<p>&amp;amp;</p>\n")

    def test_hostile_script(self):
        self.assertEqual(
            markdown_to_html("<script>alert(1)</script>"),
            "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>\n",
        )

    def test_hostile_attrs_no_passthrough(self):
        self.assertEqual(
            markdown_to_html('<img src="x" onerror="y()">'),
            "<p>&lt;img src=\u201cx\u201d onerror=\u201cy()\u201d&gt;</p>\n",
        )

    def test_hostile_attrs_no_smart_still_escaped(self):
        self.assertEqual(
            markdown_to_html('<img src="x" onerror="y()">', smart=False),
            '<p>&lt;img src="x" onerror="y()"&gt;</p>\n',
        )

    def test_gt_escaped_in_body(self):
        self.assertEqual(markdown_to_html("a > b > c"), "<p>a &gt; b &gt; c</p>\n")


class TestLists(unittest.TestCase):
    def test_ul_dash(self):
        self.assertEqual(
            markdown_to_html("- a\n- b"),
            "<ul>\n  <li>a</li>\n  <li>b</li>\n</ul>\n",
        )

    def test_ul_star(self):
        self.assertEqual(
            markdown_to_html("* a\n* b"),
            "<ul>\n  <li>a</li>\n  <li>b</li>\n</ul>\n",
        )

    def test_ol(self):
        self.assertEqual(
            markdown_to_html("1. a\n2. b"),
            "<ol>\n  <li>a</li>\n  <li>b</li>\n</ol>\n",
        )

    def test_ol_start_number_ignored(self):
        self.assertEqual(
            markdown_to_html("5. a"),
            "<ol>\n  <li>a</li>\n</ol>\n",
        )

    def test_nested_ul(self):
        self.assertEqual(
            markdown_to_html("- a\n    - b\n    - c"),
            "<ul>\n  <li>a\n    <ul>\n      <li>b</li>\n      <li>c</li>\n    </ul>\n  </li>\n</ul>\n",
        )

    def test_nested_ol(self):
        self.assertEqual(
            markdown_to_html("1. a\n    1. b"),
            "<ol>\n  <li>a\n    <ol>\n      <li>b</li>\n    </ol>\n  </li>\n</ol>\n",
        )

    def test_item_continuation(self):
        self.assertEqual(
            markdown_to_html("- a\n    more text"),
            "<ul>\n  <li>a more text</li>\n</ul>\n",
        )

    def test_blank_ends_list(self):
        self.assertEqual(
            markdown_to_html("- a\n\n- b"),
            "<ul>\n  <li>a</li>\n</ul>\n<ul>\n  <li>b</li>\n</ul>\n",
        )

    def test_paragraph_then_list(self):
        self.assertEqual(
            markdown_to_html("p\n\n- a"),
            "<p>p</p>\n<ul>\n  <li>a</li>\n</ul>\n",
        )

    def test_inline_in_items(self):
        self.assertEqual(
            markdown_to_html("- **bold**\n- `code`"),
            "<ul>\n  <li><strong>bold</strong></li>\n  <li><code>code</code></li>\n</ul>\n",
        )


class TestCodeBlocks(unittest.TestCase):
    def test_fence_with_lang(self):
        self.assertEqual(
            markdown_to_html("```py\nprint(1)\n```"),
            '<pre><code class="language-py">print(1)\n</code></pre>\n',
        )

    def test_fence_no_lang(self):
        self.assertEqual(
            markdown_to_html("```\nx\n```"),
            "<pre><code>x\n</code></pre>\n",
        )

    def test_fence_escaping(self):
        self.assertEqual(
            markdown_to_html("```html\n<script>&\n```"),
            '<pre><code class="language-html">&lt;script&gt;&amp;\n</code></pre>\n',
        )

    def test_fence_lang_escaped(self):
        self.assertEqual(
            markdown_to_html('```a"b\nx\n```'),
            '<pre><code class="language-a&quot;b">x\n</code></pre>\n',
        )

    def test_fence_unclosed_to_end(self):
        self.assertEqual(
            markdown_to_html("```py\nx\ny"),
            '<pre><code class="language-py">x\ny\n</code></pre>\n',
        )

    def test_fence_empty(self):
        self.assertEqual(markdown_to_html("```\n```"), "<pre><code></code></pre>\n")

    def test_paragraph_after_fence(self):
        self.assertEqual(
            markdown_to_html("```\nx\n```\n\ntext"),
            "<pre><code>x\n</code></pre>\n<p>text</p>\n",
        )


class TestInline(unittest.TestCase):
    def test_code_span(self):
        self.assertEqual(markdown_to_html("`x`"), "<p><code>x</code></p>\n")

    def test_code_span_escaping(self):
        self.assertEqual(
            markdown_to_html("`a < b & c`"), "<p><code>a &lt; b &amp; c</code></p>\n"
        )

    def test_code_span_keeps_markup_literal(self):
        self.assertEqual(
            markdown_to_html("`**x**`"), "<p><code>**x**</code></p>\n"
        )

    def test_unclosed_code_span_is_literal(self):
        self.assertEqual(markdown_to_html("a ` b"), "<p>a ` b</p>\n")

    def test_bold(self):
        self.assertEqual(markdown_to_html("**x**"), "<p><strong>x</strong></p>\n")

    def test_italic_star(self):
        self.assertEqual(markdown_to_html("*x*"), "<p><em>x</em></p>\n")

    def test_italic_underscore(self):
        self.assertEqual(markdown_to_html("_x_"), "<p><em>x</em></p>\n")

    def test_mixed(self):
        self.assertEqual(
            markdown_to_html("*a* and **b** and `c`"),
            "<p><em>a</em> and <strong>b</strong> and <code>c</code></p>\n",
        )

    def test_unclosed_bold_is_literal(self):
        self.assertEqual(markdown_to_html("a ** b"), "<p>a ** b</p>\n")


class TestLinksAndImages(unittest.TestCase):
    def test_link(self):
        self.assertEqual(
            markdown_to_html("[t](https://e.com)"),
            '<p><a href="https://e.com">t</a></p>\n',
        )

    def test_link_title(self):
        self.assertEqual(
            markdown_to_html('[t](https://e.com "The Title")'),
            '<p><a href="https://e.com" title="The Title">t</a></p>\n',
        )

    def test_link_href_escaped(self):
        self.assertEqual(
            markdown_to_html("[t](https://e.com/?a=1&b=2)"),
            '<p><a href="https://e.com/?a=1&amp;b=2">t</a></p>\n',
        )

    def test_link_text_inline(self):
        self.assertEqual(
            markdown_to_html("[**t**](u)"),
            '<p><a href="u"><strong>t</strong></a></p>\n',
        )

    def test_not_a_link(self):
        self.assertEqual(markdown_to_html("a [b] c"), "<p>a [b] c</p>\n")

    def test_image(self):
        self.assertEqual(
            markdown_to_html("![alt](p.png)"),
            '<p><img src="p.png" alt="alt" /></p>\n',
        )

    def test_image_title(self):
        self.assertEqual(
            markdown_to_html('![alt](p.png "T")'),
            '<p><img src="p.png" alt="alt" title="T" /></p>\n',
        )

    def test_image_attr_escaped(self):
        self.assertEqual(
            markdown_to_html('![a"b](p.png)'),
            '<p><img src="p.png" alt="a&quot;b" /></p>\n',
        )

    def test_autolink(self):
        self.assertEqual(
            markdown_to_html("<https://example.com>"),
            '<p><a href="https://example.com">https://example.com</a></p>\n',
        )

    def test_autolink_mailto(self):
        self.assertEqual(
            markdown_to_html("<mailto:a@b.com>"),
            '<p><a href="mailto:a@b.com">mailto:a@b.com</a></p>\n',
        )

    def test_not_an_autolink(self):
        self.assertEqual(
            markdown_to_html("<not a link>"), "<p>&lt;not a link&gt;</p>\n"
        )

    def test_literal_angle_bracket(self):
        self.assertEqual(markdown_to_html("a < b"), "<p>a &lt; b</p>\n")


class TestBlockquote(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(
            markdown_to_html("> hi"),
            "<blockquote>\n  <p>hi</p>\n</blockquote>\n",
        )

    def test_multi_line(self):
        self.assertEqual(
            markdown_to_html("> a\n> b"),
            "<blockquote>\n  <p>a b</p>\n</blockquote>\n",
        )

    def test_nested(self):
        self.assertEqual(
            markdown_to_html("> > deep"),
            "<blockquote>\n  <blockquote>\n    <p>deep</p>\n  </blockquote>\n</blockquote>\n",
        )

    def test_empty(self):
        self.assertEqual(markdown_to_html(">"), "<blockquote></blockquote>\n")

    def test_with_heading_and_list(self):
        self.assertEqual(
            markdown_to_html("> # T\n> \n> - a"),
            "<blockquote>\n  <h1>T</h1>\n  <ul>\n    <li>a</li>\n  </ul>\n</blockquote>\n",
        )

    def test_ends_at_blank(self):
        self.assertEqual(
            markdown_to_html("> a\n\nb"),
            "<blockquote>\n  <p>a</p>\n</blockquote>\n<p>b</p>\n",
        )


class TestThematicBreak(unittest.TestCase):
    def test_dash(self):
        self.assertEqual(markdown_to_html("---"), "<hr />\n")

    def test_star(self):
        self.assertEqual(markdown_to_html("***"), "<hr />\n")

    def test_underscore_spaced(self):
        self.assertEqual(markdown_to_html("_ _ _"), "<hr />\n")

    def test_surrounded_by_paragraphs(self):
        self.assertEqual(
            markdown_to_html("a\n\n---\n\nb"),
            "<p>a</p>\n<hr />\n<p>b</p>\n",
        )

    def test_short_is_paragraph(self):
        self.assertEqual(markdown_to_html("- -"), "<ul>\n  <li>-</li>\n</ul>\n")


class TestSmartPunctuation(unittest.TestCase):
    def test_smart_quotes(self):
        self.assertEqual(
            markdown_to_html('He said "hi"'), "<p>He said \u201chi\u201d</p>\n"
        )

    def test_smart_dashes(self):
        self.assertEqual(
            markdown_to_html("a --- b -- c"),
            "<p>a \u2014 b \u2013 c</p>\n",
        )

    def test_smart_ellipsis(self):
        self.assertEqual(markdown_to_html("wait..."), "<p>wait\u2026</p>\n")

    def test_no_smart(self):
        self.assertEqual(
            markdown_to_html('He said "hi" ...', smart=False),
            '<p>He said "hi" ...</p>\n',
        )

    def test_smart_never_in_code_span(self):
        self.assertEqual(
            markdown_to_html('`"x" -- ...`'), '<p><code>"x" -- ...</code></p>\n'
        )

    def test_smart_never_in_code_block(self):
        self.assertEqual(
            markdown_to_html('```\n"x" -- ...\n```'),
            '<pre><code>"x" -- ...\n</code></pre>\n',
        )

    def test_smart_apostrophe(self):
        self.assertEqual(markdown_to_html("don't stop"), "<p>don\u2019t stop</p>\n")


class TestMarkdownRendererClass(unittest.TestCase):
    def test_renderer_class(self):
        renderer = MarkdownRenderer(smart=False)
        self.assertEqual(renderer.render("hi"), "<p>hi</p>\n")
        self.assertEqual(renderer.render_inline("hi"), "hi")

    def test_renderer_smart_default(self):
        renderer = MarkdownRenderer()
        self.assertEqual(renderer.render('"q"'), "<p>\u201cq\u201d</p>\n")


if __name__ == "__main__":
    unittest.main()