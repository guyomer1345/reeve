"""Tests for converge.py — is the goal converging, and is it met?

The asymmetry is the whole point and every test here leans on it. `met` ends an autonomous
drive, so a wrong `met` is unrecoverable without a human noticing; `stalled` merely asks for a
human glance. So the cases that matter most are the ones where something is BROKEN — no goal,
no acceptance, an unreadable item, a torn ledger line — and the assertion is always the same:
not met.

The second theme is that progress is measured at ITEM CLOSE and nowhere else. A plan binding an
acceptance is a promise, and the tests pin that a promise reads as `planned`, never `discharged`
— that distinction is the difference between a measure and a motivational poster.
"""
import json
import os

import pytest

import converge


def _wf(tmp_path, goal=None, ledger=(), items=None):
    wf = tmp_path / "wf"
    wf.mkdir(parents=True, exist_ok=True)
    if goal is not None:
        (wf / "goal.json").write_text(json.dumps(goal), encoding="utf-8")
    if ledger:
        (wf / "goal-ledger.jsonl").write_text(
            "".join(json.dumps(e) + "\n" if isinstance(e, dict) else e + "\n" for e in ledger),
            encoding="utf-8")
    for name, spec in (items or {}).items():
        d = wf / "items" / name
        d.mkdir(parents=True)
        if spec.get("promises") is not None:
            (d / "promises.json").write_text(json.dumps(spec["promises"]), encoding="utf-8")
        if spec.get("promoted"):
            (d / "promoted.json").write_text('{"promoted": true}', encoding="utf-8")
    return str(wf)


GOAL = {"id": "g-1", "statement": "ship checkout",
        "acceptance": [{"id": "ga-1", "text": "a"}, {"id": "ga-2", "text": "b"}]}


def _m(wf):
    return converge.measure(converge.read_goal(wf), converge.read_ledger(wf),
                            converge.open_bindings(wf))


def _crit(*refs):
    return {"criteria": [{"id": "ac-%d" % i, "gate": "artifact", "discharge": "t",
                          "goal_ref": r} for i, r in enumerate(refs, 1)]}


# --- the completion predicate -------------------------------------------------

def test_met_only_when_every_acceptance_is_discharged(tmp_path):
    wf = _wf(tmp_path, GOAL, ledger=[{"goal": "g-1", "item": "i-1", "refs": ["ga-1"]}])
    assert _m(wf)["met"] is False
    wf2 = _wf(tmp_path / "b", GOAL, ledger=[{"item": "i-1", "refs": ["ga-1", "ga-2"]}])
    assert _m(wf2)["met"] is True


def test_an_open_item_binding_an_acceptance_is_planned_not_discharged(tmp_path):
    """The measure must not move on a promise. This is the failure mode 12d exists for: a loop
    that reads progress off its own plans reports motion while delivering nothing."""
    wf = _wf(tmp_path, GOAL, items={"i-1": {"promises": _crit("ga-1", "ga-2")}})
    m = _m(wf)
    assert m["met"] is False
    assert m["status"] == {"ga-1": "planned", "ga-2": "planned"}
    assert m["discharged"] == []


def test_a_promoted_items_bindings_are_not_counted_twice(tmp_path):
    """A promoted item is the ledger's to report. Counting its on-disk promises.json as well
    would let one item both discharge and 'plan' the same id."""
    wf = _wf(tmp_path, GOAL,
             ledger=[{"item": "i-1", "refs": ["ga-1"]}],
             items={"i-1": {"promises": _crit("ga-1"), "promoted": True}})
    assert converge.open_bindings(wf) == {}
    assert _m(wf)["status"]["ga-1"] == "discharged"


def test_unbound_acceptance_is_reported_before_any_work_happens(tmp_path):
    wf = _wf(tmp_path, GOAL, items={"i-1": {"promises": _crit("ga-1")}})
    m = _m(wf)
    assert m["unbound"] == ["ga-2"]
    assert m["met"] is False


# --- stall --------------------------------------------------------------------

def test_stall_fires_after_the_limit_of_no_progress_promotions(tmp_path):
    led = [{"item": "i-0", "refs": ["ga-1"]}]
    led += [{"item": "i-%d" % i, "refs": []} for i in range(1, converge.STALL_LIMIT + 1)]
    m = _m(_wf(tmp_path, GOAL, ledger=led))
    assert m["streak"] == converge.STALL_LIMIT
    assert m["stalled"] is True


def test_one_promotion_short_of_the_limit_is_not_a_stall(tmp_path):
    led = [{"item": "i-%d" % i, "refs": []} for i in range(converge.STALL_LIMIT - 1)]
    assert _m(_wf(tmp_path, GOAL, ledger=led))["stalled"] is False


def test_rediscarging_a_live_id_counts_as_no_progress(tmp_path):
    """Re-fixing the same acceptance over and over is the churn this catches. The id is in the
    goal and 'succeeds' every time, so a naive membership test would read it as progress."""
    led = [{"item": "i-0", "refs": ["ga-1"]}]
    led += [{"item": "i-%d" % i, "refs": ["ga-1"]} for i in range(1, converge.STALL_LIMIT + 1)]
    m = _m(_wf(tmp_path, GOAL, ledger=led))
    assert m["stalled"] is True
    assert m["discharged"] == ["ga-1"]


