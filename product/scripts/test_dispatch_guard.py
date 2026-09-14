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
import shutil
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
    assert "reeve:execute" in r.stderr


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
    """Uses `document` rather than `execute` deliberately: `execute` answers to the SECOND gate
    below, and being the right agent says nothing about whether it should be going alone."""
    r = _run(_project(tmp_path), subagent_type="reeve:document",
             description="Document S2a-evidence-store", prompt=".workflow/items/s2a/changelog.md")
    assert r.returncode == ALLOWED


def test_a_namespaced_dispatch_survives_an_unparseable_graph(tmp_path):
    p = _project(tmp_path, loop="this file is corrupt\n")
    r = _run(p, subagent_type="reeve:research", description="Research X")
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


# --- the second gate: never wait alone, enforced ---------------------------------------
#
# The rule has existed since D192 and lived as a sentence, so a router that blocked on one
# `execute` while two were eligible violated nothing and nothing noticed. Every test here is
# paired: the block, and the thing that must still pass — a gate that refuses every `execute`
# would stall the loop far more effectively than the omission it replaces.

def _git_project(tmp_path, loop=LOOP):
    p = _project(tmp_path, loop)
    # Laid out as an install lays it out: the hook reaches `state.json`'s wave through
    # `wave_build.py` in `.claude/scripts/`, which is the single owner of that resolution. A test
    # that imported it some other way would not be testing the shipped arrangement.
    scripts = p / ".claude" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / "wave_build.py", scripts / "wave_build.py")
    subprocess.run(["git", "init", "-q", str(p)], check=True, capture_output=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(p), "config", k, v], check=True, capture_output=True)
    (p / "seed.txt").write_text("x")
    subprocess.run(["git", "-C", str(p), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(p), "commit", "-qm", "seed"], check=True, capture_output=True)
    return p


def _head_of(p):
    out = subprocess.run(["git", "-C", str(p), "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def _decision(p, considered, batch=(), head="HEAD"):
    rec = {"considered": list(considered), "batch": list(batch),
           "fan_out": len(batch) > 1, "decided_at": "2026-09-14T00:00:00Z",
           "head": _head_of(p) if head == "HEAD" else head}
    (p / ".workflow" / "wave-decision.json").write_text(json.dumps(rec), encoding="utf-8")
    return rec


def _exec(p, item="s2a"):
    return _run(p, subagent_type="reeve:execute", description="Execute %s" % item,
                prompt="Run the plan at .workflow/items/%s/plan.md" % item)


def test_an_execute_with_no_recorded_verdict_is_REFUSED(tmp_path):
    p = _git_project(tmp_path)
    r = _exec(p)
    assert r.returncode == BLOCKED
    assert "what else could run right now" in r.stderr
    assert "check_wave_independence.py --record" in r.stderr


def test_an_execute_the_gate_graded_goes_through(tmp_path):
    """The negative control for every block below."""
    p = _git_project(tmp_path)
    _decision(p, considered=["s2a"], batch=["s2a"])
    assert _exec(p).returncode == ALLOWED


def test_a_verdict_from_before_the_last_commit_is_stale(tmp_path):
    p = _git_project(tmp_path)
    _decision(p, considered=["s2a"], batch=["s2a"], head="0" * 40)
    r = _exec(p)
    assert r.returncode == BLOCKED
    assert "stale" in r.stderr


def test_an_item_the_gate_never_looked_at_is_refused(tmp_path):
    p = _git_project(tmp_path)
    _decision(p, considered=["other"], batch=["other"])
    r = _exec(p, item="s2a")
    assert r.returncode == BLOCKED
    assert "never looked at s2a" in r.stderr


def test_sending_ONE_of_an_eligible_batch_alone_is_refused(tmp_path):
    """The ask itself: the gate said three may run together and one is going by itself."""
    p = _git_project(tmp_path)
    _decision(p, considered=["s2a", "s2b", "s2c"], batch=["s2a", "s2b", "s2c"])
    r = _exec(p, item="s2a")
    assert r.returncode == BLOCKED
    assert "3 items may run concurrently" in r.stderr
    assert "ONE turn" in r.stderr


def test_a_minted_wave_lets_the_batch_through(tmp_path):
    """The negative control for the clause above — without it the gate would make a legal
    fan-out impossible, which is worse than the omission it replaces."""
    p = _git_project(tmp_path)
    _decision(p, considered=["s2a", "s2b", "s2c"], batch=["s2a", "s2b", "s2c"])
    (p / ".workflow" / "state.json").write_text(json.dumps({"wave": "w-abc123"}), encoding="utf-8")
    assert _exec(p, item="s2a").returncode == ALLOWED


def test_a_batch_of_one_needs_no_wave(tmp_path):
    """"Alone" is only a violation when something else was eligible. The gate saying so IS the
    recorded answer, and a serial dispatch must stay free."""
    p = _git_project(tmp_path)
    _decision(p, considered=["s2a", "s2b"], batch=["s2a"])
    assert _exec(p, item="s2a").returncode == ALLOWED


def test_a_project_with_no_workflow_is_untouched(tmp_path):
    p = _project(tmp_path, loop=None)
    assert _exec(p).returncode == ALLOWED


def test_the_second_gate_does_not_touch_the_other_leaves(tmp_path):
    """Stated as an assertion because it is a deliberate scope limit, not an oversight: no gate
    computes what may run beside a `document` or a `research`, so none is claimed."""
    p = _git_project(tmp_path)
    for cap in ("document", "research", "planner", "create-demo", "verify"):
        r = _run(p, subagent_type="reeve:" + cap, description="%s s2a" % cap,
                 prompt=".workflow/items/s2a/plan.md")
        assert r.returncode == ALLOWED, cap
