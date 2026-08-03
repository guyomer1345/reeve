#!/usr/bin/env python3
"""The context-budget gate — the enforcement the "bounded by construction" claim never had.

`memory-model.md`'s read law ASSERTS that always-read files are bounded by construction.
Nothing held it true: `retention.py` caps the append-only tier (`# Sessions`) and nothing
else, so every other context-loaded file was bounded by hope. This script is the mechanism.
It answers exactly one question -- **is this doc too big** -- and deliberately not "is this
doc wrong", which `align` owns. Two owners, no overlap.

WHY TOKENS AND NOT LINES. A budget in lines is a budget in a unit the model does not read.
Tokens are also model-window-agnostic, the same reason the context governor's `warn_pct` is
a percentage rather than a token count.

TWO TIERS PER ROLE, and the second tier is the one that keeps this usable:
  HARD      -> fails `checks.sh`. For on-demand docs the hard number is not a preference at
               all, it is the Read tool's 25 000-token ceiling: a file over it *mechanically
               cannot be loaded in one call*, so this is enforcement that is a failure rather
               than advice.
  ADVISORY  -> never fails a build; it schedules a trim as an ordinary maintenance item.
Shipping only the aggressive number would have made this gate red on a clean install (the
package's own always-loaded templates are ~3.4k tokens each), and a gate that fires on a
fresh install trains a human to ignore it -- the same reason the staleness detector warns
once per SHA rather than every session. Green on install, with the aspiration tracked as
work rather than as a broken build.

ESTIMATED, NOT COUNTED, AND CALIBRATED ON A REAL FAILURE. There is no tokenizer in the
standard library and this package ships stdlib-only Python, so the count is an estimate from
character length. The divisor is not folklore: this project's own roadmap was measured at
85 083 characters when it *paged at the 25 000-token ceiling*, which puts the real ratio at
**<= 3.40 chars/token** for markdown prose. That measurement also kills the obvious choice --
the usual `chars/4` rule of thumb would have scored that exact file at 21 271 tokens,
comfortably "under" a ceiling it demonstrably could not fit. 3.2 ships, for margin below the
measured bound. It is a config knob (`chars_per_token`) because a doc dense in fenced code
tokenizes worse than prose, and lowering it is how a project tightens the estimate.

OVER BUDGET IS A TICKET, NEVER AN AUTO-EDIT. You cannot drop half a spec doc to git the way
retention drops a `# Sessions` entry -- splitting prose coherently needs judgment. So an
over-budget prose file routes to a SPLIT-AND-POINTER: a lean current-state file, an
archived-detail file, and a head marker in the survivor, mirroring the marker retention
already leaves. This script names the remedy; it never performs it.

  --check   (default) the gate: exit 1 if any file exceeds its role's HARD budget.
  --report  every file with its role, estimate and tier; exit 0. What the maintenance item
            reads, and what a human runs by hand.
  --json    machine-readable, for either mode.
"""
import argparse
import glob
import json
import math
import os
import sys

CONFIG_REL = os.path.join(".workflow", "config.json")

# Shipped defaults, DERIVED BY MEASURING this package rather than by citing a number (there
# is no single best-practice max size; that is why the budget is per role). The always-loaded
# pair the package itself ships measure ~3.3k and ~3.4k tokens, so `always_hard` sits above
# them with headroom -- the gate is green on a fresh install -- while `always_advisory` keeps
# the community sub-1k target visible as a scheduled trim.
DEFAULTS = {
    "chars_per_token": 3.2,
    "always_hard": 4000,
    "always_advisory": 1200,
    # Not a preference: the Read tool's own ceiling. A file over it cannot be read in one call.
    "ondemand_hard": 25000,
    "ondemand_advisory": 15000,
    "every_p_items": 15,
}

# The head marker the split-and-pointer convention leaves in the file that SURVIVES, so the
# detail is findable and the split is self-documenting. One owner for the string, here, for
# the same reason the brief markers live in `update_reconcile.py`: it is a compatibility
# contract, and a marker with two spellings is a marker nothing can find.
SPLIT_MARKER = "<!-- doc-budget: detail split -> %s @ %s -->"

ALWAYS = "always-loaded"
ONDEMAND = "on-demand"

ROLE_WHY = {
    ALWAYS: "rent paid every turn, every session, before a word is typed",
    ONDEMAND: "loaded when something needs it -- the 25 000-token Read ceiling is a hard wall",
}


def _read_json(path, default=None):
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return default


def budgets(project_root):
    cfg = _read_json(os.path.join(project_root, CONFIG_REL), {}) or {}
    out = dict(DEFAULTS)
    got = cfg.get("doc_budget")
    if isinstance(got, dict):
        for k, v in got.items():
            if k in out and isinstance(v, (int, float)) and v > 0:
                out[k] = v
    return out, (cfg.get("project_root") or ".")


