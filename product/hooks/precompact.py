#!/usr/bin/env python3
"""Interactive context governor — the PreCompact backstop half.

Wired in `.claude/settings.json` under `PreCompact` (both `manual` and `auto`
matchers), so it fires before EITHER kind of compaction — the automatic safety net
for a human who sails past the statusline warning without running `/dispatch` + `/clear`.

A deterministic hook cannot AUTHOR a fresh handoff (that needs a model turn), so what
it does is preserve state ACROSS the compaction: it injects the current
`.workflow/handoff.md` as `additionalContext` (which survives compaction as a system
reminder) plus a directive to refresh it. The durable anchor is thus never lost to a
compaction, and the post-compaction model is told to re-run `/dispatch` if mid-task.

It is a BACKSTOP, not a gate: it exits 0 and never blocks compaction (exit 2 would
block manual and auto, but the context ceiling is real and must not be fought — the
job here is to preserve state through the reset, not prevent it).
"""
import json
import os
import sys

MAX_CHARS = 9000  # additionalContext is capped (~10k); handoff.md is bounded by design.


def read_handoff(cwd):
    # handoff.md is COMMITTED (never relocated), so it is read under .workflow/ directly.
    path = os.path.join(cwd or ".", ".workflow", "handoff.md")
    try:
        with open(path) as fh:
            return fh.read()
    except Exception:
        return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    cwd = payload.get("cwd") or "."

    handoff = read_handoff(cwd)
    if not handoff or not handoff.strip():
        return 0  # no active build / uninitialised — nothing to preserve

    truncated = handoff
    if len(truncated) > MAX_CHARS:
        truncated = truncated[:MAX_CHARS] + "\n…(handoff truncated — read .workflow/handoff.md in full)…\n"

    context = (
        "Context is being compacted (the context-budget warning was reached without a "
        "manual /dispatch + /clear). The durable resume anchor `.workflow/handoff.md` follows "
        "verbatim so the reset cannot lose it. After compaction, if you are mid-task, run "
        "/dispatch to refresh this anchor before continuing.\n\n"
        "----- .workflow/handoff.md -----\n" + truncated
    )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreCompact",
            "additionalContext": context,
        }
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # A hook error must never block compaction; degrade to a silent no-op.
        sys.exit(0)
