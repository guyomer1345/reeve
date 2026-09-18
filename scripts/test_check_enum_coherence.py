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
# Two fixtures, because two of the five owners MOVED: D205 re-homed `checkpoint.kind` and
# `checkpoint.verdict.outcome` to `schemas-bus.md`, and this file kept serving every owner line
# out of one `schemas.md` blob. The gate reads the owner it declares, so those two invariants
# were resolving to a KeyError and 15 tests here failed for a year of commits while the gate
# itself stayed green against the real tree — a gate whose negative controls do not run.
# Partitioned rather than duplicated: serving the same blob under both paths would have made
# the tests pass again while still not checking that the gate looks in the declared file.
SCHEMAS_BUS = """\
- `integrations[]` — `{ name, kind: auth|payments, ... }`
- `request` — `{ kind: demo|qa|setup|reconcile, what, blocking: true }`
- `verdict` — `{ outcome: approve|changes|reject, notes }`
"""
SCHEMAS_MAIN = """\
**Line 1 is `status: done|continue|question|blocked`** — the typed dispatch-return envelope
- inbox message is typed — `kind: verdict|intake|control` — one transport
- **`kind: control`** — `{ op: reprioritize|pause|resume }` — honored at a boundary
- `item` — the motion's item id · `kind: align|document:audit|doc-budget|update` — the motion that ran
"""
# The whole set in one blob, for the anchor/collision unit tests below: their point is that the
# five owner regexes cannot grab each other's lines, which is only worth asserting when every
# line is present to be grabbed.
SCHEMAS = SCHEMAS_BUS + SCHEMAS_MAIN

# A CODE consumer declares the set as a literal. The prose word-search is worthless
# against one: "resume" and "pause" are ordinary English that appear in any docstring
# (bus.py's own says "it survives /clear, --resume, and session death"), so a dropped
# member sails straight through. These fixtures pin the parse instead.
BUS_OK = '''\
"""The console daemon. It survives /clear, --resume, and session death."""
VERDICT_OUTCOMES = ("approve", "changes", "reject")
CONTROL_OPS = ("reprioritize", "pause", "resume")
PARK_KINDS = ("demo", "qa", "setup", "reconcile")
'''
# The dispatch-return decider: the detector grades a return against this tuple, so a status the
# contract declares and the tuple omits is one the detector calls untyped.
RETURN_OK = '''\
"""PostToolUse detector."""
STATUSES = ("done", "continue", "question", "blocked")
'''
RETURN_STALE = '''\
"""PostToolUse detector."""
STATUSES = ("done", "question", "blocked")
'''

BUS_STALE_OPS = '''\
"""The console daemon. It survives /clear, --resume, and session death."""
VERDICT_OUTCOMES = ("approve", "changes", "reject")
CONTROL_OPS = ("reprioritize", "pause")
PARK_KINDS = ("demo", "qa", "setup", "reconcile")
'''
BUS_EXTRA_OPS = '''\
"""The console daemon. It survives /clear, --resume, and session death."""
VERDICT_OUTCOMES = ("approve", "changes", "reject")
CONTROL_OPS = ("reprioritize", "pause", "resume", "abort")
PARK_KINDS = ("demo", "qa", "setup", "reconcile")
'''
# The kind a park REFUSES is a kind whose checkpoint can never open. A kind added to
# the schema (and to the skill that raises it) but not to this tuple fails at the one
# place the failure is invisible from the schema side.
BUS_STALE_KINDS = BUS_OK.replace(', "reconcile")', ")")
BUS_EXTRA_KINDS = BUS_OK.replace(', "reconcile")', ', "reconcile", "vibes")')
CHECKPOINT = "Four kinds — demo, qa, setup, reconcile. Routes by outcome — approve, changes, reject."
CHECKPOINT_STALE = "Four kinds — demo, qa, setup, reconcile. Routes on approve, reject."  # missing changes
ROSTER_OK = "| checkpoint | skill | verdict (demo / qa / setup / reconcile) |"
ROSTER_STALE = "| checkpoint | skill | verdict (demo / qa / setup) |"  # missing reconcile
SHARED05_OK = "one typed inbox — verdict, intake, control — single consumer"
SHARED05_STALE = "one typed inbox — verdict, intake — single consumer"  # missing control

