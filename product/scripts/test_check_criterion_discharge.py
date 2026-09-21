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

    def test_human_qa_needs_no_discharge_but_DOES_need_its_product_question(self):
        """The residue defect, mechanized. A criterion became `human-qa` because nobody could name
        a check — which routes to a person by residue and made every behavioural criterion his.
        One line naming what about the PRODUCT could change is not proof the answer is good; it is
        proof somebody asked the question the package's own rule asks."""
        self.assertEqual(g.check({"criteria": [
            {"id": "ac-1", "gate": "human-qa", "why_human": "whether the empty state reads as an "
                                                            "error is a product call"},
        ]}), [])

    def test_human_qa_with_NO_why_human_blocks(self):
        fails = g.check({"criteria": [{"id": "ac-1", "gate": "human-qa"}]})
        self.assertTrue(fails)
        self.assertIn("why_human", fails[0])
        self.assertIn("not a checkpoint", fails[0])

    def test_human_qa_with_a_BLANK_why_human_blocks(self):
        self.assertTrue(g.check({"criteria": [
            {"id": "ac-1", "gate": "human-qa", "why_human": "   "}]}))

    def test_a_RUN_discharge_passes(self):
        """The class that did not exist: `verify` is chartered on artifacts, not runtime
        behaviour, so every behavioural criterion fell to the human by residue."""
        self.assertEqual(g.check({"criteria": [
            {"id": "ac-1", "gate": "artifact", "discharge": "run: python3 -m app --selftest"}]}), [])

    def test_a_BARE_run_discharge_blocks(self):
        """The one shape that LOOKS discharged and settles nothing — the presence check would pass
        it, and `verify` would then hunt for the signal of a command nobody named."""
        fails = g.check({"criteria": [
            {"id": "ac-1", "gate": "artifact", "discharge": "run:"}]})
        self.assertTrue(fails)
        self.assertIn("no command", fails[0])

    def test_a_DEFERRED_criterion_that_binds_a_GOAL_blocks(self):
        """The hole deferral would otherwise open: the goal ledger records the binding at PROMOTE
        time, so a deferred question would let `converge.py` report the goal met on an answer
        nobody has given. If the answer decides whether the goal is met, it is not deferrable."""
        fails = g.check({"criteria": [
            {"id": "ac-1", "gate": "human-qa", "why_human": "is this what we promised",
             "blocking": False, "goal_ref": "ga-2"}]})
        self.assertTrue(fails)
        self.assertIn("ga-2", fails[0])

    def test_a_deferred_criterion_with_NO_goal_ref_is_fine(self):
        self.assertEqual(g.check({"criteria": [
            {"id": "ac-1", "gate": "human-qa", "why_human": "the empty-state wording is a product "
                                                            "call", "blocking": False}]}), [])

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
            {"id": "qa", "gate": "human-qa", "why_human": "the wording is a product call"},
            {"id": "bad", "gate": "artifact"},
        ]})
        self.assertEqual(len(fails), 1)
        self.assertIn("bad", fails[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
