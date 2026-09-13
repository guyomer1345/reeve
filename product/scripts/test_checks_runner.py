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
# Every script the shipped `checks.sh` invokes. The three coverage gates run per open item
# (glob-guarded, so an empty tree skips them); `check_doc_budget.py` runs UNCONDITIONALLY on
# every `--check`, which is why it has to be present here for even the empty-tree cases to
# pass. That is not a fixture quirk — it is the dependency the runner really has, and both
# files are package-owned so `/update` refreshes them together. `check_directives.py` is the
# same shape: unconditional, and it passes cleanly with no `.workflow/directives.md` present
# (a project may simply have no standing directives).
COVERAGE_SCRIPTS = (
    "check_promise_coverage.py",
    "check_criterion_discharge.py",
    "check_decision_coverage.py",
    "check_doc_budget.py",
    "check_directives.py",
    # Not a coverage gate: the wave build slot, invoked once per `--check` that has stack
    # commands to run. It belongs in this fixture for the same reason the two above do — it is
    # a dependency the shipped runner really has, and a tree without it must still gate, by
    # falling toward building. Its absence is silently safe, which is exactly why a test tree
    # that omitted it would be testing the fallback forever without saying so.
    "wave_build.py",
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


def _git_project(tmp_path, checks_env="", project_files=None):
    """A bootstrapped project inside a real git repo (the backstop reads `git ls-files`)."""
    root = _project(tmp_path, checks_env)
    (root / ".workflow" / "config.json").write_text(json.dumps({"project_root": "./project"}))
    proj = root / "project"
    proj.mkdir()
    for name, body in (project_files or {}).items():
        (proj / name).write_text(body)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return root


def test_check_blocks_source_without_stack_gate(tmp_path):
    # F2 backstop: source under project_root but no --check stack command wired is the silent
    # stack-gate defeat (a greenfield stack locks but nothing fills checks.env). Must fail closed.
    root = _git_project(tmp_path, "", {"mod.py": "def add(a, b):\n    return a + b\n"})
    r = _run(root, "--check")
    assert r.returncode != 0, "source with an empty checks.env must fail the gate, not skip it"
    assert "no stack gate" in r.stderr


def test_check_allows_empty_project_without_stack_gate(tmp_path):
    # The bootstrap window: project_root has no source yet (only docs). Nothing to gate → pass.
    root = _git_project(tmp_path, "", {"README.md": "# spec\n"})
    r = _run(root, "--check")
    assert r.returncode == 0, r.stderr


def test_check_allows_source_once_stack_gate_wired(tmp_path):
    # Once checks.env wires a --check command, the backstop is silent (no false block).
    root = _git_project(tmp_path, "TEST=true\n", {"mod.py": "def add(a, b):\n    return a + b\n"})
    r = _run(root, "--check")
    assert r.returncode == 0, r.stderr


def test_backstop_no_ops_when_project_root_is_outside_the_repo(tmp_path):
    """The backstop's REACH, pinned as a regression. `git ls-files -- <abs path outside the
    repo>` exits 128 with empty stdout (the 2>/dev/null swallows the fatal), so the gate
    silently no-ops rather than blocking. This is the shipped, intended limit — and it is the
    reason org mode keeps the brain and the code in ONE repo (project_root ".") instead of
    pointing project_root at a tree elsewhere on the machine. If this test ever starts
    failing, the backstop grew reach and that topology constraint can be revisited."""
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    (outside / "mod.py").write_text("def add(a, b):\n    return a + b\n")
    root = _git_project(tmp_path, "", {"README.md": "# spec\n"})
    (root / ".workflow" / "config.json").write_text(json.dumps({"project_root": str(outside)}))
    r = _run(root, "--check")
    assert r.returncode == 0, r.stderr
    assert "no stack gate" not in r.stderr


def test_not_yet_wired_block_points_at_the_third_state(tmp_path):
    # The two states are told apart by the operator, so the loud one has to name the other.
    root = _git_project(tmp_path, "", {"mod.py": "def add(a, b):\n    return a + b\n"})
    r = _run(root, "--check")
    assert r.returncode != 0
    assert "STACK_GATE_NONE" in r.stderr


# --- state 3: the stack gate is off BY DECLARATION -------------------------------------
NONE_DECL = 'STACK_GATE_NONE="org mode: never execute anything out of the checkout"\n'


def test_declared_none_passes_with_source_present(tmp_path):
    """The deadlock this state exists to break: source under project_root and no stack gate
    is state 2 (block), but the same tree with a declaration is state 3 (proceed). Without
    this, org mode's first commit could never be made."""
    root = _git_project(tmp_path, NONE_DECL, {"mod.py": "def add(a, b):\n    return a + b\n"})
    r = _run(root, "--check")
    assert r.returncode == 0, r.stderr
    assert "DECLARED NONE" in r.stderr
    assert "never execute anything out of the checkout" in r.stderr   # the reason, every run


def test_declared_none_still_runs_the_coverage_gates(tmp_path):
    # Declaring the EXECUTABLE gate off must not disarm the stack-agnostic ones.
    bad = {"decisions": [{"id": "D-001", "steps": []}]}
    root = _project(tmp_path, NONE_DECL, bad)
    r = _run(root, "--check")
    assert r.returncode != 0, "the declaration must only cover checks.env, not the coverage gates"


def test_declared_none_refuses_to_execute_a_wired_check_command(tmp_path):
    """The structural half: a later re-wire (a re-run of /start's brownfield stack adoption)
    must not silently re-arm arbitrary code execution. The declaration wins, and says so."""
    root = _project(tmp_path, "")
    (root / ".workflow" / "checks.env").write_text(
        NONE_DECL + f'TEST="touch {root / "EXECUTED"}"\n')
    r = _run(root, "--check")
    assert r.returncode == 0, r.stderr
    assert not (root / "EXECUTED").exists(), "a declared-none tree executed a checks.env command"
    assert "REFUSED" in r.stderr and "TEST" in r.stderr


def test_declared_none_refuses_the_fixers_too(tmp_path):
    # FMT_FIX/LINT_FIX are `eval`'d exactly like the --check commands, so --fix is the same hole.
    root = _project(tmp_path, "")
    (root / ".workflow" / "checks.env").write_text(
        NONE_DECL + f'FMT_FIX="touch {root / "FIXED"}"\n')
    r = _run(root, "--fix", "a.py")
    assert r.returncode == 0, r.stderr
    assert not (root / "FIXED").exists(), "a declared-none tree ran a fixer"
    assert "DECLARED NONE" in r.stderr


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


def test_the_doc_budget_gate_blocks_a_commit_over_the_hard_wall(tmp_path):
    """The WIRING, not the script (which has its own tests). An on-demand doc past the
    25 000-token Read ceiling cannot be loaded in one call at all, so it fails the gate."""
    root = _git_project(tmp_path, "TEST='true'", {"README.md": "# spec\n"})
    docs = root / "project" / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "spec.md").write_text("x" * (26000 * 4))     # far past the wall at any ratio
    r = _run(root, "--check")
    assert r.returncode != 0
    assert "OVER BUDGET" in r.stdout and "docs/spec.md" in r.stdout


