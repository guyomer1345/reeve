---
name: verify
description: Check that built artifacts conform to what was asked — the plan against the changelog against the tree's real diff, and whether the spec intent and the plan's acceptance criteria were met. Operates on artifacts, not runtime behaviour. Use after execute; on failure, hand off to debug.
---

# Verify — artifact conformance ({asked} vs {done})

Core principle: an `adjudicate` specialization — gather the views (what was *asked*, what was *claimed*, what
was *actually changed*), judge conformance, gate on confidence. Conformance on **artifacts only**; runtime
behaviour is `debug`'s job and live-app confirmation is `checkpoint`'s.

## Inputs
- `plan` — the asked-for changes + `acceptance_criteria`, each tagged `gate: artifact | human-qa`.
- `changelog` — what `execute` **recorded** doing. A self-report: treat it as a claim, never as the change.
- `diff` — what the tree **actually** changed, read from git (below). The independent view; the changelog is
  checked *against* it, not trusted in place of it.
- `spec` — the intent the plan serves.

### Reading the real change
The changelog is written by the same step that made the change, so on its own it cannot catch an omission or a
mis-record. Read the actual file set first — **the diff is an artifact, so this stays inside the artifact-only
rule; you are reading git's record, not running the code**:

```sh
git rev-parse --verify -q HEAD >/dev/null \
  && git diff HEAD --name-status \
  || git ls-files --cached --stage            # no commits yet (bootstrap): everything tracked is new
git ls-files --others --exclude-standard      # NEW files — untracked, so the line above cannot see them
```

**Both commands are required.** `git diff HEAD` covers staged *and* unstaged changes to tracked files but is
**blind to a newly created file**, which is untracked until something stages it — and a new file is the most
likely thing for a changelog to under-report. Checking only the first command yields a check that passes for
the wrong reason. In org mode the brain *is* the clone, so these run against the brain's own tree as normal.

## Workflow — three checks
1. **Plan ↔ changelog ↔ diff:** the changes the `plan` asked for match what the `changelog` records **and** what
   the tree actually shows. Three divergences, each a hard fail (all are demonstrable — you can name the file):
   - **Under-report** — a path in the diff that the changelog never mentions. Silent scope creep, or a change
     the author did not realize they made. The most dangerous of the three, and the one only this check finds.
   - **Over-report** — the changelog claims a change no diff entry supports. The work was not done, or was lost.
   - **Off-plan** — a path in the diff that no plan step asked for. Not automatically wrong (a plan may license
     incidental edits), but it must be *accounted for*, not merely present.
   Judgment stays with you: matching prose to paths is not mechanical, and a changelog may legitimately describe
   one logical change spanning several files. **Set-level absence is the signal; wording is not.**
2. **Intent met:** the `spec` intent and the plan's **`artifact`-gated** `acceptance_criteria` are reflected
   and actually achieved (the definition-of-done gate). For each `artifact` criterion, its **`discharge` must
   have produced a signal** — a criterion whose named check did not run or did not pass is **not met**; `verify`
   never *vacuously passes* it.
3. **Promise coverage (artifact check):** every `plan.promises[]` entry resolves to an `acceptance_criterion`,
   and a `universal` promise's criterion is `boundary`-tagged and backed by a **property/structural test** (not
   a single in-scope example). This is the artifact-level read of what `check_promise_coverage.py` gates
   mechanically — the gate supplies the deterministic signal, so a missing or in-scope-only discharge is a hard
   **fail**, not a suspicion. You read the linkage; you do **not** run the test (that is the test-runner's job).

Lean: for small changes, judge directly without fanning out workers.

## Rules
- **The verdict is artifact-only** — `verify` never *judges* runtime behaviour (`debug`'s job) or confirms the
  live app (`checkpoint`'s), and it does not **run** the flow either. It reads artifacts.
  *(An earlier wording licensed `verify` to drive the affected flow as a pure observer, to feed a durable
  observed layer of the code map. That layer is not built — nothing in the package produces or consumes it — so
  the licence had no consumer and sat in tension with this very rule. It is removed rather than left dormant. If
  the observed layer is ever built, grant the licence again deliberately, against the real capture mechanism.)*
- Never pass/fail a `human-qa`-gated criterion; those are confirmed by a `checkpoint` (kind=qa), not here.
- **A `fail` gates only with a deterministic signal behind it** — a failing test, a type/lint violation, a
  plan↔changelog↔diff mismatch, **or an `artifact` criterion whose `discharge` produced no signal** (a hard
  fail, never a silent pass). A changelog↔diff divergence is always such a signal: the offending path is
  nameable, which makes it structural rather than suspected. A criterion↔artifact contradiction the model can **demonstrate** (point at the
  offending artifact) is itself such a signal — a *structural* mismatch, hard fail. Only a mismatch the model
  can merely *infer/suspect*, with nothing to point at, stays advisory (low confidence), not a hard fail.

## Output
`verify-verdict { pass, mismatches[], confidence }`, written to `.workflow/items/<id>/verify-verdict.md`.
**Its first line MUST be exactly `pass: true` or `pass: false`** (lowercase, one space) — the machine token the
git-native commit gates (`guard.sh` / `pre-commit.sh`) read to allow or block the item's commit. They **fail
closed**: a missing file, a `.json` instead of `.md`, or a reworded token blocks the commit. Never move, reword,
or omit this line; the mismatches and confidence follow as prose beneath it.

## Route
- **pass** → `document` / `commit`. If the `plan` declared any `human-qa` acceptance criteria, the
  orchestrator inserts a `checkpoint` (kind=qa) first; otherwise straight through — no blanket human QA.
- **fail** → `debug`. A failed check is a valid debug trigger even with no live error.
- **irreconcilable** (asked vs done can't be settled from the artifacts) → escalate → `checkpoint` (human) — the
  `adjudicate` escalate branch, not a silent pass or an endless re-gather.
