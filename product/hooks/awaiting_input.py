#!/usr/bin/env python3
"""A dialog is open — the third thing that must be false before a session may be reset.

Wired in `.claude/settings.json` under `Notification`. It writes `.workflow/awaiting-input.json`
when Claude Code raises a dialog a person has to answer, and the context gate reads it as a
`clear_safe` blocker.

WHY IT EXISTS, and it was found by probing rather than by reasoning. The supervisor's gate asked
two questions — is an anchor written, is a checkpoint parked — and a live probe drove a real
session into a **permission prompt**, where it sat. A permission dialog is waiting on a human
just as much as a parked checkpoint is, and it is invisible to `parked/`. A supervisor built on
the old gate would have cleared a session mid-dialog, or sent `continue` into one.

WHY A HOOK RATHER THAN READING THE SCREEN. The alternative was `tmux capture-pane` plus string
matching on dialog chrome — a gate whose correctness depends on the wording of a UI nobody here
controls, failing silently the first time a label changes. `Notification` states the fact
directly, so this crosses the same wall `context.json` does: something only the harness can see,
published where anything can read it.

WHICH TYPES COUNT, and the exclusion is the load-bearing half. `permission_prompt`,
`elicitation_dialog`, `elicitation_url_dialog` and `agent_needs_input` all mean **a dialog is
open**. `idle_prompt` does NOT and must never be added to that set: it means the session is
sitting idle waiting for a prompt, which is precisely the state a supervisor exists to act on.
Treating it as "a human is busy here" would disable the supervisor exactly when it should fire.

IT IS THE OTHER HALF OF THIS FILE'S JOB, THOUGH — and that is new. `idle_prompt` is the only
signal anything here has that the model is **not mid-turn**, so it is recorded with the opposite
polarity, into `.workflow/session-idle.json`, and `clear_safe` requires it to be PRESENT. That
gate condition exists because the three it had were all true at the exact instant they were most
wrong: `handoff.md` is written *during* a turn, so the supervisor reset every session
mid-sentence. Keys sent then are not queued into the turn — they land in the prompt box as text
and are never submitted (OBSERVED 2026-09-19). `hooks/prompt_submit.py` removes the flag the
moment a prompt is submitted, so the two hooks bracket idleness exactly rather than timing it.

MEASURED, not assumed, because the whole gate now rests on it: the harness emits
`{notification_type: "idle_prompt"}` after `messageIdleNotifThresholdMs` (default 60s) of true
idleness, and it dispatches the **hook** before it branches on `preferredNotifChannel` — so a
user who has turned OS notifications off still produces this flag. If that ever stops being
true, the supervisor stops resetting; it does not start resetting wrongly.

HOW IT CLEARS. `hooks/handoff_gate.py` (`Stop`) removes the flag: a turn that has ended cannot be
sitting in a dialog. That is the whole lifecycle — a dialog blocks the turn, so a `Stop` is proof
the dialog is gone, whether it was approved, denied or cancelled. No TTL, and deliberately none:
a guessed expiry would clear the flag while a person was still looking at the dialog.

FAIL DIRECTION. Any failure writes nothing and exits 0. A missing flag means the gate does not
know a dialog is open — which is the risk this accepts, because the opposite (a flag that cannot
be cleared) wedges the supervisor permanently. The band's own `handoff-now` is the precondition
for any of this, so the window in which a lost flag matters is small and bounded.
"""
import json
import os
import sys

# A dialog is open. `idle_prompt` is deliberately absent — see the docstring; adding it here
# would make the supervisor's own trigger read as "a human is busy".
DIALOG_TYPES = {
    "permission_prompt",
    "elicitation_dialog",
    "elicitation_url_dialog",
    "agent_needs_input",
}
IDLE_TYPE = "idle_prompt"
FLAG = "awaiting-input.json"
# Kept in step with `context_band.IDLE_FILE` by hand, like `FLAG` above and for the same reason:
# a `Notification` hook that imports the band is a hook that can fail to fire because an
# unrelated module did not parse. The duplication is two string literals; the alternative is a
# dependency on the hot path of the one signal the reset gate cannot do without.
IDLE_FLAG = "session-idle.json"


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0
    if payload.get("agent_id"):
        return 0                      # a subagent's dialog is not this session's screen

    kind = (payload.get("notification_type") or payload.get("type")
            or payload.get("matcher") or "")
    if kind not in DIALOG_TYPES and kind != IDLE_TYPE:
        return 0

    cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or "."
    workflow = os.path.join(cwd, ".workflow")
    if not os.path.isdir(workflow):
        return 0                      # no loop here to supervise

    # Two flags, opposite polarities, never both: a session cannot be idle at the prompt and
    # sitting in a dialog at the same time, and writing both would let the gate read a state
    # that does not exist.
    name = IDLE_FLAG if kind == IDLE_TYPE else FLAG
    try:
        tmp = os.path.join(workflow, "." + name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"kind": kind, "session_id": payload.get("session_id")},
                      fh, sort_keys=True)
        os.replace(tmp, os.path.join(workflow, name))
    except OSError:
        pass                          # see FAIL DIRECTION
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
