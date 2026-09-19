import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from mdown.cli import main


def run_cli(argv, stdin_text=""):
    out, err = io.StringIO(), io.StringIO()
    rc = None
    with mock.patch("sys.stdin", io.StringIO(stdin_text)):
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(argv)
    return rc, out.getvalue(), err.getvalue()


class TestCLIStdin(unittest.TestCase):
    def test_stdin_heading(self):
        rc, out, err = run_cli([], "# hi")
        self.assertEqual(rc, 0)
        self.assertEqual(out, "<h1>hi</h1>\n")
        self.assertEqual(err, "")

    def test_dash_reads_stdin(self):
        rc, out, _ = run_cli(["-"], "hello")
        self.assertEqual(rc, 0)
        self.assertEqual(out, "<p>hello</p>\n")

    def test_smart_flag(self):
        rc, out, _ = run_cli(["--smart"], '"hi"')
        self.assertEqual(rc, 0)
        self.assertEqual(out, "<p>\u201chi\u201d</p>\n")

    def test_no_smart_flag(self):
        rc, out, _ = run_cli(["--no-smart"], '"hi"')
        self.assertEqual(rc, 0)
        self.assertEqual(out, '<p>"hi"</p>\n')

    def test_hostile_input_via_stdin(self):
        rc, out, _ = run_cli([], "<script>alert(1)</script>")
        self.assertEqual(rc, 0)
        self.assertEqual(out, "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>\n")


class TestCLIFiles(unittest.TestCase):
    def test_read_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "in.md")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("- a\n- b\n")
            rc, out, _ = run_cli([path])
            self.assertEqual(rc, 0)
            self.assertEqual(out, "<ul>\n  <li>a</li>\n  <li>b</li>\n</ul>\n")

    def test_output_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "in.md")
            out_path = os.path.join(d, "out.html")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("# T\n")
            rc, out, _ = run_cli([path, "-o", out_path])
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")
            with open(out_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "<h1>T</h1>\n")

    def test_output_flag_long(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "in.md")
            out_path = os.path.join(d, "out.html")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("x\n")
            rc, _, _ = run_cli([path, "--output", out_path])
            self.assertEqual(rc, 0)
            with open(out_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "<p>x</p>\n")

    def test_missing_file(self):
        rc, out, err = run_cli(["/no/such/file/mdown.md"])
        self.assertEqual(rc, 1)
        self.assertEqual(out, "")
        self.assertIn("mdown: error:", err)

    def test_output_to_bad_path(self):
        rc, _, err = run_cli(["-o", "/no/such/dir/out.html"], "x")
        self.assertEqual(rc, 1)
        self.assertIn("mdown: error:", err)


class TestCLIVersion(unittest.TestCase):
    def test_version(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                main(["--version"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("mdown 1.0.0", buf.getvalue())


if __name__ == "__main__":
    unittest.main()