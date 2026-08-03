"""Tests for hooks/session_start.py — the auto-rehydrate hook and the pre-commit assert.

Runs the hook as Claude Code does (`python3 session_start.py` with the SessionStart JSON on
stdin) and asserts it emits the `hookSpecificOutput.additionalContext` contract carrying
`.workflow/handoff.md`, stays silent when there is nothing to rehydrate, and never errors out.

The second half — re-asserting `.git/hooks/pre-commit` — drives real files, because its two
interesting failures are file-shaped: clobbering somebody else's hook, and warning about the
same foreign hook on every single session start.
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent            # product/scripts
HOOK = HERE.parent / "hooks" / "session_start.py"


def _run(cwd, source="clear", config_dir=None):
    """Drive the hook exactly as Claude Code does.

    `CLAUDE_CONFIG_DIR` is ALWAYS set, and by default to a path that does not exist. The
    staleness detector reads the CLI's real install registry, so without this every test in
    this file would be coupled to whether the maintainer's own install happens to be stale
    — a test that passes or fails on the state of the developer's machine. Tests that mean
    to exercise the detector build a fake config tree and pass it here.
    """
    payload = {"hook_event_name": "SessionStart", "source": source, "cwd": str(cwd)}
    env = dict(os.environ)
    env["CLAUDE_CONFIG_DIR"] = str(config_dir or (Path(cwd) / "no-such-claude-config"))
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    return subprocess.run(
        ["python3", str(HOOK)],
        input=json.dumps(payload), cwd=cwd, capture_output=True, text=True, env=env,
    )


def _handoff(tmp_path, text):
    (tmp_path / ".workflow").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".workflow" / "handoff.md").write_text(text)


def test_injects_handoff_as_additional_context(tmp_path):
    _handoff(tmp_path, "# Handoff\ncurrent_item: ITEM-7\nloop_position: execute\n")
    r = _run(tmp_path)
    assert r.returncode == 0
    out = json.loads(r.stdout)
    ac = out["hookSpecificOutput"]["additionalContext"]
    assert out["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "ITEM-7" in ac
    assert "handoff.md" in ac                      # the framing directive names the anchor


def test_silent_when_no_handoff(tmp_path):
    (tmp_path / ".workflow").mkdir()
    r = _run(tmp_path)
    assert r.returncode == 0
    assert r.stdout.strip() == ""                  # nothing to rehydrate -> no injection


def test_silent_when_handoff_blank(tmp_path):
    _handoff(tmp_path, "   \n\n")
    r = _run(tmp_path)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_large_handoff_is_truncated(tmp_path):
    _handoff(tmp_path, "x" * 20000)
    r = _run(tmp_path)
    out = json.loads(r.stdout)
    ac = out["hookSpecificOutput"]["additionalContext"]
    assert "truncated" in ac
    assert len(ac) < 12000                         # well under the harness ~10k additionalContext cap + framing


def test_garbage_stdin_exits_zero(tmp_path):
    r = subprocess.run(["python3", str(HOOK)], input="not json", cwd=tmp_path,
                       capture_output=True, text=True)
    assert r.returncode == 0


def test_rehydrate_is_clear_only(tmp_path):
    """A fresh `startup` must not inject the whole handoff — the assert runs on every
    source, but rehydrating everywhere would be a different (and noisy) feature."""
    _handoff(tmp_path, "# Handoff\ncurrent_item: ITEM-7\n")
    assert _run(tmp_path, source="startup").stdout.strip() == ""
    assert "ITEM-7" in _run(tmp_path, source="clear").stdout


# --- re-asserting the git pre-commit backstop --------------------------------
HOOK_BODY = "#!/usr/bin/env bash\necho package-backstop\n"


def _project(tmp_path, installed=None, git=True):
    """A bootstrapped project: the package's hook source, and optionally a .git/."""
    src = tmp_path / ".claude" / "hooks"
    src.mkdir(parents=True)
    (src / "pre-commit.sh").write_text(HOOK_BODY)
    if git:
        (tmp_path / ".git" / "hooks").mkdir(parents=True)
        if installed is not None:
            (tmp_path / ".git" / "hooks" / "pre-commit").write_text(installed)
    return tmp_path / ".git" / "hooks" / "pre-commit"


