#!/usr/bin/env python3
"""Is this plan still about the tree it was planned against?

Under plan-ahead a plan is no longer written and immediately spent. A wave plans several items
and builds a subset; the rest sit with plans describing a tree that the very wave just built
is landing changes into. So a plan acquires a property it never had before -- it can rot -- and
this module is the one place that asks whether it has.

THE ANSWER IS ONE OF THREE, and the middle one is the interesting one:

    FRESH    nothing the plan declares has moved since it was written. Spend it as-is.
    SUSPECT  something it declares has moved. Its declared scope can no longer be trusted, so
             it must be refreshed before it is dispatched -- and, until it is, anything reading
             that scope must read it PESSIMISTICALLY (see `widened`).
    REPLAN   refreshing it would be patching over a hole. Throw it away and plan again.

WHY THIS IS NOT A NUMBER. The obvious design is a staleness threshold -- N commits, M files, X
hours -- and every one of those is wrong in both directions at once. A mechanical rename across
forty files is trivially refreshable; a single commit that inverts a module's contract is fatal.
Distance from the base commit does not measure what we care about, so it is not measured. What
is mechanical here is the *routing* -- fresh, patch, or start over -- and the judgement of
whether a patch is honest belongs to `planner:refresh`, which can read the diff and say
`cannot refresh`. This file never overrules that; it only decides who gets asked.

THE THREE TRIPWIRES that skip the refresh attempt entirely, because a refresh could only
produce a plausible-looking plan resting on a dead premise -- which is strictly worse than a
stale one, since staleness is detectable and a quietly-patched wrong plan is not:

  1. NO `base_sha` (or one git cannot resolve). A plan that cannot say what it was planned
     against cannot be shown fresh. Deliberately NOT inferred from git -- the last commit
     touching `plan.md` is a decent guess and a guess is what this must not be. Every plan
     written before the field existed re-plans exactly once, which is the correct migration.
  2. A DECLARED FILE WAS DELETED. The plan's scope is void rather than dated. Renames do not
     count: git detects them for free, and a renamed file is precisely the cheap case refresh
     exists for. Getting this backwards would send every refactor through a full re-plan.
  3. `refresh_count` HAS REACHED THE CAP. Each refresh is locally correct and a stack of them
     is not. This counts how often we have papered over the tree rather than pretending to
     measure how far the tree moved -- the honest mechanical stand-in for "too stale to patch".

FAIL DIRECTION. Every failure to compute -- no git, an unreadable plan, a base sha from
rewritten history -- lands on "not fresh". A caller that cannot tell an error from a verdict
will eventually treat one as the other, and the safe way to be wrong here is to refresh or
re-plan something that did not need it. The reverse wagers a dispatched worker on a plan that
does not describe the tree, and that worker is built to stop dead rather than improvise, so the
cost of being wrong permissively is a whole dispatch that was doomed before it started.

`moved` IS THE PART OTHER CODE USES -- the declared paths that actually changed. This file
stops there on purpose: turning "the ground under these paths shifted" into a pessimistic scope
needs the code map, which belongs to the independence gate, and duplicating the graph read here
would give one question two owners. What the gate does with it is widen -- and widening is why
a wave can choose its batch BEFORE paying to refresh anything, then refresh only the plans it
means to spend. A refresh bought for a plan the wave leaves behind is likely to be destroyed by
that very wave, since the gate proves the batch disjoint from ITSELF, not from the candidates
it declined.

EXIT CODES -- TWO, mirroring the independence gate for the same reason.
    0  every examined candidate is FRESH (or the tree has no history, so the question does
       not arise); the wave may read declared scopes as written.
    1  at least one is SUSPECT or REPLAN, or something could not be computed.
"""

import argparse
import json
import os
import re
import subprocess
import sys

CONFIG_REL = os.path.join(".workflow", "config.json")
DEFAULT_REFRESH_MAX = 2

FRESH, SUSPECT, REPLAN, NO_PLAN = "fresh", "suspect", "replan", "no-plan"
NO_GIT = "no-git"

# `- **base_sha** — `abc123`` / `- base_sha: abc123` / `**base_sha:** `abc123``. Plans are
# markdown written by a model, so the spelling varies; what does not vary is that the value is
# a hex sha somewhere on a line whose key is `base_sha`. Anything else is treated as absent,
# which routes to REPLAN -- the safe direction -- rather than to a guess.
_SHA = re.compile(r"^[^\n]*\bbase[ _]sha\b[^0-9a-fA-F\n]*([0-9a-fA-F]{7,40})\b", re.M)
_COUNT = re.compile(r"^[^\n]*\brefresh[ _]count\b\D*(\d+)", re.M)


