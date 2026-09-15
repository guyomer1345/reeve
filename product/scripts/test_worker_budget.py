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


# --- the breadcrumb: making the silence readable -----------------------------
# The hook's whole fail direction is silence, and one of its silent exits is also its NORMAL
# exit (the orchestrator's own tool calls, which it is registered for). That made a permanently
# dead trigger and a healthy run look identical from outside — which is how ask #3 came to be
# ticked off against a mechanism nobody could show had ever run. These pin the evidence trail.

def _crumbs(tmp_path):
    d = tmp_path / ".workflow" / "worker-budget"
    return {p.stem: json.loads(p.read_text()) for p in d.glob("*.json")} if d.is_dir() else {}


def _project(tmp_path):
    (tmp_path / ".workflow").mkdir(parents=True, exist_ok=True)
    return str(tmp_path)


def test_the_reading_half_RUNNING_leaves_proof_even_when_it_does_not_fire(tmp_path):
    """The one breadcrumb that proves something on its own, and the one the drive asserts.

    Written BEFORE the threshold test on purpose: a worker at 23% is the mechanism working, and
    if only a firing left a trace then a healthy loop would be indistinguishable from a no-op
    until something happened to cross 75% — which may be never.
    """
    path = _transcript(tmp_path, [46_000])                 # 23% — nowhere near the threshold
    r = _run({"agent_id": "agt-1", "transcript_path": path, "cwd": _project(tmp_path)})
    assert not _fired(r)
    located = _crumbs(tmp_path)["located"]
    assert located["fired"] is False
    assert located["used"] == 46_000 and located["pct"] == 23.0
    assert located["transcript"] == path


def test_a_firing_is_recorded_as_a_firing(tmp_path):
    path = _transcript(tmp_path, [160_000])
    r = _run({"agent_id": "agt-1", "transcript_path": path, "cwd": _project(tmp_path)})
    assert _fired(r)
    assert _crumbs(tmp_path)["located"]["fired"] is True


def test_the_orchestrator_path_records_WHICH_KEYS_ARRIVED(tmp_path):
    """`no-agent-id` is expected and proves nothing alone — it is what every orchestrator tool
    call produces. Its value is the key list: if the harness ever names a worker differently,
    this is the file that says so, instead of a reader re-deriving it from the source."""
    r = _run({"transcript_path": "/nope", "cwd": _project(tmp_path), "tool_name": "Task"})
    assert not _fired(r)
    crumb = _crumbs(tmp_path)["no-agent-id"]
    assert crumb["tool"] == "Task"
    assert "transcript_path" in crumb["payload_keys"]
    assert "agent_id" not in crumb["payload_keys"]
    assert "located" not in _crumbs(tmp_path), "nothing was located; it must not claim otherwise"


def test_a_transcript_it_could_not_find_records_WHERE_IT_LOOKED(tmp_path):
    sess = tmp_path / "sess-1.jsonl"
    sess.write_text("{}\n")
    r = _run({"agent_id": "ghost", "transcript_path": str(sess), "cwd": _project(tmp_path)})
    assert not _fired(r)
    tried = _crumbs(tmp_path)["no-transcript"]["tried"]
    assert os.path.join(str(tmp_path), "sess-1", "subagents", "agent-ghost.jsonl") in tried, tried


def test_a_shape_it_does_not_understand_is_recorded_as_such(tmp_path):
    d = tmp_path / "subagents"
    d.mkdir(parents=True)
    p = d / "agent-agt-1.jsonl"
    p.write_text(json.dumps({"type": "assistant", "message": {"usage": {"weird": 1}}}) + "\n")
    _run({"agent_id": "agt-1", "transcript_path": str(p), "cwd": _project(tmp_path)})
    assert "no-usage" in _crumbs(tmp_path)
    assert "located" not in _crumbs(tmp_path)


def test_it_does_NOT_create_dot_workflow_and_leaves_no_trace_without_one(tmp_path):
    """A hook that makes directories to record its own presence litters every tree a worker is
    cwd'd into. Breadcrumbs go into a `.workflow/` that already exists, or nowhere."""
    path = _transcript(tmp_path, [160_000])
    r = _run({"agent_id": "agt-1", "transcript_path": path, "cwd": str(tmp_path)})
    assert _fired(r), "the verdict is unchanged by having nowhere to record it"
    assert not (tmp_path / ".workflow").exists()


def test_the_breadcrumb_NEVER_speaks_to_the_model(tmp_path):
    """It is evidence on disk, not a second detector. A below-threshold worker must still see
    an empty stdout — `additionalContext` on every tool call is exactly the window cost this
    hook exists to protect."""
    path = _transcript(tmp_path, [46_000])
    r = _run({"agent_id": "agt-1", "transcript_path": path, "cwd": _project(tmp_path)})
    assert r.stdout.strip() == ""
    assert r.stderr.strip() == ""
    assert "located" in _crumbs(tmp_path)


