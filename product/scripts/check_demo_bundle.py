#!/usr/bin/env python3
"""Lint a throwaway demo-sandbox bundle for the format discipline the serving CSP does
NOT enforce.

The bundle is served under `Content-Security-Policy: sandbox allow-scripts allow-forms`.
That directive buys ISOLATION — an opaque origin the demo cannot escape — and nothing
else: measured in a real browser, `eval`, `new Function`, and external hosts all still
run/load under it. So "self-contained, no external hosts, no eval" — the invariants that
make a demo render identically offline and over a tunnel, never phoning home — are not a
CSP fact. They are a create-demo authoring rule, and this is their mechanical floor: a
cheap, deterministic scan run before the demo is parked, so a slip fails LOUDLY at
generation instead of shipping a demo that quietly depends on a CDN and blanks over the
tunnel.

It also enforces the REFINE LEDGER (`.refine.json`), for a failure the format rules do
not touch. `create-demo` says a `changes` verdict edits the SPEC first and regenerates
the bundle FROM it — and that was prose with nothing behind it, so a refine could put a
decision into the throwaway bytes and nowhere else. The terminal `approve` then DELETES
those bytes and locks the spec, so a decision that never reached the spec dies at the
exact moment it is approved: the artifact the human said yes to is gone and the durable
one never learned the change. That is silent and permanent, so it gets a floor rather
than a sentence. The ledger records which spec file each round was generated from and
that file's hash at the time, and this refuses a round whose spec did not move.

The refine CAP is enforced here too, for the same reason: it was a number in two
documents that no code read, so a counter nobody increments is a circuit-breaker that
never trips.

Stdlib only. Exit 0 = clean; exit 1 = violations (printed one per line); exit 2 = usage.

  check_demo_bundle.py <bundle-dir> [--workflow-dir DIR]
"""
import hashlib
import json
import os
import re
import sys

# Text asset extensions worth scanning. Binary local assets (png/woff2/…) are fine by
# being local; an external font/image is a URL inside CSS/HTML, caught below.
TEXT_EXT = {".html", ".htm", ".js", ".mjs", ".css", ".json", ".svg", ".txt", ".map"}

# The XML/SVG namespace URIs are identifiers, never fetched — the one legitimate http(s)
# literal in a self-contained bundle. Everything else that looks like a URL is a network
# dependency that breaks offline / over the tunnel.
_NS_OK = "http://www.w3.org/"

CHECKS = (
    # (label, compiled regex, a note the fixer can act on)
    ("external-host",
     re.compile(r"https?://(?!www\.w3\.org/)[^\s\"')]+", re.I),
     "an http(s) resource — vendor it locally or inline it (the demo must render offline)"),
    ("protocol-relative-url",
     re.compile(r"""(?:src|href)\s*=\s*["']//|url\(\s*["']?//""", re.I),
     "a //host URL — same as an external host; make it local"),
    ("eval",
     re.compile(r"\beval\s*\(|\bnew\s+Function\s*\(", re.I),
     "eval / new Function — not needed for a low-fi demo, and a code smell"),
    ("babel-jsx",
     re.compile(r"""type\s*=\s*["']text/babel["']|@babel/standalone|@babel""", re.I),
     "runtime JSX/Babel — huge and needs unsafe-eval; write vanilla or vendored htm+preact"),
    ("bundler-dep",
     re.compile(r"\bnode_modules\b|\brequire\s*\(", re.I),
     "an npm/bundler dependency — the bundle must be build-free and self-contained"),
)


def scan_text(path, text):
    """Yield (lineno, label, snippet, note) for every violation in one file."""
    for lineno, line in enumerate(text.splitlines(), 1):
        for label, rx, note in CHECKS:
            m = rx.search(line)
            if m:
                snippet = m.group(0)
                if len(snippet) > 80:
                    snippet = snippet[:77] + "..."
                yield lineno, label, snippet, note


REFINE_LEDGER = ".refine.json"
DEFAULT_MAX_REFINE = 3


