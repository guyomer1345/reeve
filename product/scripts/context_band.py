#!/usr/bin/env python3
"""When should this session hand off? -- a two-sided band, in units of WORK.

The old rule was one-sided: `pct >= config.context.warn_pct` printed "run /dispatch then
/clear". It had a ceiling and no floor, so nothing ever said *you still have runway, do not
hand off yet* -- and under-use is not free. A token in a worker's context is re-read many times
over a session, so a hand-off is paid for whether or not you use the window; handing off early
buys back a cold rebuild (re-read the handoff, re-orient) in exchange for a window that still
had work in it.

WHY A PERCENTAGE IS THE WRONG UNIT, which is the substance rather than a second threshold. A
fraction makes a 200k window and a 1M window warn at the same *fraction full* while leaving them
5 and 25 nodes of runway -- the same signal for wildly different situations. What a session
actually needs is enough remaining context to **finish what it is holding and write a complete
handoff**, which is a work budget:

    runway = (window - used) / per_node_cost        # in NODES, not percent

`per_node_cost` is measured, not guessed: the median inline node adds ~12k tokens. So the band
is stated in nodes and both edges fall out of one quantity, rather than two percentages that
need re-measuring separately and drift apart.

    runway < RESERVE      HAND OFF NOW. What is left is needed to finish the item in hand and
                          publish a complete anchor. Past here a session risks stopping without
                          one, which is the only failure that loses the loop's place.
    runway > COMFORTABLE  HOLD. Handing off here wastes a window that is paid for.
    between               HAND OFF AT THE NEXT CLEAN BOUNDARY -- between items, never mid-item.

THE SENSOR AND THE ACTUATOR ARE ON OPPOSITE SIDES OF A WALL, and this module exists because of
it. The statusline is the ONLY surface Claude Code exposes a token count to -- hooks and the
model receive none. So the statusline can SEE and not act, while the loop can ACT and not see.
Nothing crossed that wall: the statusline printed a banner and a human typed `/dispatch`. The
crossing is `statusline.py` PUBLISHING its reading to `context.json`; this module is the
arithmetic over it, and everything that wants the verdict reads one place.

WHAT THIS IS NOT. It is not an enforcement and cannot be one -- nothing can stop a session
spending its window, and the signal arrives in the statusline and in a file, not in the model's
context. It is a governor a session and a driver can consult, and calling it
a cap would be an overstatement of exactly the kind that makes a soft signal get trusted as a
hard one.

FAIL DIRECTION. An unreadable or stale reading yields `unknown`, never `hold`. A wrong `hold`
tells a session to keep filling a window it should be leaving, and the cost of that is a
session that stops with no anchor written.

THE GATE — the half that ACTS, added because the band above was read by nobody. For its first
life this module was a better banner and nothing more: `grep context_band` over the loop's own
routing docs returned nothing, so a two-sided, measured, well-argued verdict was printed at a
human and then dropped. The sensor shipped and the actuator did not, which is a failure this
package has now made four times over.

The gate answers two questions that were previously conflated into one, and separating them is
the substance:

    needs_handoff   The band says `handoff-now` and no USABLE anchor has been written since it
                    began saying so. Writing an anchor is ALWAYS safe, so this is deliberately
                    not gated on anything else -- not on whether a checkpoint is open, not on
                    whether the runtime half is reachable. Its consumer is `hooks/handoff_gate.py`,
                    a `Stop` hook, which BLOCKS the turn from ending until the anchor exists.
                    That is the actuator: a session cannot spend its reserve and then quietly
                    stop with nothing to resume from.
                    "Usable" is TWO conditions and the second was found the same way the
                    dialog was -- by a real drive, not by reasoning. The file must have moved
                    since the latch armed, AND it must NAME A BASE COMMIT: a resume reads
                    `git log <base_sha>..HEAD`, so an anchor without one leaves the resumed
                    session unable to see what moved while its predecessor was alive. A drive
                    that went all the way round wrote exactly that. `anchor_fresh`
                    and `anchor_names_base` are reported separately, because "nothing was
                    written" and "something was, and it cannot be resumed from" are different
                    things to go and fix.
    clear_safe      The band says `handoff-now`, the anchor IS written, nothing is waiting on a
                    human, and THE SESSION IS IDLE. Its consumer is the supervisor, whose whole
                    job is the reset (`/clear` then `continue`) and which must never reset a
                    session that a person is mid-conversation with -- nor one the MODEL is
                    mid-turn in. "Waiting on a human" is TWO things and the second was found by
                    probing, not by reasoning: a parked checkpoint, and an OPEN DIALOG (a
                    permission prompt, an elicitation). A live probe drove a real session into a
                    permission prompt and it sat there -- invisible to `parked/`, and a
                    supervisor reading the two-part gate would have cleared the screen somebody
                    was looking at.
                      The FOURTH condition -- idle -- was found the same way the second was, by
                    a drive rather than by reading, and it is the one the other three were
                    silently wrong about. `handoff.md` is written DURING a turn, so the instant
                    the session writes its anchor the first three all hold while the model is
                    still working. Every reset fired mid-turn. The design assumed keys sent then
                    would queue in the pty and be read intact at the end of the turn; they do
                    not. They land in the prompt box as literal TEXT, never submitted, and the
                    next poll adds more -- `/clear continue /clear continue` stacked until a
                    human pressed Esc, which flushed the buffer and ran the `/clear` with no
                    `continue` behind it (OBSERVED 2026-09-19). So idle is a PRECONDITION, not a
                    courtesy, and it is the only one of the four stated in the positive:
                    `session_idle` must be non-null, and absent reads as "not idle".

FRESHNESS NEEDS A MOMENT TO BE FRESH RELATIVE TO, and that moment is when the band ENTERED
`handoff-now` -- not "recently", not a TTL. So `gate()`/`demand()` latch it: the first call that
sees `handoff-now` records the anchor's mtime as it was at that instant
(`.workflow/handoff-gate.json`), and the anchor counts as written once its mtime moves past it.
Leaving `handoff-now` -- which in practice means the session was cleared -- disarms the latch, so
the demand is made once per fill cycle rather than nagging every turn afterwards.
"""
import argparse
import json
import re
import time
import os
import sys