def test_absent_hook_is_installed_and_reported(tmp_path):
    """`.git/hooks/` is not part of the repository, so every CLONE of a bootstrapped
    project arrives with the gate silently absent — and a clone runs neither /start nor
    /rebind. A session start is the one event that does fire."""
    dst = _project(tmp_path)
    r = _run(tmp_path, source="startup")
    assert r.returncode == 0
    assert dst.read_text() == HOOK_BODY
    ac = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "Installed the git pre-commit backstop" in ac


def test_an_identical_hook_is_silent(tmp_path):
    dst = _project(tmp_path, installed=HOOK_BODY)
    r = _run(tmp_path, source="startup")
    assert r.stdout.strip() == ""
    assert dst.read_text() == HOOK_BODY


def test_a_foreign_hook_is_never_clobbered(tmp_path):
    """Overwriting somebody else's hook to install our own is exactly the unasked-for,
    hard-to-notice side effect this project refuses to ship."""
    foreign = "#!/bin/sh\n# somebody else's hook\nexit 0\n"
    dst = _project(tmp_path, installed=foreign)
    r = _run(tmp_path, source="startup")
    assert dst.read_text() == foreign
    ac = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "FOREIGN" in ac
    assert "Nothing was overwritten" in ac


def test_the_foreign_warning_fires_once_not_every_session(tmp_path):
    _project(tmp_path, installed="#!/bin/sh\nexit 0\n")
    assert "FOREIGN" in _run(tmp_path, source="startup").stdout
    assert _run(tmp_path, source="startup").stdout.strip() == ""
    assert _run(tmp_path, source="startup").stdout.strip() == ""


def test_a_changed_foreign_hook_warns_again(tmp_path):
    """The marker is keyed by the foreign hook's hash: a DIFFERENT foreign hook is new
    information, and silence there would be the warning going stale."""
    dst = _project(tmp_path, installed="#!/bin/sh\nexit 0\n")
    _run(tmp_path, source="startup")
    dst.write_text("#!/bin/sh\n# a different foreign hook\nexit 0\n")
    assert "FOREIGN" in _run(tmp_path, source="startup").stdout


def test_installing_after_a_warning_clears_the_marker(tmp_path):
    """A project that removes the foreign hook must get the backstop installed AND be
    told — not stay silent because a stale marker says it was already warned."""
    dst = _project(tmp_path, installed="#!/bin/sh\nexit 0\n")
    _run(tmp_path, source="startup")
    dst.unlink()
    assert "Installed the git" in _run(tmp_path, source="startup").stdout
    assert dst.read_text() == HOOK_BODY
    # …and having installed it, it goes quiet again.
    assert _run(tmp_path, source="startup").stdout.strip() == ""


def test_a_non_git_directory_is_left_alone(tmp_path):
    _project(tmp_path, git=False)
    r = _run(tmp_path, source="startup")
    assert r.stdout.strip() == ""
    assert not (tmp_path / ".git").exists()


def test_a_project_without_the_package_half_is_left_alone(tmp_path):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    r = _run(tmp_path, source="startup")
    assert r.stdout.strip() == ""
    assert not (tmp_path / ".git" / "hooks" / "pre-commit").exists()


def test_the_assert_runs_on_clear_too_and_composes_with_the_rehydrate(tmp_path):
    dst = _project(tmp_path)
    _handoff(tmp_path, "# Handoff\ncurrent_item: ITEM-7\n")
    ac = json.loads(_run(tmp_path, source="clear").stdout)[
        "hookSpecificOutput"]["additionalContext"]
    assert "Installed the git pre-commit backstop" in ac
    assert "ITEM-7" in ac
    assert dst.read_text() == HOOK_BODY


