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


def project(tmp_path, git=True, idle=True):
    """`idle=True` by default, because a session that has quietly ENDED a turn is the case the
    nudge exists for — a fixture without the flag describes one that is mid-turn, where a
    keystroke lands in the prompt box as text and is never submitted."""
    wf = tmp_path / ".workflow"
    (wf / "items").mkdir(parents=True, exist_ok=True)
    (wf / "parked").mkdir(parents=True, exist_ok=True)
    (wf / "state.json").write_text(json.dumps({"status": "building", "node": "execute"}))
    (wf / "goal.json").write_text(json.dumps(
        {"id": "G-1", "statement": "ship it",
         "acceptance": [{"id": "ga-1", "text": "it works"}]}))
    (wf / "goal-ledger.jsonl").write_text("")
    if idle:
        (wf / "session-idle.json").write_text(json.dumps({"kind": "idle_prompt"}))
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


def polled_through(wf, start, end, step=60):
    """Run the poller the way `supervise.sh` runs it — every `step` seconds — and return the last
    verdict.

    A test that jumps straight from one tick to one twenty minutes later is not describing a
    monitor that watched twenty minutes; it is describing one that was NOT RUNNING for nineteen
    of them, which is a different thing and has its own tests below. Quiet time comes from file
    mtimes and accrues either way, so the distinction has to be made by the caller.
    """
    rec, t = None, start
    while t <= end:
        rec = monitor.observe(wf, now=t)
        monitor.write_record(wf, rec)
        t += step
    return rec


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
    rec = polled_through(project(tmp_path), later(700), later(2_600))
    assert rec["state"] == "stalled" and rec["action"] == "escalate"


def test_the_escalation_PARKS_a_steer_and_the_floor_lets_it_through(tmp_path):
    """The whole point of the escalation: a checkpoint is what the away channel alerts on. And
    the steer floor — which refuses a park the goal's verdict does not support — must accept
    this one, or the monitor could observe a stall nobody is ever told about."""
    wf = project(tmp_path)
    polled_through(wf, later(700), later(2_500))
    rec = monitor.tick(wf, now=later(2_600))
    assert rec["parked"].get("ticket_id") == "steer-G-1-not-moving", rec["parked"]
    assert os.path.exists(os.path.join(wf, "parked", "steer-G-1-not-moving.json"))


def test_the_escalation_is_IDEMPOTENT(tmp_path):
    """A stall a human has not answered must not accumulate one ticket per poll — that is how an
    away channel trains someone to ignore it."""
    wf = project(tmp_path)
    polled_through(wf, later(700), later(2_500))
    monitor.tick(wf, now=later(2_600))
    # The park itself now makes the loop `waiting`, which is correct: a human owes an answer.
    assert monitor.observe(wf, now=later(2_660))["state"] == "waiting"
    assert len(os.listdir(os.path.join(wf, "parked"))) == 1


# --- the turn gate's give-up breadcrumb ---------------------------------------

def _gave_up(tmp_path, at=1_700_000_000.0, why="there is no reason for this turn to end"):
    (tmp_path / ".workflow" / "turn-gate.json").write_text(json.dumps(
        {"owed": "continue", "owed_at": at, "owed_why": why, "demands": 0, "rung": None}))


def test_a_GIVE_UP_is_nudged_on_the_NEXT_POLL_not_ten_minutes_later(tmp_path):
    """The whole of `4l`. The turn gate knows at the instant of the stop that the turn owed a
    `continue`; the quiet ladder spends `QUIET_SECONDS` rediscovering it. Measured cadence on a
    real drive: work -> stop -> 10 min -> nudge -> work -> stop, four times over."""
    wf = project(tmp_path)
    _gave_up(tmp_path)
    rec = monitor.observe(wf)                      # NOT quiet: the loop wrote a moment ago
    assert rec["state"] == "stopped" and rec["action"] == "nudge"
    assert rec["nudges_total"] == 1


def test_a_breadcrumb_is_served_ONCE(tmp_path):
    """`owed_at` is the identity of one give-up. Re-serving it would type into the session on
    every poll for as long as the latch sat there."""
    wf = project(tmp_path)
    _gave_up(tmp_path)
    monitor.write_record(wf, monitor.observe(wf))
    assert monitor.observe(wf)["action"] == "none"


