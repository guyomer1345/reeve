---
name: close-issue
description: Close the GitHub issue a completed item resolved, at the tail of the loop after commit. The mirror of create-issue. Use once an item has passed verify (and any qa checkpoint) and been committed.
---

# Close-issue — retire the resolved tracker

Core principle: an issue is closed only when its work is truly done — past `verify` (and any qa
`checkpoint`) and committed. Closing earlier (e.g. after `execute`) would retire work that may still fail.

## When
At item completion, immediately after `commit`.

## Inputs
- the completed item and its `issue.github_ref`
- the `commit` it landed in (for the SHA).

## Workflow
1. Close the item's own GitHub issue — `gh issue close <github_ref>`.
2. Comment the resolving commit SHA on the issue — **only once the commit is pushed** (the SHA is local until
   then; if the branch is unpushed, the comment waits for the push rather than referencing a SHA GitHub can't
   resolve).

## Rules
- Close only the completed item's own issue — 1:1. Detecting issues *incidentally* resolved by the change
  is out of scope for now.
- **GitHub owns open/closed state** — the backlog holds only `github_ref`, never a duplicated local state;
  closing writes no loop-bookkeeping, so this stays a clean post-commit step (the item-tail done-flip already
  rode the commit).
- Closing the GitHub issue is an **outward action** — gated behind explicit human permission: unless
  `config.outward` pre-authorizes it, the `gh issue close` is **queued to `.workflow/outbox/`** and released later via
  a console `release` (idempotent — already-closed → no-op). The loop never stalls on it.
- No `github_ref` (item came from steering, not an issue) → nothing to close; exit quietly.

## Output
The resolved GitHub issue closed and linked to the commit.

## Route
→ `prioritize` (the loop picks the next item).
