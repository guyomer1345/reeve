"""Tests for hooks/session_start.py — the SessionStart(clear) auto-rehydrate hook.

Runs the hook as Claude Code does (`python3 session_start.py` with the SessionStart JSON on
stdin) and asserts it emits the `hookSpecificOutput.additionalContext` contract carrying
`.workflow/handoff.md`, stays silent when there is nothing to rehydrate, and never errors out.
"""
import json
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent            # product/scripts
HOOK = HERE.parent / "hooks" / "session_start.py"


def _run(cwd, source="clear"):
    payload = {"hook_event_name": "SessionStart", "source": source, "cwd": str(cwd)}
    return subprocess.run(
        ["python3", str(HOOK)],
        input=json.dumps(payload), cwd=cwd, capture_output=True, text=True,
    )


def _handoff(tmp_path, text):
    (tmp_path / ".workflow").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".workflow" / "handoff.md").write_text(text)


def test_injects_handoff_as_additional_context(tmp_path):
    _handoff(tmp_path, "# Handoff\ncurrent_item: ITEM-7\nloop_position: execute\n")
    r = _run(tmp_path)
    assert r.returncode == 0
    out = json.loads(r.stdout)
    ac = out["hookSpecificOutput"]["additionalContext"]
    assert out["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "ITEM-7" in ac
    assert "handoff.md" in ac                      # the framing directive names the anchor


def test_silent_when_no_handoff(tmp_path):
    (tmp_path / ".workflow").mkdir()
    r = _run(tmp_path)
    assert r.returncode == 0
    assert r.stdout.strip() == ""                  # nothing to rehydrate -> no injection


def test_silent_when_handoff_blank(tmp_path):
    _handoff(tmp_path, "   \n\n")
    r = _run(tmp_path)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_large_handoff_is_truncated(tmp_path):
    _handoff(tmp_path, "x" * 20000)
    r = _run(tmp_path)
    out = json.loads(r.stdout)
    ac = out["hookSpecificOutput"]["additionalContext"]
    assert "truncated" in ac
    assert len(ac) < 12000                         # well under the harness ~10k additionalContext cap + framing


def test_garbage_stdin_exits_zero(tmp_path):
    r = subprocess.run(["python3", str(HOOK)], input="not json", cwd=tmp_path,
                       capture_output=True, text=True)
    assert r.returncode == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
