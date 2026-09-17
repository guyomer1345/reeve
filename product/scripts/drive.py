#!/usr/bin/env python3
"""Should the driver start another session? -- the session-hand-off decision, in one place.

`loop.sh --drive` is a shell loop around `claude -p`, and everything it must decide before
spawning session N+1 is decided here instead of in bash: whether the operator paused, whether
the goal is met or stalled, and whether the last session actually moved anything. A shell that
made those calls would be untestable exactly where being wrong is most expensive -- an
unattended driver that misreads a stop condition either spins all night or stops on the first
quiet session.

WHY THE DRIVER DECIDES RATHER THAN THE SESSION REPORTING. The obvious design has each session
write why it stopped and the driver obey. It was rejected: a session that crashed, was killed,
or ran out of context writes nothing, and a driver that needs a report cannot tell that apart
from a clean stop. Every predicate below is computed from **durable state the session does not
author for this purpose** -- the pause latch, the goal ledger, git, the item artifacts. A dead
session cannot lie about why it died, and it does not have to.

PROGRESS IS THE ANCHOR SET, NOT JUST HEAD. `git HEAD` alone is the tempting signal and it is
wrong in one direction that matters: an item bigger than a session makes no commit for several
sessions while genuinely advancing, and a HEAD-only driver would call that a stall and stop.
So progress reuses the rule the forecast anchor table already runs on -- *each node is resolved
through the durable effect it leaves behind* -- and fingerprints HEAD **plus** the per-item
anchors (`plan.md`, `changelog.md`, `verify-verdict.md`, `debug-report.md`, `plan-delta.md`,
`promoted.json`). A session that planned an item and ran out of context has moved the
fingerprint; a session that burned a window and left nothing has not. **Deliberately NOT
content-hashed:** presence is what the anchor table proves, and hashing bodies would make an
edited draft read as progress.

WHAT THE DRIVER IS NOT ALLOWED TO DECIDE. It never picks work, never routes, never touches an
item. It answers one question -- spawn or stop -- and every stop it can return is one a human
would recognise as a reason to be told about it.

FAIL DIRECTION. A predicate that cannot be computed **stops the driver**, and this is the
opposite of `converge.py`'s permissive-reporting stance for a reason: this one spawns
processes. An unreadable pause latch, a goal file that will not parse, a git that will not
answer -- every one of them stops, because the failure mode of continuing is an unattended
machine doing work nobody can account for, and the failure mode of stopping is a human typing
the command again.
"""
import argparse
import hashlib
import json
import os
import shlex
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# The per-item artifacts that PROVE a node ran -- the forecast anchor table's set. Kept in
# step with it by hand and deliberately: a drifting copy here makes the driver blind to a node,
# never noisy about one, so the failure is silent and this comment is the tripwire.
TICKET_SAFE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

ITEM_ANCHORS = ("plan.md", "changelog.md", "verify-verdict.md", "debug-report.md",
                "plan-delta.md", "promoted.json")

# Consecutive sessions that moved no anchor before the driver gives up. The same shape and the
# same number as the relaunch-runner's RUNNER_MAX_ATTEMPTS, lifted from the relaunch to the
# session -- one mechanism that gives up, not two that disagree about when.
MAX_NOPROGRESS = 5


def _git_head(repo):
    try:
        p = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                           capture_output=True, text=True)
    except OSError:
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def fingerprint(workflow_dir):
    """A short digest of everything that would have moved if a node ran. None ⇒ cannot tell,
    which callers must treat as a stop rather than as 'unchanged'."""
    repo = os.path.dirname(os.path.abspath(workflow_dir)) or "."
    head = _git_head(repo)
    if head is None:
        return None
    marks = [head]
    items = os.path.join(workflow_dir, "items")
    try:
        names = sorted(os.listdir(items))
    except OSError:
        names = []
    for name in names:
        for anchor in ITEM_ANCHORS:
            if os.path.exists(os.path.join(items, name, anchor)):
                marks.append("%s/%s" % (name, anchor))
    return hashlib.sha256("\n".join(marks).encode("utf-8")).hexdigest()[:16]


