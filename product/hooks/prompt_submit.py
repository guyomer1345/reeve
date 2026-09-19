#!/usr/bin/env python3
"""A turn is starting — the half that makes `session-idle.json` a bracket rather than a guess.

Wired in `.claude/settings.json` under `UserPromptSubmit`. It removes
`.workflow/session-idle.json`, the flag `awaiting_input.py` writes on the harness's `idle_prompt`
notification and the fourth condition of `clear_safe`.

WHY THE PAIR, RATHER THAN A TIMESTAMP THE SUPERVISOR AGES OUT. "Is the session idle" has an exact
answer available for free: the harness says when idleness BEGINS, and a submitted prompt is the
only thing that ends it. Between those two events the session is idle by definition. A TTL would
be a guess about model latency, and the guess fails in the unrecoverable direction — a flag that
outlives the idleness it describes is a reset fired into a running turn, which corrupts the
prompt box rather than merely wasting a poll.

WHY NOT `PreToolUse`, which also proves the session is busy. It proves it too LATE: a turn that
begins with a text response has submitted a prompt and called no tool, and the window between
those two is exactly where the supervisor's own second send would land.

FAIL DIRECTION IS THE OPPOSITE OF ITS SIBLING'S, and that asymmetry is deliberate.
`awaiting_input.py` fails by not writing, which costs a reset that does not happen. This one
fails by not REMOVING, which leaves a stale permission to reset a session that is now working —
so it does the least that can fail: no imports beyond the standard library, no parsing of the
payload before the removal is attempted, no conditions but the one that identifies the project.
An `os.remove` of a file that is already gone is the ordinary case, not an error.

IT NEVER BLOCKS. `UserPromptSubmit` can veto a prompt; this hook has no opinion about prompts and
must never acquire one — it exits 0 on every path, including the ones that failed.
"""
import json
import os
import sys

# Kept in step with `context_band.IDLE_FILE` and `awaiting_input.IDLE_FLAG` by hand — see the
# note there. This hook must not import a module that could fail to parse.
IDLE_FLAG = "session-idle.json"


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    # A subagent does not own this session's screen, and the supervisor never types at one.
    if payload.get("agent_id") or payload.get("agent_type"):
        return 0

    cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or "."
    try:
        os.remove(os.path.join(cwd, ".workflow", IDLE_FLAG))
    except OSError:
        pass                          # already gone, or no project here — both are fine
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
