"""Tests for the durable pause latch — the state `pause` never had.

Before this, `bus.py` validated a `control` op, the drain delivered it, and the orchestrator
was trusted to honour it in context. The comment beside CONTROL_OPS said "pause and resume each
re-set a flag" and there was no flag: `grep -rn paused` over the package found nothing. So a
pause survived exactly as long as the session that read it, which is the precise moment an
unattended driver decides whether to start another one.

These tests pin the property that fix exists for: **the pause outlives the session.** Every one
of them writes the latch through the real drain and reads it back through a different process's
view of the world.
"""
import json
import os
import subprocess
import sys

import pytest

import bus
import drain


@pytest.fixture
def env(tmp_path):
    wf = tmp_path / ".workflow"
    (wf / "inbox").mkdir(parents=True)
    (wf / "handoff.md").write_text("# Handoff — resume anchor\n\nprose\n", encoding="utf-8")
    return wf


def _msg(wf, mid, body):
    (wf / "inbox" / (mid + ".json")).write_text(json.dumps(body), encoding="utf-8")
    return mid


def _record(wf, *mids):
    return subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(drain.__file__), "drain.py"),
         "--workflow-dir", str(wf), "record"] + ["--applied"] + list(mids),
        capture_output=True, text=True)


def _ids(n=1):
    """Bus-shaped message ids, which `record` validates."""
    base = "20260913T120000000000Z"
    return ["%s-%04d" % (base[:-1], i) for i in range(n)]


def _id(seq):
    """A bus-shaped message id. Ids sort by time, and `_apply_control` relies on that ordering,
    so the seconds field is what varies -- a later `seq` is a later message."""
    mid = "20260913T1200%02d.000000Z-deadbeef-1" % seq
    assert bus.MESSAGE_ID_RE.fullmatch(mid), mid
    return mid


def _control(wf, seq, op):
    return _msg(wf, _id(seq), {"kind": "control", "op": op})


def test_recording_a_pause_sets_the_latch_and_it_survives_the_process(env):
    mid = _control(env, 0, "pause")
    p = _record(env, mid)
    assert p.returncode == 0, p.stderr
    # Read back through a NEW Paths in a NEW process's view -- nothing in memory carries this.
    state = drain.read_control(bus.Paths(str(env)))
    assert state["paused"] is True
    assert state["by"] == mid


def test_resume_clears_the_latch(env):
    _record(env, _control(env, 0, "pause"))
    assert drain.read_control(bus.Paths(str(env)))["paused"] is True
    _record(env, _control(env, 1, "resume"))
    assert drain.read_control(bus.Paths(str(env)))["paused"] is False


def test_re_recording_the_same_pause_is_a_no_op(env):
    """A redelivered control message must be safe — the whole reason CONTROL_OPS is closed."""
    mid = _control(env, 0, "pause")
    _record(env, mid)
    first = drain.read_control(bus.Paths(str(env)))
    _record(env, mid)
    assert drain.read_control(bus.Paths(str(env)))["paused"] == first["paused"]


def test_the_last_control_in_one_batch_wins_by_message_order(env):
    """A pause and a resume drained together must land in the order they were SENT, not in
    whatever order the caller listed them."""
    pause_id = _control(env, 0, "pause")
    resume_id = _control(env, 1, "resume")
    _record(env, resume_id, pause_id)          # deliberately reversed on the command line
    assert drain.read_control(bus.Paths(str(env)))["paused"] is False


def test_a_reprioritize_does_not_touch_the_latch(env):
    """`reprioritize` is judgment and stays the orchestrator's; only pause/resume are a flag."""
    _record(env, _control(env, 0, "pause"))
    _record(env, _control(env, 1, "reprioritize"))
    assert drain.read_control(bus.Paths(str(env)))["paused"] is True


def test_a_non_control_message_does_not_touch_the_latch(env):
    _record(env, _control(env, 0, "pause"))
    q = _msg(env, _id(1), {"kind": "question", "question": "where are we?"})
    _record(env, q)
    assert drain.read_control(bus.Paths(str(env)))["paused"] is True


def test_an_absent_latch_reads_as_not_paused(env):
    assert drain.read_control(bus.Paths(str(env))).get("paused") is not True


def test_an_unparseable_latch_reads_as_not_paused(env):
    paths = bus.Paths(str(env))
    os.makedirs(os.path.dirname(paths.control), exist_ok=True)
    with open(paths.control, "w", encoding="utf-8") as fh:
        fh.write("{ truncated")
    assert drain.read_control(paths).get("paused") is not True


def test_drain_paused_exit_code_is_the_gate(env):
    d = os.path.join(os.path.dirname(drain.__file__), "drain.py")
    no = subprocess.run([sys.executable, d, "--workflow-dir", str(env), "paused"],
                        capture_output=True, text=True)
    assert no.returncode == 1
    _record(env, _control(env, 0, "pause"))
    yes = subprocess.run([sys.executable, d, "--workflow-dir", str(env), "paused"],
                         capture_output=True, text=True)
    assert yes.returncode == 0
