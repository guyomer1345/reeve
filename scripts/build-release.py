#!/usr/bin/env python3
"""build-release.py — emit the shippable product tree from the manifest.

This is the PROOF that the product boundary is real. `product/MANIFEST.json`
draws the ship line once; this script is one of its three consumers (the other
two are the leak check and /start's install step). It copies exactly the
manifest's `ship` set — honouring `exclude` — plus the plugin infrastructure
(`.claude-plugin/plugin.json`, `MANIFEST.json`) into a clean output tree, and
asserts that nothing from the construction record (the numbered design docs, the
decision log, the meta-only gates, this repo's own working brief) can leak in.

Meta-only, stdlib-only (json, shutil, fnmatch), zero-dep. Two modes:
  --check          dry-run into a temp dir + assert the invariants, emit nothing
                   (default; wired into the meta-repo pre-commit)
  --out <dir>      emit the clean tree to <dir> for a real release build

Run it after any change to what ships: if a new shipped file is added to the
tree but not to the manifest, `--check` fails loudly — which is the whole point
of retiring the two hand-kept lists that silently missed loop.sh and
check_demo_bundle.py.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCT = os.path.join(REPO, "product")
MANIFEST = os.path.join(PRODUCT, "MANIFEST.json")

# Plugin infrastructure that ships but lives outside the `ship` content dirs.
ALWAYS = ["MANIFEST.json", os.path.join(".claude-plugin", "plugin.json")]

# Build cruft that is never source and must never reach a release tree — pruned
# regardless of the manifest (running the tests litters product/scripts with
# __pycache__/*.pyc, which os.walk would otherwise sweep in, and which slip past
# a `test_*.py` exclude because a `.pyc` basename does not match `*.py`).
_IGNORE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
_IGNORE_SUFFIXES = (".pyc", ".pyo")
_IGNORE_FILES = {".DS_Store"}

# Sentinels that must NEVER appear in a release tree — the construction record.
# A release that contains any of these means the boundary leaked; fail loudly.
FORBIDDEN_NAMES = {
    "08-decision-log.md", "check-no-spec-refs.sh", "check-status-coherence.sh",
    "check_enum_coherence.py", "build-release.py",
}


def _excluded(rel, patterns):
    """True if the product-relative posix path matches any exclude glob.

    A `**/` prefix means "at any depth" — matched against the basename so
    `**/test_*.py` catches both scripts/test_bus.py and scripts/codemap/test_*.py.
    """
    base = os.path.basename(rel)
    for pat in patterns:
        if pat.startswith("**/"):
            if fnmatch.fnmatch(base, pat[3:]):
                return True
        elif fnmatch.fnmatch(rel, pat):
            return True
    return False


def load_manifest():
    with open(MANIFEST, encoding="utf-8") as f:
        m = json.load(f)
    for key in ("ship", "install"):
        if key not in m:
            raise SystemExit(f"BLOCKED: MANIFEST.json missing required key {key!r}")
    return m


def shipped_files(m):
    """Every product-relative file that ships, honouring `exclude`.

    Raises if a declared ship path does not exist — a manifest that names a
    path the tree doesn't have is drift the same as the reverse.
    """
    excl = m.get("exclude", [])
    out = []
    missing = []
    for entry in m["ship"] + ALWAYS:
        abspath = os.path.join(PRODUCT, entry)
        if not os.path.exists(abspath):
            missing.append(entry)
            continue
        if os.path.isfile(abspath):
            rel = entry
            if not _excluded(rel, excl):
                out.append(rel)
            continue
        for dirpath, dirs, files in os.walk(abspath):
            dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]  # never descend build cruft
            for fn in files:
                if fn.endswith(_IGNORE_SUFFIXES) or fn in _IGNORE_FILES:
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, PRODUCT)
                if not _excluded(rel, excl):
                    out.append(rel)
    if missing:
        raise SystemExit("BLOCKED: MANIFEST.json names ship path(s) that do not "
                         "exist under product/:\n  " + "\n  ".join(sorted(missing)))
    return sorted(out)


def emit(m, out_dir):
    files = shipped_files(m)
    for rel in files:
        src = os.path.join(PRODUCT, rel)
        dst = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    return files


def assert_clean(out_dir, files):
    """The release tree must be product-only: no excluded file, no construction
    record. Both are checked against what actually landed on disk, not the plan."""
    errs = []
    for dirpath, _dirs, names in os.walk(out_dir):
        for fn in names:
            if fnmatch.fnmatch(fn, "test_*.py"):
                rel = os.path.relpath(os.path.join(dirpath, fn), out_dir)
                errs.append(f"excluded file leaked into release: {rel}")
            if fn in FORBIDDEN_NAMES:
                rel = os.path.relpath(os.path.join(dirpath, fn), out_dir)
                errs.append(f"construction-record file leaked into release: {rel}")
    for needed in ("MANIFEST.json", os.path.join(".claude-plugin", "plugin.json")):
        if not os.path.exists(os.path.join(out_dir, needed)):
            errs.append(f"release tree is missing plugin infrastructure: {needed}")
    # every install src must ship (so /start never copies outside the boundary)
    return errs


def check_install_covered(m, files):
    shipped = set(files)
    errs = []
    for pair in m["install"]:
        src = pair["src"]
        # a dir src (e.g. scripts/codemap) is covered if any shipped file is under it
        covered = src in shipped or any(f == src or f.startswith(src + os.sep)
                                        for f in shipped)
        if not covered:
            errs.append(f"install src {src!r} is not in the shipped set — "
                        f"/start would copy a file outside the product boundary")
    return errs


def package_digest(m=None, files=None, root=None):
    """A sha256 over the SHIPPED file set — the identity a smoke receipt attests to.

    `root` points the same computation at a DIFFERENT copy of the package — an installed plugin
    in the CLI's cache, rather than this working tree. One implementation answers "what is this
    package" for both, because two answers to that is the drift this repo's own law forbids, and
    because comparing an install to the tree is only meaningful if both are measured the same
    way. Raises the same way on a copy that is missing a shipped file: incomplete is not equal.

    THE KEY IS THE PACKAGE, NOT `HEAD`, and that choice is what makes a two-hour gate usable.
    Keying on the commit meant a docs-only commit — a decision-log entry, a roadmap edit —
    invalidated an attestation about behaviour it could not possibly have changed, forcing a full
    re-run or an `--no-smoke` override. A gate that expensive, invalidated that often, is a gate
    that gets skipped, which is the failure this whole layer exists to prevent.

    The smoke drive tests the package. So the receipt is invalidated by changes to the package
    and by nothing else, and the manifest already says exactly which files those are.
    """
    if m is None:
        m = load_manifest()
    if files is None:
        files = shipped_files(m)
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        with open(os.path.join(root or PRODUCT, rel), "rb") as fh:
            h.update(hashlib.sha256(fh.read()).digest())
    return h.hexdigest()


def smoke_state():
    """The reason an emit must not proceed, or None when the receipt is current.

    The smoke drive is a PRE-RELEASE gate that cannot run here — it spends real model calls and
    takes about forty minutes. So the gate is its receipt, checked at the one moment it matters:
    cutting a release. Anything else would be a documented step, and this repo has now learned
    three times that a documented step nobody runs is not a control.
    """
    receipt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".smoke-receipt.json")
    receipt = os.path.normpath(receipt)
    try:
        with open(receipt, encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        return "no smoke-drive receipt — the package has never been run as an installed whole"

    digest = package_digest()
    modes = rec.get("modes") if isinstance(rec.get("modes"), dict) else {}
    # PER MODE, because the two paths are independently attestable and re-running the one that
    # is already green buys nothing but an hour. A mode whose entry names a different package is
    # simply not attested; the run that fixes one mode does not throw the other away unless the
    # package itself changed.
    fresh = sorted(name for name, e in modes.items()
                   if isinstance(e, dict) and e.get("package") == digest)
    if fresh == ["brownfield", "greenfield"]:
        return None
    stale = sorted(set(modes) - set(fresh))
    missing = sorted({"brownfield", "greenfield"} - set(fresh))
    return ("the smoke receipt does not cover this package (%s) — %s%s. The defect this gate "
            "exists for is visible only by comparing BOTH bootstrap paths."
            % (digest[:12],
               "not attested: " + ", ".join(missing),
               ("; stale: " + ", ".join(stale)) if stale else ""))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Emit / verify the shippable product tree.")
    ap.add_argument("--out", metavar="DIR", help="emit the clean tree to DIR")
    ap.add_argument("--check", action="store_true",
                    help="dry-run + assert invariants, emit nothing (the default)")
    ap.add_argument("--no-smoke", action="store_true",
                    help="emit WITHOUT a current smoke-drive receipt. An explicit override, "
                         "never a default: the receipt is the only evidence the package works "
                         "as an installed whole, and every defect that motivated it was "
                         "invisible to the unit suite and to this boundary check.")
    args = ap.parse_args(argv)

    m = load_manifest()
    files = shipped_files(m)
    install_errs = check_install_covered(m, files)

    if args.out and not args.check:
        if os.path.exists(args.out) and os.listdir(args.out):
            raise SystemExit(f"BLOCKED: --out dir {args.out} exists and is not empty")
        smoke = smoke_state()
        if smoke and not args.no_smoke:
            raise SystemExit(
                "BLOCKED: %s\n"
                "  Run `scripts/smoke_drive.py --mode both` (real model calls, ~40 minutes) and\n"
                "  emit again, or pass --no-smoke to say plainly that this release was cut\n"
                "  without ever running the package as an installed whole." % smoke)
        emit(m, args.out)
        clean_errs = assert_clean(args.out, files)
        errs = install_errs + clean_errs
        if errs:
            print("build-release: INVALID")
            for e in errs:
                print(f"  - {e}")
            return 1
        print(f"OK: emitted {len(files)} files to {args.out} "
              f"(clean product-only tree, no construction record)")
        return 0

    # default / --check: emit into a temp dir, assert, discard
    tmp = tempfile.mkdtemp(prefix="release-check-")
    try:
        emit(m, tmp)
        clean_errs = assert_clean(tmp, files)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    errs = install_errs + clean_errs
    if errs:
        print("build-release: INVALID — the manifest boundary is not clean")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"OK: release boundary clean — {len(files)} shipped files, "
          f"{len(m['install'])} install entries, no construction record leaks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