def test_an_advisory_alone_never_blocks_a_commit(tmp_path):
    """The whole reason for two tiers: the always-loaded aspiration is a scheduled trim, and
    a gate that failed a commit over one would be a gate people route around. The package's
    own shipped brief and loop.md sit in exactly this band."""
    root = _git_project(tmp_path, "TEST='true'", {"README.md": "# spec\n"})
    (root / "CLAUDE.md").write_text("x" * (3300 * 3))     # over advisory, under hard
    r = _run(root, "--check")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OVER BUDGET" not in r.stdout


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


def test_fix_never_hands_the_loops_own_runtime_to_a_code_formatter(tmp_path):
    """MEASURED on a drive: the commit skill scopes `--fix` to the item's staged files, and
    those include `.workflow/items/<id>/promises.json`. `ruff format` force-parses an
    explicitly-named file as Python whatever its extension, and wrote a magic trailing comma
    into the manifest — invalid JSON, and the coverage gates that read it then refuse the
    commit. A formatter has no business in `.workflow/` for any stack."""
    root = _project(tmp_path, "")
    logger = root / "fixlog.sh"
    logger.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" >> "$PWD/fixed.txt"\n')
    logger.chmod(0o755)
    (root / ".workflow" / "checks.env").write_text(f'FMT_FIX="bash {logger}"\n')
    r = _run(root, "--fix", "a.py", ".workflow/items/IT-1/promises.json",
             "./.claude/settings.json", "src/b.py")
    assert r.returncode == 0, r.stderr
    assert (root / "fixed.txt").read_text().split() == ["a.py", "src/b.py"]
    assert "promises.json" in r.stderr          # named, never silently dropped


def test_fix_with_only_runtime_files_never_invokes_the_fixer_at_all(tmp_path):
    root = _project(tmp_path, 'FMT_FIX="false"\n')   # would fail the run if invoked
    r = _run(root, "--fix", ".workflow/items/IT-1/promises.json")
    assert r.returncode == 0


