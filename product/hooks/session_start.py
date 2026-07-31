#!/usr/bin/env python3
"""SessionStart — two jobs, one hook, neither of which may ever wedge a session start.

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

Emits the SessionStart JSON contract (`hookSpecificOutput.additionalContext`) and always
exits 0 — SessionStart cannot block a session anyway, and a hook that could would be a
worse failure than anything it protects against.
"""
import hashlib
import json
import os
import shutil
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


def rehydrate(cwd):
    handoff = read_handoff(cwd)
    if not handoff or not handoff.strip():
        return None  # nothing to rehydrate — stay silent
    if len(handoff) > MAX_CHARS:
        handoff = handoff[:MAX_CHARS] + (
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

    # The rehydrate is CLEAR-ONLY. The assert above runs on every source, because a
    # fresh clone's first event is `startup`; injecting the whole handoff on every
    # startup would be a different feature, and a noisy one.
    if payload.get("source") == "clear":
        ctx = rehydrate(cwd)
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
