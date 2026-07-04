#!/usr/bin/env python3
"""Decision-coverage gate — the mechanical enforcer that a governing decision can't
evaporate between the decision-record and the code.

The third sibling of the plan-coverage gates (promise-coverage, criterion-discharge):
where those check promises and acceptance-criteria, this checks that **every governing
`decision-record` in `plan.decisions[]` maps to ≥1 plan step**. It is a DECIDABLE
structural check — not a judgment — so it can block in `.workflow/checks.sh --check` /
the pre-commit hook, unlike advisory prose. `planner` already runs this as an in-skill
gate; this makes it mechanical, so resolved intent can't silently vanish.

Input: the per-item manifest `.workflow/items/<id>/promises.json` that `planner` writes,
whose `decisions[]` mirrors `plan.decisions[]`:

    {
      "decisions": [
        { "id": "D-001", "steps": ["s1", "s3"] },
        { "id": "D-002", "steps": [] }              # <- blocks: maps to no step
      ],
      "promises": [ ... ], "criteria": [ ... ]      # read by the sibling gates
    }

Blocks (exit 2) when a decision maps to no plan step.

HONEST CEILING: this proves a decision is *referenced by* ≥1 step, not that the step
faithfully implements it — that stays `verify`'s read + the alignment scan. It raises
the bar from "silently dropped" to "must at least be wired to a step".
"""
import argparse
import json
import sys


def check(manifest):
    failures = []
    for d in manifest.get("decisions", []):
        did = d.get("id") or "<unnamed>"
        if not (d.get("steps") or []):
            failures.append(f"decision {did!r}: maps to no plan step (resolved intent would evaporate)")
    return failures


def main():
    ap = argparse.ArgumentParser(description="Block a governing decision that maps to no plan step.")
    ap.add_argument("manifest", nargs="?", help="path to promises.json (default: read stdin)")
    args = ap.parse_args()

    raw = open(args.manifest, encoding="utf-8").read() if args.manifest else sys.stdin.read()
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"decision-coverage: cannot parse manifest: {exc}", file=sys.stderr)
        return 2

    failures = check(manifest)
    if failures:
        print("BLOCKED: decision-coverage gate found unmapped decisions:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 2
    n = len(manifest.get("decisions", []))
    print(f"decision-coverage: OK ({n} decision(s) mapped to plan steps)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
