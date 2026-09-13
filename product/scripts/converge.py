#!/usr/bin/env python3
"""Is this goal converging, and is it met?

The driver stops on "met", so this answers a question that cannot be a judgement call made by
the thing that wants to keep running. It is therefore mechanical end to end: a goal is met when
every acceptance it enumerates has been discharged by a promoted item, and it is stalled when
consecutive promoted items discharge nothing new. No effort term appears anywhere in here --
a loop that counts sessions spent will churn happily and report progress the whole time.

WHY THERE IS A GOAL RECORD AT ALL, since `docs/spec.md` already states acceptance. Because it
states it as PROSE. The spec is a human-written Markdown document whose `features[].acceptance_criteria`
is a sentence, and a sentence has nothing an item's criterion can be bound to. `goal.json`
enumerates the acceptance the goal is judged on and gives each entry an id, so the binding has a
target. That enumeration is DERIVED from the spec and must be re-derived when the spec's
acceptance changes -- which is not a new discipline to remember: the autonomy floor already
treats a changed hunk inside an `acceptance_criteria` region as goal-affecting and routes it to a
human (`schemas.md § the autonomy floor`), and that routing is exactly the moment to re-derive.

WHY THE MEASURE MOVES ONLY AT ITEM CLOSE, which looks coarse and is the point. An open item has
delivered nothing; a plan that binds `ga-3` is a promise to discharge it, not a discharge. Reading
progress off open work is how a stalled loop reports motion. So:

    discharged  the id appears in `goal-ledger.jsonl`, written when `document` promoted the item
    planned     an OPEN item's promises.json binds it -- in flight, worth nothing yet
    unbound     nothing anywhere binds it, so the goal CANNOT be met as currently planned

`unbound` is the cheapest finding here and was not what this was built for. It is knowable before
any work happens: a goal carrying an acceptance no plan ever attempts is a goal that will run to
the stall limit and stop, and it can say so on day one instead.

WHY A LEDGER EXISTS WHEN THIS REPO DERIVES REALITY RATHER THAN RECORDING IT. The forecast anchor
table's law (`schemas-loopstate.md § the forecast ANCHOR TABLE`) is that reality is derived from
durable artifacts, never from a second ledger nobody keeps in step. That law holds here and the
ledger does not break it, because the artifacts it would derive from ARE DELETED: `retention.py`
prunes the whole item dir -- `promises.json` and `verify-verdict.md` with it -- once `document`
writes `promoted.json`. So this is not a parallel record of live state; it is the PROMOTED form of
an item's acceptance evidence, written at the one moment promote-then-prune already runs, by the
node that already runs it. While an item is open nothing is recorded and everything is derived.

WHAT IS DELIBERATELY NOT RECORDED: per-criterion pass/fail. `verify` hard-fails an item when any
`artifact` criterion's discharge produced no signal (`verify/SKILL.md`), so `pass: true` on line 1
of `verify-verdict.md` ALREADY entails that every artifact criterion of that plan discharged. A
per-criterion outcome field would be a second encoding of a fact the verdict token already carries,
and the two would eventually disagree.

STALL. Trailing ledger entries that added no new id. Five of them (`STALL_LIMIT`) and the goal is
stalled -- the same shape as the runner's `RUNNER_MAX_ATTEMPTS` consecutive no-progress relaunches,
lifted from the relaunch to the goal. An entry that RE-discharges an already-discharged id counts
as no progress, deliberately: re-fixing the same acceptance five times running is the churn this
exists to catch, not evidence of work. So does a promoted item with no goal binding at all -- five
consecutive items that moved no acceptance is a stall with respect to the goal whatever they were
about. The verdict is "stop and re-steer", never "abort", so a false positive costs a human glance
and a false negative costs an unattended night.

FAIL DIRECTION. Every failure to compute -- no goal file, unparseable JSON, an unreadable item --
lands on NOT met and `progress: unknown`. Never `met` on an error: the driver stops on `met`, so a
permissive error would declare a goal finished that nobody finished.
"""
import argparse
import json
import os
import sys

STALL_LIMIT = 5      # consecutive no-progress promotions before the goal is called stalled

GOAL_FILE = "goal.json"
LEDGER_FILE = "goal-ledger.jsonl"


# --- reading ------------------------------------------------------------------

def _read_json(path):
    """None on anything that is not a readable JSON object -- callers fail closed on None."""
    try:
        with open(path, encoding="utf-8") as fh:
            val = json.load(fh)
    except (OSError, ValueError):
        return None
    return val if isinstance(val, dict) else None


def read_goal(workflow_dir):
    return _read_json(os.path.join(workflow_dir, GOAL_FILE))


def read_ledger(workflow_dir):
    """Ordered list of promotion entries. A malformed LINE is skipped, not fatal -- the file is
    append-only and a torn tail must not blind the whole measure to every entry before it."""
    path = os.path.join(workflow_dir, LEDGER_FILE)
    entries = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    val = json.loads(line)
                except ValueError:
                    continue
                if isinstance(val, dict):
                    entries.append(val)
    except OSError:
        return []
    return entries


def open_bindings(workflow_dir):
    """{goal_ref: [item_id]} over items that are OPEN -- present on disk without a `promoted.json`.
    A promoted item's bindings are the ledger's to report, and reading both would double-count."""
    items_dir = os.path.join(workflow_dir, "items")
    bound = {}
    try:
        names = sorted(os.listdir(items_dir))
    except OSError:
        return bound
    for name in names:
        item = os.path.join(items_dir, name)
        if not os.path.isdir(item) or os.path.exists(os.path.join(item, "promoted.json")):
            continue
        manifest = _read_json(os.path.join(item, "promises.json"))
        if not manifest:
            continue
        for c in manifest.get("criteria", []):
            ref = (c.get("goal_ref") or "").strip()
            if ref:
                bound.setdefault(ref, []).append(name)
    return bound


