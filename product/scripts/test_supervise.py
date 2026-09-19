"""Tests for scripts/supervise.sh — the poller that resets a full interactive session.

The two properties that matter are opposite failures, and both get a test. A supervisor that
never fires leaves the drive stopping at the first full window — the thing it exists to stop. A
supervisor that fires wrongly destroys a conversation somebody was having, which is strictly
worse, so every `holding` case is asserted explicitly rather than assumed from the gate's tests.

The reset itself is driven through a REAL tmux pane against a stand-in that records what it
receives, because the whole mechanism is keystroke injection: a test that called a bash function
and checked a variable would prove nothing about the part that can actually be wrong.
"""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

import context_band as cb

HERE = Path(__file__).resolve().parent              # product/scripts
SUP = HERE / "supervise.sh"
M = cb.PER_NODE_TOKENS

pytestmark = pytest.mark.skipif(shutil.which("tmux") is None, reason="tmux is the transport")



# A REAL anchor: fresh mtime is only half of "written" — `context_band` also requires the
# anchor to name a base commit, because a resume reads `git log <base_sha>..HEAD` and one
# without it cannot say what moved (`D219` #3). A bare "# handoff" is the exact shape a
# real drive produced and nothing caught.
ANCHOR = "# handoff\n\nbase_sha: 1a2b3c4\n"

def _project(tmp_path, runway_nodes=0.5, window=1_000_000, anchor=True, idle=True):
    """An installed project whose band says hand off now, whose anchor is fresh, and whose
    session is sitting idle — the fourth condition, and the one every fixture here used to be
    silently missing. A drive found that `handoff.md` is written DURING a turn, so the other
    three are all true while the model is still working; a fixture without `idle` describes the
    state the supervisor must NOT act on."""
    p = tmp_path
    wf = p / ".workflow"
    wf.mkdir(parents=True, exist_ok=True)
    scripts = p / ".claude" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    for name in ("context_band.py", "bus.py"):
        shutil.copy(HERE / name, scripts / name)
    cb.publish(str(wf), window - runway_nodes * M, window, time.monotonic())
    (wf / "handoff.md").write_text(ANCHOR)
    cb.demand(str(wf))                               # arms the latch at this mtime
    if anchor:
        path = wf / "handoff.md"
        path.write_text("# fresh\n" + ANCHOR)
        os.utime(path, (os.path.getatime(path), os.path.getmtime(path) + 10))
    if idle:
        (wf / "session-idle.json").write_text(json.dumps({"kind": "idle_prompt"}))
    return p


def _once(project, pane):
    return subprocess.run(
        ["bash", str(SUP), "--pane", pane, "--project", str(project), "--once"],
        capture_output=True, text=True)


# --- the holding cases: every one of these must leave the session alone -----------------

def test_it_holds_when_no_anchor_has_been_written(tmp_path):
    p = _project(tmp_path, anchor=False)
    r = _once(p, "nosuchpane")
    assert r.returncode == 1
    assert "no handoff has been written" in r.stderr


def test_it_holds_while_there_is_runway(tmp_path):
    p = _project(tmp_path, runway_nodes=cb.COMFORTABLE_NODES + 10)
    r = _once(p, "nosuchpane")
    assert r.returncode == 1
    assert "not handoff-now" in r.stderr


def test_it_holds_while_a_checkpoint_awaits_a_human(tmp_path):
    p = _project(tmp_path)
    parked = p / ".workflow" / "parked"
    parked.mkdir()
    (parked / "TCK-1.json").write_text(json.dumps({"ticket_id": "TCK-1"}))
    r = _once(p, "nosuchpane")
    assert r.returncode == 1
    assert "await a human verdict" in r.stderr


def test_it_holds_while_a_DIALOG_is_open(tmp_path):
    """The condition a live probe found: a permission prompt is waiting on a human just as much
    as a parked checkpoint, and it is invisible to `parked/`."""
    p = _project(tmp_path)
    (p / ".workflow" / "awaiting-input.json").write_text(json.dumps({"kind": "permission_prompt"}))
    r = _once(p, "nosuchpane")
    assert r.returncode == 1
    assert "permission_prompt dialog is open" in r.stderr


def test_it_holds_while_the_session_is_MID_TURN(tmp_path):
    """The condition a real drive found, and the one the other three were wrong about.

    `handoff.md` is written during a turn, so at the instant the anchor lands the band says
    handoff-now, the anchor is fresh, nothing is parked and no dialog is open — every signal the
    gate had said GO while the model was still talking. Keys sent then are not queued into the
    turn; they land in the prompt box as text and are never submitted."""
    p = _project(tmp_path, idle=False)
    r = _once(p, "nosuchpane")
    assert r.returncode == 1
    assert "not known to be idle" in r.stderr


