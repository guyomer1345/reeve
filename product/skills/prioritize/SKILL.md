---
name: prioritize
description: Order the backlog and emit the next set of independent work items — the ones that can safely run in parallel. Runs on every backlog change and whenever a phase completes. Pure queue — never preempts in-flight work; the machine finishes the current item, then re-picks.
---

# Prioritize — order the backlog, emit the next wave

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
3. Make eligible only items whose `depends_on` are already done.
4. Order eligible items by **urgency × dependency-readiness**.
5. **Group into a wave.** Walking from the top, gather the independent items that can run together — ones
   that don't collide (they touch disjoint files / modules / areas). A colliding or dependent item falls to
   a later wave. The overlap test is a conservative heuristic (when in doubt, serialize) and will sharpen as
   the collision model firms up.
6. Emit that set as the next **wave**. With a single agent a wave is one item (the degenerate case);
   fanning a wave out in parallel is the coordinator's job, still to come.

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
The next **wave** — the independent items to run together (+ the updated ordering). Serial execution runs a
wave of one.

## Route
→ the orchestrator runs each item in the wave through `planner` / its sub-loop. Build/test hooks run **once
per wave**, not once per item — parallel agents sharing a build otherwise collide on it.
