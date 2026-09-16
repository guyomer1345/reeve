"""Tests for status_report.py — the four-field report, and the rule that ids carry names.

The three properties that matter are the three complaints it was built from: an id never reaches
a human bare, a field never exceeds its budget, and the digest identifies WHAT the report says
rather than WHEN it was said. Each has its negative control, because each of them fails silently
— a report that quietly drops its tail or names nothing still looks like a report.
"""
import json
import os
from pathlib import Path

import status_report as sr


def project(tmp_path, acceptance=3, discharged=("ga-1",), open_item=True, parked=None,
            decisions=True):
    wf = tmp_path / ".workflow"
    (wf / "items").mkdir(parents=True, exist_ok=True)
    (wf / "parked").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "decisions").mkdir(parents=True, exist_ok=True)
    (wf / "config.json").write_text(json.dumps({"project_root": "."}))
    (wf / "goal.json").write_text(json.dumps({
        "id": "G-1", "statement": "ship the billing flow",
        "acceptance": [{"id": "ga-%d" % i, "text": "acceptance number %d" % i}
                       for i in range(1, acceptance + 1)]}))
    (wf / "goal-ledger.jsonl").write_text("".join(
        json.dumps({"goal": "G-1", "item": "I-00%d" % n, "refs": [r]}) + "\n"
        for n, r in enumerate(discharged)))
    (wf / "state.json").write_text(json.dumps(
        {"status": "building", "node": "execute", "current_item": "I-100"}))
    if open_item:
        d = wf / "items" / "I-100"
        d.mkdir(parents=True, exist_ok=True)
        (d / "plan.md").write_text("# retry failed payments with backoff\n")
        (d / "promises.json").write_text(json.dumps(
            {"criteria": [{"id": "c1", "goal_ref": "ga-2"}]}))
    if parked:
        (wf / "parked" / "TCK-9.json").write_text(json.dumps(parked))
    if decisions:
        (tmp_path / "docs" / "decisions" / "index.md").write_text(
            "| id | title | status | ref |\n|---|---|---|---|\n"
            "| D-001 | Stripe over Paddle for card payments | active | - |\n")
    return str(wf)


# --- the complaint: "references to D92, Ref X ... they mean nothing to me" ----

def test_every_id_in_the_block_carries_its_name(tmp_path):
    wf = project(tmp_path, parked={"ticket_id": "TCK-9", "summary": "approve the test keys",
                                   "checkpoint": {"kind": "setup"}})
    block = sr.render(sr.build(wf))
    assert "ga-1 (acceptance number 1)" in block
    assert "I-100 (retry failed payments with backoff)" in block
    assert sr.bare_ids(block, {}) == [], block


def test_a_decision_id_resolves_through_the_index_its_owner_writes(tmp_path):
    wf = project(tmp_path)
    known = sr.names(wf, str(tmp_path))
    assert known["D-001"] == "Stripe over Paddle for card payments"
    assert sr.gloss("D-001", known) == "D-001 (Stripe over Paddle for card payments)"


def test_an_id_NOTHING_names_is_printed_as_unresolvable_not_dropped(tmp_path):
    """The admission is the load-bearing half: a dropped id hides the defect (an index row
    nobody wrote), and a bare one is the thing being complained about."""
    assert "UNRESOLVABLE" in sr.gloss("D-777", {})


def test_a_PRUNED_items_attribution_is_dropped_rather_than_cried_wolf_over(tmp_path):
    """`retention.py` prunes a promoted item's dir — `plan.md` with it — so the name of the item
    that discharged an acceptance months ago is gone BY DESIGN. Printing UNRESOLVABLE there would
    teach the reader to ignore the word on the day it means something."""
    wf = project(tmp_path)                      # I-000 discharged ga-1 and has no dir
    achieved = sr.build(wf)["achieved"]
    assert achieved[0]["id"] == "ga-1" and achieved[0]["by"] is None
    assert "UNRESOLVABLE" not in sr.render(sr.build(wf))


# --- the complaint: "extremely long and jumbled" -----------------------------

