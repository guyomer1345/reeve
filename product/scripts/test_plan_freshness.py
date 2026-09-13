"""Tests for plan_freshness.py — has the tree moved under this plan?

What matters here is the ROUTING, not the diffing. Git can be trusted to say which files
changed; what these pin down is where each answer sends the plan, because every one of the
three destinations is expensive to get wrong in a different way. Send a rotten plan to
`refresh` and you get a plausible plan on a dead premise. Send a trivially-updatable one to
`replan` and you pay full price for a rename. Send either to a worker unchanged and you burn a
whole dispatch on a plan describing a tree that no longer exists.

The two cases that look identical and are not: NO GIT (no history, so nothing can have landed
— the question does not arise) versus NO base_sha (there is history, and the plan cannot say
where it stands in it). The first must not force a re-plan; the second must.
"""
import json
import os
import subprocess

import pytest

import plan_freshness as pf


def _run(root, *args):
    subprocess.run(("git", "-C", str(root)) + args, check=True,
                   capture_output=True, text=True)


def _repo(root):
    root = str(root)
    _run(root, "init", "-q")
    _run(root, "config", "user.email", "t@t")
    _run(root, "config", "user.name", "t")
    os.makedirs(os.path.join(root, ".workflow"), exist_ok=True)
    with open(os.path.join(root, ".workflow", "config.json"), "w") as fh:
        json.dump({"project_root": "."}, fh)
    return root


def _write(root, rel, text="x\n"):
    path = os.path.join(str(root), rel)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)


def _commit(root, msg="c"):
    _run(root, "add", "-A")
    _run(root, "commit", "-q", "-m", msg)
    return subprocess.run(("git", "-C", str(root), "rev-parse", "HEAD"),
                          capture_output=True, text=True).stdout.strip()


def _plan(root, item, files=(), base=None, count=None):
    d = os.path.join(str(root), ".workflow", "items", item)
    os.makedirs(d, exist_ok=True)
    body = ["# Plan — %s" % item, "", "## Goal", "do it", ""]
    if base:
        body += ["- **base_sha** — `%s`" % base]
    if count is not None:
        body += ["- **refresh_count** — %d" % count]
    body += ["", "## files_touched"]
    body += ["- `%s` — because" % f for f in files]
    body += ["", "## Steps", "1. go", ""]
    with open(os.path.join(d, "plan.md"), "w") as fh:
        fh.write("\n".join(body))


# ---------------------------------------------------------------- the three destinations

def test_untouched_plan_is_fresh(tmp_path):
    root = _repo(tmp_path)
    _write(root, "a.py")
    _write(root, "b.py")
    base = _commit(root)
    _plan(root, "i1", ["a.py"], base=base)
    _write(root, "b.py", "changed\n")          # movement, but not under this plan
    _commit(root)
    assert pf.classify(root, "i1")["state"] == pf.FRESH


def test_movement_under_the_plan_is_suspect_and_widens(tmp_path):
    root = _repo(tmp_path)
    _write(root, "a.py")
    _write(root, "dir/inner.py")
    base = _commit(root)
    _plan(root, "i1", ["a.py", "dir"], base=base)
    _write(root, "dir/inner.py", "moved\n")
    _commit(root)
    r = pf.classify(root, "i1")
    assert r["state"] == pf.SUSPECT
    # `moved` is what the gate turns into a pessimistic scope; this file stops at naming it.
    assert r["moved"] == ["dir/inner.py"]


def test_deleted_declared_file_is_void_not_dated(tmp_path):
    root = _repo(tmp_path)
    _write(root, "gone.py")
    base = _commit(root)
    _plan(root, "i1", ["gone.py"], base=base)
    _run(root, "rm", "-q", "gone.py")
    _commit(root)
    r = pf.classify(root, "i1")
    assert r["state"] == pf.REPLAN
    assert "deleted" in r["why"]


def test_a_rename_refreshes_rather_than_replans(tmp_path):
    """The tripwire must not fire on the cheap case it exists to let through. Without git's
    rename detection the old path reports as a deletion and every refactor forces a full
    re-plan — the exact over-correction that would make refresh pointless."""
    root = _repo(tmp_path)
    _write(root, "old.py", "same content, moved wholesale\n" * 5)
    base = _commit(root)
    _plan(root, "i1", ["old.py"], base=base)
    _run(root, "mv", "old.py", "new.py")
    _commit(root)
    r = pf.classify(root, "i1")
    assert r["state"] == pf.SUSPECT, r
    assert "deleted" not in r["why"]


