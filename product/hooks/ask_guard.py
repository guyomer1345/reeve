#!/usr/bin/env python3
"""PreToolUse(AskUserQuestion) gate: an unattended drive may not stop to ask a dialog.

WHY THIS EXISTS, and it is the fourth time this package has shipped a sensor without an
actuator. The rule was already written and well argued: `execute` is zero-decision by
construction (*"a choice the plan didn't make is a blocker, not a judgement call"*),
`decision-engineer` is *"the project's decision authority of last resort"*, and the autonomy
floor says who owns which kind of call. **Nothing enforced any of it against the one tool that
routes around all three.** `grep AskUserQuestion` over the whole package returned nothing.

WHAT AN UNANSWERED DIALOG ACTUALLY COSTS, traced rather than assumed:
  1. `hooks/awaiting_input.py` records it -- `.workflow/awaiting-input.json`.
  2. `clear_safe` requires no open dialog, so **the supervisor will never reset that session**.
  3. `monitor.py`'s ladder returns `state=waiting, action=none` on a dialog, deliberately: a
     human owes an answer, so the heartbeat stops escalating.
  4. The away channel alerts on CHECKPOINTS. A dialog is not a checkpoint.
So the drive stops, the supervisor holds, the monitor goes quiet, and **nobody is told**. That
is the eleven-hour failure of 2026-09-19 reopened through a different door -- and it was
measured live on 2026-10-01: both of the maintainer's projects carried an open dialog flag, one
of them twenty-one minutes old, while he watched one of them refuse to reset.

IT IS THE ORCHESTRATOR THAT DOES THIS, NOT A LEAF, and that is why a hook is the only place the
gate can live. Every shipped agent's tool list excludes `AskUserQuestion` -- `execute`,
`planner`, `document` and `create-demo` get `Read, Write, Edit, Grep, Glob, Bash`, `review`
gets less. So the leaves already cannot ask; the tool is reachable only from the session that
is driving, which is exactly the session no file in `.workflow/` can constrain.

ONLY WHEN THE SESSION WAS LAUNCHED UNATTENDED. `REEVE_SUPERVISE` is exported by
`loop.sh --supervise` into the session it starts, so the environment is PROOF rather than a
guess -- the same evidence `statusline.py` uses to decide whether to show the supervision
segment. In an interactive session a human is sitting there and asking them is the correct
thing to do, so this gate is silent. **The gate is about absence, not about dialogs.**

IT DENIES WITH A ROUTE, NOT A REFUSAL, on `guard.sh`'s shape: a block that only says no
teaches nothing and gets worked around. Two routes, and which one applies is decided by WHO
OWNS THE CALL, which is the autonomy floor's question and not this hook's:
  * a BUILD decision (stack, library, architecture, an approach the plan left open)
    -> `decision-engineer`, which gathers the options and market practice and returns a
       confidence-scored verdict. It is a dispatch, not a wait.
  * a PRODUCT-OWNER decision (goal acceptance, scope, a spec change, approving a demo)
    -> a `checkpoint`, which parks durably, survives a `/clear`, and reaches the away channel.
       That is the machinery built so a human can answer from a phone.
The loop picks; this hook names both and gets out of the way.

FAIL DIRECTION: allow. An unreadable payload, a missing environment variable, any exception at
all -- the question goes through. A gate that blocked a question it could not classify would
stop an interactive session from talking to the person sitting in front of it, which is worse
than the halt it prevents, because that halt at least has somebody present to notice it.
"""
import json
import os
import sys

PLUGIN = "reeve"
ASK_TOOLS = {"AskUserQuestion"}

# The proof that nobody is watching. Exported by `loop.sh --supervise` into the session it
# starts; absent in an ordinary interactive run. Read from the environment rather than from a
# file on purpose -- a durable flag would outlive the session that set it and gate the human's
# next interactive run, which is the mistake `loop.sh` itself avoided for the same reason.
SUPERVISED_ENV = "REEVE_SUPERVISE"


def read_payload():
    try:
        return json.load(sys.stdin)
    except Exception:                     # noqa: BLE001 -- fail open; see FAIL DIRECTION
        return {}


def unattended(env=None):
    """Was this session launched with nobody watching it?"""
    env = os.environ if env is None else env
    return bool((env.get(SUPERVISED_ENV) or "").strip())


def _questions(tool_input):
    """The question headers, for a block message that names what was being asked. Best-effort:
    the message is better with them and must not depend on them."""
    out = []
    for q in (tool_input or {}).get("questions") or []:
        if not isinstance(q, dict):
            continue
        label = (q.get("header") or q.get("question") or "").strip()
        if label:
            out.append(label[:60])
    return out


def block(reason):
    print("BLOCKED by %s's unattended-drive gate: %s" % (PLUGIN, reason), file=sys.stderr)
    sys.exit(2)


def main():
    payload = read_payload()
    if payload.get("tool_name") not in ASK_TOOLS:
        return 0
    if not unattended():
        return 0                          # a human is here; asking them is correct

    asked = _questions(payload.get("tool_input"))
    naming = (" The open question(s): %s." % "; ".join(asked)) if asked else ""

    block(
        "this session was launched unattended (`loop.sh --supervise`), so there is nobody to "
        "answer a dialog -- and an unanswered one is the worst halt this package has: it blocks "
        "every context reset, the heartbeat goes quiet because it reads a dialog as *a human "
        "owes an answer*, and the away channel only alerts on checkpoints. The drive would stop "
        "and nothing anywhere would say so.%s\n"
        "  Route it instead, by who owns the call:\n"
        "  - a BUILD decision (stack, library, architecture, an approach the plan left open) -> "
        "run the SKILL `%s:decision-engineer`. It gathers the options and market practice and "
        "returns a confidence-scored verdict. A dispatch, not a wait.\n"
        "  - a PRODUCT-OWNER decision (goal acceptance, scope, a spec change, approving a "
        "demo) -> park a `%s:checkpoint`. It is durable, it survives a `/clear`, and it reaches "
        "the away channel so it can be answered from a phone.\n"
        "  If it is neither -- you need a fact, not a decision -- get the fact: "
        "`%s:research` for anything external, the spec and the decision record for anything "
        "this project already settled." % (naming, PLUGIN, PLUGIN, PLUGIN)
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:                     # noqa: BLE001 -- fail open, always
        sys.exit(0)
