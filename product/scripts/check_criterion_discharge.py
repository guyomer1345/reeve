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
  - carries an unknown `gate` (not `artifact` / `human-qa`)    → malformed;
  - is `gate: human-qa` with an empty or missing `why_human`   → THE RESIDUE DEFECT (below);
  - names a `run:` discharge with no command after the colon   → nothing to run;
  - is `blocking: false` while binding a `goal_ref`            → a deferred question cannot
    discharge a goal acceptance: the ledger records the binding at PROMOTE time, so `converge.py`
    would report the goal met on an answer nobody has given. If the answer decides whether the
    goal is met, it is not deferrable.

THE RESIDUE DEFECT, and why `why_human` is required. The rule the package states is that the human
is the PRODUCT OWNER: *a checkpoint is justified only when the answer could change what the product
IS or what it PROMISES.* The qa gate asked a different question — *is there a criterion we cannot
mechanically check* — which routes to a human by RESIDUE: anything hard to automate became his
problem, bypassing `decision-engineer`, `review`, `debug` and `research`, which this package itself
calls its decision authority and which are awake at 3am. Measured: three unattended drives spent a
whole night stopped on qa checkpoints. Requiring one line naming what about the PRODUCT could change
does not prove the answer is a good one, but it makes the absence of an answer decidable — and the
absence is the defect. Adequacy stays `verify`'s read, the same ceiling the `discharge` check has.

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
RUN_PREFIX = "run:"


def check(manifest):
    failures = []
    for c in manifest.get("criteria", []):
        cid = c.get("id") or c.get("criterion", "<unnamed>")
        gate = c.get("gate")
        discharge = (c.get("discharge") or "").strip()
        if gate not in VALID_GATES:
            failures.append(f"criterion {cid!r}: unknown gate {gate!r} (expected artifact|human-qa)")
            continue
        if gate == "artifact":
            if not discharge:
                failures.append(
                    f"criterion {cid!r}: gate=artifact but no discharge — name a mechanical check "
                    f"(a test ref, type/lint/structural, or `run: <command>`) or tag it human-qa"
                )
            elif discharge.lower().startswith(RUN_PREFIX) and not discharge[len(RUN_PREFIX):].strip():
                # A bare `run:` is the one shape that LOOKS discharged and settles nothing: the
                # presence check would pass it, and `verify` would then look for the signal of a
                # command nobody named.
                failures.append(
                    f"criterion {cid!r}: discharge is `run:` with no command after the colon"
                )
        elif c.get("blocking") is False and (c.get("goal_ref") or "").strip():
            failures.append(
                f"criterion {cid!r}: blocking=false but it binds goal acceptance "
                f"{c['goal_ref']!r} — a deferred question cannot discharge a goal acceptance "
                f"(the ledger records the binding at promote time, so the goal would read as met "
                f"on an answer nobody has given). Make it blocking, or drop the goal_ref"
            )
        elif not (c.get("why_human") or "").strip():
            failures.append(
                f"criterion {cid!r}: gate=human-qa but no why_human — name in one line what about "
                f"the PRODUCT could change if the answer came back differently. If nothing could, "
                f"it is not a checkpoint: give it a discharge (a test, or `run: <command>`) and "
                f"let `verify` settle it"
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
