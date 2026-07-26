#!/usr/bin/env python3
"""Interactive context governor — the SessionStart(clear) rehydrate half.

Wired in `.claude/settings.json` under `SessionStart` with matcher `clear`, so it
fires the moment a session starts after `/clear`. `/clear` wipes the conversation but
preserves the filesystem (and CLAUDE.md / hooks / settings), so the durable resume
anchor `.workflow/handoff.md` is still on disk — this hook injects it as
`additionalContext` so the cleared session AUTO-REHYDRATES instead of the human having
to re-explain where the build was. It is the automatic resume half of `/dispatch`.

Emits the SessionStart JSON contract (`hookSpecificOutput.additionalContext`) and
always exits 0 (SessionStart cannot block a session anyway). Absent handoff → prints
nothing (a fresh/uninitialised project has nothing to rehydrate).
"""
import json
import os
import sys

# additionalContext is capped by the harness (~10k chars); handoff.md is a bounded
# resume anchor by design, but truncate defensively so a bloated one still injects.
MAX_CHARS = 9000


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
        return 0  # nothing to rehydrate — stay silent

    truncated = handoff
    if len(truncated) > MAX_CHARS:
        truncated = truncated[:MAX_CHARS] + "\n…(handoff truncated — read .workflow/handoff.md in full)…\n"

    context = (
        "This session was cleared (/clear). The durable resume anchor "
        "`.workflow/handoff.md` follows verbatim. Resume from it plus `git log` per your "
        "orchestrator brief: DO NOT restart the bootstrap and DO NOT re-run already-committed "
        "items. If `.workflow/state.json` shows no active run, this is an ordinary session — "
        "leave the loop alone.\n\n----- .workflow/handoff.md -----\n" + truncated
    )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # A hook error must never wedge session start; degrade to a silent no-op.
        sys.exit(0)
