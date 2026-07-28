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
"""
import json
import os
import re
import subprocess
import sys

WORKFLOW = ".workflow"
# The verdict lives in the COMMITTED half (never relocated), so it is read under .workflow/.
ITEM_DIR_RE = re.compile(r"^\.workflow/items/([^/]+)/")
PASS_TRUE_RE = re.compile(r"(?i)^\s*pass:\s*true(\W|$)")
PASS_FALSE_RE = re.compile(r"(?i)^\s*pass:\s*false(\W|$)")


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


def staged_item_ids():
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        return []
    if out.returncode != 0:
        return []
    ids = []
    for name in out.stdout.splitlines():
        m = ITEM_DIR_RE.match(name.strip())
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def read_state(runtime_root):
    try:
        with open(os.path.join(runtime_root, "state.json")) as fh:
            return json.load(fh)
    except Exception:
        return None


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
    candidates = staged_item_ids()

    state = read_state(runtime)
    if state is not None and state.get("status") == "building":
        # Resolve the active item robustly: top-level current_item OR the nested position.item.
        active = state.get("current_item") or (state.get("position") or {}).get("item")
        if active and active not in candidates:
            candidates.append(active)
        if not candidates and state.get("phase") != "bootstrap":
            print("state.json status=building but no item is identifiable (no current_item, no "
                  "position.item, no staged .workflow/items/<id>/) — verify-before-commit fails closed.")
            return 1
        # phase=="bootstrap": /start publishes status=building with no item during the scaffold/spec
        # commit (the first real item only exists after reconcile->prioritize->plan). There is nothing
        # to verify, so this is NOT the "building but no item" drift the block above guards — proceed.
        # (The real drift keeps its teeth: no phase, or any non-bootstrap phase, still fails closed.)

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
