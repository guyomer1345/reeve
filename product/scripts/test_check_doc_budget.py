"""Tests for scripts/check_doc_budget.py — the context-budget gate.

What these pin down is mostly the JUDGMENT in the gate rather than the arithmetic: that the
hard tier fails and the advisory tier does not, that the estimator errs high rather than low
(erring low means a file that cannot be read passes), that the volatile tier is out of scope
on purpose, and that a fresh install is GREEN — a gate that fires on a clean bootstrap trains
a human to ignore it, which is the failure mode that makes the whole thing worthless.
"""
import json
import os
import subprocess
import sys

import pytest

import check_doc_budget as db

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check_doc_budget.py")


# ---------------------------------------------------------------- fixtures

def _project(root, project_root=".", doc_budget=None):
    os.makedirs(os.path.join(root, ".workflow"), exist_ok=True)
    cfg = {"project_root": project_root}
    if doc_budget is not None:
        cfg["doc_budget"] = doc_budget
    with open(os.path.join(root, ".workflow", "config.json"), "w") as fh:
        json.dump(cfg, fh)
    return root


def _write(root, rel, tokens=None, chars=None):
    """A file sized in ESTIMATED tokens (at the shipped 3.2 ratio) or raw characters."""
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    n = chars if chars is not None else int(tokens * 3.2)
    with open(path, "w") as fh:
        fh.write("x" * n)
    return path


def _scan(root):
    return db.scan(str(root))


def _tiers(res):
    return {r["path"]: r["tier"] for r in res["files"]}


# ---------------------------------------------------------------- the roles

def test_a_fresh_bootstrap_is_green(tmp_path):
    """The load-bearing one. The package's own always-loaded templates are ~3.4k tokens, so
    an aggressive-only budget would have made this gate RED on every clean install — and a
    gate that fires on a fresh install is a gate a human learns to skip."""
    root = _project(tmp_path)
    _write(root, "CLAUDE.md", tokens=3300)
    _write(root, ".workflow/loop.md", tokens=3400)
    res = _scan(root)
    assert res["over"] == [], "a clean install must not fail the gate"
    assert len(res["advisories"]) == 2, "but the sub-1k aspiration must stay visible"


def test_always_loaded_and_on_demand_get_different_budgets(tmp_path):
    root = _project(tmp_path)
    _write(root, "CLAUDE.md", tokens=5000)          # over the always HARD (4000)
    _write(root, "docs/spec.md", tokens=5000)       # nowhere near the on-demand HARD (25000)
    tiers = _tiers(_scan(root))
    assert tiers["CLAUDE.md"] == "over"
    assert tiers["docs/spec.md"] == "ok"

def test_the_on_demand_hard_wall_is_the_read_ceiling(tmp_path):
    """Not a preference: a file over it mechanically cannot be loaded in one call, which is
    why it is the number that FAILS rather than the number that warns."""
    root = _project(tmp_path)
    assert db.DEFAULTS["ondemand_hard"] == 25000
    _write(root, "docs/spec.md", tokens=25001)
    assert _tiers(_scan(root))["docs/spec.md"] == "over"


def test_rules_knowledge_and_decisions_are_all_on_demand(tmp_path):
    root = _project(tmp_path)
    _write(root, "rules/python.md", tokens=100)
    _write(root, "docs/knowledge/src/app.py.md", tokens=100)
    _write(root, "docs/decisions/0001-stack.md", tokens=100)
    roles = {r["path"]: r["role"] for r in _scan(root)["files"]}
    assert roles["rules/python.md"] == db.ONDEMAND
    assert roles["docs/knowledge/src/app.py.md"] == db.ONDEMAND
    assert roles["docs/decisions/0001-stack.md"] == db.ONDEMAND


def test_a_nested_project_root_is_honoured(tmp_path):
    """Greenfield puts the product under `./project`, so the docs are not at the repo root."""
    root = _project(tmp_path, project_root="./project")
    _write(root, "project/docs/spec.md", tokens=100)
    assert "project/docs/spec.md" in _tiers(_scan(root))


def test_the_volatile_tier_is_deliberately_out_of_scope(tmp_path):
    """`handoff.md` is already capped mechanically, at injection time, by the SessionStart
    hook. A second budget here would be a second owner of one bound, and the two would
    drift — so its absence is a decision, and this test is what states it."""
    root = _project(tmp_path)
    _write(root, ".workflow/handoff.md", tokens=9000)
    _write(root, ".workflow/state.json", tokens=9000)
    paths = _tiers(_scan(root))
    assert ".workflow/handoff.md" not in paths
    assert ".workflow/state.json" not in paths


# ---------------------------------------------------------------- the estimator

def test_the_estimator_errs_HIGH_not_low(tmp_path):
    """Under-reporting is the one failure this must not have: it lets a file that cannot be
    read pass the gate. The measured bound is <= 3.40 chars/token, so the shipped 3.2 divisor
    and the round-UP both push the same way."""
    assert db.DEFAULTS["chars_per_token"] <= 3.4
    assert db.estimate_tokens("x" * 100, 3.2) == 32     # 31.25 rounded up
    assert db.estimate_tokens("", 3.2) == 0