# The commit-receipt kinds (D182, generalized by D183). verify_check.py is the DECIDER — a kind
# outside this tuple is a receipt it rejects, so a motion the schema declares and the tuple omits
# is a commit that can never land, which `loop.md` promises is a straight-to-commit path.
VERIFY_OK = '''\
"""Shared verify-before-commit check. A non-item motion may align, audit, trim or update."""
RECEIPT_KINDS = ("align", "document:audit", "doc-budget", "update")
'''
VERIFY_STALE = VERIFY_OK.replace(', "doc-budget"', "")
VERIFY_EXTRA = VERIFY_OK.replace(', "update")', ', "update", "vibes")')
# `loop.md` routes loop NODES. It names the three maintenance kinds and is DECLARED EXEMPT from
# `update`, which is a command motion with no node in the graph.
LOOP_OK = ("| `document:audit` / `align` / `doc-budget` | maintenance due | `commit` |\n"
           "| *any worker* | `status: continue` / `question` / `blocked` / done | route it |")
LOOP_STALE = "| `document:audit` / `align` | maintenance due | `commit` |"  # missing doc-budget

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

    @staticmethod
    def _enum(name):
        """By NAME, never by position. These were indexed `ENUMS[0..2]` and every one of them
        broke the day a sixth enum was registered ahead of them — a test that depends on the
        order of a registry is a test that fails on an unrelated addition."""
        return next(x for x in e.ENUMS if x["name"] == name)

    def test_enum_owner_anchored_to_request(self):
        # must pick the request kinds, not the earlier integrations kinds
        vals = e.enum_values(SCHEMAS, self._enum("checkpoint.kind")["owner_re"])
        self.assertEqual(vals, ["demo", "qa", "setup", "reconcile"])

    def test_inbox_owner_anchored_to_verdict(self):
        # the inbox anchor picks the verdict|… line, never the demo|qa|… request
        vals = e.enum_values(SCHEMAS, self._enum("inbox.kind")["owner_re"])
        self.assertEqual(vals, ["verdict", "intake", "control"])

    def test_outcome_owner_anchored(self):
        # the verdict-outcome anchor picks approve|changes|reject, no collision
        vals = e.enum_values(SCHEMAS, self._enum("checkpoint.verdict.outcome")["owner_re"])
        self.assertEqual(vals, ["approve", "changes", "reject"])

    def test_registry_count_excludes_generic(self):
        n = e.registry_count(CODEMAP, e.COUNTS[0]["owner_re"], {"GenericArm"})
        self.assertEqual(n, 5)


