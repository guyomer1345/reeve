"""Tests for scripts/update_reconcile.py — /update's fixed reconcile runner.

The arithmetic these cover is the whole reason the runner ships fixed rather than being
re-derived from prose each update: the proven-orphan set difference, the "was this
hand-edited?" hash check, and — the load-bearing one — that an apply writes ONLY
package-owned paths and leaves every target-owned artifact byte-identical.
"""
import json
import os
import shutil
from pathlib import Path

import pytest

import update_reconcile as ur


# ---------------------------------------------------------------- fixtures

def _plugin(root, version="0.2.0", extra_install=(), drop=()):
    """A minimal but structurally real package: a manifest, a dir entry with an excluded
    test file, the three templates, and the orchestrator brief.

    `version=None` omits the field entirely — the SHIPPED shape since D164 deleted it. The
    reconcile tests below keep a pin, because what they exercise is the hash arithmetic and
    a stable version keeps their intent legible; `TestPluginVersion` covers the real chain.
    """
    tag = version or "nover"
    root.mkdir(parents=True, exist_ok=True)
    (root / ".claude-plugin").mkdir(exist_ok=True)
    meta = {"name": "reeve"}
    if version is not None:
        meta["version"] = version
    (root / ".claude-plugin" / "plugin.json").write_text(json.dumps(meta))

    (root / "scripts" / "codemap").mkdir(parents=True, exist_ok=True)
    (root / "scripts" / "bus.py").write_text("# bus v%s\n" % tag)
    (root / "scripts" / "codemap" / "codemap.py").write_text("# codemap v%s\n" % tag)
    (root / "scripts" / "codemap" / "test_codemap.py").write_text("# MUST NOT INSTALL\n")
    # Build cruft a working-directory plugin source carries: a `.pyc` basename is not a
    # `*.py`, so it slips past a `test_*.py`-only exclude.
    (root / "scripts" / "codemap" / "__pycache__").mkdir(exist_ok=True)
    (root / "scripts" / "codemap" / "__pycache__" / "codemap.cpython-314.pyc").write_bytes(b"\x00cruft")
    (root / "hooks").mkdir(exist_ok=True)
    (root / "hooks" / "guard.sh").write_text("# guard v%s\n" % tag)

    install = [
        {"src": "scripts/bus.py", "dest": ".claude/scripts/bus.py"},
        {"src": "scripts/codemap", "dest": ".claude/scripts/codemap"},
        {"src": "hooks/guard.sh", "dest": ".claude/hooks/guard.sh"},
    ]
    for e in extra_install:
        (root / e["src"]).parent.mkdir(parents=True, exist_ok=True)
        (root / e["src"]).write_text("# %s v%s\n" % (e["dest"], tag))
        install.append(e)
    install = [e for e in install if e["dest"] not in drop]

    (root / "MANIFEST.json").write_text(json.dumps(
        {"plugin": "reeve", "ship": ["scripts"],
         "exclude": ["**/test_*.py", "**/*.pyc", "**/*.pyo"], "install": install}))

    (root / "templates").mkdir(exist_ok=True)
    (root / "templates" / "loop.md").write_text("# loop v%s\n" % tag)
    (root / "templates" / "checks.sh").write_text("#!/usr/bin/env bash\n# checks v%s\n" % tag)
    (root / "templates" / "settings.json").write_text(
        json.dumps({"permissions": {"allow": ["Bash"]}, "version": tag}, indent=2) + "\n")
    (root / "templates" / "orchestrator-CLAUDE.md").write_text(
        "# <project> — Orchestrator\nv%s\nroot=<project_root>\n" % tag)
    (root / "templates" / "directives.md").write_text("# Directives\nseed v%s\n" % tag)
    return root


def _project(root, project_root=".", project=None):
    """A target with target-owned artifacts we assert are never touched."""
    (root / ".workflow" / "items" / "ITEM-1").mkdir(parents=True)
    cfg = {"project_root": project_root, "runner": False, "context": {"warn_pct": 60}}
    if project:
        cfg["project"] = project
    (root / ".workflow" / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
    (root / ".workflow" / "checks.env").write_text('TEST="pytest -q"\n')
    (root / ".workflow" / "backlog.md").write_text("- human backlog\n")
    (root / ".workflow" / "handoff.md").write_text("bootstrap: complete\n")
    (root / ".workflow" / "codemap.sh").write_text("# generated per-stack\n")
    (root / ".workflow" / "items" / "ITEM-1" / "plan.md").write_text("the plan\n")
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "spec.md").write_text("the spec\n")
    return root


