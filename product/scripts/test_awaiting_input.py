"""Tests for hooks/awaiting_input.py — "a dialog is open", the third gate on a reset.

The exclusion is the load-bearing half and gets its own test: `idle_prompt` must NOT set the
flag. It means the session is sitting idle waiting for a prompt, which is precisely the state a
supervisor exists to act on — treating it as "a human is busy here" would disable the supervisor
exactly when it should fire, and nothing else in the system would say why.
"""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import context_band as cb

HERE = Path(__file__).resolve().parent
HOOK = HERE.parent / "hooks" / "awaiting_input.py"
STOP_HOOK = HERE.parent / "hooks" / "handoff_gate.py"
M = cb.PER_NODE_TOKENS


def _project(tmp_path):
    (tmp_path / ".workflow").mkdir(parents=True, exist_ok=True)
    scripts = tmp_path / ".claude" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / "context_band.py", scripts / "context_band.py")
    return tmp_path


def _notify(cwd, kind, **extra):
    payload = {"hook_event_name": "Notification", "cwd": str(cwd), "notification_type": kind}
    payload.update(extra)
    return subprocess.run(["python3", str(HOOK)], input=json.dumps(payload),
                          cwd=str(cwd), capture_output=True, text=True)


def _flag(cwd):
    path = Path(cwd) / ".workflow" / "awaiting-input.json"
    return json.loads(path.read_text()) if path.exists() else None


def test_a_permission_prompt_raises_the_flag(tmp_path):
    p = _project(tmp_path)
    assert _notify(p, "permission_prompt").returncode == 0
    assert _flag(p)["kind"] == "permission_prompt"


def test_every_dialog_kind_counts(tmp_path):
    for kind in ("permission_prompt", "elicitation_dialog", "elicitation_url_dialog",
                 "agent_needs_input"):
        p = _project(tmp_path / kind)
        _notify(p, kind)
        assert _flag(p) is not None, kind


def test_IDLE_PROMPT_MUST_NOT_raise_it(tmp_path):
    """The exclusion, as an assertion. An idle session is the supervisor's trigger, not a
    reason to hold — this is the one entry whose presence would silently disable the feature."""
    p = _project(tmp_path)
    _notify(p, "idle_prompt")
    assert _flag(p) is None


def test_other_notifications_are_ignored(tmp_path):
    p = _project(tmp_path)
    for kind in ("auth_success", "agent_completed", "quota_auto_resume_fired", ""):
        _notify(p, kind)
    assert _flag(p) is None


def test_a_subagents_dialog_is_not_this_sessions_screen(tmp_path):
    p = _project(tmp_path)
    _notify(p, "permission_prompt", agent_id="ag_1")
    assert _flag(p) is None


def test_an_uninitialised_project_is_left_alone(tmp_path):
    r = _notify(tmp_path, "permission_prompt")
    assert r.returncode == 0
    assert not (tmp_path / ".workflow").exists()


def test_garbage_on_stdin_never_raises_a_flag_nobody_can_clear(tmp_path):
    p = _project(tmp_path)
    r = subprocess.run(["python3", str(HOOK)], input="not json", cwd=str(p),
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert _flag(p) is None


# --- the lifecycle: what raises it must be clearable, or the supervisor is wedged --------

def test_the_stop_hook_clears_it(tmp_path):
    """A turn that has ended cannot be sitting in a dialog — whether it was approved, denied or
    cancelled. That is the whole lifecycle, and it is why there is no TTL."""
    p = _project(tmp_path)
    cb.publish(str(p / ".workflow"), 1_000_000 - 20 * M, 1_000_000, time.monotonic())
    _notify(p, "permission_prompt")
    assert _flag(p) is not None
    r = subprocess.run(["python3", str(STOP_HOOK)],
                       input=json.dumps({"hook_event_name": "Stop", "cwd": str(p)}),
                       cwd=str(p), capture_output=True, text=True)
    assert r.returncode == 0
    assert _flag(p) is None


def test_an_open_dialog_blocks_clear_safe(tmp_path):
    p = _project(tmp_path)
    wf = str(p / ".workflow")
    cb.publish(wf, 1_000_000 - 0.5 * M, 1_000_000, time.monotonic())
    (p / ".workflow" / "handoff.md").write_text("# h\n\nbase_sha: 1a2b3c4\n")
    cb.demand(wf)
    path = p / ".workflow" / "handoff.md"
    # A REAL anchor — `context_band` requires one to name a base commit, not merely to have
    # moved (`D219` #3). The control below is "nothing blocks clear_safe", so a half-anchor
    # here would be testing the wrong blocker.
    path.write_text("# fresh\n\nbase_sha: 9f8e7d6\n")
    os.utime(path, (os.path.getatime(path), os.path.getmtime(path) + 10))
    assert cb.gate(wf)["clear_safe"] is True            # the control

    _notify(p, "permission_prompt")
    g = cb.gate(wf)
    assert g["clear_safe"] is False
    assert g["awaiting_input"]["kind"] == "permission_prompt"


def test_an_unparseable_flag_still_counts_as_open(tmp_path):
    """Safe direction: a file nobody can read is not evidence that nobody is waiting."""
    p = _project(tmp_path)
    (p / ".workflow" / "awaiting-input.json").write_text("{ torn")
    assert cb.awaiting_input(str(p / ".workflow"))["kind"] == "unknown"
