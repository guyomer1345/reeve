"""Tests for reckon.py — is the last N commits' work actually moving the goal.

Three properties carry it, and each is the answer to something measured on a real drifted project:
the window rate is NOT the stall streak (which one lucky discharge resets to zero), an unreachable
goal outranks a slow window (no amount of building fixes it), and a window that moved nothing can
never read as `progressing` however the reading skill feels about it.
"""
import json
import os
import subprocess

import reckon

ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def project(tmp_path, acceptance=3):
    wf = tmp_path / ".workflow"
    (wf / "items").mkdir(parents=True, exist_ok=True)
    (wf / "maintenance").mkdir(parents=True, exist_ok=True)
    (wf / "config.json").write_text(json.dumps({"project_root": "."}))
    (wf / "goal.json").write_text(json.dumps({
        "id": "G-1", "statement": "ship it",
        "acceptance": [{"id": "ga-%d" % i, "text": "a%d" % i}
                       for i in range(1, acceptance + 1)]}))
    (wf / "goal-ledger.jsonl").write_text("")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    commit(tmp_path, "root")
    return str(tmp_path)


def commit(root, msg):
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", msg, "--allow-empty"],
                   check=True, env=dict(os.environ, **ENV))


def promote(root, item, refs):
    """Close an item the way `document` does — one ledger line — and commit it."""
    led = os.path.join(root, ".workflow", "goal-ledger.jsonl")
    with open(led, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"goal": "G-1", "item": item, "refs": refs}) + "\n")
    commit(root, "feat: %s" % item)


def bind(root, item, refs):
    """An OPEN item's binding — `planned`, worth nothing yet, but not `unbound`."""
    d = os.path.join(root, ".workflow", "items", item)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "promises.json"), "w", encoding="utf-8") as fh:
        json.dump({"criteria": [{"id": "ac-1", "gate": "artifact", "discharge": "lint",
                                 "goal_ref": r} for r in refs]}, fh)


# --- the window is not the stall streak ---------------------------------------

def test_a_window_that_moved_NOTHING_can_never_read_as_progressing(tmp_path):
    """THE FLOOR. A loop grading its own progress drifts toward "yes" — the same reason the
    autonomy floor exists — so this is arithmetic, not a reading."""
    root = project(tmp_path)
    bind(root, "I-open", ["ga-1", "ga-2", "ga-3"])   # all bound: nothing reads as unreachable
    for i in range(3):
        promote(root, "I-%d" % i, [])
    res = reckon.measure(root)
    assert res["verdict"] == "no-progress"
    assert res["items_closed"] == 3 and res["acceptance_moved"] == []


def test_ONE_LUCKY_DISCHARGE_does_not_clear_the_window(tmp_path):
    """The stall streak's own weakness, measured on `consumer`: five straight items that moved
    nothing, then one that did, and the streak reads 0 — "not stalled" — while the owner was
    re-steering the queue by hand. A window rate cannot be reset by one item."""
    root = project(tmp_path, acceptance=3)
    for i in range(5):
        bind(root, "I-%d" % i, ["ga-2", "ga-3"])
        promote(root, "I-%d" % i, [])
    promote(root, "I-lucky", ["ga-1"])
    res = reckon.measure(root)
    assert res["acceptance_moved"] == ["ga-1"]
    assert res["items_closed"] == 6, "all six items are in the window, not just the last"
    # Progress is real but thin, and the pass still SAYS what the window cost.
    assert res["commits_per_item"] is not None


def test_a_HEALTHY_window_reads_as_progressing(tmp_path):
    """The negative control. Without it this is just a pass that always complains."""
    root = project(tmp_path, acceptance=2)
    promote(root, "I-1", ["ga-1"])
    promote(root, "I-2", ["ga-2"])
    res = reckon.measure(root)
    assert res["verdict"] == "progressing", res["findings"]
    assert res["findings"] == []


# --- the goal itself is the thing that is wrong -------------------------------

def test_UNBOUND_acceptance_makes_the_goal_unreachable_and_outranks_a_slow_window(tmp_path):
    """The signal `converge.py` has computed since day one and nothing has ever consumed.
    Measured live: 3 of 7 on one project, 10 of 13 on another — the second cannot be met as
    planned, and no amount of building changes that."""
    root = project(tmp_path, acceptance=3)
    bind(root, "I-1", ["ga-1"])
    promote(root, "I-1", ["ga-1"])
    res = reckon.measure(root)
    assert res["verdict"] == "goal-unreachable"
    assert res["unbound"] == ["ga-2", "ga-3"]
    assert "cannot be met as currently planned" in res["findings"][0]


def test_unbound_does_NOT_cry_wolf_before_any_item_has_closed(tmp_path):
    """A goal minted an hour ago has everything unbound because nothing is planned yet. Firing
    there would teach the operator to ignore the one finding that matters most."""
    root = project(tmp_path, acceptance=3)
    commit(root, "chore: some work with no item behind it")
    res = reckon.measure(root)
    assert res["verdict"] != "goal-unreachable"
    assert res["items_closed"] == 0


