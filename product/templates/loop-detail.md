# Loop — the long-form detail

The on-demand half of the routing graph. [`loop.md`](loop.md) holds what the
orchestrator needs **every turn** — the routing table, the side doors and the boundary order — and is
budgeted as an always-loaded doc (`doc_budget.always_hard`, and its share of `always_total_hard`). This file holds the parts that are read
**when the situation arises**: the per-kind drain semantics, the forecast divergence check, the one-time
stack-wiring transition, and the maintenance-item contract. Each has a one-line pointer from `loop.md`.

Split out of `loop.md` when that file crossed its always-loaded hard budget, per the split-and-pointer
convention in [`memory-model.md`](../shared/memory-model.md). `loop.md § <name>` for any section below resolves
here — the name is the anchor, and the two files are one document.

## the boundary drain, by kind
The order itself is in `loop.md`. What each kind *does*, and the **anchor** that makes a repeat a no-op:

- **verdict** — resumes the parked ticket whose `token` matches; an unknown or already-closed token →
  dead-letter and surface it. The ticket is then closed with `bus.py unpark --id <ticket_id>`, which removes
  the record and re-projects `handoff.md`'s parked block. *Anchor:* the token itself (already closed →
  no-op) — and "closed" means the record is gone, which is why `unpark` is the step that makes the anchor real.
- **intake** — promoted into `backlog.md` through triage, stamped with the source message id. *Anchor:* that
  stamp (an item already carrying the id is already promoted → skip).
- **control** — reprioritize / pause, honored here only (non-preemptive; never mid-item). *Anchor:* none
  possible, so control ops are required to be idempotent.
- **release** — fires the named `outbox/` entries through `guard.sh`. *Anchor:* the entry's status (already
  fired → skip).
- **question** — run `answer`: reply from this project's own record and append the turn to
  `.workflow/thread/thread.json`. *Anchor:* that turn's source message id (a reply already carrying it →
  skip). **Last, and it advances nothing** — a question is a read, so it never delays a parked resume or a
  promotion, and it must never be promoted into the backlog on its own.

### recording what you applied
`python3 .claude/scripts/drain.py record --applied <id> [<id>...] [--dead-letter <id>="why"]`

Record each id **as soon as** its apply succeeds, **not** in one batch at the end. A crash between applying
and recording re-applies that message on restart, so the window should be as small as you can make it. Each
kind's effect is *also* idempotent, via the anchors above — that is what covers the window you cannot close.

`record` recomputes the watermark, prunes the consumed-set and republishes `handoff.md` durably. **It owns
the machine block in that file** — never hand-write, hand-edit or delete that block. The prose around it is
yours to rewrite freely.

### a returned credential never passes through the orchestrator
If `list` marks a message `sensitive`, **do not open the file.** Run
`python3 .claude/scripts/drain.py secret --id <id>`: it moves the value into the secret store, unlinks the
message and records it, without the value ever reaching a context window or a log. This is also the **one**
exception to "the consumer never deletes an inbox file" — a credential must not sit waiting on a janitor.

**The drain is split, and the split is the point.** *Which* messages are new, in what order they apply, what
the watermark is now, and what may be pruned are all a pure function of the inbox and `handoff.md` — that
half is `drain.py`'s (`list` → apply → `record`), and it is not re-derived by hand. *Applying* a message is
judgment — which ticket a verdict resumes, whether an ask is worth promoting and at what priority, how a
rejection routes — and that half stays with the orchestrator. `record` recomputes `consumed_through` (the
low-watermark: every message at or below it is consumed, so the bus may collect it) and **prunes the
consumed-set to ids above it**, which is what keeps `handoff.md` bounded — a cold start reads that file whole.

## the dispatch boundary
`loop.md` carries the rule. This is how the batch is actually formed, and why the failure direction is what it is.

**Form the batch, then dispatch it once.** Concurrency in this harness exists **only** for work dispatched in the
same turn — while a `Task` is in flight the orchestrator is blocked on its result and cannot interleave. So there
is no such thing as "using the wait": the lever is *not waiting alone in the first place*. Judged **at the
boundary, never per turn** — the answer only changes at a boundary, and re-deciding it every turn spends the
router's window (the scarcest thing in a drive) to re-derive a constant.

**Two kinds of member, neither subordinate to the other.**
- **Homogeneous — N `execute` items at once.** When several items' work genuinely does not overlap, running their
  `execute` calls concurrently is the plain intended use and the largest throughput win available. It is not a
  by-product of the rule below and must not be treated as one: the first question at a boundary is *how many
  independent items can run right now*, and the answer is allowed to be several.
- **Heterogeneous — never wait alone.** Before dispatching anything blocking, establish that there is genuinely
  nothing else worth doing, and put what there is in the same batch: research a **queued** item will need, a plan
  already unblocked. **`Viable` means the backlog already implies it** — not invented exploration. Unbounded
  speculative work is its own defect: it spends on output that may be discarded *and* pollutes the knowledge base
  with findings nobody asked for.