def test_the_chars_per_four_rule_of_thumb_would_have_missed_the_measured_failure():
    """This project's roadmap was 85 083 characters when it PAGED at the 25 000-token
    ceiling. The usual `chars/4` heuristic scores that file under the wall — so it would have
    passed the gate. That measurement is why the divisor is what it is."""
    measured_chars = 85083
    assert db.estimate_tokens("x" * measured_chars, 4.0) < 25000, "chars/4 is unsafe here"
    assert db.estimate_tokens("x" * measured_chars, db.DEFAULTS["chars_per_token"]) > 25000


def test_the_ratio_is_a_knob_because_code_dense_docs_tokenize_worse(tmp_path):
    root = _project(tmp_path, doc_budget={"chars_per_token": 2.0})
    _write(root, "docs/spec.md", chars=52000)   # 26 000 tok at 2.0; 16 250 at 3.2
    assert _tiers(_scan(root))["docs/spec.md"] == "over"


def test_budget_overrides_are_read_and_junk_is_ignored(tmp_path):
    root = _project(tmp_path, doc_budget={"always_hard": 500, "bogus": 1, "always_advisory": -3})
    _write(root, "CLAUDE.md", tokens=800)
    res = _scan(root)
    assert res["budgets"]["always_hard"] == 500
    assert res["budgets"]["always_advisory"] == db.DEFAULTS["always_advisory"], \
        "a nonsense override must fall back, not poison the budget"
    assert res["over"] and res["over"][0]["path"] == "CLAUDE.md"


# ---------------------------------------------------------------- the two tiers as behaviour

def test_check_fails_on_hard_and_report_never_does(tmp_path):
    """The whole point of the second tier: an advisory schedules work, it does not stop a
    commit. `--report` must be safe to run anywhere, including over a hard breach."""
    root = _project(tmp_path)
    _write(root, "docs/spec.md", tokens=30000)
    assert db.main(["--project-root", str(root)]) == 1
    assert db.main(["--project-root", str(root), "--report"]) == 0

    root2 = _project(tmp_path / "b")
    _write(root2, "CLAUDE.md", tokens=3300)              # advisory only
    assert db.main(["--project-root", str(root2)]) == 0


def test_the_remedy_for_prose_is_split_and_pointer_never_deletion(tmp_path):
    """Over-budget is a TICKET. You cannot drop half a spec doc to git the way retention
    drops a Sessions entry, so the gate names the split and never performs it."""
    root = _project(tmp_path)
    _write(root, "docs/spec.md", tokens=30000)
    out = db.render(_scan(root), report=True)
    assert "split-and-pointer" in out
    assert "doc-budget: detail split" in out
    assert "never by deleting" in out


def test_an_always_loaded_breach_says_why_it_is_expensive(tmp_path):
    root = _project(tmp_path)
    _write(root, "CLAUDE.md", tokens=3300)
    out = db.render(_scan(root), report=True)
    assert "every turn" in out