def test_each_field_is_BUDGETED_and_says_what_it_withheld(tmp_path):
    wf = project(tmp_path, acceptance=30, discharged=("ga-%d" % i for i in range(1, 12)))
    block = sr.render(sr.build(wf), limit=3)
    assert "+8 more (ask)" in block, block
    assert len([l for l in block.splitlines() if l.startswith("  - ")]) <= 12


def test_a_long_line_is_capped_rather_than_wrapped(tmp_path):
    wf = project(tmp_path)
    for line in sr.render(sr.build(wf)).splitlines():
        assert len(line) <= sr.LINE_CHARS + 4


# --- the format, and the four changes it makes to what was asked for ---------

def test_the_decision_field_is_ABSENT_when_there_is_nothing_to_decide(tmp_path):
    """He said it is usually empty. A section that usually says nothing trains the eye to skip
    it, and then it is skipped on the one day it matters."""
    assert "DECISION FOR YOU" not in sr.render(sr.build(project(tmp_path)))


def test_the_decision_field_is_FIRST_when_there_is(tmp_path):
    wf = project(tmp_path, parked={"ticket_id": "TCK-9", "summary": "approve the test keys",
                                   "checkpoint": {"kind": "setup"}})
    block = sr.render(sr.build(wf))
    assert block.index("DECISION FOR YOU") < block.index("ACHIEVED")
    assert "TCK-9 (approve the test keys) — setup checkpoint" in block


def test_the_goal_is_NAMED_at_the_top(tmp_path):
    """Every field says "for the goal" and none of them named it."""
    assert sr.render(sr.build(project(tmp_path))).startswith("GOAL — ship the billing flow")


def test_in_flight_says_whether_it_is_MOVING(tmp_path):
    """Without the node and the age the field cannot tell working from stuck, which is the whole
    of the second ask."""
    block = sr.render(sr.build(project(tmp_path)))
    assert "execute, idle" in block


def test_a_goal_with_no_acceptance_bound_anywhere_says_the_goal_CANNOT_be_met(tmp_path):
    block = sr.render(sr.build(project(tmp_path)))
    assert "UNBOUND: no plan attempts this" in block


def test_no_goal_is_a_STATE_not_an_error(tmp_path):
    wf = project(tmp_path)
    os.remove(os.path.join(wf, "goal.json"))
    assert sr.render(sr.build(wf)).startswith("GOAL — none set.")


def test_an_item_binding_no_acceptance_is_called_out(tmp_path):
    wf = project(tmp_path)
    (Path(wf) / "items" / "I-100" / "promises.json").write_text(json.dumps({"criteria": []}))
    assert "BINDS NO GOAL ACCEPTANCE" in sr.render(sr.build(wf))


# --- the digest, which is what makes the gate possible -----------------------

def test_the_digest_ignores_TIME(tmp_path):
    """A digest that moved on its own would make every report stale on arrival, and the gate
    that reads it a nuisance to be switched off within a day."""
    wf = project(tmp_path)
    one = sr.digest(sr.build(wf, now=1_000_000))
    two = sr.digest(sr.build(wf, now=1_000_000 + 86_400))
    assert one == two


def test_the_digest_MOVES_when_the_loop_does(tmp_path):
    wf = project(tmp_path)
    before = sr.digest(sr.build(wf))
    with open(os.path.join(wf, "goal-ledger.jsonl"), "a") as fh:
        fh.write(json.dumps({"goal": "G-1", "item": "I-100", "refs": ["ga-2"]}) + "\n")
    assert sr.digest(sr.build(wf)) != before


def test_the_rendered_marker_is_the_digest(tmp_path):
    report = sr.build(project(tmp_path))
    found = sr.MARKER_RE.search(sr.render(report))
    assert found and found.group(1) == sr.digest(report)


# --- the lint ----------------------------------------------------------------

def test_the_lint_flags_a_bare_id_and_passes_a_named_one():
    assert sr.bare_ids("we followed D-001 here") == [("D-001", 1)]
    assert sr.bare_ids("we followed D-001 (Stripe over Paddle) here") == []


def test_a_PATH_containing_an_id_is_not_a_bare_reference():
    """`.workflow/items/I-001/plan.md` is a path, not a pointer the reader must dereference."""
    assert sr.bare_ids("see .workflow/items/I-001/plan.md for the steps") == []


