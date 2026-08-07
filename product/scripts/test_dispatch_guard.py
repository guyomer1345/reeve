"""Tests for hooks/dispatch_guard.py — the gate that keeps loop nodes off general workers.

Runs the hook the way Claude Code does (`python3 dispatch_guard.py` with the PreToolUse JSON
on stdin) and asserts the exit code, because exit 2 IS the block: it is what stops the tool
call and hands the reason to the model. Exit 0 is "let it through".

The two halves worth guarding are opposite failures. A gate that blocks nothing is the defect
it was built for (that is what the shipped prose was). A gate that blocks everything stalls the
loop it protects — so the namespaced dispatch, the non-dispatch tool, and the uninitialised
project are all asserted to pass, including when the graph itself is broken.
"""
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent            # product/scripts
HOOK = HERE.parent / "hooks" / "dispatch_guard.py"

LOOP = """\
# Loop — the routing graph

| node | on output | next |
|---|---|---|
| `discuss` | spec drafted | `create-demo?` |
| `create-demo` | demo approved | `planner:decompose` |
| `planner:plan-one` | plan ready | `execute` |
| `execute` | changelog | `verify` |
| `verify` | **pass** | `document` |
| `document` | knowledge updated | `commit` |

Side doors (callable from anywhere): `create-issue` → backlog · `research` (service) · `answer`.
"""

BLOCKED = 2
ALLOWED = 0


def _project(tmp_path, loop=LOOP):
    if loop is not None:
        (tmp_path / ".workflow").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".workflow" / "loop.md").write_text(loop, encoding="utf-8")
    return tmp_path


def _run(cwd, subagent_type="general-purpose", description="", prompt="", tool="Agent"):
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": {
            "subagent_type": subagent_type,
            "description": description,
            "prompt": prompt,
        },
    }
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(cwd)
    return subprocess.run(
        ["python3", str(HOOK)],
        input=json.dumps(payload), cwd=str(cwd), capture_output=True, text=True, env=env,
    )


# --- the measured failure: this is the exact shape the drive produced -----------------
def test_execute_to_general_purpose_is_blocked(tmp_path):
    r = _run(_project(tmp_path), description="Execute S2a-evidence-store",
             prompt="Work the plan step by step and record what you did.")
    assert r.returncode == BLOCKED
    assert "execute" in r.stderr
    assert "dev-autonomous-workflow:execute" in r.stderr


def test_document_to_general_purpose_is_blocked(tmp_path):
    r = _run(_project(tmp_path), description="Document S2a-evidence-store", prompt="Fold it in.")
    assert r.returncode == BLOCKED


def test_a_hyphenated_node_name_is_matched_whole(tmp_path):
    r = _run(_project(tmp_path), description="Create-demo for the settings screen", prompt="x")
    assert r.returncode == BLOCKED
    assert "create-demo" in r.stderr


def test_the_prompts_first_line_counts_as_a_title(tmp_path):
    r = _run(_project(tmp_path), description="",
             prompt="Verify the item's artifacts against the plan.\n\nDetails follow.")
    assert r.returncode == BLOCKED


def test_a_bare_imperative_opener_still_matches(tmp_path):
    r = _run(_project(tmp_path), description="Run execute for item 3", prompt="x")
    assert r.returncode == BLOCKED


# --- the paraphrase that names no node still reaches into the loop's runtime ----------
def test_a_prompt_touching_the_items_tree_is_blocked_even_with_no_node_name(tmp_path):
    r = _run(_project(tmp_path), description="Carry out the approved work",
             prompt="Read .workflow/items/s2a/plan.md and make the changes it lists.")
    assert r.returncode == BLOCKED


def test_an_ordinary_general_purpose_search_is_allowed(tmp_path):
    r = _run(_project(tmp_path), description="Find the auth middleware",
             prompt="Search the codebase for where sessions are validated and report back.")
    assert r.returncode == ALLOWED


def test_the_word_document_in_ordinary_prose_is_not_a_dispatch_title(tmp_path):
    r = _run(_project(tmp_path), description="Summarise the vendor API",
             prompt="Read their reference document and list the endpoints.")
    assert r.returncode == ALLOWED


# --- the gate must never stall the loop's own work ------------------------------------
def test_a_namespaced_agent_dispatch_is_allowed(tmp_path):
    r = _run(_project(tmp_path), subagent_type="dev-autonomous-workflow:execute",
             description="Execute S2a-evidence-store", prompt=".workflow/items/s2a/plan.md")
    assert r.returncode == ALLOWED


def test_a_namespaced_dispatch_survives_an_unparseable_graph(tmp_path):
    p = _project(tmp_path, loop="this file is corrupt\n")
    r = _run(p, subagent_type="dev-autonomous-workflow:research", description="Research X")
    assert r.returncode == ALLOWED


def test_an_unparseable_graph_blocks_general_dispatch_rather_than_passing_vacuously(tmp_path):
    p = _project(tmp_path, loop="this file is corrupt\n")
    r = _run(p, description="Execute S2a-evidence-store")
    assert r.returncode == BLOCKED
    assert "names no nodes" in r.stderr


def test_a_project_with_no_loop_is_left_alone(tmp_path):
    r = _run(_project(tmp_path, loop=None), description="Execute something")
    assert r.returncode == ALLOWED


def test_a_non_dispatch_tool_is_ignored(tmp_path):
    r = _run(_project(tmp_path), tool="Bash", description="Execute S2a")
    assert r.returncode == ALLOWED


def test_a_garbled_payload_never_tracebacks(tmp_path):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(_project(tmp_path))
    r = subprocess.run(["python3", str(HOOK)], input="not json at all",
                       cwd=str(tmp_path), capture_output=True, text=True, env=env)
    assert r.returncode == ALLOWED
    assert "Traceback" not in r.stderr


def test_the_task_tool_name_is_matched_too(tmp_path):
    r = _run(_project(tmp_path), tool="Task", description="Execute S2a-evidence-store")
    assert r.returncode == BLOCKED
