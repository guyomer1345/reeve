---
name: discuss
description: First step of any new intake — a new project or a new feature — before planning. Runs the requirements conversation with the user and produces the spec. Use when the user wants to start something new and the goal isn't yet captured as a written, testable spec.
---

# Discuss — requirements conversation → spec

Core principle: turn a user's intent into a written `spec`. Requirements only — **never decide the tech
stack or any engineering choice here.**

## When
The first capability in any new intake loop (project or feature), ahead of `create-demo` and `planner`.

## Inputs
The user's intent (conversation) + any existing `spec` to extend.

## Workflow
1. Let the user describe what they want; reflect it back until the idea is formed.
2. Drive the spec to completeness against the required fields:
   - **project (inception):** audience, runtime, purpose, screens, features, data_model, integrations,
     tech_stack.
   - **feature:** purpose, and visuals + acceptance criteria if it has a visible surface.
3. Tag every field with a **commitment level** from the enum — locked / provisional / unspecified. Default
   detail and styling to *provisional* (expected to change). Flow and scope are *provisional* too, but flag them
   the **lock-on-approval** set — the demo / reconcile checkpoint promotes them to `locked` (a later deviation is
   then a bug), while detail/styling stay provisional. Never emit a value outside the enum.
4. For any genuine engineering decision (stack, library, architecture), **do not decide** — record
   `TBD → decision-engineer` as a pointer. If the user states a firm preference, record it as `locked`.
5. **Track provisional debt on the no-demo path:** at spec-completion, if the sandbox gate will not fire (no
   demo for this item — the gate being `create-demo`'s `When` conditions, the single source), spawn a
   `create-issue` (kind=debt) for each field left `provisional`, so no deferred decision is silently lost. (When
   a demo does run, `create-demo` files these after approval instead — exactly one path files, never both.)

## Rules
- Requirements only — never resolve an engineering decision; leave a `TBD → decision-engineer` pointer.

## Output
A `spec`, every field commitment-tagged, with `TBD → decision-engineer` pointers where decisions are open.

## Route
→ the sandbox-gate check (`create-demo`), then `planner`. Exit when every required field is filled or
explicitly provisional/TBD.

## Calls
`create-issue` (kind=debt) — for `provisional` fields on the no-demo path.
