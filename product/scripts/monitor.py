#!/usr/bin/env python3
"""Is the unattended drive still moving, and if not, who finds out? -- the drive heartbeat.

THE COMPLAINT: *"the workflow pauses a lot of no reason ... sometimes it says 'okay now doing X'
and never dispatches X ... it needs monitoring ... maybe we can monitor as well through the Tmux
that was planned? consider better fits for this as well."*

THE CONSIDERED ANSWER, since better fits were asked for: **tmux is the fallback, not the
mechanism.** The primary catch is `turn_check.py`'s ladder on the `Stop` hook — always on, needs
no second process, and fires at the exact instant the failure happens. What a `Stop` hook cannot
see is the session that **never ends a turn**: one that idles, or sits in a dialog — a
condition found by driving a real session into a permission prompt and watching it wait. Nothing about
those is decidable from inside the session, because nothing inside the session is running. So
this is a poller, and a poller is the right shape for exactly that residue and no more.

THE PULSE IS THE NEWEST WRITE THE LOOP MADE, which needs no new hook and no cooperation from the
session. A driving loop writes constantly — `state.json` at every iteration,
item artifacts as nodes complete, and a worker-budget breadcrumb on **every single tool
call**. So "the loop has written nothing for ten minutes" is not a heuristic about a model's
intentions; it is the observation that the machine has stopped touching its own state. It is an
ALLOW-LIST rather than all of `.workflow/` because this supervisor's own gate call writes there
too — see `PULSE_DIRS`. The alternative — reading the session transcript — needs the session id, which means a
hook recording it, which means a session that dies before recording it is invisible.

WAITING IS NOT STALLING, and conflating them is how a monitor becomes noise. A parked checkpoint,
an open dialog (`awaiting-input.json`) and the operator's pause latch all mean *a human owes an
answer*; the drive is stopped on purpose and nudging it would be shouting at a session that is
behaving correctly. Those states report `waiting` and take no action, ever.

A SESSION THAT IS NOT AT AN IDLE PROMPT IS THE FOURTH MEMBER OF THAT FAMILY, and it lives here
rather than in the transport. `supervise.sh` states its own law -- *"judgement lives in
`monitor.py`; this file is transport"* -- and the idle precondition was put in the transport as a
veto, so this file said `nudge`, the shell silently declined, and the BUDGET WAS SPENT ANYWAY:
observed 2026-09-20, `no motion - nothing written for 10m; NOT nudging: the session is not known
idle` against `monitor.json` recording `nudges: 1`. The one-nudge budget went on a nudge that
never left the process, and the next rung is a durable `steer` park -- a false stop for a session
that had never actually been nudged. The condition is the same family as the three above ("the
session is not in a state where a keystroke helps"), so it is judged here, where it is testable.

ITS ONE EXCEPTION IS THE STALL RUNG, and without it this file would go silent on the case it
exists for. A session that is not idle is normally a session that is WORKING -- and a working
loop writes constantly, so it never reaches the quiet window at all. Quiet for the full stall
window AND not at an idle prompt therefore means wedged (or an idle flag that was lost), and
neither is something a keystroke fixes. So the nudge is withheld and the escalation still fires:
the operator still finds out, through the away channel that already owns that route.

THE CHEAPEST SIGNAL IS NOT THE PULSE AT ALL -- IT IS THE TURN GATE SAYING SO. `turn_gate.py`
knows at the INSTANT of a stop that the turn owed a `continue`; this file used to spend
`QUIET_SECONDS` independently noticing silence to conclude the same thing. Measured cadence on a
real drive: work -> stop -> 10 minutes -> nudge -> work -> stop, `nudges_total: 4`, and the nudge
worked every single time. The nudge was never the problem; its PRICE was. So the gate leaves an
`owed` breadcrumb when it gives up, and that rung sits above the quiet ladder -- a ten-minute tax
collapses to the next 60-second poll, and the ladder below goes back to being what it is for: a
session that is DEAD, not one that merely stopped. Each breadcrumb is served once (`owed_at` is
its identity) and three served breadcrumbs that move no pulse escalate, so the shortcut cannot
become a keystroke loop.

TWO ESCALATIONS, IN ORDER, AND THE FIRST IS CHEAP. A quiet drive gets ONE nudge — a bare
`continue`, which is exactly what a session that quietly ended a turn needs and what a session
mid-work will simply queue behind its current turn. Only if it is still quiet after that does
this raise a `steer` checkpoint, because a checkpoint is what the daemon's away channel already
alerts on: the same argument `drive.py` makes for its own terminal stops — buy the notification
through the machinery that owns it rather than building a second sender beside it.

IT IS THE ONE OTHER PRODUCER OF EVIDENCE THE STEER FLOOR ACCEPTS. `bus.py`'s `steer_floor`
refuses a `steer` park that the goal's own verdict does not support, and *"the drive has stopped
moving"* is a claim `converge.py` cannot make -- a goal can be perfectly healthy and the session
still dead. So the floor accepts this file's record instead, and only while it is CURRENT: the
stall must name the fingerprint the loop is still sitting on. That is what keeps the escape from
becoming a bypass -- a session cannot talk its way through it, it can only be observed through it.

FAIL DIRECTION: do nothing, throughout — the same rule `supervise.sh` runs on. Every unreadable
file, absent git and unexpected shape reports `unknown` and takes no action. A monitor that fails
by staying quiet costs a stall nobody was told about, which is the status quo; one that fails by
acting drives keystrokes into a session that was working.

Usage:
    python3 monitor.py tick --workflow-dir .workflow [--project-root .] [--json]
    python3 monitor.py show --workflow-dir .workflow
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

RECORD = "monitor.json"
QUIET_SECONDS = int(os.environ.get("REEVE_MONITOR_QUIET") or 600)     # 10m -> one nudge
STALL_SECONDS = int(os.environ.get("REEVE_MONITOR_STALL") or 1800)    # 30m -> escalate
# WHAT COUNTS AS A PULSE, and it is an ALLOW-LIST for a reason a test found rather than a reason
# anyone reasoned to: `.workflow/` as a whole is NOT a pulse, because this supervisor's own gate
# call writes there. `context_band.py --gate` arms or disarms `handoff-gate.json` on every poll,
# so a monitor reading "newest mtime under .workflow/" would watch a dead session and see its own
# heartbeat reflected back at it, for ever. Every path below is one the LOOP writes while working
# and no observer writes: the published position, the item artifacts, the queues, and
# a worker-budget breadcrumb on every single tool call. The observers' own files —
# `context.json`, `handoff-gate.json`, `turn-gate.json`, `monitor.json`, `supervise.log` — are
# excluded by not being listed, which is why this is a list and not an exclusion set: a new
# observer added later is silently safe, a new loop artifact is silently missed, and of those two
# failures only the second is quiet rather than wrong.
PULSE_DIRS = ("items", "parked", "inbox", "outbox", "thread", "worker-budget", "maintenance")
PULSE_FILES = ("state.json", "handoff.md", "goal-ledger.jsonl", "backlog.md", "bus.json")
# PRESENCE IS THE FACT, and the body is only for humans -- the same reading `context_band.py`
# takes, and the name is kept in step with `context_band.IDLE_FILE` by hand, as the two hooks
# that write it already do. Reading the path directly rather than importing the band keeps this
# file's fail direction intact: a band that will not import must not be able to silence the
# monitor, and it cannot silence what it is not asked.
IDLE_FILE = "session-idle.json"
# The turn gate's give-up breadcrumb. The gate knows AT THE INSTANT OF THE STOP that the turn
# owed a `continue`; without reading it this file spends `QUIET_SECONDS` independently
# rediscovering the same fact, and the measured cadence on a real drive was work -> stop -> 10
# minutes -> nudge -> work -> stop, with `nudges_total: 4` and every nudge working. The tax was
# the ten minutes, not the nudge.
TURN_GATE = "turn-gate.json"
# Breadcrumbs served that moved nothing before this escalates. Three, because the keystroke's
# effect is DERIVED (a pulse that advances) and one unmoved poll can mean a turn that is still
# starting. A session that ignores three is not one more typing will reach.
OWED_MISSES = int(os.environ.get("REEVE_MONITOR_OWED_MISSES") or 3)


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            val = json.load(fh)
        return val if isinstance(val, dict) else {}
    except (OSError, ValueError):
        return {}


def _mtimes(path, depth=1):
    """Newest mtime at `path`, descending at most `depth` levels. Missing -> nothing."""
    out = []
    try:
        out.append(os.path.getmtime(path))
        for name in os.listdir(path) if os.path.isdir(path) else []:
            child = os.path.join(path, name)
            try:
                out.append(os.path.getmtime(child))
            except OSError:
                continue
            if depth > 0 and os.path.isdir(child):
                out.extend(_mtimes(child, depth - 1))
    except OSError:
        return out
    return out


def pulse(workflow):
    """The newest write the LOOP made, or None if it has never written anything readable."""
    stamps = []
    for rel in PULSE_DIRS:
        stamps.extend(_mtimes(os.path.join(workflow, rel), depth=1))
    for rel in PULSE_FILES:
        try:
            stamps.append(os.path.getmtime(os.path.join(workflow, rel)))
        except OSError:
            continue
    return max(stamps) if stamps else None


def waiting_on_a_human(workflow):
    """-> (kind, reason), or (None, None). A drive stopped ON PURPOSE has not stalled.

    The KIND is returned because the three are not equally absolute. A dialog and the operator's
    pause latch are unconditional -- there is a person in the middle of something either way. A
    parked checkpoint is not: a checkpoint parks the ITEM, and the loop is supposed to pick up
    the next independent one, so a park with the turn gate's give-up breadcrumb beside it is a
    session that stopped for nothing WHILE something was parked. That distinction is the turn
    ladder's to make and it has already made it; this file only has to not overrule it.
    """
    parked = os.path.join(workflow, "parked")
    try:
        if any(n.endswith(".json") for n in os.listdir(parked)):
            return "parked", "a checkpoint is parked"
    except OSError:
        pass
    if os.path.exists(os.path.join(workflow, "awaiting-input.json")):
        return "dialog", "a dialog is open in the session"
    if _read(os.path.join(workflow, "control.json")).get("paused"):
        return "paused", "the operator paused the loop"
    return None, None


def turn_owed(workflow):
    """-> (owed_at, why) from `turn-gate.json`'s give-up breadcrumb, or None.

    Written by `hooks/turn_gate.py` when it releases a turn that still owed something, and
    retired by the same hook the moment the gate is handling the stop in-session again or the
    loop ends a turn legitimately. Presence alone is not enough to act on -- `owed_at` is the
    identity of THIS give-up, so a breadcrumb already served is not served twice.
    """
    rec = _read(os.path.join(workflow, TURN_GATE))
    at = rec.get("owed_at")
    if not rec.get("owed") or not isinstance(at, (int, float)):
        return None
    return at, str(rec.get("owed_why") or rec.get("owed"))


def at_an_idle_prompt(workflow):
    """Is this session sitting at an idle prompt? -> bool.

    ABSENT READS AS NOT IDLE, which is the asymmetry `context_band.session_idle` explains at
    length: keys sent into a running turn do not queue into it, they land in the prompt box as
    literal text and are never submitted. A nudge withheld costs a poll; a nudge mistimed costs
    the conversation.
    """
    return os.path.exists(os.path.join(workflow, IDLE_FILE))


def _fingerprint(workflow):
    try:
        import drive
        return drive.fingerprint(workflow)
    except Exception:                              # noqa: BLE001 — no git, no judgement
        return None


def observe(workflow, now=None, quiet=QUIET_SECONDS, stall=STALL_SECONDS):
    """-> the verdict dict. Pure except for reading; the caller decides whether to act."""
    now = time.time() if now is None else now
    prev = _read(os.path.join(workflow, RECORD))
    fp = _fingerprint(workflow)
    beat = pulse(workflow)
    out = {"at": now, "fingerprint": fp, "pulse": beat,
           "nudges_total": int(prev.get("nudges_total") or 0),
           "escalations_total": int(prev.get("escalations_total") or 0),
           "quiet_periods": int(prev.get("quiet_periods") or 0),
           # Carried forward explicitly, because the record is rebuilt from scratch every tick
           # and a breadcrumb ledger that resets each poll would re-serve the same one for ever.
           "owed_served": prev.get("owed_served"), "owed_pulse": prev.get("owed_pulse"),
           "owed_misses": int(prev.get("owed_misses") or 0)}

    kind, reason = waiting_on_a_human(workflow)
    if kind in ("dialog", "paused"):
        out.update(state="waiting", action="none", why=reason, quiet_for=0, nudges=0)
        return out

    # THE BREADCRUMB RUNG, and it is above the quiet ladder because that is the whole point: the
    # turn gate established at the instant of the stop that this turn owed a `continue`, so
    # waiting `QUIET_SECONDS` to observe silence is rediscovering a known fact at a cost of ten
    # minutes. It outranks a parked checkpoint (the ladder already weighed that — a park stops
    # the ITEM) and never outranks a dialog or the operator's pause.
    owed = turn_owed(workflow)
    if owed and owed[0] != out["owed_served"]:
        at, why = owed
        if not at_an_idle_prompt(workflow):
            # The session is mid-turn: it stopped, and something started it again. Nothing to
            # do, and nothing to spend — the breadcrumb stays unserved and is retired by the
            # gate itself on the next legitimate end.
            out.update(state="waiting", action="none", quiet_for=0, nudges=0,
                       why="the turn gate says a `continue` is owed, but the session is not "
                           "known to be idle — it is already moving again")
            return out
        misses = out["owed_misses"] + 1 if (beat is not None and out["owed_pulse"] == beat) else 0
        if misses >= OWED_MISSES:
            out.update(state="stalled", action="escalate", quiet_for=0, nudges=0,
                       owed_served=at, owed_misses=misses,
                       escalations_total=out["escalations_total"] + 1,
                       why="%d nudges after the turn gate gave up moved nothing — %s" % (
                           misses, why))
            return out
        out.update(state="stopped", action="nudge", quiet_for=0, nudges=0,
                   owed_served=at, owed_pulse=beat, owed_misses=misses,
                   nudges_total=out["nudges_total"] + 1,
                   why="the turn gate gave up on a stop that owed `%s` — %s" % (
                       _read(os.path.join(workflow, TURN_GATE)).get("owed") or "continue", why))
        return out

    if kind:
        out.update(state="waiting", action="none", why=reason, quiet_for=0, nudges=0)
        return out
    if beat is None:
        out.update(state="unknown", action="none", why="nothing under .workflow/ is readable",
                   quiet_for=0, nudges=0)
        return out

    quiet_for = max(0.0, now - beat)
    # A NEW pulse resets the count, whatever the fingerprint says: a loop that is writing is a
    # loop that is alive, even mid-item where no anchor has landed yet. Tying this to the
    # fingerprint alone would call a long `execute` a stall and nudge a session that is working.
    nudges = int(prev.get("nudges") or 0) if quiet_for >= quiet else 0
    if quiet_for < quiet:
        out.update(state="moving", action="none", quiet_for=quiet_for, nudges=0,
                   why="written %ds ago" % int(quiet_for))
        return out
    if not at_an_idle_prompt(workflow):
        # Quiet AND not at the prompt. Below the stall window this is `waiting` and costs
        # nothing: the budget is not spent, so the nudge is still there to be spent the moment
        # the session is reachable. At the stall window it is the wedged case -- see the
        # docstring -- and the escalation is the only rung left that does not type into a
        # running turn.
        if quiet_for >= stall:
            out.update(state="stalled", action="escalate", quiet_for=quiet_for, nudges=nudges,
                       escalations_total=out["escalations_total"] + 1,
                       why=("nothing written for %dm and the session is not at an idle prompt — "
                            "a keystroke cannot reach it" % int(quiet_for // 60)))
            return out
        out.update(state="waiting", action="none", quiet_for=quiet_for, nudges=nudges,
                   why=("nothing written for %dm, but the session is not known to be idle — "
                        "keys sent into a running turn are never submitted"
                        % int(quiet_for // 60)))
        return out
    if nudges == 0:
        out.update(state="quiet", action="nudge", quiet_for=quiet_for, nudges=1,
                   quiet_periods=out["quiet_periods"] + 1,
                   nudges_total=out["nudges_total"] + 1,
                   why="nothing written under .workflow/ for %dm" % int(quiet_for // 60))
        return out
    if quiet_for >= stall:
        out.update(state="stalled", action="escalate", quiet_for=quiet_for, nudges=nudges,
                   escalations_total=out["escalations_total"] + 1,
                   why="still nothing written %dm after a nudge" % int(quiet_for // 60))
        return out
    out.update(state="quiet", action="none", quiet_for=quiet_for, nudges=nudges,
               why="nudged %ds ago; waiting for the stall window" % int(quiet_for))
    return out


def write_record(workflow, rec):
    path = os.path.join(workflow, RECORD)
    tmp = path + ".tmp-%d" % os.getpid()
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=1, sort_keys=True)
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def escalate(workflow, rec):
    """Raise the `steer` checkpoint, idempotently. -> a result dict, never raises.

    The record is written BEFORE this runs (see `tick`), and that ordering is load-bearing: the
    steer floor accepts a park whose stall is recorded and current, so a park attempted before
    its own evidence exists would be refused by the gate that is meant to let it through.
    """
    goal = _read(os.path.join(workflow, "goal.json")).get("id") or "goal"
    ticket = "steer-%s-not-moving" % goal
    try:
        from bus import Paths, write_park
        return write_park(Paths(workflow), {
            "ticket_id": ticket,
            "token": "%s:monitor" % ticket,
            "checkpoint": {"kind": "steer", "request": {
                "kind": "steer",
                "what": ("the drive has stopped moving and did not answer a nudge — it needs "
                         "direction, not a retry"),
                "expected": rec.get("why", ""),
                "blocking": True}},
            "loop_position": "monitor",
        }, summary=rec.get("why", "")[:120])
    except Exception as exc:                       # noqa: BLE001 — a monitor never crashes
        return {"error": "could not park the steer checkpoint: %r" % exc}


def tick(workflow, now=None):
    """Observe, record, and escalate if it has come to that. -> the verdict."""
    rec = observe(workflow, now)
    if rec.get("action") == "escalate":
        write_record(workflow, rec)                # evidence first — see `escalate`
        rec["parked"] = escalate(workflow, rec)
    write_record(workflow, rec)
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["tick", "show"])
    ap.add_argument("--workflow-dir", default=".workflow")
    ap.add_argument("--project-root", default=".", help="accepted for symmetry with the gate")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.workflow_dir):
        print("no %s here" % args.workflow_dir, file=sys.stderr)
        return 0                                   # not an initialised project: do nothing
    rec = tick(args.workflow_dir) if args.cmd == "tick" else _read(
        os.path.join(args.workflow_dir, RECORD))
    if args.json:
        print(json.dumps(rec, indent=2, sort_keys=True))
    else:
        print("%s — %s (action: %s)" % (rec.get("state", "unknown"), rec.get("why", ""),
                                        rec.get("action", "none")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
