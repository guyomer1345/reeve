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
    sa.record(str(proj), "t-1")
    ok, msg = _check(proj)
    assert ok is True and "covered by the approval receipt" in msg


# --- the receipt must not be forgeable --------------------------------------

def test_editing_the_spec_AFTER_approval_blocks_again(proj):
    """The move the digest exists to catch. A receipt that merely said "approved" would licence
    this, and it is exactly how a goal change gets past a human who approved something else."""
    _stage(proj, LOCKED_SPEC)
    sa.record(str(proj), "t-1")
    assert _check(proj)[0] is True
    _stage(proj, LOCKED_SPEC.replace("users can sign in", "users can sign in with SSO only"))
    ok, msg = _check(proj)
    assert ok is False
    assert "DIFFERENT spec content" in msg
    assert "editing after approval" in msg


def test_a_stale_receipt_does_not_licence_a_LATER_change(proj):
    """One approval must not be a standing permit."""
    _stage(proj, LOCKED_SPEC)
    sa.record(str(proj), "t-1")
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
    sa.record(str(proj), "t-1")
    # Now dirty the worktree WITHOUT staging it. The commit still contains the approved text.
    (proj / "docs" / "spec.md").write_text(LOCKED_SPEC + "\nunstaged junk\n", encoding="utf-8")
    assert _check(proj)[0] is True


def test_record_stamps_the_STAGED_content(proj):
    _stage(proj, LOCKED_SPEC)
    rec = sa.record(str(proj), "t-1")
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
                    "--ticket", "t-1"], capture_output=True, text=True)
    allowed = subprocess.run([sys.executable, gate, "--project-root", str(proj),
                              "--scripts-dir", HERE, "check"], capture_output=True, text=True)
    assert allowed.returncode == 0


# --- the CLI shape `checks.sh` actually uses ---------------------------------
#
# The bug a live drive found and this suite did not. `checks.sh` writes the natural order —
# `spec_approval.py check --scripts-dir "$SCRIPTS"` — and argparse binds a top-level flag only
# BEFORE the subcommand, so it errored and the gate failed closed on EVERY commit of every
# project bootstrapped from that version. The tests above passed because they happened to put
# the flags first. That is exactly how a CLI-shaped bug survives a green suite: the test and the
# real caller invoke the same script two different ways, and only one of them is exercised.

@pytest.mark.parametrize("argv_order", ["flags-first", "flags-after"])
def test_both_argument_orders_work(proj, argv_order):
    gate = os.path.join(HERE, "spec_approval.py")
    _stage(proj, LOCKED_SPEC)
    if argv_order == "flags-first":
        argv = [gate, "--project-root", str(proj), "--scripts-dir", HERE, "check"]
    else:
        argv = [gate, "check", "--project-root", str(proj), "--scripts-dir", HERE]
    r = subprocess.run([sys.executable] + argv, capture_output=True, text=True)
    assert "unrecognized arguments" not in r.stderr, r.stderr
    assert r.returncode == 2, r.stderr            # blocked: crosses the floor, no receipt


def test_the_exact_invocation_checks_sh_writes(proj):
    """Pinned literally against the template, so the two cannot drift apart again. If the
    template changes its call, this test is the thing that should notice."""
    tmpl = os.path.join(HERE, "..", "templates", "checks.sh")
    body = open(tmpl, encoding="utf-8").read()
    assert 'spec_approval.py" check --scripts-dir' in body, "checks.sh call shape changed"
    gate = os.path.join(HERE, "spec_approval.py")
    _stage(proj, CLEAN_SPEC)
    r = subprocess.run([sys.executable, gate, "check", "--scripts-dir", HERE],
                       capture_output=True, text=True, cwd=str(proj))
    assert r.returncode == 0, r.stderr