**Eligibility, and why it fails towards serial.** `check_wave_independence.py` decides, on the retained predicate:
**dependency-ready ∧ file-disjoint ∧ ¬1-hop code-map neighbour**. It reports, per rejected candidate, which clause
rejected it and against which other member — enough to act on without re-deriving it. A candidate whose
independence cannot be *proven* — no plan, no `files_touched`, no code map, an unparseable entry — is **not
eligible** and runs serially. **The burden of proof is on fanning out, never on staying serial:** a wrong "serial"
costs wall-clock, a wrong "parallel" costs correctness, and those are not comparable. Note this is narrower than
the predicate's original grading, which admitted a near-miss as a *flagged* start with raised integration rigor —
that concession made sense when the candidate would run **later**, and does not when it runs **concurrently**.

**Build once per wave.** The authoritative gate (`checks.sh --check`, the one a commit depends on) runs **once per
wave**, not once per member — N workers each triggering it collide on shared build state, caches, ports and
fixtures. That is distinct from a worker validating its own work inside its own worktree, which is legitimate and
may happen many times.

**Interleaving is the degenerate case, not a separate feature.** While an item is parked on a human verdict, the
next *independent* item starts rather than the loop idling — the same predicate, the same boundary, a batch of one.
A whole-loop park is simply "nothing eligible". Non-preemptive and item-level throughout: the human is still the
only thing that preempts.

## forecast divergence check
If the item being picked has a frozen `.workflow/forecasts/<id>.json`, run it **before starting work**:
```bash
python3 .claude/scripts/forecast.py reality .workflow/forecasts/<id>.json \
  --workflow-dir .workflow --check
```
A non-zero exit means the loop reached a node the approved chain never predicted — a **structural**
divergence. Do not walk on: re-run `create-forecast` for the remaining tail and re-show it, so the human is
re-consulted on a route they never agreed to. Reality is **derived** from the anchor table
(`schemas.md § the forecast ANCHOR TABLE`), so there is nothing to record and nothing to keep in step.

**This fires at the boundary ONLY, never mid-item** — that is what keeps `prioritize`'s non-preemption and
the never-stall rule intact, and it is why it is plain control-flow rather than a routing edge in the table.
A divergence found mid-item is not lost; it is picked up at the next boundary, which is the first moment the
loop is allowed to change its mind anyway.

## stack-wiring at tech_stack lock
A greenfield project starts with an empty product tree, so `/start` cannot detect a stack and writes only the
**coverage-only** `checks.env` + the unspecialized `rules/` baseline. The stack is chosen later, by
`decision-engineer` resolving the spec's `tech_stack` (a `TBD → decision-engineer` pointer). **The moment that
resolution flips `tech_stack` to `locked` while `.workflow/checks.env` still wires no stack gate, run the
stack-wiring step** (the stack-dependent half of `/start` step 6) before the next `execute`:
- fill `.workflow/checks.env` with the concrete `FMT_CHECK`/`LINT`/`TYPECHECK`/`TEST` (+ `FMT_FIX`/`LINT_FIX`)
  commands for the chosen stack, **scoped to `project_root`**;
- specialize each `rules/` `— enforced by:` tag to the concrete tool, and wire the enforcers (formatter,
  linter, typechecker, test runner, CI) — gap-fill, never clobber;
- add the stack's build-output paths to `.gitignore`; regenerate the code map.

This is a **one-time transition** (stack `unspecified/TBD → locked`), not a per-item step — it is the
orchestrator's to run, so the leaf skills stay in their lane. It is a positive fast-path: `checks.sh --check`
**fails the commit closed** whenever source exists under `project_root` with no stack gate wired, so skipping
this step cannot silently disarm the gate — it stops the loop loudly until the stack is wired.

**Skip this entirely when `checks.env` sets `STACK_GATE_NONE`** — a tree whose code must never be executed
here is *declared*, not unwired, and is already transitioned. Wiring commands into it re-arms `eval` on
foreign code; the runner refuses them and reports the conflict, so the attempt is noise, not a fix.

## maintenance items
`prioritize` injects a **maintenance item** on a threshold (§ `prioritize`): a *retention/size* threshold →
`document:audit` (bound the append-only tier); a *drift* threshold → `align` (reconcile spec/decisions/promises
vs code); a *doc-size* advisory → `doc-budget` (trim or split-and-pointer a context-loaded doc that has grown
past its role's budget — the hard tier is already enforced on the commit gate, so only advisories arrive here).
A maintenance item is **self-contained**: it runs its own pass and flows straight to `commit` — there is no
`planner`/`execute`/`verify`, because there is no product-code change to plan and no runtime behaviour to
verify — then `close-issue?` (skip: no linked issue) → `prioritize`. `align`'s *semantic* findings leave as
ordinary `create-issue` tickets (the side-door) and ride the normal queue; only its mechanical auto-fixes + the
new scan anchor ride this commit. The three thresholds are **decoupled** — memory pressure ≠ drift risk ≠ doc
size, and one shared threshold would make each of them fire for another's reason.

**No verify means no verdict — and from outside, a verify-free item and a *skipped* verify look identical.** So
the pass **stages a receipt in its own commit**: `.workflow/maintenance/<item-id>.json`
(`{ item, kind, summary }`, `kind` = the maintenance node that ran). That receipt is what the commit gate
accepts in place of a verdict; without it a maintenance item has **no legal commit at all**. It writes its own
and **deletes any earlier one**, so the directory holds only the current commit's receipt and the history of
past maintenance is that directory's git log. Never fake a trivial `pass: true` verdict instead — the console
reads that first line as "verify passed" (`shared/schemas.md § commit-receipt`).