def _install(plugin, project, brief=True, seeds=True):
    """Simulate /start step 4+7: copy the package in, wrap the brief, record the ledger.

    `seeds` is a knob because both states are real and they must both be tested: /start seeds
    `.workflow/directives.md`, but a project installed BEFORE seeds existed has no such file
    and /update is what must create it."""
    for dest, src in ur.expected_files(str(plugin), str(project)).items():
        d = project / dest
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, d)
    if seeds:
        for src_rel, dest in ur.SEEDS:
            d = project / dest
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(plugin / src_rel, d)
    body = ur.render_brief(str(plugin), str(project))
    text = "# my project\n\nMy own notes above.\n\n"
    if brief:
        text += ur.BRIEF_BEGIN + body + ur.BRIEF_END + "\n"
    text += "\nMy own notes below.\n"
    (project / "CLAUDE.md").write_text(text)
    ur.main(["record", "--plugin-root", str(plugin), "--project-root", str(project)])
    cfg = json.loads((project / ".workflow" / "config.json").read_text())
    cfg["workflow_version"] = ur.plugin_version(str(plugin))
    (project / ".workflow" / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")


def _snapshot(root):
    out = {}
    for base, _dirs, files in os.walk(root):
        for f in files:
            p = Path(base) / f
            out[str(p.relative_to(root))] = p.read_bytes()
    return out


def _kinds(plan):
    return {a["path"]: a["kind"] for a in plan["actions"]}


@pytest.fixture
def env(tmp_path):
    plugin = _plugin(tmp_path / "pkg_old", version="0.1.0")
    project = _project(tmp_path / "proj")
    _install(plugin, project)
    return tmp_path, plugin, project


# ---------------------------------------------------------------- the expected set

def test_excluded_test_files_never_install(env):
    _tmp, plugin, project = env
    assert not (project / ".claude/scripts/codemap/test_codemap.py").exists()
    assert ".claude/scripts/codemap/test_codemap.py" not in ur.expected_files(
        str(plugin), str(project))


def test_build_cruft_never_installs(env):
    """Found by dry-running `plan` against a real project: a plugin sourced from a working
    directory (a directory-source marketplace, the dev setup) carries __pycache__/*.pyc, and
    a `.pyc` basename does not match a `test_*.py` exclude — so it was planned as an ADD."""
    _tmp, plugin, project = env
    exp = ur.expected_files(str(plugin), str(project))
    assert not any(p.endswith(".pyc") for p in exp), "build cruft leaked into the install set"
    assert not (project / ".claude/scripts/codemap/__pycache__").exists()


def test_directory_entries_expand_per_file(env):
    _tmp, plugin, project = env
    exp = ur.expected_files(str(plugin), str(project))
    assert os.path.join(".claude", "scripts", "codemap", "codemap.py") in exp


# ---------------------------------------------------------------- planning

def test_same_version_same_content_is_a_noop(env):
    _tmp, plugin, project = env
    plan = ur.compute_plan(str(plugin), str(project))
    assert plan["noop"] is True
    # `SEEDED` is the seed tier's own no-op: the file is present, so it is the operator's and
    # nothing happens to it. Grouped with SAME here because "nothing to do" is the assertion.
    assert set(_kinds(plan).values()) == {"SAME", "SEEDED"}


def test_new_version_refreshes_changed_and_adds_new(tmp_path, env):
    _t, _old, project = env
    new = _plugin(tmp_path / "pkg_new", version="0.2.0", extra_install=[
        {"src": "scripts/update_reconcile.py", "dest": ".claude/scripts/update_reconcile.py"}])
    plan = ur.compute_plan(str(new), str(project))
    kinds = _kinds(plan)
    assert plan["noop"] is False
    assert plan["old_version"] == "0.1.0" and plan["new_version"] == "0.2.0"
    assert kinds[os.path.join(".claude", "scripts", "bus.py")] == "REFRESH"
    assert kinds[os.path.join(".claude", "scripts", "update_reconcile.py")] == "ADD"


def test_retired_file_is_a_proven_orphan(tmp_path, env):
    _t, _old, project = env
    new = _plugin(tmp_path / "pkg_new", version="0.2.0",
                  drop={".claude/hooks/guard.sh"})
    kinds = _kinds(ur.compute_plan(str(new), str(project)))
    assert kinds[os.path.join(".claude", "hooks", "guard.sh")] == "ORPHAN"


def test_retired_but_edited_file_is_flagged_never_removed(tmp_path, env):
    _t, _old, project = env
    (project / ".claude" / "hooks" / "guard.sh").write_text("# I patched this locally\n")
    new = _plugin(tmp_path / "pkg_new", version="0.2.0", drop={".claude/hooks/guard.sh"})
    kinds = _kinds(ur.compute_plan(str(new), str(project)))
    assert kinds[os.path.join(".claude", "hooks", "guard.sh")] == "ORPHAN-EDITED"
    ur.main(["apply", "--plugin-root", str(new), "--project-root", str(project),
             "--confirm-overwrite"])
    assert (project / ".claude" / "hooks" / "guard.sh").exists(), "an edited orphan must survive"


def test_unrecorded_file_is_never_an_orphan(tmp_path, env):
    # A file the human dropped into .claude/scripts/ themselves is not ours to remove.
    _t, _old, project = env
    mine = project / ".claude" / "scripts" / "my_own_helper.py"
    mine.write_text("# mine\n")
    new = _plugin(tmp_path / "pkg_new", version="0.2.0")
    assert os.path.join(".claude", "scripts", "my_own_helper.py") not in _kinds(
        ur.compute_plan(str(new), str(project)))
    ur.main(["apply", "--plugin-root", str(new), "--project-root", str(project)])
    assert mine.exists()


def test_no_ledger_means_unknown_old_flag_only(tmp_path):
    # The `idea testing` case: an install from before the ledger existed.
    plugin = _plugin(tmp_path / "pkg_old", version="0.1.0")
    project = _project(tmp_path / "proj")
    _install(plugin, project)
    os.remove(project / ur.LEDGER_REL)
    cfg = json.loads((project / ".workflow" / "config.json").read_text())
    del cfg["workflow_version"]
    (project / ".workflow" / "config.json").write_text(json.dumps(cfg, indent=2))

    new = _plugin(tmp_path / "pkg_new", version="0.2.0", drop={".claude/hooks/guard.sh"})
    plan = ur.compute_plan(str(new), str(project))
    kinds = _kinds(plan)
    assert plan["has_ledger"] is False
    assert plan["old_version"] is None
    assert "ORPHAN" not in kinds.values(), "nothing is provable without a ledger"
    assert (project / ".claude" / "hooks" / "guard.sh").exists()
    assert kinds[os.path.join(".claude", "settings.json")] == "REFRESH?"


# ---------------------------------------------------------------- the confirm gate

def test_locally_edited_settings_blocks_apply(tmp_path, env):
    _t, _old, project = env
    (project / ".claude" / "settings.json").write_text('{"permissions": {"allow": ["Bash", "MY_OWN"]}}')
    new = _plugin(tmp_path / "pkg_new", version="0.2.0")
    plan = ur.compute_plan(str(new), str(project))
    assert _kinds(plan)[os.path.join(".claude", "settings.json")] == "LOCAL-EDIT"
    rc = ur.main(["apply", "--plugin-root", str(new), "--project-root", str(project)])
    assert rc == 2, "an unconfirmed overwrite of an edited settings.json must BLOCK"
    assert "MY_OWN" in (project / ".claude" / "settings.json").read_text()
    rc = ur.main(["apply", "--plugin-root", str(new), "--project-root", str(project),
                  "--confirm-overwrite"])
    assert rc == 0
    assert "MY_OWN" not in (project / ".claude" / "settings.json").read_text()


def test_edited_package_script_refreshes_without_confirmation(tmp_path, env):
    # Only the two human-facing files gate on confirmation; a patched package script is
    # surfaced as LOCAL-EDIT and overwritten (it is package code, restored from the package).
    _t, _old, project = env
    (project / ".claude" / "scripts" / "bus.py").write_text("# patched\n")
    new = _plugin(tmp_path / "pkg_new", version="0.2.0")
    plan = ur.compute_plan(str(new), str(project))
    assert _kinds(plan)[os.path.join(".claude", "scripts", "bus.py")] == "LOCAL-EDIT"
    assert ur.main(["apply", "--plugin-root", str(new), "--project-root", str(project)]) == 0
    assert "bus v0.2.0" in (project / ".claude" / "scripts" / "bus.py").read_text()


# ---------------------------------------------------------------- the brief block

def test_brief_block_refreshes_and_preserves_the_rest_of_claude_md(tmp_path, env):
    _t, _old, project = env
    new = _plugin(tmp_path / "pkg_new", version="0.2.0")
    assert ur.main(["apply", "--plugin-root", str(new), "--project-root", str(project)]) == 0
    text = (project / "CLAUDE.md").read_text()
    assert "My own notes above." in text and "My own notes below." in text
    assert "v0.2.0" in text and "v0.1.0" not in text
    assert text.count(ur.BRIEF_BEGIN) == 1 and text.count(ur.BRIEF_END) == 1


def test_brief_placeholders_are_filled_from_the_target_config(tmp_path):
    plugin = _plugin(tmp_path / "pkg", version="0.1.0")
    project = _project(tmp_path / "proj", project_root="./project")
    _install(plugin, project)
    body, found = ur.read_brief_block(str(project))
    assert found
    assert "root=./project" in body and "<project_root>" not in body
    assert "# proj — Orchestrator" in body  # no config.project ⇒ the basename fallback


def test_the_project_name_comes_from_config_not_the_checkout_directory(tmp_path):
    """A checkout dir named something else must not make /update rename the project."""
    plugin = _plugin(tmp_path / "pkg", version="0.1.0")
    project = _project(tmp_path / "some-checkout-dir", project_root="./project",
                       project="slugify")
    _install(plugin, project)
    body, _ = ur.read_brief_block(str(project))
    assert "# slugify — Orchestrator" in body
    assert "some-checkout-dir" not in body


def test_a_config_named_project_is_not_reported_as_a_local_edit(tmp_path):
    """The regression: the package inventing a difference from itself, then demanding
    --confirm-overwrite over it. A same-version plan must be a clean no-op."""
    plugin = _plugin(tmp_path / "pkg", version="0.1.0")
    project = _project(tmp_path / "some-checkout-dir", project="slugify")
    _install(plugin, project)
    plan = ur.compute_plan(str(plugin), str(project))
    brief = [a for a in plan["actions"] if a["path"] == ur.BRIEF_KEY]
    assert [a["kind"] for a in brief] == ["SAME"], brief


def test_unmarked_brief_is_flagged_not_rewritten(tmp_path):
    plugin = _plugin(tmp_path / "pkg_old", version="0.1.0")
    project = _project(tmp_path / "proj")
    _install(plugin, project, brief=False)
    before = (project / "CLAUDE.md").read_text()
    new = _plugin(tmp_path / "pkg_new", version="0.2.0")
    assert _kinds(ur.compute_plan(str(new), str(project)))[ur.BRIEF_KEY] == "BRIEF-UNMARKED"
    ur.main(["apply", "--plugin-root", str(new), "--project-root", str(project)])
    assert (project / "CLAUDE.md").read_text() == before


# ---------------------------------------------------------------- the boundary

TARGET_OWNED = [
    ".workflow/checks.env",
    ".workflow/backlog.md",
    ".workflow/handoff.md",
    ".workflow/codemap.sh",
    ".workflow/items/ITEM-1/plan.md",
    "docs/spec.md",
]


def test_apply_touches_only_package_owned_paths(tmp_path, env):
    """The mechanical guarantee behind category (b): everything else is byte-identical."""
    _t, _old, project = env
    before = _snapshot(project)
    new = _plugin(tmp_path / "pkg_new", version="0.2.0", extra_install=[
        {"src": "scripts/update_reconcile.py", "dest": ".claude/scripts/update_reconcile.py"}])
    assert ur.main(["apply", "--plugin-root", str(new), "--project-root", str(project)]) == 0
    after = _snapshot(project)

    changed = {p for p in set(before) | set(after) if before.get(p) != after.get(p)}
    allowed = set(ur.expected_files(str(new), str(project))) | {
        "CLAUDE.md", ur.LEDGER_REL, ur.CONFIG_REL}
    assert changed <= allowed, "wrote outside the package-owned set: %s" % (changed - allowed)
    for p in TARGET_OWNED:
        assert before[p] == after[p], "%s is target-owned and must never change" % p


def test_apply_stamps_the_version_and_keeps_human_config_knobs(tmp_path, env):
    _t, _old, project = env
    new = _plugin(tmp_path / "pkg_new", version="0.2.0")
    ur.main(["apply", "--plugin-root", str(new), "--project-root", str(project)])
    cfg = json.loads((project / ".workflow" / "config.json").read_text())
    assert cfg["workflow_version"] == "0.2.0"
    assert cfg["context"] == {"warn_pct": 60} and cfg["runner"] is False


def test_apply_is_idempotent(tmp_path, env):
    _t, _old, project = env
    new = _plugin(tmp_path / "pkg_new", version="0.2.0")
    ur.main(["apply", "--plugin-root", str(new), "--project-root", str(project)])
    after_first = _snapshot(project)
    plan = ur.compute_plan(str(new), str(project))
    assert set(_kinds(plan).values()) == {"SAME", "SEEDED"} and plan["noop"] is True
    ur.main(["apply", "--plugin-root", str(new), "--project-root", str(project)])
    assert _snapshot(project) == after_first


# ------------------------------------------------- seeds: written once, then not ours

def test_a_seed_is_created_when_it_is_absent(tmp_path):
    """The half that makes `/update` able to introduce a seed at all. A project installed before
    `.workflow/directives.md` existed has no such file, and the channel is useless until one is
    there — so an absent seed is an ADD-shaped event, reported as `SEED`."""
    plugin = _plugin(tmp_path / "pkg", version="0.1.0")
    project = _project(tmp_path / "proj")
    _install(plugin, project, seeds=False)
    dest = project / ".workflow" / "directives.md"
    assert not dest.exists()

    assert _kinds(ur.compute_plan(str(plugin), str(project)))[
        os.path.join(".workflow", "directives.md")] == "SEED"
    ur.main(["apply", "--plugin-root", str(plugin), "--project-root", str(project)])
    assert dest.read_text() == (plugin / "templates" / "directives.md").read_text()


def test_a_seed_is_never_refreshed_over_the_operators_edits(tmp_path):
    """The half the whole category exists for, and the one a `TEMPLATES` entry would have got
    WRONG. `.workflow/directives.md` is package-supplied but PROJECT-OWNED: an operator adding a
    standing directive by hand is the entire point of the channel, so an update that refreshed it
    would delete exactly the thing the file was built to keep. Present is terminal, even when the
    new package ships different seed content."""
    old = _plugin(tmp_path / "pkg", version="0.1.0")
    project = _project(tmp_path / "proj")
    _install(old, project)
    mine = "# Directives\n\n## mine\n- type: behavioural\n- entered: 2026-01-01\n- retire: standing\n\nstop at 30%.\n"
    (project / ".workflow" / "directives.md").write_text(mine)

    new = _plugin(tmp_path / "pkg_new", version="0.2.0")   # ships DIFFERENT seed content
    plan = ur.compute_plan(str(new), str(project))
    assert _kinds(plan)[os.path.join(".workflow", "directives.md")] == "SEEDED"
    ur.main(["apply", "--plugin-root", str(new), "--project-root", str(project)])
    assert (project / ".workflow" / "directives.md").read_text() == mine
    # And it is not reported as a local edit needing confirmation — it is not a local edit, it
    # is the file doing what it is for.
    assert not any(a["confirm"] for a in plan["actions"]
                   if a["path"].endswith("directives.md"))


def test_a_seed_is_kept_out_of_the_ledger_so_it_can_never_become_an_orphan(tmp_path):
    """Two failures at once if it were recorded: an edited seed would read as `LOCAL-EDIT` on
    every update, and a package that later stopped shipping the seed would see the operator's own
    file as a provable `ORPHAN` and delete it. The ledger proves package files pristine; a seed is
    EXPECTED to diverge, so it is not the ledger's business."""
    plugin = _plugin(tmp_path / "pkg", version="0.1.0")
    project = _project(tmp_path / "proj")
    _install(plugin, project)
    ur.main(["apply", "--plugin-root", str(plugin), "--project-root", str(project)])
    ledger = json.loads((project / ".workflow" / "install-set.json").read_text())
    assert os.path.join(".workflow", "directives.md") not in ledger["files"]
    assert os.path.join(".workflow", "directives.md") not in ur.expected_files(
        str(plugin), str(project))


def test_checks_sh_stays_executable(tmp_path, env):
    _t, _old, project = env
    new = _plugin(tmp_path / "pkg_new", version="0.2.0")
    ur.main(["apply", "--plugin-root", str(new), "--project-root", str(project)])
    assert os.access(project / ".workflow" / "checks.sh", os.X_OK)


def test_uninitialised_project_is_refused(tmp_path):
    plugin = _plugin(tmp_path / "pkg", version="0.1.0")
    bare = tmp_path / "bare"
    bare.mkdir()
    assert ur.main(["plan", "--plugin-root", str(plugin), "--project-root", str(bare)]) == 1


# ------------------------------------------------- _atomic_write on hostile filesystems
# A repo checkout can sit on a filesystem that does not honour file modes: a WSL /mnt/c
# DrvFs mount without metadata, a CIFS/SMB share, some container bind mounts. There
# `os.chmod` raises EPERM even though the write itself succeeds. An unconditional chmod
# aborted the whole apply -- stranding exactly the checkouts that most need updating --
# and left a `<name>.tmp.update` file behind as unexplained debris.

def test_chmod_failure_does_not_abort_the_write(tmp_path, monkeypatch, capsys):
    """EPERM from chmod must not fail the write: the mode is cosmetic for this package
    (every installed script runs via its interpreter, so no exec bit is load-bearing)."""
    def _boom(*_a, **_k):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(ur.os, "chmod", _boom)
    monkeypatch.setattr(ur, "_chmod_unsupported_warned", False)
    target = tmp_path / "sub" / "guard.sh"

    ur._atomic_write(str(target), "#!/bin/sh\necho hi\n", 0o755)

    assert target.read_text() == "#!/bin/sh\necho hi\n"        # content is correct
    assert "chmod is unsupported" in capsys.readouterr().err    # and it said so


def test_chmod_failure_warns_only_once(tmp_path, monkeypatch, capsys):
    """One note per run, not one per file -- an apply writes ~20 files."""
    def _boom(*_a, **_k):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(ur.os, "chmod", _boom)
    monkeypatch.setattr(ur, "_chmod_unsupported_warned", False)
    for i in range(3):
        ur._atomic_write(str(tmp_path / ("f%d" % i)), "x", 0o755)

    assert capsys.readouterr().err.count("chmod is unsupported") == 1


def test_write_failure_leaves_no_tmp_debris(tmp_path, monkeypatch):
    """A raise mid-write must clean up its temp file rather than leaving it beside the
    real one, where it reads as mysterious debris on the next inspection."""
    def _boom(*_a, **_k):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(ur.os, "replace", _boom)
    target = tmp_path / "guard.sh"

    with pytest.raises(OSError):
        ur._atomic_write(str(target), "data", 0o644)

    assert list(tmp_path.glob("*.tmp.update")) == []
    assert not target.exists()


# ---------------------------------------------------------------- the version chain (D164)

class TestPluginVersion:
    """`plugin_version`'s four rungs. D164 deleted `version` from `plugin.json` so the
    PLATFORM keys delivery on the commit SHA; this function has to resolve the same value
    the platform did, because that value becomes `config.workflow_version`."""

    def test_rung1_a_pin_still_wins(self, tmp_path):
        """Re-adding the field stays supported, just discouraged — otherwise a future
        release that wants a pin would find the code has decided against it."""
        p = _plugin(tmp_path / "0.9.9", version="0.9.9")
        assert ur.plugin_version(str(p)) == "0.9.9"

    def test_rung2_basename_is_the_resolved_cache_key(self, tmp_path):
        """For a real install the basename IS the key the platform resolved — measured on
        2.1.220 as a 12-char short SHA for a version-less directory-source plugin."""
        p = _plugin(tmp_path / "5f8148115e14", version=None)
        assert ur.plugin_version(str(p)) == "5f8148115e14"

    def test_rung2_accepts_a_semver_or_unknown_cache_key(self, tmp_path):
        # Resolution rules (1)/(2) name the dir with a semver; rule (4) names it `unknown`.
        assert ur.plugin_version(str(_plugin(tmp_path / "0.1.0", version=None))) == "0.1.0"
        assert ur.plugin_version(str(_plugin(tmp_path / "unknown", version=None))) == "unknown"

    def test_rung3_the_plugin_dir_edge_falls_back_to_git_head(self, tmp_path):
        """The `07` edge: under `--plugin-dir ./product` the basename is `product`, not a
        SHA. Rung 2 must DECLINE a human-chosen directory name and the repo's own HEAD is
        the honest answer — otherwise `/update` would stamp the literal string `product`."""
        repo = tmp_path / "repo"
        (repo).mkdir()
        _plugin(repo / "product", version=None)
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e")
        import subprocess
        for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "x"]):
            subprocess.run(["git", "-C", str(repo)] + args, check=True, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short=12", "HEAD"],
                              stdout=subprocess.PIPE, check=True).stdout.decode().strip()

        got = ur.plugin_version(str(repo / "product"))
        assert got == head, "the --plugin-dir edge must resolve HEAD, not 'product'"
        assert got != "product"

    def test_rung4_no_pin_no_key_no_git_is_unknown(self, tmp_path):
        p = _plugin(tmp_path / "some-checkout-dir", version=None)
        assert ur.plugin_version(str(p)) == "unknown"

    def test_unknown_is_never_a_noop(self, tmp_path):
        """Two installs that both FAILED to resolve a version are not the same install.
        Calling that a no-op would be the D151 lie in a new costume."""
        plugin = _plugin(tmp_path / "some-checkout", version=None)
        project = _project(tmp_path / "proj")
        _install(plugin, project)
        cfg = json.loads((project / ".workflow" / "config.json").read_text())
        assert cfg["workflow_version"] == "unknown"

        plan = ur.compute_plan(str(plugin), str(project))
        assert plan["old_version"] == plan["new_version"] == "unknown"
        assert plan["noop"] is False
        assert "no-op" not in ur.render_plan(plan)

    def test_a_resolved_key_that_did_not_move_is_still_a_noop(self, tmp_path):
        """The other direction: under a SHA the equality test gets strictly MORE correct,
        so it must still fire when the content genuinely did not move."""
        plugin = _plugin(tmp_path / "5f8148115e14", version=None)
        project = _project(tmp_path / "proj")
        _install(plugin, project)
        assert ur.compute_plan(str(plugin), str(project))["noop"] is True


