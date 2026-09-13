"""Tests for spec_approval.py — the receipt that makes the autonomy floor an enforcement.

The floor by itself is a CONSULTATION: loop.md asks the orchestrator to run it, and a loop that
simply does not is precisely the case the floor exists for. Running it at commit time fixes
that and breaks the legitimate case — a human WAS asked and DID approve — so the escape is the
design problem, not the gate.

Everything below is about the escape not being forgeable. A receipt that merely said "approved"
would licence every later spec change forever, and worse, would licence editing the spec AFTER
approval — the exact move the floor exists to catch. So the tests that matter most are the ones
where a receipt EXISTS and is still refused.
"""
import json
import os
import subprocess
import sys

import pytest

import spec_approval as sa

HERE = os.path.dirname(os.path.abspath(sa.__file__))

CLEAN_SPEC = """# Spec

## Features
- **Login** — commitment: `provisional`
  - users can sign in
"""

LOCKED_SPEC = """# Spec

## Features
- **Login** — commitment: `locked`
  - users can sign in
"""


def _git(root, *args):
    return subprocess.run(("git", "-C", str(root)) + args, capture_output=True, text=True)


@pytest.fixture
def proj(tmp_path):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    (root / ".workflow").mkdir()
    (root / "docs" / "spec.md").write_text(CLEAN_SPEC, encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    return root


def _stage(root, text):
    (root / "docs" / "spec.md").write_text(text, encoding="utf-8")
    _git(root, "add", "-A")


def _check(root):
    return sa.check(str(root), HERE)


# --- the gate is quiet when the floor is clear -------------------------------

def test_a_change_that_does_not_cross_the_floor_needs_no_receipt(proj):
    _stage(proj, CLEAN_SPEC + "\n- **Search** — commitment: `provisional`\n")
    ok, msg = _check(proj)
    assert ok is True and "no approval receipt needed" in msg


# --- the enforcement ---------------------------------------------------------

def test_crossing_the_floor_with_no_receipt_is_BLOCKED(proj):
    """The consultation becoming an enforcement: nothing downstream used to notice."""
    _stage(proj, LOCKED_SPEC)
    ok, msg = _check(proj)
    assert ok is False
    assert "carries no approval receipt" in msg
    assert "drifts toward 'not fundamental'" in msg      # says WHY, not just no


def test_a_matching_receipt_lets_the_approved_change_through(proj):
    """The escape must actually work, or the gate gets switched off."""
    _stage(proj, LOCKED_SPEC)
    sa.record(str(proj), "t-1", "t-1:steer:abc")
    ok, msg = _check(proj)
    assert ok is True and "covered by the approval receipt" in msg


# --- the receipt must not be forgeable --------------------------------------

def test_editing_the_spec_AFTER_approval_blocks_again(proj):
    """The move the digest exists to catch. A receipt that merely said "approved" would licence
    this, and it is exactly how a goal change gets past a human who approved something else."""
    _stage(proj, LOCKED_SPEC)
    sa.record(str(proj), "t-1", "tok")
    assert _check(proj)[0] is True
    _stage(proj, LOCKED_SPEC.replace("users can sign in", "users can sign in with SSO only"))
    ok, msg = _check(proj)
    assert ok is False
    assert "DIFFERENT spec content" in msg
    assert "editing after approval" in msg


def test_a_stale_receipt_does_not_licence_a_LATER_change(proj):
    """One approval must not be a standing permit."""
    _stage(proj, LOCKED_SPEC)
    sa.record(str(proj), "t-1", "tok")
    _stage(proj, LOCKED_SPEC + "\n- **Payments** — commitment: `locked`\n")
    assert _check(proj)[0] is False


def test_a_receipt_with_no_digest_is_refused(proj):
    _stage(proj, LOCKED_SPEC)
    (proj / ".workflow" / "spec-approval.json").write_text(
        json.dumps({"ticket_id": "t-1"}), encoding="utf-8")
    assert _check(proj)[0] is False


def test_an_unparseable_receipt_is_refused_not_ignored(proj):
    _stage(proj, LOCKED_SPEC)
    (proj / ".workflow" / "spec-approval.json").write_text("{ truncated", encoding="utf-8")
    ok, msg = _check(proj)
    assert ok is False and "carries no approval receipt" in msg


# --- staged, not worktree ----------------------------------------------------

def test_the_gate_reads_the_STAGED_spec_not_the_worktree(proj):
    """A gate reading the worktree could be satisfied by a file the commit does not contain."""
    _stage(proj, LOCKED_SPEC)
    sa.record(str(proj), "t-1", "tok")
    # Now dirty the worktree WITHOUT staging it. The commit still contains the approved text.
    (proj / "docs" / "spec.md").write_text(LOCKED_SPEC + "\nunstaged junk\n", encoding="utf-8")
    assert _check(proj)[0] is True


def test_record_stamps_the_STAGED_content(proj):
    _stage(proj, LOCKED_SPEC)
    rec = sa.record(str(proj), "t-1", "tok")
    assert rec["spec_sha256"] == sa.spec_digest(LOCKED_SPEC)


# --- fail direction: uncomputable is BLOCKED --------------------------------

def test_a_missing_floor_gate_blocks_rather_than_waving_through(proj, tmp_path):
    """An escape hatch that opens when the mechanism malfunctions is not an escape hatch."""
    empty = tmp_path / "noscripts"
    empty.mkdir()
    ok, msg = sa.check(str(proj), str(empty))
    assert ok is False and "could not be run" in msg


def test_an_unreadable_spec_blocks(proj, monkeypatch):
    _stage(proj, LOCKED_SPEC)
    monkeypatch.setattr(sa, "staged_spec", lambda *a, **k: None)
    ok, msg = sa.check(str(proj), HERE)
    assert ok is False and "could not be read" in msg


# --- the cli contract --------------------------------------------------------

def test_cli_exit_codes(proj):
    gate = os.path.join(HERE, "spec_approval.py")
    _stage(proj, LOCKED_SPEC)
    blocked = subprocess.run([sys.executable, gate, "--project-root", str(proj),
                              "--scripts-dir", HERE, "check"], capture_output=True, text=True)
    assert blocked.returncode == 2
    subprocess.run([sys.executable, gate, "--project-root", str(proj), "record",
                    "--ticket", "t-1", "--token", "tok"], capture_output=True, text=True)
    allowed = subprocess.run([sys.executable, gate, "--project-root", str(proj),
                              "--scripts-dir", HERE, "check"], capture_output=True, text=True)
    assert allowed.returncode == 0
