# 10 — Capability Roster (Space 2 v1)

Closes the `02` open item (roster + I/O contracts + skill-vs-agent + topology). Derived by walking a full
new-project loop end-to-end (session 2026-06-29). Each capability's full contract lives in its own package
file; artifact formats live in `shared/schemas.md`. **This doc is the map** — roster, loop order,
call-graph, open items.

## Package layout **[DECIDED — D25; rooted under `product/` by D125]**
Claude-Code-native plugin source under **`product/`** (the plugin root — D125 moved it off the repo root so the
construction record and the shipped package stop sharing a namespace). Paths below are relative to it, and
**`product/MANIFEST.json` is the authoritative ship boundary** — this list is orientation, never the source:
- `commands/<name>.md` — human-invoked entry points (`/start`, `/update`, `/rebind`, `/dispatch`)
- `skills/<name>/SKILL.md` — procedure capabilities (model-invoked)
- `agents/<name>.md` — leaf worker capabilities
- `shared/schemas.md` — inter-capability artifact schemas
- `shared/format.md` — the authoring format every package file follows (D31/D34)
- `shared/memory-model.md` — the three-tier rule for what the loop may rewrite/change/never-touch (D38), plus the
  read/retention + context-budget laws and the **distillation law** every summarising step obeys (D172)
- `rules/<topic>.md` — thin baseline engineering rules, specialized per project by `/start` (D40)
- `templates/` — files `/start` installs into a target: `orchestrator-CLAUDE.md`, `loop.md`,
  `settings.json` (loop permission rules: `allow` local / outward via the outbox), and the fixed
  `checks.sh` mechanical-gate runner (D52/D57/D58; `checks.sh` D127)
- `hooks/` — the enforced gates installed to `.claude/hooks/`: `guard.sh` (secret-scan + verify-before-commit +
  the push floor), `pre-commit.sh`, the shared `verify_check.py`, `session_start.py`, `precompact.py` (D58/D110/D129/D136/D144)
- `scripts/` — the shipped helpers `/start` copies to `.claude/scripts/` per the manifest `install[]` map
  (the daemon, drain, retention, code-map engine, coverage gates, reconcile + rebind runners, statusline)

**Driver added (D46/D47):** the orchestrator **`CLAUDE.md`** (root brief) + **`.workflow/loop.md`** (routing
graph + diagram) + **`hooks/`** (the enforced gates), plus `product/.claude-plugin/plugin.json` and the repo's
own `.claude-plugin/marketplace.json` (D125). The repo is **both** the construction record
(`docs/design/00`–`11`) and the package source (`product/`).

## Skill vs agent **[DECIDED — D24, D27, D84]**
- **skill** = a procedure / controller — run by the orchestrator; defines *how*; **may dispatch agents**.
- **agent** = a **leaf worker** — its own tools, persistent/re-messageable (D4); does the heavy lifting;
  **never spawns sub-agents.**
- Topology (closes `02`): **strict hub-and-spoke** — only skills/orchestrator fan out; agents are leaves.
- Consequence: the only agents are `research` and `setup-guide`; all adjudicators (`verify`, `debug`,
  `decision-engineer`) are skills.
