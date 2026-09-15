#!/usr/bin/env python3
"""The unattended drive's `Stop` hook — the actuator for `turn_check.py`'s ladder.

Thin by design: every judgement lives in `.claude/scripts/turn_check.py`, which is testable and
runnable by a human (`python3 turn_check.py` answers "what does this turn owe?"). This file does
the wiring only — whose stop it is, whether anyone is watching, the demand counter, and the two
documented ways of blocking a `Stop`.

SCOPED TO AN UNATTENDED DRIVE, at the maintainer's word: *"this is only when we are letting
multiple sessions go by themselves to achieve a goal not for just planning etc."* Detected from
the driver's own environment (`REEVE_DRIVE` / `REEVE_SUPERVISE`, exported by `loop.sh`) or an
explicit `config.run.drive.gate_turns` for an operator who drives some other way. A gate that
fired while a human sat there planning would be the same nuisance in the opposite direction, and
the first thing he would do is switch it off — taking the unattended case with it.

IT DEFERS TO `handoff_gate.py`. When the context band says an anchor is owed, that demand is more
urgent and already blocks; two hooks blocking one turn with two instructions is how a session
ends up obeying neither.

THE LATCH carries two facts between turns: the fingerprint at the previous stop (so "this turn
moved nothing" is answerable at all) and the report digest last satisfied (so an unchanged loop
is not asked for the same report twice). It is written on EVERY stop, including the ones that
block — otherwise the first block would poison the fingerprint comparison for the second.

LOOP STOP. After MAX_DEMANDS blocks on the same rung the hook gives up and says so. A hook that
blocks forever wedges the session it was protecting, and this one can fire on every turn.

FAIL DIRECTION IS OPEN on every path — unparseable payload, no `.workflow/`, an import that
raises, a torn latch. Same asymmetry `handoff_gate.py` argues: a session wrongly allowed to end
costs a turn; a session wrongly prevented from ending loses everything it was doing.
"""
import json
import os
import sys

MAX_DEMANDS = 2
LATCH = "turn-gate.json"

GAVE_UP = ("Turn gate: asked %d times (%s) and nothing changed. Letting the turn end rather than "
           "wedging the session — but this is being recorded as a stop for no reason.")


def _latch(workflow):
    try:
        with open(os.path.join(workflow, LATCH), encoding="utf-8") as fh:
            val = json.load(fh)
        return val if isinstance(val, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_latch(workflow, rec):
    path = os.path.join(workflow, LATCH)
    tmp = path + ".tmp-%d" % os.getpid()
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, sort_keys=True)
        os.replace(tmp, path)
    except OSError:
        pass


def unattended(workflow):
    if os.environ.get("REEVE_DRIVE") or os.environ.get("REEVE_SUPERVISE"):
        return True
    try:
        with open(os.path.join(workflow, "config.json"), encoding="utf-8") as fh:
            cfg = json.load(fh)
        return bool(((cfg.get("run") or {}).get("drive") or {}).get("gate_turns"))
    except (OSError, ValueError, AttributeError):
        return False


# How many assistant messages back the report marker is looked for. NOT a tolerance for a stale
# report -- the DIGEST is what decides currency, and a report from an earlier state simply will
# not match. This is a tolerance for a WRITE RACE, measured on a real drive: the session pasted
# the report, and the very next line in the transcript is this gate blocking with "no goal report
# was given this turn". The `Stop` hook races the flush of the message that triggered it, so "the
# last assistant message" is not reliably the one the session just wrote.
#
# WHY THIS CONVERGES WHERE ONE MESSAGE DID NOT. Unseen once is recoverable; unseen forever is
# not. With a window, a paste the hook could not see at stop N is certainly on disk by stop N+1,
# so the race can DELAY credit by a turn but cannot deny it. With a window of one, the block
# itself pushes the paste out of last position — the session answers the block, that answer
# becomes the last message, and the report is never seen again. The observed run went: demand,
# paste, demand again, paste again, GAVE UP — a session that complied twice, recorded as "a stop
# for no reason". A gate whose only terminal state is a false accusation teaches the operator to
# switch it off, which is the whole failure this rung exists to avoid.
LOOKBACK = 4


def last_assistant_text(transcript, limit=LOOKBACK):
    """The last few assistant messages of the session, newest first, or ''.

    Scanned from the end and stopped after `limit` of them, so the cost does not grow with the
    session. Joined rather than returned separately: every caller is asking "did the session say
    X", and none of them cares which message it was in."""
    try:
        with open(transcript, encoding="utf-8") as fh:
            lines = fh.readlines()
    except (OSError, UnicodeDecodeError, TypeError):
        return ""
    out = []
    for raw in reversed(lines):
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        if rec.get("type") != "assistant":
            continue
        content = (rec.get("message") or {}).get("content")
        if isinstance(content, str):
            out.append(content)
        else:
            out.append("\n".join(b.get("text") or "" for b in content or []
                                 if isinstance(b, dict) and b.get("type") == "text"))
        if len(out) >= limit:
            break
    return "\n".join(out)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = None
    if not isinstance(payload, dict):
        return 0
    if payload.get("agent_id") or payload.get("agent_type"):
        return 0          # a worker's stop; it reports to its caller, not to the human

    cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or "."
    workflow = os.path.join(cwd, ".workflow")
    if not os.path.isdir(workflow) or not unattended(workflow):
        return 0

    sys.path.insert(0, os.path.join(cwd, ".claude", "scripts"))
    try:
        import turn_check
    except Exception:
        return 0

    try:
        import time

        import context_band as cb
        if cb.demand(workflow, project_dir=cwd, now=time.monotonic()).get("needs_handoff"):
            return 0      # the anchor outranks everything here; that gate is already blocking
    except Exception:
        pass

    latch = _latch(workflow)
    try:
        res = turn_check.check(workflow,
                               last_text=last_assistant_text(payload.get("transcript_path")),
                               prev_fingerprint=latch.get("fingerprint"),
                               satisfied_digest=latch.get("satisfied"))
    except Exception:
        return 0

    rec = {"fingerprint": res.get("fingerprint"), "satisfied": latch.get("satisfied"),
           "demands": latch.get("demands") or 0, "rung": latch.get("rung")}
    if not res["demand"]:
        rec.update(satisfied=res.get("digest") or latch.get("satisfied"), demands=0, rung=None)
        _write_latch(workflow, rec)
        return 0

    same_rung = latch.get("rung") == res["demand"]
    demands = (rec["demands"] + 1) if same_rung else 1
    rec.update(demands=demands, rung=res["demand"])
    _write_latch(workflow, rec)
    if demands > MAX_DEMANDS:
        print(json.dumps({"systemMessage": GAVE_UP % (MAX_DEMANDS, res["why"])}))
        return 0

    reason = res["instruction"]
    # Belt and braces, for `handoff_gate.py`'s reason: whichever mechanism the running harness
    # honours, it blocks once and reads the same text.
    print(json.dumps({
        "decision": "block",
        "reason": reason,
        "hookSpecificOutput": {"hookEventName": "Stop", "decision": "block", "reason": reason},
    }))
    print(reason, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
