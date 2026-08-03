#!/usr/bin/env python3
"""Tests for the chain-forecast prune — the arm that makes the forecast an ITEM-DIR
lifecycle artifact rather than a file that accumulates forever (D162).

The rule copies `prune_items` exactly, and copying it exactly is the point: a forecast is
committed while its change is open and pruned when it closes, with the history in git —
the project's own memory law, not a new retention policy. So it keys off the SAME
`promoted.json` marker that authorizes deleting the item dir, and nothing else.

The trap this avoids is inferring closure from ABSENCE. A forecast is created at intake,
BEFORE the demo and before any item dir exists (a forecast placed after the demo cannot
predict the demo checkpoint, which is one of the gates it exists to front-load). So
"there is no items/<id>/ dir" is the state of a brand-new forecast, not a closed one —
a prune written that way would delete every forecast the instant it was written.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retention  # noqa: E402


class PruneForecasts(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.forecasts = os.path.join(self.root, "forecasts")
        self.items = os.path.join(self.root, "items")
        os.makedirs(self.forecasts)
        os.makedirs(self.items)

    def _forecast(self, fid):
        p = os.path.join(self.forecasts, fid + ".json")
        with open(p, "w") as fh:
            json.dump({"forecast_id": fid, "status": "frozen", "events": []}, fh)
        return p

    def _item(self, iid, promoted=None):
        d = os.path.join(self.items, iid)
        os.makedirs(d, exist_ok=True)
        if promoted is not None:
            with open(os.path.join(d, "promoted.json"), "w") as fh:
                json.dump({"promoted": promoted}, fh)
        return d

    def test_a_forecast_whose_item_is_promoted_is_pruned(self):
        self._forecast("item-1")
        self._item("item-1", promoted=True)
        pruned, kept = retention.prune_forecasts(self.forecasts, self.items, dry_run=False)
        self.assertEqual(pruned, ["item-1"])
        self.assertEqual(kept, [])
        self.assertFalse(os.path.exists(os.path.join(self.forecasts, "item-1.json")))

    def test_an_OPEN_items_dir_keeps_its_forecast(self):
        self._forecast("item-1")
        self._item("item-1")                       # no promoted marker → still open
        pruned, kept = retention.prune_forecasts(self.forecasts, self.items, dry_run=False)
        self.assertEqual((pruned, kept), ([], ["item-1"]))

    def test_an_INTAKE_forecast_with_no_item_dir_yet_is_KEPT(self):
        """The whole reason this cannot infer closure from absence. A forecast runs before
        the demo at intake — there is no item dir yet, and there may not be one for a
        while. Deleting on absence would delete every forecast at birth."""
        self._forecast("new-change")
        pruned, kept = retention.prune_forecasts(self.forecasts, self.items, dry_run=False)
        self.assertEqual((pruned, kept), ([], ["new-change"]))
        self.assertTrue(os.path.exists(os.path.join(self.forecasts, "new-change.json")))

    def test_a_falsy_promoted_marker_does_not_authorize_the_delete(self):
        self._forecast("item-1")
        self._item("item-1", promoted=False)
        self.assertEqual(retention.prune_forecasts(self.forecasts, self.items,
                                                   dry_run=False), ([], ["item-1"]))

    def test_dry_run_reports_without_deleting(self):
        self._forecast("item-1")
        self._item("item-1", promoted=True)
        pruned, _ = retention.prune_forecasts(self.forecasts, self.items, dry_run=True)
        self.assertEqual(pruned, ["item-1"])
        self.assertTrue(os.path.exists(os.path.join(self.forecasts, "item-1.json")))

    def test_no_forecasts_dir_is_noop(self):
        self.assertEqual(retention.prune_forecasts(
            os.path.join(self.root, "nope"), self.items, dry_run=False), ([], []))

    def test_non_json_files_are_left_alone(self):
        with open(os.path.join(self.forecasts, "README.md"), "w") as fh:
            fh.write("notes")
        retention.prune_forecasts(self.forecasts, self.items, dry_run=False)
        self.assertTrue(os.path.exists(os.path.join(self.forecasts, "README.md")))


class PruneOrdering(unittest.TestCase):
    """The forecast prune runs BEFORE the item prune, and the order is load-bearing.

    Both read the same `promoted.json`, and the item prune DELETES the dir that holds it.
    Run the other way round, a crash between the two would leave a forecast whose marker
    no longer exists — orphaned forever, because nothing could ever authorize its delete
    again. This way a crash only leaves the item dir, which the next audit re-prunes.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_the_driver_prunes_forecasts_before_items(self):
        w = os.path.join(self.root, ".workflow")
        os.makedirs(os.path.join(w, "items", "item-1"))
        os.makedirs(os.path.join(w, "forecasts"))
        with open(os.path.join(w, "items", "item-1", "promoted.json"), "w") as fh:
            json.dump({"promoted": True}, fh)
        with open(os.path.join(w, "forecasts", "item-1.json"), "w") as fh:
            json.dump({"forecast_id": "item-1", "status": "frozen", "events": []}, fh)
        with open(os.path.join(w, "config.json"), "w") as fh:
            json.dump({"project_root": "."}, fh)
        rc = retention.main(["--workflow-dir", w, "--project-root", self.root])
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(os.path.join(w, "forecasts", "item-1.json")))
        self.assertFalse(os.path.exists(os.path.join(w, "items", "item-1")))


if __name__ == "__main__":
    unittest.main()
