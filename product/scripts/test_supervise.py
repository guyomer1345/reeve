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

def _project(tmp_path, runway_nodes=0.5, window=1_000_000, anchor=True):
    """An installed project whose band says hand off now and whose anchor is fresh."""
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
