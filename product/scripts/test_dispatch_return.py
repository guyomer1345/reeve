"""Tests for hooks/dispatch_return.py — the PostToolUse detector for an over-contract return.

Runs the hook the way Claude Code does (`python3 dispatch_return.py` with the PostToolUse JSON
on stdin) and asserts the exit code, because exit 2 IS the warning: on PostToolUse it shows
stderr to the model and blocks nothing, which is the only action available after the tool has
already run. Exit 0 is "say nothing".

The failure this file mostly guards is the OPPOSITE of the one the hook exists for. A detector
that fires after every dispatch and is occasionally wrong is a detector the caller learns to
skip, and there is no measured distribution of return sizes behind the ceiling — so every
not-measurable case (an unknown payload shape, a foreign agent, a non-dispatch tool, garbage on
stdin) is asserted SILENT, and only a return that is unmistakably a pasted body warns.
"""
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent            # product/scripts
HOOK = HERE.parent / "hooks" / "dispatch_return.py"

WARNED = 2
SILENT = 0

# Comfortably over the hook's 20 000-character ceiling, and comfortably under it.
HUGE = "x" * 25000
SMALL = "wrote 3 files; changelog at .workflow/items/S2a/changelog.md; no divergences"


def _run(subagent_type="reeve:execute", response=None, tool="Agent"):
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": tool,
        "tool_input": {"subagent_type": subagent_type, "description": "", "prompt": ""},
        "tool_response": response,
        "tool_use_id": "toolu_01TEST",
    }
    return subprocess.run(
        ["python3", str(HOOK)],
        input=json.dumps(payload), capture_output=True, text=True, env=dict(os.environ),
    )


def test_an_oversized_return_from_a_package_agent_warns():
    r = _run(response={"type": "text", "text": HUGE})
    assert r.returncode == WARNED
    # The message has to be actionable at the point of reading, not just disapproving: the
    # caller's next move (don't carry it; the bulk belongs in scratch) is the whole payload.
    assert "dispatch-return over contract" in r.stderr
    assert "scratch/" in r.stderr
    assert "25000" in r.stderr


def test_a_normal_return_is_silent():
    r = _run(response={"type": "text", "text": SMALL})
    assert r.returncode == SILENT
    assert r.stderr == ""


def test_the_boundary_is_inclusive_so_exactly_at_ceiling_is_fine():
    r = _run(response={"type": "text", "text": "y" * 20000})
    assert r.returncode == SILENT


def test_content_block_lists_are_measured_whole():
    """A subagent return may arrive as content blocks; three 8k blocks is a 24k return."""
    blocks = [{"type": "text", "text": "z" * 8000} for _ in range(3)]
    r = _run(response={"content": blocks})
    assert r.returncode == WARNED


def test_a_bare_string_response_is_measured():
    assert _run(response=HUGE).returncode == WARNED


def test_bare_agent_names_count_as_this_packages_agents():
    """A dispatch may be written `execute` or `reeve:execute`; both are the same capability."""
    assert _run(subagent_type="execute", response=HUGE).returncode == WARNED


def test_a_foreign_agent_is_never_warned_about():
    """The contract is this package's. A search dispatch to a general worker never agreed to it,
    and warning about it would teach the caller to ignore the warning that matters."""
    for foreign in ("general-purpose", "Explore", "other-plugin:execute", "statusline-setup"):
        r = _run(subagent_type=foreign, response=HUGE)
        assert r.returncode == SILENT, foreign
        assert r.stderr == ""


def test_an_inline_node_is_not_a_dispatch_and_is_not_measured():
    """`verify`, `planner`, `debug` run inline; they are not in the dispatched set."""
    assert _run(subagent_type="reeve:verify", response=HUGE).returncode == SILENT


def test_a_non_dispatch_tool_is_ignored():
    r = _run(tool="Bash", response={"stdout": HUGE, "exit_code": 0})
    assert r.returncode == SILENT


def test_an_unrecognised_payload_shape_is_silent_not_guessed():
    """Not-measured must read as silence. The documented schema does not pin down the shape of
    `tool_response` for a subagent dispatch, so a shape this cannot read is a measurement that
    did not happen — and a size it invented would be a warning the reader cannot falsify."""
    for shape in (None, 12345, {"usage": {"input_tokens": 9}}, [], {}):
        r = _run(response=shape)
        assert r.returncode == SILENT, shape
        assert r.stderr == ""


def test_garbage_on_stdin_never_interferes_with_the_loop():
    r = subprocess.run(["python3", str(HOOK)], input="not json at all",
                       capture_output=True, text=True, env=dict(os.environ))
    assert r.returncode == SILENT
    assert r.stderr == ""


def test_a_missing_tool_input_is_silent():
    r = subprocess.run(
        ["python3", str(HOOK)],
        input=json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Agent"}),
        capture_output=True, text=True, env=dict(os.environ))
    assert r.returncode == SILENT


def test_the_hook_is_registered_for_posttooluse_on_the_dispatch_tools():
    """The file is inert unless `settings.json` wires it, and the matcher has to be the dispatch
    tools — the same pair `dispatch_guard.py` matches at PreToolUse."""
    settings = json.loads((HERE.parent / "templates" / "settings.json").read_text(encoding="utf-8"))
    post = settings["hooks"]["PostToolUse"]
    entry = [e for e in post if e["matcher"] == "Agent|Task"]
    assert entry, "no PostToolUse(Agent|Task) entry"
    assert any("dispatch_return.py" in h["command"] for h in entry[0]["hooks"])


def test_the_hook_ships():
    """A hook absent from the manifest is not installed into a target, so it would never run."""
    manifest = json.loads((HERE.parent / "MANIFEST.json").read_text(encoding="utf-8"))
    dests = {row["dest"] for row in manifest["install"]}
    assert ".claude/hooks/dispatch_return.py" in dests