def test_record_also_accepts_flags_after_the_subcommand(proj):
    gate = os.path.join(HERE, "spec_approval.py")
    _stage(proj, LOCKED_SPEC)
    r = subprocess.run([sys.executable, gate, "record", "--ticket", "t-1",
                        "--project-root", str(proj)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert sa.read_receipt(str(proj))["ticket_id"] == "t-1"


def test_the_receipt_does_not_trip_the_SECRET_SCAN(proj):
    """The defect a live drive found, pinned so it cannot come back.

    The receipt is COMMITTED — it must ride the commit it authorises — and `guard.sh` blocks any
    staged `token:` followed by 12+ key-shaped characters. The original receipt carried the
    checkpoint's correlation token, which is comfortably longer, so it could never be staged:
    two package rules with no reachable compliant state. The fix is on THIS side deliberately —
    a false positive on a token-shaped field is far cheaper than a missed credential, so the
    scan does not move. This asserts the receipt stays clean against the real pattern.
    """
    import re
    guard = os.path.join(HERE, "..", "hooks", "guard.sh")
    line = [l for l in open(guard, encoding="utf-8") if l.startswith("SECRET_RE=")][0]
    pattern = line.split("=", 1)[1].strip().strip("'")
    _stage(proj, LOCKED_SPEC)
    sa.record(str(proj), "bootstrap-reconcile")           # a realistic, long ticket id
    body = open(os.path.join(str(proj), sa.RECEIPT_REL), encoding="utf-8").read()
    hit = re.search(pattern, body, re.I)
    assert hit is None, "receipt would be blocked as a secret: %r" % (hit.group(0) if hit else "")


def test_the_receipt_carries_no_credential_shaped_field_names(proj):
    """The structural half of the rule above: if a future field reintroduces one of these names,
    this fails at the schema rather than waiting for a commit to be blocked."""
    _stage(proj, LOCKED_SPEC)
    rec = sa.record(str(proj), "t-1")
    assert not {"token", "secret", "password", "api_key", "apikey"} & set(rec)


# --- the block now ROUTES somewhere ------------------------------------------
# The gate always refused correctly and then routed nowhere: its message said "raise a
# checkpoint" and a real unattended drive read that, wrote the withheld change to a
# spec-delta.md, noted it in the backlog, and carried on. The ask had no durable owner, so
# `clear_safe`, the console and the handoff mirror all believed nobody was waiting.

def _runtime(root):
    """`parked/` lives under the runtime root, which `bus.Paths` resolves. A project with no
    runtime pointer keeps it inside `.workflow/`, which is what these tests exercise."""
    return root / ".workflow" / "parked"


def test_a_block_PARKS_a_spec_checkpoint(proj):
    _stage(proj, LOCKED_SPEC)
    ok, msg = sa.check(str(proj), HERE, do_park=True)
    assert ok is False
    parked = sorted(p.name for p in _runtime(proj).glob("*.json"))
    assert len(parked) == 1, parked
    rec = json.loads((_runtime(proj) / parked[0]).read_text())
    assert rec["checkpoint"]["kind"] == "spec"
    assert rec["token"], "a tokenless park can be answered but never resumed"
    assert rec["checkpoint"]["request"]["blocking"] is True
    assert parked[0][:-5] in msg, "the refusal must name the ticket it raised"


def test_the_gate_stays_READ_ONLY_without_the_flag(proj):
    """Every other caller — align, a dry run, a test — must not open checkpoints."""
    _stage(proj, LOCKED_SPEC)
    ok, msg = _check(proj)
    assert ok is False
    assert not _runtime(proj).exists() or not list(_runtime(proj).glob("*.json"))
    assert "Route it" in msg


def test_re_running_the_gate_does_not_open_a_SECOND_checkpoint(proj):
    """`checks.sh` runs on every commit attempt. Without idempotency a blocked change that is
    retried buries the human in identical cards."""
    _stage(proj, LOCKED_SPEC)
    for _ in range(3):
        sa.check(str(proj), HERE, do_park=True)
    assert len(list(_runtime(proj).glob("*.json"))) == 1


def test_editing_the_spec_opens_a_DIFFERENT_checkpoint(proj):
    """Keyed on the spec digest, so a changed spec is a different ask — the human would be
    approving text the first ticket never quoted."""
    _stage(proj, LOCKED_SPEC)
    sa.check(str(proj), HERE, do_park=True)
    first = sorted(p.name for p in _runtime(proj).glob("*.json"))
    _stage(proj, LOCKED_SPEC + "\n- **Search** — commitment: `locked`\n")
    sa.check(str(proj), HERE, do_park=True)
    now = sorted(p.name for p in _runtime(proj).glob("*.json"))
    assert len(now) == 2 and first[0] in now


def test_a_STALE_receipt_also_parks(proj):
    """The other blocked path — approved v1, staging v2 — is the same situation to a human and
    must reach one the same way."""
    _stage(proj, LOCKED_SPEC)
    sa.record(str(proj), "t-1")
    _stage(proj, LOCKED_SPEC + "\n- **Search** — commitment: `locked`\n")
    ok, msg = sa.check(str(proj), HERE, do_park=True)
    assert ok is False and "DIFFERENT spec content" in msg
    assert len(list(_runtime(proj).glob("*.json"))) == 1


def test_a_park_that_FAILS_still_blocks_and_says_so(proj, monkeypatch):
    """Fail-soft, and it is the opposite direction to everything else in this file. The gate has
    already decided to refuse; parking is how the refusal reaches a person. A park that raised
    would turn an actionable block into a crash — and the commit would still be blocked, with
    nobody told why. The `/rebind` case (runtime root gone) is exactly when this matters."""
    _stage(proj, LOCKED_SPEC)
    monkeypatch.setattr(sa, "park", lambda *a, **k: ("SPEC-x", "the runtime root is gone"))
    ok, msg = sa.check(str(proj), HERE, do_park=True)
    assert ok is False
    assert "could NOT be parked" in msg and "runtime root is gone" in msg
    assert "/rebind" in msg


def test_an_approved_change_parks_NOTHING(proj):
    """The escape still works, and works without side effects."""
    _stage(proj, LOCKED_SPEC)
    sa.record(str(proj), "t-1")
    ok, _ = sa.check(str(proj), HERE, do_park=True)
    assert ok is True
    assert not _runtime(proj).exists() or not list(_runtime(proj).glob("*.json"))


def test_the_park_names_the_item_when_there_is_one(proj):
    (proj / ".workflow" / "state.json").write_text(json.dumps({"current_item": "I-007"}))
    _stage(proj, LOCKED_SPEC)
    sa.check(str(proj), HERE, do_park=True)
    rec = json.loads(next(_runtime(proj).glob("*.json")).read_text())
    assert "I-007" in rec["checkpoint"]["request"]["what"]


def test_the_cli_accepts_park_on_either_side_of_the_subcommand(proj):
    """The argument-order trap this file already caught once, re-checked for the new flag."""
    _stage(proj, LOCKED_SPEC)
    for argv in (["check", "--scripts-dir", HERE, "--park", "--project-root", str(proj)],
                 ["--project-root", str(proj), "check", "--scripts-dir", HERE, "--park"]):
        assert sa.main(argv) == 2
    assert len(list(_runtime(proj).glob("*.json"))) == 1


# ============================================================ the nested project root
# A DRIVE, not a review, found this: the floor resolved `project_root`/`docs_root` out of
# `config.json` and read `project/docs/spec.md`, while this gate hardcoded `docs/spec.md` and
# never opened the config. The floor fired, the gate could not read the staged spec, and every
# commit was BLOCKED with the escape unreachable — `check()` dies on the unreadable spec before
# it consults any receipt, so the receipt could never be honoured. It blocked a greenfield
# project's entire backlog and could not be repaired from inside the loop. The suite was green
# throughout, because every test here used the one layout where the two spellings coincide.

def _nested(tmp_path, spec_text):
    """A project whose spec is NOT at `<root>/docs/spec.md` — the layout `/start` scaffolds.

    The spec is COMMITTED and then EDITED, not merely staged: a spec this change creates does
    not cross the floor at all (its rules ask what a change does to an existing demand), so a
    fixture that only stages one would leave every test below asserting against a gate that
    never fires — for a reason that has nothing to do with the layout they are about.
    """
    root = tmp_path / "repo"
    (root / ".workflow").mkdir(parents=True)
    (root / "project" / "docs").mkdir(parents=True)
    (root / ".workflow" / "config.json").write_text(json.dumps({"project_root": "./project"}))
    spec = root / "project" / "docs" / "spec.md"
    spec.write_text(spec_text)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "project/docs/spec.md"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "the spec exists"], check=True)
    spec.write_text(spec_text.replace("users can sign in", "users can sign in with a passkey"))
    subprocess.run(["git", "-C", str(root), "add", "project/docs/spec.md"], check=True)
    return root


