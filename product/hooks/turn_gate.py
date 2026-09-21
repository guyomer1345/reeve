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

THE GIVE-UP IS PER EPISODE, AND IT LEAVES A BREADCRUMB. Both halves were measured on a real
drive: `demands: 53` against `MAX_DEMANDS = 2` on a session whose every stop was illegitimate,
which means the gate had been standing down for fifty-one of them -- the counter only ever reset
on the may-end path, so a session that never ends legitimately never re-arms it. It now resets on
the give-up too, so the give-up releases THIS turn rather than the rest of the session. And
because the release hands a still-owing session back to nobody, it stamps `owed`/`owed_at` on the
latch: the fact that this turn owed a `continue` is known HERE, at the instant of the stop, and
`monitor.py` otherwise spends `QUIET_SECONDS` (ten minutes) independently rediscovering it. The
supervisor's next 60s poll reads the breadcrumb and sends the keystroke, and the monitor's own
ladder goes back to being what it is for: a session that is dead, not one that merely stopped.

FAIL DIRECTION IS OPEN on every path — unparseable payload, no `.workflow/`, an import that
raises, a torn latch. Same asymmetry `handoff_gate.py` argues: a session wrongly allowed to end
costs a turn; a session wrongly prevented from ending loses everything it was doing.
"""
import json
import os
import sys
import time

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


def workers_this_session(transcript):
    """-> how many subagents this session has run, or None if it cannot be told.

    The same place `worker_budget.py` locates a worker's own transcript:
    `<project>/<session-id>/subagents/agent-*.jsonl`, written by the harness beside the session
    transcript whose path arrives on the payload. `None` is CANNOT TELL and the rung it feeds
    stays silent on it -- an unreadable directory must never read as "no worker ran".
    """
    try:
        base = os.path.dirname(os.path.abspath(transcript))
    except (TypeError, ValueError):
        return None
    # THE SESSION TRANSCRIPT IS THE PROOF WE ARE LOOKING IN THE RIGHT PLACE, and that distinction
    # is the whole function. `subagents/` is created when a subagent first runs, so its ABSENCE
    # is the zero this rung needs -- not ignorance. Treating a missing directory as "cannot tell"
    # made the rung silent on precisely the runs it was built for: measured against the two real
    # trees where the breach happened, both answered "cannot tell" while the two healthy ones
    # answered 3. If the transcript itself is not there, we are somewhere else entirely and the
    # honest answer is None.
    if not os.path.isfile(transcript):
        return None
    d = os.path.join(base, os.path.splitext(os.path.basename(transcript))[0], "subagents")
    if not os.path.isdir(d):
        return 0
    try:
        return len([n for n in os.listdir(d)
                    if n.startswith("agent-") and n.endswith(".jsonl")])
    except OSError:
        return None


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
    transcript = payload.get("transcript_path")
    try:
        res = turn_check.check(workflow,
                               last_text=last_assistant_text(transcript),
                               prev_fingerprint=latch.get("fingerprint"),
                               satisfied_digest=latch.get("satisfied"),
                               prev_promoted=latch.get("promoted"),
                               workers_seen=workers_this_session(transcript))
    except Exception:
        return 0

    # `promoted` rides the latch for the same reason `fingerprint` does: "what is NEW since the
    # last stop" is not answerable from one observation. It is written on EVERY stop, including
    # the ones that block, so the dispatch rung fires once per item rather than on every turn
    # after it -- the breach has already happened and repeating it would only wedge the session.
    rec = {"fingerprint": res.get("fingerprint"), "satisfied": latch.get("satisfied"),
           "demands": latch.get("demands") or 0, "rung": latch.get("rung"),
           "promoted": res.get("promoted") or latch.get("promoted") or [],
           # Spent once and kept until the anchor is actually fixed -- see the give-up path.
           "anchor_demanded": bool(latch.get("anchor_demanded"))
                              and not res.get("anchor_ok", True)}
    if not res["demand"]:
        rec.update(satisfied=res.get("digest") or latch.get("satisfied"), demands=0, rung=None,
                   owed=None)
        _write_latch(workflow, rec)
        return 0

    same_rung = latch.get("rung") == res["demand"]
    demands = (rec["demands"] + 1) if same_rung else 1
    # The breadcrumb is retired the moment the gate is handling the stop in-session again: it
    # says "this turn ended owing something", and a turn that is being BLOCKED has not ended.
    rec.update(demands=demands, rung=res["demand"], owed=None)
    _write_latch(workflow, rec)
    if demands > MAX_DEMANDS:
        # GIVING UP IS THE MOMENT THE ANCHOR MATTERS MOST, and it was the one moment nothing
        # asked for it. The ladder returns its FIRST demand, so a turn owing rung 1 never hears
        # about rung 2 -- and here the session is about to end regardless, leaving a successor
        # with no `base_sha` to run `git log <base_sha>..HEAD` against. MEASURED: both modes of
        # one full run ended exactly this way and both wrote prose where the sha goes.
        # So the give-up converts to the anchor demand ONCE rather than releasing silently.
        #
        # ONE-SHOT, VIA ITS OWN LATCH FLAG, and the first version of this was wrong in a way
        # the wedge test caught: setting `rung = "anchor"` did not work, because the LADDER
        # still returns `continue` on the next stop (rung 1 is unsatisfied — that is why we are
        # here). The rung then alternates continue -> anchor -> continue, `same_rung` is never
        # true, the counter restarts every time and the session is blocked forever. A flag is
        # the honest record: this conversion has been spent, so the next give-up releases.
        # Cleared as soon as the anchor is good, so a later bad one can demand again.
        if not res.get("anchor_ok", True) and not latch.get("anchor_demanded"):
            rec.update(anchor_demanded=True)
            _write_latch(workflow, rec)
            reason = res["anchor_instruction"]
            print(json.dumps({
                "decision": "block",
                "reason": reason,
                "hookSpecificOutput": {"hookEventName": "Stop", "decision": "block",
                                       "reason": reason},
            }))
            print(reason, file=sys.stderr)
            return 2
        # THE BREADCRUMB, AND THE RE-ARM. The turn is about to end still owing something, with
        # nobody watching. Two consequences are recorded rather than one:
        #   · `owed` — this stop was illegitimate, established here by the full ladder. The
        #     supervisor's next poll sends the `continue`; without it `monitor.py` spends ten
        #     minutes noticing silence to conclude what was known at this instant. MEASURED on a
        #     real drive: work -> stop -> 10 min -> nudge -> work -> stop, four times over.
        #   · `demands = 0` — the give-up is for THIS turn, not for the session. Left at 3 it
        #     stands down for ever on a session whose stops are all illegitimate, which is
        #     exactly the session it exists for (`demands: 53`, zero blocks). Re-arming cannot
        #     wedge anything: every third stop still releases.
        rec.update(demands=0, rung=None, owed=res["demand"], owed_at=time.time(),
                   owed_why=(res.get("why") or "")[:200])
        _write_latch(workflow, rec)
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