def test_existence_survives_what_the_count_does_not(tmp_path):
    """The count is advisory — two workers of one wave can lose an increment. Existence is the
    signal, so a torn or garbage prior file must reset the count and keep the file."""
    path = _transcript(tmp_path, [46_000])
    _run({"agent_id": "agt-1", "transcript_path": path, "cwd": _project(tmp_path)})
    _run({"agent_id": "agt-1", "transcript_path": path, "cwd": _project(tmp_path)})
    assert _crumbs(tmp_path)["located"]["count"] == 2
    crumb = tmp_path / ".workflow" / "worker-budget" / "located.json"
    crumb.write_text("{not json")
    _run({"agent_id": "agt-1", "transcript_path": path, "cwd": _project(tmp_path)})
    assert _crumbs(tmp_path)["located"]["count"] == 1


def test_an_unwritable_breadcrumb_root_changes_NOTHING(tmp_path):
    """Recording must never be able to break the thing it is recording."""
    path = _transcript(tmp_path, [160_000])
    (tmp_path / ".workflow").mkdir()
    (tmp_path / ".workflow" / "worker-budget").write_text("i am a file, not a directory")
    r = _run({"agent_id": "agt-1", "transcript_path": path, "cwd": str(tmp_path)})
    assert r.returncode == 0
    assert _fired(r)


# --- the locator, against the layout that is actually on disk ----------------
# Both of these are regressions for defects the breadcrumb work surfaced, and they are ONE
# defect in two halves that hid each other. The real layout is:
#     <project>/<session-id>.jsonl                        the session transcript
#     <project>/<session-id>/subagents/agent-<aid>.jsonl   the worker's own
# The shipped locator accepted the payload's `transcript_path` on the sole evidence that it was
# a file — which makes it the SESSION transcript — and its fallback looked under
# `dirname(session)`, one level too high to ever exist. So the first route answered wrongly and
# the second could not answer at all, and fixing either alone still leaves it broken.

def _session_layout(tmp_path, aid, worker_totals, session_total=180_000):
    """The real thing, reproduced: a session transcript file with a same-named sibling dir."""
    project = tmp_path / "project"
    project.mkdir(parents=True, exist_ok=True)
    sess = project / "sess-1.jsonl"
    sess.write_text(_line(session_total) + "\n")           # the ORCHESTRATOR, nearly full
    sub = project / "sess-1" / "subagents"
    sub.mkdir(parents=True, exist_ok=True)
    worker = sub / ("agent-%s.jsonl" % aid)
    worker.write_text("\n".join(_line(t) for t in worker_totals) + "\n")
    return str(sess), str(worker)


def test_the_SESSION_transcript_is_never_read_as_a_workers_own(tmp_path):
    """The mis-attribution half. A worker at 20% of its own window, under an orchestrator at
    90% of its, must not be told to yield — otherwise every worker of every wave yields, and
    the fuller the parent gets the sooner they do it."""
    sess, _ = _session_layout(tmp_path, "agt-1", [40_000], session_total=180_000)
    r = _run({"agent_id": "agt-1", "transcript_path": sess, "cwd": _project(tmp_path)})
    assert not _fired(r), "it read the orchestrator's occupancy and billed it to the worker"
    assert _crumbs(tmp_path)["located"]["used"] == 40_000


def test_the_workers_own_transcript_is_FOUND_from_the_session_path(tmp_path):
    """The no-op half. `dirname` of `<sid>.jsonl` is the project directory; the subagents live
    under `<sid>/`, so the session dir is the transcript path minus its extension."""
    sess, worker = _session_layout(tmp_path, "agt-1", [160_000], session_total=10_000)
    r = _run({"agent_id": "agt-1", "transcript_path": sess, "cwd": _project(tmp_path)})
    assert _fired(r), "a worker at 80% went untold because its transcript was never located"
    assert _crumbs(tmp_path)["located"]["transcript"] == worker


def test_one_workers_transcript_is_never_billed_to_ANOTHER(tmp_path):
    sess, _ = _session_layout(tmp_path, "agt-1", [180_000])
    r = _run({"agent_id": "agt-2", "transcript_path": sess, "cwd": _project(tmp_path)})
    assert not _fired(r)
    assert "no-transcript" in _crumbs(tmp_path)


def test_a_path_outside_subagents_is_refused_however_it_arrives(tmp_path):
    """The invariant, tested directly: under `subagents/` AND named for this agent, or nothing.
    Kept as its own test so a future route cannot reintroduce the defect by adding a candidate."""
    stray = tmp_path / "agent-agt-1.jsonl"
    stray.write_text(_line(180_000) + "\n")
    r = _run({"agent_id": "agt-1", "transcript_path": str(stray), "cwd": _project(tmp_path)})
    assert not _fired(r)
    assert "located" not in _crumbs(tmp_path)
