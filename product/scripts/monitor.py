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
    """-> a reason, or None. A drive stopped ON PURPOSE is not a drive that has stalled."""
    parked = os.path.join(workflow, "parked")
    try:
        if any(n.endswith(".json") for n in os.listdir(parked)):
            return "a checkpoint is parked"
    except OSError:
        pass
    if os.path.exists(os.path.join(workflow, "awaiting-input.json")):
        return "a dialog is open in the session"
    if _read(os.path.join(workflow, "control.json")).get("paused"):
        return "the operator paused the loop"
    return None


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
           "quiet_periods": int(prev.get("quiet_periods") or 0)}

    reason = waiting_on_a_human(workflow)
    if reason:
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
