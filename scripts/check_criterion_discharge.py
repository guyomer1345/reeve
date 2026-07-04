#!/usr/bin/env python3
"""Criterion-discharge gate — the mechanical enforcer of "no vacuous artifact-pass".

The sibling of the promise-coverage gate: where that checks every impact-flagged promise maps
to a resolvable test, this checks every **`artifact`-gated acceptance criterion names a concrete
mechanical `discharge`**. It is a DECIDABLE structural check (like the no-spec-refs grep), not a
judgment — so it can block in `.workflow/checks.sh --check` / the pre-commit hook, unlike advisory
prose. It makes schemas.md's asserted invariant ("planner emits no un-checkable criterion") true
instead of aspirational: a criterion the planner can't attach a mechanical check to must be tagged
`human-qa`, never left as a bare `artifact` that `verify` would then pass with nothing behind it.

Input: the per-item manifest `.workflow/items/<id>/promises.json` that `planner` writes, whose
`criteria[]` mirrors the plan's `acceptance_criteria`:

    {
      "criteria": [
        { "id": "ac-1", "gate": "artifact", "discharge": "tests/test_sort.py::test_sorted" },
        { "id": "ac-2", "gate": "human-qa" }
      ],
      "promises": [ ... ], "known_tests": [ ... ]        # read by check_promise_coverage.py
    }

Blocks (exit 2) when a criterion:
  - is `gate: artifact` with an empty or missing `discharge`   → un-checkable-as-artifact;
  - carries an unknown `gate` (not `artifact` / `human-qa`)    → malformed.

HONEST CEILING (stated so no one mistakes this for more than it is): this proves a discharge is
PRESENT and typed. It CANNOT prove the named discharge is ADEQUATE — a "renders without error"
test named as the discharge for a "looks right" criterion (a plausible-but-insufficient discharge)
passes here. Adequacy stays `verify`'s read (it hard-fails a discharge that produced no signal) and
a deferred hardening (the same adversarial adequacy lens the promise `boundary` rule uses). This
gate raises the bar from "left an artifact criterion with nothing behind it" to "must name a check".
"""
import argparse
import json
import sys

VALID_GATES = {"artifact", "human-qa"}


def check(manifest):
    failures = []
    for c in manifest.get("criteria", []):
        cid = c.get("id") or c.get("criterion", "<unnamed>")
        gate = c.get("gate")
        if gate not in VALID_GATES:
            failures.append(f"criterion {cid!r}: unknown gate {gate!r} (expected artifact|human-qa)")
        elif gate == "artifact" and not (c.get("discharge") or "").strip():
            failures.append(
                f"criterion {cid!r}: gate=artifact but no discharge — name a mechanical check "
                f"(a test ref, or type/lint/structural) or tag it human-qa"
            )
    return failures


def main():
    ap = argparse.ArgumentParser(description="Block an artifact acceptance-criterion with no mechanical discharge.")
    ap.add_argument("manifest", nargs="?", help="path to promises.json (default: read stdin)")
    args = ap.parse_args()

    raw = open(args.manifest, encoding="utf-8").read() if args.manifest else sys.stdin.read()
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"criterion-discharge: cannot parse manifest: {exc}", file=sys.stderr)
        return 2

    failures = check(manifest)
    if failures:
        print("BLOCKED: criterion-discharge gate found un-checkable artifact criteria:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 2
    n = len(manifest.get("criteria", []))
    print(f"criterion-discharge: OK ({n} criterion(s) classified + discharged)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
