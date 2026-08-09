#!/usr/bin/env python3
"""Shared verify-before-commit check for guard.sh (PreToolUse) and pre-commit.sh (git hook).

Both hooks must enforce the same rule — an item cannot be committed until its `verify` passed —
and must enforce it IDENTICALLY. This is the single implementation they both call, so the two
copies can never drift (the drift is exactly how a safety gate quietly dies).

Fail CLOSED. Prints a one-line block reason to stdout and exits 1 when the commit must be
blocked; exits 0 when it may proceed. The caller applies its own block (guard.sh exit 2 /
pre-commit exit 1) using the printed reason.

Two drift vectors defeated the old `state.json.current_item` read, both by leaving `$item`
empty so the whole gate was skipped (fail OPEN):
  - SHAPE drift  — the orchestrator naturally wrote a nested `position.item` and omitted the
    top-level `current_item`; and
  - PATH drift   — on a relocated runtime tree (`runtime.json`) the hardcoded
    `.workflow/state.json` is absent, so `json.load` threw and was swallowed.
So this does NOT trust a single fragile key or path:
  - PRIMARY: derive the item(s) under commit from the STAGED diff (`.workflow/items/<id>/`) —
    always local, always ground truth, immune to both drift vectors.
  - CROSS-CHECK: read state.json runtime-aware (via runtime.json, like bus.py) and robustly
    (`current_item` OR `position.item`). A `status: building` with no identifiable item is a
    fail-closed block, not a skip.

NOT EVERY COMMIT CARRIES A BUILT ITEM, and the fail-closed rule above had no way to say so, so
two legitimate motions had no legal commit at all:
  - the `/start` BOOTSTRAP publishes `building` before any item exists  -> `_bootstrapping()`;
  - a MAINTENANCE item (`loop.md` § Maintenance items) runs its own pass and flows straight to
    commit with no planner/execute/verify  -> a staged maintenance RECEIPT (below).
Both escapes take an explicit marker the motion itself publishes, never an inference from an
absent item. The maintenance marker is deliberately NOT a `state.json` field: bootstrap's phase
marker is safe because it fires once and then disappears forever, whereas maintenance recurs for
the life of the project — a volatile marker for a recurring motion re-arms on every threshold hit
and, left stale by a crashed pass, would disarm this gate for the next PRODUCT-CODE commit. That
is the same fail-open shape as the two drift vectors above. A marker carried in the commit under
review cannot go stale, and is visible in the diff a human reads.
"""
import json
import os
import re
import subprocess
import sys

WORKFLOW = ".workflow"
# The verdict lives in the COMMITTED half (never relocated), so it is read under .workflow/.
ITEM_DIR_RE = re.compile(r"^\.workflow/items/([^/]+)/")
MAINT_RE = re.compile(r"^\.workflow/maintenance/([^/]+)\.json$")
PASS_TRUE_RE = re.compile(r"(?i)^\s*pass:\s*true(\W|$)")
PASS_FALSE_RE = re.compile(r"(?i)^\s*pass:\s*false(\W|$)")
# The `loop.md` maintenance nodes — the only kinds a receipt may claim.
MAINT_KINDS = ("align", "document:audit", "doc-budget")


def resolve_runtime_root():
    """Mirror bus.py Paths._resolve_runtime_root: absent/empty pointer => the workflow dir IS
    the runtime root (the common, non-relocated case)."""
    pointer = os.path.join(WORKFLOW, "runtime.json")
    try:
        with open(pointer) as fh:
            root = json.load(fh).get("runtime_root")
    except FileNotFoundError:
        return WORKFLOW
    except (OSError, ValueError):
        # An unreadable pointer must not silently disable the gate; the state read below still
        # fails closed if it depends on state.json, and the staged-diff derivation is unaffected.
        return WORKFLOW
    if not root:
        return WORKFLOW
    root = os.path.abspath(os.path.expanduser(root))
    return root if os.path.isdir(root) else WORKFLOW


def staged_paths():
    """The staged paths, ADDED/MODIFIED ONLY — `--diff-filter=d` drops deletions.

    That filter is load-bearing, not tidiness. `git diff --cached --name-only` lists deleted
    paths too, and a deleted `.workflow/items/<id>/...` still matches ITEM_DIR_RE — so the
    `document:audit` retention prune re-derived every dir it had just deleted as an item under
    commit, went looking for the verdict inside it, and blocked on the file the same commit was
    deleting. A deletion is the one change that can carry nothing left to verify.
    """
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=d"],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        return []
    if out.returncode != 0:
        return []
    return [name.strip() for name in out.stdout.splitlines() if name.strip()]