def test_a_breadcrumb_outranks_a_PARKED_checkpoint(tmp_path):
    """A checkpoint parks the ITEM, not the machine — and the turn ladder has already weighed
    that before it gave up. This file must not overrule the judgement it is acting on."""
    wf = project(tmp_path)
    (tmp_path / ".workflow" / "parked" / "TCK-1.json").write_text("{}")
    _gave_up(tmp_path)
    assert monitor.observe(wf)["action"] == "nudge"


def test_a_breadcrumb_NEVER_outranks_a_dialog_or_the_operators_pause(tmp_path):
    """Both mean a person is in the middle of something. Unconditional, breadcrumb or not."""
    wf = project(tmp_path)
    _gave_up(tmp_path)
    (tmp_path / ".workflow" / "awaiting-input.json").write_text(json.dumps({"kind": "permission"}))
    assert monitor.observe(wf)["action"] == "none"
    (tmp_path / ".workflow" / "awaiting-input.json").unlink()
    (tmp_path / ".workflow" / "control.json").write_text(json.dumps({"paused": True}))
    assert monitor.observe(wf)["action"] == "none"


def test_a_breadcrumb_is_NOT_served_into_a_running_turn(tmp_path):
    """It stopped and something restarted it. Keys sent now land in the prompt box as text."""
    wf = project(tmp_path, idle=False)
    _gave_up(tmp_path)
    rec = monitor.observe(wf)
    assert rec["action"] == "none" and rec["owed_served"] is None


def test_THREE_served_breadcrumbs_that_move_NOTHING_escalate(tmp_path):
    """The shortcut must not become a keystroke loop. The effect is DERIVED — a pulse that
    advances — because `send-keys` exiting 0 says tmux accepted the key, never that the session
    submitted it."""
    wf = project(tmp_path)
    for n in range(4):
        _gave_up(tmp_path, at=1_700_000_000.0 + n)
        rec = monitor.observe(wf)
        monitor.write_record(wf, rec)
    # Three keystrokes went out and moved no pulse; the fourth breadcrumb escalates instead.
    assert rec["state"] == "stalled" and rec["action"] == "escalate", rec
    assert rec["nudges_total"] == 3


def test_a_breadcrumb_that_DID_move_the_loop_keeps_its_budget(tmp_path):
    """A session that stops for nothing but works between stops is exactly the case this rung is
    for — 53 consecutive illegitimate stops on one real drive, every nudge productive."""
    wf = project(tmp_path)
    for n in range(4):
        _gave_up(tmp_path, at=1_700_000_000.0 + n)
        rec = monitor.observe(wf)
        monitor.write_record(wf, rec)
        os.utime(os.path.join(wf, "state.json"), None)      # the nudge produced work
    assert rec["action"] == "nudge" and rec["owed_misses"] == 0


# --- a session a keystroke cannot reach ---------------------------------------

def test_a_MID_TURN_session_is_waiting_and_the_nudge_BUDGET_IS_NOT_SPENT(tmp_path):
    """The `4e` regression, in one assertion. The idle precondition used to live in
    `supervise.sh` as a veto: this file said `nudge`, the shell declined, and the budget was
    spent anyway — so the next rung was a durable `steer` park for a session that had never
    actually been nudged."""
    wf = project(tmp_path, idle=False)
    rec = monitor.observe(wf, now=later(700))
    assert rec["state"] == "waiting" and rec["action"] == "none"
    assert rec["nudges"] == 0 and rec["nudges_total"] == 0


def test_the_WITHHELD_nudge_is_still_there_once_the_session_is_reachable(tmp_path):
    """Withholding must not consume it: the same quiet period gets its nudge the moment the
    session is back at the prompt."""
    wf = project(tmp_path, idle=False)
    monitor.write_record(wf, monitor.observe(wf, now=later(700)))
    (tmp_path / ".workflow" / "session-idle.json").write_text("{}")
    rec = monitor.observe(wf, now=later(800))
    assert rec["action"] == "nudge" and rec["nudges"] == 1


def test_a_MID_TURN_session_quiet_for_the_WHOLE_STALL_WINDOW_still_escalates(tmp_path):
    """The one exception, and without it this file would go silent on the case it exists for. A
    working loop writes constantly, so it never reaches the quiet window at all — quiet for the
    full stall window AND not at the prompt means wedged, or an idle flag that was lost. Neither
    is fixed by typing, and both are things the operator must be told about."""
    rec = polled_through(project(tmp_path, idle=False), later(700), later(2_600))
    assert rec["state"] == "stalled" and rec["action"] == "escalate"