def estimate_tokens(text, chars_per_token):
    """Characters -> an estimated token count, rounded UP.

    Rounding up and dividing by a number below the measured ratio both push the same way, on
    purpose: under-reporting means a file that cannot actually be read passes the gate, which
    is the one failure this must not have.
    """
    cpt = chars_per_token if chars_per_token and chars_per_token > 0 else DEFAULTS["chars_per_token"]
    return int(math.ceil(len(text) / float(cpt)))


def workflow_docs(project_root, proot):
    """(role, path) for every doc the workflow owns and a session can be made to read.

    The VOLATILE tier is deliberately ABSENT -- `state.json` and `handoff.md` are rewritten in
    place and `handoff.md` is already capped mechanically, at injection time, by the
    SessionStart hook. Giving it a second budget here would be a second owner of one bound,
    and the two would drift.
    """
    p = (lambda *a: os.path.join(project_root, *a))
    d = (lambda *a: os.path.join(project_root, proot, *a))
    out = []
    for path in (p("CLAUDE.md"), p(".workflow", "loop.md")):
        if os.path.isfile(path):
            out.append((ALWAYS, path))
    patterns = [
        d("docs", "spec.md"),
        d("docs", "architecture.md"),
        d("rules", "**", "*.md"),
        d("docs", "knowledge", "**", "*.md"),
        d("docs", "decisions", "**", "*.md"),
        p(".workflow", "backlog.md"),
    ]
    seen = {path for _r, path in out}
    for pat in patterns:
        for path in sorted(glob.glob(pat, recursive=True)):
            if os.path.isfile(path) and path not in seen:
                seen.add(path)
                out.append((ONDEMAND, path))
    return out


def scan(project_root):
    b, proot = budgets(project_root)
    rows = []
    for role, path in workflow_docs(project_root, proot):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue  # unreadable is not over-budget; it is nothing to say
        est = estimate_tokens(text, b["chars_per_token"])
        hard = b["always_hard"] if role == ALWAYS else b["ondemand_hard"]
        adv = b["always_advisory"] if role == ALWAYS else b["ondemand_advisory"]
        tier = "over" if est > hard else ("advisory" if est > adv else "ok")
        rows.append({"path": os.path.relpath(path, project_root).replace(os.sep, "/"),
                     "role": role, "tokens": est, "hard": hard, "advisory": adv,
                     "tier": tier})
    rows.sort(key=lambda r: (-r["tokens"], r["path"]))
    return {"budgets": b, "files": rows,
            "over": [r for r in rows if r["tier"] == "over"],
            "advisories": [r for r in rows if r["tier"] == "advisory"]}


def _remedy(row):
    if row["role"] == ALWAYS:
        return ("trim it -- move detail to an on-demand doc and leave a pointer; this file "
                "is read before every single turn")
    return ("split-and-pointer -- a lean current-state file plus an archived-detail file, "
            "with `%s` at the head of the survivor" % (SPLIT_MARKER % ("<detail path>", "<sha>")))


def render(result, report):
    lines = []
    for r in result["over"]:
        lines.append("OVER BUDGET  %-52s %7d tok  > %d (%s HARD)"
                     % (r["path"], r["tokens"], r["hard"], r["role"]))
        lines.append("             %s" % _remedy(r))
    if report:
        for r in result["advisories"]:
            lines.append("ADVISORY     %-52s %7d tok  > %d (%s -- %s)"
                         % (r["path"], r["tokens"], r["advisory"], r["role"],
                            ROLE_WHY[r["role"]]))
            lines.append("             not a build failure: schedule a trim. %s" % _remedy(r))
    n = len(result["files"])
    if result["over"]:
        lines.append("BLOCKED: %d of %d workflow-owned doc(s) exceed a HARD budget. Over the "
                     "on-demand wall a file cannot be read in one call at all, so this is a "
                     "broken read, not a style note. Fix by splitting, never by deleting "
                     "content that carries intent." % (len(result["over"]), n))
    else:
        lines.append("OK: doc budget -- %d workflow-owned doc(s) within budget (%d advisory)"
                     % (n, len(result["advisories"])))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="the context-budget gate over workflow-owned docs")
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--report", action="store_true",
                    help="list advisories too and always exit 0 (the maintenance-item view)")
    ap.add_argument("--check", action="store_true",
                    help="the gate: exit 1 on any HARD breach (the default)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.project_root)
    result = scan(root)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render(result, report=args.report))
    # `--report` is the read-only view: it must not fail a commit for an advisory, and its
    # whole job is to be safe to run anywhere.
    return 0 if args.report else (1 if result["over"] else 0)


if __name__ == "__main__":
    sys.exit(main())