# --- looping around a problem --------------------------------------------------

def test_CHURN_is_measured_as_commits_per_closed_item(tmp_path):
    """Decidable where "did we go round in circles" is not: the item dirs that would show the
    refine/debug cycles are pruned at promote time. The baseline is measured (1.56 / 1.60 on two
    live projects), so twice it is the line."""
    root = project(tmp_path, acceptance=1)
    for i in range(6):
        commit(root, "fix: attempt %d at the same thing" % i)
    bind(root, "I-1", ["ga-1"])
    promote(root, "I-1", ["ga-1"])
    res = reckon.measure(root)
    assert res["commits_per_item"] >= reckon.BASELINE_COMMITS_PER_ITEM * reckon.CHURN_MULTIPLE
    assert res["verdict"] == "churning", res
    assert any("baseline" in f for f in res["findings"])


# --- the window's anchor -------------------------------------------------------

def test_the_window_opens_at_the_LAST_RECKON_not_the_first_commit(tmp_path):
    """And `--diff-filter=A` is load-bearing: a later maintenance pass DELETES this receipt (the
    directory is self-collecting), and a plain path filter would match the deletion and measure
    the window from the wrong end."""
    root = project(tmp_path, acceptance=2)
    promote(root, "I-1", ["ga-1"])
    rec = os.path.join(root, ".workflow", "maintenance", "reckon-001.json")
    with open(rec, "w", encoding="utf-8") as fh:
        json.dump({"item": "reckon-001", "kind": "reckon", "summary": "looked"}, fh)
    commit(root, "chore(reckon): the anchor")
    os.remove(rec)                                  # the next maintenance pass collects it
    commit(root, "chore(audit): a later pass deletes it")
    promote(root, "I-2", ["ga-2"])
    res = reckon.measure(root)
    assert res["items_closed"] == 1, "only the item after the last reckon is in the window"
    assert res["acceptance_moved"] == ["ga-2"]
    assert res["base_why"] == "the last reckon"


def test_a_TORN_ledger_line_before_the_window_does_not_shift_it(tmp_path):
    """The window index counts entries the way `converge.read_ledger` does, because it indexes
    into that list. Counting raw lines would misalign by one per torn line and attribute another
    window's item to this one."""
    root = project(tmp_path, acceptance=2)
    led = os.path.join(root, ".workflow", "goal-ledger.jsonl")
    with open(led, "a", encoding="utf-8") as fh:
        fh.write("{not json at all\n")
    promote(root, "I-1", ["ga-1"])
    rec = os.path.join(root, ".workflow", "maintenance", "reckon-001.json")
    with open(rec, "w", encoding="utf-8") as fh:
        json.dump({"item": "reckon-001", "kind": "reckon", "summary": "looked"}, fh)
    commit(root, "chore(reckon): the anchor")
    promote(root, "I-2", ["ga-2"])
    res = reckon.measure(root)
    assert res["items_closed"] == 1 and res["acceptance_moved"] == ["ga-2"]


def test_no_goal_is_its_own_verdict(tmp_path):
    root = project(tmp_path)
    os.remove(os.path.join(root, ".workflow", "goal.json"))
    commit(root, "chore: drop the goal")
    assert reckon.measure(root)["verdict"] == "no-goal"


def test_a_tree_with_no_git_reports_unknown_and_blocks_nothing(tmp_path):
    """Fail direction: this pass has no veto over anything, so an unreadable input costs a cycle
    and nothing else."""
    (tmp_path / ".workflow").mkdir()
    res = reckon.measure(str(tmp_path))
    assert res["verdict"] == "unknown"
    assert reckon.due(str(tmp_path))[0] is False, "cannot tell ⇒ do not inject"


# --- the clock ------------------------------------------------------------------

def test_due_fires_at_the_configured_count(tmp_path):
    root = project(tmp_path, acceptance=1)
    assert reckon.every_n(root) == reckon.DEFAULT_EVERY == 5
    for _ in range(4):
        commit(root, "chore: tick")
    assert reckon.due(root)[0] is False, "four commits is not five"
    commit(root, "chore: tick")
    assert reckon.due(root)[0] is True


def test_the_count_is_a_KNOB_and_nonsense_falls_back(tmp_path):
    """Two projects is two projects — the baseline is measured, not universal. A mistyped knob
    must fall back rather than silently switch the anchor off."""
    root = project(tmp_path, acceptance=1)
    cfg = os.path.join(root, ".workflow", "config.json")
    with open(cfg, "w", encoding="utf-8") as fh:
        json.dump({"project_root": ".", "reckon": {"every_n_commits": 2}}, fh)
    assert reckon.every_n(root) == 2
    with open(cfg, "w", encoding="utf-8") as fh:
        json.dump({"project_root": ".", "reckon": {"every_n_commits": "soon"}}, fh)
    assert reckon.every_n(root) == reckon.DEFAULT_EVERY
