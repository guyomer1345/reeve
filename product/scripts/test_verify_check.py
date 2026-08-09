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


def test_bootstrap_phase_scaffold_commit_proceeds(tmp_path):
    # /start publishes status=building + phase=bootstrap at every stage boundary, before any
    # item exists. The scaffold commit it then makes must not be blocked as unidentifiable —
    # this used to reject EVERY brownfield bootstrap commit.
    root = _repo(tmp_path)
    _state(root, {"status": "building", "phase": "bootstrap",
                  "node": "start:7", "note": "verifying install (step 7)"})
    (root / ".workflow" / "config.json").write_text("{}")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = _run(root)
    assert r.returncode == 0, r.stdout


def test_bootstrap_carveout_does_not_excuse_a_failing_item(tmp_path):
    # The carve-out only skips the unidentifiable-item block; a staged item with a FAILING
    # verdict still blocks, so it cannot be used to smuggle unverified work past the gate.
    root = _repo(tmp_path)
    _state(root, {"status": "building", "phase": "bootstrap", "node": "start:2"})
    _verdict(root, "false")
    _stage(root)
    r = _run(root)
    assert r.returncode == 1, "bootstrap phase must not wave a failing item through"
    assert "FAILING" in r.stdout


def test_no_state_no_staged_item_proceeds(tmp_path):
    # A pure scaffold commit: nothing under an item dir, no active build → nothing to verify.
    root = _repo(tmp_path)
    (root / ".workflow" / "config.json").write_text("{}")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = _run(root)
    assert r.returncode == 0, r.stdout


def test_bootstrap_phase_building_no_item_proceeds(tmp_path):
    # /start's scaffold/spec commit publishes status=building + phase=bootstrap with no item to verify
    # (the first real item only exists after reconcile->prioritize->plan). The gate must NOT fail closed
    # on it — D133's bootstrap state-publishing meeting the D129 fail-closed gate. Regression for D138.
    root = _repo(tmp_path)
    _state(root, {"status": "building", "phase": "bootstrap", "node": "start:7"})
    (root / ".workflow" / "config.json").write_text("{}")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = _run(root)
    assert r.returncode == 0, r.stdout


def test_building_no_phase_still_blocks(tmp_path):
    # The real drift keeps its teeth: status=building, NO phase, no identifiable item still fails closed.
    root = _repo(tmp_path)
    _state(root, {"status": "building"})
    (root / "note.txt").write_text("x\n")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = _run(root)
    assert r.returncode == 1
    assert "no item is identifiable" in r.stdout


# --- maintenance items: a verify-free motion needs a LEGAL commit, not a faked verdict ---

def _receipt(root, ident, kind="align", item=None, raw=None):
    d = root / ".workflow" / "maintenance"
    d.mkdir(parents=True, exist_ok=True)
    body = raw if raw is not None else json.dumps(
        {"item": ident if item is None else item, "kind": kind, "summary": "scan done"})
    (d / ("%s.json" % ident)).write_text(body)


def _commit_all(root, msg="c"):
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "--no-verify", "-m", msg], cwd=root, check=True)


def test_maintenance_receipt_lets_a_verify_free_item_commit(tmp_path):
    # loop.md § Maintenance items: `align` runs its own pass and flows STRAIGHT to commit — no
    # planner/execute/verify, so there is no verdict to find. Before the receipt this had no legal
    # commit at all: with current_item set the gate demanded a verdict, without it the gate failed
    # closed on an unidentifiable item.
    root = _repo(tmp_path)
    _state(root, {"status": "building", "current_item": "MAINT-1", "node": "align"})
    (root / ".workflow" / "align").mkdir()
    (root / ".workflow" / "align" / "anchor.json").write_text('{"base_sha": "abc"}')
    _receipt(root, "MAINT-1")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = _run(root)
    assert r.returncode == 0, r.stdout


