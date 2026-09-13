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
"""
import argparse
import json
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
    dead session's window is worse than no verdict."""
    path = os.path.join(workflow_dir, "context.json")
    try:
        with open(path, encoding="utf-8") as fh:
            val = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(val, dict):
        return None
    if now is not None and isinstance(val.get("mono"), (int, float)):
        if now - val["mono"] > STALE_SECONDS:
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


def main(argv=None):
    ap = argparse.ArgumentParser(description="Should this session hand off yet?")
    ap.add_argument("--workflow-dir", default=".workflow")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    import time
    r = read_reading(args.workflow_dir, now=time.monotonic())
    v = band(r.get("used"), r.get("window")) if r else {
        "verdict": "unknown",
        "reason": "no recent context reading — the statusline publishes it, so this is either a "
                  "session with no statusline configured or one that has not rendered yet"}
    print(json.dumps(v, indent=2, sort_keys=True) if args.json else v["reason"])
    return {"handoff-now": 2, "handoff-at-boundary": 1, "hold": 0}.get(v["verdict"], 0)


if __name__ == "__main__":
    sys.exit(main())