def _goal_id(workflow_dir):
    """The active goal's id, for keying a steer ticket. Unreadable ⇒ a stable placeholder,
    because a park that cannot be named is worse than one named generically."""
    try:
        with open(os.path.join(workflow_dir, "goal.json"), encoding="utf-8") as fh:
            val = json.load(fh)
        gid = (val or {}).get("id")
        return gid if isinstance(gid, str) and TICKET_SAFE.match(gid) else "goal"
    except (OSError, ValueError, AttributeError):
        return "goal"


def _converge(workflow_dir, cmd):
    """(exit_code, ok). `ok` False ⇒ the module could not be run at all."""
    try:
        p = subprocess.run([sys.executable, os.path.join(HERE, "converge.py"),
                            "--workflow-dir", workflow_dir, cmd],
                           capture_output=True, text=True)
    except OSError:
        return None, False
    return p.returncode, True


def decide(workflow_dir, prev_fp, streak, max_noprogress=MAX_NOPROGRESS):
    """The whole verdict. Order matters: an operator's pause outranks everything, then the
    goal's own terminal states, then the driver's own give-up guard."""
    try:
        import drain
        from bus import Paths
        paths = Paths(workflow_dir)
        control = drain.read_control(paths)
    except Exception as exc:                      # noqa: BLE001 - any failure stops
        return {"cont": False, "reason": "cannot read the pause latch (%s) — stopping rather "
                                         "than spawning blind" % exc, "fingerprint": prev_fp,
                "streak": streak}

    if control.get("paused"):
        return {"cont": False, "reason": "PAUSED by %s at %s — resume with a `control` message"
                                         % (control.get("by", "?"), control.get("at", "?")),
                "fingerprint": prev_fp, "streak": streak}

    fp = fingerprint(workflow_dir)
    if fp is None:
        return {"cont": False, "reason": "cannot fingerprint progress (no git?) — stopping",
                "fingerprint": prev_fp, "streak": streak}

    # A goal is optional; with none, the driver still drives (item-at-a-time) and only the
    # no-progress guard can stop it. That is a real mode, but it is indistinguishable from the
    # measured failure -- inception skipping the node that mints the goal -- so every verdict
    # SAYS which of the two the driver is in rather than leaving the quieter one to be assumed.
    goal = os.path.exists(os.path.join(workflow_dir, "goal.json"))
    goalless = "" if goal else (" [no goal.json — this drive has no stop-when-done; it stops "
                                "only on an empty backlog or the no-progress guard]")
    if goal:
        rc, ok = _converge(workflow_dir, "met")
        if not ok:
            return {"cont": False, "reason": "cannot run converge.py — stopping",
                    "fingerprint": fp, "streak": streak}
        if rc == 0:
            return {"cont": False, "reason": "GOAL MET — capture, notify, and stop for "
                                             "re-steering", "fingerprint": fp, "streak": streak,
                    "met": True, "goal": _goal_id(workflow_dir)}
        rc, ok = _converge(workflow_dir, "check")
        if ok and rc == 2:
            return {"cont": False, "reason": "GOAL STALLED — read back what was attempted and "
                                             "why it did not move; never retry the same item",
                    "fingerprint": fp, "streak": streak, "stalled": True,
                    "goal": _goal_id(workflow_dir)}

    # Progress is measured against the PREVIOUS fingerprint, so the first tick (no previous)
    # never scores no-progress -- there has been no session to have made any.
    if prev_fp is None:
        return {"cont": True, "reason": "first session" + goalless, "fingerprint": fp,
                "streak": 0, "goalless": not goal}
    if fp == prev_fp:
        streak += 1
        if streak >= max_noprogress:
            return {"cont": False, "streak": streak, "fingerprint": fp, "goalless": not goal,
                    "reason": "NO PROGRESS in %d consecutive sessions — stopping rather than "
                              "burning windows; a human must look" % streak + goalless}
        return {"cont": True, "streak": streak, "fingerprint": fp, "goalless": not goal,
                "reason": "no progress (%d/%d)" % (streak, max_noprogress) + goalless}
    return {"cont": True, "streak": 0, "fingerprint": fp, "goalless": not goal,
            "reason": "progress" + goalless}