def test_a_SUBMITTED_prompt_retires_the_idle_flag_and_the_gate_closes(tmp_path):
    """The bracket, from the gate's side: `prompt_submit.py` removes the flag the instant a turn
    starts, which is what stops the supervisor sending a second pair into its own first one."""
    p = _project(tmp_path)
    assert "not known to be idle" not in _once(p, "nosuchpane").stderr
    (p / ".workflow" / "session-idle.json").unlink()
    assert "not known to be idle" in _once(p, "nosuchpane").stderr


def test_a_missing_pane_is_never_a_reason_to_send_anywhere_else(tmp_path):
    p = _project(tmp_path)
    r = _once(p, "definitely-not-a-session:9.9")
    assert r.returncode == 1
    assert "is gone" in r.stderr


def test_an_uninitialised_project_refuses_rather_than_guessing(tmp_path):
    r = _once(tmp_path, "nosuchpane")
    assert r.returncode == 66
    assert "initialised project" in r.stderr


def test_the_pane_is_required_because_guessing_clears_the_wrong_window(tmp_path):
    r = subprocess.run(["bash", str(SUP), "--project", str(tmp_path), "--once"],
                       capture_output=True, text=True)
    assert r.returncode == 64
    assert "--pane is required" in r.stderr


# --- the firing case, driven through a real pane ----------------------------------------

def test_it_sends_clear_THEN_continue_into_a_real_pane(tmp_path):
    """End to end over the actual transport. Two sends, not one: a cleared session does not
    start on its own — SessionStart injects the anchor as context, and context is not a turn."""
    p = _project(tmp_path)
    sink = tmp_path / "sink.txt"
    reader = tmp_path / "reader.sh"
    reader.write_text('while IFS= read -r line; do echo "$line" >> "%s"; done\n' % sink)
    session = "reeve-test-%d" % os.getpid()
    subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)
    subprocess.run(["tmux", "new-session", "-d", "-s", session,
                    "bash %s" % reader], check=True, capture_output=True)
    try:
        r = subprocess.run(
            ["bash", str(SUP), "--pane", session, "--project", str(p), "--once"],
            capture_output=True, text=True,
            env={**os.environ, "REEVE_SUPERVISE_SETTLE": "1"})
        assert r.returncode == 0, r.stderr
        deadline = time.time() + 20
        got = ""
        while time.time() < deadline:
            got = sink.read_text() if sink.exists() else ""
            if "continue" in got:
                break
            time.sleep(0.5)
        lines = [l for l in got.splitlines() if l.strip()]
        assert lines == ["/clear", "continue"], (lines, r.stderr)
    finally:
        subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)


# --- the attempt cap: the one thing the gate cannot see ----------------------------------
# `send-keys` exiting 0 means tmux took the keystroke, never that the TUI submitted it. So a
# send that does not land changes nothing the gate reads, the gate stays true, and the next poll
# sends again — which is how a real drive ended up with `/clear continue /clear continue` stacked
# in a prompt box. The ledger is checked against a DERIVED effect: a `/clear` that lands
# collapses the context reading.

def _latch(project, attempts, used):
    (project / ".workflow" / "supervise-latch.json").write_text(
        json.dumps({"attempts": attempts, "used": used}))


def _used(runway_nodes=0.5, window=1_000_000):
    return int(window - runway_nodes * M)


def test_it_GIVES_UP_after_three_sends_that_moved_nothing(tmp_path):
    p = _project(tmp_path)
    _latch(p, 3, _used())                     # three sends, reading unchanged since the first
    r = _once(p, "nosuchpane")
    assert r.returncode == 1
    assert "GIVING UP" in r.stderr
    # And it must say what a human can actually do about it, not merely that it stopped.
    assert "Esc" in r.stderr and "supervise-latch.json" in r.stderr


def test_a_reading_that_COLLAPSED_retires_the_ledger_rather_than_capping(tmp_path):
    """Three successful resets in a row must not trip a cap built for three failed ones. The
    ledger is retired on the reading, not on this file's own report of success — and it is
    retired on EVERY tick, because a landed reset leaves the gate false for a long while."""
    p = _project(tmp_path)
    _latch(p, 3, _used() + 5 * cb.PER_NODE_TOKENS)   # the window was far fuller when we sent
    r = _once(p, "nosuchpane")
    assert "GIVING UP" not in r.stderr
    assert "is gone" in r.stderr                      # it went on to try the (absent) pane
    assert not (p / ".workflow" / "supervise-latch.json").exists()


