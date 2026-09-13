"""Tests for scripts/check-template-budgets.py — the context budget enforced AT SOURCE.

What these pin down is the JUDGMENT rather than the arithmetic, because the arithmetic is
deliberately not this script's: the estimator, the numbers and the role rule are all imported
from the shipped gate, and a test that re-derived them here would be the second copy the whole
design exists to avoid. So what is tested is the part that is genuinely new —

  * that the template -> destination mapping really is read from `update_reconcile.py` and not
    restated (including the orchestrator brief, whose source path is parsed out of a function
    body because there is no constant to import);
  * that the role a template gets is the role the SHIPPED classifier assigns its installed
    destination — which is why `loop-detail.md` is on-demand, and why it stops being
    classifiable at all the moment `loop.md` loses its split pointer;
  * that the always-loaded TOTAL fails even when every single file is under its own cap. That
    is D184's entire point and the one bound the per-file cap structurally cannot see;
  * that a new template nobody mapped FAILS rather than being skipped. Silent skipping is this
    gate's own defect one level up: it is how the next always-loaded file ships unmeasured.

Fixtures only. Nothing here reads or writes the real `product/templates/`, except the two
tests that deliberately assert against the live repo (the mapping's shape, and the fact that
this script does not ship).
"""
import importlib.util
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCRIPT = os.path.join(HERE, "check-template-budgets.py")

# The filename is hyphenated, matching its meta-only siblings (`check-status-coherence.sh`,
# `check-no-spec-refs.sh`), so it is not importable by name. Load it by path.
_spec = importlib.util.spec_from_file_location("check_template_budgets", SCRIPT)
tb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tb)

db = tb.db   # the shipped gate, as the script itself sees it
ur = tb.ur   # the mapping's owner

MARKER = "<!-- doc-budget: detail split -> loop-detail.md -->"


# ---------------------------------------------------------------- fixtures

