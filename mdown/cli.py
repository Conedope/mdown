"""Command line interface for mdown."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .render import markdown_to_html


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdown",
        description="Convert a documented Markdown subset to HTML.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help="input Markdown file (use '-' or omit for stdin)",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        default=None,
        help="write output to FILE instead of stdout",
    )
    smart = parser.add_mutually_exclusive_group()
    smart.add_argument(
        "--smart",
        dest="smart",
        action="store_true",
        help="enable smart punctuation (curly quotes, dashes, ellipsis); on by default",
    )
    smart.add_argument(
        "--no-smart",
        dest="smart",
        action="store_false",
        help="disable smart punctuation",
    )
    parser.set_defaults(smart=True)
    parser.add_argument("--version", action="version", version="mdown %s" % __version__)
    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.file is None or args.file == "-":
        source = sys.stdin.read()
    else:
        try:
            with open(args.file, "r", encoding="utf-8") as handle:
                source = handle.read()
        except OSError as exc:
            print("mdown: error: %s" % exc, file=sys.stderr)
            return 1

    html = markdown_to_html(source, smart=args.smart)
    if not html.endswith("\n"):
        html += "\n"

    try:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as handle:
                handle.write(html)
        else:
            sys.stdout.write(html)
    except OSError as exc:
        print("mdown: error: %s" % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())