def test_the_shipped_package_pins_no_version_anywhere():
    """Call 1's invariant, as a test rather than as a release ritual.

    Delivery keys on the commit SHA only while BOTH of these stay absent: resolution rule
    (1) re-pins from `plugin.json`, and rule (2) re-pins from the MARKETPLACE entry — so
    "omit it in the plugin, keep a semver in the marketplace" decouples nothing. This is
    not the release gate D164 deleted (that one guarded a bump nobody had to make); it
    guards the new shape against a well-meaning re-pin.
    """
    here = Path(__file__).resolve().parent                      # product/scripts
    meta = json.loads((here.parent / ".claude-plugin" / "plugin.json").read_text())
    assert "version" not in meta, (
        "plugin.json pins a version again — that restores resolution rule (1) and delivery "
        "stops keying on the commit SHA (D164)")

    mkt = here.parent.parent / ".claude-plugin" / "marketplace.json"
    if mkt.exists():                                            # absent in a shipped tarball
        for entry in json.loads(mkt.read_text()).get("plugins", []):
            assert "version" not in entry, (
                "the marketplace entry pins %s — resolution rule (2) re-pins from there "
                "(D164)" % entry.get("name"))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


# --- gitignore detection: /update names what would be committed, never writes it ----------
#
# `/update` refreshes package files, but `.gitignore` is TARGET-owned — so a package that
# introduces a new runtime path silently gets it committed on every already-started project.
# The old instruction was prose telling the model to read the schema docs and work it out, and
# it named the wrong documents once `control.json` landed in a third one. These pin the
# mechanical replacement: the shipped gitignore clause in `commands/start.md` IS the list, and
# `check_enum_coherence.py` already proves it matches the design record's tree.

