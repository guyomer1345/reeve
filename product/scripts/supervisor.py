#!/usr/bin/env python3
"""Is this project under supervision, and can it be armed right now? -- one owner for both.

THE COMPLAINT, in the maintainer's words: *"Currently the process of getting to a not-supervised
run is very vague; I need to run a few commands, make sure there isn't idle stuff, verify that
they work -- it isn't robust. I want one `supervise.sh`, I run it, I prompt Claude `continue`
once, and from there on we are inside a supervised run."*

WHAT IT REPLACED. Getting into a supervised run took `tmux new-session`, then
`loop.sh --supervise` (which refuses outside tmux), then `continue` -- and separately KNOWING to
check `pgrep -af supervise.sh` for duplicates or absences, `parked/` for a stale ticket,
`config.json` for a ceiling, and the log to confirm any of it took. **Every failure of that week
came from that list, not from the loop:** three supervisors on one pane and none on the other;
supervisors stopped for a deploy and never restarted (eleven hours lost); a false park nobody
could see without reading JSON.

TWO QUESTIONS, ONE OWNER, AND THE SECOND IS WHY THE FIRST IS ANSWERABLE.
  * `alive()` -- IS A SUPERVISOR RUNNING FOR THIS PROJECT? Nothing anywhere could say. The
    heartbeat that exists to catch a dead loop (`monitor.py`) runs INSIDE `supervise.sh`, so it
    is hosted by a process that can simply not be there -- and when it is not, the console, the
    status line, the loop and the turn gate were all silent. Now the supervisor PUBLISHES itself
    (the same argument `loop.sh` makes for the orchestrator lock: there is no ambient signal, so
    a live process must say so), and three consumers read this one answer.
  * `preflight()` -- MAY THIS PROJECT BE ARMED? The preconditions nothing owned. FATAL ones
    refuse, because handing back a half-armed state is the failure being fixed; everything else
    is reported, because the other half of that failure was invisibility rather than the fact.

WHY A PIDFILE HERE WHERE THE ORCHESTRATOR USES AN FLOCK. The orchestrator lock is held by the
process that becomes `claude`, so the kernel releases it on death and there is never a stale
lock. A supervisor is a bash poller: it cannot exec into the thing it supervises, and an flock
held by a shell loop tells a reader nothing about WHICH pane it is driving. So it is a record
with a liveness check -- and the check is what keeps it honest: the pid must still exist AND
still be a supervise.sh, or the record reads as `gone`, which is the answer that matters.

FAIL DIRECTION, and it differs by question. `alive()` never reports `running` on a guess: an
unreadable record, a pid it cannot probe, or a process it cannot identify all read as `unknown`
or `gone`, because the cost of a false `running` is an operator who stops checking. `preflight()`
fails FATAL only on facts it has measured; anything it merely could not read is a warning, or a
person is refused a run for the sake of a scratch file.

Usage:
    python3 supervisor.py status    [--workflow-dir .workflow] [--json]
    python3 supervisor.py preflight [--project .] [--pane <target>] [--json]
    python3 supervisor.py publish   --pid <n> --pane <target> [--workflow-dir .workflow]
    python3 supervisor.py retire    [--workflow-dir .workflow]
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

RECORD = "supervisor.json"


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            val = json.load(fh)
        return val if isinstance(val, dict) else {}
    except (OSError, ValueError):
        return {}


def _process_is_a_supervisor(pid):
    """-> True / False / None (cannot tell). Two questions, and the second is the point.

    `kill(pid, 0)` answers "does this pid exist", which pid reuse makes insufficient on its own:
    the shell that dies at 02:00 can be a compiler at 02:05. Where `/proc` is available the
    command line settles it. Where it is not (macOS), existence is all there is and the answer
    is still reported rather than guessed at -- see the caller.
    """
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass                              # alive and not ours -- existence is established
    except (OSError, OverflowError, TypeError, ValueError):
        return None
    try:
        with open("/proc/%d/cmdline" % pid, "rb") as fh:
            return b"supervise.sh" in fh.read()
    except OSError:
        return None                       # no /proc, or it vanished between the two reads


def alive(workflow_dir):
    """-> {state, pid, pane, since, why}. `state` ∈ running | gone | none | unknown.

    `none` and `gone` are deliberately different answers. Nothing was ever armed here, versus
    something was armed and is not there any more -- the second is the eleven-hour failure and
    the first is an ordinary interactive session.
    """
    rec = _read(os.path.join(workflow_dir, RECORD))
    out = {"state": "none", "pid": None, "pane": None, "since": None,
           "why": "no supervisor has been armed for this project"}
    if not rec:
        return out
    pid, pane = rec.get("pid"), rec.get("pane")
    out.update(pid=pid, pane=pane, since=rec.get("since"))
    if not isinstance(pid, int):
        out.update(state="unknown", why="the supervisor record names no usable pid")
        return out
    verdict = _process_is_a_supervisor(pid)
    if verdict is True:
        out.update(state="running", why="pid %d is supervising %s" % (pid, pane))
    elif verdict is False:
        out.update(state="gone", why="pid %d is not running — the supervisor for %s has "
                                     "stopped and nothing restarted it" % (pid, pane))
    else:
        out.update(state="unknown", why="pid %d could not be identified" % pid)
    return out


def publish(workflow_dir, pid, pane):
    """Called by `supervise.sh` at start. Best-effort: a supervisor that cannot write its own
    record still supervises, and the record is a surface, not a lock."""
    try:
        os.makedirs(workflow_dir, exist_ok=True)
        tmp = os.path.join(workflow_dir, "." + RECORD + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"pid": int(pid), "pane": pane, "since": time.time()}, fh, sort_keys=True)
        os.replace(tmp, os.path.join(workflow_dir, RECORD))
        return True
    except (OSError, TypeError, ValueError):
        return False


def retire(workflow_dir):
    """Called from `supervise.sh`'s exit trap. A record left behind by a supervisor that exited
    cleanly would read as `gone`, which is an alarm rather than a fact."""
    try:
        os.remove(os.path.join(workflow_dir, RECORD))
        return True
    except OSError:
        return False


# ------------------------------------------------------------------ the preflight

def _parked(workflow_dir):
    d = os.path.join(workflow_dir, "parked")
    try:
        return sorted(n[:-5] for n in os.listdir(d) if n.endswith(".json"))
    except OSError:
        return []


def _goal(workflow_dir):
    rec = _read(os.path.join(workflow_dir, "goal.json"))
    ident = rec.get("id")
    return ident if isinstance(ident, str) and ident.strip() else None


def _ceiling(project_root):
    cfg = _read(os.path.join(project_root, ".workflow", "config.json"))
    pct = (cfg.get("context") or {}).get("warn_pct")
    return pct if isinstance(pct, (int, float)) else None


def _trusted(project_root):
    try:
        import bus
        return bus.workspace_trusted(os.path.abspath(project_root))
    except Exception:                     # noqa: BLE001 — an undocumented platform file
        return None


def preflight(project_root, pane=None, workflow_dir=None):
    """-> {ready, fatal[], warn[], armed{}}. What is true BEFORE a supervisor is started.

    THE LINE BETWEEN fatal AND warn, because drawing it wrong makes this unusable in one
    direction and useless in the other. **Fatal is reserved for a state in which arming does
    not achieve what the operator asked for**: no project to supervise, or a supervisor already
    running (three on one pane is a measured failure, not a hypothetical). **Everything else is
    reported and started anyway** -- a missing goal is a real drive that simply has no
    stop-when-done yet (inception has not run, and refusing would make the first supervised run
    impossible), and a parked ticket is a legitimate state the operator must SEE rather than be
    blocked by, which is exactly what `4h` established for the loop itself.
    """
    project_root = project_root or "."
    wf = workflow_dir or os.path.join(project_root, ".workflow")
    out = {"ready": True, "fatal": [], "warn": [], "armed": {}}

    if not os.path.isdir(wf):
        out["fatal"].append("%s does not exist — this project has not been started (`/start`)"
                            % wf)
        out["ready"] = False
        return out

    sup = alive(wf)
    out["armed"]["supervisor"] = sup
    if sup["state"] == "running":
        out["fatal"].append(
            "a supervisor is ALREADY running for this project (%s). Two would send `/clear` "
            "into the same pane on their own schedules — stop it first (kill %s), or attach to "
            "the session it is driving." % (sup["why"], sup["pid"]))
        out["ready"] = False
    elif sup["state"] == "gone":
        out["warn"].append("the previous supervisor (%s) is gone; its record is being replaced"
                           % sup["pid"])
    elif sup["state"] == "unknown":
        out["warn"].append("a supervisor record exists and could not be checked: %s — look for "
                           "a stray `supervise.sh` before trusting this run" % sup["why"])

    goal = _goal(wf)
    out["armed"]["goal"] = goal
    if not goal:
        out["warn"].append(
            "NO GOAL is set, so this drive has no stop-when-done condition: `converge.py` can "
            "report neither met nor stalled, and the run ends only on an empty backlog or the "
            "no-progress guard. Legitimate before inception has run; wrong after it.")

    tickets = _parked(wf)
    out["armed"]["parked"] = tickets
    if tickets:
        out["warn"].append(
            "%d checkpoint(s) are already parked (%s). A parked ticket blocks every context "
            "reset for as long as it sits there — answer them, or delete a stale one, before "
            "leaving this run alone." % (len(tickets), ", ".join(tickets)))

    pct = _ceiling(project_root)
    out["armed"]["warn_pct"] = pct
    if pct is None:
        out["warn"].append("no operator ceiling is set (`config.context.warn_pct`); the context "
                           "BAND governs resets, measured in nodes of runway")

    trusted = _trusted(project_root)
    out["armed"]["trusted"] = trusted
    if trusted is False:
        out["warn"].append(
            "this workspace is NOT trusted, so `.claude/settings.json`'s allowlist is inert and "
            "ordinary local work will prompt — which is a halt with nobody there. Accept the "
            "trust dialog in an interactive session, or re-run `/start`.")

    if pane:
        out["armed"]["pane"] = pane
    return out


def render(res):
    """The armed report, as the operator reads it. One screen, and it says what it armed."""
    lines = []
    a = res.get("armed") or {}
    for msg in res.get("fatal") or []:
        lines.append("REFUSING: " + msg)
    if not res.get("ready"):
        lines.append("Nothing was armed. Fix the above and run this again.")
        return "\n".join(lines)
    for msg in res.get("warn") or []:
        lines.append("!  " + msg)
    lines.append("ARMED:")
    lines.append("   pane        %s" % (a.get("pane") or "(this one)"))
    lines.append("   goal        %s" % (a.get("goal") or "NONE"))
    lines.append("   parked      %s" % (", ".join(a.get("parked") or []) or "nothing"))
    lines.append("   ceiling     %s" % ("%s%%" % a["warn_pct"] if a.get("warn_pct") is not None
                                        else "none set — the band governs"))
    lines.append("   trusted     %s" % {True: "yes", False: "NO", None: "could not tell"}[
        a.get("trusted")])
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["status", "preflight", "publish", "retire"])
    ap.add_argument("--workflow-dir", default=None)
    ap.add_argument("--project", default=".")
    ap.add_argument("--pane", default=None)
    ap.add_argument("--pid", type=int, default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    wf = args.workflow_dir or os.path.join(args.project, ".workflow")

    if args.cmd == "publish":
        return 0 if publish(wf, args.pid, args.pane) else 1
    if args.cmd == "retire":
        retire(wf)
        return 0
    if args.cmd == "status":
        rec = alive(wf)
        print(json.dumps(rec, indent=2, sort_keys=True) if args.json else rec["why"])
        return 0 if rec["state"] == "running" else 1

    res = preflight(args.project, pane=args.pane, workflow_dir=args.workflow_dir)
    print(json.dumps(res, indent=2, sort_keys=True) if args.json else render(res))
    return 0 if res["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
