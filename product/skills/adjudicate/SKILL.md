---
name: adjudicate
description: Base procedure for any "gather competing views of reality, then judge" task. Not invoked directly — specialized by verify, debug, and decision-engineer. Reference it when building a capability that must compare realities and return a confidence-scored verdict.
---

# Adjudicate (base) — gather views → judge → confidence-gate

Core principle: the shared spine for every adjudication capability. An implementation supplies only **which
views** to gather and **how to judge**; the procedure and the I/O contract are fixed here.

## Inputs
A question + a view-set (which realities to gather) + a confidence threshold (from `config.run`, else the
implementation's shipped default — never an unsourced constant).

## Workflow
1. **Fan out** workers to gather each view independently — heavy context stays with the workers; they
   return thin summaries.
2. **Compare & judge** the views per the implementation's rubric.
3. **Score confidence — conjunction of signals.** A verdict that **gates** (fail / block) needs a
   **deterministic signal** corroborating it: a failing test, a thrown error, a lint/type violation, a
   tree/structure mismatch. A model-only finding with no such signal is **advisory / low-confidence** — it
   never hard-gates alone, so a lone AI hunch can't stall or whipsaw the loop.
4. **Gate:**
   - confidence ≥ threshold → emit the verdict.
   - confidence < threshold → gather more (more workers / more tests / `research`) and re-run.
   - views irreconcilable → escalate to the orchestrator (and the human if needed).

## Output
`{ verdict, confidence, escalate? }`.

## Implementations
- `verify` — views = {asked, done}; judge conformance (lean — may skip the fan-out).
- `debug` — views = {intended behaviour, actual behaviour}; judge root cause.
- `decision-engineer` — views = {option A, option B, …, market practice}; judge best fit.
