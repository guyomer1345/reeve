"""Tests for hooks/worker_budget.py — the hook that lets a worker YIELD before its window ends.

This is the actuator half of the dispatch-return contract, and the one that was written off as
impossible on the reasoning that a subagent cannot spawn its own successor. It does not need to:
it needs to stop cleanly and say so, and the orchestrator does the rest.

What matters here is mostly what it does NOT do. It runs after every tool call of every worker in
the drive, so the failure that would actually hurt is noise — firing on the orchestrator, firing
twice, firing on a transcript it only guessed at, or firing on a shape it does not understand.
"""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(os.path.dirname(HERE), "hooks", "worker_budget.py")

WINDOW = 200_000


def _line(total, role="assistant"):
    """One assistant line of a subagent transcript, with usage split across the three terms the
    hook must add together — leaving the cache terms out would report a fraction of the truth."""
    cache_read = int(total * 0.8)
    cache_creation = int(total * 0.15)
    inp = total - cache_read - cache_creation
    return json.dumps({
        "type": role,
        "message": {"usage": {"cache_read_input_tokens": cache_read,
                              "cache_creation_input_tokens": cache_creation,
                              "input_tokens": inp}},
    })


def _transcript(tmp_path, totals, aid="agt-1"):
    d = tmp_path / "subagents"
    d.mkdir(parents=True, exist_ok=True)
    path = d / ("agent-%s.jsonl" % aid)
    path.write_text("\n".join(_line(t) for t in totals) + "\n")
    return str(path)


def _run(payload, env=None):
    e = dict(os.environ)
    e.pop("REEVE_WORKER_YIELD_PCT", None)
    e.update(env or {})
    return subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                          capture_output=True, text=True, env=e)


def _fired(r):
    return "WORKER BUDGET" in (r.stderr or "")


# --- it fires when the worker really is near the end -------------------------

def test_a_worker_past_the_threshold_is_told_to_YIELD(tmp_path):
    path = _transcript(tmp_path, [50_000, 160_000])       # 80% of 200k
    r = _run({"agent_id": "agt-1", "transcript_path": path})
    assert _fired(r)
    assert "status: continue" in r.stderr
    assert "scratch/" in r.stderr
    assert "NOT a failure" in r.stderr, "a yield reported as a failure gets re-planned"


def test_the_LAST_line_is_what_counts(tmp_path):
    """The file is appended during the run, so the tail is the present. An early large line
    followed by smaller ones would be a transcript that shrank, which does not happen — but
    reading anything other than the tail would report the past as the present."""
    path = _transcript(tmp_path, [190_000, 10_000])
    assert not _fired(_run({"agent_id": "agt-1", "transcript_path": path}))


def test_all_three_usage_terms_are_counted(tmp_path):
    """`cache_read` is the majority of occupancy. Counting only `input_tokens` would put a
    worker at 5% of its window when it is at 80%."""
    d = tmp_path / "subagents"
    d.mkdir(parents=True)
    path = d / "agent-agt-1.jsonl"
    path.write_text(json.dumps({
        "type": "assistant",
        "message": {"usage": {"cache_read_input_tokens": 150_000,
                              "cache_creation_input_tokens": 9_000,
                              "input_tokens": 1_000}}}) + "\n")
    assert _fired(_run({"agent_id": "agt-1", "transcript_path": str(path)}))


def test_the_threshold_is_operator_settable(tmp_path):
    path = _transcript(tmp_path, [100_000])               # 50%
    assert not _fired(_run({"agent_id": "agt-1", "transcript_path": path}))
    assert _fired(_run({"agent_id": "agt-1", "transcript_path": path},
                       env={"REEVE_WORKER_YIELD_PCT": "40"}))


def test_a_nonsense_threshold_falls_back_to_the_default(tmp_path):
    path = _transcript(tmp_path, [100_000])
    for bad in ("0", "100", "-5", "abc", ""):
        assert not _fired(_run({"agent_id": "agt-1", "transcript_path": path},
                               env={"REEVE_WORKER_YIELD_PCT": bad})), bad


# --- once, not every turn ----------------------------------------------------

def test_it_fires_ONCE_per_worker(tmp_path):
    """Past the threshold a worker stays past it. Repeating on every remaining tool call is both
    noise and a growing share of the window this is trying to protect."""
    path = _transcript(tmp_path, [170_000])
    payload = {"agent_id": "agt-1", "transcript_path": path}
    assert _fired(_run(payload))
    assert not _fired(_run(payload))
    assert not _fired(_run(payload))


def test_a_DIFFERENT_worker_gets_its_own_telling(tmp_path):
    a = _transcript(tmp_path, [170_000], aid="agt-1")
    b = _transcript(tmp_path, [170_000], aid="agt-2")
    assert _fired(_run({"agent_id": "agt-1", "transcript_path": a}))
    assert _fired(_run({"agent_id": "agt-2", "transcript_path": b}))


# --- silence, in every direction that is not positively known ----------------

def test_the_ORCHESTRATOR_is_never_told_to_yield(tmp_path):
    """The router has its own governor and a different remedy — write a handoff, clear. Telling
    it to `return status: continue` would be advice it cannot take."""
    path = _transcript(tmp_path, [190_000])
    assert not _fired(_run({"transcript_path": path}))


def test_a_transcript_it_cannot_POSITIVELY_locate_is_silence(tmp_path):
    assert not _fired(_run({"agent_id": "agt-1", "transcript_path": str(tmp_path / "nope.jsonl")}))
    assert not _fired(_run({"agent_id": "agt-1"}))


def test_an_unfamiliar_usage_shape_is_silence(tmp_path):
    d = tmp_path / "subagents"
    d.mkdir(parents=True)
    path = d / "agent-agt-1.jsonl"
    path.write_text(json.dumps({"type": "assistant", "message": {"tokens": 190_000}}) + "\n")
    assert not _fired(_run({"agent_id": "agt-1", "transcript_path": str(path)}))


def test_unreadable_input_is_silence_and_exit_zero():
    r = subprocess.run([sys.executable, HOOK], input="not json",
                       capture_output=True, text=True)
    assert r.returncode == 0 and not _fired(r)


def test_a_torn_transcript_line_does_not_stop_it(tmp_path):
    """A file appended to during a run can end mid-write. The last COMPLETE usage line wins."""
    d = tmp_path / "subagents"
    d.mkdir(parents=True)
    path = d / "agent-agt-1.jsonl"
    path.write_text(_line(170_000) + "\n" + '{"type":"assis')
    assert _fired(_run({"agent_id": "agt-1", "transcript_path": str(path)}))


def test_it_always_exits_zero(tmp_path):
    """It runs after every tool call in the drive. A non-zero exit here would surface as an
    error on work that is fine."""
    path = _transcript(tmp_path, [190_000])
    assert _run({"agent_id": "agt-1", "transcript_path": path}).returncode == 0
    assert _run({"agent_id": "agt-1"}).returncode == 0
