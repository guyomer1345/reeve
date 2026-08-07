"""Tests for scripts/measure-dispatch.py — the meta-side dispatch-fidelity measurement.

Fixtures are synthetic transcripts in the real shape, because the point of these tests is the
one thing a measurement script must never do: report a confident zero when it has actually
stopped understanding the data. So the assertions are as much about "says nothing was found"
as about the counts themselves.
"""
import importlib.util
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("measure_dispatch", HERE / "measure-dispatch.py")
md = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(md)


def _turn(usage=None, tools=(), ts="2026-08-07T10:00:00.000Z", msg_id=None):
    content = [dict({"type": "tool_use", "name": n, "input": i},
                    **({"id": i.get("_id")} if isinstance(i, dict) and i.get("_id") else {}))
               for n, i in tools]
    msg = {"content": content or [{"type": "text", "text": "ok"}], "usage": usage or {}}
    if msg_id:
        msg["id"] = msg_id
    return {"type": "assistant", "timestamp": ts, "message": msg}


def _result(tool_id, text, ts="2026-08-07T10:00:01.000Z"):
    """The user-side record that carries what a tool actually returned."""
    return {"type": "user", "timestamp": ts, "isSidechain": True,
            "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tool_id, "content": text}]}}


def _subagent(root, session, agent_id, agent_type, description, prompt,
              turns=(), started="2026-08-07T10:00:00.000Z"):
    d = Path(root) / session / "subagents"
    d.mkdir(parents=True, exist_ok=True)
    lines = [{"type": "user", "timestamp": started, "isSidechain": True,
              "message": {"role": "user", "content": prompt}}]
    lines.extend(turns)
    (d / f"agent-{agent_id}.jsonl").write_text(
        "\n".join(json.dumps(x) for x in lines), encoding="utf-8")
    (d / f"agent-{agent_id}.meta.json").write_text(
        json.dumps({"agentType": agent_type, "description": description,
                    "agentId": agent_id, "spawnDepth": 1}), encoding="utf-8")


def test_slugify_matches_the_cli_one_char_for_one(tmp_path):
    # a real observed pair: a space and a dot each become exactly one dash
    assert md.slugify("/mnt/c/x/agentic cyber").endswith("-agentic-cyber")
    assert md.slugify("/home/u/.claude").endswith("-home-u--claude")


def test_a_general_purpose_loop_dispatch_is_counted_and_named(tmp_path, capsys):
    _subagent(tmp_path, "s1", "a1", "general-purpose", "Execute S2a-evidence-store",
              "Work the plan at .workflow/items/s2a/plan.md", [_turn()])
    subs, skills, n, _ = md.scan(str(tmp_path))
    rc = md.report(subs, skills, n)
    out = capsys.readouterr().out
    assert "LOOP NODES ON A GENERAL WORKER" in out
    assert "execute" in out
    assert rc == 2                       # a finding, not a clean run


def test_a_namespaced_dispatch_counts_as_the_role_arriving(tmp_path, capsys):
    _subagent(tmp_path, "s1", "a1", "dev-autonomous-workflow:execute", "Execute item",
              ".workflow/items/s2a/plan.md", [_turn()])
    subs, skills, n, _ = md.scan(str(tmp_path))
    assert subs[0]["attribution"] == "declared"
    assert subs[0]["node"] == "execute"
    assert md.report(subs, skills, n) == 0
    assert "1/1  role reached the worker" in capsys.readouterr().out


def test_a_skill_load_inside_a_general_subagent_also_counts_as_arrival(tmp_path, capsys):
    _subagent(tmp_path, "s1", "a1", "general-purpose", "Verify the item", "check it",
              [_turn(tools=[("Skill", {"skill": "dev-autonomous-workflow:verify"})])])
    subs, _, _, _ = md.scan(str(tmp_path))
    assert subs[0]["skill_loads"] == 1


def test_token_components_stay_separate(tmp_path):
    _subagent(tmp_path, "s1", "a1", "dev-autonomous-workflow:execute", "Execute", "go", [
        _turn(usage={"input_tokens": 5, "cache_creation_input_tokens": 1000,
                     "cache_read_input_tokens": 20000, "output_tokens": 300}),
        _turn(usage={"input_tokens": 5, "cache_creation_input_tokens": 500,
                     "cache_read_input_tokens": 35000, "output_tokens": 100}),
    ])
    s = md.scan(str(tmp_path))[0][0]
    assert s["created_tokens"] == 1500
    assert s["output_tokens"] == 400
    assert s["read_tokens"] == 55000        # the re-read tax, summed
    assert s["peak_context"] == 35000       # the largest single context, NOT the sum
    assert s["new_tokens"] == 1910          # what the dispatch caused to be processed fresh


def test_a_nested_dispatch_inside_a_leaf_is_reported(tmp_path, capsys):
    _subagent(tmp_path, "s1", "a1", "general-purpose", "Execute the item", "go",
              [_turn(tools=[("Agent", {"subagent_type": "general-purpose"})])])
    subs, skills, n, _ = md.scan(str(tmp_path))
    md.report(subs, skills, n)
    assert "leaves that spawned their own agent" in capsys.readouterr().out
    assert subs[0]["nested_dispatches"] == 1


def test_main_window_skill_loads_are_the_telephone_game_signal(tmp_path):
    (tmp_path / "s1").mkdir()
    (tmp_path / "s1.jsonl").write_text(json.dumps(
        _turn(tools=[("Skill", {"skill": "dev-autonomous-workflow:execute"}),
                     ("Agent", {"subagent_type": "general-purpose"})])), encoding="utf-8")
    _, skills, dispatches, _ = md.scan(str(tmp_path))
    assert skills["dev-autonomous-workflow:execute"] == 1
    assert dispatches == 1


def test_a_sidechain_record_is_not_counted_as_a_main_window_dispatch(tmp_path):
    (tmp_path / "s1").mkdir()
    rec = _turn(tools=[("Agent", {})])
    rec["isSidechain"] = True
    (tmp_path / "s1.jsonl").write_text(json.dumps(rec), encoding="utf-8")
    _, _, dispatches, _ = md.scan(str(tmp_path))
    assert dispatches == 0


def test_an_empty_scan_says_nothing_was_measured_rather_than_all_clear(tmp_path, capsys):
    rc = md.report([], {}, 0)
    out = capsys.readouterr().out
    assert "nothing measured" in out
    assert "NOT a clean result" in out
    assert rc == 1


def test_since_excludes_older_dispatches(tmp_path):
    _subagent(tmp_path, "s1", "old", "general-purpose", "Execute old", "go",
              [_turn(ts="2026-08-01T10:00:00.000Z")], started="2026-08-01T10:00:00.000Z")
    _subagent(tmp_path, "s1", "new", "general-purpose", "Execute new", "go",
              [_turn()], started="2026-08-07T10:00:00.000Z")
    assert len(md.scan(str(tmp_path), since="2026-08-07")[0]) == 1


def test_an_unreadable_meta_file_degrades_to_unattributed_not_a_crash(tmp_path):
    _subagent(tmp_path, "s1", "a1", "general-purpose", "x", "y", [_turn()])
    (tmp_path / "s1" / "subagents" / "agent-a1.meta.json").write_text("{ broken")
    s = md.scan(str(tmp_path))[0][0]
    assert s["agent_type"] == "(none)"
    assert s["node"] == "(unattributed)"


# ---------------------------------------------------------------- one response, many records

def test_one_response_written_as_several_records_is_counted_once(tmp_path):
    """The defect that inflated this script's own first numbers 2.8x.

    The CLI writes ONE RECORD PER CONTENT BLOCK, each repeating the whole response's `usage`.
    A response that thought, spoke and called two tools therefore lands four times — and a
    naive sum multiplies `cache_creation` by four.
    """
    u = {"input_tokens": 5, "cache_creation_input_tokens": 1000,
         "cache_read_input_tokens": 20000, "output_tokens": 40}
    _subagent(tmp_path, "s1", "a1", "dev-autonomous-workflow:execute", "Execute", "go", [
        _turn(usage=u, msg_id="msg_1"),
        _turn(usage=u, msg_id="msg_1", tools=[("Read", {"file_path": "a.py"})]),
        _turn(usage=u, msg_id="msg_1", tools=[("Read", {"file_path": "b.py"})]),
    ])
    s = md.scan(str(tmp_path))[0][0]
    assert s["created_tokens"] == 1000      # not 3000
    assert s["read_tokens"] == 20000        # not 60000
    assert s["turns"] == 1                  # one API call, three records
    assert s["tools"]["Read"] == 2          # tool CALLS are still counted per block


def test_a_partial_record_never_lowers_the_response_total(tmp_path):
    """Within one response the counters are snapshots, so the aggregate is MAX, not first."""
    _subagent(tmp_path, "s1", "a1", "dev-autonomous-workflow:execute", "Execute", "go", [
        _turn(usage={"cache_creation_input_tokens": 900, "output_tokens": 3}, msg_id="m"),
        _turn(usage={"cache_creation_input_tokens": 900, "output_tokens": 1200}, msg_id="m"),
    ])
    s = md.scan(str(tmp_path))[0][0]
    assert s["output_tokens"] == 1200 and s["created_tokens"] == 900


def test_records_with_no_response_id_still_count_separately(tmp_path):
    """An unknown shape must over-count as before, never silently drop turns."""
    calls = md.api_calls([
        {"type": "assistant", "message": {"usage": {"output_tokens": 10}}},
        {"type": "assistant", "message": {"usage": {"output_tokens": 20}}},
    ])
    assert [c["output_tokens"] for c in calls] == [10, 20]


# ---------------------------------------------------------------- the 11f writer attribution

def _plan(project, item, files):
    d = Path(project) / ".workflow" / "items" / item
    d.mkdir(parents=True, exist_ok=True)
    rows = "\n".join("| `%s` | why |" % f for f in files)
    (d / "plan.md").write_text(
        "# Plan\n\n## Files touched\n| file | what |\n|---|---|\n%s\n\n## Steps\n1. do it\n"
        % rows, encoding="utf-8")


def test_discovery_and_production_are_attributed_separately(tmp_path):
    project = tmp_path / "proj"
    _plan(project, "IT-1", ["src/a.py"])
    transcripts = tmp_path / "tx"
    _subagent(transcripts, "s1", "a1", "dev-autonomous-workflow:execute", "Execute",
              "run .workflow/items/IT-1/plan.md", [
                  _turn(tools=[("Read", {"file_path": str(project / "src/a.py"), "_id": "t1"})]),
                  _turn(tools=[("Write", {"file_path": str(project / "src/a.py"),
                                          "content": "x" * 400, "_id": "t2"})]),
              ])
    # the read fed 800 chars back; the write fed nothing back but PRODUCED 400
    p = transcripts / "s1" / "subagents" / "agent-a1.jsonl"
    p.write_text(p.read_text() + "\n" + json.dumps(_result("t1", "y" * 800)), encoding="utf-8")
    s = md.scan(str(transcripts), project_root=str(project))[0][0]
    assert s["scope"]["discovery_chars"] == 800
    assert s["scope"]["produced_chars"] == 400
    assert s["scope"]["read_calls"] == 1 and s["scope"]["write_calls"] == 1
    assert s["item"] == "IT-1"


def test_a_file_read_through_bash_is_still_discovery(tmp_path):
    """A worker can cat its way through a repo; counting only `Read` would call that clean."""
    transcripts = tmp_path / "tx"
    _subagent(transcripts, "s1", "a1", "dev-autonomous-workflow:execute", "Execute", "go", [
        _turn(tools=[("Bash", {"command": "sed -n 1,200p src/big.py", "_id": "t1"}),
                     ("Bash", {"command": "pytest -q", "_id": "t2"})]),
    ])
    p = transcripts / "s1" / "subagents" / "agent-a1.jsonl"
    p.write_text(p.read_text() + "\n" + json.dumps(_result("t1", "y" * 600))
                 + "\n" + json.dumps(_result("t2", "z" * 100)), encoding="utf-8")
    s = md.scan(str(transcripts))[0][0]
    assert s["scope"]["discovery_chars"] == 600   # the sed
    assert s["scope"]["exec_chars"] == 100        # the test run is feedback, not context


def test_the_same_file_read_twice_is_counted_as_a_re_read(tmp_path):
    transcripts = tmp_path / "tx"
    _subagent(transcripts, "s1", "a1", "dev-autonomous-workflow:execute", "Execute", "go", [
        _turn(tools=[("Read", {"file_path": "/p/a.py"}), ("Read", {"file_path": "/p/a.py"}),
                     ("Read", {"file_path": "/p/b.py"})]),
    ])
    s = md.scan(str(transcripts))[0][0]
    assert s["scope"]["read_calls"] == 3
    assert s["scope"]["distinct_files_read"] == 2
    assert s["scope"]["reread_calls"] == 1


def test_reads_are_scored_against_the_plans_declared_files(tmp_path):
    project = tmp_path / "proj"
    _plan(project, "IT-1", ["src/a.py", "docs/*"])
    transcripts = tmp_path / "tx"
    _subagent(transcripts, "s1", "a1", "dev-autonomous-workflow:execute", "Execute",
              "work .workflow/items/IT-1/", [
                  _turn(tools=[("Read", {"file_path": str(project / "src/a.py")}),
                               ("Read", {"file_path": str(project / "docs/spec.md")}),
                               ("Read", {"file_path": str(project / "src/elsewhere.py")})]),
              ])
    s = md.scan(str(transcripts), project_root=str(project))[0][0]
    assert s["scope"]["on_plan_reads"] == 2      # the named file and the declared glob
    assert s["scope"]["off_plan_reads"] == 1


def test_no_plan_is_reported_as_unscored_not_as_zero_off_plan(tmp_path, capsys):
    transcripts = tmp_path / "tx"
    _subagent(transcripts, "s1", "a1", "dev-autonomous-workflow:execute", "Execute", "go",
              [_turn(tools=[("Read", {"file_path": "/p/a.py"})])])
    subs = md.scan(str(transcripts))[0]
    assert "off_plan_reads" not in subs[0]["scope"]
    md.report_writer_scope(subs)
    assert "no plan" in capsys.readouterr().out


def test_boot_is_the_first_responses_cache_write(tmp_path):
    """The fixed cost of a dispatch existing — what any plan-splitting proposal must beat."""
    _subagent(tmp_path, "s1", "a1", "dev-autonomous-workflow:execute", "Execute", "go", [
        _turn(usage={"cache_creation_input_tokens": 9999, "cache_read_input_tokens": 0},
              msg_id="m1"),
        _turn(usage={"cache_creation_input_tokens": 2000,
                     "cache_read_input_tokens": 9999}, msg_id="m2"),
    ])
    assert md.scan(str(tmp_path))[0][0]["boot_tokens"] == 9999


def test_the_router_trace_attributes_growth_to_the_node_that_was_running(tmp_path):
    """An inline node's reads land in the ROUTER's window; a dispatched one's do not. This is
    the only view that puts those two on the same axis."""
    def call(ctx, tools, mid):
        return _turn(usage={"cache_read_input_tokens": ctx}, tools=tools, msg_id=mid)
    recs = [
        call(10_000, [("Skill", {"skill": "dev-autonomous-workflow:planner"})], "m1"),
        call(50_000, [("Agent", {"subagent_type": "dev-autonomous-workflow:execute"})], "m2"),
        call(52_000, [], "m3"),
    ]
    trace = md.router_trace(recs)
    assert [(m["how"], m["label"]) for m in trace] == [("inline", "planner"),
                                                       ("dispatch", "execute")]
    assert trace[0]["added"] == 40_000     # the inline node's reads landed here
    assert trace[1]["added"] == 2_000      # the dispatched one handed back a pointer


def test_loop_runtime_reads_are_not_scored_as_off_plan_hunting(tmp_path):
    """The first run of this report called `execute` 57% off-plan; every one of those reads
    was the item's own plan.md/promises.json — files a plan never lists in its own table."""
    project = tmp_path / "proj"
    _plan(project, "IT-1", ["src/a.py"])
    transcripts = tmp_path / "tx"
    _subagent(transcripts, "s1", "a1", "dev-autonomous-workflow:execute", "Execute",
              "work .workflow/items/IT-1/", [
                  _turn(tools=[("Read", {"file_path": str(project / "src/a.py")}),
                               ("Read", {"file_path": str(project /
                                                          ".workflow/items/IT-1/plan.md")}),
                               ("Read", {"file_path": str(project / ".workflow/checks.env")})]),
              ])
    s = md.scan(str(transcripts), project_root=str(project))[0][0]["scope"]
    assert s["on_plan_reads"] == 1
    assert s["off_plan_reads"] == 0          # NOT 2
    assert s["scaffolding_reads"] == 2


def test_a_stall_past_the_cache_ttl_is_named_not_billed_as_context(tmp_path):
    """A node that idled once reads as a node that consumed twice the context — which is
    half of the number that opened this phase."""
    _subagent(tmp_path, "s1", "a1", "dev-autonomous-workflow:execute", "Execute", "go", [
        _turn(usage={"cache_creation_input_tokens": 10_000}, msg_id="m1",
              ts="2026-08-07T10:00:00.000Z"),
        _turn(usage={"cache_creation_input_tokens": 55_000}, msg_id="m2",
              ts="2026-08-07T10:11:00.000Z"),   # 11 minutes later: the whole prefix again
        _turn(usage={"cache_creation_input_tokens": 500}, msg_id="m3",
              ts="2026-08-07T10:11:30.000Z"),
    ])
    s = md.scan(str(tmp_path))[0][0]
    assert s["stalls"] == 1 and s["stall_tokens"] == 55_000