class Enums(unittest.TestCase):
    def _files(self, roster, shared05=SHARED05_OK, bus=BUS_OK,
               verify=VERIFY_OK, loop=LOOP_OK, ret=RETURN_OK):
        return {"product/hooks/dispatch_return.py": ret,
                "product/shared/schemas.md": SCHEMAS_MAIN,
                "product/shared/schemas-bus.md": SCHEMAS_BUS,
                "product/skills/checkpoint/SKILL.md": CHECKPOINT,
                "docs/design/10-roster.md": roster,
                "docs/design/05-shared-state.md": shared05,
                "product/scripts/bus.py": bus,
                "product/hooks/verify_check.py": verify,
                "product/templates/loop.md": loop}

    def test_clean_passes(self):
        self.assertEqual(e.check_enums(reader(self._files(ROSTER_OK))), [])

    def test_the_return_decider_dropping_a_status_is_caught(self):
        """`continue` is the status that makes a worker's context bound real. If the detector's
        tuple loses it while the contract still declares it, a worker that yields correctly gets
        told its return was untyped — and the one path that recovers a blown window is the one
        that breaks."""
        errs = e.check_enums(reader(self._files(ROSTER_OK, ret=RETURN_STALE)))
        self.assertTrue(any("dispatch-return.status" in x and "continue" in x for x in errs), errs)

    def test_code_consumer_dropping_a_member_is_caught(self):
        """The control enum is CLOSED because a control op has no effect anchor: the
        only thing making a redelivered one safe is that re-applying it is a no-op. If
        the code and the schema drift, that guarantee quietly stops being true."""
        errs = e.check_enums(reader(self._files(ROSTER_OK, bus=BUS_STALE_OPS)))
        self.assertTrue(any("inbox.control.op" in x and "bus.py" in x for x in errs), errs)

    def test_code_consumer_adding_a_member_is_caught(self):
        """Both directions. An op the schema never admitted is the dangerous one — it
        is how a non-idempotent op enters through the front door."""
        errs = e.check_enums(reader(self._files(ROSTER_OK, bus=BUS_EXTRA_OPS)))
        self.assertTrue(any("inbox.control.op" in x and "abort" in x for x in errs), errs)

    def test_commit_receipt_kind_dropped_by_the_gate_is_caught(self):
        """A motion the schema declares and RECEIPT_KINDS omits is a commit whose
        receipt the gate rejects — so it can never commit, while `loop.md` still routes it
        straight to `commit`. The drift is invisible from the schema side."""
        errs = e.check_enums(reader(self._files(ROSTER_OK, verify=VERIFY_STALE)))
        self.assertTrue(any("commit_receipt.kind" in x and "verify_check.py" in x for x in errs), errs)

    def test_commit_receipt_kind_added_by_the_gate_is_caught(self):
        """Both directions: a kind the gate would honour that no schema admits is an
        exemption from verify-before-commit that nothing declared."""
        errs = e.check_enums(reader(self._files(ROSTER_OK, verify=VERIFY_EXTRA)))
        self.assertTrue(any("commit_receipt.kind" in x and "vibes" in x for x in errs), errs)

    def test_commit_receipt_kind_missing_from_the_loop_is_caught(self):
        """The prose consumer matters too: a maintenance node `loop.md` never routes is a
        node the orchestrator cannot reach."""
        errs = e.check_enums(reader(self._files(ROSTER_OK, loop=LOOP_STALE)))
        self.assertTrue(any("commit_receipt.kind" in x and "loop.md" in x for x in errs), errs)

    def test_a_declared_exemption_lets_a_prose_consumer_cover_a_subset(self):
        """`loop.md` routes loop NODES, so it names the three maintenance kinds and never
        `update` — a command motion with no node. Without the declared exemption the only ways
        past the gate are to drop the consumer (losing the check that a maintenance node is
        routable) or to add a non-node to an always-loaded file to satisfy a gate."""
        files = self._files(ROSTER_OK)
        self.assertNotIn("update", files["product/templates/loop.md"])
        self.assertFalse([x for x in e.check_enums(reader(files))
                          if "commit_receipt.kind" in x and "loop.md" in x])

    def test_a_stale_exemption_is_itself_reported(self):
        """An exemption is a hole, so it may not outlive the value it exempts. If the owner
        stops declaring `update`, the exemption naming it must fail rather than sit there
        silently widening to whatever the set becomes next."""
        inv = next(i for i in e.ENUMS if i["name"] == "commit_receipt.kind")
        original = inv.get("consumer_exempt")
        inv["consumer_exempt"] = {"product/templates/loop.md": ("no-such-kind",)}
        try:
            errs = e.check_enums(reader(self._files(ROSTER_OK)))
        finally:
            inv["consumer_exempt"] = original
        self.assertTrue(any("no-such-kind" in x and "stale exemption" in x for x in errs), errs)

    def test_a_mention_in_prose_does_not_satisfy_a_code_consumer(self):
        """The toothless case, pinned: BUS_STALE_OPS drops "resume" from the tuple while
        the word still appears in the docstring (--resume). A word-search passes it."""
        files = self._files(ROSTER_OK, bus=BUS_STALE_OPS)
        self.assertIn("resume", files["product/scripts/bus.py"], "fixture must still mention it")
        self.assertTrue(e.check_enums(reader(files)), "the gate fell back to a word-search")

    def test_park_kinds_dropping_a_member_is_caught(self):
        """`bus.py`'s PARK_KINDS is the enum's DECIDER — `write_park` refuses anything
        outside it. A kind the schema declares and this tuple omits is a checkpoint that
        can never open, and nothing on the schema side can see it."""
        errs = e.check_enums(reader(self._files(ROSTER_OK, bus=BUS_STALE_KINDS)))
        self.assertTrue(any("checkpoint.kind" in x and "bus.py" in x for x in errs), errs)

    def test_park_kinds_adding_a_member_is_caught(self):
        errs = e.check_enums(reader(self._files(ROSTER_OK, bus=BUS_EXTRA_KINDS)))
        self.assertTrue(any("checkpoint.kind" in x and "vibes" in x for x in errs), errs)

    def test_moved_code_declaration_is_flagged_not_ignored(self):
        files = self._files(ROSTER_OK, bus="# the tuple got renamed\nOPS = ('pause',)\n")
        errs = e.check_enums(reader(files))
        self.assertTrue(any("declaration not found" in x for x in errs), errs)

    def test_missing_value_flagged(self):
        errs = e.check_enums(reader(self._files(ROSTER_STALE)))
        self.assertTrue(any("reconcile" in x and "10-roster.md" in x for x in errs))

    def test_inbox_missing_value_flagged(self):
        errs = e.check_enums(reader(self._files(ROSTER_OK, shared05=SHARED05_STALE)))
        self.assertTrue(any("control" in x and "05-shared-state.md" in x for x in errs))

    def test_outcome_missing_value_flagged(self):
        files = self._files(ROSTER_OK)
        files["product/skills/checkpoint/SKILL.md"] = CHECKPOINT_STALE  # drops "changes"
        errs = e.check_enums(reader(files))
        self.assertTrue(any("changes" in x and "checkpoint" in x for x in errs))