def test_assert_hook_cli_is_the_same_code_path_for_rebind(tmp_path):
    """`/rebind` re-asserts the backstop by calling THIS, not by re-describing the
    three-way in prose — a rule with two owners is a rule that drifts."""
    dst = _project(tmp_path)
    r = subprocess.run(["python3", str(HOOK), "--assert-hook"], cwd=tmp_path,
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert "Installed the git pre-commit backstop" in r.stdout
    assert dst.read_text() == HOOK_BODY
    r2 = subprocess.run(["python3", str(HOOK), "--assert-hook"], cwd=tmp_path,
                        capture_output=True, text=True)
    assert r2.stdout.strip() == ""


def test_an_uninstallable_hook_reports_rather_than_wedging_the_session(tmp_path):
    import os
    import stat
    hooks = _project(tmp_path).parent
    os.chmod(hooks, stat.S_IRUSR | stat.S_IXUSR)  # readable, not writable
    try:
        r = _run(tmp_path, source="startup")
        assert r.returncode == 0
        if r.stdout.strip():  # a filesystem that actually enforces the mode
            assert "could not be installed" in r.stdout
    finally:
        os.chmod(hooks, stat.S_IRWXU)


# --- the two-hop staleness detector (D164) -----------------------------------
# Three layers, so TWO copies: source -> INSTALL (the CLI's cache, which is what runs) ->
# PROJECT scaffold. Hop A catches a stale install, hop B a stale project, and neither
# implies the other. These drive real files because every interesting failure is
# file-shaped: warning on every session, or staying silent when the install is stale.

def _git_repo(path, commits=2):
    """A real repo, returning the SHA of each commit in order."""
    path.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e")

    def g(*a):
        return subprocess.run(["git", "-C", str(path)] + list(a), env=env, check=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL).stdout.decode().strip()
    g("init", "-q")
    shas = []
    for i in range(commits):
        (path / ("f%d" % i)).write_text(str(i))
        g("add", "-A")
        g("commit", "-qm", "c%d" % i)
        shas.append(g("rev-parse", "HEAD"))
    return shas


def _advance(path):
    """One more commit on an existing repo, returning the new HEAD."""
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e")
    (path / ("f%d" % len(list(path.glob("f*"))))).write_text("more")
    for a in (["add", "-A"], ["commit", "-qm", "more"]):
        subprocess.run(["git", "-C", str(path)] + a, env=env, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], check=True,
                          stdout=subprocess.PIPE).stdout.decode().strip()


def _cli_config(root, installed_sha, version, location, mkt="dev-marketplace"):
    """A fake CLAUDE_CONFIG_DIR holding the two registry files the detector reads.

    Shapes copied from a real 2.1.220 install, not invented: `installed_plugins.json` maps
    `"<plugin>@<marketplace>"` to a LIST of per-scope entries, and `gitCommitSha` is the
    FULL 40-char source commit as of install time while `version` is the resolved cache key.
    """
    p = root / "plugins"
    p.mkdir(parents=True, exist_ok=True)
    (p / "installed_plugins.json").write_text(json.dumps({
        "version": 2,
        "plugins": {"dev-autonomous-workflow@%s" % mkt: [{
            "scope": "user",
            "installPath": "/cache/dev-autonomous-workflow/%s" % version,
            "version": version,
            "installedAt": "2026-08-03T11:26:51.816Z",
            "lastUpdated": "2026-08-03T11:26:51.816Z",
            "gitCommitSha": installed_sha,
        }]},
    }))
    (p / "known_marketplaces.json").write_text(json.dumps({
        mkt: {"source": {"source": "directory", "path": str(location)},
              "installLocation": str(location)},
    }))
    return root


def _target(tmp_path, stamped=None):
    """A bootstrapped project whose pre-commit assert is already satisfied, so anything on
    stdout came from the detector."""
    _project(tmp_path, installed=HOOK_BODY)
    if stamped is not None:
        (tmp_path / ".workflow").mkdir(exist_ok=True)
        (tmp_path / ".workflow" / "config.json").write_text(
            json.dumps({"project_root": ".", "workflow_version": stamped}))
    return tmp_path


MARKER = ".git/hooks/.disciplined-builder-stale"


def test_hop_a_fires_when_the_install_is_behind_a_directory_source(tmp_path):
    """The maintainer's anchor: a `directory` marketplace, so the source tree's own HEAD.
    This is D151 — the install had drifted 12 commits while `claude plugin update` said
    "already at the latest version"."""
    src = tmp_path / "src"
    first, head = _git_repo(src, commits=2)
    cfg = _cli_config(tmp_path / "cc", installed_sha=first, version=first[:12], location=src)
    proj = _target(tmp_path / "proj", stamped=first[:12])

    r = _run(proj, source="startup", config_dir=cfg)
    assert r.returncode == 0
    ac = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "INSTALLED workflow package is NOT the source" in ac
    assert first[:12] in ac and head[:12] in ac
    assert "1 commit ahead" in ac                      # not "1 commits"
    assert "claude plugin update" in ac
    assert json.loads((proj / MARKER).read_text())["reinstall"] == \
        first[:12] + ".." + head[:12]


