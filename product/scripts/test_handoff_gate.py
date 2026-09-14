"""Tests for hooks/handoff_gate.py — the Stop hook that makes the band a control.

Runs the hook the way Claude Code does: `python3 handoff_gate.py` with the Stop payload on
stdin, against a tmp project laid out as an install lays one out (`.claude/scripts/` beside
`.workflow/`). That layout is part of what is under test — the hook reaches the band by
importing it out of the installed scripts directory, so a test that imported it directly would
prove nothing about the shipped arrangement.

Two properties matter more than the rest and each has its negative control: it BLOCKS when an
anchor is owed (or the band is a banner again), and it STOPS blocking — when the anchor lands,
and when it has asked twice and been ignored (or it wedges the session it was protecting).
"""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import context_band as cb

HERE = Path(__file__).resolve().parent            # product/scripts
HOOK = HERE.parent / "hooks" / "handoff_gate.py"
M = cb.PER_NODE_TOKENS


def _project(tmp_path, runway_nodes=0.5, window=1_000_000, with_scripts=True):
    """A project as installed: the band under .claude/scripts, a reading under .workflow."""
    wf = tmp_path / ".workflow"
    wf.mkdir(parents=True, exist_ok=True)
    if with_scripts:
        scripts = tmp_path / ".claude" / "scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        shutil.copy(HERE / "context_band.py", scripts / "context_band.py")
    if runway_nodes is not None:
        cb.publish(str(wf), window - runway_nodes * M, window, time.monotonic())
    return tmp_path


def _run(cwd, **extra):
    payload = {"hook_event_name": "Stop", "cwd": str(cwd)}
    payload.update(extra)
    return subprocess.run(["python3", str(HOOK)], input=json.dumps(payload),
                          cwd=str(cwd), capture_output=True, text=True)


def _anchor(cwd, text="# handoff\n", bump=0.0):
    path = Path(cwd) / ".workflow" / "handoff.md"
    path.write_text(text)
    if bump:
        os.utime(path, (os.path.getatime(path), os.path.getmtime(path) + bump))


def _blocked(r):
    """Both documented block mechanisms must fire, carrying the same text.

    This hook IS the actuator: a block that the running harness does not honour leaves the band
    exactly where it was, read by nobody. So exit 2 (which blocks a Stop regardless of JSON) and
    the JSON decision are asserted together, not either-or.
    """
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    out = json.loads(r.stdout)
    hs = out.get("hookSpecificOutput") or {}
    assert out.get("decision") == "block"        # the older top-level spelling
    assert hs.get("decision") == "block"         # the documented one
    assert hs.get("hookEventName") == "Stop"
    assert hs["reason"] in r.stderr              # exit 2 routes the instruction through stderr
    return hs["reason"]


def test_it_blocks_the_turn_when_an_anchor_is_owed(tmp_path):
    p = _project(tmp_path)
    reason = _blocked(_run(p))
    assert "handoff.md" in reason
    assert "bus.py mirror" in reason               # the procedure, inline — /dispatch is not callable
    assert "git rev-parse HEAD" in reason
    assert "continue" in reason                    # a cleared session does not start on its own


def test_it_stops_blocking_once_the_anchor_lands(tmp_path):
    """The negative control. Without it the hook is a wedge, not a gate."""
    p = _project(tmp_path)
    _blocked(_run(p))
    _anchor(p, "# fresh\n", bump=10)
    r = _run(p)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_it_is_silent_while_there_is_runway(tmp_path):
    """If this ever blocks, the band's floor half has stopped meaning anything."""
    for nodes in (cb.COMFORTABLE_NODES + 10, (cb.RESERVE_NODES + cb.COMFORTABLE_NODES) / 2.0):
        p = _project(tmp_path / ("r%s" % nodes), runway_nodes=nodes)
        r = _run(p)
        assert r.returncode == 0
        assert r.stdout.strip() == ""


def test_it_gives_up_after_two_demands_rather_than_wedging(tmp_path):
    p = _project(tmp_path)
    _blocked(_run(p))
    _blocked(_run(p))
    r = _run(p)                                    # third: ignored twice, let the turn end
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out.get("decision") != "block"
    assert "not saved" in out["systemMessage"]


def test_a_subagents_stop_is_not_the_orchestrators(tmp_path):
    p = _project(tmp_path)
    r = _run(p, agent_id="ag_1", agent_type="execute")
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_it_fails_OPEN_when_the_band_is_unreachable(tmp_path):
    """A turn that can never end costs more than an unwritten anchor."""
    p = _project(tmp_path, with_scripts=False)
    r = _run(p)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_an_uninitialised_project_is_left_alone(tmp_path):
    p = _project(tmp_path, runway_nodes=None)      # no reading published at all
    r = _run(p)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_garbage_on_stdin_never_wedges(tmp_path):
    """An unparseable payload establishes neither whose stop it is nor which project, and this
    hook blocks turns — so it declines rather than guessing. Note the project here DOES owe an
    anchor: it is the payload that is refused, not the verdict."""
    p = _project(tmp_path)
    r = subprocess.run(["python3", str(HOOK)], input="not json", cwd=str(p),
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert r.stdout.strip() == ""
