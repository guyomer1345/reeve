"""Tests for scripts/loop.sh — the orchestrator launcher's lock discipline.

loop.sh publishes a live orchestrator by holding an `flock` for the session's whole lifetime, so
the relaunch-runner can tell "someone is driving" from "nobody is". Two very different conditions
both prevent that, and the launcher used to report them identically:

  * the lock is genuinely HELD by another session  -> "an orchestrator already holds ..."
  * `flock` DOES NOT EXIST on this system         -> exit 127, which `if ! flock -n 9` inverted
                                                     into the same "already holds" branch

The second is the native-Windows case: Git for Windows' bash ships no `flock`. The refusal was
right, but the diagnosis sent the operator to hunt a session that does not exist, on a machine
where the launcher can never work. These tests pin the two apart, and pin the refusal itself --
declining to start is the safety property (two orchestrators would silently clobber one
`.workflow/`), so a "fix" that proceeded without a lock would be a regression, not an improvement.

The absent-`flock` case is built with a PATH containing ONLY symlinks to the utilities loop.sh
needs. That matters: an earlier version of this test put a stub directory ahead of the system
PATH, which still resolved `/usr/bin/flock`, so the test passed while proving nothing. The
`test_the_harness_can_actually_hide_flock` guard below exists so that cannot happen silently
again -- a harness that cannot fail is not evidence.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent                 # product/scripts
LOOP = HERE / "loop.sh"

# What loop.sh actually reaches for, beyond bash builtins.
NEEDED = ("bash", "sh", "dirname", "mkdir", "cat")


def _sandbox(tmp_path, *, with_flock):
    """A project + a PATH holding only what loop.sh needs (optionally including flock)."""
    binv, proj = tmp_path / "bin", tmp_path / "proj"
    (proj / ".workflow").mkdir(parents=True)
    binv.mkdir()

    for util in NEEDED:
        src = shutil.which(util)
        if src is None:                                # pragma: no cover - platform floor
            pytest.skip(f"{util} unavailable")
        (binv / util).symlink_to(src)
    if with_flock:
        src = shutil.which("flock")
        if src is None:
            pytest.skip("flock unavailable on this platform")
        (binv / "flock").symlink_to(src)

    lock = proj / ".workflow" / "orchestrator.lock"
    # Stand in for the real bus.py Paths resolution, which is not what these tests are about.
    (binv / "python3").write_text(f'#!/bin/sh\necho "{lock}"\n')
    (binv / "python3").chmod(0o755)
    # `exec claude` must succeed for the happy path to be observable.
    (binv / "claude").write_text('#!/bin/sh\necho CLAUDE_STARTED\n')
    (binv / "claude").chmod(0o755)

    shutil.copy(LOOP, binv / "loop.sh")
    return binv, proj, lock


def _run(binv, proj):
    return subprocess.run(
        [str(binv / "bash"), str(binv / "loop.sh")],
        cwd=proj, env={"PATH": str(binv)},
        capture_output=True, text=True,
    )


def test_the_harness_can_actually_hide_flock(tmp_path):
    """Guard the guard: if this PATH still resolves flock, every absence test below is vacuous."""
    binv, _, _ = _sandbox(tmp_path, with_flock=False)
    probe = subprocess.run(
        [str(binv / "bash"), "-c", "command -v flock"],
        env={"PATH": str(binv)}, capture_output=True, text=True,
    )
    assert probe.returncode != 0, f"harness leaked a real flock at {probe.stdout!r}"


def test_missing_flock_refuses_to_start(tmp_path):
    """The safety property survives: no lock published => no orchestrator started."""
    binv, proj, _ = _sandbox(tmp_path, with_flock=False)
    r = _run(binv, proj)
    assert r.returncode == 1
    assert "CLAUDE_STARTED" not in r.stdout


def test_missing_flock_does_not_claim_another_orchestrator_is_running(tmp_path):
    """The whole point: name the real cause, and explicitly deny the wrong one."""
    binv, proj, _ = _sandbox(tmp_path, with_flock=False)
    err = _run(binv, proj).stderr
    assert "flock" in err and "not available" in err
    assert "NOT 'another orchestrator is running'" in err
    # The misleading line from the old behaviour must not appear.
    assert "already holds" not in err


@pytest.mark.skipif(shutil.which("flock") is None, reason="flock unavailable")
def test_free_lock_starts_the_orchestrator(tmp_path):
    binv, proj, _ = _sandbox(tmp_path, with_flock=True)
    r = _run(binv, proj)
    assert r.returncode == 0
    assert "CLAUDE_STARTED" in r.stdout


@pytest.mark.skipif(shutil.which("flock") is None, reason="flock unavailable")
def test_held_lock_still_reports_a_held_lock(tmp_path):
    """The genuine contention case keeps its own, different message."""
    binv, proj, lock = _sandbox(tmp_path, with_flock=True)
    fd = os.open(lock, os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        subprocess.run([str(binv / "flock"), "-n", str(fd)], pass_fds=(fd,), check=True)
        r = _run(binv, proj)
        assert r.returncode == 1
        assert "already holds" in r.stderr
        assert "not available" not in r.stderr
        assert "CLAUDE_STARTED" not in r.stdout
    finally:
        os.close(fd)