def test_a_met_goal_is_never_reported_stalled(tmp_path):
    """Otherwise finishing early and then doing maintenance would raise an alarm about a goal
    that is done."""
    led = [{"item": "i-0", "refs": ["ga-1", "ga-2"]}]
    led += [{"item": "i-%d" % i, "refs": []} for i in range(1, converge.STALL_LIMIT + 2)]
    m = _m(_wf(tmp_path, GOAL, ledger=led))
    assert m["met"] is True
    assert m["stalled"] is False


def test_refs_outside_the_goal_never_count_as_progress(tmp_path):
    """A stale ledger from a previous goal must not silently satisfy this one."""
    led = [{"item": "i-%d" % i, "refs": ["ga-OLD"]} for i in range(converge.STALL_LIMIT)]
    m = _m(_wf(tmp_path, GOAL, ledger=led))
    assert m["discharged"] == []
    assert m["stalled"] is True


# --- fail direction: every breakage lands on NOT MET ---------------------------

def test_no_goal_file_is_not_an_error_and_is_not_met(tmp_path):
    m = _m(_wf(tmp_path))
    assert m["met"] is False and m["goal"] is None


def test_a_goal_with_no_acceptance_is_never_met(tmp_path):
    """The one shape that would otherwise be vacuously true: all zero of its acceptance are
    discharged. A driver reading that as done would stop having built nothing."""
    m = _m(_wf(tmp_path, {"id": "g-1", "acceptance": []}))
    assert m["met"] is False
    assert "never be mechanically met" in m["reason"]


def test_unparseable_goal_reads_as_no_goal_rather_than_met(tmp_path):
    wf = tmp_path / "wf"
    wf.mkdir()
    (wf / "goal.json").write_text("{not json", encoding="utf-8")
    assert _m(str(wf))["met"] is False


def test_a_torn_ledger_line_does_not_blind_the_entries_before_it(tmp_path):
    wf = _wf(tmp_path, GOAL, ledger=[{"item": "i-1", "refs": ["ga-1"]}, "{partial"])
    assert _m(wf)["discharged"] == ["ga-1"]


def test_an_unreadable_item_manifest_is_skipped_not_fatal(tmp_path):
    wf = _wf(tmp_path, GOAL, items={"i-1": {"promises": None}, "i-2": {"promises": _crit("ga-1")}})
    (os.path.join(wf, "items", "i-1", "promises.json"))
    assert converge.open_bindings(wf) == {"ga-1": ["i-2"]}


# --- record -------------------------------------------------------------------

def test_record_appends_the_items_bindings(tmp_path):
    wf = _wf(tmp_path, GOAL, items={"i-1": {"promises": _crit("ga-1", "ga-2")}})
    converge.record(wf, "i-1")
    led = converge.read_ledger(wf)
    assert len(led) == 1 and led[0]["refs"] == ["ga-1", "ga-2"] and led[0]["item"] == "i-1"


def test_record_is_idempotent_by_item(tmp_path):
    """A crash between the append and `promoted.json` replays this. A duplicate entry would
    lengthen a stall streak that never happened — recovery corrupting the measure."""
    wf = _wf(tmp_path, GOAL, items={"i-1": {"promises": _crit("ga-1")}})
    converge.record(wf, "i-1")
    converge.record(wf, "i-1")
    assert len(converge.read_ledger(wf)) == 1


def test_record_of_an_item_with_no_goal_binding_still_appends(tmp_path):
    """It must: an item that moved no acceptance is exactly what the stall streak counts."""
    wf = _wf(tmp_path, GOAL, items={"i-1": {"promises": {"criteria": [{"id": "ac-1"}]}}})
    converge.record(wf, "i-1")
    assert converge.read_ledger(wf)[0]["refs"] == []


def test_record_without_a_goal_is_a_no_op(tmp_path):
    wf = _wf(tmp_path, items={"i-1": {"promises": _crit("ga-1")}})
    converge.record(wf, "i-1")
    assert converge.read_ledger(wf) == []


# --- cli exit codes -----------------------------------------------------------

def test_met_exit_code_tracks_the_predicate(tmp_path):
    wf = _wf(tmp_path, GOAL, ledger=[{"item": "i-1", "refs": ["ga-1", "ga-2"]}])
    assert converge.main(["--workflow-dir", wf, "met"]) == 0
    wf2 = _wf(tmp_path / "b", GOAL, ledger=[{"item": "i-1", "refs": ["ga-1"]}])
    assert converge.main(["--workflow-dir", wf2, "met"]) == 1


def test_check_exits_two_only_on_a_stall(tmp_path):
    led = [{"item": "i-%d" % i, "refs": []} for i in range(converge.STALL_LIMIT)]
    assert converge.main(["--workflow-dir", _wf(tmp_path, GOAL, ledger=led), "check"]) == 2
    assert converge.main(["--workflow-dir", _wf(tmp_path / "b", GOAL), "check"]) == 0


def test_met_exits_nonzero_when_there_is_no_goal(tmp_path):
    """The driver asks `met` to decide whether to stop. No goal must not read as done."""
    assert converge.main(["--workflow-dir", _wf(tmp_path), "met"]) == 1
