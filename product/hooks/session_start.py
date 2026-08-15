#!/usr/bin/env python3
"""SessionStart — three jobs, one hook, none of which may ever wedge a session start.

  1. REHYDRATE (source=clear only). `/clear` wipes the conversation but preserves the
     filesystem, so the durable resume anchor `.workflow/handoff.md` is still on disk;
     this injects it as `additionalContext` so the cleared session auto-resumes instead
     of the human re-explaining where the build was. The automatic half of `/dispatch`.

  2. RE-ASSERT the git pre-commit backstop (EVERY source). `/start` installs
     `.claude/hooks/pre-commit.sh` as `.git/hooks/pre-commit`, but `.git/hooks/` is not
     part of the repository — so every CLONE of a bootstrapped project arrives with the
     gate silently absent, and a clone runs neither `/start` (already bootstrapped) nor
     `/rebind` (already bound). The one event that DOES fire on a clone is a session
     start, which is why the assert lives here.

     The scrutiny this needs is lower than it first reads, in both directions.
     Re-asserting cannot DISARM anything: the gate is already absent in the case this
     fires on, so the only reachable transition is absent -> installed. And the severity
     is bounded: in-loop commits go through the `commit` skill's `checks.sh --fix` +
     `--check`, so the git hook backstops OUT-OF-LOOP commits only. Missing it narrows
     coverage; it does not disarm the loop.

     Three-way, and the third arm is the important one:
       absent          -> install it, and say so in one line
       byte-identical  -> silent (the overwhelmingly common case; two stats and a read)
       DIFFERENT       -> NEVER clobber, warn once. A foreign pre-commit hook belongs to
                          whoever put it there. Overwriting somebody's hook to install
                          our own is exactly the kind of unasked-for, hard-to-notice
                          side effect this project refuses to ship.

     The warning rides `additionalContext`, and that was ASSUMED to leave a headless
     `claude -p` clone quietly uncovered. Driven on the live harness, it does not: a
     `-p` session is handed the warning and can quote it back verbatim in its rendered
     form. The assumed residual was never real, and a residual nobody rechecks is the
     more expensive kind of wrong — it invites a second mechanism to close a hole that
     is already shut.

  3. DETECT STALENESS (EVERY source). Two hops, warn-once per distinct SHA. See
     `detect_staleness` for the mechanism; the reason it is a DETECTOR and not a preventer
     is that the automatic delivery path is CLI-side and broken (issue #17361, live on
     2.1.220), so no author-side choice makes delivery automatic. What an author *can*
     control is that the install can SAY it is stale.

Emits the SessionStart JSON contract (`hookSpecificOutput.additionalContext`) and always
exits 0 — SessionStart cannot block a session anyway, and a hook that could would be a
worse failure than anything it protects against.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

# additionalContext is capped by the harness (~10k chars); handoff.md is a bounded
# resume anchor by design, but truncate defensively so a bloated one still injects.
MAX_CHARS = 9000

SOURCE = os.path.join(".claude", "hooks", "pre-commit.sh")
INSTALLED = os.path.join(".git", "hooks", "pre-commit")
# Where "warn ONCE" is remembered. It has to be machine-local (a clone must warn on its
# own), it must not be committed, and it should sit beside the thing it describes —
# `.git/` is all three by construction, with no gitignore entry and no runtime-tree
# dependency. Keyed by the foreign hook's hash, so a DIFFERENT foreign hook warns again.
MARKER = os.path.join(".git", "hooks", ".disciplined-builder-assert")
# The staleness detector's warn-once state, a sibling of the marker above and machine-local
# for the same three reasons, which apply to it even harder: the installed SHA is a fact
# about THIS machine, so committing it would let one machine's install silence the warning
# on every other. `.git/hooks/` needs no `.gitignore` entry (git cannot track it), survives
# a `/rebind` (it is not in the relocatable runtime tree), and is bounded at one small file
# rewritten in place — so nothing has to prune it. `shared/schemas.md` owns both.
STALE_MARKER = os.path.join(".git", "hooks", ".disciplined-builder-stale")

PLUGIN_NAME = "reeve"
_SHA_RE = re.compile(r"[0-9a-f]{7,40}\Z")


def read_handoff(cwd):
    # handoff.md is COMMITTED (never relocated), so it is read under .workflow/ directly.
    path = os.path.join(cwd or ".", ".workflow", "handoff.md")
    try:
        with open(path) as fh:
            return fh.read()
    except Exception:
        return None


def _read(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def assert_pre_commit(cwd):
    """The three-way. Returns a line to surface, or None when there is nothing to say.

    Every failure path returns None rather than raising: this runs on every session
    start, and a project that cannot be repaired is not a project that should be unable
    to start a session.
    """
    root = cwd or "."
    src = os.path.join(root, SOURCE)
    dst = os.path.join(root, INSTALLED)
    want = _read(src)
    if want is None:
        return None  # not a bootstrapped project, or the package half is not installed
    if not os.path.isdir(os.path.join(root, ".git")):
        return None  # not a git repo (a worktree's .git is a file) — nothing to hook
    got = _read(dst)

    if got == want:
        return None  # the common case, and it says nothing

    if got is None:
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
        except OSError as exc:
            return ("The git pre-commit backstop is NOT installed and could not be "
                    "installed automatically (%s). Out-of-loop commits are not gated. "
                    "Copy %s to %s by hand." % (exc, SOURCE, INSTALLED))
        try:
            os.chmod(dst, 0o755)
        except OSError:
            # A filesystem that will not honour a mode (Windows-interop, some network
            # mounts) already reports every file executable, so git runs the hook
            # regardless. Refusing to proceed over an unenforceable permission bit is
            # strictly worse than proceeding.
            pass
        _forget(root)
        return ("Installed the git pre-commit backstop at %s (it was absent — "
                "`.git/hooks/` is not part of the repository, so a clone never gets "
                "it). Out-of-loop commits are gated again." % INSTALLED)

    # Present and DIFFERENT. Do not touch it.
    digest = hashlib.sha256(got).hexdigest()
    if _already_warned(root, digest):
        return None
    _remember(root, digest)
    return ("A FOREIGN `%s` is installed — it is not this package's backstop, and it "
            "has been left exactly as it is. Nothing was overwritten. The consequence: "
            "commits made OUTSIDE the loop are not running `checks.sh --check`. In-loop "
            "commits are unaffected (the `commit` skill runs the gate itself). To wire "
            "the backstop, merge `%s` into that hook by hand." % (INSTALLED, SOURCE))


def _already_warned(root, digest):
    return (_read(os.path.join(root, MARKER)) or b"").decode(
        "utf-8", "replace").strip() == digest


def _remember(root, digest):
    try:
        with open(os.path.join(root, MARKER), "w") as fh:
            fh.write(digest + "\n")
    except OSError:
        pass  # then it warns again next session, which is the safe direction


def _forget(root):
    try:
        os.unlink(os.path.join(root, MARKER))
    except OSError:
        pass


# ------------------------------------------------------------------ staleness detector

def _read_json(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return None


def _config_dir():
    # CLAUDE_CONFIG_DIR relocates the ENTIRE CLI config tree. Honour it, or on a machine
    # that sets it the detector reads a registry that is not the one in use and stays
    # silent forever — the failure mode that is invisible rather than noisy.
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(
        os.path.expanduser("~"), ".claude")


def _git(args):
    """`git <args>` -> stripped stdout, or None on any failure. Never raises.

    Timeout is not paranoia: the maintainer's own source tree sits on a Windows-interop
    mount, and session start is not allowed to be hostage to a filesystem.
    """
    try:
        out = subprocess.run(["git"] + args, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.decode("utf-8", "replace").strip()


def _installed_record():
    """Our entry in the CLI's install registry, plus the marketplace name it came from.

    `installed_plugins.json` maps `"<plugin>@<marketplace>"` to a LIST of entries, one per
    scope. Where there is more than one we take the most recently updated: it is the one a
    fresh session is likeliest to be running, and choosing wrong can only mis-time a
    warning that already fails open.
    """
    reg = _read_json(os.path.join(_config_dir(), "plugins", "installed_plugins.json"))
    best, best_mkt = None, None
    for key, entries in ((reg or {}).get("plugins") or {}).items():
        name, _, mkt = str(key).partition("@")
        if name != PLUGIN_NAME or not isinstance(entries, list):
            continue
        for e in entries:
            if not isinstance(e, dict):
                continue
            if best is None or str(e.get("lastUpdated") or "") > str(best.get("lastUpdated") or ""):
                best, best_mkt = e, mkt
    return best, best_mkt


def _marketplace_anchor(mkt):
    """(sha, location) the marketplace source is at ON THIS DISK, or (None, None).

    Two source kinds, two anchors — one detector, two audiences:
      github / url / git  -> the clone the CLI keeps, which records its commit in `.gcs-sha`
                             (and is not itself a git repo, so there is nothing else to ask)
      directory           -> the source tree itself, so `git rev-parse HEAD`
    Probed in that order rather than switched on `source.source`, so a source kind the CLI
    adds later still resolves if it leaves either anchor behind.

    THREE outcomes, not two. `(None, location)` is the registered-but-GONE case: the source
    tree the package was installed from is no longer on this disk. Folding it into
    `(None, None)` would read to the caller as "no anchor to compare against" and go quiet,
    which is precisely backwards — an install whose source has vanished can never be
    updated again, and silence lets it read as current forever.
    """
    known = _read_json(os.path.join(_config_dir(), "plugins", "known_marketplaces.json"))
    loc = ((known or {}).get(mkt) or {}).get("installLocation") if mkt else None
    if not loc:
        return None, None
    if not os.path.isdir(loc):
        return None, loc
    gcs = _read(os.path.join(loc, ".gcs-sha"))
    if gcs:
        sha = gcs.decode("utf-8", "replace").strip()
        if _SHA_RE.match(sha):
            return sha, loc
    sha = _git(["-C", loc, "rev-parse", "HEAD"])
    return (sha, loc) if sha and _SHA_RE.match(sha) else (None, None)


def _same_sha(a, b):
    """SHAs from different sources are abbreviated differently — compare on the prefix."""
    a, b = (a or "").lower(), (b or "").lower()
    if not a or not b:
        return False
    n = min(len(a), len(b))
    return a[:n] == b[:n]


def _running_version(entry):
    """The resolved cache key of the package that is ACTUALLY running.

    `CLAUDE_PLUGIN_ROOT` is the direct answer and its basename IS that key — but MEASURED
    on 2.1.220, it is NOT exported to this hook: the hook is wired from the PROJECT's
    `.claude/settings.json` (the package installs itself into the project, because settings
    reference hooks by project-relative path), and a project-settings hook gets
    `CLAUDE_PROJECT_DIR` only. So the registry's `version` is the working anchor and the
    env var is the preferred one when some future session does export it.
    """
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if root:
        base = os.path.basename(os.path.abspath(root))
        if base:
            return base
    v = (entry or {}).get("version")
    return str(v) if v else None


def detect_staleness(cwd):
    """Two hops, because there are three layers and therefore TWO copies.

      source (a checkout, or the CLI's marketplace clone)
        -> INSTALL   `claude plugin install` COPIES it into the CLI's cache; that copy is
                     what `CLAUDE_PLUGIN_ROOT` points at, so that copy is what runs
        -> PROJECT   `/start` copies the manifest's install set into the project's own git,
                     because `.claude/settings.json` names those files by project-relative
                     path and the cache path is machine-specific and uncommittable

      hop A  install vs source    -> the INSTALL is stale: reinstall
      hop B  project vs install   -> the PROJECT is stale: run `/update`

    Neither hop implies the other, and hop B alone is the one that can LIE: `/update` is
    BOUNDED BY THE INSTALL — it runs the install's own `update_reconcile.py` and never
    reaches back to the source — so a stale install does not merely run old code, it
    PROPAGATES old code into every project that updates from it, and reports success.

    LOCAL-ONLY, deliberately: no network call, so no timeout policy, no offline path and no
    freshness cache at session start. The price is that a github install cannot see commits
    that are on the remote but not yet in its clone — that is CLI-side delivery (#17361 F1),
    which is not ours to fix and is the reason this detects instead of preventing.

    Warn-ONCE per distinct SHA pair. A warning that fires every session is noise, and noise
    is how the drift this exists to catch once went unnoticed for twelve commits and
    seventeen files. Returns a list of
    lines; EVERY failure path returns fewer lines rather than raising.
    """
    root = cwd or "."
    # No `.git/` directory means nowhere to remember having warned, and a detector with no
    # memory is a detector that becomes noise. A worktree (whose `.git` is a file) is
    # silent for the same reason `assert_pre_commit` is.
    if not os.path.isdir(os.path.join(root, ".git")):
        return []
    entry, mkt = _installed_record()
    if not entry:
        return []  # no install record: a `--plugin-dir` dev run, or a vendored copy

    notes = []

    # hop A — the install against the source it was installed from.
    installed = str(entry.get("gitCommitSha") or "")
    anchor, loc = _marketplace_anchor(mkt)
    if loc and anchor is None:
        # The source is registered and GONE — a checkout that was moved, renamed or deleted
        # (a throwaway one is the easy way to do this by accident: bind the package to it,
        # then delete it). The install keeps working, because it is a COPY, so nothing
        # visibly breaks; what breaks is every route to a newer one. Keyed on the dead path
        # so re-pointing it silences this by itself, like the SHA-pair hops.
        if _stale_once(root, "reinstall", "missing:" + loc):
            notes.append(
                "The source this workflow package was installed FROM no longer exists on "
                "this disk: `%s` is still registered as its marketplace, and that path is "
                "gone. The install itself keeps working — it is a COPY — but nothing can "
                "update it any more, and it will keep reading as current however far the "
                "real source moves ahead. Re-point it at a checkout that exists and "
                "reinstall: `claude plugin marketplace add <path-to-checkout> && claude "
                "plugin install %s`." % (loc, PLUGIN_NAME))
    elif installed and anchor and not _same_sha(installed, anchor):
        if _stale_once(root, "reinstall", installed[:12] + ".." + anchor[:12]):
            behind = _git(["-C", loc, "rev-list", "--count", installed + ".." + anchor])
            gap = (" — the source is %s commit%s ahead" %
                   (behind, "" if behind == "1" else "s")) if (behind or "").isdigit() \
                and behind != "0" else ""
            notes.append(
                "The INSTALLED workflow package is NOT the source it was installed from: "
                "installed at %s, the source on this disk is at %s%s. Installing COPIES the "
                "package, so everything you run — every hook, script and skill — is the OLD "
                "copy, and `/update` would propagate it into this project while reporting "
                "success. Fix it before trusting anything this session does: "
                "`claude plugin marketplace update %s && claude plugin update %s`, then "
                "restart the session."
                % (installed[:12], anchor[:12], gap, mkt or "<marketplace>", PLUGIN_NAME))

    # hop B — this project's scaffold against the install that wrote it.
    cfg = _read_json(os.path.join(root, ".workflow", "config.json")) or {}
    old = cfg.get("workflow_version")
    new = _running_version(entry)
    # An ABSENT stamp is the unknown-old install, which `/update` already handles as a full
    # reconcile — warning about it on every session of every not-yet-bootstrapped project
    # would be pure noise, so absence is silent here on purpose.
    if old and new and not _same_sha(str(old), new):
        if _stale_once(root, "update", str(old) + ".." + new):
            notes.append(
                "This project's package-owned files were written by workflow package %s, "
                "but the INSTALLED package is %s. The files under `.claude/` and "
                "`.workflow/` are from the older snapshot. Run `/update` to reconcile them "
                "— it refreshes only what the package owns and never touches your own "
                "files." % (old, new))
    return notes


def _stale_load(root):
    return _read_json(os.path.join(root, STALE_MARKER)) or {}


def _stale_once(root, hop, key):
    """True the FIRST time `hop` is seen at `key`; records it. False on a repeat.

    Keyed on the SHA pair, so the warning returns the moment either side moves, and goes
    silent by itself once the fix lands (the condition simply stops holding). A write that
    fails leaves it warning again next session, which is the safe direction.
    """
    state = _stale_load(root)
    if state.get(hop) == key:
        return False
    state[hop] = key
    try:
        with open(os.path.join(root, STALE_MARKER), "w") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
            fh.write("\n")
    except OSError:
        pass
    return True


def rehydrate(cwd, budget=MAX_CHARS):
    handoff = read_handoff(cwd)
    if not handoff or not handoff.strip():
        return None  # nothing to rehydrate — stay silent
    # `budget` is MAX_CHARS less whatever the warnings above already spent, so a staleness
    # note plus a full-size handoff cannot together overrun the harness cap. The handoff is
    # the part that yields, because it is the one that has a `read the file in full` escape.
    budget = max(1000, min(MAX_CHARS, budget))
    if len(handoff) > budget:
        handoff = handoff[:budget] + (
            "\n…(handoff truncated — read .workflow/handoff.md in full)…\n")
    return (
        "This session was cleared (/clear). The durable resume anchor "
        "`.workflow/handoff.md` follows verbatim. Resume from it plus `git log` per your "
        "orchestrator brief: DO NOT restart the bootstrap and DO NOT re-run already-committed "
        "items. If `.workflow/state.json` shows no active run, this is an ordinary session — "
        "leave the loop alone.\n\n----- .workflow/handoff.md -----\n" + handoff)


def main():
    # `--assert-hook` runs the pre-commit assert ALONE, with no stdin contract, so
    # `/rebind` can re-assert the backstop by calling this exact code path rather than
    # re-describing the three-way in prose. A rule with two owners is a rule that drifts,
    # and this file is the owner.
    if "--assert-hook" in sys.argv[1:]:
        note = assert_pre_commit(os.getcwd())
        if note:
            print(note)
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    cwd = payload.get("cwd") or "."

    parts = []
    note = assert_pre_commit(cwd)
    if note:
        parts.append("[disciplined-builder] " + note)
        # Also to stderr, so it lands in the transcript rather than only in a context
        # window that may be summarized away.
        sys.stderr.write(note + "\n")

    # Staleness runs on EVERY source, for the same reason the assert does: the event that
    # is guaranteed to happen is a session start. It is deliberately FIRST in the rendered
    # context after the assert — a session that is about to run old code should learn that
    # before it reads a handoff describing work the old code cannot do.
    for stale in detect_staleness(cwd):
        parts.append("[disciplined-builder] STALE: " + stale)
        sys.stderr.write(stale + "\n")

    # The rehydrate is CLEAR-ONLY. The assert above runs on every source, because a
    # fresh clone's first event is `startup`; injecting the whole handoff on every
    # startup would be a different feature, and a noisy one.
    if payload.get("source") == "clear":
        ctx = rehydrate(cwd, MAX_CHARS - sum(len(p) for p in parts))
        if ctx:
            parts.append(ctx)

    if not parts:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n\n".join(parts),
        }
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # A hook error must never wedge session start; degrade to a silent no-op.
        sys.exit(0)
