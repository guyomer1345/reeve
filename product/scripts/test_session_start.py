"""Tests for hooks/session_start.py — the auto-rehydrate hook and the pre-commit assert.

Runs the hook as Claude Code does (`python3 session_start.py` with the SessionStart JSON on
stdin) and asserts it emits the `hookSpecificOutput.additionalContext` contract carrying
`.workflow/handoff.md`, stays silent when there is nothing to rehydrate, and never errors out.

The second half — re-asserting `.git/hooks/pre-commit` — drives real files, because its two
interesting failures are file-shaped: clobbering somebody else's hook, and warning about the
same foreign hook on every single session start.
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


def test_rehydrate_is_clear_only(tmp_path):
    """A fresh `startup` must not inject the whole handoff — the assert runs on every
    source, but rehydrating everywhere would be a different (and noisy) feature."""
    _handoff(tmp_path, "# Handoff\ncurrent_item: ITEM-7\n")
    assert _run(tmp_path, source="startup").stdout.strip() == ""
    assert "ITEM-7" in _run(tmp_path, source="clear").stdout


# --- re-asserting the git pre-commit backstop --------------------------------
HOOK_BODY = "#!/usr/bin/env bash\necho package-backstop\n"


def _project(tmp_path, installed=None, git=True):
    """A bootstrapped project: the package's hook source, and optionally a .git/."""
    src = tmp_path / ".claude" / "hooks"
    src.mkdir(parents=True)
    (src / "pre-commit.sh").write_text(HOOK_BODY)
    if git:
        (tmp_path / ".git" / "hooks").mkdir(parents=True)
        if installed is not None:
            (tmp_path / ".git" / "hooks" / "pre-commit").write_text(installed)
    return tmp_path / ".git" / "hooks" / "pre-commit"


def test_absent_hook_is_installed_and_reported(tmp_path):
    """`.git/hooks/` is not part of the repository, so every CLONE of a bootstrapped
    project arrives with the gate silently absent — and a clone runs neither /start nor
    /rebind. A session start is the one event that does fire."""
    dst = _project(tmp_path)
    r = _run(tmp_path, source="startup")
    assert r.returncode == 0
    assert dst.read_text() == HOOK_BODY
    ac = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "Installed the git pre-commit backstop" in ac


def test_an_identical_hook_is_silent(tmp_path):
    dst = _project(tmp_path, installed=HOOK_BODY)
    r = _run(tmp_path, source="startup")
    assert r.stdout.strip() == ""
    assert dst.read_text() == HOOK_BODY


def test_a_foreign_hook_is_never_clobbered(tmp_path):
    """Overwriting somebody else's hook to install our own is exactly the unasked-for,
    hard-to-notice side effect this project refuses to ship."""
    foreign = "#!/bin/sh\n# somebody else's hook\nexit 0\n"
    dst = _project(tmp_path, installed=foreign)
    r = _run(tmp_path, source="startup")
    assert dst.read_text() == foreign
    ac = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "FOREIGN" in ac
    assert "Nothing was overwritten" in ac


def test_the_foreign_warning_fires_once_not_every_session(tmp_path):
    _project(tmp_path, installed="#!/bin/sh\nexit 0\n")
    assert "FOREIGN" in _run(tmp_path, source="startup").stdout
    assert _run(tmp_path, source="startup").stdout.strip() == ""
    assert _run(tmp_path, source="startup").stdout.strip() == ""


def test_a_changed_foreign_hook_warns_again(tmp_path):
    """The marker is keyed by the foreign hook's hash: a DIFFERENT foreign hook is new
    information, and silence there would be the warning going stale."""
    dst = _project(tmp_path, installed="#!/bin/sh\nexit 0\n")
    _run(tmp_path, source="startup")
    dst.write_text("#!/bin/sh\n# a different foreign hook\nexit 0\n")
    assert "FOREIGN" in _run(tmp_path, source="startup").stdout


def test_installing_after_a_warning_clears_the_marker(tmp_path):
    """A project that removes the foreign hook must get the backstop installed AND be
    told — not stay silent because a stale marker says it was already warned."""
    dst = _project(tmp_path, installed="#!/bin/sh\nexit 0\n")
    _run(tmp_path, source="startup")
    dst.unlink()
    assert "Installed the git" in _run(tmp_path, source="startup").stdout
    assert dst.read_text() == HOOK_BODY
    # …and having installed it, it goes quiet again.
    assert _run(tmp_path, source="startup").stdout.strip() == ""


def test_a_non_git_directory_is_left_alone(tmp_path):
    _project(tmp_path, git=False)
    r = _run(tmp_path, source="startup")
    assert r.stdout.strip() == ""
    assert not (tmp_path / ".git").exists()


def test_a_project_without_the_package_half_is_left_alone(tmp_path):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    r = _run(tmp_path, source="startup")
    assert r.stdout.strip() == ""
    assert not (tmp_path / ".git" / "hooks" / "pre-commit").exists()


def test_the_assert_runs_on_clear_too_and_composes_with_the_rehydrate(tmp_path):
    dst = _project(tmp_path)
    _handoff(tmp_path, "# Handoff\ncurrent_item: ITEM-7\n")
    ac = json.loads(_run(tmp_path, source="clear").stdout)[
        "hookSpecificOutput"]["additionalContext"]
    assert "Installed the git pre-commit backstop" in ac
    assert "ITEM-7" in ac
    assert dst.read_text() == HOOK_BODY


def test_assert_hook_cli_is_the_same_code_path_for_rebind(tmp_path):
    """`/rebind` re-asserts the backstop by calling THIS, not by re-describing the
    three-way in prose — a rule with two owners is a rule that drifts."""
    dst = _project(tmp_path)
    r = subprocess.run(["python3", str(HOOK), "--assert-hook"], cwd=tmp_path,
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert "Installed the git pre-commit backstop" in r.stdout
    assert dst.read_text() == HOOK_BODY
    r2 = subprocess.run(["python3", str(HOOK), "--assert-hook"], cwd=tmp_path,
                        capture_output=True, text=True)
    assert r2.stdout.strip() == ""


def test_an_uninstallable_hook_reports_rather_than_wedging_the_session(tmp_path):
    import os
    import stat
    hooks = _project(tmp_path).parent
    os.chmod(hooks, stat.S_IRUSR | stat.S_IXUSR)  # readable, not writable
    try:
        r = _run(tmp_path, source="startup")
        assert r.returncode == 0
        if r.stdout.strip():  # a filesystem that actually enforces the mode
            assert "could not be installed" in r.stdout
    finally:
        os.chmod(hooks, stat.S_IRWXU)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