def _sha256(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def _max_refine(workflow_dir):
    """`config.demo.max_refine_rounds`, defaulted. An unreadable config is not a reason
    to refuse a demo — it falls back rather than inventing a failure."""
    try:
        with open(os.path.join(workflow_dir, "config.json")) as fh:
            cfg = json.load(fh)
        n = (cfg.get("demo") or {}).get("max_refine_rounds")
        if isinstance(n, int) and n > 0:
            return n
    except (OSError, ValueError, AttributeError):
        pass
    return DEFAULT_MAX_REFINE


def check_refine_ledger(bundle_dir, workflow_dir):
    """Enforce `.refine.json`: shape, the cap, and that each round MOVED THE SPEC.

    Absent is fine — round 0 is a demo nobody has asked to change yet. Present means
    every entry must name the spec it was regenerated from and that file's hash at the
    time, and the check is the one thing a composer cannot satisfy by remembering to set
    a flag: the recorded hash must match the file on disk NOW (so the ledger describes
    the real spec, not an aspiration), and it must differ from the previous round's (so
    the spec actually changed when the human asked for a change).
    """
    path = os.path.join(bundle_dir, REFINE_LEDGER)
    if not os.path.exists(path):
        return []
    try:
        with open(path) as fh:
            led = json.load(fh)
    except (OSError, ValueError) as exc:
        return ["%s: unreadable (%s) — it is the refine circuit-breaker; a bundle whose "
                "round count cannot be read must not be parked" % (REFINE_LEDGER, exc)]
    if not isinstance(led, dict):
        return ["%s: must be an object {round, rounds[]}" % REFINE_LEDGER]

    rounds = led.get("rounds")
    n = led.get("round")
    if not isinstance(n, int) or n < 0:
        return ["%s: `round` must be a non-negative integer" % REFINE_LEDGER]
    cap = _max_refine(workflow_dir)
    if n > cap:
        return ["%s: round %d exceeds config.demo.max_refine_rounds (%d) — do NOT "
                "auto-proceed; escalate to a live `discuss` carrying the refine history"
                % (REFINE_LEDGER, n, cap)]
    if n == 0:
        return []
    if not isinstance(rounds, list) or len(rounds) != n:
        return ["%s: `rounds[]` must hold one entry per round (round=%d, entries=%s)"
                % (REFINE_LEDGER, n, len(rounds) if isinstance(rounds, list) else "none")]

    violations, previous = [], None
    root = os.path.dirname(os.path.abspath(workflow_dir))
    for i, entry in enumerate(rounds, 1):
        at = "%s rounds[%d]" % (REFINE_LEDGER, i)
        if not isinstance(entry, dict):
            violations.append("%s: must be an object {round, spec_ref}" % at)
            continue
        ref = entry.get("spec_ref")
        if not isinstance(ref, dict) or not isinstance(ref.get("path"), str) \
                or not isinstance(ref.get("sha256"), str):
            violations.append(
                "%s: needs spec_ref {path, sha256} — the spec this round was regenerated "
                "FROM. A refine edits the spec first; the bundle is pruned on approve, so "
                "a decision only in the bundle dies when it is approved" % at)
            continue
        spec = os.path.join(root, ref["path"])
        got = _sha256(spec)
        if got is None:
            violations.append("%s: spec_ref.path does not exist or cannot be read (%s)"
                              % (at, ref["path"]))
        elif i == len(rounds) and got != ref["sha256"]:
            # Only the LATEST round is pinned to the file's current bytes. Earlier rounds
            # legitimately describe superseded revisions — requiring those to match would
            # make every later edit retroactively invalid.
            violations.append(
                "%s: spec_ref.sha256 does not match %s as it is on disk now — regenerate "
                "the bundle FROM the current spec and re-record" % (at, ref["path"]))
        if previous is not None and ref.get("sha256") == previous:
            violations.append(
                "%s: the spec did not change from the previous round. A `changes` verdict "
                "edits the SPEC and regenerates from it; a round that only rewrote the "
                "bundle leaves the decision nowhere durable" % at)
        previous = ref.get("sha256")
    return violations


def lint(bundle_dir, workflow_dir=None):
    """Return a list of violation strings (empty => clean)."""
    violations = []
    if not os.path.isdir(bundle_dir):
        return ["%s: not a directory" % bundle_dir]
    # demos/<item-id>/ sits under .workflow/, so the workflow dir is two levels up unless
    # the caller says otherwise.
    if workflow_dir is None:
        workflow_dir = os.path.dirname(os.path.dirname(os.path.abspath(bundle_dir)))
    if not os.path.exists(os.path.join(bundle_dir, "index.html")):
        violations.append("%s: no index.html (a bundle's entry point is index.html)"
                          % bundle_dir)
    for root, _dirs, files in os.walk(bundle_dir):
        for name in sorted(files):
            ext = os.path.splitext(name)[1].lower()
            full = os.path.join(root, name)
            rel = os.path.relpath(full, bundle_dir)
            if ext not in TEXT_EXT:
                continue
            try:
                with open(full, "r", errors="replace") as fh:
                    text = fh.read()
            except OSError as exc:
                violations.append("%s: cannot read (%s)" % (rel, exc))
                continue
            for lineno, label, snippet, note in scan_text(full, text):
                violations.append("%s:%d: %s: %s — %s"
                                  % (rel, lineno, label, snippet, note))
    violations.extend(check_refine_ledger(bundle_dir, workflow_dir))
    return violations


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    workflow_dir = None
    for i, a in enumerate(argv):
        if a == "--workflow-dir" and i + 1 < len(argv):
            workflow_dir = argv[i + 1]
            args = [x for x in args if x != workflow_dir]
    if len(args) != 1:
        sys.stderr.write("usage: check_demo_bundle.py <bundle-dir> "
                         "[--workflow-dir DIR]\n")
        return 2
    violations = lint(args[0], workflow_dir)
    if violations:
        sys.stderr.write("BLOCKED: this demo bundle must not be parked:\n")
        for v in violations:
            sys.stderr.write("  " + v + "\n")
        return 1
    print("OK: demo bundle is self-contained (no external hosts, no eval, build-free) "
          "and its refine ledger is sound")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
