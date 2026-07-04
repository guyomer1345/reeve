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
| `checkpoint:demo` | fail (rejected) | `create-demo` (refine the sandbox / spec) |
| `checkpoint:setup` | fail (couldn't complete) | re-attempt `checkpoint` (re-guides via setup-guide) / escalate to human |
| `document` | knowledge + Sessions updated | `commit` |
| `commit` | snapshot made | `close-issue?` |
| `close-issue` | issue closed (or no linked issue → skip) | `prioritize` (next item) |
| `document:audit` | retention pass done (changes staged) | `commit` |
| `align` | scan done (tickets filed via `create-issue`, fixes staged, anchor written) | `commit` |

Side doors (callable from anywhere): `create-issue` → backlog · `research` (service).

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
