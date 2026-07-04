#!/usr/bin/env python3
"""Fixture tests for the criterion-discharge gate (stdlib unittest, zero-dep)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_criterion_discharge as g  # noqa: E402


class CriterionDischarge(unittest.TestCase):
    def test_artifact_with_discharge_passes(self):
        self.assertEqual(g.check({
            "criteria": [{"id": "ac-1", "gate": "artifact", "discharge": "tests/test_x.py::t"}],
        }), [])

    def test_artifact_token_discharge_passes(self):
        for tok in ("type", "lint", "structural"):
            self.assertEqual(g.check({
                "criteria": [{"id": "ac-1", "gate": "artifact", "discharge": tok}],
            }), [], tok)

    def test_artifact_without_discharge_blocks(self):
        fails = g.check({"criteria": [{"id": "ac-1", "gate": "artifact"}]})
        self.assertTrue(fails)
        self.assertIn("discharge", fails[0])

    def test_artifact_blank_discharge_blocks(self):
        self.assertTrue(g.check({"criteria": [{"id": "ac-1", "gate": "artifact", "discharge": "  "}]}))

    def test_human_qa_needs_no_discharge(self):
        self.assertEqual(g.check({"criteria": [{"id": "ac-1", "gate": "human-qa"}]}), [])

    def test_unknown_gate_blocks(self):
        fails = g.check({"criteria": [{"id": "ac-1", "gate": "maybe"}]})
        self.assertTrue(fails)
        self.assertIn("gate", fails[0])

    def test_no_criteria_passes(self):
        self.assertEqual(g.check({"criteria": []}), [])
        self.assertEqual(g.check({}), [])

    def test_mixed_reports_only_the_bad_one(self):
        fails = g.check({"criteria": [
            {"id": "ok", "gate": "artifact", "discharge": "lint"},
            {"id": "qa", "gate": "human-qa"},
            {"id": "bad", "gate": "artifact"},
        ]})
        self.assertEqual(len(fails), 1)
        self.assertIn("bad", fails[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
