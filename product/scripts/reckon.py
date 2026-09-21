#!/usr/bin/env python3
"""Is the work of the last N commits actually moving the goal? -- the periodic anchor.

THE ASK: *"after X commits the repo will stop driving development and stop to think: ok the goal
is X, in the last 5 sessions we did Y, does Y truly progress us towards X? have we been scoped on
the wrong thing? working in loops around a problem that needs stopping and consulting QA? is the
goal just not anchored enough and needs to be clarified for us to progress?"*

WHY IT IS ON ITS OWN CLOCK, AND NOT TRIGGERED BY THE CONVERGENCE MEASURE. This was argued the
other way first and the maintainer was right. Every existing signal -- the stall streak, the
discharge fraction, the progress report -- is computed from the loop's own bookkeeping AGAINST A
GOAL IT ASSUMES IS SOUND. When the goal's own acceptance is unreachable, all of them faithfully
measure a fiction, and anything triggered BY them inherits the fiction and cannot report it. The
reflection has to be able to audit the measuring apparatus itself, so its trigger must sit
outside the apparatus. A commit counter is crude precisely because it is independent.

MEASURED, NOT FELT -- WHY FIVE. Two live projects on the maintainer's machine, 2026-09-21:
**1.56 and 1.60 commits per promoted item** (14 commits / 9 items; 8 / 5) -- consistent across two
codebases with nothing in common, so ~1.6 is the working ratio and five commits is about three
items of work. The window to beat came from the same data: on `consumer`, FIVE consecutive
promoted items discharged no acceptance (`ph-07b`, `drift-034`, `drift-032`, `gap-046`,
`gap-043`, `drift-033`) -- roughly eight commits -- before the owner re-steered the queue by hand.
To catch drift earlier than the human did, the pass must fire INSIDE that window: 5 commits lands
at about three items, two ahead of where he caught it. That is the whole basis for the default,
and it is a knob (`config.reckon.every_n_commits`) because two projects is two projects.

WHAT IT MEASURES, all of it arithmetic over artifacts that already exist -- no dispatch, no model
call, no new bookkeeping:
  * the WINDOW        commits since the last reckon receipt was added (git), and the ledger lines
                      appended in that span (the ledger is committed, so `git show <base>:` gives
                      its length then and subtraction gives the window exactly).
  * acceptance MOVED  goal acceptance ids newly discharged inside the window. Zero is the floor.
  * UNBOUND           acceptance nothing anywhere plans to discharge -- `converge.py` has computed
                      this since day one and NOTHING HAS EVER CONSUMED IT. Measured on the same
                      two projects: 3 of 7, and 10 of 13. The second means that goal cannot be met
                      as currently planned, which is the answer to *"is the goal anchored?"* and
                      no amount of building will change it.
  * CHURN             commits per closed item against the 1.6 baseline. Five commits to close one
                      item is the shape of looping around a problem, and it is decidable where
                      "did we go round in circles" is not: the item dirs that would show the
                      refine/debug cycles are pruned at promote time.

THE FLOOR IT CANNOT ARGUE PAST. A loop grading its own progress drifts toward *"yes, progressing"*
-- the same reason the autonomy floor exists. So: **zero acceptance moved in the window ⇒ the
verdict is not `progressing`, whatever the reading skill concludes.** Judgement may escalate above
this file's verdict; it may never soften it.

FAIL DIRECTION: report, never block. Every unreadable input lands on `unknown`, which routes to
nothing and costs a cycle. This pass has no veto over anything -- it is an observation that earns
a checkpoint at most, and a gate that could halt a drive on a torn JSON file would be a worse
failure than the drift it watches for.

Usage:
    python3 reckon.py due     [--project-root .] [--json]     # exit 0 when a reckon is due
    python3 reckon.py measure [--project-root .] [--json]     # the numbers, always exit 0
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

WORKFLOW = ".workflow"
LEDGER = "goal-ledger.jsonl"
# The receipt this pass stages, and the anchor the next window is measured from. The maintenance
# directory is self-collecting (each pass deletes earlier receipts as it writes its own), so the
# last reckon is not readable from disk -- it is read from git, by the commit that ADDED a file
# matching this prefix. Derived, never recorded twice.
RECEIPT_GLOB = ".workflow/maintenance/reckon-*.json"
DEFAULT_EVERY = 5
# Commits per closed item, measured on two live projects (1.56, 1.60). Doubling it is the churn
# line: twice the normal cost to land one item is the shape of a loop that keeps re-opening the
# same work. A ratio rather than a count, so it means the same thing in a fast week and a slow one.
BASELINE_COMMITS_PER_ITEM = 1.6
CHURN_MULTIPLE = 2.0


def _git(root, *args):
    try:
        out = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True,
                             timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def every_n(project_root):
    """`config.reckon.every_n_commits`, or the measured default. Nonsense falls back rather than
    disabling the pass: a mistyped knob must not silently switch off the anchor."""
    cfg = _read_json(os.path.join(project_root, WORKFLOW, "config.json"), {}) or {}
    v = (cfg.get("reckon") or {}).get("every_n_commits")
    return v if isinstance(v, int) and v >= 1 else DEFAULT_EVERY


def base_sha(project_root):
    """The commit the current window opens at: the last reckon, else the goal's own birth.

    `--diff-filter=A` is load-bearing -- a later maintenance pass DELETES this receipt, and a
    plain path filter would match that deletion and measure a window from the wrong end.
    """
    last = _git(project_root, "log", "--diff-filter=A", "--format=%H", "-1", "--", RECEIPT_GLOB)
    if last:
        return last, "the last reckon"
    goal = _read_json(os.path.join(project_root, WORKFLOW, "goal.json"), {}) or {}
    sha = goal.get("created_sha")
    if isinstance(sha, str) and sha.strip():
        return sha.strip(), "the goal's first commit"
    root = _git(project_root, "rev-list", "--max-parents=0", "-1", "HEAD")
    return (root, "the first commit") if root else (None, "nothing to measure from")


def _ledger_len_at(project_root, sha):
    """How many ledger ENTRIES existed at `sha`. Absent there ⇒ 0, which is the honest answer for a
    window that opens before the ledger did.

    Counted exactly the way `converge.read_ledger` counts — parseable dict lines, blanks and torn
    lines skipped — because this number INDEXES INTO that list. Counting raw lines here would
    misalign the window by one for every malformed line before the base, and the slice would then
    attribute someone else's item to this window.
    """
    blob = _git(project_root, "show", "%s:%s/%s" % (sha, WORKFLOW, LEDGER))
    if blob is None:
        return 0
    n = 0
    for line in blob.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            val = json.loads(line)
        except ValueError:
            continue
        if isinstance(val, dict):
            n += 1
    return n


def window(project_root):
    """-> {base, base_why, commits, ledger_from}. The span this pass is judging."""
    base, why = base_sha(project_root)
    out = {"base": base, "base_why": why, "commits": None, "ledger_from": 0}
    if not base:
        return out
    n = _git(project_root, "rev-list", "%s..HEAD" % base, "--count")
    out["commits"] = int(n) if (n or "").isdigit() else None
    out["ledger_from"] = _ledger_len_at(project_root, base)
    return out


def measure(project_root):
    """The whole objective reading. Never raises; unknowns are reported as unknown."""
    wf = os.path.join(project_root, WORKFLOW)
    out = {"verdict": "unknown", "findings": [], "commits": None, "items_closed": None,
           "acceptance_moved": [], "unbound": [], "planned": [], "discharged": [],
           "commits_per_item": None, "goal": None, "statement": ""}

    win = window(project_root)
    out.update(base=win["base"], base_why=win["base_why"], commits=win["commits"])
    if win["commits"] is None:
        out["findings"].append("the commit window could not be read — no git, or no anchor to "
                               "measure from")
        return out

    try:
        import converge
        goal = converge.read_goal(wf)
        ledger = converge.read_ledger(wf)
        m = converge.measure(goal, ledger, converge.open_bindings(wf))
    except Exception:                              # noqa: BLE001 — a reading pass never crashes
        out["findings"].append("convergence could not be measured")
        return out

    if not m.get("goal"):
        out.update(verdict="no-goal")
        out["findings"].append("no goal is set, so there is nothing to measure progress against "
                               "— this drive has no stop-when-done condition at all")
        return out

    status = m.get("status") or {}
    out.update(goal=m.get("goal"), statement=m.get("statement", ""),
               unbound=sorted(a for a in status if status[a] == "unbound"),
               planned=sorted(a for a in status if status[a] == "planned"),
               discharged=sorted(a for a in status if status[a] == "discharged"))

    # THE WINDOW'S OWN ARITHMETIC, and it is deliberately not the stall streak. The streak counts
    # CONSECUTIVE empty promotions and so is reset by a single lucky discharge: measured on
    # `consumer`, five straight items that moved nothing, then one that did, and the streak reads
    # 0 -- "not stalled" -- while the owner was re-steering the queue by hand. A window rate
    # cannot be reset by one item.
    ids = [a for a in status]
    before = set()
    for e in ledger[:win["ledger_from"]]:
        before.update(r for r in (e.get("refs") or []) if r in ids)
    moved = set()
    for e in ledger[win["ledger_from"]:]:
        moved.update(r for r in (e.get("refs") or []) if r in ids and r not in before)
    items = max(0, len(ledger) - win["ledger_from"])
    out.update(items_closed=items, acceptance_moved=sorted(moved))
    out["commits_per_item"] = round(win["commits"] / items, 2) if items else None

    if out["unbound"] and items:
        out["findings"].append(
            "%d of %d goal acceptance criteria are UNBOUND — nothing anywhere plans to discharge "
            "them, so this goal cannot be met as currently planned (%s)"
            % (len(out["unbound"]), len(ids), ", ".join(out["unbound"])))
    if not moved:
        out["findings"].append(
            "%d commit(s) and %d closed item(s) moved NO goal acceptance" % (win["commits"], items))
    if out["commits_per_item"] and out["commits_per_item"] >= BASELINE_COMMITS_PER_ITEM * CHURN_MULTIPLE:
        out["findings"].append(
            "%.2f commits per closed item against a %.1f baseline — the shape of re-opening the "
            "same work rather than finishing it" % (out["commits_per_item"],
                                                    BASELINE_COMMITS_PER_ITEM))

    # PRECEDENCE: the verdict is the finding that changes what happens NEXT, and an unreachable
    # goal outranks a slow window because no amount of building fixes it.
    if out["unbound"] and items:
        out["verdict"] = "goal-unreachable"
    elif not moved:
        out["verdict"] = "no-progress"           # THE FLOOR — see the module docstring
    elif out["commits_per_item"] and out["commits_per_item"] >= BASELINE_COMMITS_PER_ITEM * CHURN_MULTIPLE:
        out["verdict"] = "churning"
    else:
        out["verdict"] = "progressing"
    return out


def due(project_root):
    """-> (bool, commits, threshold). Is a reckon owed right now?"""
    n = every_n(project_root)
    commits = window(project_root)["commits"]
    if commits is None:
        return False, None, n                    # cannot tell ⇒ do not inject
    return commits >= n, commits, n


def render(res):
    lines = ["reckon: %s" % res["verdict"]]
    if res.get("goal"):
        lines.append("  goal      %s — %s" % (res["goal"], (res.get("statement") or "")[:90]))
    lines.append("  window    %s commit(s) since %s, %s item(s) closed"
                 % (res.get("commits"), res.get("base_why"), res.get("items_closed")))
    lines.append("  moved     %s" % (", ".join(res.get("acceptance_moved") or []) or "NOTHING"))
    lines.append("  acceptance %d discharged · %d planned · %d unbound"
                 % (len(res.get("discharged") or []), len(res.get("planned") or []),
                    len(res.get("unbound") or [])))
    for f in res.get("findings") or []:
        lines.append("  ! " + f)
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["due", "measure"])
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "due":
        owed, commits, n = due(args.project_root)
        rec = {"due": owed, "commits": commits, "every_n_commits": n}
        print(json.dumps(rec, sort_keys=True) if args.json else
              ("due — %s commit(s) since the last reckon (every %s)" % (commits, n) if owed
               else "not due — %s of %s commit(s)" % (commits, n)))
        return 0 if owed else 1

    res = measure(args.project_root)
    print(json.dumps(res, indent=2, sort_keys=True) if args.json else render(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