PLUGIN = os.path.join(os.path.dirname(os.path.abspath(ur.__file__)), "..")


def _gi_project(tmp_path, ignore_body=None):
    root = tmp_path / "proj"
    root.mkdir(exist_ok=True)
    if ignore_body is not None:
        (root / ".gitignore").write_text(ignore_body, encoding="utf-8")
    return str(root)


def test_the_clause_is_parsed_from_the_shipped_file():
    paths = ur.runtime_paths(PLUGIN)
    assert "state.json" in paths
    assert "control.json" in paths      # the path that exposed the stale prose pointer


def test_prose_pointers_are_not_mistaken_for_paths():
    """The clause cites `shared/schemas.md § scratch` mid-sentence; a naive backtick scrape
    would report a documentation reference as a path a human should ignore."""
    assert not [p for p in ur.runtime_paths(PLUGIN) if "§" in p or p.startswith("shared/")]


def test_a_missing_path_is_reported(tmp_path):
    root = _gi_project(tmp_path, "node_modules/\n.workflow/state.json\n")
    assert "control.json" in ur.missing_ignores(PLUGIN, root)


def test_a_covered_path_is_not_reported(tmp_path):
    root = _gi_project(tmp_path, "\n".join(ur.runtime_paths(PLUGIN)) + "\n")
    assert ur.missing_ignores(PLUGIN, root) == []