def park_steer(workflow_dir, verdict):
    """Park a `steer` checkpoint for a terminal stop, so the stop is REACHABLE.

    An unattended drive that just goes quiet is indistinguishable from one that died. A
    parked checkpoint is what the daemon's away channel already alerts on, so raising one
    buys the notification through the machinery that owns it -- rather than a second sender
    beside it, which would mean a second copy of the delivery-and-backoff logic and a second
    way for the channel to be wrong.

    IDEMPOTENT BY CONSTRUCTION. The ticket id and token are DERIVED from (goal, reason), so a
    driver restarted against the same terminal state rewrites the same record rather than
    filing a second ask. A stalled goal that a human has not yet answered must not accumulate
    one ticket per driver launch -- that is how an away channel trains someone to ignore it.

    Best-effort, and deliberately so: the driver's job is to STOP, and it has already decided
    to. A park that fails must not turn a clean stop into a crash, so the failure is reported
    and the stop proceeds. The console still shows the goal's state either way.
    """
    kind = "met" if verdict.get("met") else "stalled"
    goal_id = verdict.get("goal") or "goal"
    ticket = "steer-%s-%s" % (goal_id, kind)
    digest = hashlib.sha256(ticket.encode("utf-8")).hexdigest()[:8]
    rec = {
        "ticket_id": ticket,
        "token": "%s:steer:%s" % (ticket, digest),
        "checkpoint": {
            "kind": "steer",
            "request": {
                "kind": "steer",
                "what": ("the goal is met — confirm it is finished, or say what is still missing"
                         if kind == "met" else
                         "the drive stopped moving — it needs direction, not a retry"),
                "expected": verdict.get("reason", ""),
                "blocking": True,
            },
        },
        "loop_position": "converge",
    }
    try:
        from bus import Paths, write_park
        return write_park(Paths(workflow_dir), rec, summary=verdict.get("reason", "")[:120])
    except Exception as exc:                       # noqa: BLE001 -- never crash a clean stop
        return {"error": "could not park the steer checkpoint: %r" % exc}


def _shell(verdict):
    """KEY=VALUE lines for `eval` in the driver. Shell parsing JSON is how a driver acquires a
    dependency on `jq` and a new way to be wrong at 3am.

    QUOTED WITH shlex.quote, NOT json.dumps, and the difference is not cosmetic. These reasons
    are written for humans and contain backticks -- "resume with a `control` message" -- which
    inside double quotes are COMMAND SUBSTITUTION. JSON-quoting produced a line that `eval` ran
    as a command; the exit test caught it as `control: command not found`. Single-quote shell
    escaping is closed under backticks, `$`, and everything else a reason might ever say, so the
    safety comes from the quoting rather than from nobody writing an awkward sentence.
    """
    return "\n".join([
        "DRIVE_CONTINUE=%d" % (1 if verdict["cont"] else 0),
        "DRIVE_FINGERPRINT=%s" % shlex.quote(verdict.get("fingerprint") or ""),
        "DRIVE_STREAK=%d" % verdict.get("streak", 0),
        "DRIVE_REASON=%s" % shlex.quote(verdict.get("reason", "")),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Should the session driver spawn again?")
    ap.add_argument("--workflow-dir", default=".workflow")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fingerprint", help="the current progress fingerprint")
    t = sub.add_parser("tick", help="the spawn/stop verdict (exit 0 = spawn, 1 = stop)")
    t.add_argument("--prev-fingerprint", default="")
    t.add_argument("--streak", type=int, default=0)
    t.add_argument("--shell", action="store_true", help="KEY=VALUE for `eval`")
    args = ap.parse_args(argv)

    if args.cmd == "fingerprint":
        fp = fingerprint(args.workflow_dir)
        print(fp or "")
        return 0 if fp else 1

    v = decide(args.workflow_dir, args.prev_fingerprint or None, args.streak)
    # A TERMINAL stop (the goal is met, or it stalled) gets a `steer` checkpoint so the stop
    # is reachable from a phone. A pause does NOT: the human who paused already knows, and
    # asking them to answer a checkpoint about their own instruction is noise. Nor does a
    # no-progress give-up, which is the driver's own guard rather than a verdict about the
    # goal -- it may fire on a goal that is perfectly healthy and simply blocked.
    if not v["cont"] and (v.get("met") or v.get("stalled")):
        v["parked"] = park_steer(args.workflow_dir, v)
    print(_shell(v) if args.shell else json.dumps(v, indent=2, sort_keys=True))
    if not args.shell:
        print("drive: " + v["reason"], file=sys.stderr)
    return 0 if v["cont"] else 1


if __name__ == "__main__":
    sys.exit(main())
