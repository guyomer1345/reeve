# Loop — the routing graph
<!-- doc-budget: detail split -> loop-detail.md -->

The orchestrator reads this to route. **Topology is fixed** (it changes only with the package); the live
position lives in `state.json`. Nodes are skills/agents; edges are followed on a node's output.
Read **before every turn**, so it is budgeted always-loaded and carries only what routing needs: the long-form
detail lives in **`loop-detail.md`**, pointed to from each section below — read it when that situation arises.

## Routing table
| node | on output | next |
|---|---|---|
| `charter` *(greenfield entry, ahead of `discuss`)* | founding conversation settled → falsifiable `locked` constraints | `discuss` |
| `charter` | no human present — nothing may be `locked` | escalate → `checkpoint` (steer) |
| `ingest` *(brownfield entry — `/start` routes here)* | knowledge graph + reconstructed spec built | `checkpoint:reconcile` |
| `checkpoint:reconcile` | reconstructed spec confirmed | `charter` → `prioritize` |
| `checkpoint:reconcile` | corrections needed | `ingest` (re-run) / `discuss` |
| `discuss` | spec drafted | `create-forecast?` (forecast gate) |
| `create-forecast` | approved, or the gate never triggered | `create-demo?` (sandbox gate) |
| `create-demo` | approved, or the gate never triggered | `planner:decompose` |
| `planner:decompose` | roadmap → backlog + goal (receipt staged) | `commit` |
| `prioritize` | plan batch emitted | `planner:plan-one` (per item in the batch) |
| `prioritize` | maintenance due (retention · drift · doc-size · the reckon clock) | `document:audit` / `align` / `doc-budget` / `reckon` |
| `prioritize` | backlog empty | `idle` (await steering) |
| `idle` | steering arrives / new backlog item (a `create-issue` side-door) | `prioritize` (re-pick) |
| `planner:plan-one` | open decisions | `decision-engineer` → back to `planner:plan-one` |
| `planner:plan-one` | plan ready, per-item sandbox gate fires (visible surface, underdetermined) | `create-demo` (per item) |
| `planner:plan-one` | plan ready, no per-item demo | `execute` |
| `decision-engineer` | needs evidence | `research` → back to `decision-engineer` |
| `create-demo` | demo approved (per-item checkpoint pass) | `execute` |
| `create-demo` | refine cap hit (`config.demo.max_refine_rounds`) — never auto-proceed | escalate → `discuss` (live realignment, carrying the refine history) |
| `execute` | changelog | `verify` |
| `execute` | structural divergence (the plan is wrong) | `planner:plan-one` (re-plan) |
| *any worker* | `status: continue` | **re-dispatch the SAME node** with the scratch path it named |
| *any worker* | `status: question` / `blocked` | `decision-engineer` / `refine` (`debug` if behaviour ≠ intent) |
| `verify` | **pass** | `review?` |
| `verify` | **fail** | `debug` |
| `review` | nothing demonstrable (or no code changed → skip) | `checkpoint:qa?` |
| `review` | a demonstrable defect · cap hit | `refine` · escalate → `checkpoint` |
| `debug` | root cause | `refine` |
| `debug` | confidence stays < threshold after retries (no clear cause) | escalate → `checkpoint` (human) |
| `refine` | correction plan | `planner:plan-one` → `execute` |
| `checkpoint:qa` | pass · no human-qa criteria → skip · **deferred (`blocking: false`) → park and carry on** | `document` |
| `checkpoint:qa` | fail (a deferred one fails at a later drain, after the commit) | `debug` |
| `checkpoint:demo` | approve | lock the spec state → **prune the demo** → continue (`planner:decompose` at inception · `execute` per-item) |
| `checkpoint:demo` | changes | `create-demo` (refine the sandbox / spec — **keep** the bundle + its refine count) |
| `checkpoint:demo` | reject | `discuss` (→ **prune the demo**) |
| `checkpoint:forecast` | approve | **freeze the forecast** (before the unpark) → continue (`create-demo?`) |
| `checkpoint:forecast` | changes | `create-forecast` (re-forecast with the edits — the record stays a draft) |
| `checkpoint:forecast` | reject | `discuss` |
| `checkpoint:setup` | fail (couldn't complete) | re-attempt `checkpoint` (re-guides via setup-guide) / escalate to human |
| `checkpoint:spec` | approve / changes · reject | apply the delta → **record the receipt** → resume · discard → `refine` |
| `document` | knowledge + Sessions updated | `commit` |
| `commit` | snapshot made | `close-issue?` |
| `close-issue` | issue closed (or no linked issue → skip) | `converge?` (if a goal) → `prioritize` |
| `converge` | `met`, or `STALLED` (see `converge.py`) | `idle` (await steering) — **never** retry the item |
| `document:audit` | retention pass done (changes + receipt staged) | `commit` |
| `align` | scan done (tickets filed, fixes + receipt staged, anchor written) | `commit` |
| `doc-budget` | over-budget doc trimmed or split-and-pointered (receipt staged) | `commit` |
| `reckon` | the window judged (receipt staged) | `commit` — re-prioritize or `debug` first; the GOAL unreachable ⇒ escalate → `checkpoint` (steer) |

<!-- Every side door must be named ON the "Side doors" line: the linter reads only that line, so a
     door introduced on a continuation line is silently unrouted. -->
Side doors (callable from anywhere): `create-issue` → backlog · `research` (service) · `answer` · `status`.
The last two enter from the boundary drain, never from a node: neither advances anything, so neither has an edge.

## The autonomy boundary — who owns the decision
Take every decision that does not change the goal; **route anything that may**. Before acting on one that could
change what the project is committed to, run
`python3 .claude/scripts/check_autonomy_floor.py --project-root .` — **exit 1 ⇒ `checkpoint` (human), whatever
your own read.** Judgment may escalate **above** that floor, never below it; it is a minimum, not a cap.
→ **Why, and what the floor cannot see: `shared/schemas.md § the autonomy floor`** (the standing directive lives
in `.workflow/directives.md`).

**The gated rows (`create-demo?` · `review?`) are the router's call, before any dispatch** — default **no
demo**, per work-item; **`review?` runs whenever the item's diff changed code**. Each gate's conditions live
once in its own capability; read them there.

## Dispatch boundary — form the batch, and never wait alone
Concurrency exists only for work dispatched **together**, so the batch is the speed lever. Before any
long-running dispatch: form the **largest legal batch** and send it in **one turn**. **Never dispatch a blocking
call by itself while other viable work exists.** Both `execute` items that do not overlap and other viable work
(research a queued item needs, an unblocked plan) go in the same batch.

**Eligibility is not a judgement call.** Run `python3 .claude/scripts/check_wave_independence.py --record`:
only its batch may fan out, a rejected candidate **runs serially**, and missing evidence never reads as
"probably fine". It judges plan **freshness** too — a plan whose tree moved under it is read pessimistically and
must go through `planner:refresh` before dispatch; re-run the gate on the batch afterwards.
**`--record` is not optional.** It publishes the verdict, and `PreToolUse` **refuses an `execute`** that no
verdict at this commit covers — including one sent alone while the gate said N could run together.

→ **Batch formation, what counts as viable, build-once-per-wave, and interleaving while one item is parked:
`loop-detail.md § the dispatch boundary`.**

## Scheduler boundary — the inbox drain
Between items (and before any pick) the orchestrator **drains `.workflow/inbox/`** — the console's typed
messages to the loop. **Plain control-flow, not a node**: no skill runs and no edge is followed, so it appears
nowhere in the table above. Order within one boundary:

`drain (skip already-consumed ids) → apply control → resume a ready-parked ticket (oldest verdict first, +aging)
→ promote intake → start-new → fire release → answer questions → sleep`

A parked ticket resumes **only** via this drain. The consumer **never deletes** an inbox file — the bus owns
that directory and collects consumed messages itself.

→ **What each kind does and its idempotence anchor, and why the drain is split between `drain.py` and
judgment: `loop-detail.md § the boundary drain, by kind`.**

**Read the context gate here too** — `python3 .claude/scripts/context_band.py --gate --json`.
`handoff-at-boundary` ⇒ finish the drain, write `handoff.md`, then stop picking. `handoff-now` ⇒ write it
**now**, before anything else, and say a `/clear` is safe. **Ending a turn is an EVENT, not a default:**
unattended it needs a reason (parked AND nothing else eligible · met · stalled · paused · `idle`) and leaves
the report, `status_report.py` pasted whole; anything else is resolved here. `Stop` hooks enforce all three, so
skipping one is not silent — but they fire mid-turn, where a boundary is cheaper and truer.
→ **`loop-detail.md § the context gate` · `§ the turn gate`.**

→ **If the item being picked has a frozen `.workflow/forecasts/<id>.json`, run the divergence check before
starting work — boundary only, never mid-item: `loop-detail.md § forecast divergence check`.**

## Stack-wiring at tech_stack lock
Greenfield starts with no stack (`/start` writes a coverage-only `checks.env`). When `decision-engineer` flips
`tech_stack` to `locked` the orchestrator runs the **one-time** transition — gate commands, `rules/` tags,
enforcers — before the next `execute`.

→ **Steps, why skipping cannot silently disarm the gate, and `STACK_GATE_NONE`:
`loop-detail.md § stack-wiring at tech_stack lock`.**

## Non-item commits — the receipt
A maintenance item has no `planner`/`execute`/`verify` behind it, so no verdict; nor has `planner:decompose`.
**Every commit with no item behind it stages a receipt** (`.workflow/maintenance/<item-id>.json`, `kind` = the
motion) — without one there is no legal commit, and never fake a `pass: true` verdict instead.

→ **The contract, who stages inception's, and why the thresholds are decoupled:
`loop-detail.md § maintenance items`.**

## Item-complete tail
The tail is the table's. Not in it: the backlog done-flip and the `handoff.md` rewrite happen **before**
`commit` (it captures them); `close-issue` is the only post-commit step.
