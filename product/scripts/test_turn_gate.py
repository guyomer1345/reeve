"""Tests for hooks/turn_gate.py — the Stop hook that makes the turn ladder a control.

Runs the hook the way Claude Code does: `python3 turn_gate.py` with the Stop payload on stdin,
against a tmp project laid out as an install lays one out (`.claude/scripts/` beside
`.workflow/`). The layout is part of what is under test — the hook reaches its judgement by
importing out of the installed scripts directory, and a test that imported `turn_check` directly
would prove nothing about the shipped arrangement. `D222` is the reason that sentence is here: a
hook can be on disk, correct, and never invoked.

Three properties carry the rest, and each has its negative control: it is SILENT when a human is
watching, it BLOCKS an unattended stop that has no reason, and it STOPS blocking — when the
reason arrives, and when it has asked twice and been ignored.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent            # product/scripts
HOOK = HERE.parent / "hooks" / "turn_gate.py"
SCRIPTS = ("turn_check.py", "status_report.py", "converge.py", "drive.py", "context_band.py")


def project(tmp_path, status="building", parked=False, git=True):
    wf = tmp_path / ".workflow"
    (wf / "items").mkdir(parents=True, exist_ok=True)
    (wf / "parked").mkdir(parents=True, exist_ok=True)
    scripts = tmp_path / ".claude" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    for name in SCRIPTS:
        shutil.copy(HERE / name, scripts / name)
    (wf / "config.json").write_text(json.dumps({"project_root": "."}))
    (wf / "state.json").write_text(json.dumps({"status": status, "node": "execute"}))
    (wf / "goal.json").write_text(json.dumps(
        {"id": "G-1", "statement": "ship it",
         "acceptance": [{"id": "ga-1", "text": "the thing works"}]}))
    (wf / "goal-ledger.jsonl").write_text("")
    if parked:
        (wf / "parked" / "TCK-1.json").write_text(json.dumps(
            {"ticket_id": "TCK-1", "summary": "approve the keys",
             "checkpoint": {"kind": "setup"}}))
    if git:
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
        (tmp_path / "f").write_text("x")
        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "x"], check=True,
                       env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                                GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t"))
    return tmp_path


def transcript(tmp_path, text):
    """A session transcript in the shape the hook reads: JSONL, assistant messages last."""
    path = tmp_path / "session.jsonl"
    path.write_text(
        json.dumps({"type": "user", "message": {"content": "go"}}) + "\n"
        + json.dumps({"type": "assistant",
                      "message": {"content": [{"type": "text", "text": text}]}}) + "\n")
    return str(path)


def run(cwd, unattended=True, **extra):
    payload = {"hook_event_name": "Stop", "cwd": str(cwd)}
    payload.update(extra)
    env = dict(os.environ)
    env.pop("REEVE_DRIVE", None)
    env.pop("REEVE_SUPERVISE", None)
    if unattended:
        env["REEVE_DRIVE"] = "1"
    return subprocess.run(["python3", str(HOOK)], input=json.dumps(payload),
                          capture_output=True, text=True, env=env)


def blocked(res):
    if res.returncode == 2:
        return True
    try:
        return json.loads(res.stdout or "{}").get("decision") == "block"
    except ValueError:
        return False


# --- scoped to an unattended drive -------------------------------------------

def test_it_says_NOTHING_while_a_human_is_driving(tmp_path):
    """*"this is only when we are letting multiple sessions go by themselves ... not for just
    planning"*. A gate firing mid-conversation is the same nuisance in the other direction, and
    the first thing he would do is switch it off — taking the unattended case with it."""
    res = run(project(tmp_path), unattended=False)
    assert res.returncode == 0 and res.stdout.strip() == ""


def test_config_can_turn_it_on_for_an_operator_who_drives_some_other_way(tmp_path):
    p = project(tmp_path)
    (p / ".workflow" / "config.json").write_text(json.dumps(
        {"project_root": ".", "run": {"drive": {"gate_turns": True}}}))
    assert blocked(run(p, unattended=False))


def test_a_SUBAGENTS_stop_is_not_the_orchestrators(tmp_path):
    """A worker reports to its caller, not to the human, and has no goal to report on."""
    res = run(project(tmp_path), agent_id="agt-1")
    assert res.returncode == 0 and res.stdout.strip() == ""


def test_a_project_that_is_not_INITIALISED_is_none_of_its_business(tmp_path):
    (tmp_path / "x").mkdir()
    assert run(tmp_path).returncode == 0


# --- rung 1 -------------------------------------------------------------------

def test_it_BLOCKS_a_stop_that_has_no_reason(tmp_path):
    res = run(project(tmp_path))
    assert blocked(res)
    assert "no reason for this turn to end" in (res.stdout + res.stderr)


def test_the_block_offers_the_FOUR_ways_out(tmp_path):
    """A gate that only refuses teaches nothing; each way out is a real route the loop has."""
    text = run(project(tmp_path)).stdout
    for route in ("Continue the loop", "decision-engineer", "bus.py park", "Stop properly"):
        assert route in text


def test_a_parked_checkpoint_lets_the_turn_end_once_the_report_is_there(tmp_path):
    p = project(tmp_path, parked=True)
    import status_report as sr
    block = sr.render(sr.build(str(p / ".workflow")))
    res = run(p, transcript_path=transcript(p, "all yours\n" + block))
    assert not blocked(res)


# --- rung 2 -------------------------------------------------------------------

def test_a_legitimate_stop_still_owes_the_REPORT(tmp_path):
    res = run(project(tmp_path, parked=True))
    assert blocked(res) and "status_report.py" in (res.stdout + res.stderr)


def test_an_unchanged_loop_is_not_asked_TWICE(tmp_path):
    """The latch, doing the job that keeps this gate switched on."""
    p = project(tmp_path, parked=True)
    import status_report as sr
    t = transcript(p, sr.render(sr.build(str(p / ".workflow"))))
    assert not blocked(run(p, transcript_path=t))
    assert not blocked(run(p, transcript_path=transcript(p, "nothing to add")))


# --- it never wedges the session it was protecting ---------------------------

def test_it_GIVES_UP_after_two_demands(tmp_path):
    p = project(tmp_path)
    assert blocked(run(p))
    assert blocked(run(p))
    res = run(p)
    assert not blocked(res)
    assert "Letting the turn end" in res.stdout


def test_moving_to_a_DIFFERENT_rung_resets_the_count(tmp_path):
    """Satisfying "continue the loop" should not inherit the report rung's spent patience — they
    are different demands and the session did the first one."""
    p = project(tmp_path)
    run(p), run(p)                                   # two demands on rung `continue`
    (p / ".workflow" / "parked" / "TCK-1.json").write_text(json.dumps(
        {"ticket_id": "TCK-1", "checkpoint": {"kind": "qa"}}))
    res = run(p)
    assert blocked(res) and "status_report.py" in (res.stdout + res.stderr)


def test_the_latch_is_written_even_on_a_BLOCKING_stop(tmp_path):
    """Or the first block poisons the fingerprint comparison for the second, and a session told
    it moved nothing gets told so again for the wrong reason."""
    p = project(tmp_path)
    run(p)
    latch = json.loads((p / ".workflow" / "turn-gate.json").read_text())
    assert latch["fingerprint"] and latch["demands"] == 1 and latch["rung"] == "continue"


# --- fail direction -----------------------------------------------------------

def test_an_unparseable_payload_lets_the_turn_end(tmp_path):
    res = subprocess.run(["python3", str(HOOK)], input="not json",
                         capture_output=True, text=True, env=dict(os.environ, REEVE_DRIVE="1"))
    assert res.returncode == 0


def test_a_MISSING_scripts_directory_lets_the_turn_end(tmp_path):
    """The gate cannot judge without its own judgement module, and guessing is worse than
    allowing — a session wrongly prevented from ending loses everything it was doing."""
    p = project(tmp_path)
    shutil.rmtree(p / ".claude" / "scripts")
    assert not blocked(run(p))


def test_it_DEFERS_while_an_anchor_is_owed(tmp_path):
    """Two hooks blocking one turn with two instructions is how a session obeys neither."""
    import context_band as cb
    p = project(tmp_path)
    import time
    cb.publish(str(p / ".workflow"), 990_000, 1_000_000, time.monotonic())
    assert not blocked(run(p))