def test_hop_a_reads_a_github_clones_gcs_sha(tmp_path):
    """The released user's anchor. The CLI's marketplace clone is not itself a git repo —
    it records its commit in `.gcs-sha`, so there is nothing else to ask."""
    clone = tmp_path / "clone"
    clone.mkdir()
    anchor = "b" * 40
    (clone / ".gcs-sha").write_text("a" * 40)          # placeholder, overwritten below
    (clone / ".gcs-sha").write_text(anchor)            # no trailing newline, as measured
    cfg = _cli_config(tmp_path / "cc", installed_sha="a" * 40, version="aaaaaaaaaaaa",
                      location=clone)
    proj = _target(tmp_path / "proj")

    ac = json.loads(_run(proj, source="startup", config_dir=cfg).stdout)[
        "hookSpecificOutput"]["additionalContext"]
    assert "INSTALLED workflow package is NOT the source" in ac
    assert "commit ahead" not in ac                    # no repo to count against, so no claim


def test_hop_a_is_silent_when_the_install_matches_the_source(tmp_path):
    src = tmp_path / "src"
    (head,) = _git_repo(src, commits=1)
    cfg = _cli_config(tmp_path / "cc", installed_sha=head, version=head[:12], location=src)
    proj = _target(tmp_path / "proj", stamped=head[:12])
    assert _run(proj, source="startup", config_dir=cfg).stdout.strip() == ""


def test_hop_b_fires_when_the_project_is_behind_the_install(tmp_path):
    """The axis that can LIE: `/update` is bounded by the install, so a project can be
    behind an install that is itself current, and only this hop says so."""
    src = tmp_path / "src"
    (head,) = _git_repo(src, commits=1)
    cfg = _cli_config(tmp_path / "cc", installed_sha=head, version="deadbeefcafe",
                      location=src)
    proj = _target(tmp_path / "proj", stamped="0ldc0mm1t123")

    ac = json.loads(_run(proj, source="startup", config_dir=cfg).stdout)[
        "hookSpecificOutput"]["additionalContext"]
    assert "INSTALLED workflow package is NOT the source" not in ac   # hop A is quiet
    assert "0ldc0mm1t123" in ac and "deadbeefcafe" in ac
    assert "Run `/update`" in ac
    assert json.loads((proj / MARKER).read_text())["update"] == "0ldc0mm1t123..deadbeefcafe"


def test_hop_b_is_silent_without_a_stamp(tmp_path):
    """An ABSENT `workflow_version` is the unknown-old install `/update` already reconciles
    in full. Warning about it every session of every un-bootstrapped project is pure noise."""
    src = tmp_path / "src"
    (head,) = _git_repo(src, commits=1)
    cfg = _cli_config(tmp_path / "cc", installed_sha=head, version="deadbeefcafe",
                      location=src)
    proj = _target(tmp_path / "proj")                  # no config.json at all
    assert _run(proj, source="startup", config_dir=cfg).stdout.strip() == ""


def test_both_hops_can_fire_together(tmp_path):
    src = tmp_path / "src"
    first, head = _git_repo(src, commits=2)
    cfg = _cli_config(tmp_path / "cc", installed_sha=first, version=first[:12], location=src)
    proj = _target(tmp_path / "proj", stamped="0ldc0mm1t123")

    ac = json.loads(_run(proj, source="startup", config_dir=cfg).stdout)[
        "hookSpecificOutput"]["additionalContext"]
    assert "INSTALLED workflow package is NOT the source" in ac
    assert "Run `/update`" in ac
    # Reinstall-first is the order the text has to imply: `/update` driven by a stale
    # install propagates the stale files into the project and reports success.
    assert ac.index("INSTALLED workflow package") < ac.index("Run `/update`")
    assert set(json.loads((proj / MARKER).read_text())) == {"reinstall", "update"}


def test_the_warning_fires_once_not_every_session(tmp_path):
    """A warning on every session start is noise, and noise is how the D151 drift survived
    twelve commits in the first place."""
    src = tmp_path / "src"
    first, _head = _git_repo(src, commits=2)
    cfg = _cli_config(tmp_path / "cc", installed_sha=first, version=first[:12], location=src)
    proj = _target(tmp_path / "proj")

    assert "NOT the source" in _run(proj, source="startup", config_dir=cfg).stdout
    assert _run(proj, source="startup", config_dir=cfg).stdout.strip() == ""
    assert _run(proj, source="startup", config_dir=cfg).stdout.strip() == ""