class Counts(unittest.TestCase):
    def _files(self, roadmap):
        return {"product/scripts/codemap/codemap.py": CODEMAP, "docs/design/11-roadmap.md": roadmap}

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
        return {"docs/design/05-shared-state.md": layout,
                "product/shared/schemas.md": schemas,
                "product/commands/start.md": start}

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


class SplitAwareRead(unittest.TestCase):
    """`schemas.md` outgrew the Read ceiling and split. Every invariant here parses an OWNER
    doc whole, so "whole" has to keep meaning "whole" once a doc is two files."""

    MARKER = "<!-- doc-budget: detail split -> schemas-runtime.md -->"

    def test_a_split_owner_is_read_across_both_halves(self):
        files = {"product/shared/schemas.md": "head\n" + self.MARKER,
                 "product/shared/schemas-runtime.md": "tail"}
        got = e.read_with_splits("product/shared/schemas.md", reader(files))
        self.assertIn("head", got)
        self.assertIn("tail", got)

    def test_the_marker_spelling_is_borrowed_not_restated(self):
        """One owner for the string — a marker with two spellings is a marker nothing finds."""
        self.assertEqual(e.split_pointers(self.MARKER)[0][0], "schemas-runtime.md")

    def test_R2_would_FAIL_CLOSED_on_a_survivor_only_read(self):
        """The measured direction: the native-FS claims live in the half that moved out, so
        not following the pointer makes R2 report pins no header backs — loud, not silent."""
        rows = [("bus.lock", "RUNTIME pin"), ("alerts.json", "RUNTIME pin")]
        survivor_only = "## spec\n"
        both = survivor_only + ("## bus.lock · *`.workflow/bus.lock`; kept on a native filesystem*\n"
                                "## alerts.json · *`.workflow/alerts.json`; kept on a native filesystem*\n")
        self.assertEqual(len(e.check_pin_consumer(rows, survivor_only)), 2)
        self.assertEqual(e.check_pin_consumer(rows, both), [])

    def test_an_unreadable_detail_half_does_not_crash_the_gate(self):
        files = {"product/shared/schemas.md": "head\n" + self.MARKER}   # detail absent
        got = e.read_with_splits("product/shared/schemas.md", reader(files))
        self.assertIn("head", got)   # degrades to the survivor; the invariants then fail closed


