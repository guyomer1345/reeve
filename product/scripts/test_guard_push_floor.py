"""Tests for hooks/guard.sh — the protected-branch push floor.

guard.sh is the Layer-1 hard floor: it is the one gate with no approve-and-proceed path, so a
regression here is silent and expensive. It had no test coverage at all until the floor became
lowerable per-project via `guard.allow_protected_push` (schemas.md § config.json → guard).

These tests build a minimal git project and invoke the hook exactly as the harness does — piping a
`{"tool_input":{"command":...}}` PreToolUse payload on stdin, from the repo root — and assert both
directions of the new knob:

  * the DEFAULT is unchanged (main/master still blocked, so a fresh /start is unaffected);
  * the opt-in works, but only for the main/master floor — names added via `protected_branches`
    survive it, which is the nuance that makes "opt out of main, keep release" expressible;
  * it fails CLOSED on every degraded read (malformed config, missing config, non-JSON-`true`
    truthy value). Silence must only ever be more conservative, never less.

Exit 2 = blocked (the harness contract), exit 0 = permitted.
"""
import json
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent                 # product/scripts
GUARD = HERE.parent / "hooks" / "guard.sh"             # product/hooks/guard.sh

BLOCKED, ALLOWED = 2, 0


def _repo(tmp_path):
    """A minimal git repo on `main` with guard.sh installed at its real relative path."""
    root = tmp_path
    (root / ".claude" / "hooks").mkdir(parents=True)
    (root / ".workflow").mkdir(parents=True)
    (root / ".claude" / "hooks" / "guard.sh").write_text(GUARD.read_text())
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    (root / "f").write_text("x\n")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    # hooksPath=/dev/null so the project's own pre-commit hook never interferes
    subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "init"],
                   cwd=root, check=True)
    return root


def _run(root, cmd, config=None, raw_config=None):
    """Invoke the guard with a push command; returns (exit_code, stderr)."""
    if raw_config is not None:
        (root / ".workflow" / "config.json").write_text(raw_config)
    elif config is not None:
        (root / ".workflow" / "config.json").write_text(json.dumps(config))
    payload = json.dumps({"tool_input": {"command": cmd}})
    p = subprocess.run(["bash", ".claude/hooks/guard.sh"], cwd=root, input=payload,
                       capture_output=True, text=True)
    return p.returncode, p.stderr


# --- the default floor is unchanged -------------------------------------------------

@pytest.mark.parametrize("branch", ["main", "master"])
def test_default_blocks_main_and_master(tmp_path, branch):
    root = _repo(tmp_path)
    rc, err = _run(root, f"git push origin {branch}", config={"guard": {}})
    assert rc == BLOCKED
    assert branch in err


def test_default_allows_a_feature_branch(tmp_path):
    root = _repo(tmp_path)
    rc, _ = _run(root, "git push origin feat/x", config={"guard": {}})
    assert rc == ALLOWED


def test_absent_guard_key_still_blocks_main(tmp_path):
    root = _repo(tmp_path)
    rc, _ = _run(root, "git push origin main", config={})
    assert rc == BLOCKED


# --- the opt-in --------------------------------------------------------------------

def test_allow_protected_push_permits_main(tmp_path):
    root = _repo(tmp_path)
    rc, err = _run(root, "git push origin main",
                   config={"guard": {"allow_protected_push": True}})
    assert rc == ALLOWED
    # never silent: the guard announces that the floor was lowered
    assert "floor lowered" in err


def test_opt_in_still_honours_explicitly_added_branches(tmp_path):
    """Lowering the main/master floor must NOT discard `protected_branches`."""
    root = _repo(tmp_path)
    cfg = {"guard": {"allow_protected_push": True, "protected_branches": ["release"]}}
    assert _run(root, "git push origin release", config=cfg)[0] == BLOCKED
    assert _run(root, "git push origin main", config=cfg)[0] == ALLOWED


def test_opt_in_permits_push_all_when_nothing_is_protected(tmp_path):
    root = _repo(tmp_path)
    rc, _ = _run(root, "git push --all",
                 config={"guard": {"allow_protected_push": True}})
    assert rc == ALLOWED


def test_push_all_still_blocked_while_anything_is_protected(tmp_path):
    root = _repo(tmp_path)
    cfg = {"guard": {"allow_protected_push": True, "protected_branches": ["release"]}}
    rc, err = _run(root, "git push --all", config=cfg)
    assert rc == BLOCKED
    assert "--all" in err or "mirror" in err


# --- fail-closed on every degraded read --------------------------------------------

def test_malformed_config_keeps_the_floor(tmp_path):
    root = _repo(tmp_path)
    rc, _ = _run(root, "git push origin main", raw_config='{"guard":{ BROKEN')
    assert rc == BLOCKED


def test_missing_config_keeps_the_floor(tmp_path):
    root = _repo(tmp_path)
    rc, _ = _run(root, "git push origin main")          # no config.json written at all
    assert rc == BLOCKED


@pytest.mark.parametrize("truthy", ["true", "yes", 1])
def test_only_real_json_true_lowers_the_floor(tmp_path, truthy):
    """A string/int truthy value must NOT lower a safety floor — strict `is True`."""
    root = _repo(tmp_path)
    rc, _ = _run(root, "git push origin main",
                 config={"guard": {"allow_protected_push": truthy}})
    assert rc == BLOCKED


# --- org mode: a push path for the private tree is an acknowledged act, or none ------
# The tree holds derived IP about a product the operator does not own, so "no remote" is
# the default and adding one is a governance decision. The guard gates the ACT; the console
# badges the STATE, so a remote added out of band is still visible.

ORG = {"project_root": ".", "org": {"checkout": "/home/dev/work/acme"}}
ORG_ACK = {"project_root": ".",
           "org": {"checkout": "/home/dev/work/acme",
                   "archive_remote_ack": "personal offsite backup, cleared 2026-08-04"}}


@pytest.mark.parametrize("cmd", [
    "git remote add archive git@example.com:me/brain.git",
    "git remote set-url archive git@example.com:me/brain.git",
    "git remote rename origin archive",
])
def test_org_mode_blocks_giving_the_private_tree_a_push_path(tmp_path, cmd):
    root = _repo(tmp_path)
    rc, err = _run(root, cmd, config=ORG)
    assert rc == BLOCKED
    assert "archive_remote_ack" in err


def test_the_acknowledgement_key_permits_it(tmp_path):
    root = _repo(tmp_path)
    rc, _ = _run(root, "git remote add archive git@example.com:me/brain.git", config=ORG_ACK)
    assert rc == ALLOWED


def test_reading_remotes_is_never_blocked(tmp_path):
    # `git remote -v` is how the badge itself reads the state; gating a read would be
    # both useless and self-defeating.
    root = _repo(tmp_path)
    rc, _ = _run(root, "git remote -v", config=ORG)
    assert rc == ALLOWED


def test_outside_org_mode_remotes_are_the_projects_own_business(tmp_path):
    """The gate must not fire on an ordinary project — it owns its repo and its remotes."""
    root = _repo(tmp_path)
    rc, _ = _run(root, "git remote add origin git@example.com:me/mine.git", config={})
    assert rc == ALLOWED


def test_a_malformed_config_does_not_invent_an_org_gate(tmp_path):
    # Fails OPEN here, unlike the push floor, and deliberately: a project that is NOT in org
    # mode must never be blocked from managing its own remotes by an unreadable config.
    root = _repo(tmp_path)
    rc, _ = _run(root, "git remote add origin git@example.com:me/mine.git",
                 raw_config="{not json")
    assert rc == ALLOWED