def staged_item_ids(paths):
    ids = []
    for name in paths:
        m = ITEM_DIR_RE.match(name)
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def maintenance_receipts(paths):
    """(ids, complaints) for the staged `.workflow/maintenance/<id>.json` receipts.

    VALIDATED, because an unvalidated marker is a hole — any file that landed in that directory
    would otherwise satisfy the identifiable-item tripwire. A receipt must parse, must name the
    node it ran, and must agree with its own filename; anything else is not a receipt and is
    reported as the reason the commit is blocked rather than silently ignored (a format slip
    fails the same direction the verdict's does). Read from the worktree, like the verdict.
    """
    ids, bad = [], []
    for name in paths:
        m = MAINT_RE.match(name)
        if not m:
            continue
        ident = m.group(1)
        try:
            with open(name, encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            bad.append("%s is not readable JSON" % name)
            continue
        if not isinstance(rec, dict):
            bad.append("%s is not a JSON object" % name)
        elif rec.get("item") != ident:
            bad.append("%s declares item %r, which does not match its filename"
                       % (name, rec.get("item")))
        elif rec.get("kind") not in MAINT_KINDS:
            bad.append("%s declares kind %r (expected one of: %s)"
                       % (name, rec.get("kind"), ", ".join(MAINT_KINDS)))
        elif ident not in ids:
            ids.append(ident)
    return ids, bad


def read_state(runtime_root):
    try:
        with open(os.path.join(runtime_root, "state.json")) as fh:
            return json.load(fh)
    except Exception:
        return None


def _bootstrapping(state):
    """The /start motion publishes `status: building, phase: bootstrap` at every stage boundary
    so the console can render progress — before any item exists. That is NOT drift, and the
    unidentifiable-item block would otherwise reject EVERY bootstrap commit (the scaffold commit
    included), dead-ending a brownfield install at step 7.

    Deliberately narrow: it takes the explicit `phase` marker, never an inference from an absent
    item, so the only state that skips the fail-closed is one the bootstrap ITSELF published.
    A `building` state with no item and no bootstrap phase still blocks, and a bootstrap commit
    that DOES stage an item dir still has that item's verdict checked below.
    """
    return (state.get("phase") or (state.get("position") or {}).get("phase")) == "bootstrap"


def verdict_ok(item):
    """Fail-closed verdict check: proceed only on a well-formed `pass: true` first line."""
    path = os.path.join(WORKFLOW, "items", item, "verify-verdict.md")
    if not os.path.isfile(path):
        return False, "item %s has no verify-verdict.md; run verify before committing." % item
    try:
        with open(path) as fh:
            first = fh.readline().strip()
    except OSError:
        first = ""
    if PASS_FALSE_RE.match(first):
        return False, "item %s has a FAILING verify-verdict; debug -> refine -> verify before committing." % item
    if not PASS_TRUE_RE.match(first):
        return False, ("item %s verify-verdict first line must be 'pass: true' (got: %r); re-run verify."
                       % (item, first))
    return True, ""


def main():
    runtime = resolve_runtime_root()
    staged = staged_paths()
    candidates = staged_item_ids(staged)
    maintenance, bad_receipts = maintenance_receipts(staged)

    state = read_state(runtime)
    if state is not None and state.get("status") == "building":
        # Resolve the active item robustly: top-level current_item OR the nested position.item.
        active = state.get("current_item") or (state.get("position") or {}).get("item")
        # A maintenance item IS the current item while it runs and has no verdict BY DESIGN, so
        # its own id must not be promoted into the verdict-checked set. The receipt it staged is
        # what says so — never the absence of a verdict, which is indistinguishable from a skipped
        # verify. An id that ALSO staged an item dir stays a candidate: `planner` mkdirs that dir,
        # so something built under it, and a built item is verified rather than exempted.
        if active and active not in candidates and active not in maintenance:
            candidates.append(active)
        if not candidates and not maintenance and not _bootstrapping(state):
            msg = ("state.json status=building but no item is identifiable (no current_item, no "
                   "position.item, no staged .workflow/items/<id>/, no valid staged maintenance "
                   "receipt) — verify-before-commit fails closed.")
            if bad_receipts:
                msg += " Rejected receipt(s): %s." % "; ".join(bad_receipts)
            print(msg)
            return 1

    # No active build and nothing staged under an item dir => a genuine bootstrap / pre-item
    # commit (the /start scaffold, the pre-stack spec) => nothing to verify => proceed.
    for item in candidates:
        ok, msg = verdict_ok(item)
        if not ok:
            print(msg)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
