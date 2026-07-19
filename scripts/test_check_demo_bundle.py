#!/usr/bin/env python3
"""Tests for the demo-bundle lint — the mechanical floor for the format discipline the
serving CSP does not enforce. Driven against real files, not mocked: the point is that a
clean bundle passes and each banned pattern is actually caught."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_demo_bundle as cdb  # noqa: E402


class LintDemoBundle(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def write(self, name, text):
        full = os.path.join(self.root, name)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as fh:
            fh.write(text)

    def test_a_self_contained_bundle_passes(self):
        self.write("index.html",
                   '<!doctype html><h1>hi</h1>'
                   '<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
                   '<img src="data:image/png;base64,AAAA">'
                   '<script>const x = 1 + 1; document.title = "ok";</script>')
        self.write("app.css", "body{color:#111;background:#fff}")
        self.assertEqual(cdb.lint(self.root), [])

    def test_missing_index_html_is_a_violation(self):
        self.write("main.html", "<h1>wrong entry name</h1>")
        v = cdb.lint(self.root)
        self.assertTrue(any("no index.html" in x for x in v))

    def test_external_host_is_caught(self):
        self.write("index.html", '<link href="https://cdn.example/water.css">')
        v = cdb.lint(self.root)
        self.assertTrue(any("external-host" in x for x in v), v)

    def test_protocol_relative_url_is_caught(self):
        self.write("index.html", '<script src="//unpkg.com/preact"></script>')
        self.assertTrue(any("protocol-relative" in x for x in cdb.lint(self.root)))

    def test_external_font_in_css_is_caught(self):
        self.write("index.html", "<style>@font-face{src:url(https://f.gstatic.com/a.woff2)}</style>")
        self.assertTrue(any("external-host" in x for x in cdb.lint(self.root)))

    def test_eval_and_new_function_are_caught(self):
        self.write("index.html", '<script>const a = eval("1");</script>')
        self.assertTrue(any("eval" in x for x in cdb.lint(self.root)))
        self.write("index.html", '<script>const a = new Function("return 1")();</script>')
        self.assertTrue(any("eval" in x for x in cdb.lint(self.root)))

    def test_babel_jsx_is_caught(self):
        self.write("index.html", '<script type="text/babel">const x = <div/>;</script>')
        self.assertTrue(any("babel-jsx" in x for x in cdb.lint(self.root)))

    def test_bundler_dep_is_caught(self):
        self.write("index.html", '<h1>x</h1>')
        self.write("app.js", 'const fs = require("fs");')
        self.assertTrue(any("bundler-dep" in x for x in cdb.lint(self.root)))

    def test_w3_namespace_is_not_a_false_positive(self):
        """The one legitimate http literal: xmlns namespace identifiers are never fetched."""
        self.write("index.html",
                   '<svg xmlns="http://www.w3.org/2000/svg" '
                   'xmlns:xlink="http://www.w3.org/1999/xlink"><rect/></svg>')
        self.assertEqual([x for x in cdb.lint(self.root) if "external-host" in x], [])

    def test_binary_assets_are_not_scanned_as_text(self):
        # A local png is fine; it must not be scanned for patterns (and must not crash).
        self.write("index.html", "<h1>x</h1><img src='logo.png'>")
        with open(os.path.join(self.root, "logo.png"), "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
        self.assertEqual(cdb.lint(self.root), [])

    def test_main_exit_codes(self):
        self.write("index.html", "<h1>clean</h1>")
        self.assertEqual(cdb.main(["x", self.root]), 0)
        self.write("index.html", '<script src="https://cdn.x/y.js"></script>')
        self.assertEqual(cdb.main(["x", self.root]), 1)
        self.assertEqual(cdb.main(["x"]), 2)  # usage


if __name__ == "__main__":
    unittest.main()
