"""Tests for monitor.py — the heartbeat that watches the session a `Stop` hook cannot see.

The three properties that decide whether this is worth running at all: WAITING is never mistaken
for stalling (or it nudges a session that is correctly stopped), a working loop is never nudged
(or it drives keystrokes into a session mid-turn), and a stall escalates exactly once through the
channel that already reaches a human. Each has its negative control.
"""
import json
import os
import subprocess
import time

import monitor


def project(tmp_path, git=True):
    wf = tmp_path / ".workflow"
    (wf / "items").mkdir(parents=True, exist_ok=True)
    (wf / "parked").mkdir(parents=True, exist_ok=True)
    (wf / "state.json").write_text(json.dumps({"status": "building", "node": "execute"}))
    (wf / "goal.json").write_text(json.dumps(
        {"id": "G-1", "statement": "ship it",
         "acceptance": [{"id": "ga-1", "text": "it works"}]}))
    (wf / "goal-ledger.jsonl").write_text("")
    if git:
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
        (tmp_path / "f").write_text("x")
        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "x"], check=True,
                       env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                                GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t"))
    return str(wf)


def later(seconds):
    return time.time() + seconds


# --- waiting is not stalling --------------------------------------------------

def test_a_PARKED_checkpoint_is_waiting_not_stalling(tmp_path):
    """The drive is stopped on purpose and a human owes the answer. Nudging here is shouting at
    a session that is behaving correctly."""
    wf = project(tmp_path)
    (tmp_path / ".workflow" / "parked" / "TCK-1.json").write_text("{}")
    rec = monitor.observe(wf, now=later(100_000))
    assert rec["state"] == "waiting" and rec["action"] == "none"


def test_an_OPEN_DIALOG_is_waiting(tmp_path):
    """`D217`'s finding: a live session sat in a permission prompt, invisible to every other
    signal. It is waiting on a person, not stalled."""
    wf = project(tmp_path)
    (tmp_path / ".workflow" / "awaiting-input.json").write_text(json.dumps({"kind": "permission"}))
    assert monitor.observe(wf, now=later(100_000))["state"] == "waiting"


def test_a_PAUSED_loop_is_waiting(tmp_path):
    wf = project(tmp_path)
    (tmp_path / ".workflow" / "control.json").write_text(json.dumps({"paused": True}))
    assert monitor.observe(wf, now=later(100_000))["action"] == "none"


# --- a working loop is never nudged -------------------------------------------

def test_a_loop_that_is_WRITING_is_alive(tmp_path):
    wf = project(tmp_path)
    rec = monitor.observe(wf)
    assert rec["state"] == "moving" and rec["action"] == "none"


def test_a_long_item_with_no_new_ANCHOR_still_counts_as_alive(tmp_path):
    """The failure this design avoids: tying liveness to the fingerprint alone would call a long
    `execute` — which lands no anchor for an hour — a stall, and nudge a session that is working.
    The pulse is any write under `.workflow/`, not a node completing."""
    wf = project(tmp_path)
    import drive
    fp = drive.fingerprint(wf)
    os.utime(os.path.join(wf, "state.json"), None)          # the loop published its position
    rec = monitor.observe(wf)
    assert rec["state"] == "moving"
    assert rec["fingerprint"] == fp, "no anchor moved, and that is not the question"


# --- quiet, then one nudge, then an escalation --------------------------------

def test_a_QUIET_drive_gets_exactly_one_nudge(tmp_path):
    wf = project(tmp_path)
    rec = monitor.observe(wf, now=later(700))
    assert rec["state"] == "quiet" and rec["action"] == "nudge" and rec["nudges"] == 1


def test_it_does_not_nudge_TWICE_in_the_same_quiet_period(tmp_path):
    wf = project(tmp_path)
    monitor.write_record(wf, monitor.observe(wf, now=later(700)))
    rec = monitor.observe(wf, now=later(800))
    assert rec["action"] == "none" and rec["nudges"] == 1


def test_a_NEW_pulse_resets_everything(tmp_path):
    """A nudge that worked must leave no residue, or the next quiet period escalates early."""
    wf = project(tmp_path)
    monitor.write_record(wf, monitor.observe(wf, now=later(700)))
    os.utime(os.path.join(wf, "state.json"), None)
    rec = monitor.observe(wf)
    assert rec["state"] == "moving" and rec["nudges"] == 0


def test_a_drive_that_IGNORED_the_nudge_escalates(tmp_path):
    wf = project(tmp_path)
    monitor.write_record(wf, monitor.observe(wf, now=later(700)))
    rec = monitor.observe(wf, now=later(2_000))
    assert rec["state"] == "stalled" and rec["action"] == "escalate"


def test_the_escalation_PARKS_a_steer_and_the_floor_lets_it_through(tmp_path):
    """The whole point of the escalation: a checkpoint is what the away channel alerts on. And
    the steer floor — which refuses a park the goal's verdict does not support — must accept
    this one, or the monitor could observe a stall nobody is ever told about."""
    wf = project(tmp_path)
    monitor.write_record(wf, monitor.observe(wf, now=later(700)))
    rec = monitor.tick(wf, now=later(2_000))
    assert rec["parked"].get("ticket_id") == "steer-G-1-not-moving", rec["parked"]
    assert os.path.exists(os.path.join(wf, "parked", "steer-G-1-not-moving.json"))


def test_the_escalation_is_IDEMPOTENT(tmp_path):
    """A stall a human has not answered must not accumulate one ticket per poll — that is how an
    away channel trains someone to ignore it."""
    wf = project(tmp_path)
    monitor.write_record(wf, monitor.observe(wf, now=later(700)))
    monitor.tick(wf, now=later(2_000))
    # The park itself now makes the loop `waiting`, which is correct: a human owes an answer.
    assert monitor.observe(wf, now=later(3_000))["state"] == "waiting"
    assert len(os.listdir(os.path.join(wf, "parked"))) == 1


# --- fail direction: do nothing -----------------------------------------------

def test_a_project_with_no_git_still_observes_and_acts(tmp_path):
    """The fingerprint is for the steer floor's currency check, not for liveness; without git the
    monitor still sees that nothing is being written."""
    wf = project(tmp_path, git=False)
    rec = monitor.observe(wf, now=later(700))
    assert rec["fingerprint"] is None and rec["action"] == "nudge"


def test_an_unreadable_workflow_takes_NO_action(tmp_path):
    rec = monitor.observe(str(tmp_path / "nothing-here"))
    assert rec["state"] == "unknown" and rec["action"] == "none"


def test_the_cli_never_fails_on_a_project_that_is_not_initialised(tmp_path):
    assert monitor.main(["tick", "--workflow-dir", str(tmp_path / "nope")]) == 0
