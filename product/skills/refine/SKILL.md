---
name: refine
description: Decide what to do with a verify failure, a debug finding, a gating review finding, or a newly-arisen need, and route the correction back through planner→execute. Never edits code itself — it preserves execute's zero-decision discipline by funnelling every change through the normal plan→execute→verify pipe.
---

# Refine — the correction router

Core principle: closes the loop after something comes back wrong or a new need appears — by routing, never
by editing code, so `execute` stays decision-free.

## When
A `debug-report` (the root cause of a verify/qa failure), a **gating `review-report`**, or a new need that arose
from the just-built code.

## Inputs
A `debug-report`, a gating `review-report`, or a stated new need. A `verify`/qa failure reaches `refine` **via
`debug`** (as a `debug-report`), never as a raw `verify-verdict` — the topology routes the failure through
root-cause first.

**A gating `review-report` comes here DIRECTLY, and that asymmetry is the point.** `debug` exists to find a
cause from a symptom; a gating review finding has already cleared the demonstration bar — it names the file,
the line, and the input that breaks it — so it *is* the cause. Sending it through `debug` would re-derive what
the reviewer handed over. An **advisory** finding is not a trigger at all: it rides the report, and one that
keeps recurring belongs in `create-issue`, never here.

## Workflow
1. Read the finding.
2. Decide the corrective action.
3. Emit a **`plan-delta`** (see `schemas.md`) → `planner` (plan-one) → `execute` → `verify`. Loop until verify
   passes.

## Rules
- Touches **no code** itself. Every change flows through the disciplined plan → execute → verify pipe.

## Output
A plan-delta handed to `planner`.

## Route
→ `planner` (plan-one) → `execute` → `verify`; loop until re-verified pass.
A correction that came from `review` re-enters `review` after `verify` passes, and that loop is **capped**
(`config.review.max_rounds`) — at the cap the orchestrator escalates to a `checkpoint` rather than routing a
further delta. An item that cannot be got right in N rounds is a design question, not a defect.