# The measured median cost of one inline node, in tokens. A NUMBER SET TO A MEASUREMENT, which
# is this package's rule for numbers -- not an instinct about how big a step feels.
PER_NODE_TOKENS = 12000

# Nodes of runway that must remain for a session to finish what it holds and publish a complete
# handoff. Two, deliberately: one for the step in hand and one for the anchor itself, which is
# the piece that must never be the thing that gets squeezed out.
RESERVE_NODES = 2

# Above this, handing off is throwing away a paid-for window. Five nodes is roughly a whole
# item's worth of work -- the point at which "I could still finish something here" stops being
# wishful.
COMFORTABLE_NODES = 5

STALE_SECONDS = 900          # a reading older than this describes a session that is likely gone
                             # -- UNLESS it is known idle, which is evidence of the opposite; see
                             # `read_reading`.

# The latch that gives "freshly written" a moment to be fresh relative to. Beside `context.json`
# on the repo mount deliberately: the `Stop` hook reads it every turn and must not have to
# resolve the runtime root to do so (a project whose runtime half has gone missing still needs
# its anchor written -- that is exactly when it needs it most).
GATE_FILE = "handoff-gate.json"

# Written by `hooks/awaiting_input.py` when Claude Code raises a dialog a person must answer,
# removed by `hooks/handoff_gate.py` when a turn ends (a dialog blocks the turn, so a `Stop` is
# proof the dialog is gone). Present ⇒ somebody is being waited on, and no reset may happen.
AWAITING_FILE = "awaiting-input.json"

# The session is sitting at an idle prompt — the FOURTH thing that must be true before a reset
# may be sent, and the only one stated in the positive. TWO writers and one remover:
# `awaiting_input.py` writes it on the harness's own `idle_prompt` notification, and
# `session_start.py` writes it at a start / resume / clear, which the harness cannot announce
# because its idle timer never arms in a session with no messages. `prompt_submit.py` removes it
# the instant a prompt is submitted, so they bracket idleness exactly rather than guessing at it.
IDLE_FILE = "session-idle.json"

# Dispatched workers that have not come back. One file per `tool_use_id`, written by
# `hooks/dispatch_guard.py` (PreToolUse on Agent|Task) and removed by `hooks/dispatch_return.py`
# (PostToolUse on the same) -- both hooks already existed and were already wired, so start and end
# were observable all along and nothing read them.
IN_FLIGHT_DIR = "in-flight"

