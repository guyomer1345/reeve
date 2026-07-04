#!/usr/bin/env python3
"""Fixture tests for the contract linter (stdlib unittest, zero-dep)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_contracts as c  # noqa: E402

LOOP = """\
| node | on output | next |
|---|---|---|
| `discuss` | spec drafted | `execute` |
| `execute` | changelog | `idle` |

Side doors (callable from anywhere): `create-issue` → backlog · `research` (service).
"""

SCHEMAS = """\
- `commitment` ∈ `{ locked, provisional, unspecified }` — tagged per element
- `request` — `{ kind: demo|qa|setup, blocking: true }`
- `{ title, kind: bug|feature|debt, description }`
"""

# a minimal, fully-consistent skill set for the LOOP above
CLEAN = {"discuss": "body", "execute": "body", "create-issue": "body"}


class ParseLoop(unittest.TestCase):
    def test_nodes_targets_sidedoors(self):
        nodes, targets, doors = c.parse_loop(LOOP)
        self.assertEqual(nodes, {"discuss", "execute"})
        self.assertEqual(targets, {"execute", "idle"})
        self.assertEqual(doors, {"create-issue", "research"})

    def test_optional_marker_normalized(self):
        nodes, targets, _ = c.parse_loop("| `close-issue?` | x | `prioritize` |")
        self.assertIn("close-issue", nodes)


class ParseEnums(unittest.TestCase):
    def test_commitment_and_kind_union(self):
        commitment, kinds = c.parse_enums(SCHEMAS)
        self.assertEqual(commitment, {"locked", "provisional", "unspecified"})
        self.assertEqual(kinds, {"demo", "qa", "setup", "bug", "feature", "debt"})


class HardChecks(unittest.TestCase):
    def test_clean_graph_passes(self):
        hard, adv = c.check(LOOP, CLEAN, SCHEMAS)
        self.assertEqual(hard, [])
        self.assertEqual(adv, [])

    def test_dangling_target_blocks(self):
        loop = LOOP.replace("`idle`", "`nowhere`")
        hard, _ = c.check(loop, CLEAN, SCHEMAS)
        self.assertTrue(any("nowhere" in h for h in hard))

    def test_unrouted_mode_ref_blocks(self):
        skills = dict(CLEAN, document="injects a `document:audit` item")
        hard, _ = c.check(LOOP, skills, SCHEMAS)
        self.assertTrue(any("document:audit" in h for h in hard))

    def test_routed_mode_ref_ok(self):
        loop = LOOP.replace("| `execute` | changelog | `idle` |",
                            "| `execute` | changelog | `idle` |\n| `document:audit` | done | `idle` |")
        skills = dict(CLEAN, document="injects a `document:audit` item")
        hard, _ = c.check(loop, skills, SCHEMAS)
        self.assertEqual(hard, [])


class Advisories(unittest.TestCase):
    def test_coverage_gap_is_advisory_not_hard(self):
        skills = dict(CLEAN, ingest="brownfield entry")
        hard, adv = c.check(LOOP, skills, SCHEMAS)
        self.assertEqual(hard, [])
        self.assertTrue(any("ingest" in a for a in adv))

    def test_commitment_hyphen_drift(self):
        skills = dict(CLEAN, discuss="tag flow to *locked-candidate*")
        _, adv = c.check(LOOP, skills, SCHEMAS)
        self.assertTrue(any("locked-candidate" in a for a in adv))

    def test_novel_kind_flagged(self):
        skills = dict(CLEAN, checkpoint="raise checkpoint(kind=reconcile)")
        # checkpoint is uncovered here too, but we only assert the kind advisory
        _, adv = c.check(LOOP, skills, SCHEMAS)
        self.assertTrue(any("reconcile" in a for a in adv))

    def test_known_kind_not_flagged(self):
        skills = dict(CLEAN, execute="raise checkpoint(kind=demo) and kind=debt")
        _, adv = c.check(LOOP, skills, SCHEMAS)
        self.assertFalse(any("kind=" in a for a in adv))


if __name__ == "__main__":
    unittest.main(verbosity=2)