- **Context-isolation axis (D84 — refines D27):** the line is drawn by *two* axes, not just fan-out. A skill runs
  *inline in the orchestrator's context*; an agent runs *isolated* and returns a thin pointer. So a node is a
  **leaf agent** when it does heavy autonomous work AND neither fans out nor holds the human conversation; it
  stays a **skill** when it is a fan-out controller (leaves can't spawn — authored *thin*), human-interactive, or
  thin bookkeeping. **Fan-out need beats heaviness** — a heavy adjudicator stays a skill. **Reclassification
  pending (deferred to a dedicated session): `execute` + `create-demo` → leaf agents** (`document` stays a skill
  for now; `ingest` stays a skill — it spawns `research`). Until then the table below reads the on-disk truth.

## The adjudicate pattern **[DECIDED — D24]**
One base skill `adjudicate` (gather views → judge → confidence-gate → loop/escalate), specialized by
`verify` / `debug` / `decision-engineer`. Collapses the prior Arbiter / engineer-agent / decision-engineer
overlap into one adjudicator.

## Roster
| capability | kind | one-line job | file |
|---|---|---|---|
| start (init) | command | bootstrap the workflow; greenfield/brownfield (D28/D29) | `commands/start` |
| update | command | migrate an initialised project onto the installed package version (D137/D139) | `commands/update` |
| rebind | command | bind the machine-local runtime half to THIS machine after a move (D141/D142) | `commands/rebind` |
| dispatch | command | write a complete `handoff.md` on demand so a `/clear` is safe (D136) | `commands/dispatch` |
| adjudicate | skill (base) | gather views → judge → confidence-gate | `skills/adjudicate` |
| discuss | skill | intake conversation → `spec` | `skills/discuss` |
| create-demo | skill *(→ agent, D84 — pending)* | throwaway sandbox for product approval | `skills/create-demo` |
| create-forecast | skill | the chain of events the loop proposes, before it walks it | `skills/create-forecast` |
| prioritize | skill | order the backlog, emit the next wave | `skills/prioritize` |
| planner | skill | decompose → `roadmap` / plan one item → `plan` | `skills/planner` |
| decision-engineer | skill | resolve an open build decision (adjudicate) | `skills/decision-engineer` |
| research | agent | gather info (Investigation worker) | `agents/research` |
| execute | skill *(→ agent, D84 — pending)* | run a plan, decide nothing → `changelog` | `skills/execute` |
| verify | skill | artifact conformance (adjudicate) | `skills/verify` |
| debug | skill | root-cause behaviour ≠ intended (adjudicate) | `skills/debug` |
| refine | skill | route corrections back through planner→execute | `skills/refine` |
| checkpoint | skill | pause for a human verdict (demo / qa / setup / reconcile / forecast) | `skills/checkpoint` |
| setup-guide | agent | precise human steps for a manual external task | `agents/setup-guide` |
| document | skill | fold changes + decisions into the knowledge base | `skills/document` |
| ingest | skill | brownfield: build the knowledge base + reconstructed spec from existing code | `skills/ingest` |
| commit | skill | git snapshot (Conventional Commit; the checkpoint marker) | `skills/commit` |
| create-issue | skill | capture a problem/idea → backlog + GitHub issue | `skills/create-issue` |
| close-issue | skill | close the GitHub issue a completed item resolved (commit tail) | `skills/close-issue` |
| align | skill | periodic spec↔code reconciliation scan (mechanical always-whole + scoped semantic) | `skills/align` |
| answer | skill *(side door — entered from the boundary drain)* | answer a human's question from the project's own record → the conversation thread | `skills/answer` |

## Loop order (the spine)
`.workflow/loop.md` is the **authoritative** routing graph (D80); this is the summary spine. Edges added in the
resolve phase — brownfield entry, per-item demo, fail-**by-kind**, `debug`/`verify` **escalate→checkpoint**,
`idle`→`prioritize` wake, `execute` structural→re-plan — live there, not duplicated here.
```
brownfield: /start → ingest → checkpoint(reconcile) → prioritize    ┐ intake (09)
greenfield: /start → discuss → create-demo (if the gate fires)      ┘
  → prioritize (pick next)
  → planner ──► decision-engineer ──► research   [per-item demo gate → create-demo → execute]
  → execute (→ changelog; structural divergence → re-plan)
  → verify ──on-fail──► debug ──► refine (routes correction back to planner→execute)
      └ debug/verify no-resolution → escalate → checkpoint (human)
  → checkpoint (qa only if the plan declared human-qa; setup for spec integrations + execute-discovered; reconcile for brownfield)
  → document (→ Space 6 Sessions)
  → commit (the checkpoint marker)
  → close-issue (close the GitHub issue the item resolved)

create-issue → backlog   (side-door, from anywhere; picked at next prioritize / idle-wake)
research                  (service, callable from anywhere)
```

## Call-graph (who calls whom)
- `planner` → `decision-engineer` → `research`
- `create-demo` → `checkpoint`
- `checkpoint`(setup) → `setup-guide`  *(leaf: does its own research)*
- `verify` → `debug` → `refine` → `planner` → `execute`
- `debug` → `research`
- any → `create-issue` · any → `research`
- item-complete tail: `verify`(pass) → `document` → `commit` → `close-issue`
- maintenance items (injected by `prioritize`): `document:audit` → `commit`; `align` → `create-issue` (per
  semantic finding) → `prioritize`, mechanical fixes ride `commit` (D71/D81)

## Build status
- **The full roster is written** (`skills/`, `agents/`) + `shared/schemas.md` — the table above is the source
  (list = count); numbers aren't restated here, they drift. Roster v1 complete (added `close-issue`, D33).
- **Authoring-format pass complete (D31/D34):** every skill + agent follows `shared/format.md` and
  carries no spec-internal refs (grep-gated — `scripts/check-no-spec-refs.sh`).
- **Dogfood-validated (D52):** the orchestrator design *drives* — a throwaway greenfield repo ran two tasks
  (happy + fail/decision) end-to-end; MVP install = loose `.claude/` files (D57). Findings → D53–D57.

## `init` / `/start`  **[BUILT v1 — D29 → `commands/start.md`]**
The bootstrap command (D10/D28). **greenfield** = repo-setup → scaffold → **console up as the bootstrap front
door** (step 5 — the daemon is BUILT, D115/D116, and surfaced there by D132, no longer a stub) → hand to
`discuss`; **fully supported now.** **brownfield/integrate** = the shared scaffold plus the Space-6
**`ingest` skill** + reconciliation checkpoint; ingest **mechanics decided (D68)**, the **`ingest` skill
authored**, and the **shared code-map engine built + wired into `/start` step 4** (five precise arms + a
tier-0 floor — arm build thread CLOSED, D77/D79) — brownfield ingests any recognized language (owner: `11` Space 6). Orchestrator `CLAUDE.md` driver now
specced (D46–D49). *(The two sub-steps this once listed as stubbed are both closed: console launch is `/start`
step 5 against the built daemon — D115/D116/D132 — and the disk layout is `05`'s tree, which D114 made the
owner of each path's commit-class / `bus:` / `pin` markers.)*

## Adoption deltas — workflow-kit + GSD (D36–D45, +D40/D65/D67)
Skill bodies **authored** (session 2026-07-01); each delta maps to its landed home:
- `prioritize` — **waves**: dependency-group the ready set; run a wave; re-pick (D36). **+ drift tickets ride
  the normal queue at commitment-severity** (D65). **+ the D91 eligibility predicate + continue-while-parked
  scheduler** (resume-a-ready-parked-ticket first +aging → start-new eligible → sleep; boundary check is plain
  code, not an LLM call).
- `execute` — **divergence tiers** (cosmetic / prerequisite-repair-as-separate-commit / structural-stop, D37);
  **refuse** a destructive `plan` with no verified `backup`, run+verify it first (D42).
- `planner` — set `risk_class` + require `backup` when destructive (D42); **decision-coverage gate** —
  every `decision-record` maps to ≥1 step or block (D43); emit **no un-checkable** acceptance criterion (D30).
- `adjudicate` — **conjunction-of-signals**: an LLM verdict gates only with a corroborating deterministic
  signal; AI-only → advisory (D45). Propagates to `verify`/`debug`/`decision-engineer`.
- `commit` — **secret-scan** the staged diff, stop on a hit (D44); **+ mechanical-gate step** (`checks.sh --fix`
  → log; semantic drift → `create-issue`, never resolved inline) (D65/D67).
- thin **`rules/`** baseline (enforced-by tags) + **`/start` step-4 enforcement wiring** + git `pre-commit`
  backstop + the **fixed `.workflow/checks.sh` runner + generated `.workflow/checks.env`**, nearest-file-wins
  (D40/D65/D67; `checks.sh` shipped fixed + driven, D127).
- **Also landed earlier:** `document` same-item doc + Mermaid-C4 freshness + audit prune (D41);
  `shared/memory-model.md` (D38); `shared/schemas.md` plan `risk_class`/`backup`/`decisions[]`.

## Still open
- The **collision-model independence test** — **DECIDED (D91):** eligible iff *dependency-ready ∧ file-disjoint
  (hard) ∧ ¬1-hop code-map neighbor (soft → flagged speculative-merge)*. Powers both waves (D36) and
  continue-while-parked interleaving. `prioritize` owns the predicate; `verify` owns the rebase-onto-trunk
  speculative-merge on a parked ticket's resume.
- `init` **brownfield-ingest** — mechanics decided (D68); `ingest` skill authored + the code-map engine (five
  arms + tier-0 floor, thread CLOSED D77/D79) wired into `/start`. Runtime driven (D130) + lived (D131–D134 —
  the Phase-6 experience fixes); open code-map follow-ons (living observed layer, D83 charter) live in `11` Space 6.
- D41 freshness mechanisms (staleness signal, prune pass) + #8 (verify reads diff?) — `07`.