class AnchorTable(unittest.TestCase):
    """The forecast ANCHOR TABLE: the doc is the owner, `forecast.py`'s dict is the probe.

    Adopted after it failed once, silently: the doc's header says the table is read by
    `forecast.py reality`, and a node added to the table left the dict behind — so the row was
    documentation claiming to be a mechanism, and only a hand read caught it.
    """

    DOC = """\
### the forecast ANCHOR TABLE  · read by `forecast.py reality`, written by nobody
| node | anchor | proves |
|---|---|---|
| `planner` | `items/<id>/plan.md` | the item was planned |
| `review` | `items/<id>/review-report.md` | the code was read cold |
| `create-demo` | `demos/<id>/` | a sandbox was built |
| `checkpoint:<kind>` | a `parked/` record of that kind | the human was asked |

- prose after the table
"""
    CODE = """\
ANCHOR_TABLE = {
    "planner":         ("item_file", "plan.md"),
    "review":          ("item_file", "review-report.md"),
    "create-demo":     ("workflow_path", "demos"),
    "checkpoint":      ("parked", None),
}
"""

    def _run(self, doc=None, code=None):
        files = {"product/shared/schemas-loopstate.md": doc or self.DOC,
                 "product/scripts/forecast.py": code or self.CODE,
                 "product/shared/schemas.md": ""}
        return e.check_anchor_table(reader(files))

    def test_the_matched_pair_is_clean(self):
        self.assertEqual(self._run(), [])

    def test_a_row_the_code_never_probes_is_documentation_not_a_mechanism(self):
        """The direction that actually happened."""
        errs = self._run(code=self.CODE.replace(
            '    "review":          ("item_file", "review-report.md"),\n', ""))
        self.assertEqual(len(errs), 1)
        self.assertIn("`review`", errs[0])
        self.assertIn("unknown", errs[0])

    def test_a_probe_the_table_never_declares_breaks_its_exhaustiveness_claim(self):
        errs = self._run(doc=self.DOC.replace(
            "| `review` | `items/<id>/review-report.md` | the code was read cold |\n", ""))
        self.assertEqual(len(errs), 1)
        self.assertIn("exhaustive", errs[0])

    def test_disagreeing_on_the_ARTIFACT_is_caught_not_just_the_node_set(self):
        """Same node both sides, different file — the probe reads something never written, so
        the node reports `pending` forever. A node-set-only check would call this clean."""
        errs = self._run(code=self.CODE.replace("review-report.md", "review.md"))
        self.assertEqual(len(errs), 1)
        self.assertIn("pending", errs[0])

    def test_non_item_file_probes_compare_on_the_NODE_alone(self):
        """`demos/`, `frozen_at` and a `parked/` record are prose descriptions of non-file
        probes; holding them to a filename match would fail every one of them forever."""
        self.assertEqual(self._run(), [])

    def test_the_gate_says_so_when_its_OWN_anchor_moves(self):
        for doc, code, want in (("no table here\n", None, "was not found"),
                                (None, "nothing = 1\n", "was not found")):
            errs = self._run(doc=doc, code=code)
            self.assertEqual(len(errs), 1)
            self.assertIn(want, errs[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
