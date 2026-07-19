#!/usr/bin/env python3
"""Tests for the demo-bundle straggler prune (the audit backstop for a demo left behind
by a crash between checkpoint-resolve and the primary terminal-apply delete)."""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retention  # noqa: E402


class PruneDemos(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.demos = os.path.join(self.root, "demos")
        self.parked = os.path.join(self.root, "parked")
        os.makedirs(self.demos)
        os.makedirs(self.parked)

    def _demo(self, name):
        d = os.path.join(self.demos, name)
        os.makedirs(d)
        with open(os.path.join(d, "index.html"), "w") as fh:
            fh.write("<h1>%s</h1>" % name)
        return d

    def _park(self, ticket_id, demo_id=None):
        rec = {"ticket_id": ticket_id,
               "checkpoint": {"kind": "demo", "demo_id": demo_id or ticket_id}}
        with open(os.path.join(self.parked, ticket_id + ".json"), "w") as fh:
            json.dump(rec, fh)

    def test_a_bundle_with_no_parked_record_is_pruned(self):
        self._demo("resolved-item")
        pruned, skipped = retention.prune_demos(self.demos, self.parked, dry_run=False)
        self.assertEqual(pruned, ["resolved-item"])
        self.assertEqual(skipped, [])
        self.assertFalse(os.path.exists(os.path.join(self.demos, "resolved-item")))

    def test_a_bundle_with_an_open_checkpoint_is_kept(self):
        self._demo("live-item")
        self._park("live-item")
        pruned, skipped = retention.prune_demos(self.demos, self.parked, dry_run=False)
        self.assertEqual(pruned, [])
        self.assertEqual(skipped, ["live-item"])
        self.assertTrue(os.path.exists(os.path.join(self.demos, "live-item")))

    def test_open_matched_by_demo_id_even_if_ticket_differs(self):
        # ticket_id and the demo pointer need not be equal; the pointer keeps it.
        self._demo("demo-abc")
        self._park("ticket-99", demo_id="demo-abc")
        pruned, skipped = retention.prune_demos(self.demos, self.parked, dry_run=False)
        self.assertEqual(pruned, [])
        self.assertEqual(skipped, ["demo-abc"])

    def test_dry_run_reports_without_deleting(self):
        self._demo("resolved-item")
        pruned, _ = retention.prune_demos(self.demos, self.parked, dry_run=True)
        self.assertEqual(pruned, ["resolved-item"])
        self.assertTrue(os.path.exists(os.path.join(self.demos, "resolved-item")))

    def test_unreadable_parked_record_keeps_its_stem_conservatively(self):
        self._demo("weird")
        with open(os.path.join(self.parked, "weird.json"), "w") as fh:
            fh.write("{not json")
        pruned, skipped = retention.prune_demos(self.demos, self.parked, dry_run=False)
        self.assertEqual(pruned, [])
        self.assertEqual(skipped, ["weird"])

    def test_mixed(self):
        self._demo("open1"); self._park("open1")
        self._demo("gone1")
        self._demo("gone2")
        pruned, skipped = retention.prune_demos(self.demos, self.parked, dry_run=False)
        self.assertEqual(sorted(pruned), ["gone1", "gone2"])
        self.assertEqual(skipped, ["open1"])

    def test_no_demos_dir_is_noop(self):
        self.assertEqual(retention.prune_demos(
            os.path.join(self.root, "nope"), self.parked, dry_run=False), ([], []))


if __name__ == "__main__":
    unittest.main()