# How long an entry may sit before it is presumed dead. This is a BACKSTOP, not a timeout: the
# ordinary end of an entry is its PostToolUse, and a session that dies mid-dispatch has its whole
# directory cleared at the next `SessionStart`. What is left is the one case neither covers -- a
# worker that vanishes without its PostToolUse inside a session that keeps running -- and an entry
# that never ages out there would stop the supervisor resetting, forever. An hour is roughly four
# times the longest dispatch observed on a real drive (16m02s, `reeve:planner`), so it cannot fire
# on a working worker; it is not a guess about how long work takes.
IN_FLIGHT_STALE_SECONDS = 3600


# WHAT MAKES AN ANCHOR AN ANCHOR, and why mtime alone was not enough. A resume reads
# `git log <base_sha>..HEAD` to see what moved while the session that wrote the anchor was
# alive; an anchor naming no base commit cannot answer that, so the resumed session is left
# guessing at exactly the thing it was cleared to be told. `/dispatch` has always NAMED the
# field and nothing has ever checked it -- and a real drive duly went all the way round
# (planned, executed, verified, documented, committed) and wrote one without it.
# This is load-bearing twice over now that `12h`'s supervisor clears sessions ON PURPOSE.
#
# Permissive on spelling, strict on substance: any `base_sha` label followed by a hex commit
# id. `base_sha: none` / `unknown` / an empty value all fail, correctly -- they are the shapes
# a session writes when it did not look.
BASE_SHA_RE = re.compile(r"(?i)base[_\s-]?sha\W{0,6}\b([0-9a-f]{7,40})\b")


