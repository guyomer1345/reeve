"""Tests for scripts/review_bundle.py — the org-mode review bundle.

What these pin is the BOUNDARY, not the plumbing. The bundle is the one artifact that
deliberately crosses from a private clone into a repo the operator does not own, so the
tests that matter are the ones that prove what does NOT cross: no brain path, no loop commit
message, no sidecar, and no sha the owner's repo cannot resolve. The happy path is one test;
the refusals are most of the file, which is the right ratio for a leak boundary.
"""
import json
import os
import subprocess
import sys

import pytest

import review_bundle as rb

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "review_bundle.py")


def _git(root, *args, **kw):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          check=kw.get("check", True)).stdout


def _upstream(tmp_path):
    """A repo standing in for the product's owner: their code, their docs, their CLAUDE.md."""
    up = tmp_path / "upstream"
    up.mkdir()
    _git(up, "init", "-q", "-b", "main")
    _git(up, "config", "user.email", "owner@acme")
    _git(up, "config", "user.name", "owner")
    (up / "src").mkdir()
    (up / "src" / "app.py").write_text("def handler(req): return 200\n")
    (up / "docs").mkdir()
    (up / "docs" / "spec.md").write_text("# acme internal spec\n")
    (up / "CLAUDE.md").write_text("# acme brief\n")
    _git(up, "add", "-A")
    _git(up, "commit", "-qm", "acme init")
    return up


def _brain(tmp_path, org=True):
    """The private clone with the workflow layered on: `.workflow/` + `.claude/`, nothing else."""
    up = _upstream(tmp_path)
    brain = tmp_path / "brain"
    _git(tmp_path, "clone", "-q", str(up), str(brain))
    _git(brain, "remote", "set-url", "--push", "origin", "no_push")
    _git(brain, "config", "user.email", "brain@local")
    _git(brain, "config", "user.name", "brain")
    (brain / ".workflow" / "items" / "itm-7").mkdir(parents=True)
    (brain / ".workflow" / "docs").mkdir(parents=True)
    (brain / ".claude" / "scripts").mkdir(parents=True)
    cfg = {"project_root": ".", "docs_root": ".workflow"}
    if org:
        cfg["org"] = {"checkout": "/home/dev/work/acme"}
    (brain / ".workflow" / "config.json").write_text(json.dumps(cfg))
    (brain / ".workflow" / "items" / "itm-7" / "plan.md").write_text("plan: retry the handler\n")
    (brain / ".workflow" / "items" / "itm-7" / "changelog.md").write_text("changelog: retries\n")
    _git(brain, "add", "-A")
    _git(brain, "commit", "-qm", "chore: brain scaffold")
    _git(brain, "fetch", "-q", "origin")
    return brain


def _work(brain, item, code=None, brain_file=None, msg="fix(handler): work"):
    """One loop commit touching company code and/or the brain, trailered to an item."""
    if code is not None:
        (brain / "src" / "app.py").write_text(code)
    if brain_file is not None:
        (brain / ".workflow" / "docs" / "knowledge.json").write_text(brain_file)
    _git(brain, "add", "-A")
    _git(brain, "commit", "-qm", "%s\n\nRefs: item #%s" % (msg, item))


# ------------------------------------------------------------------ the happy path

def test_two_loop_commits_become_one_diff_with_the_brain_excluded(tmp_path):
    brain = _brain(tmp_path)
    _work(brain, "itm-7", code="def handler(req): return 200  # retry\n",
          brain_file='{"derived":"acme internals"}', msg="fix: retry")
    _work(brain, "itm-7", code="def handler(req): return 201  # retry\n",
          brain_file='{"derived":"more acme internals"}', msg="fix: status")
    meta, reasons = rb.build(str(brain), "itm-7")
    assert reasons == []
    assert meta["files"] == ["src/app.py"], "only the owner's own file may cross"
    diff = (brain / ".workflow" / "bundles" / "itm-7.diff").read_text()
    # ONE squashed hunk: the intermediate 200 state never appears.
    assert "+def handler(req): return 201  # retry" in diff
    assert "return 200  # retry" not in diff
    # and none of the loop's own prose came with it
    assert "Refs: item" not in diff and "fix: retry" not in diff and "derived" not in diff


def test_the_sidecar_is_a_separate_file_and_never_inside_the_diff(tmp_path):
    brain = _brain(tmp_path)
    _work(brain, "itm-7", code="x = 1\n")
    meta, _ = rb.build(str(brain), "itm-7")
    diff = (brain / ".workflow" / "bundles" / "itm-7.diff").read_text()
    side = json.loads((brain / ".workflow" / "bundles" / "itm-7.json").read_text())
    assert side["item_id"] == "itm-7"
    assert side["summary"]["plan"].startswith("plan:")
    for probe in ("itm-7", "plan:", "base_resolved_by"):
        assert probe not in diff, "the sidecar's content must not be in the diff"