def test_a_path_covered_with_a_directory_prefix_counts_as_covered(tmp_path):
    """An ignore file may say `.workflow/control.json` where the package says `control.json`.
    A matcher strict enough to be precise would report half a correct file as missing, which
    is how a useful signal becomes one people skip."""
    root = _gi_project(tmp_path, ".workflow/control.json\n")
    assert "control.json" not in ur.missing_ignores(PLUGIN, root)


def test_comments_do_not_count_as_coverage(tmp_path):
    root = _gi_project(tmp_path, "# control.json goes here one day\n")
    assert "control.json" in ur.missing_ignores(PLUGIN, root)


def test_no_gitignore_at_all_reports_every_path(tmp_path):
    root = _gi_project(tmp_path, None)
    assert ur.missing_ignores(PLUGIN, root) == ur.runtime_paths(PLUGIN)


def test_an_unreadable_clause_reports_NOTHING_rather_than_a_wrong_list(tmp_path):
    """The whole value is that the names are true. A `/update` that cannot read the clause must
    stay silent rather than send a human to edit a file against a guess."""
    empty = tmp_path / "noplugin"
    (empty / "commands").mkdir(parents=True)
    (empty / "commands" / "start.md").write_text("nothing resembling the clause\n",
                                                 encoding="utf-8")
    assert ur.runtime_paths(str(empty)) == []
    assert ur.missing_ignores(str(empty), _gi_project(tmp_path, "")) == []


def test_the_action_is_flag_only_and_never_confirms(tmp_path):
    """`.gitignore` is target-owned: `/update` names the line and the human says yes. A
    [CONFIRM] would imply this command is about to write the file."""
    root = _gi_project(tmp_path, "")
    plan = ur.compute_plan(PLUGIN, root)
    gi = [a for a in plan["actions"] if a["kind"] == "GITIGNORE"]
    assert gi
    assert not any(a["confirm"] for a in gi)
    assert "never write it" in ur.render_plan(plan)