def anchor_names_base(path):
    """Does the anchor at `path` name a base commit? -- the content half of "written".

    WHAT THIS CANNOT PROVE, stated here rather than left to be discovered: that the sha is
    REAL, or that it is current. Resolving it needs git, and `demand()` is deliberately
    answerable from the repo mount with no subprocess -- so this checks the SHAPE. A shape
    check catches the failure that actually happened (no field at all) and not a fabricated
    id. Currency is not checked because it is not wanted: an anchor names the commit it was
    written at, and a resume reading further back than necessary loses nothing.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return BASE_SHA_RE.search(fh.read()) is not None
    except OSError:
        return False


def band(used_tokens, window_tokens, warn_pct=None):
    """The verdict, as a dict. Unknown inputs yield `unknown` rather than a guess.

    `warn_pct` is an EXPLICIT OPERATOR CEILING and outranks the runway calculation when it
    fires. Not a hedge: a human who sets `config.context.warn_pct` is saying *warn me at this
    fraction, whatever the arithmetic thinks*, and a governor that silently ignored a standing
    operator instruction would reproduce the exact failure the directive channel exists to
    stop. The band is the DEFAULT; it is not an override of the human."""
    if not isinstance(window_tokens, (int, float)) or window_tokens <= 0:
        return {"verdict": "unknown", "reason": "no context-window size in the reading"}
    if not isinstance(used_tokens, (int, float)) or used_tokens < 0:
        return {"verdict": "unknown", "reason": "no token count in the reading"}

    remaining = max(0.0, float(window_tokens) - float(used_tokens))
    runway = remaining / PER_NODE_TOKENS
    pct = 100.0 * float(used_tokens) / float(window_tokens)
    out = {"used": int(used_tokens), "window": int(window_tokens), "pct": round(pct, 1),
           "runway_nodes": round(runway, 1), "reserve": RESERVE_NODES,
           "comfortable": COMFORTABLE_NODES}

    if isinstance(warn_pct, (int, float)) and 0 < warn_pct <= 100 and pct >= warn_pct:
        out["verdict"] = "handoff-now"
        out["operator_ceiling"] = warn_pct
        out["reason"] = ("context %d%% is at or past the ceiling you set (config.context."
                         "warn_pct = %g%%) — run /dispatch, then /clear. %.1f nodes of runway "
                         "remain, so this is your instruction rather than the arithmetic's."
                         % (round(pct), warn_pct, runway))
    elif runway < RESERVE_NODES:
        out["verdict"] = "handoff-now"
        out["reason"] = ("%.1f nodes of runway left — below the %d-node reserve needed to finish "
                         "this item and write a complete handoff. Run /dispatch, then /clear."
                         % (runway, RESERVE_NODES))
    elif runway > COMFORTABLE_NODES:
        out["verdict"] = "hold"
        out["reason"] = ("%.1f nodes of runway — keep working. Handing off here pays a cold "
                         "rebuild for a window that still has work in it." % runway)
    else:
        out["verdict"] = "handoff-at-boundary"
        out["reason"] = ("%.1f nodes of runway — hand off at the next clean boundary (between "
                         "items, never mid-item), not immediately and not much later." % runway)
    return out


def read_reading(workflow_dir, now=None):
    """The last reading `statusline.py` published, or None. A reading older than STALE_SECONDS
    is None too: it describes a session that has probably already ended, and a verdict about a
    dead session's window is worse than no verdict.

    AN IDLE SESSION IS NOT A GONE SESSION, and the staleness rule could not tell them apart.
    The statusline publishes once per turn, so a session that has been sitting at the prompt for
    fifteen minutes has no fresh reading, the band returns `unknown`, and `clear_safe` blocks on
    *"the band says unknown, not handoff-now"* -- a condition it can never satisfy, because the
    thing that would refresh the reading is the turn the reset exists to make possible. Harmless
    where it was first seen (`consumer` at 17% after ~40 idle minutes, no reset wanted) and
    exactly backwards in the case that matters: **a session that stops at 95% and sits for a
    quarter of an hour can no longer be reset by the supervisor at all.** `session-idle.json` is
    the evidence that distinguishes the two, and it is already the gate's fourth condition.

    THE RISK THIS ACCEPTS, stated rather than hidden: a session that DIED leaves its idle flag
    behind (the next `SessionStart` is what rewrites it), so its last reading is honoured
    indefinitely and the supervisor may type into a pane whose session is gone. That costs
    keystrokes a dead pane ignores, capped by `supervise.sh`'s `MAX_RESETS` -- which is exactly
    the case that cap was built for: sends that change nothing.
    """
    path = os.path.join(workflow_dir, "context.json")
    try:
        with open(path, encoding="utf-8") as fh:
            val = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(val, dict):
        return None
    if now is not None and isinstance(val.get("mono"), (int, float)):
        if now - val["mono"] > STALE_SECONDS and session_idle(workflow_dir) is None:
            return None
    return val


def publish(workflow_dir, used_tokens, window_tokens, mono):
    """Cross the wall: record what only the statusline can see, where anything can read it.

    Best-effort and never raising -- this runs inside the status line, and a status line that
    crashes blanks itself. A lost reading degrades to `unknown`, which is the safe direction.
    """
    try:
        os.makedirs(workflow_dir, exist_ok=True)
        tmp = os.path.join(workflow_dir, ".context.json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"used": used_tokens, "window": window_tokens, "mono": mono},
                      fh, sort_keys=True)
        os.replace(tmp, os.path.join(workflow_dir, "context.json"))
        return True
    except OSError:
        return False


def warn_pct_configured(project_dir):
    """`config.context.warn_pct` as the operator SET it, or None when they did not.

    Lives here rather than in the status line because it is an input to the BAND, and the band
    now has two readers -- the status line and the gate below. An explicitly set percentage is a
    standing instruction that outranks the arithmetic; an ABSENT one must not be silently
    materialised into a ceiling nobody asked for, which would make the band unreachable (a 30%
    default fires long before runway ever runs low).
    """
    try:
        with open(os.path.join(project_dir, ".workflow", "config.json"), encoding="utf-8") as fh:
            cfg = json.load(fh)
        pct = (cfg.get("context") or {}).get("warn_pct")
        if isinstance(pct, (int, float)) and 0 < pct <= 100:
            return float(pct)
    except Exception:
        pass
    return None


def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def _read_latch(workflow_dir):
    try:
        with open(os.path.join(workflow_dir, GATE_FILE), encoding="utf-8") as fh:
            val = json.load(fh)
    except (OSError, ValueError):
        return None
    return val if isinstance(val, dict) else None


def _write_latch(workflow_dir, latch):
    """Best-effort and never raising -- every caller runs inside a hook or a status line."""
    try:
        os.makedirs(workflow_dir, exist_ok=True)
        tmp = os.path.join(workflow_dir, "." + GATE_FILE + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(latch, fh, sort_keys=True)
        os.replace(tmp, os.path.join(workflow_dir, GATE_FILE))
        return True
    except OSError:
        return False


def _clear_latch(workflow_dir):
    try:
        os.remove(os.path.join(workflow_dir, GATE_FILE))
    except OSError:
        pass


def record_demand(workflow_dir):
    """Count one demand made. The `Stop` hook's loop-stop: after MAX_DEMANDS it gives up and
    lets the turn end, because a hook that blocks forever wedges the session it was protecting.
    Separate from the latch's arming so that merely ASKING the gate never inflates the count."""
    latch = _read_latch(workflow_dir) or {}
    latch["demands"] = int(latch.get("demands") or 0) + 1
    _write_latch(workflow_dir, latch)
    return latch["demands"]


