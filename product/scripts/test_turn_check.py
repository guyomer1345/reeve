"""Tests for turn_check.py — may this turn end, and what does it owe before it does.

The ladder's whole value is that ending an unattended turn stops being the default, so the tests
that matter are the ones that pin the CLOSED SET of reasons a turn may end. Each reason has a
test, because a missing one is not a bug that shows up as noise — it is a session that gets
blocked forever with a legitimate reason to stop.
"""
import json
import os
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


# ============================================================ rung 2 — the anchor is an anchor
# `base_sha` is the anchor's one load-bearing field: a resumed session reads
# `git log <base_sha>..HEAD` against it. It was ASKED FOR in `/dispatch` and in
# `handoff_gate.py`'s instruction and CHECKED nowhere except under context pressure, so the
# ordinary path — a session rewriting the anchor at the end of an item with plenty of context
# left — could leave a handoff that is prose with no resume in it. A real greenfield drive did
# exactly that, twice, while brownfield's was fine. Nothing inside the package was looking; the
# seam that caught it lives in the smoke harness, one layer up.

def _endable(tmp_path, anchor=None):
    """A project whose turn MAY legitimately end, so rung 1 does not shadow rung 2."""
    wf = project(tmp_path, status="idle")
    if anchor is not None:
        with open(os.path.join(wf, "handoff.md"), "w") as fh:
            fh.write(anchor)
    return wf


def test_an_anchor_with_no_base_sha_blocks_the_turn(tmp_path):
    res = tc.check(_endable(tmp_path, "# Handoff\n\nprose about where we are\n"))
    assert res["demand"] == "anchor", res
    assert "base_sha" in res["why"]
    assert "git rev-parse HEAD" in res["instruction"], "it must say how to get the id"


def test_base_sha_UNKNOWN_is_caught_too(tmp_path):
    """The shape a session writes when it did not look. It reads as a field that is there."""
    for filler in ("unknown", "none", ""):
        res = tc.check(_endable(tmp_path, "# Handoff\n\nbase_sha: %s\n" % filler))
        assert res["demand"] == "anchor", (filler, res)


def test_a_REAL_base_sha_falls_through_to_the_next_rung(tmp_path):
    res = tc.check(_endable(tmp_path, "# Handoff\n\nbase_sha: 29483cf (B-3's base)\n"))
    assert res["demand"] != "anchor", res


def test_NO_anchor_at_all_is_not_this_rungs_business(tmp_path):
    """That is `handoff_gate.py`'s, under the band. A project that has never written one must
    not be blocked here — the two gates would demand different things on the same turn, which
    is the failure the ladder's one-rung-wins rule exists to prevent."""
    wf = _endable(tmp_path)
    assert not os.path.exists(os.path.join(wf, "handoff.md"))
    assert tc.check(wf)["demand"] != "anchor"


def test_an_unreadable_context_band_stays_PERMISSIVE(tmp_path, monkeypatch):
    """Fail direction is permissive on every path in this file, and this rung is no exception:
    a gate that stopped a session from ending AT ALL is the more expensive failure."""
    wf = _endable(tmp_path, "# Handoff\n\nno base here\n")
    monkeypatch.setitem(__import__("sys").modules, "context_band", None)
    assert tc.check(wf)["demand"] != "anchor"


def test_the_anchor_rung_does_not_outrank_a_turn_that_may_not_END(tmp_path):
    """Rung order, asserted rather than assumed: a session that announced work and abandoned it
    is told to continue, not to go and tidy a file."""
    wf = project(tmp_path, status="building")
    with open(os.path.join(wf, "handoff.md"), "w") as fh:
        fh.write("# Handoff\n\nno base here\n")
    assert tc.check(wf)["demand"] == "continue"


# ============================================================ rung 3 — was the work dispatched
# `planner`, `execute` and `document` are dispatch-only: "you never do a node's work yourself",
# "a property of the node, not a judgement call". Two real drives took an item ALL THE WAY ROUND
# — built, verified, documented, committed — with no worker anywhere, once on greenfield and
# once on brownfield, and both items looked perfect. That is what makes it worth a rung: the cost
# is invisible and compounding. The router's context holds what a worker would have handed back
# as a pointer, the worker token cap has nothing to cap, a wave has nothing to run in parallel,
# and `execute`'s refusal to guess is replaced by the router simply deciding.

