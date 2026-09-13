#!/usr/bin/env python3
"""Tests that `items/<id>/scratch/` really does inherit promote-then-prune — no new TTL.

The design claim is that scratch needs no retention rule of its own because `prune_items`
already deletes the whole item directory once `document` has written `promoted.json`. That is a
claim about an existing implementation, not a new feature, so it is asserted rather than
assumed: a nested directory is exactly the thing a prune written with `os.remove` or a flat
`listdir` would step over, and the failure would be silent — raw working material accumulating
forever under closed items, in a tree the retention pass reports as collected.

The other half matters as much and is the direction an over-eager fix would break. Until the
marker is written the item dir is SKIPPED, so a live worker's scratch is never collected out from
under it mid-dispatch. Scratch lives exactly as long as its item: no shorter, no longer.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retention  # noqa: E402


class ScratchInheritsItemLifecycle(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.items = os.path.join(self.root, "items")
        os.makedirs(self.items)

    def _item(self, iid, promoted=None, scratch=("raw.log",)):
        d = os.path.join(self.items, iid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "plan.md"), "w") as fh:
            fh.write("# plan\n")
        s = os.path.join(d, "scratch")
        os.makedirs(s, exist_ok=True)
        for name in scratch:
            path = os.path.join(s, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as fh:
                fh.write("x" * 4096)
        if promoted is not None:
            with open(os.path.join(d, "promoted.json"), "w") as fh:
                json.dump({"promoted": promoted}, fh)
        return d

    def test_scratch_dies_with_its_promoted_item(self):
        d = self._item("S1", promoted=True)
        pruned, skipped = retention.prune_items(self.items, dry_run=False)
        self.assertEqual(pruned, ["S1"])
        self.assertEqual(skipped, [])
        self.assertFalse(os.path.exists(d))
        self.assertFalse(os.path.exists(os.path.join(d, "scratch")))

    def test_a_nested_scratch_tree_goes_too(self):
        """Workers nest (`scratch/pages/`, `scratch/logs/`); the prune must be recursive."""
        d = self._item("S2", promoted=True,
                       scratch=("logs/build.log", "pages/a.html", "pages/deep/b.json"))
        retention.prune_items(self.items, dry_run=False)
        self.assertFalse(os.path.exists(d))

    def test_scratch_survives_while_the_item_is_un_promoted(self):
        """No marker → the dir is SKIPPED, so a live dispatch's working material is never
        collected out from under it. This is the half an explicit scratch TTL would break."""
        d = self._item("S3", promoted=None)
        pruned, skipped = retention.prune_items(self.items, dry_run=False)
        self.assertEqual(pruned, [])
        self.assertEqual(skipped, ["S3"])
        self.assertTrue(os.path.isfile(os.path.join(d, "scratch", "raw.log")))

    def test_promoted_false_is_not_promoted(self):
        d = self._item("S4", promoted=False)
        retention.prune_items(self.items, dry_run=False)
        self.assertTrue(os.path.isfile(os.path.join(d, "scratch", "raw.log")))

    def test_dry_run_deletes_nothing_but_still_reports_the_item(self):
        d = self._item("S5", promoted=True)
        pruned, _ = retention.prune_items(self.items, dry_run=True)
        self.assertEqual(pruned, ["S5"])
        self.assertTrue(os.path.isfile(os.path.join(d, "scratch", "raw.log")))


if __name__ == "__main__":
    unittest.main()
