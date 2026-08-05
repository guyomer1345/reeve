"""Tests for scripts/project_state.py — the mechanical half of the "where is this project" view.

The script's whole value is that its numbers are trustworthy, so these tests concentrate on the two
ways a status view lies:

  * it reports a MISSING source as an empty one ("0 features" when there is no spec at all), and
  * it silently reads the WRONG project (the org-mode docs_root split).

Both are worse than no view, because a number is believed in a way an absence is not. The rest pins
that nothing is written to disk -- a stored status doc rots and is then believed anyway.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "project_state.py"


def _run(cwd, *args):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          cwd=cwd, capture_output=True, text=True)


def _project(tmp_path, *, config=None):
    wf = tmp_path / ".workflow"
    wf.mkdir(parents=True)
    if config is not None:
        (wf / "config.json").write_text(json.dumps(config))
    return tmp_path


def _spec(root, body):
    d = Path(root) / "docs"
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.md").write_text(body)


# ------------------------------------------------------------------ absence vs emptiness

def test_no_workflow_root_is_a_usage_error_not_a_state(tmp_path):
    r = _run(tmp_path)
    assert r.returncode == 2
    assert "no workflow root" in r.stderr


def test_missing_spec_says_missing_and_never_reports_zero_features(tmp_path):
    p = _project(tmp_path)
    r = _run(p)
    assert r.returncode == 0
    assert "no spec at" in r.stdout
    # The failure this guards: rendering an absent spec as a real, empty one.
    assert "0 commitment tags" not in r.stdout


def test_present_but_untagged_spec_is_reported_as_zero_not_missing(tmp_path):
    p = _project(tmp_path)
    _spec(p, "# Spec\n## Purpose\nA thing with no commitment tags.\n")
    out = _run(p).stdout
    assert "no spec at" not in out
    assert "0 commitment tags" in out
    assert "not graded" in out


def test_missing_code_map_says_missing(tmp_path):
    out = _run(_project(tmp_path)).stdout
    assert "no code map at" in out


# ------------------------------------------------------------------ counting

def test_commitment_tags_are_counted_per_element(tmp_path):
    p = _project(tmp_path)
    _spec(p, "\n".join([
        "# Spec", "## Features",
        "- a — commitment: locked",
        "- b — commitment: provisional",
        "- c — commitment: provisional",
        "- d — commitment: unspecified",
        "## Stack", "- db: TBD → decision-engineer",
    ]))
    data = json.loads(_run(p, "--json").stdout)["intent"]
    assert data["commitment"] == {"locked": 1, "provisional": 2, "unspecified": 1}
    assert data["open_decisions"] == 1


def test_a_word_that_merely_mentions_commitment_is_not_counted(tmp_path):
    """Prose about commitment is not a tag; counting it would inflate every spec."""
    p = _project(tmp_path)
    _spec(p, "# Spec\nWe should discuss commitment and whether locked is right.\n")
    assert json.loads(_run(p, "--json").stdout)["intent"]["commitment_total"] == 0


def test_parked_items_are_surfaced_as_blocked_on_the_reader(tmp_path):
    p = _project(tmp_path)
    pk = p / ".workflow" / "parked"
    pk.mkdir()
    (pk / "c1.json").write_text(json.dumps(
        {"item": "item-9", "kind": "qa", "question": "does this look right?"}))
    out = _run(p).stdout
    assert "BLOCKED ON YOU" in out
    assert "item-9" in out


def test_verified_items_are_counted_from_the_verdict_token(tmp_path):
    p = _project(tmp_path)
    items = p / ".workflow" / "items"
    for name, token in (("i1", "pass: true"), ("i2", "pass: false"), ("i3", "pass: true")):
        d = items / name
        d.mkdir(parents=True)
        (d / "verify-verdict.md").write_text(token + "\n")
    done = json.loads(_run(p, "--json").stdout)["done"]
    assert done["item_count"] == 3
    assert done["verified_count"] == 2


# ------------------------------------------------------------------ reading the right project

def test_docs_root_split_is_honoured_so_org_mode_reads_its_own_docs(tmp_path):
    """The org-mode case: derived docs live under .workflow/, NOT the owner's docs/.

    If this regressed, `status` would read (and report) the OWNER's spec as the project's own --
    exactly the boundary org mode exists to hold.
    """
    p = _project(tmp_path, config={"project_root": ".", "docs_root": ".workflow"})
    _spec(p / ".workflow", "# Ours\n## F\n- x — commitment: locked\n")
    _spec(p, "# THEIRS — the owner's own spec\n## G\n- y — commitment: provisional\n")

    s = json.loads(_run(p, "--json").stdout)
    assert s["intent"]["present"]
    assert s["intent"]["commitment"] == {"locked": 1, "provisional": 0, "unspecified": 0}
    assert ".workflow" in s["intent"]["source"]


def test_absent_docs_root_falls_back_to_the_project_root(tmp_path):
    p = _project(tmp_path, config={"project_root": "."})
    _spec(p, "# Spec\n## F\n- x — commitment: locked\n")
    assert json.loads(_run(p, "--json").stdout)["intent"]["commitment"]["locked"] == 1


# ------------------------------------------------------------------ generated, never stored

def test_it_writes_nothing(tmp_path):
    p = _project(tmp_path)
    _spec(p, "# Spec\n## F\n- x — commitment: locked\n")
    before = {str(q) for q in p.rglob("*")}
    _run(p)
    _run(p, "--json")
    assert {str(q) for q in p.rglob("*")} == before


def test_it_survives_a_project_that_is_not_a_git_repo(tmp_path):
    p = _project(tmp_path)
    r = _run(p)
    assert r.returncode == 0
    assert "git unavailable" in r.stdout


def test_malformed_json_sources_degrade_rather_than_crash(tmp_path):
    p = _project(tmp_path)
    (p / ".workflow" / "state.json").write_text("{not json")
    (p / "docs" / "knowledge").mkdir(parents=True)
    (p / "docs" / "knowledge" / "graph.json").write_text("{not json")
    r = _run(p)
    assert r.returncode == 0
    assert "the loop has never run here" in r.stdout
    assert "no code map at" in r.stdout