def test_the_only_sha_quoted_at_the_human_is_one_their_repo_has(tmp_path):
    """The brain carries scaffold and per-item commits the owner's repo has never seen, so
    its own base sha is unresolvable on their side. Found by rendering the hand-off."""
    brain = _brain(tmp_path)
    _work(brain, "itm-7", code="x = 1\n")
    meta, _ = rb.build(str(brain), "itm-7")
    upstream_shas = _git(tmp_path / "upstream", "log", "--format=%H").split()
    assert meta["upstream_base"] in upstream_shas
    assert meta["base"] not in upstream_shas          # brain-local, audit only
    hint = rb._apply_hint(meta, "b.diff")
    assert meta["upstream_base"][:12] in hint
    assert meta["base"][:12] not in hint


def test_the_bundle_applies_cleanly_to_the_owners_own_checkout(tmp_path):
    """The property the whole mechanism exists for, asserted against a real second clone
    rather than inferred: the human applies it, and authors the commit themselves."""
    brain = _brain(tmp_path)
    _work(brain, "itm-7", code="def handler(req): return 201\n",
          brain_file='{"derived":"secret"}')
    rb.build(str(brain), "itm-7")
    checkout = tmp_path / "checkout"
    _git(tmp_path, "clone", "-q", str(tmp_path / "upstream"), str(checkout))
    _git(checkout, "config", "user.email", "dev@acme")
    _git(checkout, "config", "user.name", "dev")
    _git(checkout, "apply", str(brain / ".workflow" / "bundles" / "itm-7.diff"))
    assert (checkout / "src" / "app.py").read_text() == "def handler(req): return 201\n"
    assert not (checkout / ".workflow").exists(), "the brain must not materialise upstream"
    _git(checkout, "add", "-A")
    _git(checkout, "commit", "-qm", "handler returns 201")
    assert "dev" in _git(checkout, "log", "-1", "--format=%an")


# ------------------------------------------------------------------ the refusals

def test_a_brain_reference_added_to_a_company_file_is_refused(tmp_path):
    # Path exclusion cannot catch this one: the PATH is theirs, the CONTENT is ours.
    brain = _brain(tmp_path)
    _work(brain, "itm-8", code="x = 1  # see .workflow/docs/knowledge.json\n")
    meta, reasons = rb.build(str(brain), "itm-8")
    assert meta is None
    assert any("references the brain" in r for r in reasons)


def test_a_bundle_carrying_a_brain_path_is_refused_on_verify(tmp_path):
    """`verify` reads the produced BYTES, not the pathspec that produced them — so the
    exclusion is checked rather than merely applied."""
    brain = _brain(tmp_path)
    _work(brain, "itm-7", code="x = 1\n")
    rb.build(str(brain), "itm-7")
    path = brain / ".workflow" / "bundles" / "itm-7.diff"
    path.write_text(path.read_text() + (
        "diff --git a/.workflow/docs/knowledge.json b/.workflow/docs/knowledge.json\n"
        "--- a/.workflow/docs/knowledge.json\n+++ b/.workflow/docs/knowledge.json\n"
        "@@ -1 +1 @@\n-old\n+derived\n"))
    assert any("brain path" in r for r in rb.verify(str(path)))


def test_an_item_touching_only_the_brain_produces_no_bundle(tmp_path):
    # An empty diff would otherwise be written as a valid, meaningless bundle.
    brain = _brain(tmp_path)
    _work(brain, "itm-9", brain_file='{"derived":"only brain work"}')
    meta, reasons = rb.build(str(brain), "itm-9")
    assert meta is None and any("EMPTY" in r for r in reasons)


def test_outside_org_mode_the_bundle_is_refused(tmp_path):
    brain = _brain(tmp_path, org=False)
    _work(brain, "itm-7", code="x = 1\n")
    with pytest.raises(RuntimeError, match="ORG-MODE"):
        rb.build(str(brain), "itm-7")


def test_an_item_with_no_committed_work_is_refused_not_empty(tmp_path):
    brain = _brain(tmp_path)
    with pytest.raises(RuntimeError, match="no commit carries"):
        rb.build(str(brain), "itm-never")


def test_runs_as_a_subprocess_the_way_a_skill_calls_it(tmp_path):
    brain = _brain(tmp_path)
    _work(brain, "itm-7", code="x = 1\n")
    r = subprocess.run([sys.executable, SCRIPT, "build", "itm-7",
                        "--project-root", str(brain)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "BUNDLE itm-7" in r.stdout and "src/app.py" in r.stdout


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
