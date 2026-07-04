#!/usr/bin/env python3
"""Fixture tests for the decision-coverage gate (stdlib unittest, zero-dep)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_decision_coverage as g  # noqa: E402


class DecisionCoverage(unittest.TestCase):
    def test_mapped_decision_passes(self):
        self.assertEqual(g.check({"decisions": [{"id": "D-1", "steps": ["s1"]}]}), [])

    def test_unmapped_decision_blocks(self):
        fails = g.check({"decisions": [{"id": "D-1", "steps": []}]})
        self.assertTrue(fails)
        self.assertIn("D-1", fails[0])

    def test_missing_steps_key_blocks(self):
        self.assertTrue(g.check({"decisions": [{"id": "D-1"}]}))

    def test_no_decisions_passes(self):
        self.assertEqual(g.check({"decisions": []}), [])
        self.assertEqual(g.check({}), [])

    def test_reports_only_the_unmapped(self):
        fails = g.check({"decisions": [
            {"id": "ok", "steps": ["s1"]},
            {"id": "bad", "steps": []},
        ]})
        self.assertEqual(len(fails), 1)
        self.assertIn("bad", fails[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
