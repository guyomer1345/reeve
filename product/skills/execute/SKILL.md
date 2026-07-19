---
name: execute
description: Run a plan file step by step and record exactly what was done. Makes no decisions of its own — if it hits anything undecided, it stops and escalates. Use to carry out an approved plan, never to design or choose.
---

# Execute — run a plan, decide nothing

Core principle: the **keystone** of the loop — because execute decides nothing, `verify` and `document` can
trust the changelog.

## Inputs
A `plan` (goal, ordered verifiable `steps`, `acceptance_criteria`).

## Workflow
1. **Guard destructive work first.** If the `plan`'s `risk_class` is destructive (`data-destructive` /
   `prod-touching`), refuse to run the destructive step unless the plan carries a `backup` block — run and
   verify the backup, record it in the `changelog`, *then* proceed. No verified backup → stop and escalate;
   an unattended executor never runs an irreversible op without a proven rollback.
2. Work the plan's `steps` in order — including **running each `artifact` criterion's discharging test/check**
   (the `plan` named them), so `verify` reads a real signal rather than passing vacuously.
3. Record every action in the `changelog` (`step, files, result`) — a failing discharge is a recorded result
   (it routes `verify` → `debug`), never a silent skip.
4. **Handle any divergence by tier** — never silently:
   - **cosmetic** (a helper moved, line drift): adapt, record it, continue.
   - **prerequisite-repair** (an in-scope-adjacent fix the plan didn't name): apply it, record it as a
     divergence tagged `prerequisite-repair`, continue. It rides its **own commit** at the item tail so the
     stumbled-into fix never hides inside the planned change.
   - **structural** (the plan assumes something untrue): stop and escalate — this *is* the decision boundary.

## Rules
- **Zero autonomous decisions.** A choice the plan didn't make is a blocker, not a judgement call.
- **Escalate, never improvise.** On a blocker (an undecided option, missing info), stop and raise it up —
  the orchestrator routes it (e.g. to `decision-engineer`), then execution resumes from the resolved plan.
- **Stay in its lane.** Execute writes code per the plan; it does **not** update `docs/knowledge/` or the spec
  (that's `document`) and never chooses anything (that's `planner` / `decision-engineer`).

## Output
A `changelog` referencing the plan.

## Route
→ `verify`. On a blocker: raise it up and pause until the orchestrator resolves it, then resume.
