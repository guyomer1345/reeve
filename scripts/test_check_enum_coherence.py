#!/usr/bin/env python3
"""Fixture tests for the enum/registry coherence gate (stdlib unittest, zero-dep)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_enum_coherence as e  # noqa: E402

# An `integrations` kind: line BEFORE `request` — the anchor must not grab it.
# The `inbox` kind: line has no `request`, so the checkpoint anchor skips it and
# the inbox anchor (starts on `verdict|`) can't grab the demo|qa|… request line.
SCHEMAS = """\
- `integrations[]` — `{ name, kind: auth|payments, ... }`
- `request` — `{ kind: demo|qa|setup|reconcile, what, blocking: true }`
- `verdict` — `{ outcome: approve|changes|reject, notes }`
- inbox message is typed — `kind: verdict|intake|control` — one transport
"""
CHECKPOINT = "Four kinds — demo, qa, setup, reconcile. Routes by outcome — approve, changes, reject."
CHECKPOINT_STALE = "Four kinds — demo, qa, setup, reconcile. Routes on approve, reject."  # missing changes
ROSTER_OK = "| checkpoint | skill | verdict (demo / qa / setup / reconcile) |"
ROSTER_STALE = "| checkpoint | skill | verdict (demo / qa / setup) |"  # missing reconcile
SHARED05_OK = "one typed inbox — verdict, intake, control — single consumer"
SHARED05_STALE = "one typed inbox — verdict, intake — single consumer"  # missing control

CODEMAP = "ARMS = [PythonArm(), JsTsArm(), GoArm(), JavaArm(), CSharpArm(), GenericArm()]  # precedence\n"
ROADMAP_OK = "**Five precise arms built** — thread CLOSED (D77/D79)."
ROADMAP_STALE = "**Four precise arms built** — the next arm is remaining."

# --- layout fixtures (D114) --------------------------------------------------
# `<worktrees>/` sits at the same indent as `.workflow/`, so the parser must stop
# there — it is a launch-root sibling, not a `.workflow/` leaf.
LAYOUT_OK = """\
## Disk layout **[layout DECIDED]**
Preamble prose.
```
<launch root>      # where Claude runs
  CLAUDE.md         # orchestrator brief
  .workflow/
    config.json     # run config    (committed) · bus:none
    state.json      # live position — RUNTIME, gitignored · bus:read · pin
    handoff.md      # durable resume anchor  (committed) · bus:read
    outbox/         # RUNTIME — pending outward actions, gitignored · bus:read · pin
    demos/<id>/     # RUNTIME — throwaway bundle, gitignored · bus:static · no-pin
  <worktrees>/      # RUNTIME — one worktree per ticket, gitignored · bus:none · no-pin
  <project_root>/   # the product
```
Trailing prose.
"""
SCHEMAS_LAYOUT_OK = """\
## state.json  · the live pointer · *`.workflow/state.json`; RUNTIME, kept on a native filesystem*
## outbox / pending-outward-action  · the queue · *`.workflow/outbox/<id>.json`; RUNTIME, gitignored, kept on a native filesystem*
## handoff.md  · the resume anchor · *`.workflow/handoff.md`; committed, stays on the repo mount*
"""
START_OK = """\
   Add the **runtime** paths to the target's `.gitignore` — `state.json`, `outbox/`,
   `demos/`, and the per-ticket worktrees; the durable artifacts (`config.json`,
   `handoff.md`) are committed.