def test_a_moved_sha_warns_again(tmp_path):
    """Keyed on the SHA PAIR, so new drift is new information — silence there would be the
    warning going stale, which is the failure the warn-once state exists to avoid becoming."""
    src = tmp_path / "src"
    first, _second = _git_repo(src, commits=2)
    cfg = _cli_config(tmp_path / "cc", installed_sha=first, version=first[:12], location=src)
    proj = _target(tmp_path / "proj")
    assert "NOT the source" in _run(proj, source="startup", config_dir=cfg).stdout
    assert _run(proj, source="startup", config_dir=cfg).stdout.strip() == ""

    _advance(src)                                      # the source moves again
    assert "NOT the source" in _run(proj, source="startup", config_dir=cfg).stdout


def test_fixing_the_drift_makes_it_silent_by_itself(tmp_path):
    """No state has to be cleared for the warning to stop: the condition simply stops
    holding once the install is current."""
    src = tmp_path / "src"
    first, head = _git_repo(src, commits=2)
    stale = _cli_config(tmp_path / "cc", installed_sha=first, version=first[:12], location=src)
    proj = _target(tmp_path / "proj")
    assert "NOT the source" in _run(proj, source="startup", config_dir=stale).stdout

    fixed = _cli_config(tmp_path / "cc2", installed_sha=head, version=head[:12], location=src)
    assert _run(proj, source="startup", config_dir=fixed).stdout.strip() == ""


def test_silent_without_an_install_record(tmp_path):
    """A `--plugin-dir` dev run or a vendored copy has no registry entry, and inventing a
    warning for it would be a guess."""
    (tmp_path / "cc" / "plugins").mkdir(parents=True)
    proj = _target(tmp_path / "proj", stamped="0ldc0mm1t123")
    assert _run(proj, source="startup", config_dir=tmp_path / "cc").stdout.strip() == ""


def test_a_garbage_registry_never_wedges_the_session(tmp_path):
    """Fails open, always. A hook that could break session start would be a worse failure
    than anything it protects against."""
    p = tmp_path / "cc" / "plugins"
    p.mkdir(parents=True)
    (p / "installed_plugins.json").write_text("{not json at all")
    (p / "known_marketplaces.json").write_text("[]")
    proj = _target(tmp_path / "proj", stamped="0ldc0mm1t123")
    r = _run(proj, source="startup", config_dir=tmp_path / "cc")
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_a_worktree_is_silent_because_it_cannot_remember(tmp_path):
    """A worktree's `.git` is a FILE, so there is nowhere to keep the warn-once state — and
    a detector with no memory is a detector that becomes noise. Same rule as the assert."""
    src = tmp_path / "src"
    first, _head = _git_repo(src, commits=2)
    cfg = _cli_config(tmp_path / "cc", installed_sha=first, version=first[:12], location=src)
    proj = tmp_path / "proj"
    (proj / ".claude" / "hooks").mkdir(parents=True)
    (proj / ".claude" / "hooks" / "pre-commit.sh").write_text(HOOK_BODY)
    (proj / ".git").write_text("gitdir: /elsewhere/.git/worktrees/x\n")
    assert _run(proj, source="startup", config_dir=cfg).stdout.strip() == ""


def test_the_warning_also_reaches_the_transcript(tmp_path):
    """`additionalContext` can be summarized away; stderr lands in the transcript. Same
    belt-and-braces the foreign-hook warning already uses."""
    src = tmp_path / "src"
    first, _head = _git_repo(src, commits=2)
    cfg = _cli_config(tmp_path / "cc", installed_sha=first, version=first[:12], location=src)
    proj = _target(tmp_path / "proj")
    assert "NOT the source" in _run(proj, source="startup", config_dir=cfg).stderr


def test_staleness_composes_with_the_rehydrate_within_the_context_cap(tmp_path):
    """A full-size handoff plus a warning must not together overrun the harness cap — the
    handoff is the part that yields, because it is the one with a `read it in full` escape."""
    src = tmp_path / "src"
    first, _head = _git_repo(src, commits=2)
    cfg = _cli_config(tmp_path / "cc", installed_sha=first, version=first[:12], location=src)
    proj = _target(tmp_path / "proj", stamped="0ldc0mm1t123")
    _handoff(proj, "# Handoff\ncurrent_item: ITEM-7\n" + "x" * 20000)

    ac = json.loads(_run(proj, source="clear", config_dir=cfg).stdout)[
        "hookSpecificOutput"]["additionalContext"]
    assert "NOT the source" in ac and "Run `/update`" in ac and "ITEM-7" in ac
    assert len(ac) <= 12000, "the warnings must not push the injection past the cap"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
