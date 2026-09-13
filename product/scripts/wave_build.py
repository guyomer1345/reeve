#!/usr/bin/env python3
"""wave_build.py — the wave's authoritative build slot. "Build once per wave", as a mechanism.

WHAT IT IS FOR. When a wave fans out, N workers run at once in N git worktrees, and each of them
eventually reaches the gate a commit hangs on — `.workflow/checks.sh --check`, whose stack half
(`FMT_CHECK`/`LINT`/`TYPECHECK`/`TEST`) runs REPO-WIDE. N of those at once share one build cache,
one set of ports, one set of fixtures and one machine. They collide, and a gate that collides is
a flaky gate rather than an honest one. The package has asserted "build once per wave" in prose
for a long time and enforced it nowhere; this is the enforcement.

THE LINE IT DRAWS, which is the whole design. A worker running the project's tests inside its own
worktree to find out whether its own work is right is NOT this. That act is scoped to its
worktree, may happen as often as it likes, and nothing here touches it — `execute` needs it, and a
mechanism that forbade it would have broken the loop in order to protect the build. What this
governs is the other act: the ONE authoritative gate whose verdict a commit depends on. One is a
worker checking itself; the other is the wave deciding. Only the second takes the slot.

TWO ARTIFACTS, both anchored on `git rev-parse --git-common-dir`:
  <common-dir>/reeve-wave-build.lock   an empty file, `flock`'d by checks.sh — the EXCLUSION.
  <common-dir>/reeve-wave-build.json   `{wave, passed: {<fingerprint>: {at, pid}}}` — the MEMO.
The anchor is not a taste call. The lock has to be the SAME file for every worker, and the workers
sit in different worktrees: `.workflow/`'s runtime half is gitignored, so a per-ticket worktree has
no copy of `state.json` or of any lock under it to contend on, while git guarantees that every
worktree of a repo resolves to one common dir. Being inside `.git/` also means it can never be
committed, needs no `.gitignore` line to earn that, and dies with the repo.

CRASH SAFETY — by construction, not by recovery, and deliberately the same discipline as
`orchestrator.lock` rather than a second one invented here. The only thing held across the build is
a kernel `flock`: a worker that dies holding the slot has it released by the kernel the moment it
dies, so no wave can be wedged by a corpse and there is no lease, no heartbeat and no stale-pid
sweep to get subtly wrong. The memo is only ever written AFTER a gate has finished and passed, so a
crash mid-build leaves nothing behind to believe — the next run simply builds.

WHICH DIRECTION IT FAILS: IT BUILDS. Every unknown — no git, no `flock`, an unreadable or
half-written marker, a wave nobody named, a changed file it cannot hash, a lock waited on and never
got — resolves to "run the build". A gate fails closed, and for THIS gate closed means running: the
worst a missing memo can cost is a wasted build, while the other direction would wave an unverified
commit through on the strength of a file nobody could read. The memo is a cache with an exact key,
never a permission slip — it says only *this exact tree already passed this exact gate inside this
same wave*, which is the one case where running again cannot produce a different answer.

ONLY PASSES ARE MEMOIZED, and that is not an oversight. The commonest cause of a red stack gate is a
machine that never got the toolchain `checks.env` names (the case `/rebind` exists for), and that is
repaired without changing a byte of the tree. A memoized failure would keep reporting the old
verdict after the repair — the same trap one level down. So a failing run records nothing, and a
failing tree is re-gated every time until it passes.

WHY THE WAVE ID IS PART OF THE KEY. It bounds the memo's life to the wave that produced it, using
the wave `state.json` already carries — no second notion of "which wave is this". A tree state can
recur across waves (a revert, a branch switch), and a cache that outlived its wave would be
answering a question nobody asked it. No wave id — the serial/degenerate case, `wave: null` — means
no key at all, so a wave of one behaves exactly as it did before this file existed: it builds, every
time, and pays only an uncontended `flock`.

Usage (called by `.workflow/checks.sh --check`, from inside the `flock` that runner holds):
    wave_build.py claim     exit 0 = this wave already passed this tree; skip the stack gate.
                            exit 1 = run it. Prints the fingerprint on stdout EITHER WAY, so
                            `record` names the tree state that was actually gated.
    wave_build.py record --fingerprint <fp>    record a PASS for the tree `claim` measured.
Neither subcommand ever raises into the caller's gate; both answer 0/1 and say why on stderr.
"""
import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import time

WORKFLOW = ".workflow"
LOCK_NAME = "reeve-wave-build.lock"
MARKER_NAME = "reeve-wave-build.json"

# Bounds on the memo and on the fingerprint. Each one, when tripped, means "no key" -> build.
MAX_PASSES = 32              # entries kept per wave; a fanned-out wave needs one per worker
MAX_CHANGED = 2000           # a worktree this dirty is not a state worth keying on
MAX_FILE = 8 << 20           # 8 MiB: past this, hashing the file costs more than the build saves


# ------------------------------------------------------------------ small readers

