#!/usr/bin/env python3
"""Fixture tests for the enum/registry coherence gate (stdlib unittest, zero-dep)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_enum_coherence as e  # noqa: E402

# An `integrations` kind: line BEFORE `request` — the anchor must not grab it.
SCHEMAS = """\
- `integrations[]` — `{ name, kind: auth|payments, ... }`
- `request` — `{ kind: demo|qa|setup|reconcile, what, blocking: true }`
"""
CHECKPOINT = "Four kinds — demo, qa, setup, reconcile. Routes by kind."
ROSTER_OK = "| checkpoint | skill | verdict (demo / qa / setup / reconcile) |"
ROSTER_STALE = "| checkpoint | skill | verdict (demo / qa / setup) |"  # missing reconcile

CODEMAP = "ARMS = [PythonArm(), JsTsArm(), GoArm(), JavaArm(), CSharpArm(), GenericArm()]  # precedence\n"
ROADMAP_OK = "**Five precise arms built** — thread CLOSED (D77/D79)."
ROADMAP_STALE = "**Four precise arms built** — the next arm is remaining."


def reader(files):
    return lambda rel: files[rel]


class Helpers(unittest.TestCase):
    def test_num_word_and_digit(self):
        self.assertEqual(e._num("five"), 5)
        self.assertEqual(e._num("5"), 5)
        self.assertIsNone(e._num("the"))

    def test_enum_owner_anchored_to_request(self):
        # must pick the request kinds, not the earlier integrations kinds
        vals = e.enum_values(SCHEMAS, e.ENUMS[0]["owner_re"])
        self.assertEqual(vals, ["demo", "qa", "setup", "reconcile"])

    def test_registry_count_excludes_generic(self):
        n = e.registry_count(CODEMAP, e.COUNTS[0]["owner_re"], {"GenericArm"})
        self.assertEqual(n, 5)


class Enums(unittest.TestCase):
    def _files(self, roster):
        return {"shared/schemas.md": SCHEMAS,
                "skills/checkpoint/SKILL.md": CHECKPOINT,
                "10-roster.md": roster}

    def test_clean_passes(self):
        self.assertEqual(e.check_enums(reader(self._files(ROSTER_OK))), [])

    def test_missing_value_flagged(self):
        errs = e.check_enums(reader(self._files(ROSTER_STALE)))
        self.assertTrue(any("reconcile" in x and "10-roster.md" in x for x in errs))


class Counts(unittest.TestCase):
    def _files(self, roadmap):
        return {"scripts/codemap/codemap.py": CODEMAP, "11-roadmap.md": roadmap}

    def test_matching_count_passes(self):
        self.assertEqual(e.check_counts(reader(self._files(ROADMAP_OK))), [])

    def test_count_mismatch_flagged(self):
        errs = e.check_counts(reader(self._files(ROADMAP_STALE)))
        self.assertTrue(any("Four precise arms" in x for x in errs))

    def test_non_count_phrase_ignored(self):
        # "the precise arms" carries no number -> not a claim, no false positive
        self.assertEqual(e.check_counts(reader(self._files("see the precise arms below"))), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
