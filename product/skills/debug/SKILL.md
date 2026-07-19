---
name: debug
description: Find the root cause when behaviour doesn't match intent — triggered by a failed verify, a failed test, or a live error. Maps intended vs actual behaviour, judges the cause with a confidence score, and loops for more information when unsure. Hands its finding to refine; it diagnoses, it does not fix.
---

# Debug — root-cause behaviour ≠ intended

Core principle: an `adjudicate` specialization (views = {intended behaviour, actual behaviour}; domain =
defects). Operates on **runtime behaviour** — the counterpart of `verify`, which operates on artifacts.

## When
`verify` fails, a test fails, or a live error occurs. A failed check is a valid trigger even with no live
crash.

## Inputs
- `verify-verdict` (fail) / test output / the live error signal — the **actual** behaviour.
- `spec` + `acceptance_criteria` + knowledge base — the **intended** behaviour.

## Workflow
1. Dispatch workers to map both worlds — intended vs actual behaviour (from code + the failure signal).
2. Judge where the divergence originates → root cause, with a confidence score. A cause the failing signal
   (test / error / mismatch) actually corroborates scores high; one the model only theorizes stays low.
3. confidence < threshold → call `research` (is this a known issue?) or request more tests **via a `plan-delta`
   to `refine`** (which routes the added tests through planner→execute); then re-run. **After a bounded retry
   budget with confidence still below threshold, stop and escalate** rather than spin.

## Rules
- Diagnoses only — it does **not** fix; the fix routes through `refine`.
- **Bounded, not infinite.** The confidence loop has a retry budget; exhausting it with no clear cause is an
  **escalation** to a human `checkpoint`, not another lap.

## Output
`debug-report` `{ symptom, cause, fix, avoid, confidence }` — the same format as the knowledge-base
`# Sessions` log.

## Route
→ `refine` (hand off the report) · **escalate → `checkpoint` (human)** when no clear cause survives the retry
budget.

## Calls
`research`.