def test_the_spec_is_found_through_config_not_at_the_hardcoded_path(tmp_path):
    root = _nested(tmp_path, LOCKED_SPEC)
    assert sa.staged_spec(str(root), HERE) is not None, \
        "the gate could not read a spec the floor reads fine — the original defect"


def test_the_git_relative_path_is_used_for_the_STAGED_blob(tmp_path):
    """`git show :<rel>` needs a path relative to the GIT TOPLEVEL. Deriving it from
    `project_root` instead is what limited the old code to one layout."""
    root = _nested(tmp_path, LOCKED_SPEC)
    top, rel, path = sa.spec_location(str(root), HERE)
    assert rel == "project/docs/spec.md"
    assert os.path.realpath(top) == os.path.realpath(str(root))
    assert os.path.isfile(path)
    # and it really is the STAGED blob, not the worktree
    (root / "project" / "docs" / "spec.md").write_text(LOCKED_SPEC + "\nunstaged\n")
    assert b"unstaged" not in sa.staged_spec(str(root), HERE)


def test_the_receipt_records_the_path_that_was_actually_approved(tmp_path):
    root = _nested(tmp_path, LOCKED_SPEC)
    rec = sa.record(str(root), "TCK-1", HERE)
    assert rec["spec_path"] == "project/docs/spec.md", \
        "a receipt naming a file that does not exist is unreadable to every downstream reader"
    assert os.path.isfile(os.path.join(str(root), rec["spec_path"]))


