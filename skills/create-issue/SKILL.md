---
name: create-issue
description: Capture a problem, bug, or "do this later" without addressing it now, and open a real GitHub issue for it. The side-door into the loop — issues are later consumed by planner and closed by close-issue. Use for found bugs, deferred work, and every provisional spec item (tracked debt).
---

# Create-issue — the backlog side-door

Core principle: capture without addressing. Every issue is dual-tracked — a backlog entry for the loop and
a real GitHub issue for durable, external visibility — so nothing relies on in-memory state.

## When
A bug / unwanted behaviour surfaces, the user wants something noted for later, or a `provisional` spec item
needs a finalize-later ticket.

## Inputs
The problem/idea + its `kind` (bug|feature|debt), `severity`, and `source`.

## Workflow
1. File the backlog `issue` `{ title, kind, description, severity, source }`.
2. Open the matching GitHub issue (`gh issue create`), labelling from `kind` and `severity`.
3. Store the returned issue number on the backlog item as `github_ref`.

## Rules
- Capture only — never start fixing here.
- The backlog item stores only `github_ref`; open/closed state lives in GitHub, not mirrored locally.
- Opening the GitHub issue is an **outward action** — gated behind explicit human permission: the backlog
  entry is local and immediate, and unless `config.outward` pre-authorizes it, the `gh issue create` is **queued to
  `.workflow/outbox/`** and released later via a console `release` (on release, if the local item closed meanwhile →
  dropped, not mirrored). The loop never stalls on it.
- `severity` is set here (e.g. a universal-invariant-class bug); it feeds `prioritize`'s ordering, but the
  machine never self-preempts (pure queue).

## Output
A backlog `issue` carrying its `github_ref`, mirrored by a real GitHub issue.

## Route
→ backlog (side-door, from anywhere). The item is picked at the **next `prioritize`** — immediately if the loop
was `idle` (the idle→`prioritize` wake edge), otherwise at the next natural pick; it **never preempts** in-flight
work (pure queue).
