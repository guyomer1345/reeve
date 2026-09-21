---
name: reckon
description: Stop driving every N commits and ask whether the work is actually moving the goal — does the last window progress it, were we scoped on the wrong thing, are we looping around a problem, or is the goal itself not anchored enough to progress against. A maintenance item injected by `prioritize` on its own commit clock, deliberately independent of every convergence signal, because those are computed against a goal they assume is sound. Routes: re-prioritize, correct, or park a `steer` when the goal is the broken thing. Runs its pass, stages a receipt, flows to `commit`.
---

# Reckon — does the work still point at the goal

Core principle: the numbers are `reckon.py`'s and are not yours to soften. You explain them, decide
what to do, and route — the one verdict you may not reach is *"progressing"* when nothing moved.

## When
Injected by `prioritize` when `python3 .claude/scripts/reckon.py due --project-root .` exits 0 —
every `config.reckon.every_n_commits` commits, default **5**.

**Why a commit clock and not the convergence signals.** Every other progress measure in this
package is computed from the loop's own bookkeeping, *against a goal it assumes is sound*. When the
goal's acceptance is unreachable, the stall streak, the discharge fraction and the report are all
faithfully measuring a fiction — and anything triggered BY them inherits the fiction and cannot
report it. This has to be able to audit the measuring apparatus, so its trigger sits outside it.
**Measured, not felt:** two live projects ran at 1.56 and 1.60 commits per closed item, so five
commits is about three items; the drift run their owner corrected by hand was five items (~8
commits), so firing at five lands two items ahead of where a person caught it.

## Inputs
`reckon.py measure --project-root . --json` — the whole objective reading. Then, and only to
explain what it found: the `goal`, the window's items and their changelogs, `docs/spec.md`
(including its `## Charter` constraints), `backlog.md`.

## Workflow
1. **Take the reading first, before forming any view.**
   ```bash
   python3 .claude/scripts/reckon.py measure --project-root . --json
   ```
   It gives you `verdict` · `commits` · `items_closed` · `acceptance_moved` · `unbound` ·
   `planned` · `discharged` · `commits_per_item` · `findings[]`.
2. **Answer the four questions in this order**, using the numbers as the evidence and the
   artifacts only to explain them:
   - *Is the question well-formed?* — `unbound` first. Acceptance nothing anywhere plans to
     discharge means **this goal cannot be met as currently planned**, however well the building
     is going. Check each unbound criterion: is it unreachable because nobody has planned it yet,
     or because it cannot be tested as written?
   - *Did the window move it?* — `acceptance_moved`. Empty is the floor.
   - *Were we scoped on the wrong thing?* — items in the window that bound no acceptance. Read
     their changelogs: incidental work is legitimate, a window made entirely of it is not.
   - *Are we looping?* — `commits_per_item` against the 1.6 baseline, plus repeated corrections
     over one file or item.
3. **Write the reckoning into the receipt** (Output) — the numbers, the answer to each question,
   and what you are doing about it. One short paragraph per question; this is a record, not a
   report to a human.
4. **Route** (below), then flow to `commit`.

## Rules
- **You may never upgrade the verdict.** `reckon.py` computes `no-progress` from zero acceptance
  moved; that is arithmetic, and a pass that talks itself into *"but the groundwork was valuable"*
  is the exact drift this exists to catch. You may DOWNGRADE (call a `progressing` window
  churning) — judgement escalates above the floor, never below it.
- **Never edit the goal.** Changing what acceptance demands is goal-affecting by the autonomy
  floor, so it goes to the human as a proposal, not as a change you made and mentioned.
- **`unbound` already has a cheap consumer and you are not it.** `prioritize` step 3 files an unbound
  acceptance as a backlog row — *has anyone planned this yet*. Yours is the different question: *can this
  acceptance be discharged at all as written*. Do not re-file what it files; answer the question it cannot.
- **Never open work.** You do not plan, dispatch or fix; you re-order and route. Corrections go
  through `refine` → `planner` like everything else.
- **Bounded.** One pass over the window's artifacts, not a re-read of the project. If the window
  is large, read the ledger and the changelogs and stop there.
- **Say when it is fine.** A `progressing` verdict writes its receipt and says nothing else — no
  checkpoint, no ticket, no interruption. A pass that always finds something is one nobody reads.

## Output
A **`commit-receipt`** at `.workflow/maintenance/reckon-<n>.json` — `{ item, kind: reckon,
summary }` — carrying the reading and the four answers. It is also **the anchor the next window
opens at**: `reckon.py` finds it by the commit that ADDED it, so the receipt is what makes the
clock self-measuring rather than a counter somebody has to keep.
**The filename stem MUST begin with `reckon-`** (and equal `item`, as every receipt must). That
prefix is the contract between this skill and the script's `--diff-filter=A` search: a receipt
named anything else is not found, the window silently falls back to the goal's first commit, and
it then grows without bound — the clock keeps firing while measuring the wrong span.

## Route
- **`progressing`** → `commit`. Silent.
- **`churning`** → the loop's own call: `debug` or `decision-engineer` on the thing being circled,
  or get the evidence by running it (`run:` discharge). Then `commit`.
- **`no-progress` / scoped wrong** → re-prioritize: order the backlog so the next wave binds
  acceptance, and `create-issue` for work that should be dropped rather than carried. Then
  `commit`.
- **`goal-unreachable`** → **`checkpoint` (`kind: steer`)**, and this is the only outcome that
  reaches a human. Carry the specific unbound criteria and a **proposed sharpening of each** —
  bring the product question, never the verification. Changing goal acceptance is the product
  owner's by the autonomy floor (`shared/schemas.md § the autonomy floor`), and per the parked-item
  rule the loop keeps building whatever is still eligible while they answer.
- **`no-goal`** → the goal demand already exists on the turn ladder; park a `steer` naming that the
  drive has no stop-when-done condition.

## Calls
`create-issue` — for work the reckoning says should be dropped or re-scoped.
