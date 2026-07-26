"""Tests for hooks/precompact.py — the PreCompact context-governor backstop.

Runs the hook as Claude Code does (`python3 precompact.py` with the PreCompact JSON on stdin)
and asserts it injects the handoff anchor through a compaction, NEVER blocks (exit 0, no
`decision: block`), and stays silent with nothing to preserve.
"""
import json
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent            # product/scripts
HOOK = HERE.parent / "hooks" / "precompact.py"


def _run(cwd, matcher="auto"):
    payload = {"hook_event_name": "PreCompact", "cwd": str(cwd)}
    return subprocess.run(
        ["python3", str(HOOK)],
        input=json.dumps(payload), cwd=cwd, capture_output=True, text=True,
    )


def _handoff(tmp_path, text):
    (tmp_path / ".workflow").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".workflow" / "handoff.md").write_text(text)


def test_injects_handoff_and_never_blocks(tmp_path):
    _handoff(tmp_path, "# Handoff\ncurrent_item: ITEM-3\n")
    r = _run(tmp_path)
    assert r.returncode == 0                        # backstop, not a gate
    out = json.loads(r.stdout)
    assert out["hookSpecificOutput"]["hookEventName"] == "PreCompact"
    ac = out["hookSpecificOutput"]["additionalContext"]
    assert "ITEM-3" in ac
    assert "/dispatch" in ac                        # directive to refresh after compaction
    assert out.get("decision") != "block"           # must not block compaction


def test_silent_when_no_handoff(tmp_path):
    (tmp_path / ".workflow").mkdir()
    r = _run(tmp_path)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_large_handoff_is_truncated(tmp_path):
    _handoff(tmp_path, "y" * 20000)
    out = json.loads(_run(tmp_path).stdout)
    ac = out["hookSpecificOutput"]["additionalContext"]
    assert "truncated" in ac
    assert len(ac) < 12000


def test_garbage_stdin_exits_zero(tmp_path):
    r = subprocess.run(["python3", str(HOOK)], input="not json", cwd=tmp_path,
                       capture_output=True, text=True)
    assert r.returncode == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