def test_code_blocks_are_skipped_whole():
    text = "prose\n```\ncurl /api/D-001\n```\nmore prose\n"
    assert sr.bare_ids(text) == []


def test_the_lint_reports_the_LINE_so_it_can_be_fixed():
    assert sr.bare_ids("one\ntwo\nthe D92 decision\n") == [("D92", 3)]


# --- it never writes ---------------------------------------------------------

def test_nothing_is_stored(tmp_path):
    """A synthesized status doc is stale the moment the next commit lands, and a stale one is
    worse than none because it is believed."""
    wf = project(tmp_path)
    before = {p for p in Path(tmp_path).rglob("*")}
    sr.render(sr.build(wf))
    assert {p for p in Path(tmp_path).rglob("*")} == before


# ============================================================ the lint that failed a correct report
# An item titled `ITEM-001 - topwords` renders as `ITEM-001 (ITEM-001 - topwords)`, and the id
# INSIDE the parentheses was flagged as bare — the lint demanding a name for the very thing it
# was looking at being named. The fix it printed was character-for-character what the line
# already said. Found by a real drive, which went red on a report that was correct.

def test_an_id_inside_its_own_gloss_is_not_bare():
    line = "  - ITEM-001 (ITEM-001 — topwords: top-N word frequency report) — not current"
    assert sr.bare_ids(line) == []


def test_a_genuinely_bare_id_AFTER_a_gloss_is_still_caught():
    """The skip must end at the closing paren, not swallow the rest of the line."""
    line = "  - ITEM-001 (topwords) blocked by ITEM-009 — see it"
    assert [i for i, _ in sr.bare_ids(line)] == ["ITEM-009"]


def test_a_gloss_no_longer_repeats_the_id_it_is_glossing():
    known = {"ITEM-001": "ITEM-001 — topwords: top-N word frequency report"}
    assert sr.gloss("ITEM-001", known) == "ITEM-001 (topwords: top-N word frequency report)"


def test_an_id_appearing_MID_title_is_left_alone():
    """Only a LEADING occurrence is boilerplate; elsewhere it is part of the sentence."""
    known = {"ITEM-002": "regression pin for ITEM-001"}
    assert sr.gloss("ITEM-002", known) == "ITEM-002 (regression pin for ITEM-001)"


def test_a_title_that_is_ONLY_its_id_keeps_the_title_rather_than_emptying():
    known = {"ITEM-003": "ITEM-003"}
    assert sr.gloss("ITEM-003", known) == "ITEM-003 (ITEM-003)"


# ============================================================ the report failing its own lint
# `names()` read three owners — the decisions index, `goal.json`, and each item's `plan.md` — and
# an id is only in `items/` once something has PLANNED it. So every filed-but-unplanned item
# resolved to nothing, and the report's own LEFT field is made of exactly those. A drive printed
# `I-003` bare, failed its own lint for it, and offered "nothing names this id" about an entry
# sitting under a `### I-003 — …` heading two files away.

def _wf(tmp_path, backlog=None, goal=None, plans=None):
    wf = tmp_path / ".workflow"
    (wf / "items").mkdir(parents=True)
    if backlog:
        (wf / "backlog.md").write_text(backlog)
    if goal:
        (wf / "goal.json").write_text(json.dumps(goal))
    for ident, head in (plans or {}).items():
        (wf / "items" / ident).mkdir(parents=True, exist_ok=True)
        (wf / "items" / ident / "plan.md").write_text("# %s\n" % head)
    return str(wf)


def test_an_unplanned_backlog_id_resolves_to_its_backlog_heading(tmp_path):
    wf = _wf(tmp_path, backlog="### I-003 — re-present the reconcile to a human  · debt\n")
    assert sr.names(wf, str(tmp_path))["I-003"] == "re-present the reconcile to a human"


def test_a_PLAN_still_wins_over_the_backlog_line(tmp_path):
    """Once planned, the plan is the thing that named it; the backlog line is the older,
    thinner version of the same name."""
    wf = _wf(tmp_path, backlog="### I-003 — thin early wording\n",
             plans={"I-003": "the fuller name the plan gave it"})
    assert sr.names(wf, str(tmp_path))["I-003"] == "the fuller name the plan gave it"