def _with_items(tmp_path, promoted=(), status="idle"):
    wf = project(tmp_path, status=status)
    with open(os.path.join(wf, "handoff.md"), "w") as fh:
        fh.write("base_sha: abc1234\n")          # past rung 2
    for ident in promoted:
        d = os.path.join(wf, "items", ident)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "promoted.json"), "w") as fh:
            json.dump({"promoted": True}, fh)
    return wf


def test_an_item_finished_with_NO_worker_blocks_the_turn(tmp_path):
    wf = _with_items(tmp_path, promoted=["I-1"])
    res = tc.check(wf, prev_promoted=[], workers_seen=0)
    assert res["demand"] == "dispatch", res
    assert "I-1" in res["why"]
    assert "reeve:execute" in res["instruction"], "it must name the correction"
    assert "do not rebuild" in res["instruction"], "the built item stands; the NEXT one is the fix"


def test_a_dispatched_item_falls_through(tmp_path):
    wf = _with_items(tmp_path, promoted=["I-1"])
    assert tc.check(wf, prev_promoted=[], workers_seen=3)["demand"] != "dispatch"


def test_it_fires_ONCE_per_item_not_every_turn_after(tmp_path):
    """The breach has already happened; repeating the demand would only wedge the session."""
    wf = _with_items(tmp_path, promoted=["I-1"])
    assert tc.check(wf, prev_promoted=["I-1"], workers_seen=0)["demand"] != "dispatch"


def test_CANNOT_TELL_either_input_stays_silent(tmp_path):
    """A gate that fires when it does not know is a gate that gets switched off."""
    wf = _with_items(tmp_path, promoted=["I-1"])
    assert tc.check(wf, prev_promoted=None, workers_seen=0)["demand"] != "dispatch"
    assert tc.check(wf, prev_promoted=[], workers_seen=None)["demand"] != "dispatch"


def test_a_session_that_moved_NOTHING_is_not_blamed_for_an_inherited_item(tmp_path):
    """A session that promoted an item and died before its Stop hook ran never got it into the
    latch, so the next session sees it as fresh with none of its own workers."""
    wf = _with_items(tmp_path, promoted=["I-1"])
    _, fp = tc.moved(wf, None)
    res = tc.check(wf, prev_fingerprint=fp, prev_promoted=[], workers_seen=0)
    assert res["demand"] != "dispatch", "nothing moved this turn, so nothing was built this turn"


def test_the_promoted_set_is_reported_so_the_caller_can_latch_it(tmp_path):
    wf = _with_items(tmp_path, promoted=["I-1", "I-2"])
    assert tc.check(wf, prev_promoted=[], workers_seen=3)["promoted"] == ["I-1", "I-2"]


def test_a_turn_that_MAY_NOT_END_still_outranks_the_dispatch_rung(tmp_path):
    """Ladder order asserted, not assumed: abandoning work in flight is the worse failure."""
    wf = _with_items(tmp_path, promoted=["I-1"], status="building")
    assert tc.check(wf, prev_promoted=[], workers_seen=0)["demand"] == "continue"


def test_a_BROKEN_ANCHOR_outranks_the_dispatch_rung(tmp_path):
    """Losing the loop's place breaks the next session outright; this breach has already
    happened and its correction is the next item."""
    wf = _with_items(tmp_path, promoted=["I-1"])
    with open(os.path.join(wf, "handoff.md"), "w") as fh:
        fh.write("no base here\n")
    assert tc.check(wf, prev_promoted=[], workers_seen=0)["demand"] == "anchor"


