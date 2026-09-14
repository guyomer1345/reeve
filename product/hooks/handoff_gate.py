#!/usr/bin/env python3
"""Interactive context governor — the half that ACTS.

Wired in `.claude/settings.json` under `Stop`, which takes no matcher: it fires whenever the
orchestrator finishes a turn. When `context_band.py` says `handoff-now` and no anchor has been
written since it started saying so, this hook **blocks the stop** and tells the session to write
`.workflow/handoff.md` before it ends the turn.

WHY A HOOK AND NOT A ROUTING RULE. `loop.md` carries the rule too, and the rule is the preferred
path — it fires at a clean boundary, between items, where a handoff is cheapest and most
accurate. But a routing rule is prose: a session that simply does not run it violates nothing and
nothing notices, which is precisely how the band came to be a better banner read by nobody. The
hook is the backstop that makes the omission impossible rather than merely discouraged. Same
shape as `precompact.py`: a governor plus something that fires whether or not it is obeyed.

IT BLOCKS, WHERE `precompact.py` CANNOT. PreCompact must not fight the context ceiling — the
compaction is happening regardless and the job there is to survive it. A `Stop` is different:
nothing irreversible is in flight, the band's whole reserve (two nodes) exists to pay for exactly
this turn, and the failure being prevented — a session that stops with no anchor — is the only
one that loses the loop's place.

THREE THINGS IT DELIBERATELY DOES NOT DO.
  · It does not ask whether a checkpoint is open. Writing an anchor is always safe; gating it on
    a reachable runtime root would withhold the anchor exactly when a broken runtime makes it
    most valuable. That question belongs to `clear_safe`, whose consumer is the supervisor.
  · It does not send `/clear`, and it could not — a hook cannot drive the session. It brings the
    session to the state from which a reset is safe, and stops there.
  · It does not run `/dispatch`. A model cannot invoke its own slash command, so the instruction
    below carries the procedure's load-bearing steps inline rather than pointing at a command
    file that may not exist in the target's `.claude/commands/`.

LOOP STOP. Claude Code's `Stop` payload carries no `stop_hook_active`, so the count is kept here:
after MAX_DEMANDS blocks with the anchor still unwritten, the hook gives up and lets the turn
end, saying so. A hook that blocks forever wedges the session it was protecting.

FAIL DIRECTION is open, unlike the band's. Any failure — no `.workflow/`, no reading, an
unimportable `context_band`, a torn latch — exits 0 and lets the turn end. A session wrongly
stopped without an anchor loses its place; a session wrongly prevented from ever stopping loses
everything it was doing.
"""
import json
import os
import sys

MAX_DEMANDS = 2

INSTRUCTION = (
    "CONTEXT GATE — %s\n\n"
    "Do not end this turn and do not start new work. Write the resume anchor first, which is "
    "what `/dispatch` does:\n"
    "1. `python3 .claude/scripts/bus.py mirror --workflow-dir .workflow` (re-projects the "
    "open-checkpoint block; if it fails, say so plainly and route to `/rebind` — do not "
    "hand-write a `parked[]` you cannot verify).\n"
    "2. Rewrite `.workflow/handoff.md` whole with Write/Edit — never a Bash `>` redirect — for a "
    "session that knows nothing: the `bootstrap:` line if the bootstrap is still in motion, "
    "`current_item`, `loop_position`, `base_sha` = `git rev-parse HEAD`, and in prose what is "
    "committed vs uncommitted right now, what the next action is, and any in-flight decision. "
    "Leave both machine blocks (`drain:begin…`, `parked:begin…`) byte for byte.\n"
    "3. Do not commit and do not run verify/document — this is a context snapshot, not an "
    "item-close.\n"
    "4. Then tell the human plainly that the anchor is written and a `/clear` is safe, and that "
    "the cleared session needs a bare `continue` to pick it up — it does not start on its own."
)

GAVE_UP = (
    "Context gate: asked %d times for a handoff and `.workflow/handoff.md` has not moved. "
    "Letting the turn end rather than wedging the session — but this session's place is not "
    "saved. Run /dispatch, then /clear."
)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = None
    if not isinstance(payload, dict):
        # A payload that will not parse establishes NEITHER of the two facts this hook needs:
        # whose stop it is, and which project. Blocking on a guess could wedge a subagent.
        return 0

    # A subagent's stop, not the orchestrator's. The band measures the session that owns the
    # window and the handoff; a worker has neither.
    if payload.get("agent_id") or payload.get("agent_type"):
        return 0

    cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or "."
    sys.path.insert(0, os.path.join(cwd, ".claude", "scripts"))
    import time

    import context_band as cb

    workflow = os.path.join(cwd, ".workflow")
    # A turn that has ended cannot be sitting in a dialog, whether it was approved, denied or
    # cancelled — so this is where `awaiting-input.json` is retired. Deliberately not a TTL: a
    # guessed expiry would clear the flag while a person was still looking at the prompt.
    cb.clear_awaiting(workflow)
    verdict = cb.demand(workflow, project_dir=cwd, now=time.monotonic())
    if not verdict.get("needs_handoff"):
        return 0

    if verdict.get("demands", 0) >= MAX_DEMANDS:
        print(json.dumps({"systemMessage": GAVE_UP % MAX_DEMANDS}))
        return 0

    cb.record_demand(workflow)
    reason = INSTRUCTION % verdict.get("reason", "the context band says hand off now.")
    # BELT AND BRACES, because this hook is the whole actuator and a block that does not land
    # leaves the slice exactly where it started — a band nobody acts on. Two documented
    # mechanisms, pointing the same way, carrying the same text:
    #   · exit 2, which blocks a `Stop` *regardless of JSON output*, with the instruction on
    #     stderr (fed to the model);
    #   · `hookSpecificOutput.decision: "block"` on stdout, the shape the reference documents,
    #     plus the older top-level `decision`/`reason` pair that shipped versions still read.
    # Whichever the running harness honours, it blocks once and reads the same reason. The cost
    # is a duplicated string; the cost of guessing wrong is the actuator.
    print(json.dumps({
        "decision": "block",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "decision": "block",
            "reason": reason,
        },
    }))
    sys.stderr.write(reason + "\n")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        # Never wedge a session. An unwritten handoff costs this session's place; a turn that
        # can never end costs the work in it.
        sys.exit(0)