# --- the wave build slot: "build once per wave" as a mechanism --------------------------
# The two acts these tests keep apart: a worker running the project's tests inside its own
# worktree to check its OWN work (unbounded, untouched, not exercised here), and the
# AUTHORITATIVE gate a commit hangs on — `checks.sh --check`, which is what takes the slot.


def _counting_build(tmp_path, exit_code=0):
    """A stack TEST command that records each invocation OUTSIDE the repo.

    Outside is load-bearing rather than tidy: a log written inside the tree would change the
    tree's own fingerprint on every run, so the memo could never hit and these tests would
    pass for entirely the wrong reason.
    """
    outside = tmp_path.parent / (tmp_path.name + "-build")
    outside.mkdir(exist_ok=True)
    log = outside / "runs.txt"
    script = outside / "build.sh"
    script.write_text('#!/usr/bin/env bash\necho run >> "%s"\nexit %d\n' % (log, exit_code))
    return 'TEST="bash %s"\n' % script, log


def _runs(log):
    return len(log.read_text().split()) if log.exists() else 0


def _wave_project(tmp_path, checks_env, wave):
    """A git project whose `state.json` names a wave — and gitignores it, as /start does.

    The gitignore is not decoration. An untracked, unignored `state.json` would be part of
    the tree fingerprint, so flipping the wave id would change the KEY as well as the wave
    and the new-wave test would pass without the wave ever being read.
    """
    root = _git_project(tmp_path, checks_env, {"README.md": "# spec\n"})
    (root / ".gitignore").write_text(".workflow/state.json\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=root, check=True)
    _set_wave(root, wave)
    return root


def _set_wave(root, wave):
    (root / ".workflow" / "state.json").write_text(
        json.dumps({"status": "building", "current_item": None, "wave": wave}))


def _slot_paths(root):
    return (root / ".git" / "reeve-wave-build.lock", root / ".git" / "reeve-wave-build.json")


def test_a_wave_of_one_builds_every_time_exactly_as_before(tmp_path):
    """The degenerate case, which is still the common one. `wave: null` names no wave, so
    there is no key, so there is no memo — the gate runs on every commit exactly as it did
    before the slot existed. It pays one uncontended flock and nothing else."""
    env, log = _counting_build(tmp_path)
    root = _wave_project(tmp_path, env, None)
    assert _run(root, "--check").returncode == 0
    assert _run(root, "--check").returncode == 0
    assert _runs(log) == 2, "a wave of one must not start reusing a verdict"


def test_the_same_wave_never_re_gates_an_unchanged_tree(tmp_path):
    """The mechanism itself: inside one wave, a second authoritative gate over a
    byte-identical tree is not run — re-running it could not produce a different answer. This
    is the duplicate the loop pays today on EVERY item, since the commit skill runs `--check`
    and then the git hook runs it again over the same tree."""
    env, log = _counting_build(tmp_path)
    root = _wave_project(tmp_path, env, "wave-1")
    assert _run(root, "--check").returncode == 0
    second = _run(root, "--check")
    assert second.returncode == 0, second.stderr
    assert _runs(log) == 1, "the same wave re-gated a tree state it had already passed"
    assert "SKIPPING the stack gate" in second.stderr   # never silent about a skipped build


def test_a_changed_tree_is_re_gated_inside_the_same_wave(tmp_path):
    # The memo is a cache with an exact key, never a permission slip: a changed tree is a
    # different question, and gets asked.
    env, log = _counting_build(tmp_path)
    root = _wave_project(tmp_path, env, "wave-1")
    assert _run(root, "--check").returncode == 0
    (root / "project" / "mod.py").write_text("def add(a, b):\n    return a + b\n")
    assert _run(root, "--check").returncode == 0
    assert _runs(log) == 2, "a changed tree reused a verdict that was never about it"


def test_a_new_wave_drops_the_memo(tmp_path):
    # The wave id bounds the memo's life. A tree state can recur across waves (a revert, a
    # branch switch) and a cache that outlived its wave would answer a question nobody asked.
    env, log = _counting_build(tmp_path)
    root = _wave_project(tmp_path, env, "wave-1")
    assert _run(root, "--check").returncode == 0
    _set_wave(root, "wave-2")
    assert _run(root, "--check").returncode == 0
    assert _runs(log) == 2, "a later wave inherited an earlier wave's verdict"


def test_a_failing_gate_is_never_memoized(tmp_path):
    """Only passes are remembered. The commonest red stack gate is a machine that never got
    the toolchain `checks.env` names — repaired without changing a byte of the tree, so a
    remembered failure would keep reporting the old verdict after the cure."""
    env, log = _counting_build(tmp_path, exit_code=1)
    root = _wave_project(tmp_path, env, "wave-1")
    assert _run(root, "--check").returncode != 0
    assert _run(root, "--check").returncode != 0
    assert _runs(log) == 2, "a failure was memoized; the machine-repair case is now unfixable"


def test_an_unreadable_marker_falls_toward_building(tmp_path):
    # The fail direction, proven: if the wave-build state cannot be read, the answer is
    # "build again" (wasteful, correct), never "skip it" (fast, unverified).
    env, log = _counting_build(tmp_path)
    root = _wave_project(tmp_path, env, "wave-1")
    assert _run(root, "--check").returncode == 0
    _, marker = _slot_paths(root)
    marker.write_text("{ not json at all")
    r = _run(root, "--check")
    assert r.returncode == 0, r.stderr
    assert _runs(log) == 2
    assert "marker unreadable" in r.stderr    # reported, never a silent rebuild forever


def test_two_concurrent_authoritative_gates_never_overlap(tmp_path):
    """The collision this exists to stop. The stack command takes a lock of its own (an
    atomic mkdir OUTSIDE the repo) and fails if anyone else holds it, so an overlap is a red
    gate rather than a judgement call. `wave: null` deliberately disables the memo here: both
    runs must really build, which is what leaves the exclusion as the only thing under test."""
    outside = tmp_path.parent / (tmp_path.name + "-slot")
    outside.mkdir(exist_ok=True)
    script = outside / "build.sh"
    script.write_text('#!/usr/bin/env bash\nmkdir "%s/busy" || exit 1\nsleep 0.5\n'
                      'rmdir "%s/busy"\n' % (outside, outside))
    root = _wave_project(tmp_path, 'TEST="bash %s"\n' % script, None)
    procs = [subprocess.Popen(["bash", ".workflow/checks.sh", "--check"], cwd=root,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
             for _ in range(2)]
    results = [(p.wait(timeout=120), p.communicate()) for p in procs]
    assert [rc for rc, _ in results] == [0, 0], \
        "two authoritative gates ran at once: %r" % (results,)


def test_the_slot_leaves_nothing_in_the_working_tree(tmp_path):
    """Why the anchor is the common git dir and not `.workflow/`: a lock there would need a
    `.gitignore` line to earn, and a lock inside a per-ticket worktree could not be contended
    on at all. Inside `.git/` it is uncommittable by construction."""
    env, _log = _counting_build(tmp_path)
    root = _wave_project(tmp_path, env, "wave-1")
    assert _run(root, "--check").returncode == 0
    lock, marker = _slot_paths(root)
    assert lock.exists() and marker.exists()
    dirty = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=root,
                           capture_output=True, text=True).stdout
    assert "reeve-wave-build" not in dirty


def test_no_stack_commands_means_no_slot_at_all(tmp_path):
    # No ceremony where there is nothing to serialize: a coverage-only gate never reaches for
    # git, flock or the marker.
    root = _wave_project(tmp_path, "", "wave-1")
    assert _run(root, "--check").returncode == 0
    lock, marker = _slot_paths(root)
    assert not lock.exists() and not marker.exists()


def test_fix_never_takes_the_build_slot(tmp_path):
    # `--fix` is a worker repairing its own staged files in its own worktree — the other side
    # of the line. It is not the authoritative gate and must not queue behind one.
    root = _wave_project(tmp_path, 'FMT_FIX="true"\nTEST="true"\n', "wave-1")
    assert _run(root, "--fix", "a.py").returncode == 0
    lock, _marker = _slot_paths(root)
    assert not lock.exists()


def test_a_chmod_alone_re_gates_the_tree(tmp_path):
    """The narrow case the content hash alone would miss: `chmod +x` on a file the gate runs
    changes what the gate DOES while changing no byte of it. The index carries mode for
    tracked files; the fingerprint carries it for the worktree side too."""
    env, log = _counting_build(tmp_path)
    root = _wave_project(tmp_path, env, "wave-1")
    hook = root / "project" / "hook.sh"
    hook.write_text("#!/usr/bin/env bash\ntrue\n")
    assert _run(root, "--check").returncode == 0
    assert _runs(log) == 1
    hook.chmod(0o755)
    assert _run(root, "--check").returncode == 0
    assert _runs(log) == 2, "a mode-only change reused a verdict taken before it"
