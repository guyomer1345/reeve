"""Tests for hooks/verify_check.py — the SHARED verify-before-commit check.

guard.sh (PreToolUse) and pre-commit.sh (git hook) both call this helper, so it is the one place
the fail-closed rule lives. These tests build a minimal git project, stage a change, and run the
helper exactly as the hooks do (`python3 <helper>` from the repo root), asserting it fails CLOSED
across the two drift vectors that used to leave the old `state.json.current_item` read empty and
silently skip the gate: SHAPE drift (a nested `position.item`) and PATH drift (a relocated
runtime tree via runtime.json).
"""
import json
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent                     # product/scripts
HELPER = HERE.parent / "hooks" / "verify_check.py"         # product/hooks/verify_check.py


def _repo(tmp_path):
    root = tmp_path
    (root / ".workflow" / "items" / "ITEM-1").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    return root


def _state(root, obj):
    (root / ".workflow" / "state.json").write_text(json.dumps(obj))


def _verdict(root, value, item="ITEM-1"):
    (root / ".workflow" / "items" / item / "verify-verdict.md").write_text("pass: %s\nnotes\n" % value)


def _stage(root, item="ITEM-1"):
    (root / ".workflow" / "items" / item / "impl.py").write_text("print(1)\n")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)


def _run(root):
    return subprocess.run(["python3", str(HELPER)], cwd=root, capture_output=True, text=True)


# --- the two reproduced drift vectors: both used to exit 0 (fail open) ---

def test_shape_drift_failing_verdict_blocks(tmp_path):
    # Nested position.item, no top-level current_item, a FAILING verdict.
    root = _repo(tmp_path)
    _state(root, {"status": "building", "position": {"item": "ITEM-1", "node": "execute"}})
    _verdict(root, "false")
    _stage(root)
    r = _run(root)
    assert r.returncode == 1, "shape drift must fail closed"
    assert "FAILING" in r.stdout


def test_path_drift_failing_verdict_blocks(tmp_path):
    # state.json relocated via runtime.json; the old hook read the absent .workflow/state.json.
    root = _repo(tmp_path)
    runtime = tmp_path / "runtime_root"
    runtime.mkdir()
    (runtime / "state.json").write_text(json.dumps({"status": "building", "current_item": "ITEM-1"}))
    (root / ".workflow" / "runtime.json").write_text(json.dumps({"runtime_root": str(runtime)}))
    _verdict(root, "false")
    _stage(root)
    r = _run(root)
    assert r.returncode == 1, "path drift must fail closed"


# --- fail-closed on missing / malformed verdicts ---

def test_missing_verdict_with_staged_item_blocks(tmp_path):
    root = _repo(tmp_path)
    _state(root, {"status": "building", "position": {"item": "ITEM-1"}})
    _stage(root)                                            # no verify-verdict.md written
    r = _run(root)
    assert r.returncode == 1
    assert "no verify-verdict" in r.stdout


def test_reworded_verdict_blocks(tmp_path):
    root = _repo(tmp_path)
    _state(root, {"status": "building", "current_item": "ITEM-1"})
    (root / ".workflow" / "items" / "ITEM-1" / "verify-verdict.md").write_text("PASSED: yes\n")
    _stage(root)
    r = _run(root)
    assert r.returncode == 1, "a non-well-formed first line must not wave through"


def test_building_but_unidentifiable_item_blocks(tmp_path):
    # status=building, no current_item, no position.item, nothing staged under an item dir.
    root = _repo(tmp_path)
    _state(root, {"status": "building"})
    (root / "note.txt").write_text("x\n")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = _run(root)
    assert r.returncode == 1
    assert "no item is identifiable" in r.stdout


# --- legitimate proceeds ---

def test_passing_verdict_nested_shape_proceeds(tmp_path):
    root = _repo(tmp_path)
    _state(root, {"status": "building", "position": {"item": "ITEM-1"}})
    _verdict(root, "true")
    _stage(root)
    r = _run(root)
    assert r.returncode == 0, r.stdout


def test_derives_item_from_staged_diff_without_state(tmp_path):
    # No state.json at all: the staged .workflow/items/<id>/ diff alone identifies the item.
    root = _repo(tmp_path)
    _verdict(root, "false")
    _stage(root)
    r = _run(root)
    assert r.returncode == 1, "a failing item in the staged diff must block even with no state.json"


def test_bootstrap_idle_proceeds(tmp_path):
    root = _repo(tmp_path)
    _state(root, {"status": "idle", "current_item": None})
    (root / ".workflow" / "backlog.md").write_text("scaffold\n")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = _run(root)
    assert r.returncode == 0, r.stdout


def test_no_state_no_staged_item_proceeds(tmp_path):
    # A pure scaffold commit: nothing under an item dir, no active build → nothing to verify.
    root = _repo(tmp_path)
    (root / ".workflow" / "config.json").write_text("{}")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = _run(root)
    assert r.returncode == 0, r.stdout


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
