"""Tests for supervisor.py — is a supervisor alive here, and may this project be armed.

Two properties carry it, and each is the answer to a failure that actually happened. A
supervisor that is NOT running must never read as running (that is the eleven-hour night: the
supervisors were stopped for a deploy and nothing anywhere said so). And arming must refuse
rather than hand back a half-armed state (that is three supervisors on one pane and none on the
other). Everything else is reported, because the other half of both failures was invisibility.
"""
import json
import os
import subprocess
import time

import supervisor

# A pid high enough to be free on any machine this runs on. `os.kill(pid, 0)` raises
# ProcessLookupError, which is the `gone` path -- the one that matters.
DEAD_PID = 4_000_000


def project(tmp_path, goal=True, parked=(), warn_pct=None):
    wf = tmp_path / ".workflow"
    (wf / "parked").mkdir(parents=True, exist_ok=True)
    if goal:
        (wf / "goal.json").write_text(json.dumps({"id": "G-1", "statement": "ship it"}))
    for t in parked:
        (wf / "parked" / (t + ".json")).write_text(json.dumps({"ticket_id": t}))
    cfg = {"project_root": "."}
    if warn_pct is not None:
        cfg["context"] = {"warn_pct": warn_pct}
    (wf / "config.json").write_text(json.dumps(cfg))
    return str(wf)


def a_real_supervisor(tmp_path):
    """A live process whose command line really says `supervise.sh`.

    Not a stand-in for convenience: pid reuse is why the liveness check reads `/proc` at all, so
    a test that only proved "some pid exists" would pass against the bug.
    """
    script = tmp_path / "supervise.sh"
    script.write_text("#!/usr/bin/env bash\nsleep 60\n")
    return subprocess.Popen(["bash", str(script)])


# --- is a supervisor alive here ----------------------------------------------

def test_no_record_is_NONE_not_gone(tmp_path):
    """Two different answers on purpose: nothing was ever armed here, versus something was
    armed and is not there any more. Only the second is an alarm."""
    wf = project(tmp_path)
    assert supervisor.alive(wf)["state"] == "none"


def test_a_LIVE_supervisor_reads_as_running(tmp_path):
    wf = project(tmp_path)
    proc = a_real_supervisor(tmp_path)
    try:
        supervisor.publish(wf, proc.pid, "reeve:0.0")
        rec = supervisor.alive(wf)
        assert rec["state"] == "running" and rec["pid"] == proc.pid and rec["pane"] == "reeve:0.0"
    finally:
        proc.kill(), proc.wait()


def test_a_DEAD_supervisor_reads_as_gone(tmp_path):
    """The eleven-hour failure, in one assertion."""
    wf = project(tmp_path)
    supervisor.publish(wf, DEAD_PID, "reeve:0.0")
    rec = supervisor.alive(wf)
    assert rec["state"] == "gone" and "stopped" in rec["why"]


def test_a_process_that_is_NOT_a_supervisor_is_never_running(tmp_path):
    """Pid reuse: the shell that dies at 02:00 can be a compiler at 02:05. Existence alone is
    not the question."""
    wf = project(tmp_path)
    proc = subprocess.Popen(["sleep", "60"])
    try:
        supervisor.publish(wf, proc.pid, "reeve:0.0")
        assert supervisor.alive(wf)["state"] != "running"
    finally:
        proc.kill(), proc.wait()


def test_a_TORN_record_is_unknown_rather_than_running(tmp_path):
    """Fail direction: a false `running` is an operator who stops checking."""
    wf = project(tmp_path)
    (tmp_path / ".workflow" / "supervisor.json").write_text('{"pane": "x"}')
    assert supervisor.alive(wf)["state"] == "unknown"


def test_retire_removes_the_record(tmp_path):
    """A record left by a supervisor that exited cleanly would read as `gone` — an alarm rather
    than a fact."""
    wf = project(tmp_path)
    supervisor.publish(wf, DEAD_PID, "reeve:0.0")
    supervisor.retire(wf)
    assert supervisor.alive(wf)["state"] == "none"