def test_json_is_machine_readable(tmp_path, capsys):
    root = _project(tmp_path)
    _write(root, "docs/spec.md", tokens=100)
    db.main(["--project-root", str(root), "--report", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["budgets"]["ondemand_hard"] == 25000
    assert payload["files"][0]["path"] == "docs/spec.md"


# ---------------------------------------------------------------- robustness

def test_an_uninitialised_project_says_nothing_and_exits_zero(tmp_path):
    """It runs on the commit gate, so on a tree with no docs yet it must be quiet, not loud."""
    assert db.main(["--project-root", str(tmp_path)]) == 0


def test_a_malformed_config_falls_back_to_the_shipped_defaults(tmp_path):
    os.makedirs(os.path.join(tmp_path, ".workflow"))
    with open(os.path.join(tmp_path, ".workflow", "config.json"), "w") as fh:
        fh.write("{not json")
    b, proot = db.budgets(str(tmp_path))
    assert b == db.DEFAULTS and proot == "."


def test_runs_as_a_subprocess_the_way_checks_sh_calls_it(tmp_path):
    root = _project(tmp_path)
    _write(root, "docs/spec.md", tokens=30000)
    r = subprocess.run([sys.executable, SCRIPT, "--project-root", str(root)],
                       capture_output=True, text=True)
    assert r.returncode == 1
    assert "BLOCKED" in r.stdout


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


# ------------------------------------------------- following the split pointer
# A split moves sections OUT of a doc, so a consumer that PARSES the survivor alone reads
# less than the schema declares. These pin the resolver the two contract gates read through
# — and, just as load-bearing, that the SIZER deliberately does not follow it.

def _survivor(root, detail_rel, sha=None, body="alpha\n"):
    marker = (db.SPLIT_MARKER % (detail_rel, sha)) if sha else (db.SPLIT_MARKER_SIBLING % detail_rel)
    path = os.path.join(root, "doc.md")
    with open(path, "w") as fh:
        fh.write("# doc\n\n%s\n\n%s" % (marker, body))
    return path


def test_a_live_sibling_pointer_is_followed(tmp_path):
    root = str(tmp_path)
    with open(os.path.join(root, "detail.md"), "w") as fh:
        fh.write("omega\n")
    text, unresolved = db.read_with_splits(_survivor(root, "detail.md"))
    assert "alpha" in text and "omega" in text
    assert unresolved == []


def test_an_archived_pointer_carries_a_sha_and_a_sibling_pointer_does_not(tmp_path):
    """The two forms exist because the first real customer split into a LIVE sibling —
    stamping a sha on a file still being edited would send a reader to git for nothing."""
    root = str(tmp_path)
    assert "@" in db.SPLIT_MARKER % ("d.md", "abc1234")
    assert "@" not in db.SPLIT_MARKER_SIBLING % "d.md"
    for marker in (db.SPLIT_MARKER % ("detail.md", "abc1234"), db.SPLIT_MARKER_SIBLING % "detail.md"):
        assert db.split_pointers(marker)[0][0] == "detail.md"


def test_archived_detail_absent_from_disk_is_normal_not_an_error(tmp_path):
    """`@ <sha>` means the content lives in git. Absence is the design, not a fault."""
    root = str(tmp_path)
    text, unresolved = db.read_with_splits(_survivor(root, "gone.md", sha="abc1234"))
    assert unresolved == []
    assert "alpha" in text


def test_a_missing_LIVE_sibling_is_reported_never_swallowed(tmp_path):
    """A silently skipped half reads as 'all clear' — the failure this whole thing avoids."""
    root = str(tmp_path)
    text, unresolved = db.read_with_splits(_survivor(root, "gone.md"))
    assert len(unresolved) == 1 and "gone.md" in unresolved[0]


def test_pointers_are_followed_recursively_and_cycles_terminate(tmp_path):
    root = str(tmp_path)
    with open(os.path.join(root, "a.md"), "w") as fh:
        fh.write("AAA\n" + db.SPLIT_MARKER_SIBLING % "b.md")
    with open(os.path.join(root, "b.md"), "w") as fh:
        fh.write("BBB\n" + db.SPLIT_MARKER_SIBLING % "doc.md")   # cycle back to the survivor
    text, unresolved = db.read_with_splits(_survivor(root, "a.md"))
    assert "alpha" in text and "AAA" in text and "BBB" in text
    assert unresolved == []


def test_the_SIZER_does_not_follow_the_pointer(tmp_path):
    """The counterpart to everything above, and the reason the resolver is opt-in: the
    survivor is under the wall *because* the detail moved out. A sizer that followed the
    pointer would re-add the bytes and report the split as having achieved nothing. The
    detail is budgeted, but as its OWN row -- otherwise the remedy produces a file the gate
    stopped watching, free to grow back through the wall."""
    root = _project(str(tmp_path))
    _write(root, "docs/spec.md", tokens=20000)
    with open(os.path.join(root, "docs", "spec.md"), "a") as fh:
        fh.write("\n" + db.SPLIT_MARKER_SIBLING % "spec-detail.md")
    _write(root, "docs/spec-detail.md", tokens=20000)
    rows = {r["path"]: r for r in _scan(root)["files"]}
    assert rows["docs/spec.md"]["tokens"] < 25000        # judged alone, and it passes
    assert rows["docs/spec-detail.md"]["tokens"] < 25000  # the detail is sized on its own


def test_a_split_detail_file_is_itself_budgeted(tmp_path):
    """The remedy must not produce a file the gate stopped watching: a detail half that
    grows back through the wall is exactly the failure the split was meant to fix."""
    root = _project(str(tmp_path))
    _write(root, "docs/spec.md", tokens=1000)
    with open(os.path.join(root, "docs", "spec.md"), "a") as fh:
        fh.write("\n" + db.SPLIT_MARKER_SIBLING % "spec-detail.md")
    _write(root, "docs/spec-detail.md", tokens=26000)
    result = _scan(root)
    over = {r["path"] for r in result["over"]}
    assert "docs/spec-detail.md" in over
    assert "docs/spec.md" not in over


def test_a_detail_split_out_of_an_always_loaded_file_is_on_demand(tmp_path):
    """Breaking detail out of `CLAUDE.md` is the always-tier remedy; what lands is by
    definition no longer read every turn, so it must not inherit the always-loaded budget."""
    root = _project(str(tmp_path))
    _write(root, "CLAUDE.md", tokens=900)
    with open(os.path.join(root, "CLAUDE.md"), "a") as fh:
        fh.write("\n" + db.SPLIT_MARKER_SIBLING % "docs/brief-detail.md")
    _write(root, "docs/brief-detail.md", tokens=3000)   # over always_hard, under ondemand_hard
    rows = {r["path"]: r for r in _scan(root)["files"]}
    assert rows["docs/brief-detail.md"]["role"] == db.ONDEMAND
    assert rows["docs/brief-detail.md"]["tier"] == "ok"
