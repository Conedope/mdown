"""mdown — a small, dependency-free Markdown to HTML converter."""

__version__ = "1.0.0"

from .render import MarkdownRenderer, markdown_to_html

__all__ = ["markdown_to_html", "MarkdownRenderer", "__version__"]