def _cfg(wf):
    try:
        with open(os.path.join(wf, CONFIG_REL), encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:
        return {}


def refresh_max(wf):
    v = (_cfg(wf).get("run") or {}).get("wave", {}).get("refresh_max")
    return v if isinstance(v, int) and v >= 0 else DEFAULT_REFRESH_MAX


def _git(wf, *args):
    """-> (ok, stdout). Never raises: a git failure is a verdict input, not a crash."""
    try:
        p = subprocess.run(("git", "-C", wf) + args, capture_output=True,
                           text=True, timeout=60)
    except Exception:
        return False, ""
    return p.returncode == 0, p.stdout


def is_repo(wf):
    """Is there a history for a plan to have gone stale against?

    Treated as a SEPARATE state from "stale", and the distinction is not cosmetic. Everywhere
    else in this file an absence routes to the conservative answer, because absence usually
    means *we cannot tell*. Here it means something different: the premise itself is missing.
    Plan-ahead staleness is caused by sibling waves LANDING COMMITS underneath an unbuilt plan,
    and with no repository there are no commits, no waves, and nothing that could have moved.
    Routing that to REPLAN would force every plan in a non-repo tree to be re-planned forever,
    which is not conservative -- it is just broken.

    The limit, stated because it is real: uncommitted edits in a working tree are invisible
    here. They belong to an in-flight worker, and the independence gate already holds in-flight
    items as constraining writers, so the gap is covered there rather than papered over here.
    """
    ok, out = _git(wf, "rev-parse", "--is-inside-work-tree")
    return ok and out.strip() == "true"


def plan_meta(wf, item):
    """-> (base_sha|None, refresh_count, raw_text|None) for one item's plan."""
    try:
        with open(os.path.join(wf, ".workflow", "items", item, "plan.md"),
                  encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None, 0, None
    m = _SHA.search(text)
    c = _COUNT.search(text)
    return (m.group(1) if m else None), (int(c.group(1)) if c else 0), text


def changed_since(wf, base_sha):
    """-> (ok, {path: status}) for `base_sha..HEAD`, with renames detected.

    Statuses are git's own single letters; only `D` is load-bearing here. `-M` is what keeps a
    rename out of the deletion bucket: without it git reports the old path as `D` and every
    refactor would trip tripwire 2 and force a full re-plan.
    """
    ok, out = _git(wf, "diff", "--name-status", "-M", "%s..HEAD" % base_sha)
    if not ok:
        return False, {}
    changed = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        code = parts[0][:1]
        if code == "R" and len(parts) >= 3:
            # A rename touches BOTH paths and neither is a deletion: the old name is where a
            # plan's declared scope points, the new one is where the content went.
            changed[parts[1]] = "R"
            changed[parts[2]] = "R"
        else:
            changed[parts[-1]] = code
    return True, changed


def classify(wf, item, cap=None):
    """-> a verdict dict for one item. Never raises."""
    if cap is None:
        cap = refresh_max(wf)
    from check_wave_independence import plan_tokens          # one owner for scope parsing
    base, count, text = plan_meta(wf, item)
    out = {"id": item, "base_sha": base, "refresh_count": count,
           "declared": [], "moved": [], "why": ""}

    if text is None:
        out["state"] = NO_PLAN
        out["why"] = "no plan"
        return out

    declared, _why = plan_tokens(wf, item)
    out["declared"] = declared

    if not is_repo(wf):
        out["state"] = NO_GIT
        out["why"] = "no git repository -- nothing can have landed under this plan"
        return out
    if count >= cap:
        out["state"] = REPLAN
        out["why"] = "refreshed %d time(s), cap is %d -- patches have stacked far enough" % (count, cap)
        return out
    if not base:
        out["state"] = REPLAN
        out["why"] = "no `base_sha` -- cannot be shown fresh against anything"
        return out

    ok, changed = changed_since(wf, base)
    if not ok:
        out["state"] = REPLAN
        out["why"] = "`base_sha` %s does not resolve against this history" % base[:12]
        return out

    # Declared entries are plan spellings (globs, dirs, brace sets); a changed path is a
    # concrete file. Match on prefix so a plan declaring a directory sees the file inside it.
    moved, deleted = [], []
    for d in declared:
        d = d.rstrip("/")
        for path, code in changed.items():
            if path == d or path.startswith(d + "/"):
                moved.append(path)
                if code == "D":
                    deleted.append(path)
    out["moved"] = sorted(set(moved))

    if deleted:
        out["state"] = REPLAN
        out["why"] = "declared file(s) deleted, scope is void not dated: %s" % ", ".join(sorted(set(deleted))[:4])
        return out
    if moved:
        out["state"] = SUSPECT
        out["why"] = "%d declared path(s) moved since %s" % (len(out["moved"]), base[:12])
        return out

    out["state"] = FRESH
    return out


def scan(wf, items=None):
    if not items:
        idir = os.path.join(wf, ".workflow", "items")
        items = sorted(n for n in os.listdir(idir)
                       if os.path.isfile(os.path.join(idir, n, "plan.md"))) \
            if os.path.isdir(idir) else []
    cap = refresh_max(wf)
    res = [classify(wf, i, cap) for i in items]
    return {"refresh_max": cap, "results": res,
            "all_fresh": bool(res) and all(r["state"] in (FRESH, NO_GIT) for r in res)}


def render(res):
    order = {REPLAN: 0, SUSPECT: 1, NO_PLAN: 2, NO_GIT: 3, FRESH: 4}
    lines = ["plan freshness (refresh cap %d)" % res["refresh_max"], ""]
    for r in sorted(res["results"], key=lambda r: (order.get(r["state"], 9), r["id"])):
        lines.append("  %-8s %s%s" % (r["state"].upper(), r["id"],
                                      ("  -- " + r["why"]) if r["why"] else ""))
        if r["state"] == SUSPECT:
            lines.append("           moved: %s" % ", ".join(r["moved"][:6]))
    if not res["results"]:
        lines.append("  (no planned items)")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="is a plan still about the tree it was planned against")
    ap.add_argument("items", nargs="*", help="item ids (default: every item with a plan)")
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    res = scan(os.path.abspath(args.project_root), args.items)
    print(json.dumps(res, indent=2, sort_keys=True) if args.json else render(res))
    return 0 if res["all_fresh"] else 1


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