def demand(workflow_dir, project_dir=None, now=None, arm=True):
    """Does this session owe an anchor right now? -- the half with no dependencies.

    Deliberately answerable from the repo mount alone: no runtime root, no `bus.py`, no
    subprocess. Writing a handoff is always safe, so nothing here may veto it.
    """
    if project_dir is None:
        project_dir = os.path.dirname(os.path.abspath(workflow_dir)) or "."
    reading = read_reading(workflow_dir, now=now)
    if reading:
        out = dict(band(reading.get("used"), reading.get("window"),
                        warn_pct_configured(project_dir)))
    else:
        out = {"verdict": "unknown",
               "reason": "no recent context reading — the statusline publishes it, so this is "
                         "either a session with no statusline configured or one that has not "
                         "rendered yet"}

    handoff = os.path.join(workflow_dir, "handoff.md")
    latch = _read_latch(workflow_dir)

    if out["verdict"] != "handoff-now":
        # Disarm. In practice this is the post-`/clear` turn: the window emptied, so the demand
        # is discharged and the next fill cycle gets a fresh one rather than a stale count.
        if arm and latch is not None:
            _clear_latch(workflow_dir)
        out.update({"needs_handoff": False, "handoff_written": False, "demands": 0,
                    "armed_at_mtime": None})
        return out

    if latch is None:
        latch = {"armed_handoff_mtime": _mtime(handoff), "demands": 0}
        if arm:
            _write_latch(workflow_dir, latch)

    armed = float(latch.get("armed_handoff_mtime") or 0.0)
    fresh = _mtime(handoff) > armed
    # "Written" is FRESH AND USABLE, not merely touched. Both halves report separately so an
    # operator reading `--json` can tell "nothing was written" from "something was, and it
    # cannot be resumed from" -- two different things to go and do.
    names_base = anchor_names_base(handoff)
    written = fresh and names_base
    out.update({"needs_handoff": not written, "handoff_written": written,
                "anchor_fresh": fresh, "anchor_names_base": names_base,
                "demands": int(latch.get("demands") or 0), "armed_at_mtime": armed})
    if fresh and not names_base:
        # Say WHICH half is missing. The generic band reason would send the session to rewrite
        # an anchor it has just written, with no hint as to what was wrong with it.
        out["reason"] = ("the anchor was rewritten but names no `base_sha`, so a resumed "
                         "session cannot read `git log <base_sha>..HEAD` and cannot see what "
                         "moved. Add it (`git rev-parse HEAD`) — the rest of the anchor stands.")
    return out


