#!/usr/bin/env python3
"""Tests for the demo-bundle lint — the mechanical floor for the format discipline the
serving CSP does not enforce. Driven against real files, not mocked: the point is that a
clean bundle passes and each banned pattern is actually caught."""
import json
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


class RefineLedger(unittest.TestCase):
    """The floor under `create-demo`'s "edit the SPEC first, then regenerate".

    That was prose with nothing behind it, and a real drive skipped it: refine round 1
    put "a unique icon beside every speaker name" into the bundle and nowhere else. The
    terminal `approve` DELETES the bundle and locks the spec, so the decision the human
    approved would have been destroyed at the moment of approval while the durable
    artifact stayed wrong. Silent and permanent — so it gets a check, not a sentence.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        # A realistic tree: <project>/.workflow/demos/<item>/ beside <project>/docs/
        self.workflow = os.path.join(self.root, ".workflow")
        self.bundle = os.path.join(self.workflow, "demos", "item-1")
        os.makedirs(self.bundle)
        os.makedirs(os.path.join(self.root, "docs"))
        with open(os.path.join(self.bundle, "index.html"), "w") as fh:
            fh.write("<h1>demo</h1>")
        self.spec = os.path.join(self.root, "docs", "spec.md")
        self.write_spec("v1")

    def write_spec(self, text):
        with open(self.spec, "w") as fh:
            fh.write(text)
        return cdb._sha256(self.spec)

    def ledger(self, obj):
        with open(os.path.join(self.bundle, ".refine.json"), "w") as fh:
            json.dump(obj, fh)

    def lint(self):
        return cdb.lint(self.bundle, self.workflow)

    def config(self, obj):
        with open(os.path.join(self.workflow, "config.json"), "w") as fh:
            json.dump(obj, fh)

    def ref(self, sha):
        return {"path": "docs/spec.md", "sha256": sha}

    def test_no_ledger_is_fine(self):
        """Round 0 — nobody has asked for a change yet."""
        self.assertEqual(self.lint(), [])

    def test_a_round_that_moved_the_spec_passes(self):
        sha = cdb._sha256(self.spec)
        self.ledger({"round": 1, "rounds": [{"round": 1, "spec_ref": self.ref(sha)}]})
        self.assertEqual(self.lint(), [])

    def test_a_round_that_did_not_move_the_spec_is_refused(self):
        """The exact defect: round 2 regenerated the bundle off an unchanged spec."""
        sha = cdb._sha256(self.spec)
        self.ledger({"round": 2, "rounds": [
            {"round": 1, "spec_ref": self.ref(sha)},
            {"round": 2, "spec_ref": self.ref(sha)}]})
        out = " ".join(self.lint())
        self.assertIn("did not change from the previous round", out)

    def test_a_round_with_no_spec_ref_is_refused(self):
        self.ledger({"round": 1, "rounds": [{"round": 1}]})
        out = " ".join(self.lint())
        self.assertIn("spec_ref", out)
        self.assertIn("pruned on approve", out)

    def test_the_latest_round_must_match_the_spec_on_disk(self):
        """Recording a hash the file no longer has means the bundle was generated from
        a spec that has since moved — the ledger would be describing an aspiration."""
        stale = cdb._sha256(self.spec)
        self.write_spec("v2 — edited after the bundle was built")
        self.ledger({"round": 1, "rounds": [{"round": 1, "spec_ref": self.ref(stale)}]})
        self.assertIn("as it is on disk now", " ".join(self.lint()))

    def test_earlier_rounds_may_reference_superseded_revisions(self):
        """Only the LATEST round is pinned to current bytes; requiring all of them would
        make every later edit retroactively invalidate the whole history."""
        r1 = cdb._sha256(self.spec)
        r2 = self.write_spec("v2")
        self.ledger({"round": 2, "rounds": [
            {"round": 1, "spec_ref": self.ref(r1)},
            {"round": 2, "spec_ref": self.ref(r2)}]})
        self.assertEqual(self.lint(), [])

    def test_the_cap_is_enforced_and_names_the_escalation(self):
        """Previously `max_refine_rounds` lived in two documents that no code read — a
        counter nobody checks is a circuit-breaker that never trips."""
        self.config({"demo": {"max_refine_rounds": 2}})
        sha = cdb._sha256(self.spec)
        self.ledger({"round": 3, "rounds": [{"round": 3, "spec_ref": self.ref(sha)}]})
        out = " ".join(self.lint())
        self.assertIn("exceeds config.demo.max_refine_rounds", out)
        self.assertIn("discuss", out)

    def test_the_cap_defaults_when_config_is_absent_or_junk(self):
        sha = cdb._sha256(self.spec)
        self.ledger({"round": 4, "rounds": [{"round": 4, "spec_ref": self.ref(sha)}]})
        self.assertIn("exceeds", " ".join(self.lint()))   # default cap is 3
        self.config({"demo": {"max_refine_rounds": "lots"}})
        self.assertIn("exceeds", " ".join(self.lint()))   # junk -> default, never a crash

    def test_an_unreadable_ledger_blocks_rather_than_passing_quietly(self):
        with open(os.path.join(self.bundle, ".refine.json"), "w") as fh:
            fh.write("{not json")
        self.assertIn("unreadable", " ".join(self.lint()))

    def test_rounds_must_account_for_every_round(self):
        sha = cdb._sha256(self.spec)
        self.ledger({"round": 2, "rounds": [{"round": 1, "spec_ref": self.ref(sha)}]})
        self.assertIn("one entry per round", " ".join(self.lint()))

    def test_the_workflow_dir_is_derived_when_not_passed(self):
        """demos/<id>/ sits under .workflow/, so the common call needs no flag."""
        sha = cdb._sha256(self.spec)
        self.ledger({"round": 1, "rounds": [{"round": 1, "spec_ref": self.ref(sha)}]})
        self.assertEqual(cdb.lint(self.bundle), [])
        self.assertEqual(cdb.main(["x", self.bundle]), 0)


if __name__ == "__main__":
    unittest.main()