def test_the_ESCAPE_is_reachable_on_a_nested_layout(tmp_path):
    """The whole point. Blocked -> approve -> committable, on the layout that could not get
    past the first step. `a gate with no escape gets switched off` is this file's own header."""
    root = _nested(tmp_path, LOCKED_SPEC)
    ok, msg = sa.check(str(root), HERE)
    assert not ok and "no approval receipt" in msg, msg
    sa.record(str(root), "TCK-1", HERE)
    ok, msg = sa.check(str(root), HERE)
    assert ok, msg


def test_editing_after_approval_still_blocks_on_a_nested_layout(tmp_path):
    """The escape must not become a skeleton key just because the path now resolves."""
    root = _nested(tmp_path, LOCKED_SPEC)
    sa.record(str(root), "TCK-1", HERE)
    (root / "project" / "docs" / "spec.md").write_text(LOCKED_SPEC + "\n  - and reset it\n")
    subprocess.run(["git", "-C", str(root), "add", "project/docs/spec.md"], check=True)
    ok, msg = sa.check(str(root), HERE)
    assert not ok and "DIFFERENT spec content" in msg, msg


def test_an_UNLOADABLE_floor_still_fails_closed(tmp_path):
    """The fallback is the old hardcoded relative path, which resolves to nothing on this
    layout — so it still BLOCKS. An escape hatch that opens when the gate malfunctions is not
    an escape hatch, and that rule survives the fix."""
    root = _nested(tmp_path, LOCKED_SPEC)
    assert sa._floor(str(tmp_path / "no-scripts-here")) is None
    ok, msg = sa.check(str(root), str(tmp_path / "no-scripts-here"))
    assert not ok, msg
