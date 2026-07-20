"""Tests for templates/checks.sh — the SHIPPED FIXED per-item mechanical gate.

The runner is copied verbatim into each project as `.workflow/checks.sh`; the only
per-project input is `.workflow/checks.env` (stack commands). These tests build a minimal
project tree (checks.sh + checks.env + the real coverage-gate scripts + a promises.json),
run the runner as the git hook and the commit skill do, and assert the gate behaviour.
Stack commands are stubbed (`true` / `false` / a logging script) so the tests need no real
formatter or test runner installed.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent            # product/scripts
RUNNER_SRC = HERE.parent / "templates" / "checks.sh"
COVERAGE_SCRIPTS = (
    "check_promise_coverage.py",
    "check_criterion_discharge.py",
    "check_decision_coverage.py",
)


def _project(tmp_path, checks_env="", promises=None):
    """Lay out a minimal bootstrapped project and return its root."""
    root = tmp_path
    (root / ".workflow").mkdir()
    (root / ".claude" / "scripts").mkdir(parents=True)
    shutil.copy(RUNNER_SRC, root / ".workflow" / "checks.sh")
    for s in COVERAGE_SCRIPTS:
        shutil.copy(HERE / s, root / ".claude" / "scripts" / s)
    (root / ".workflow" / "checks.env").write_text(checks_env)
    if promises is not None:
        item = root / ".workflow" / "items" / "itm-1"
        item.mkdir(parents=True)
        (item / "promises.json").write_text(json.dumps(promises))
    return root


def _run(root, *args):
    return subprocess.run(
        ["bash", ".workflow/checks.sh", *args],
        cwd=root, capture_output=True, text=True,
    )


# A promises.json that satisfies all three coverage gates.
GOOD_PROMISES = {
    "criteria": [{"id": "ac-1", "gate": "artifact", "boundary": True, "discharge": "tests/t.py::t"}],
    "promises": [{"id": "p1", "text": "any x", "universal": True, "test_ref": "ac-1"}],
    "decisions": [{"id": "D-001", "steps": ["s1"]}],
}


def test_check_passes_clean_project(tmp_path):
    root = _project(tmp_path, "FMT_CHECK=true\nLINT=true\nTEST=true\n", GOOD_PROMISES)
    r = _run(root, "--check")
    assert r.returncode == 0, r.stderr


def test_check_no_stack_no_items_passes(tmp_path):
    # Empty checks.env and no open items: nothing to run, clean pass.
    root = _project(tmp_path, "")
    r = _run(root, "--check")
    assert r.returncode == 0, r.stderr


def test_check_fails_on_failing_stack_command(tmp_path):
    root = _project(tmp_path, "FMT_CHECK=true\nTEST=false\n", GOOD_PROMISES)
    r = _run(root, "--check")
    assert r.returncode != 0


def test_check_fails_on_unlinked_promise(tmp_path):
    bad = {"criteria": [], "promises": [{"id": "p1", "text": "x", "universal": False}]}
    root = _project(tmp_path, "", bad)   # no test_ref -> promise-coverage gate blocks
    r = _run(root, "--check")
    assert r.returncode != 0


def test_check_fails_on_decision_mapped_to_no_step(tmp_path):
    bad = {"decisions": [{"id": "D-001", "steps": []}]}
    root = _project(tmp_path, "", bad)
    r = _run(root, "--check")
    assert r.returncode != 0


def test_check_fails_on_malformed_promises_json(tmp_path):
    root = _project(tmp_path, "")
    item = root / ".workflow" / "items" / "itm-x"
    item.mkdir(parents=True)
    (item / "promises.json").write_text("{ not valid json ")
    r = _run(root, "--check")
    assert r.returncode != 0    # a broken manifest must block, not silently skip


def test_check_iterates_multiple_items(tmp_path):
    root = _project(tmp_path, "", GOOD_PROMISES)   # itm-1 good
    bad = {"decisions": [{"id": "D-002", "steps": []}]}
    item2 = root / ".workflow" / "items" / "itm-2"
    item2.mkdir(parents=True)
    (item2 / "promises.json").write_text(json.dumps(bad))
    r = _run(root, "--check")
    assert r.returncode != 0    # one bad item among many still fails the gate


def test_cd_ing_stack_command_does_not_skip_coverage_gates(tmp_path):
    # A natural stack command like `cd project && pytest` must NOT change the runner's CWD
    # and silently bypass the coverage-gate loop. Regression for a bug found by driving.
    bad = {"decisions": [{"id": "D-001", "steps": []}]}   # would fail the decision gate
    root = _project(tmp_path, 'TEST="cd .claude && true"\n', bad)
    r = _run(root, "--check")
    assert r.returncode != 0, "cd in a stack command let the coverage gates be skipped"


def test_fix_passes_staged_files_to_fixer(tmp_path):
    # A logging stub stands in for the formatter; prove the file list reaches it verbatim.
    root = _project(tmp_path, "")
    logger = root / "fixlog.sh"
    logger.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" >> "$PWD/fixed.txt"\n')
    logger.chmod(0o755)
    (root / ".workflow" / "checks.env").write_text(f'FMT_FIX="bash {logger}"\n')
    r = _run(root, "--fix", "a.py", "b.py")
    assert r.returncode == 0, r.stderr
    logged = (root / "fixed.txt").read_text().split()
    assert logged == ["a.py", "b.py"]


def test_fix_with_no_files_is_noop(tmp_path):
    # --fix with no file args must not sweep the repo (formatter never invoked bare).
    root = _project(tmp_path, 'FMT_FIX="false"\n')   # would fail if invoked
    r = _run(root, "--fix")
    assert r.returncode == 0


def test_unknown_mode_errors(tmp_path):
    root = _project(tmp_path, "")
    r = _run(root, "--wat")
    assert r.returncode == 2


def test_no_mode_errors(tmp_path):
    root = _project(tmp_path, "")
    r = _run(root)
    assert r.returncode == 2


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