def test_a_backlog_line_with_no_title_is_not_invented(tmp_path):
    wf = _wf(tmp_path, backlog="### I-004\n")
    assert "I-004" not in sr.names(wf, str(tmp_path))


# --- authored prose the report re-prints -------------------------------------------------

def test_a_bare_id_in_the_GOAL_STATEMENT_is_glossed(tmp_path):
    known = {"I-003": "re-present the reconcile to a human"}
    out = sr.name_ids_in_prose("NOTE: I-003 re-presents it.", known)
    assert out == "NOTE: I-003 (re-present the reconcile to a human) re-presents it."


def test_prose_BEFORE_an_already_glossed_id_survives(tmp_path):
    """The cursor bug, pinned: one variable for "emitted so far" and "do not match inside this"
    silently deleted the statement's first sentence while the lint went green — the worst
    possible pair of outcomes."""
    known = {"I-003": "re-present the reconcile to a human"}
    text = "Close the gap. Derived under D-001 (no human confirmed it); I-003 re-presents it."
    out = sr.name_ids_in_prose(text, known)
    assert out.startswith("Close the gap. Derived under D-001 (no human confirmed it);")
    assert "I-003 (re-present the reconcile to a human)" in out


def test_an_UNRESOLVABLE_id_in_prose_is_left_exactly_as_written(tmp_path):
    """Inventing a name here would hide the missing index row that is the real defect."""
    assert sr.name_ids_in_prose("see I-009 for this", {}) == "see I-009 for this"


def test_prose_with_no_ids_is_returned_unchanged(tmp_path):
    assert sr.name_ids_in_prose("nothing to see", {"I-1": "x"}) == "nothing to see"


# ============================================================ what counts as "already named"
# Three defects in one scanner, all found by drives on reports that were correct.

def test_a_gloss_whose_LABEL_is_not_id_shaped_still_shields_its_contents():
    """A parked checkpoint renders as `SPEC-<hex> (…)`, and `SPEC-aea09395eebc` is not an ID_RE
    id — hex, not digits. So no gloss was recognised and `I-001`, inside the ticket's own
    summary, was reported bare. The convention is `X (name)` for every X the report prints;
    what X looks like is not the question."""
    line = "  - SPEC-aea09395eebc (A spec change needs approval (item I-001).) — spec checkpoint"
    assert sr.bare_ids(line) == []


def test_parentheses_are_matched_in_BALANCE():
    """Taking the first `)` ended the span at `(item I-001)` and left the rest exposed. Nested
    parentheses are ordinary in an authored summary."""
    line = "  - TCK-1 (outer (inner I-001) still inside I-002) done"
    assert sr.bare_ids(line) == []


def test_a_TRUNCATED_gloss_still_shields_what_survived():
    """Bullets are cut to a width, so a gloss can lose its closing paren. What was cut off is
    still part of the name."""
    line = "  - A-1 (criterion text) — by I-001 (Plan — I-001 · Implement `don"
    assert sr.bare_ids(line) == []


def test_the_LABEL_of_a_gloss_is_named_by_it():
    """The label lives OUTSIDE its own span — the span starts at the `(` — so "inside a gloss"
    does not cover it. Dropping this reported every correctly-named id as bare."""
    assert sr.bare_ids("I-001 (the name) and `I-002` (another)") == []


def test_a_GENUINELY_bare_id_after_a_gloss_is_still_caught():
    """The negative control. Widening what counts as named must not blind the lint."""
    line = "  - A-1 (criterion text) — blocked by I-009, see it"
    assert [i for i, _ in sr.bare_ids(line)] == ["I-009"]


def test_a_bare_id_BEFORE_any_gloss_is_still_caught():
    line = "  - I-009 is blocked by A-1 (criterion text)"
    assert [i for i, _ in sr.bare_ids(line)] == ["I-009"]


def test_a_parenthesis_that_opens_a_CLAUSE_shields_nothing():
    """`(` after a space is punctuation, not a gloss. Treating every parenthesis as a name would
    let a bare id hide inside any aside."""
    line = "  - the work stalled (blocked by I-009) this week"
    assert [i for i, _ in sr.bare_ids(line)] == ["I-009"]