# ---------------------------------------------------------------- the tripwires

def test_missing_base_sha_replans_and_is_never_guessed(tmp_path):
    root = _repo(tmp_path)
    _write(root, "a.py")
    _commit(root)
    _plan(root, "i1", ["a.py"])                 # no base_sha at all
    r = pf.classify(root, "i1")
    assert r["state"] == pf.REPLAN
    assert "base_sha" in r["why"]


def test_unresolvable_base_sha_replans(tmp_path):
    root = _repo(tmp_path)
    _write(root, "a.py")
    _commit(root)
    _plan(root, "i1", ["a.py"], base="deadbeefdeadbeef")
    assert pf.classify(root, "i1")["state"] == pf.REPLAN


def test_refresh_cap_replans_even_when_nothing_moved(tmp_path):
    """Counting patches, not distance: the tree here is untouched and the plan still goes back
    for a full re-plan, because two locally-correct refreshes do not compose into a correct
    plan."""
    root = _repo(tmp_path)
    _write(root, "a.py")
    base = _commit(root)
    _plan(root, "i1", ["a.py"], base=base, count=2)
    r = pf.classify(root, "i1")
    assert r["state"] == pf.REPLAN
    assert "cap" in r["why"]
    _plan(root, "i2", ["a.py"], base=base, count=1)
    assert pf.classify(root, "i2")["state"] == pf.FRESH


def test_refresh_cap_is_a_project_knob(tmp_path):
    root = _repo(tmp_path)
    _write(root, "a.py")
    base = _commit(root)
    with open(os.path.join(root, ".workflow", "config.json"), "w") as fh:
        json.dump({"project_root": ".", "run": {"wave": {"refresh_max": 5}}}, fh)
    _plan(root, "i1", ["a.py"], base=base, count=3)
    assert pf.refresh_max(root) == 5
    assert pf.classify(root, "i1")["state"] == pf.FRESH


# ---------------------------------------------------------------- absence, told apart

def test_no_repository_is_not_the_same_as_stale(tmp_path):
    """No history means no commits, so nothing can have landed under the plan. Routing this to
    REPLAN would re-plan every item forever in a tree where staleness cannot occur."""
    root = str(tmp_path)
    os.makedirs(os.path.join(root, ".workflow"))
    with open(os.path.join(root, ".workflow", "config.json"), "w") as fh:
        json.dump({"project_root": "."}, fh)
    _plan(root, "i1", ["a.py"])                 # not even a base_sha
    r = pf.classify(root, "i1")
    assert r["state"] == pf.NO_GIT
    assert pf.scan(root)["all_fresh"] is True   # and it does not fail the run


def test_no_plan_is_reported_not_swallowed(tmp_path):
    root = _repo(tmp_path)
    _commit(root)
    os.makedirs(os.path.join(root, ".workflow", "items", "i1"))
    assert pf.classify(root, "i1")["state"] == pf.NO_PLAN


# ---------------------------------------------------------------- the caller's contract

def test_exit_code_1_on_anything_not_fresh(tmp_path):
    root = _repo(tmp_path)
    _write(root, "a.py")
    base = _commit(root)
    _plan(root, "i1", ["a.py"], base=base)
    assert pf.main(["--project-root", root]) == 0
    _write(root, "a.py", "moved\n")
    _commit(root)
    assert pf.main(["--project-root", root]) == 1


def test_a_broken_git_call_lands_on_not_fresh(tmp_path, monkeypatch):
    """Negative control on the fail direction: if the diff cannot be computed at all, the
    answer must not drift to FRESH."""
    root = _repo(tmp_path)
    _write(root, "a.py")
    base = _commit(root)
    _plan(root, "i1", ["a.py"], base=base)
    assert pf.classify(root, "i1")["state"] == pf.FRESH
    monkeypatch.setattr(pf, "changed_since", lambda *a, **k: (False, {}))
    assert pf.classify(root, "i1")["state"] == pf.REPLAN