# ============================================================ rung 1 — the goal that was never minted
# MEASURED, twice (runs 6 and 8 of the D227 campaign): greenfield dispatched workers correctly
# and simply never ran `planner:decompose`, so no goal was minted. The item-level rung above
# cannot see this — every item had a worker behind it; the node that never happened has no
# item. What made it expensive is that nothing said so: `converge.py` has nothing to measure,
# every gate built on convergence has nothing to read, and the drive loses its stop-when-done.

def _goalless(tmp_path, promoted=(), status="building"):
    wf = _with_items(tmp_path, promoted=promoted, status=status)
    os.remove(os.path.join(wf, "goal.json"))
    return wf


def test_a_building_loop_with_no_goal_is_not_told_it_is_NEITHER_MET_NOR_STALLED(tmp_path):
    """The sentence that was there before asserted something about a goal that does not exist —
    and `met`/`stalled` are not merely false here, they are unreachable."""
    wf = _goalless(tmp_path)
    ok, why = tc.may_end(wf)
    assert not ok
    assert "NO GOAL IS SET" in why and "stop-when-done" in why
    assert "neither met nor stalled" not in why


def test_planned_work_with_no_goal_demands_the_node_that_mints_one(tmp_path):
    """The rung: inception is behind a loop that has planned an item, so a missing goal is a
    node that did not run — and the demand names both paths that mint one."""
    wf = _goalless(tmp_path, promoted=["I-1"])
    res = tc.check(wf, prev_promoted=["I-1"], workers_seen=2)
    assert res["demand"] == "goal", res
    assert "decompose" in res["instruction"] and "reconcile" in res["instruction"]
    assert "steer" in res["instruction"], \
        "a project that really means to run goal-less needs a way to say so"


def test_a_PLANNED_item_is_enough_long_before_anything_is_promoted(tmp_path):
    """MEASURED, and it is why this rung is not keyed on promotion: the third occurrence
    dispatched `research` and then `planner` in plan-one mode on a roadmap item the router had
    minted itself, and promoted NOTHING in the whole session. A promotion-keyed rung watched an
    hour of that go by in silence. `planner` mkdirs the item dir when it plans, and both graph
    paths mint the goal before anything is planned."""
    wf = _goalless(tmp_path)
    os.makedirs(os.path.join(wf, "items", "ROAD-1"))
    with open(os.path.join(wf, "items", "ROAD-1", "plan.md"), "w") as fh:
        fh.write("# ROAD-1 — slugify\n")
    res = tc.check(wf, prev_promoted=[], workers_seen=1)
    assert res["demand"] == "goal", res
    assert res["promoted"] == [], "nothing was promoted — that is the whole point"


def test_a_loop_still_INSIDE_inception_is_not_accused_of_skipping_it(tmp_path):
    """Nothing PLANNED yet: the goal is missing because the node that mints it has not run
    YET, which is every project's first few turns and is not a breach."""
    wf = _goalless(tmp_path)
    res = tc.check(wf, prev_promoted=[], workers_seen=1)
    assert res["demand"] == "continue", res


def test_the_goal_rung_does_not_fire_when_the_turn_MAY_end(tmp_path):
    """It is a better reason for rung 1's verdict, not a fifth rung: a parked ticket is still a
    legitimate reason to stop, goal or no goal."""
    wf = _goalless(tmp_path, promoted=["I-1"])
    with open(os.path.join(wf, "parked", "TCK-9.json"), "w") as fh:
        json.dump({"ticket_id": "TCK-9", "checkpoint": {"kind": "steer"}}, fh)
    res = tc.check(wf, prev_promoted=["I-1"], workers_seen=2)
    assert res["demand"] != "goal", res


def test_an_UNREADABLE_goal_is_not_a_skipped_node(tmp_path):
    """`_goal_missing` answers only on confirmed absence. A goal that exists and will not parse
    is a different fault, and telling that session it skipped decompose sends it to rewrite a
    file that is already there."""
    wf = _with_items(tmp_path, promoted=["I-1"], status="building")
    with open(os.path.join(wf, "goal.json"), "w") as fh:
        fh.write("{not json")
    res = tc.check(wf, prev_promoted=["I-1"], workers_seen=2)
    assert res["demand"] != "goal", res