def awaiting_input(workflow_dir):
    """The open dialog, or None. A file that exists but will not parse still counts as open —
    the safe direction is "somebody is being waited on"."""
    path = os.path.join(workflow_dir, AWAITING_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            val = json.load(fh)
    except (OSError, ValueError):
        return {"kind": "unknown"}
    return val if isinstance(val, dict) else {"kind": "unknown"}


def clear_awaiting(workflow_dir):
    """Called from the `Stop` hook. A turn that has ended cannot be sitting in a dialog."""
    try:
        os.remove(os.path.join(workflow_dir, AWAITING_FILE))
        return True
    except OSError:
        return False


def session_idle(workflow_dir):
    """The idle-prompt record, or None when this session is not KNOWN to be idle.

    Absent reads as "not idle", and that asymmetry is the whole point. Every other `clear_safe`
    condition is a reason to hold stated in the negative; this one is a permission stated in the
    positive, because the failure it prevents cannot be undone. Keys sent into a running turn do
    not queue into it -- they land in the prompt box as literal text and are never submitted, so
    a single mistimed reset corrupts the input buffer and every retry makes it worse (OBSERVED,
    2026-09-19, on a real agentic drive: a stack of `/clear continue /clear continue` that only
    Esc could clear, and Esc then ran the `/clear` with no `continue` behind it).

    WHY THE RACE IS REAL AND NOT RARE. `handoff.md` is written DURING a turn, so the moment the
    session writes its anchor the other three conditions all hold while the model is still
    talking. The gate was true at exactly the wrong instant, every single time.

    A file that exists but will not parse still counts as idle: it was written by the idle hook
    and removed by the submit hook, so its PRESENCE is the fact and its body is only for humans.
    """
    path = os.path.join(workflow_dir, IDLE_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            val = json.load(fh)
    except (OSError, ValueError):
        return {"since": "unknown"}
    return val if isinstance(val, dict) else {"since": "unknown"}


def mark_idle(workflow_dir, record=None):
    """Called from the `Notification` hook on `idle_prompt`. Best-effort, like every writer here."""
    try:
        tmp = os.path.join(workflow_dir, "." + IDLE_FILE + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(record or {}, fh, sort_keys=True)
        os.replace(tmp, os.path.join(workflow_dir, IDLE_FILE))
        return True
    except OSError:
        return False


def clear_idle(workflow_dir):
    """Called from `UserPromptSubmit`: a prompt has been submitted, so the turn is running.

    It is the ONLY clearer. `SessionStart` used to call this too, and had it backwards — a
    started, resumed or cleared session is at an idle prompt BY DEFINITION, and the harness
    will never announce it (`idle_prompt` arms off the last message timestamp, and a cleared
    session has no messages). So that hook WRITES the flag instead, for exactly those three
    sources; see `hooks/session_start.py`, job 4, which also says why `compact` is not one.
    """
    try:
        os.remove(os.path.join(workflow_dir, IDLE_FILE))
        return True
    except OSError:
        return False


def workers_in_flight(workflow_dir, now=None, stale=IN_FLIGHT_STALE_SECONDS):
    """Dispatched workers that have not returned, newest first. `[]` when none.

    THE FACT NOTHING IN THIS PACKAGE HAD, and the harness made it load-bearing. The turn gate and
    the reset gate were both designed when a dispatch BLOCKED the parent: a turn that ended meant
    a session that had stopped. The harness now auto-backgrounds agents, so the parent's turn ends
    while the worker runs -- and both gates read that as a stop.
      · `turn_check.may_end` called every background dispatch a stop for nothing. On a real drive
        `turn-gate.json` reached `{"demands": 35}` against `MAX_DEMANDS = 2`: all false, and having
        spent the budget on them the gate stood down for the case it exists to catch.
      · `clear_safe` was worse. `idle_prompt` fires while a worker runs -- the parent genuinely IS
        at the prompt -- so with the band at `handoff-now` and an anchor written, the supervisor
        would `/clear` mid-dispatch and throw the worker away.
    Presence is the fact; the body is for humans. A file that will not parse still counts.
    """
    if now is None:
        now = time.time()
    path = os.path.join(workflow_dir, IN_FLIGHT_DIR)
    out = []
    try:
        names = os.listdir(path)
    except OSError:
        return out
    for name in names:
        if not name.endswith(".json"):
            continue
        full = os.path.join(path, name)
        try:
            age = now - os.path.getmtime(full)
        except OSError:
            continue
        if age > stale:
            continue                  # presumed dead -- see IN_FLIGHT_STALE_SECONDS
        rec = {}
        try:
            with open(full, encoding="utf-8") as fh:
                val = json.load(fh)
            if isinstance(val, dict):
                rec = val
        except (OSError, ValueError):
            pass
        rec.setdefault("agent", "unknown")
        rec["age_seconds"] = int(age)
        out.append(rec)
    out.sort(key=lambda r: r.get("age_seconds", 0))
    return out


def _parked_open(workflow_dir):
    """How many checkpoints are waiting on a human — or None when that cannot be established.

    Counted from `parked/` itself, not from the mirror in `handoff.md`: the mirror is a
    projection, and a projection is the wrong thing to ask when the question is "is a person
    genuinely blocked". `bus.py` owns the path resolution, so it is imported rather than
    re-derived — lazily, because this is the only part of the gate that costs anything and the
    `Stop` hook never asks it.

    None is NOT zero. An unreachable runtime root means nobody can say whether a human is
    waiting, and the consumer of that answer resets a live session — so it must read as "do not".
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import bus
        paths = bus.Paths(workflow_dir)
        if not os.path.isdir(paths.runtime):
            return None
        return len([n for n in os.listdir(paths.parked) if n.endswith(".json")])
    except FileNotFoundError:
        return 0            # a reachable runtime root that has simply never parked anything
    except (Exception, SystemExit):
        # `SystemExit` is deliberate and not defensive padding: `bus.Paths` RAISES it when the
        # runtime pointer names a root that is gone — the /rebind case — and `SystemExit` is not
        # an `Exception`. Caught here it becomes `None`, which reads as "a human may be waiting".
        return None


def gate(workflow_dir, project_dir=None, now=None, arm=True):
    """The full verdict, including whether a supervisor may reset this session."""
    out = demand(workflow_dir, project_dir=project_dir, now=now, arm=arm)
    blocked = []
    if out["verdict"] != "handoff-now":
        blocked.append("the band says %s, not handoff-now" % out["verdict"])
    if not out["handoff_written"]:
        blocked.append(
            "the handoff names no `base_sha`, so nothing could resume from it"
            if out.get("anchor_fresh")
            else "no handoff has been written since the band began asking for one")
    dialog = awaiting_input(workflow_dir)
    out["awaiting_input"] = dialog
    if dialog:
        blocked.append("a %s dialog is open — somebody is being asked something right now"
                       % (dialog.get("kind") or "unknown"))
    idle = session_idle(workflow_dir)
    out["session_idle"] = idle
    # `is None`, not falsiness: the record's BODY is for humans and an empty one is a legitimate
    # write. Presence is the fact.
    if idle is None:
        blocked.append("the session is not known to be idle — the harness announces an idle "
                       "prompt and nothing has since been submitted, and neither is true right "
                       "now. Keys sent into a running turn land in the prompt box as text and "
                       "are never submitted")
    flight = workers_in_flight(workflow_dir, now=None)
    out["workers_in_flight"] = flight
    if flight:
        blocked.append("%d dispatched worker(s) have not returned (%s) — the parent is idle "
                       "BECAUSE it is waiting for them, and a reset here throws the work away"
                       % (len(flight), ", ".join(sorted({str(r.get("agent")) for r in flight}))))
    n = _parked_open(workflow_dir)
    out["parked_open"] = n
    if n is None:
        blocked.append("the open-checkpoint record is unreadable — nothing can say a human is "
                       "not waiting, so this reads as though one is")
    elif n > 0:
        blocked.append("%d checkpoint(s) await a human verdict" % n)
    out["clear_safe"] = not blocked
    out["blocked_by"] = blocked
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Should this session hand off yet?")
    ap.add_argument("--workflow-dir", default=".workflow")
    ap.add_argument("--project-root", default=None,
                    help="where .workflow/config.json's operator ceiling is read from "
                         "(default: the parent of --workflow-dir)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--gate", action="store_true",
                    help="the ACTING verdict: needs_handoff / clear_safe / blocked_by. Always "
                         "JSON — this surface is read by the Stop hook and the supervisor, not "
                         "by eyes. Exit 0 iff a reset is safe RIGHT NOW, 1 otherwise.")
    ap.add_argument("--no-arm", action="store_true",
                    help="ask without latching the moment the band entered handoff-now "
                         "(a pure read; use it when inspecting, never when driving)")
    args = ap.parse_args(argv)

    import time
    if args.gate:
        g = gate(args.workflow_dir, project_dir=args.project_root, now=time.monotonic(),
                 arm=not args.no_arm)
        print(json.dumps(g, indent=2, sort_keys=True))
        return 0 if g["clear_safe"] else 1

    r = read_reading(args.workflow_dir, now=time.monotonic())
    warn = warn_pct_configured(args.project_root
                               or os.path.dirname(os.path.abspath(args.workflow_dir)) or ".")
    v = band(r.get("used"), r.get("window"), warn) if r else {
        "verdict": "unknown",
        "reason": "no recent context reading — the statusline publishes it, so this is either a "
                  "session with no statusline configured or one that has not rendered yet"}
    print(json.dumps(v, indent=2, sort_keys=True) if args.json else v["reason"])
    return {"handoff-now": 2, "handoff-at-boundary": 1, "hold": 0}.get(v["verdict"], 0)


if __name__ == "__main__":
    sys.exit(main())