def test_maintenance_item_without_a_receipt_still_blocks(tmp_path):
    # The escape is the published marker, never the ABSENCE of a verdict — which is exactly what a
    # skipped verify looks like too.
    root = _repo(tmp_path)
    _state(root, {"status": "building", "current_item": "MAINT-1", "node": "align"})
    (root / ".workflow" / "align").mkdir()
    (root / ".workflow" / "align" / "anchor.json").write_text('{"base_sha": "abc"}')
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = _run(root)
    assert r.returncode == 1, "no receipt => the maintenance claim was never published"


def test_unstaged_receipt_does_not_exempt(tmp_path):
    # The marker must ride the commit under review. One sitting in the tree unstaged would be a
    # standing exemption for every later commit — the stale-marker hole this design exists to avoid.
    root = _repo(tmp_path)
    _receipt(root, "MAINT-1")
    _commit_all(root, "receipt lands")
    _state(root, {"status": "building", "current_item": "MAINT-1"})
    (root / "note.txt").write_text("x\n")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = _run(root)
    assert r.returncode == 1, "a receipt from an earlier commit must not exempt this one"


def test_unknown_kind_receipt_is_rejected_and_named(tmp_path):
    root = _repo(tmp_path)
    _state(root, {"status": "building"})
    _receipt(root, "MAINT-1", kind="execute")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = _run(root)
    assert r.returncode == 1, "only the loop's maintenance nodes may claim the exemption"
    assert "Rejected receipt" in r.stdout and "execute" in r.stdout


def test_receipt_not_matching_its_filename_is_rejected(tmp_path):
    root = _repo(tmp_path)
    _state(root, {"status": "building"})
    _receipt(root, "MAINT-1", item="ITEM-9")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = _run(root)
    assert r.returncode == 1
    assert "does not match its filename" in r.stdout


def test_unparseable_receipt_is_rejected(tmp_path):
    root = _repo(tmp_path)
    _state(root, {"status": "building"})
    _receipt(root, "MAINT-1", raw="not json at all")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = _run(root)
    assert r.returncode == 1
    assert "not readable JSON" in r.stdout


def test_receipt_does_not_excuse_a_staged_item_dir(tmp_path):
    # A maintenance commit that ALSO stages a built item dir still has that item's verdict checked:
    # `planner` mkdirs the dir, so something was built under it, and a built item is verified.
    root = _repo(tmp_path)
    _state(root, {"status": "building", "current_item": "MAINT-1"})
    _receipt(root, "MAINT-1")
    _verdict(root, "false")
    _stage(root)
    r = _run(root)
    assert r.returncode == 1, "the receipt exempts the maintenance item, never a built one"
    assert "FAILING" in r.stdout


def test_pruned_item_dir_does_not_read_as_an_unverified_item(tmp_path):
    # `document:audit`'s retention prune DELETES closed item dirs. Deleted paths are still listed by
    # `git diff --cached --name-only`, so the prune used to re-derive every dir it had just deleted
    # as an item under commit and block on the verdict it was deleting.
    root = _repo(tmp_path)
    _verdict(root, "true")
    _stage(root)
    _commit_all(root, "item lands")
    subprocess.run(["git", "rm", "-r", "-q", ".workflow/items/ITEM-1"], cwd=root, check=True)
    r = _run(root)
    assert r.returncode == 0, r.stdout


def test_prune_ridden_maintenance_commit_proceeds(tmp_path):
    # The whole `document:audit` shape at once: a prune deletion plus its own receipt, mid-build.
    root = _repo(tmp_path)
    _verdict(root, "true")
    _stage(root)
    _commit_all(root, "item lands")
    _state(root, {"status": "building", "current_item": "MAINT-2", "node": "document:audit"})
    subprocess.run(["git", "rm", "-r", "-q", ".workflow/items/ITEM-1"], cwd=root, check=True)
    _receipt(root, "MAINT-2", kind="document:audit")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    r = _run(root)
    assert r.returncode == 0, r.stdout


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
