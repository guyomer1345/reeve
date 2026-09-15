"""Tests for turn_check.py — may this turn end, and what does it owe before it does.

The ladder's whole value is that ending an unattended turn stops being the default, so the tests
that matter are the ones that pin the CLOSED SET of reasons a turn may end. Each reason has a
test, because a missing one is not a bug that shows up as noise — it is a session that gets
blocked forever with a legitimate reason to stop.
"""
import json
import subprocess

import turn_check as tc


def project(tmp_path, status="building", parked=False, paused=False,
            acceptance=2, discharged=(), git=True):
    if git:
        # A real repo, because `drive.fingerprint` is HEAD plus the anchor set and returns None
        # without git — which is the permissive path, not the one these tests are about.
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
        (tmp_path / "f").write_text("x")
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin"}
        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "x"], check=True, env=env)
    wf = tmp_path / ".workflow"
    (wf / "items").mkdir(parents=True, exist_ok=True)
    (wf / "parked").mkdir(parents=True, exist_ok=True)
    (wf / "config.json").write_text(json.dumps({"project_root": "."}))
    (wf / "state.json").write_text(json.dumps({"status": status, "node": "execute"}))
    (wf / "goal.json").write_text(json.dumps({
        "id": "G-1", "statement": "ship it",
        "acceptance": [{"id": "ga-%d" % i, "text": "acceptance %d" % i}
                       for i in range(1, acceptance + 1)]}))
    (wf / "goal-ledger.jsonl").write_text("".join(
        json.dumps({"goal": "G-1", "item": "I-%03d" % n, "refs": list(r)}) + "\n"
        for n, r in enumerate(discharged)))
    if parked:
        (wf / "parked" / "TCK-1.json").write_text(json.dumps(
            {"ticket_id": "TCK-1", "checkpoint": {"kind": "qa"}}))
    if paused:
        (wf / "control.json").write_text(json.dumps({"paused": True}))
    return str(wf)


# --- rung 1: the closed set of reasons a turn may end ------------------------

def test_a_building_loop_with_no_reason_MAY_NOT_end(tmp_path):
    """The complaint, verbatim: it stops for nothing, with nobody there to notice."""
    ok, why = tc.may_end(project(tmp_path))
    assert not ok and "no reason for this turn to end" in why


def test_a_parked_checkpoint_is_a_reason(tmp_path):
    ok, why = tc.may_end(project(tmp_path, parked=True))
    assert ok and "parked" in why


def test_a_paused_loop_is_a_reason(tmp_path):
    ok, why = tc.may_end(project(tmp_path, paused=True))
    assert ok and "paused" in why


def test_an_IDLE_loop_is_a_reason(tmp_path):
    """Backlog empty, awaiting steering — `state.json`'s own word for finished-for-now."""
    ok, why = tc.may_end(project(tmp_path, status="idle"))
    assert ok and "not building" in why


def test_a_MET_goal_is_a_reason(tmp_path):
    ok, why = tc.may_end(project(tmp_path, acceptance=2, discharged=(["ga-1"], ["ga-2"])))
    assert ok and "met" in why


def test_a_STALLED_goal_is_a_reason(tmp_path):
    """The same verdict the driver stops on — never a second opinion about it."""
    wf = project(tmp_path, acceptance=2, discharged=(["ga-1"],) + tuple([[]] * 6))
    ok, why = tc.may_end(wf)
    assert ok and "stalled" in why


def test_unreadable_state_MAY_END(tmp_path):
    """Permissive on every failure: a session wrongly stopped from ending loses everything it
    was doing, and that failure cannot be recovered by typing the command again."""
    wf = tmp_path / ".workflow"
    wf.mkdir()
    ok, why = tc.may_end(str(wf))
    assert ok and "nothing to block" in why


# --- the two shapes of a stop for nothing, which send you to different places -

def test_a_turn_that_moved_NOTHING_is_told_so(tmp_path):
    wf = project(tmp_path)
    import drive
    # The previous stop's fingerprint IS the current one: nothing landed in between.
    res = tc.check(wf, prev_fingerprint=drive.fingerprint(wf))
    assert res["demand"] == "continue"
    assert "moved NOTHING durable" in res["instruction"]


def test_a_turn_that_moved_and_stopped_anyway_is_told_SOMETHING_ELSE(tmp_path):
    wf = project(tmp_path)
    res = tc.check(wf, prev_fingerprint="the fingerprint before this turn landed anything")
    assert res["demand"] == "continue"
    assert "DID move the loop and then stopped anyway" in res["instruction"]


def test_with_no_previous_fingerprint_it_states_neither_shape(tmp_path):
    """The first turn of a session has nothing to compare against, and a gate that guessed
    would tell the reader the wrong thing about their own turn."""
    res = tc.check(project(tmp_path))
    assert res["demand"] == "continue"
    assert "moved NOTHING" not in res["instruction"]
    assert "DID move" not in res["instruction"]


# --- rung 2: the report ------------------------------------------------------

def test_a_turn_that_may_end_still_owes_the_REPORT(tmp_path):
    res = tc.check(project(tmp_path, parked=True))
    assert res["demand"] == "report" and "no goal report was given" in res["why"]


def test_pasting_the_current_block_satisfies_it(tmp_path):
    wf = project(tmp_path, parked=True)
    import status_report as sr
    res = tc.check(wf, last_text="here you go\n" + sr.render(sr.build(wf)))
    assert res["demand"] is None


def test_a_STALE_block_is_refused_and_SAYS_it_is_stale(tmp_path):
    """Different from "no report": it sends the reader to a different mistake — pasting an old
    block rather than forgetting one."""
    wf = project(tmp_path, parked=True)
    res = tc.check(wf, last_text="[reeve-report state:000000000000]")
    assert res["demand"] == "report" and "stale" in res["why"]


def test_an_UNCHANGED_loop_is_not_asked_for_the_same_block_twice(tmp_path):
    """The nuisance objection, answered mechanically — this is what keeps the gate switched on."""
    wf = project(tmp_path, parked=True)
    import status_report as sr
    digest = sr.digest(sr.build(wf))
    assert tc.check(wf, satisfied_digest=digest)["demand"] is None


def test_the_report_rung_NEVER_preempts_rung_one(tmp_path):
    """A turn told two things at once obeys neither."""
    res = tc.check(project(tmp_path))
    assert res["demand"] == "continue"


def test_rung_one_passing_does_not_require_a_goal_at_all(tmp_path):
    """The loop runs item-at-a-time without a goal; that is a state, not an error."""
    wf = project(tmp_path, status="idle")
    (tmp_path / ".workflow" / "goal.json").unlink()
    res = tc.check(wf, last_text="")
    assert res["demand"] == "report"          # still owed — the block renders "GOAL — none set"