def _write(root, rel, tokens, head=""):
    """A template sized in ESTIMATED tokens at the shipped ratio, with an optional head line."""
    path = os.path.join(root, "product", "templates", rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    head = (head + "\n") if head else ""
    body = "x" * max(0, int(tokens * db.DEFAULTS["chars_per_token"]) - len(head))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(head + body)
    return path


def _repo(tmp_path, loop=1000, detail=1000, brief=1000, marker=True, directives=200):
    """A fixture repo carrying only `product/templates/` — the mapping and the sizer still come
    from the real checkout, because those are the LOGIC under test, not the data.

    EVERY mapped template must be written here, seeds included: an owner that maps a file this
    fixture does not create is a `MISSING` finding, and the gate is right to say so. So the
    fixture tracks the owner rather than the owner tracking the fixture — `directives.md` is
    small by default because it is a seed, and because its size is not what any of these tests
    are about."""
    root = str(tmp_path)
    _write(root, "loop.md", loop, head=MARKER if marker else "")
    _write(root, "loop-detail.md", detail)
    _write(root, "orchestrator-CLAUDE.md", brief)
    _write(root, "directives.md", directives)
    return root


def _budgets(**over):
    b = dict(db.DEFAULTS)
    b.update(over)
    return b


def _tiers(res):
    return {r["template"].rsplit("/", 1)[-1]: r["tier"] for r in res["files"]}


def _roles(res):
    return {r["template"].rsplit("/", 1)[-1]: r["role"] for r in res["files"]}


def _run(root, *args):
    return subprocess.run([sys.executable, SCRIPT, "--repo-root", root, *args],
                          capture_output=True, text=True)


# ---------------------------------------------------------------- the mapping has one owner

def test_the_mapping_is_read_from_update_reconcile_not_restated():
    """Every whole-file pair must be exactly what `update_reconcile.TEMPLATES` declares. If the
    owner adds a template tomorrow, this gate must already know about it."""
    pairs = dict(tb.template_map())
    for src, dest in ur.TEMPLATES:
        assert pairs[("product/" + src).replace(os.sep, "/")] == dest.replace(os.sep, "/")


def test_the_orchestrator_brief_is_mapped_to_the_project_root_brief():
    """The brief is the one pair that is not in `TEMPLATES` — it is a managed BLOCK inside the
    target's root CLAUDE.md, handled separately by the same owner. Missing it would leave the
    heaviest always-loaded file out of the total, which is the bug wearing a different hat."""
    pairs = dict(tb.template_map())
    assert pairs["product/templates/orchestrator-CLAUDE.md"] == "CLAUDE.md"


def test_a_moved_owner_fails_loudly_rather_than_budgeting_one_file_fewer(monkeypatch):
    """The brief's source path is PARSED out of a function body, so the parse can rot. When it
    does, the gate must break — a mapping that silently gets shorter is a gate that silently
    stops measuring the file it was written for."""
    def renamed(plugin_root, project_root):
        return os.path.join(plugin_root, "elsewhere", "brief.md")
    monkeypatch.setattr(ur, "render_brief", renamed)
    with pytest.raises(tb.MappingError):
        tb.template_map()


def test_non_markdown_templates_are_out_of_scope(tmp_path):
    """`checks.sh` and `settings.json` are mapped by the same owner and are deliberately not
    budgeted: the doc budget is a budget on prose a session reads, not on shipped code."""
    root = _repo(tmp_path)
    with open(os.path.join(root, "product", "templates", "checks.sh"), "w") as fh:
        fh.write("#!/usr/bin/env bash\n" + "x" * 200000)
    res = tb.scan(root)
    assert "checks.sh" not in _tiers(res)
    assert not res["unmapped"], "a non-markdown template must not read as uncovered"
    assert not tb.failed(res)


# ---------------------------------------------------------------- the role has one owner

def test_the_role_is_whatever_the_shipped_classifier_gives_the_destination(tmp_path):
    """Not decided here: each template is materialised at its installed path and
    `check_doc_budget.workflow_docs()` is asked. loop.md and the brief land on always-loaded
    paths; loop-detail.md is reached only through a split pointer, so it is on-demand whatever
    its referrer was."""
    res = tb.scan(_repo(tmp_path))
    assert _roles(res) == {"loop.md": db.ALWAYS,
                           "orchestrator-CLAUDE.md": db.ALWAYS,
                           "directives.md": db.ALWAYS,
                           "loop-detail.md": db.ONDEMAND}


def test_the_split_pointer_is_what_makes_the_detail_reachable(tmp_path):
    """Drop the marker from loop.md and the detail file becomes unreachable from the installed
    tree — the classifier gives it no role, so it has no budget, so the gate fails. A detail
    half growing back through the wall unseen is exactly what the split remedy must not allow."""
    root = _repo(tmp_path, marker=False)
    res = tb.scan(root)
    assert [p["kind"] for p in res["unmapped"]] == ["unclassified"]
    assert tb.failed(res)


def test_the_on_demand_half_gets_the_read_ceiling_not_the_always_cap(tmp_path):
    """A detail file far over `always_hard` is fine — it is not rent. Under the on-demand wall
    it is simply a document."""
    res = tb.scan(_repo(tmp_path, detail=db.DEFAULTS["always_hard"] * 3))
    assert _tiers(res)["loop-detail.md"] == "ok"
    assert not tb.failed(res)


# ---------------------------------------------------------------- the two bounds

def test_a_template_over_its_per_file_hard_budget_fails(tmp_path):
    root = _repo(tmp_path, loop=db.DEFAULTS["always_hard"] + 1)
    res = tb.scan(root)
    assert _tiers(res)["loop.md"] == "over"
    assert tb.failed(res)
    assert "OVER BUDGET" in tb.render(res, report=False)
    assert _run(root).returncode == 1


def test_the_always_loaded_total_fails_when_every_file_is_under_its_own_cap(tmp_path):
    """D184's whole point, and the reason the per-file cap was capping the wrong thing. Two
    files each comfortably under `always_hard` still cost the sum of both before a word is
    typed, and only the TOTAL bound can see that number."""
    b = _budgets(always_hard=4000, always_total_hard=7000, always_total_advisory=6400)
    root = _repo(tmp_path, loop=3900, brief=3900, directives=0)
    res = tb.scan(root, budgets=b)

    assert res["over"] == [], "no single file is over its own cap"
    assert all(r["tier"] != "over" for r in res["files"])
    assert res["total"]["tokens"] == 7800
    assert res["total"]["tier"] == "over"
    assert tb.failed(res), "the set is over the ceiling even though every file is under cap"

    out = tb.render(res, report=False)
    assert "always-loaded TOTAL HARD" in out
    assert "7800" in out and "7000" in out, "the verdict must state the numbers"


def test_the_total_sums_the_always_loaded_tier_only(tmp_path):
    """The on-demand tier is deliberately not totalled: nothing loads it until something needs
    it, so summing it would fail a package for owning documentation."""
    res = tb.scan(_repo(tmp_path, loop=1000, brief=1000, detail=9000, directives=500))
    assert res["total"]["files"] == 3
    assert res["total"]["tokens"] == 2500


# ---------------------------------------------------------------- coverage

def test_an_unmapped_new_template_fails(tmp_path):
    """A new `product/templates/*.md` that no owner maps must FAIL, not be skipped. Silent
    skipping is how the next always-loaded file ships unmeasured — this gate's own defect one
    level up."""
    root = _repo(tmp_path)
    _write(root, "new-always-loaded-thing.md", 500)
    res = tb.scan(root)
    assert [p["template"] for p in res["unmapped"]] == \
        ["product/templates/new-always-loaded-thing.md"]
    assert res["unmapped"][0]["kind"] == "unmapped"
    assert res["over"] == [] and res["total"]["tier"] == "ok", \
        "nothing is over budget — the failure is purely that a template carries no budget"
    assert tb.failed(res)
    assert "UNMAPPED" in tb.render(res, report=False)
    assert _run(root).returncode == 1


def test_a_mapped_template_that_is_not_on_disk_fails(tmp_path):
    """The mirror case: the owner promises to install a file the package does not have. That
    is a broken install, not a smaller package."""
    root = _repo(tmp_path)
    os.remove(os.path.join(root, "product", "templates", "loop-detail.md"))
    res = tb.scan(root)
    assert [p["kind"] for p in res["unmapped"]] == ["missing"]
    assert tb.failed(res)


# ---------------------------------------------------------------- tiers and modes

def test_advisories_do_not_fail(tmp_path):
    """The warning tier must stay a warning. An advisory that fails a build is a hard cap with
    a softer name, and a tier that is tripped forever is a tier nobody reads (D184)."""
    b = _budgets(always_hard=4000, always_advisory=3200)
    root = _repo(tmp_path, loop=3500, brief=1000)
    res = tb.scan(root, budgets=b)
    assert _tiers(res)["loop.md"] == "advisory"
    assert res["over"] == []
    assert not tb.failed(res)
    assert _run(root).returncode == 0, "the real defaults must not fail on this fixture either"


def test_advisories_are_silent_in_check_mode_and_visible_in_report(tmp_path):
    b = _budgets(always_hard=4000, always_advisory=3200)
    res = tb.scan(_repo(tmp_path, loop=3500, brief=1000), budgets=b)
    assert "ADVISORY" not in tb.render(res, report=False)
    assert "ADVISORY" in tb.render(res, report=True)


def test_the_total_advisory_band_warns_without_failing(tmp_path):
    b = _budgets(always_total_hard=8000, always_total_advisory=6400)
    res = tb.scan(_repo(tmp_path, loop=3400, brief=3400), budgets=b)
    assert res["total"]["tier"] == "advisory"
    assert not tb.failed(res)
    assert "always-loaded TOTAL" in tb.render(res, report=True)


def test_report_exits_zero_even_on_a_red_repo(tmp_path):
    """`--report` is the read-only view. It must be safe to run anywhere, including on a tree
    that the gate would otherwise block."""
    root = _repo(tmp_path, loop=db.DEFAULTS["always_hard"] + 500)
    _write(root, "unmapped-too.md", 100)
    assert _run(root).returncode == 1, "the fixture must really be red"
    done = _run(root, "--report")
    assert done.returncode == 0
    assert "OVER BUDGET" in done.stdout and "UNMAPPED" in done.stdout


def test_report_lists_every_template_with_its_numbers(tmp_path):
    """A human must be able to act on the output without rerunning anything, which means the
    in-budget rows and their estimates are part of the report, not just the breaches."""
    out = _run(_repo(tmp_path), "--report").stdout
    for name in ("loop.md", "loop-detail.md", "orchestrator-CLAUDE.md"):
        assert name in out
    assert "always-loaded set" in out


def test_json_mode_carries_the_verdict_for_a_machine(tmp_path):
    root = _repo(tmp_path, loop=db.DEFAULTS["always_hard"] + 1)
    done = _run(root, "--json")
    assert done.returncode == 1
    got = json.loads(done.stdout)
    assert got["over"] and got["total"]["role"] == db.ALWAYS
    assert got["budgets"]["always_total_hard"] == db.DEFAULTS["always_total_hard"]
    assert {r["installs_to"] for r in got["files"]} >= {".workflow/loop.md", "CLAUDE.md"}


def test_a_clean_package_is_green(tmp_path):
    """The same discipline the shipped gate holds itself to: a gate that fires on a healthy
    tree is a gate a human learns to skip."""
    root = _repo(tmp_path, loop=2000, brief=2000, detail=2000)
    done = _run(root)
    assert done.returncode == 0
    assert done.stdout.startswith("OK: template budget")


# ---------------------------------------------------------------- it must never ship

def test_this_gate_is_meta_only_and_cannot_leak_into_the_package():
    """It reads `product/templates/` as SOURCE and binds the packager, not the driven project.
    The ship line is `product/MANIFEST.json` and this file sits outside `product/` entirely, so
    `build-release.py` cannot reach it — asserted rather than assumed."""
    assert not os.path.abspath(SCRIPT).startswith(os.path.join(REPO, "product") + os.sep)
    manifest = open(os.path.join(REPO, "product", "MANIFEST.json"), encoding="utf-8").read()
    assert "check-template-budgets" not in manifest
    assert "check_template_budgets" not in manifest


def test_it_rides_the_meta_repo_pre_commit():
    """A gate nothing runs is a gate that does not exist — the defect it closes was precisely a
    measurement nobody took."""
    hook = os.path.join(REPO, ".git", "hooks", "pre-commit")
    if not os.path.isfile(hook):
        pytest.skip("no .git/hooks/pre-commit in this checkout")
    assert "check-template-budgets.py" in open(hook, encoding="utf-8").read()


def test_the_live_repo_is_measurable():
    """Not an assertion about the READING — the numbers are the maintainer's to move. Only that
    the instrument resolves the real mapping, classifies every real template, and produces a
    verdict rather than an exception."""
    res = tb.scan(REPO)
    assert res["files"], "the real package must produce measurable rows"
    assert all(r["role"] in (db.ALWAYS, db.ONDEMAND) for r in res["files"])
    assert isinstance(tb.failed(res), bool)