def test_an_unreadable_ledger_costs_one_send_and_never_disables_the_supervisor(tmp_path):
    p = _project(tmp_path)
    (p / ".workflow" / "supervise-latch.json").write_text("{not json at all")
    r = _once(p, "nosuchpane")
    assert "GIVING UP" not in r.stderr and "is gone" in r.stderr


# --- the heartbeat: the session a `Stop` hook cannot see ---------------------------------
# The turn gate catches every stop-for-nothing at the instant it happens. A session that never
# ends a turn — idling, or sat in a dialog — never reaches it, and the supervisor is the only
# process still watching. These pin the transport half; `test_monitor.py` owns the judgement.

def _heartbeat_project(tmp_path, quiet_seconds=None):
    """The reset gate must HOLD (there is runway), because that is when the heartbeat runs —
    a dead session and a healthy one look identical from the reset gate's side."""
    p = _project(tmp_path, runway_nodes=cb.COMFORTABLE_NODES + 10)
    shutil.copy(HERE / "monitor.py", p / ".claude" / "scripts" / "monitor.py")
    shutil.copy(HERE / "drive.py", p / ".claude" / "scripts" / "drive.py")
    shutil.copy(HERE / "converge.py", p / ".claude" / "scripts" / "converge.py")
    if quiet_seconds:
        wf = p / ".workflow"
        old = time.time() - quiet_seconds
        for path in list(wf.rglob("*")) + [wf]:
            os.utime(path, (old, old))
    return p


def test_a_QUIET_drive_is_nudged_through_the_real_transport(tmp_path):
    p = _heartbeat_project(tmp_path, quiet_seconds=1200)
    sink = tmp_path / "sink.txt"
    reader = tmp_path / "reader.sh"
    reader.write_text('while IFS= read -r line; do echo "$line" >> "%s"; done\n' % sink)
    session = "reeve-hb-%d" % os.getpid()
    subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)
    subprocess.run(["tmux", "new-session", "-d", "-s", session, "bash %s" % reader],
                   check=True, capture_output=True)
    try:
        r = subprocess.run(["bash", str(SUP), "--pane", session, "--project", str(p), "--once"],
                           capture_output=True, text=True)
        assert r.returncode == 1, "the RESET must still hold — this is a nudge, not a clear"
        assert "nudging" in r.stderr, r.stderr
        deadline = time.time() + 20
        got = ""
        while time.time() < deadline and "continue" not in got:
            got = sink.read_text() if sink.exists() else ""
            time.sleep(0.5)
        assert [l for l in got.splitlines() if l.strip()] == ["continue"], got
    finally:
        subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)


def test_a_QUIET_drive_that_is_MID_TURN_is_not_nudged_either(tmp_path):
    """The nudge is the same keystroke injection the reset is, so it carries the same
    precondition. A session that never ends a turn because it is WORKING is not one a `continue`
    would help, and typing into it corrupts the prompt box exactly as a mistimed reset does."""
    p = _heartbeat_project(tmp_path, quiet_seconds=1200)
    (p / ".workflow" / "session-idle.json").unlink()
    r = _once(p, "nosuchpane")
    assert "NOT nudging" in r.stderr
    assert "nudging %s" % "nosuchpane" not in r.stderr


def test_a_MOVING_drive_is_left_alone(tmp_path):
    """The failure that would matter most: keystrokes into a session that was working."""
    p = _heartbeat_project(tmp_path)
    r = _once(p, "nosuchpane")
    assert "nudging" not in r.stderr and "STALLED" not in r.stderr


def test_a_PAUSED_loop_is_never_nudged(tmp_path):
    """`paused` returns before the heartbeat runs at all — a paused loop is stopped on purpose."""
    p = _heartbeat_project(tmp_path, quiet_seconds=1200)
    (p / ".workflow" / "control.json").write_text(json.dumps({"paused": True}))
    shutil.copy(HERE / "drain.py", p / ".claude" / "scripts" / "drain.py")
    r = _once(p, "nosuchpane")
    assert "nudging" not in r.stderr


def test_a_project_without_the_monitor_INSTALLED_still_supervises(tmp_path):
    """The heartbeat is additive: an older tree that predates it must not break the reset."""
    p = _heartbeat_project(tmp_path, quiet_seconds=1200)
    (p / ".claude" / "scripts" / "monitor.py").unlink()
    r = _once(p, "nosuchpane")
    assert r.returncode == 1 and "holding" in r.stderr
