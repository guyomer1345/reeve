---
name: commit
description: Snapshot project state to git after a phase is documented — the durable checkpoint marker the loop resumes from. One commit per completed phase/item, written as a Conventional Commit linked back to its work item. Use at the tail of a completed item, after document.
---

# Commit — the durable checkpoint marker

Core principle: one commit per completed phase/item. The commit is what the loop resumes from and what the
handoff relies on, so its message is machine-readable loop state, not just prose.

## When
After `document`, per completed phase/item.

## Inputs
- the completed item's staged changes
- the `plan` / backlog item it traces back to (for the id) and any `issue` it resolves (for `github_ref`).

## Workflow
1. Stage the item's changes.
2. **Secret-scan the staged diff first.** Look for key prefixes, private-key headers, and
   `password` / `secret` / `api_key` / `token` set to a real (non-placeholder) literal. On a hit, **stop and
   escalate** — never commit the secret; once in history it lives there forever. (A guard hook re-checks this
   deterministically as the backstop — the step keeps it visible in the loop.)
3. **Run the mechanical gate.** Run the project's check runner (`.workflow/checks.sh --fix`) — it reformats,
   applies lint fixes, and strips a stale reference: the zero-judgment fixes a script can make safely. **Scope
   `--fix` to the item's staged files** — never a repo-wide sweep, which would pull unrelated drift into this
   atomic commit. Because these fixes are **zero-semantic** (format / lint / ref-strip), they need no re-verify;
   anything that would change behaviour is never auto-fixed. Re-stage and re-run in check mode. **Log what it
   fixed** (in the commit body or the `changelog`) — never silently mask a bad generator. Two failure paths from
   `--check`:
   - **a hard, non-auto-fixable error** (a type/lint error `--fix` couldn't resolve) → **do not proceed**: halt
     and **escalate to the orchestrator** — a real defect (debug/refine territory), not doc drift, and it must not
     ride a commit.
   - **doc↔code drift** a script *cannot* safely fix (a stale/contradictory/over-claimed doc, a missing owner, a
     symbol a doc still names that the code renamed) → file a `create-issue` ticket with the evidence and the
     affected element's `commitment`, `severity` set from it (a locked contradiction rides high; cosmetic drift
     sits low as `debt`), and let the commit proceed.
4. **Split out a prerequisite-repair, if any.** If the `changelog` recorded a `prerequisite-repair`
   divergence, commit that repair as its **own** commit first — typed and scanned like any other — so the
   stumbled-into fix stays reviewable and revertible apart from the planned change.
5. **Bookkeeping (before the commit captures it):** flip the backlog item's `done` state and rewrite
   `handoff.md`, so the completing commit records them (after any prerequisite-repair commit).
6. Write the planned change as a **Conventional Commit** — `type(scope): summary`, type from the item's `kind`
   (`bug → fix`, `feature → feat`, `debt → refactor`/`chore`; **default `chore` if `kind` is absent**).
7. Add linking trailers:
   - `Refs: item #<backlog-id>` — always.
   - `Closes: #<github-issue>` — when this item resolves a tracked issue.

## Rules
- One commit for the item's planned change; a recorded `prerequisite-repair` rides its **own** preceding
  commit (the only split). Never bundle otherwise-unrelated items.
- The message must trace back to the item — no bare "wip"/"fix" subjects.
- The mechanical gate auto-fixes only zero-judgment issues; it **never decides which side of a doc↔code
  contradiction is right** — that authority call is deferred to the loop (the filed ticket routes through
  `prioritize` → planning). The installed git pre-commit hook re-runs the same check as the
  outside-the-loop backstop.
- Bookkeeping rides the **planned** commit: the backlog item's done-flip and the `handoff.md` rewrite happen
  **before** it (after any prerequisite-repair commit), so the completing commit captures them. `close-issue`
  is the only post-commit tail step — **except in org mode**, below.
- **Org mode — the commit is not the hand-off; the BUNDLE is.** These commits live in a private clone with no
  push path, so they serve resume and nothing else. After committing, produce the item's review bundle:
  ```bash
  python3 .claude/scripts/review_bundle.py build <item-id>
  ```
  One item → one squashed diff → one commit the **human** authors, in their own checkout. Report what it prints
  verbatim: it names the files that cross and the upstream commit the work descends from. If it **REFUSES**,
  that is the boundary working — do not hand-edit the diff and do not work around it. The two refusals that
  mean something are a brain path in the output (the exclusion did not hold) and a loop reference written into
  one of the owner's own files (a comment citing `.workflow/…`, which is derived-IP plumbing their reviewer
  cannot interpret) — fix the *cause*, then rebuild. `close-issue` stays local-only here: never the owner's
  tracker.

## Output
A commit — the checkpoint marker. Its `Closes:` trailer names the issue that `close-issue` then closes.

## Route
→ `close-issue` (close the GitHub issue this item resolved), then the loop picks the next item.

## Calls
`create-issue` — when the mechanical gate surfaces semantic drift a script can't safely fix.

## References
Remote push and the branch lifecycle (the parallel-work merge/conflict extension) sit beyond this skill.
Commit is local and autonomous; **push is an outward action — gated behind explicit human permission**:
unless `config.outward` pre-authorizes it (`allow`), the loop **queues the push to `.workflow/outbox/` and keeps
committing** — a console `release` batch-approval fires it later (re-run through `guard.sh`). It never stalls on the
push.