# --- the supervisor's give-up is not just a log line --------------------------

def test_the_SUPERVISORS_GIVE_UP_reaches_a_human(tmp_path):
    """`MAX_RESETS` stopped the send loop and said so into `supervise.log` — nothing parked and
    nothing alerted, so an operator who does not read that file learns about it when the drive
    stops moving. That is the failure mode the away channel exists to abolish."""
    wf = project(tmp_path)
    (tmp_path / ".workflow" / "supervise-latch.json").write_text(json.dumps(
        {"attempts": 3, "used": 190_000, "gave_up": True}))
    rec = monitor.tick(wf)
    assert rec["state"] == "stalled" and rec["action"] == "escalate"
    assert rec["parked"].get("ticket_id") == "steer-G-1-reset-not-landing", rec["parked"]
    # Its own ticket, because its ask is its own: look at the pane, flush the prompt box.
    parked = json.loads((tmp_path / ".workflow" / "parked"
                         / "steer-G-1-reset-not-landing.json").read_text())
    assert "Esc" in parked["checkpoint"]["request"]["what"]


def test_the_GIVE_UP_escalation_does_not_re_alert_every_poll(tmp_path):
    """The park it raises IS a parked checkpoint, so the next poll reports `waiting`. That is
    what the rung's placement below the parked check buys — a `deadline` restamped every 60s is
    an away channel that teaches its reader to ignore it."""
    wf = project(tmp_path)
    (tmp_path / ".workflow" / "supervise-latch.json").write_text(json.dumps({"gave_up": True}))
    monitor.tick(wf)
    rec = monitor.tick(wf)
    assert rec["state"] == "waiting" and rec["action"] == "none"
    assert len(os.listdir(os.path.join(wf, "parked"))) == 1


def test_a_supervisor_that_has_NOT_given_up_escalates_nothing(tmp_path):
    """The negative control: an ordinary attempt ledger is not an alarm."""
    wf = project(tmp_path)
    (tmp_path / ".workflow" / "supervise-latch.json").write_text(json.dumps(
        {"attempts": 1, "used": 190_000, "gave_up": False}))
    assert monitor.observe(wf)["action"] == "none"


# --- a window nobody watched is not evidence ----------------------------------

def test_a_RESTARTED_monitor_does_not_escalate_on_its_OWN_DOWNTIME(tmp_path):
    """It cost a whole night. OBSERVED 2026-09-20: the supervisor was restarted at 13:32:17Z and
    a `steer` was parked SEVENTEEN SECONDS later — *"still nothing written 251m after a nudge"*,
    and those 251 minutes were the window in which the monitor itself was not running. The park
    is durable and `clear_safe` holds on it for ever, so the drive stops until a human deletes a
    ticket that asks no question."""
    wf = project(tmp_path)
    monitor.write_record(wf, monitor.observe(wf, now=later(700)))          # before the deploy
    when = later(15_000)
    rec = monitor.observe(wf, now=when)                                    # restarted, 4h later
    assert rec["action"] != "escalate", rec
    assert rec["watching_since"] == when, "the restart must re-baseline, not judge"
    # And it holds for the whole stall window rather than escalating on the next poll.
    assert polled_through(wf, when + 60, when + 1_700)["action"] != "escalate"


def test_a_RESTARTED_monitor_still_NUDGES_which_is_the_whole_point(tmp_path):
    """The asymmetry is the design. A keystroke is cheap and is exactly what a session idle
    since a deploy needs; withholding it for ten minutes after every restart would cost the
    recovery this file exists for. Only the durable escalation waits for an observed window."""
    wf = project(tmp_path)
    monitor.write_record(wf, dict(monitor.observe(wf, now=later(700)), nudges=1))
    rec = monitor.observe(wf, now=later(15_000))
    assert rec["action"] == "nudge", rec
    assert rec["nudges"] == 1, "the nudge spent in an unobserved era is not evidence either"


def test_an_OBSERVED_stall_still_escalates_after_a_restart(tmp_path):
    """The negative control: re-baselining delays the escalation, it does not remove it."""
    wf = project(tmp_path)
    monitor.write_record(wf, monitor.observe(wf, now=later(700)))
    rec = polled_through(wf, later(15_000), later(17_000))
    assert rec["state"] == "stalled" and rec["action"] == "escalate", rec


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
