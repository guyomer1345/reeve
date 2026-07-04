#!/usr/bin/env python3
"""Fixture tests for the promise-coverage gate (stdlib unittest, zero-dep)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_promise_coverage as g  # noqa: E402


class PromiseCoverage(unittest.TestCase):
    def test_linked_promise_passes(self):
        self.assertEqual(g.check({
            "known_tests": ["ac-1"],
            "promises": [{"id": "p1", "test_ref": "ac-1", "universal": False}],
        }), [])

    def test_unlinked_promise_blocks(self):
        self.assertTrue(g.check({
            "known_tests": ["ac-1"],
            "promises": [{"id": "p1", "test_ref": None}],
        }))

    def test_dangling_ref_blocks(self):
        self.assertTrue(g.check({
            "known_tests": ["ac-1"],
            "promises": [{"id": "p1", "test_ref": "ac-99"}],
        }))

    def test_universal_without_boundary_blocks(self):
        fails = g.check({
            "known_tests": ["ac-1"],
            "promises": [{"id": "floor", "test_ref": "ac-1", "universal": True, "boundary": False}],
        })
        self.assertTrue(fails)
        self.assertIn("boundary", fails[0])

    def test_universal_with_boundary_passes(self):
        self.assertEqual(g.check({
            "known_tests": ["ac-1"],
            "promises": [{"id": "floor", "test_ref": "ac-1", "universal": True, "boundary": True}],
        }), [])

    def test_no_promises_passes(self):
        self.assertEqual(g.check({"known_tests": [], "promises": []}), [])

    def test_boundary_resolved_off_linked_criterion(self):
        # boundary on the CRITERION (not the promise) — the S5 fix
        self.assertEqual(g.check({
            "criteria": [{"id": "ac-1", "gate": "artifact", "boundary": True}],
            "promises": [{"id": "floor", "test_ref": "ac-1", "universal": True}],
        }), [])

    def test_universal_criterion_without_boundary_blocks(self):
        fails = g.check({
            "criteria": [{"id": "ac-1", "gate": "artifact", "boundary": False}],
            "promises": [{"id": "floor", "test_ref": "ac-1", "universal": True}],
        })
        self.assertTrue(fails)
        self.assertIn("boundary", fails[0])

    def test_test_ref_resolves_to_criteria_id(self):
        # a criterion id is a valid test_ref target even absent known_tests
        self.assertEqual(g.check({
            "criteria": [{"id": "ac-1", "gate": "artifact"}],
            "promises": [{"id": "p1", "test_ref": "ac-1", "universal": False}],
        }), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
