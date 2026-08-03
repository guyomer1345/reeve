#!/usr/bin/env python3
"""Tests for the `# Lessons` convention — the placement rule that makes Sessions
distillation safe.

Distillation is no longer deferred: the `audit` item reduces each entry about to fall past
*K* to a one-line lesson before `retention.py` caps, because compression beats raw retention
(a distilled entry leaves something behind; a raw one dropped to git leaves nothing a future
session reads).

That only works if the lessons themselves survive the cap, and there is a real trap here.
`# Sessions` is the node's TERMINAL section and its region deliberately runs to EOF once
entries have begun — that rule exists so a markdown H1 inside a postmortem body cannot
truncate the region and leave later entries uncapped. The consequence is that a `## Lessons`
written *under* `# Sessions` would be parsed as a session ENTRY and dropped by the very cap it
was written to survive: distilled memory deleted by the mechanism meant to preserve it.

So `# Lessons` is top-level and sits BEFORE `# Sessions`. These tests are what hold that,
because the failure is silent — the lessons just quietly stop being there.
"""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
RETENTION = os.path.join(HERE, "retention.py")

LESSON = "- the share-link bug came from trusting a clock; assert on the token, not the time"


def _node(body):
    return "---\npath: app.py\n---\n## Purpose\ndoes things\n\n" + body


def _entries(n):
    out = []
    for i in range(1, n + 1):
        out.append("## [2026-01-%02d] debug | entry %d\nbody %d\n" % (i, i, i))
    return "".join(out)


def _project(tmp_path, node_body, sessions_k=2):
    root = tmp_path
    (root / ".workflow").mkdir(parents=True, exist_ok=True)
    (root / ".workflow" / "config.json").write_text(
        json.dumps({"project_root": ".", "retention": {"sessions_k": sessions_k}}))
    kn = root / "docs" / "knowledge"
    kn.mkdir(parents=True, exist_ok=True)
    (kn / "app.py.md").write_text(_node(node_body))
    subprocess.run(["git", "init", "-q", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"], cwd=root, check=True,
                   env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e",
                            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e"))
    return root


def _run(root):
    # Run it the way the `audit` item does: CWD = the repo root, no `--project-root`.
    # `retention.py` resolves `--workflow-dir` relative to the cwd and reads `sessions_k`
    # from there, and its `--project-root` means the PRODUCT root (`./project` on
    # greenfield) — not the repo root, which is what the same flag means in
    # `update_reconcile.py`. Passing a repo path here silently reads no config and caps at
    # the default K, which is exactly the way this harness was wrong the first time.
    r = subprocess.run([sys.executable, RETENTION], cwd=str(root),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "K=2" in r.stdout, "the fixture's sessions_k was not picked up: %s" % r.stdout
    return (root / "docs" / "knowledge" / "app.py.md").read_text()


def test_lessons_before_sessions_survives_the_cap(tmp_path):
    """The whole convention, as behaviour. Four entries, K=2: two drop to git, and the
    distilled lesson must still be on disk."""
    root = _project(tmp_path, "# Lessons\n%s\n\n# Sessions\n%s" % (LESSON, _entries(4)))
    out = _run(root)
    assert LESSON in out, "the distilled lesson was destroyed by the cap it must survive"
    assert "retention: 2 Sessions entries archived" in out, "the cap did not actually run"
    assert "entry 1" not in out and "entry 4" in out


def test_lessons_is_not_counted_as_a_session_entry(tmp_path):
    """It must not consume one of the K slots either — a lesson is not a postmortem."""
    root = _project(tmp_path, "# Lessons\n%s\n\n# Sessions\n%s" % (LESSON, _entries(2)))
    out = _run(root)
    assert "retention:" not in out, "nothing should have been archived at exactly K entries"
    assert LESSON in out
    assert "entry 1" in out and "entry 2" in out


def test_the_trap_is_real_lessons_UNDER_sessions_would_be_capped_away(tmp_path):
    """Documents WHY the placement rule exists, by exercising the wrong placement.

    A `## Lessons` nested under `# Sessions` is indistinguishable from an entry header, so it
    takes a slot and is dropped in date order like any other. If this test ever starts
    failing, the region rule changed and the placement requirement should be re-derived
    rather than assumed."""
    root = _project(tmp_path, "# Sessions\n## Lessons\n%s\n%s" % (LESSON, _entries(4)))
    out = _run(root)
    assert LESSON not in out, (
        "the wrong placement no longer loses the lesson — re-check the placement rule in "
        "memory-model.md, it may now be over-strict")


def test_a_node_with_lessons_and_no_sessions_is_untouched(tmp_path):
    root = _project(tmp_path, "# Lessons\n%s\n" % LESSON)
    out = _run(root)
    assert LESSON in out
    assert "retention:" not in out


def test_repeated_runs_are_idempotent_for_lessons(tmp_path):
    """The audit item is re-runnable, so a second pass must not erode the lessons."""
    root = _project(tmp_path, "# Lessons\n%s\n\n# Sessions\n%s" % (LESSON, _entries(4)))
    first = _run(root)
    second = _run(root)
    assert LESSON in second
    assert first == second


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