def git(*args):
    """Read-only git. Returns stdout, or None if git could not answer.

    Never raises: every caller treats None as "no key" and builds, so a repo-less tree, a git
    that is not installed, and a command that failed are all the same safe answer.
    """
    try:
        p = subprocess.run(["git", *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout if p.returncode == 0 else None


def read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def common_dir():
    """The one directory every worktree of this repo agrees on, absolute. None ⇒ no anchor."""
    out = git("rev-parse", "--git-common-dir")
    if not out or not out.strip():
        return None
    # In the main checkout this comes back relative (`.git`), resolved against the CWD — which is
    # the repo root, because that is where both the commit skill and the git hook run the runner.
    path = os.path.abspath(out.strip())
    return path if os.path.isdir(path) else None


def marker_path():
    root = common_dir()
    return os.path.join(root, MARKER_NAME) if root else None


def lock_path():
    """Exposed for the runner and for tests; checks.sh derives the same path in bash."""
    root = common_dir()
    return os.path.join(root, LOCK_NAME) if root else None


# ------------------------------------------------------------------ the wave id

def _runtime_root(workflow):
    """Mirror `verify_check.resolve_runtime_root`: an absent/empty/dangling pointer means the
    workflow dir IS the runtime root, which is the common, non-relocated case."""
    pointer = read_json(os.path.join(workflow, "runtime.json"))
    root = pointer.get("runtime_root") if isinstance(pointer, dict) else None
    if not root:
        return workflow
    root = os.path.abspath(os.path.expanduser(root))
    return root if os.path.isdir(root) else workflow


def _workflow_dirs():
    """Where `state.json` might be, nearest first.

    The CWD's `.workflow/` is the ordinary answer. The second candidate is the MAIN checkout's,
    reached through the common git dir, and it is what makes this work from a per-ticket worktree
    at all: the runtime half of `.workflow/` is gitignored, so a fresh worktree has no `state.json`
    of its own and would otherwise be unable to name the wave it is part of.
    """
    dirs = [WORKFLOW]
    root = common_dir()
    if root:
        main = os.path.join(os.path.dirname(root), WORKFLOW)
        if os.path.abspath(main) != os.path.abspath(WORKFLOW):
            dirs.append(main)
    return [d for d in dirs if os.path.isdir(d)]


def wave_id():
    """`state.json`'s `wave`, as a string — or None, which means "no memo, just build"."""
    for workflow in _workflow_dirs():
        state = read_json(os.path.join(_runtime_root(workflow), "state.json"))
        if not isinstance(state, dict):
            continue
        wave = state.get("wave")
        if isinstance(wave, bool) or not isinstance(wave, (str, int)):
            continue                      # bool is an int; a wave is a name, not a flag
        wave = str(wave).strip()
        if wave:
            return wave
    return None


def mint_wave_id(members):
    """-> the id for a wave dispatching `members`, DERIVED rather than allocated.

    A wave is identified by what it dispatched and where: the sorted member ids plus `HEAD`.
    Nothing has to hand out numbers, keep a counter or read a clock, and re-deriving it from
    the same batch on the same tree gives the same answer -- which is what makes the build memo
    work at all, since two different waves collide only when they dispatch the same items at
    the same commit, and that is not two waves.

    This closes the half of the wave-build slot that shipped dormant: exclusion (one build at a
    time) has always been mechanical, while dedup (do not re-gate a tree this wave already
    passed) could not fire because nothing in the package ever wrote a non-null `wave`.
    """
    head = git("rev-parse", "--short", "HEAD")
    base = ",".join(sorted(str(m) for m in members)) + "|" + (head.strip() if head else "nohead")
    return "w-" + hashlib.sha256(base.encode("utf-8")).hexdigest()[:10]


# ------------------------------------------------------------------ the tree fingerprint

def _path_digest(path):
    """A digest of what is at `path` NOW, or None meaning "cannot key on this tree".

    Absent is a real, keyable state (a deletion), so it gets a constant rather than a refusal.
    Everything else that is not a readable regular file — a symlink flip, a dirty submodule, an
    oversized blob — returns None and the whole fingerprint collapses to None. That is the
    fail-toward-building rule applied to the key itself: a key that is only probably right is
    worse than no key, because the cost of no key is one build and the cost of a wrong key is a
    gate that did not run.
    """
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return b"\x00absent"
    except OSError:
        return None
    if stat.S_ISLNK(st.st_mode):
        try:
            return b"\x00link" + os.readlink(path).encode("utf-8", "surrogateescape")
        except OSError:
            return None
    if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_FILE:
        return None
    h = hashlib.sha256()
    # The exec bits, because a `chmod +x` on a script the gate runs changes what the gate DOES
    # while changing no byte of content. The index already carries mode for tracked files;
    # this is the same fact for the worktree side.
    h.update(b"m%o\0" % (st.st_mode & 0o111))
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.digest()


def _changed_paths(status_z):
    """Parse `git status --porcelain=v1 -z -uall` into [(xy, path)].

    `-z` rather than the human format on purpose: it never quotes and never escapes, so a path
    with a space or a newline in it is parsed rather than guessed at. A rename/copy entry is
    followed by its ORIGIN path as a separate NUL-terminated field, which must be consumed or
    every field after it is off by one.
    """
    fields = status_z.split("\0")
    out, i = [], 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue                      # the trailing empty field, or something unparseable
        xy, path = entry[:2], entry[3:]
        if "R" in xy or "C" in xy:
            i += 1                        # skip the origin path this entry carries
        out.append((xy, path))
    return out


def fingerprint():
    """A digest of everything the stack gate would see, or None ⇒ no key ⇒ build.

    Two halves, because the gate reads both: the INDEX (`ls-files -s` is mode+sha+stage+path for
    every tracked file — the staged tree, exactly, and it already covers `checks.env`, so a
    re-wired stack gate changes the key) and the WORKTREE DELTA (every path git reports as
    differing from the index or as untracked, hashed by content). The git pre-commit hook stashes
    unstaged changes before it runs, so its tree and the commit skill's tree are honestly
    different fingerprints whenever unstaged work exists — and they collapse to the same one, and
    so to a single build, when it does not.
    """
    index = git("ls-files", "-s")
    status = git("status", "--porcelain=v1", "-z", "-uall")
    if index is None or status is None:
        return None
    changed = _changed_paths(status)
    if len(changed) > MAX_CHANGED:
        return None
    h = hashlib.sha256()
    h.update(b"reeve-wave-build/1\0")
    h.update(index.encode("utf-8", "surrogateescape"))
    for xy, path in sorted(changed):
        digest = _path_digest(path)
        if digest is None:
            return None
        h.update(b"\0" + xy.encode("ascii", "replace") + b"\0")
        h.update(path.encode("utf-8", "surrogateescape") + b"\0")
        h.update(digest)
    return h.hexdigest()


# ------------------------------------------------------------------ the marker

def read_marker(path):
    """The marker, or None. A corrupt one is REPORTED and then treated as absent — silently
    rebuilding is correct, silently rebuilding forever without saying why is how a mechanism
    becomes folklore."""
    if not os.path.exists(path):
        return None
    data = read_json(path)
    if not isinstance(data, dict):
        sys.stderr.write("  (wave build: marker unreadable at %s — building, and rewriting it)\n"
                         % path)
        return None
    return data


def write_marker(path, data):
    """Atomic replace beside the target. Best effort by design: this file is a cache, so losing
    a write costs one rebuild and is never worth failing a gate over."""
    tmp = path + ".tmp%d" % os.getpid()
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass


# ------------------------------------------------------------------ subcommands

def cmd_claim():
    fp = fingerprint()
    print(fp or "")                       # stdout is the fingerprint channel, always
    marker = marker_path()
    if marker is None or not fp:
        return 1
    wave = wave_id()
    if not wave:
        return 1                          # the serial case: nothing named the wave, so build
    data = read_marker(marker)
    if not isinstance(data, dict) or data.get("wave") != wave:
        return 1
    passed = data.get("passed")
    hit = passed.get(fp) if isinstance(passed, dict) else None
    if not isinstance(hit, dict):
        return 1
    sys.stderr.write(
        "+ wave build slot: SKIPPING the stack gate — wave %s already passed this exact tree "
        "at %s (pid %s). Re-running it cannot change the answer.\n"
        % (wave, hit.get("at", "?"), hit.get("pid", "?")))
    return 0


def cmd_record(fp):
    marker = marker_path()
    wave = wave_id()
    fp = fp or fingerprint()
    if marker is None or not wave or not fp:
        return 0                          # nothing to remember is not a failure
    data = read_marker(marker)
    if not isinstance(data, dict) or data.get("wave") != wave:
        data = {"wave": wave, "passed": {}}     # a new wave drops the old wave's memo whole
    passed = data.get("passed")
    if not isinstance(passed, dict):
        passed = {}
    passed[fp] = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "pid": os.getpid()}
    if len(passed) > MAX_PASSES:
        keep = sorted(passed.items(), key=lambda kv: str(kv[1].get("at", "")))[-MAX_PASSES:]
        passed = dict(keep)
    write_marker(marker, {"wave": wave, "passed": passed})
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="the wave's authoritative build slot")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("claim", help="0 = this wave already passed this tree; 1 = run the build")
    mint = sub.add_parser("mint", help="print the wave id for a batch (write it to state.json `wave`)")
    mint.add_argument("members", nargs="+", help="the item ids this wave dispatches")
    rec = sub.add_parser("record", help="record a PASS for the tree `claim` measured")
    rec.add_argument("--fingerprint", default="")
    args = ap.parse_args(argv)
    # A bug in here must never be the reason a commit is refused OR allowed unverified. `claim`
    # answers 1 (build) on anything unexpected; `record` answers 0 (nothing remembered).
    try:
        if args.cmd == "claim":
            return cmd_claim()
        if args.cmd == "mint":
            print(mint_wave_id(args.members))
            return 0
        return cmd_record(args.fingerprint.strip())
    except Exception as exc:                                  # noqa: BLE001 — deliberate floor
        sys.stderr.write("  (wave build slot: %s failed (%s) — building)\n" % (args.cmd, exc))
        return 1 if args.cmd == "claim" else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(1)
