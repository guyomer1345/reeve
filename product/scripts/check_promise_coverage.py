#!/usr/bin/env python3
"""Promise-coverage gate — the mechanical enforcer that a load-bearing promise can't ship untested.

The sibling of the decision-coverage gate: where that checks every governing decision maps to a
plan step, this checks every **impact-flagged promise** maps to a **resolvable test**. It is a
DECIDABLE structural check (like the no-spec-refs grep), not a judgment — so it can block in
`.workflow/checks.sh --check` / the pre-commit hook, unlike advisory prose.

Input: a per-item manifest `.workflow/items/<id>/promises.json` that `planner` writes from the
impact-flagged decision-records:

    {
      "known_tests": ["ac-1", "ac-2", ...],        # (optional) extra resolvable test ids
      "criteria": [                                 # the plan's acceptance_criteria — carries `boundary`
        { "id": "ac-1", "gate": "artifact", "boundary": true }
      ],
      "promises": [
        { "id": "p1", "text": "...", "universal": true|false, "test_ref": "ac-1" }
      ]
    }

Blocks (exit 2) when a promise:
  - has no `test_ref`, or a `test_ref` that resolves to no `known_tests`/`criteria` id   → unlinked;
  - is `universal` but its LINKED CRITERION is not `boundary`-tagged                     → in-scope-only.
    (`boundary` lives on the criterion, per schemas/planner — not on the promise.)

HONEST CEILING (stated so no one mistakes this for more than it is): this proves the *linkage* is
present and typed. It CANNOT prove the linked test is adequate — a test that exercises an in-scope
case while labelled as covering a universal promise (a "sham link") passes here. Adequacy of a
universal is the job of a property / structural invariant drawn from OUTSIDE the build's own
enumeration (see the code-map floor test for the template), and of the adversarial promise
elicitation upstream. This gate raises the bar from "never thought of it" to "must actively lie."
"""
import argparse
import json
import sys


def check(manifest):
    # `boundary` lives on the acceptance-CRITERION (schemas + planner), not on the promise. Resolve it off the
    # linked criterion; the criteria ids are also valid test_ref targets.
    criteria = manifest.get("criteria", [])
    crit_ids = {c.get("id") for c in criteria if c.get("id")}
    crit_boundary = {c.get("id"): bool(c.get("boundary")) for c in criteria if c.get("id")}
    known = set(manifest.get("known_tests", [])) | crit_ids
    failures = []
    for p in manifest.get("promises", []):
        pid = p.get("id") or p.get("text", "<unnamed>")
        ref = p.get("test_ref")
        if not ref:
            failures.append(f"promise {pid!r}: no test_ref (unlinked promise)")
        elif ref not in known:
            failures.append(f"promise {pid!r}: test_ref {ref!r} does not resolve to a known test/criterion")
        # fall back to the promise's own boundary only for legacy manifests that carry no criteria[]
        elif p.get("universal") and not crit_boundary.get(ref, p.get("boundary")):
            failures.append(
                f"promise {pid!r}: universal, but its criterion {ref!r} is not boundary-tagged "
                f"(a universal needs a case drawn from OUTSIDE the build's enumeration)"
            )
    return failures


def main():
    ap = argparse.ArgumentParser(description="Block a load-bearing promise with no resolvable test.")
    ap.add_argument("manifest", nargs="?", help="path to promises.json (default: read stdin)")
    args = ap.parse_args()

    raw = open(args.manifest, encoding="utf-8").read() if args.manifest else sys.stdin.read()
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"promise-coverage: cannot parse manifest: {exc}", file=sys.stderr)
        return 2

    failures = check(manifest)
    if failures:
        print("BLOCKED: promise-coverage gate found un-discharged promises:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 2
    n = len(manifest.get("promises", []))
    print(f"promise-coverage: OK ({n} promise(s) linked to resolvable tests)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
