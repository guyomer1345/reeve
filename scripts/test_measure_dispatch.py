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


def _turn(usage=None, tools=(), ts="2026-08-07T10:00:00.000Z"):
    content = [{"type": "tool_use", "name": n, "input": i} for n, i in tools]
    return {"type": "assistant", "timestamp": ts,
            "message": {"content": content or [{"type": "text", "text": "ok"}],
                        "usage": usage or {}}}


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
    subs, skills, n = md.scan(str(tmp_path))
    rc = md.report(subs, skills, n)
    out = capsys.readouterr().out
    assert "LOOP NODES ON A GENERAL WORKER" in out
    assert "execute" in out
    assert rc == 2                       # a finding, not a clean run


def test_a_namespaced_dispatch_counts_as_the_role_arriving(tmp_path, capsys):
    _subagent(tmp_path, "s1", "a1", "dev-autonomous-workflow:execute", "Execute item",
              ".workflow/items/s2a/plan.md", [_turn()])
    subs, skills, n = md.scan(str(tmp_path))
    assert subs[0]["attribution"] == "declared"
    assert subs[0]["node"] == "execute"
    assert md.report(subs, skills, n) == 0
    assert "1/1  role reached the worker" in capsys.readouterr().out


def test_a_skill_load_inside_a_general_subagent_also_counts_as_arrival(tmp_path, capsys):
    _subagent(tmp_path, "s1", "a1", "general-purpose", "Verify the item", "check it",
              [_turn(tools=[("Skill", {"skill": "dev-autonomous-workflow:verify"})])])
    subs, _, _ = md.scan(str(tmp_path))
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
    subs, skills, n = md.scan(str(tmp_path))
    md.report(subs, skills, n)
    assert "leaves that spawned their own agent" in capsys.readouterr().out
    assert subs[0]["nested_dispatches"] == 1


def test_main_window_skill_loads_are_the_telephone_game_signal(tmp_path):
    (tmp_path / "s1").mkdir()
    (tmp_path / "s1.jsonl").write_text(json.dumps(
        _turn(tools=[("Skill", {"skill": "dev-autonomous-workflow:execute"}),
                     ("Agent", {"subagent_type": "general-purpose"})])), encoding="utf-8")
    _, skills, dispatches = md.scan(str(tmp_path))
    assert skills["dev-autonomous-workflow:execute"] == 1
    assert dispatches == 1


def test_a_sidechain_record_is_not_counted_as_a_main_window_dispatch(tmp_path):
    (tmp_path / "s1").mkdir()
    rec = _turn(tools=[("Agent", {})])
    rec["isSidechain"] = True
    (tmp_path / "s1.jsonl").write_text(json.dumps(rec), encoding="utf-8")
    _, _, dispatches = md.scan(str(tmp_path))
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
