# Loop — the routing graph

The orchestrator reads this to route. **Topology is fixed** (it changes only with the package);
the live position lives in `state.json`. Nodes are skills/agents; edges are followed on a node's output.

## Routing table
| node | on output | next |
|---|---|---|
| `ingest` *(brownfield entry — `/start` routes here)* | knowledge graph + reconstructed spec built | `checkpoint:reconcile` |
| `checkpoint:reconcile` | reconstructed spec confirmed | `prioritize` |
| `checkpoint:reconcile` | corrections needed | `ingest` (re-run) / `discuss` |
| `discuss` | spec drafted | `create-demo?` (sandbox gate) |
| `create-demo` | demo approved (checkpoint pass) | `planner:decompose` |
| `create-demo` | gate not triggered | `planner:decompose` |
| `planner:decompose` | roadmap → backlog | `prioritize` |
| `prioritize` | next wave emitted | `planner:plan-one` (per item in the wave) |
| `prioritize` | maintenance due (retention or drift threshold) | `document:audit` / `align` |
| `prioritize` | backlog empty | `idle` (await steering) |
| `idle` | steering arrives / new backlog item (a `create-issue` side-door) | `prioritize` (re-pick) |
| `planner:plan-one` | open decisions | `decision-engineer` → back to `planner:plan-one` |
| `planner:plan-one` | plan ready, per-item sandbox gate fires (visible surface, underdetermined) | `create-demo` (per item) |
| `planner:plan-one` | plan ready, no per-item demo | `execute` |
| `decision-engineer` | needs evidence | `research` → back to `decision-engineer` |
| `create-demo` | demo approved (per-item checkpoint pass) | `execute` |
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
| `checkpoint:setup` | fail (couldn't complete) | re-attempt `checkpoint` (re-guides via setup-guide) / escalate to human |
| `document` | knowledge + Sessions updated | `commit` |
| `commit` | snapshot made | `close-issue?` |
| `close-issue` | issue closed (or no linked issue → skip) | `prioritize` (next item) |
| `document:audit` | retention pass done (changes staged) | `commit` |
| `align` | scan done (tickets filed via `create-issue`, fixes staged, anchor written) | `commit` |

Side doors (callable from anywhere): `create-issue` → backlog · `research` (service).

## Scheduler boundary — the inbox drain
Between items (and before any pick) the orchestrator **drains `.workflow/inbox/`** — the console's typed
messages to the loop. This is **plain control-flow, not a node**: no skill runs and no edge is followed, so it
appears nowhere in the table above. Order within one boundary:

`drain (skip already-consumed ids) → apply control → resume a ready-parked ticket (oldest verdict first, +aging)
→ promote intake → start-new → fire release → sleep`

What each kind does at the boundary, and the anchor that makes a repeat a no-op:
- **verdict** — resumes the parked ticket whose `token` matches; an unknown or already-closed token → dead-letter
  and surface it. *Anchor:* the token itself (already closed → no-op).
- **intake** — promoted into `backlog.md` through triage, stamped with the source message id. *Anchor:* that stamp
  (an item already carrying the id is already promoted → skip).
- **control** — reprioritize / pause, honored here only (non-preemptive; never mid-item). *Anchor:* none possible,
  so control ops are required to be idempotent.
- **release** — fires the named `outbox/` entries through `guard.sh`. *Anchor:* the entry's status (already fired
  → skip).

A parked ticket resumes **only** via this drain. The consumer **never deletes** an inbox file (the bus owns that
directory and collects consumed messages itself).

**The drain is split, and the split is the point.** *Which* messages are new, in what order they apply, what the
watermark is now, and what may be pruned are all a pure function of the inbox and `handoff.md` — that half is
`drain.py`'s (`list` → apply → `record`), and it is not re-derived by hand. *Applying* a message is judgment —
which ticket a verdict resumes, whether an ask is worth promoting and at what priority, how a rejection routes —
and that half stays here. `record` recomputes `consumed_through` (the low-watermark: every message at or below it
is consumed, so the bus may collect it) and **prunes the consumed-set to ids above it**, which is what keeps
`handoff.md` bounded — a cold start reads that file whole.

## Maintenance items
`prioritize` injects a **maintenance item** on a threshold (§ `prioritize`): a *retention/size* threshold →
`document:audit` (bound the append-only tier); a *drift* threshold → `align` (reconcile spec/decisions/promises
vs code). A maintenance item is **self-contained**: it runs its own pass and flows straight to `commit` — there
is no `planner`/`execute`/`verify`, because there is no product-code change to plan and no runtime behaviour to
verify — then `close-issue?` (skip: no linked issue) → `prioritize`. `align`'s *semantic* findings leave as
ordinary `create-issue` tickets (the side-door) and ride the normal queue; only its mechanical auto-fixes + the
new scan anchor ride this commit. The two thresholds are **decoupled** — memory pressure ≠ drift risk.

## Item-complete tail
`verify`(pass) → `checkpoint:qa?` → `document` → `commit` → `close-issue?` → `prioritize`.
The item's backlog done-flip and the `handoff.md` rewrite happen **before** `commit` (it captures them);
`close-issue` is the only post-commit step.

## Diagram
```mermaid
flowchart TD
  start([/start]) -->|greenfield| discuss
  start -->|brownfield| ingest --> reconcile{reconcile ok?}
  reconcile -->|confirmed| prioritize
  reconcile -->|corrections| ingest
  discuss --> demo{sandbox gate?}
  demo -->|visible surface| create-demo --> dec[planner:decompose]
  demo -->|no| dec
  dec --> prioritize
  prioritize -->|next wave| plan[planner:plan-one]
  prioritize -->|maintenance due| maint[document:audit / align] --> commit
  prioritize -->|empty| idle([idle])
  idle -.steering / new issue.-> prioritize
  plan -->|open decision| decision-engineer --> plan
  decision-engineer -.needs evidence.-> research -.-> decision-engineer
  plan -->|per-item demo| pdemo[create-demo] --> execute
  plan -->|plan ready| execute --> verify
  execute -.structural divergence.-> plan
  verify -->|pass| qa{human-qa?}
  verify -->|fail| debug --> refine --> plan
  debug -.no clear cause.-> hcp[checkpoint: human]
  qa -->|pass / none| document
  qa -->|fail| debug
  document --> commit --> close{linked issue?}
  close -->|yes| close-issue --> prioritize
  close -->|no| prioritize
  any[any node] -.problem found.-> create-issue -.-> backlog[(backlog)]
```