"""


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

    def test_inbox_owner_anchored_to_verdict(self):
        # the inbox anchor picks the verdict|… line, never the demo|qa|… request
        vals = e.enum_values(SCHEMAS, e.ENUMS[1]["owner_re"])
        self.assertEqual(vals, ["verdict", "intake", "control"])

    def test_outcome_owner_anchored(self):
        # the verdict-outcome anchor picks approve|changes|reject, no collision
        vals = e.enum_values(SCHEMAS, e.ENUMS[2]["owner_re"])
        self.assertEqual(vals, ["approve", "changes", "reject"])

    def test_registry_count_excludes_generic(self):
        n = e.registry_count(CODEMAP, e.COUNTS[0]["owner_re"], {"GenericArm"})
        self.assertEqual(n, 5)


class Enums(unittest.TestCase):
    def _files(self, roster, shared05=SHARED05_OK):
        return {"shared/schemas.md": SCHEMAS,
                "skills/checkpoint/SKILL.md": CHECKPOINT,
                "10-roster.md": roster,
                "05-shared-state.md": shared05}

    def test_clean_passes(self):
        self.assertEqual(e.check_enums(reader(self._files(ROSTER_OK))), [])

    def test_missing_value_flagged(self):
        errs = e.check_enums(reader(self._files(ROSTER_STALE)))
        self.assertTrue(any("reconcile" in x and "10-roster.md" in x for x in errs))

    def test_inbox_missing_value_flagged(self):
        errs = e.check_enums(reader(self._files(ROSTER_OK, shared05=SHARED05_STALE)))
        self.assertTrue(any("control" in x and "05-shared-state.md" in x for x in errs))

    def test_outcome_missing_value_flagged(self):
        files = self._files(ROSTER_OK)
        files["skills/checkpoint/SKILL.md"] = CHECKPOINT_STALE  # drops "changes"
        errs = e.check_enums(reader(files))
        self.assertTrue(any("changes" in x and "checkpoint" in x for x in errs))


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


class LayoutParsing(unittest.TestCase):
    def test_only_workflow_leaves_are_rows(self):
        rows = e.parse_workflow_tree(LAYOUT_OK)
        self.assertEqual([p for p, _ in rows],
                         ["config.json", "state.json", "handoff.md", "outbox/", "demos/<id>/"])

    def test_stops_at_launch_root_siblings(self):
        # `<worktrees>/` and `<project_root>/` are the launch root's, not `.workflow/`'s
        rows = e.parse_workflow_tree(LAYOUT_OK)
        self.assertNotIn("<worktrees>/", [p for p, _ in rows])

    def test_missing_anchor_is_loud_not_empty(self):
        self.assertIsNone(e.parse_workflow_tree("# a doc with no layout tree"))

    def test_norm_keys_on_first_component(self):
        self.assertEqual(e._norm("parked/<id>.json"), "parked")
        self.assertEqual(e._norm("demos/<id>/"), "demos")
        self.assertEqual(e._norm("state.json"), "state.json")

    def test_pin_of_reads_all_three_states(self):
        self.assertIs(e._pin_of("RUNTIME · bus:read · pin"), True)
        self.assertIs(e._pin_of("RUNTIME · bus:static · no-pin"), False)   # not a `pin` match
        self.assertIsNone(e._pin_of("RUNTIME · bus:read"))


class Layout(unittest.TestCase):
    def _files(self, layout=LAYOUT_OK, schemas=SCHEMAS_LAYOUT_OK, start=START_OK):
        return {"05-shared-state.md": layout,
                "shared/schemas.md": schemas,
                "commands/start.md": start}

    def test_clean_passes(self):
        self.assertEqual(e.check_layout(reader(self._files())), [])

    # R1 — the D105/D111 failure mode at its root: a new RUNTIME dir lands and
    # nobody is forced to answer "does the bus read it? is it pinned?"
    def test_new_runtime_dir_without_markers_flagged(self):
        layout = LAYOUT_OK.replace(
            "  <worktrees>/",
            "    cache/          # RUNTIME — a new dir nobody classified, gitignored\n  <worktrees>/")
        errs = e.check_layout(reader(self._files(layout=layout)))
        self.assertTrue(any("cache/" in x and "bus:" in x for x in errs))
        self.assertTrue(any("cache/" in x and "no-pin" in x for x in errs))

    def test_unknown_bus_value_flagged(self):
        layout = LAYOUT_OK.replace("state.json      # live position — RUNTIME, gitignored · bus:read · pin",
                                   "state.json      # live position — RUNTIME, gitignored · bus:serves · pin")
        errs = e.check_layout(reader(self._files(layout=layout)))
        self.assertTrue(any("bus:serves" in x for x in errs))

    def test_committed_path_needs_no_pin_marker(self):
        # `handoff.md` is committed + bus:read and carries no pin marker — legal
        self.assertEqual([x for x in e.check_layout(reader(self._files())) if "handoff" in x], [])

    # R2 — the real D105 drift: `outbox/` reached the tree, not the schema.
    def test_pinned_path_missing_from_schemas_flagged(self):
        schemas = SCHEMAS_LAYOUT_OK.replace(
            "`.workflow/outbox/<id>.json`; RUNTIME, gitignored, kept on a native filesystem",
            "`.workflow/outbox/<id>.json`; RUNTIME, gitignored")
        errs = e.check_layout(reader(self._files(schemas=schemas)))
        self.assertTrue(any("outbox" in x and "native filesystem" in x for x in errs))

    # R2, reverse — schemas claims a pin the tree does not grant.
    def test_schemas_claiming_unpinned_path_flagged(self):
        schemas = SCHEMAS_LAYOUT_OK + (
            "## demos  · the bundle · *`.workflow/demos/<id>/`; RUNTIME, kept on a native filesystem*\n")
        errs = e.check_layout(reader(self._files(schemas=schemas)))
        self.assertTrue(any("demos" in x and "does not mark it pin" in x for x in errs))

    # R3 — the A2 drift: a RUNTIME path the gitignore scaffold would commit.
    def test_runtime_path_missing_from_gitignore_scaffold_flagged(self):
        start = START_OK.replace("`state.json`, `outbox/`,\n   `demos/`,", "`state.json`, `demos/`,")
        errs = e.check_layout(reader(self._files(start=start)))
        self.assertTrue(any("outbox" in x and "would be committed" in x for x in errs))

    def test_gitignore_anchor_moved_is_loud(self):
        errs = e.check_layout(reader(self._files(start="a scaffold with no gitignore clause")))
        self.assertTrue(any("anchor moved" in x for x in errs))


if __name__ == "__main__":
    unittest.main(verbosity=2)