# --- the measure --------------------------------------------------------------

def measure(goal, ledger, bound):
    """The whole verdict as one dict. `goal` None ⇒ no goal is active, which is not an error:
    the loop runs item-at-a-time without one and this simply has nothing to say."""
    if not goal:
        return {"goal": None, "met": False, "stalled": False, "progress": "unknown",
                "reason": "no goal.json — nothing to converge on"}

    acceptance = [a for a in goal.get("acceptance", []) if isinstance(a, dict) and a.get("id")]
    ids = [a["id"] for a in acceptance]
    if not ids:
        return {"goal": goal.get("id"), "met": False, "stalled": False, "progress": "unknown",
                "reason": "goal.json enumerates no acceptance — a goal with no acceptance can "
                          "never be mechanically met; re-derive it from the spec"}

    discharged = set()
    for e in ledger:
        for r in e.get("refs", []) or []:
            if r in ids:
                discharged.add(r)

    status = {}
    for aid in ids:
        if aid in discharged:
            status[aid] = "discharged"
        elif bound.get(aid):
            status[aid] = "planned"
        else:
            status[aid] = "unbound"

    # Trailing promotions that added nothing new. Replayed forward so "new" means new AT THE TIME,
    # which is what no-progress means -- a re-discharge is not progress even though the id is live.
    seen, streak = set(), 0
    for e in ledger:
        fresh = [r for r in (e.get("refs", []) or []) if r in ids and r not in seen]
        seen.update(fresh)
        streak = 0 if fresh else streak + 1

    unbound = [a for a in ids if status[a] == "unbound"]
    met = len(discharged) == len(ids)
    return {
        "goal": goal.get("id"),
        "statement": goal.get("statement", ""),
        "met": met,
        "stalled": (not met) and streak >= STALL_LIMIT,
        "streak": streak,
        "stall_limit": STALL_LIMIT,
        "total": len(ids),
        "discharged": sorted(discharged),
        "unbound": unbound,
        "status": status,
        "promotions": len(ledger),
        "progress": "%d/%d acceptance discharged" % (len(discharged), len(ids)),
    }


# --- recording ----------------------------------------------------------------

def record(workflow_dir, item_id):
    """Append one promotion entry. Called at `document`'s promote moment, BEFORE the item dir is
    prunable -- it is the last point at which the bindings still exist to be read.

    IDEMPOTENT by item id: a re-run (a crash between the append and `promoted.json`, a replayed
    tail) rewrites nothing and appends nothing. Without this the stall streak would be corrupted by
    recovery itself -- a duplicated no-progress entry lengthens a streak that never happened."""
    goal = read_goal(workflow_dir)
    if not goal:
        return 0, "no goal.json — nothing to record against"
    for e in read_ledger(workflow_dir):
        if e.get("item") == item_id:
            return 0, "item %s already recorded — no-op" % item_id

    manifest = _read_json(os.path.join(workflow_dir, "items", item_id, "promises.json"))
    refs = []
    if manifest:
        for c in manifest.get("criteria", []):
            ref = (c.get("goal_ref") or "").strip()
            if ref and ref not in refs:
                refs.append(ref)

    entry = {"goal": goal.get("id"), "item": item_id, "refs": refs}
    path = os.path.join(workflow_dir, LEDGER_FILE)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return 0, "recorded %s → %s" % (item_id, ", ".join(refs) or "no goal acceptance")


# --- cli ----------------------------------------------------------------------

def _render(m):
    if not m.get("goal"):
        return m.get("reason", "no goal")
    head = "goal %s: %s" % (m["goal"], m["progress"])
    if m.get("reason"):
        return head + " — " + m["reason"]
    bits = [head]
    if m["met"]:
        bits.append("MET")
    if m.get("stalled"):
        bits.append("STALLED (%d consecutive promotions added nothing; limit %d) — stop and "
                    "re-steer: read back what was attempted and why it did not move, re-research, "
                    "re-plan. NEVER retry the same item — a retry is what produced this streak."
                    % (m["streak"], m["stall_limit"]))
    if m.get("unbound"):
        bits.append("UNBOUND (no plan attempts these, so the goal cannot be met as planned): "
                    + ", ".join(m["unbound"]))
    return "\n".join(bits)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Acceptance-derived convergence for the active goal.")
    ap.add_argument("--workflow-dir", default=".workflow")
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("status", help="the measure (exit 0 always — reporting is not a gate)")
    st.add_argument("--json", action="store_true")
    sub.add_parser("met", help="exit 0 when every acceptance is discharged, 1 otherwise")
    ck = sub.add_parser("check", help="exit 2 when the goal is STALLED — the driver's stop")
    ck.add_argument("--json", action="store_true")
    rec = sub.add_parser("record", help="append a promotion entry (document, at promote time)")
    rec.add_argument("--item", required=True)
    args = ap.parse_args(argv)

    wf = args.workflow_dir
    if args.cmd == "record":
        code, msg = record(wf, args.item)
        print("converge: " + msg, file=sys.stderr)
        return code

    m = measure(read_goal(wf), read_ledger(wf), open_bindings(wf))
    if getattr(args, "json", False):
        print(json.dumps(m, indent=2, sort_keys=True))
    else:
        print(_render(m), file=sys.stderr)

    if args.cmd == "met":
        return 0 if m["met"] else 1
    if args.cmd == "check":
        return 2 if m.get("stalled") else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
