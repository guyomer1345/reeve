# Loop — the routing graph
<!-- doc-budget: detail split -> loop-detail.md -->

The orchestrator reads this to route. **Topology is fixed** (it changes only with the package);
the live position lives in `state.json`. Nodes are skills/agents; edges are followed on a node's output.

This file is read **before every turn**, so it is budgeted as an always-loaded doc and carries only what
routing needs. The long-form detail — per-kind drain semantics, the forecast divergence check, the
stack-wiring transition, the maintenance-item contract — lives in **`loop-detail.md`**, pointed to
from each section below. Read it when that situation arises, not every turn.

## Routing table
| node | on output | next |
|---|---|---|
| `ingest` *(brownfield entry — `/start` routes here)* | knowledge graph + reconstructed spec built | `checkpoint:reconcile` |
| `checkpoint:reconcile` | reconstructed spec confirmed | `prioritize` |
| `checkpoint:reconcile` | corrections needed | `ingest` (re-run) / `discuss` |
| `discuss` | spec drafted | `create-forecast?` (forecast gate) |
| `create-forecast` | forecast approved (checkpoint pass) | `create-demo?` (sandbox gate) |
| `create-forecast` | gate not triggered | `create-demo?` (sandbox gate) |
| `create-demo` | demo approved (checkpoint pass) | `planner:decompose` |
| `create-demo` | gate not triggered | `planner:decompose` |
| `planner:decompose` | roadmap → backlog | `prioritize` |
| `prioritize` | plan batch emitted | `planner:plan-one` (per item in the batch) |
| `prioritize` | maintenance due (retention, drift, or doc-size threshold) | `document:audit` / `align` / `doc-budget` |
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
| `verify` | **pass** | `checkpoint:qa?` |
| `verify` | **fail** | `debug` |
| `debug` | root cause | `refine` |
| `debug` | confidence stays < threshold after retries (no clear cause) | escalate → `checkpoint` (human) |
| `refine` | correction plan | `planner:plan-one` → `execute` |
| `checkpoint:qa` | pass (or no human-qa criteria → skip) | `document` |
| `checkpoint:qa` | fail | `debug` |
| `checkpoint:demo` | approve | lock the spec state → **prune the demo** → continue (`planner:decompose` at inception · `execute` per-item) |
| `checkpoint:demo` | changes | `create-demo` (refine the sandbox / spec — **keep** the bundle + its refine count) |
| `checkpoint:demo` | reject | `discuss` (→ **prune the demo**) |
| `checkpoint:forecast` | approve | **freeze the forecast** (before the unpark) → continue (`create-demo?`) |
| `checkpoint:forecast` | changes | `create-forecast` (re-forecast with the edits — the record stays a draft) |
| `checkpoint:forecast` | reject | `discuss` |
| `checkpoint:setup` | fail (couldn't complete) | re-attempt `checkpoint` (re-guides via setup-guide) / escalate to human |
| `document` | knowledge + Sessions updated | `commit` |
| `commit` | snapshot made | `close-issue?` |
| `close-issue` | issue closed (or no linked issue → skip) | `prioritize` (next item) |
| `document:audit` | retention pass done (changes + receipt staged) | `commit` |
| `align` | scan done (tickets filed via `create-issue`, fixes + receipt staged, anchor written) | `commit` |
| `doc-budget` | over-budget doc trimmed or split-and-pointered (changes + receipt staged) | `commit` |

<!-- Every side door must be named ON the line below: the contract linter reads only the line that
     starts with "Side doors", so a door introduced on a continuation line is silently unrouted. -->
Side doors (callable from anywhere): `create-issue` → backlog · `research` (service) · `answer` · `status`.
`answer` is entered from the boundary drain, never from a node — a question advances nothing, so it has no
edge. `status` is the same shape: a pure read of where the project is, mutating nothing and returning to
wherever it was called from.

## The autonomy boundary — who owns the decision
Take every decision that does not change the goal; **route anything that may**. Before acting on a decision that
could change what the project is committed to, run
`python3 .claude/scripts/check_autonomy_floor.py --project-root .` — **exit 1 ⇒ `checkpoint` (human), regardless
of your own read.** Judgment may escalate **above** that floor, never below it; it is a minimum, not a cap.
→ **Why, and what the floor cannot see: `shared/schemas.md § the autonomy floor`** (the standing directive lives
in `.workflow/directives.md`).

**The gated rows (`create-demo?`) are the router's call, before any dispatch** — default **no demo**, decided
per work-item. Its three conditions live once in the `create-demo` capability's *sandbox gate* section: read
them there (this file is read every turn; that one is not).

## Dispatch boundary — form the batch, and never wait alone
Concurrency exists only for work dispatched **together**, so the batch is the speed lever. Before any
long-running dispatch: form the **largest legal batch** and send it in **one turn**. **Never dispatch a blocking
call by itself while other viable work exists.** Both `execute` items that do not overlap and other viable work
(research a queued item needs, an unblocked plan) go in the same batch — neither is subordinate.

**Eligibility is not a judgement call.** Run `python3 .claude/scripts/check_wave_independence.py`: only its batch
may fan out, a rejected candidate **runs serially**, and missing evidence never reads as "probably fine". It
judges plan **freshness** too — a plan whose tree moved under it is read pessimistically and must go through
`planner:refresh` before dispatch; re-run the gate on the batch afterwards.

→ **Batch formation, what counts as viable, build-once-per-wave, and interleaving while one item is parked:
`loop-detail.md § the dispatch boundary`.**

## Scheduler boundary — the inbox drain
Between items (and before any pick) the orchestrator **drains `.workflow/inbox/`** — the console's typed
messages to the loop. This is **plain control-flow, not a node**: no skill runs and no edge is followed, so it
appears nowhere in the table above. Order within one boundary:

`drain (skip already-consumed ids) → apply control → resume a ready-parked ticket (oldest verdict first, +aging)
→ promote intake → start-new → fire release → answer questions → sleep`

A parked ticket resumes **only** via this drain. The consumer **never deletes** an inbox file (the bus owns
that directory and collects consumed messages itself).

→ **What each kind does and its idempotence anchor, and why the drain is split between `drain.py` and
judgment: `loop-detail.md § the boundary drain, by kind`.**

→ **If the item being picked has a frozen `.workflow/forecasts/<id>.json`, run the divergence check before
starting work — boundary only, never mid-item: `loop-detail.md § forecast divergence check`.**

## Stack-wiring at tech_stack lock
A greenfield project starts with no stack, so `/start` writes a coverage-only `checks.env`. The **one-time**
transition when `decision-engineer` flips `tech_stack` to `locked` — fill the gate commands, specialize the
`rules/` tags, wire the enforcers — is the orchestrator's to run, before the next `execute`. Skipping it
cannot silently disarm the gate: `checks.sh --check` fails the commit closed while source exists under
`project_root` with no stack gate wired.

→ **The steps, and the `STACK_GATE_NONE` exemption: `loop-detail.md § stack-wiring at tech_stack lock`.**

## Maintenance items
`prioritize` injects a maintenance item on a threshold: retention/size → `document:audit`, drift → `align`,
doc-size advisory → `doc-budget`. It is **self-contained** — no `planner`/`execute`/`verify` — and flows
straight to `commit`, then `close-issue?` (skip) → `prioritize`. Because there is no verdict, the pass
**stages a receipt** (`.workflow/maintenance/<item-id>.json`); without it there is no legal commit. Never fake
a `pass: true` verdict instead.

→ **The receipt contract and why the three thresholds are decoupled:
`loop-detail.md § maintenance items`.**

## Item-complete tail
`verify`(pass) → `checkpoint:qa?` → `document` → `commit` → `close-issue?` → `prioritize`.
The item's backlog done-flip and the `handoff.md` rewrite happen **before** `commit` (it captures them);
`close-issue` is the only post-commit step.
