---
name: prioritize
description: Order the backlog and emit the next batch of items to plan. Runs on every backlog change and whenever a phase completes. Pure queue — never preempts in-flight work; the machine finishes the current item, then re-picks. It does not decide what may run in parallel; `check_wave_independence.py` owns that.
---

# Prioritize — order the backlog, emit the next batch to plan

Core principle: a **pure queue** — the machine never preempts itself; it finishes the current item, then
re-picks.

## When
On any backlog change (a new roadmap, a new issue) and whenever a phase/item completes.

## Inputs
The backlog (items with `depends_on`, `kind`, `severity`).

## Workflow
1. **GC the queue first:** drop done items so `backlog.md` stays a live *open* queue, not a ledger — **any entry
   `commit` flipped done** (roadmap items *and* local `issue` entries, which is every issue carrying no
   `github_ref`: a mirrored issue's open/closed state lives in GitHub, a local one's lives in its own done-flip),
   and `issue` entries whose `github_ref` **is** closed on GitHub. Both rules matter: local issues are not a
   greenfield edge case — `/rebind` files machine-move losses as exactly that shape, and an entry no rule
   collects is permanent sediment.
2. **Schedule maintenance — three decoupled triggers** (memory pressure ≠ drift risk ≠ doc size, so separate
   thresholds — a shared one would make any of them fire for the wrong reason):
   - *Retention/size* → inject a `document:audit` item when a threshold retention can actually **reduce** is
     tripped — a node's `# Sessions` exceeds `sessions_k` **by a margin** (retention caps back to `sessions_k`,
     leaving headroom so the next single append doesn't immediately re-trip), **superseded** `docs/decisions/`
     bodies awaiting GC > `decisions_superseded_n`, or closed+promoted `items/` > `items_closed_m` — or every
     `every_p_items` items. Count the *superseded* decisions, not the active ones: GC removes superseded bodies,
     so that is the count the audit lowers — an active count would never drop and would thrash.
   - *Drift* → inject an `align` item: `config.align.every_n_commits` commits since the last scan anchor
     (`.workflow/align/anchor.json`'s `base_sha`), or a phase/wave boundary just closed.
   - *Doc size* → inject a `doc-budget` item every `config.doc_budget.every_p_items` items, **when
     `python3 .claude/scripts/check_doc_budget.py --report` actually reports an advisory** — the finding *is*
     the threshold, so there is no second number to tune. Only the ADVISORY tier reaches here: the hard tier
     already fails `checks.sh` on every commit, so by the time you are scheduling, the unreadable-file case is
     impossible. Inject **at most one open `doc-budget` item at a time** (an over-size doc stays over-size until
     someone trims it, and re-filing it every P items would be sediment, not a signal). The item's work is a
     **trim or a split-and-pointer** — never a deletion of content that carries intent, and never an automatic
     rewrite: splitting prose coherently is judgment, which is exactly why this is a ticket and not a script.
     `memory-model.md` owns the convention and the head marker.
   All three are self-contained maintenance items (`loop.md` § Maintenance items) — they run their pass and flow
   straight to `commit`, never through `planner`/`execute`/`verify`. Because of that each **stages a maintenance
   receipt** (`.workflow/maintenance/<item-id>.json`) in its own commit: with no verdict to show, that receipt is
   the only thing standing between a verify-free item and a commit gate that reads it as an unverified one.
3. **Check the goal is still reachable, when one is active.** If `.workflow/goal.json` exists, run
   `python3 .claude/scripts/converge.py status --workflow-dir .workflow`. Anything it reports **`unbound`** is a
   goal acceptance that *no plan anywhere attempts* — the goal cannot be met as currently queued, and this is the
   one finding available **before** the work is spent rather than after five sessions of it. File it with
   `create-issue` (kind `feature`) so it enters the queue as ordinary work; do not invent the item's content
   here — naming the gap is queue work, filling it is `discuss`/`planner`'s. Report `unbound` at most once per
   acceptance: it stays unbound until something plans it, and re-filing every pass would be sediment, not a
   signal — the same rule the `doc-budget` trigger above runs on.
4. Make eligible only items whose `depends_on` are already done.
5. Order eligible items by **urgency × dependency-readiness**.
6. **Emit the PLAN BATCH: the head of the queue, up to `config.run.wave.plan_max`**, skipping anything already
   planned, in flight or parked. Straight down the order from step 5 — no separability judgement here, for two
   reasons worth stating because the obvious design is to make one:
   - **You have nothing to judge with.** A backlog row carries `{title, kind, severity, depends_on}` and *no
     file scope*. Scope first exists when a plan exists, which is the whole reason planning has to run ahead of
     dispatch at all. Guessing an area from a title would be a judgement dressed as a filter.
   - **Planning far from dispatch creates staleness debt.** A plan is durable, so a surplus plan is not waste —
     but a plan for an item ten waves out gets refreshed over and over as the tree moves beneath it, and
     eventually hits `refresh_max` and is re-planned from scratch. Head-of-queue keeps each plan close to the
     moment it is spent.
   Surplus is expected and is the mechanism, not an overrun: unbuilt items keep their plans and walk into the
   next wave already eligible, so the pool of provably-independent work grows monotonically. Only the first
   wave pays full price.
7. **Do not claim these items are independent — you cannot know that yet, and something else now does.**
   `check_wave_independence.py` computes it from the real plans once they exist, and it is the only owner of
   that answer. What this step emits is a batch that is *worth planning*; what may then be dispatched together
   is the gate's call and is routinely a subset. (This step used to gather "the independent items that can run
   together" on an admitted conservative heuristic. That was one fact with two owners the moment the gate
   shipped.)

## Rules
- **Never preempt in-flight work.** A bug found *during* the current item is handled inside that item's own
  `verify → debug → refine` loop — it is not a competing backlog item, so it never reaches prioritize as an
  interrupt.
- The only preempt path is the **human's manual override** (steering: "do this now") — a human action, not
  an autonomous scheduling decision.
- **Drift tickets ride the normal queue.** A doc↔code drift the commit gate or a periodic scan couldn't
  auto-fix arrives as an ordinary `issue`; order it by the same urgency × dependency rule. Its `severity`
  already reflects the affected element's `commitment` (a locked contradiction sorts high so it isn't starved;
  cosmetic drift sits low as `debt`), so no special-casing.

## Output
The **plan batch** — the next `plan_max` items to plan, in queue order (+ the updated ordering). It is a
candidate set, never a promise of concurrency.

## Route
→ the orchestrator plans the batch, then runs `check_wave_independence.py` to learn which of the resulting
plans may be dispatched together. The authoritative build/test gate runs **once per wave**, not once per item —
parallel agents sharing a build otherwise collide on it (one build cache, one set of ports, one set of
fixtures).

**That is now a mechanism, not a convention you have to remember.** `checks.sh --check` takes the **wave build
slot** before it runs the stack commands: an `flock` on the repo's common git dir — the one path every worktree
resolves to identically — so two authoritative gates never run at once, plus a memo keyed on `state.json`'s
`wave` + a digest of the tree, so a tree state this wave already passed is not gated a second time. Every
unknown (no wave id, no lock, an unreadable memo) falls the same way: it builds. An agent running the project's
tests inside its own worktree to check **its own** work is a different act and is not governed by this at all.
→ `shared/schemas.md § wave-build slot`.