# --- may this project be armed -----------------------------------------------

def test_an_UNSTARTED_project_refuses(tmp_path):
    res = supervisor.preflight(str(tmp_path))
    assert not res["ready"] and "has not been started" in res["fatal"][0]


def test_a_supervisor_ALREADY_RUNNING_refuses(tmp_path):
    """Measured: three supervisors ended up on one pane, each sending `/clear` on its own
    schedule. This is the one state where arming does not achieve what was asked for."""
    wf = project(tmp_path)
    proc = a_real_supervisor(tmp_path)
    try:
        supervisor.publish(wf, proc.pid, "reeve:0.0")
        res = supervisor.preflight(str(tmp_path))
        assert not res["ready"] and "ALREADY running" in res["fatal"][0]
        assert str(proc.pid) in res["fatal"][0]
    finally:
        proc.kill(), proc.wait()


def test_a_DEAD_supervisors_record_is_a_warning_not_a_refusal(tmp_path):
    """Replacing it is exactly what this command is for."""
    wf = project(tmp_path)
    supervisor.publish(wf, DEAD_PID, "reeve:0.0")
    res = supervisor.preflight(str(tmp_path))
    assert res["ready"] and any("is gone" in w for w in res["warn"])


def test_a_PARKED_ticket_is_reported_and_does_not_refuse(tmp_path):
    """The failure was a false park nobody could see without reading JSON — invisibility, not
    the park. And `4h` settled that a park is not a reason to stop the machine."""
    project(tmp_path, parked=("gap-027-qa",))
    res = supervisor.preflight(str(tmp_path))
    assert res["ready"]
    assert any("gap-027-qa" in w for w in res["warn"])
    assert res["armed"]["parked"] == ["gap-027-qa"]


def test_NO_GOAL_is_reported_and_does_not_refuse(tmp_path):
    """Refusing would make the first supervised run of a greenfield project impossible —
    inception is what mints the goal, and it has not run yet."""
    project(tmp_path, goal=False)
    res = supervisor.preflight(str(tmp_path))
    assert res["ready"] and any("NO GOAL" in w for w in res["warn"])


def test_a_clean_project_arms_and_SAYS_WHAT_IT_ARMED(tmp_path):
    """*"...and it SAYS what it armed."* The report is the deliverable, not a side effect."""
    project(tmp_path, warn_pct=30)
    res = supervisor.preflight(str(tmp_path), pane="reeve:0.0")
    assert res["ready"] and res["armed"]["goal"] == "G-1" and res["armed"]["warn_pct"] == 30
    text = supervisor.render(res)
    assert "ARMED:" in text and "reeve:0.0" in text and "G-1" in text and "30%" in text


def test_the_REFUSAL_renders_as_a_refusal(tmp_path):
    text = supervisor.render(supervisor.preflight(str(tmp_path)))
    assert text.startswith("REFUSING:") and "Nothing was armed" in text


def test_the_cli_exit_code_is_the_verdict(tmp_path):
    """`loop.sh` branches on it, so it is a contract rather than a convenience."""
    project(tmp_path)
    here = os.path.dirname(os.path.abspath(supervisor.__file__))
    ok = subprocess.run(["python3", os.path.join(here, "supervisor.py"), "preflight",
                         "--project", str(tmp_path)], capture_output=True, text=True)
    assert ok.returncode == 0 and "ARMED:" in ok.stdout
    bad = subprocess.run(["python3", os.path.join(here, "supervisor.py"), "preflight",
                          "--project", str(tmp_path / "nowhere")], capture_output=True, text=True)
    assert bad.returncode == 1


def test_publish_stamps_a_start_time(tmp_path):
    wf = project(tmp_path)
    before = time.time()
    supervisor.publish(wf, DEAD_PID, "reeve:0.0")
    assert supervisor.alive(wf)["since"] >= before
