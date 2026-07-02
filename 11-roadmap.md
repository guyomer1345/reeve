# 11 — Roadmap (what's left to build)

Living map of remaining work after the orchestrator + doc-surface foundations landed (sessions through
2026-06-30). The six-space design lives in `00`–`10`; this doc tracks **status + sequence**, not new design.
Each open item is tagged **[core]** (needed for a credible v1), **[stageable]** (real work, slot it in when it
pays off), or **[later]** (deliberately deferred). Update as items close.

## Done / proven
- **Space 1 — Orchestrator.** Root-`CLAUDE.md` driver, the `.workflow/loop.md` spine, the
  read→place→advance algorithm, the resume model (`state.json` / `handoff.md` / git), and the autonomous
  **permission model** (broad-allow + `ask` outward + `guard.sh`) — **dogfood-validated** end-to-end, zero
  local prompts after trust (D46–D58).
- **Space 2 — Roster + contracts.** 15 skills + 2 agents, I/O schemas, hub-and-spoke topology (D24–D34, D53);
  the **D36–D45 skill-body deltas** authored (`prioritize` waves · `execute` divergence tiers +
  refuse-destructive · `planner` risk_class+backup + decision-coverage gate · `adjudicate`
  conjunction-of-signals · `commit` secret-scan) + the prerequisite-repair two-commit carve-out and
  machine-actionable divergence `tier` (D66); the **`rules/` baseline + `/start` enforcement wiring** and the
  **two-tier drift gate** authored (thin `rules/*.md` with enforced-by tags · `/start` step-4 · `commit`
  mechanical step + git `pre-commit` backstop + generated `checks.sh` · `prioritize` drift-ticket queue —
  D40/D65/D67; only the per-stack `checks.sh` generator remains).
- **Space 5 — Disk layout + retention.** `.workflow/` tree + schemas (D53); the **retention/read law**
  (cap-and-archive, D59–D61) + the **retention script built** (`scripts/retention.py`, D71); the **unified
  `<project_root>/docs/` root** (D62).
- **Space 6 (partial) — Document freshness/prune.** `document` owns same-item freshness + the `audit` prune
  (D61); the knowledge *schema* is set (D38/D39).

## What's left — by space (every open thread)

### Space 1 — Orchestrator  *(core driver done)*
- **Waves coordination** — `build-once-per-wave` + the **collision independence test** (when two items can
  share a wave). Only bites once agents run in parallel. **[stageable]**
- **True-overnight reset** — MVP is human-prompted `/clear` + restart from `handoff.md`; unattended overnight
  needs the optional **SDK runner**. **[later]**
- **Model + effort routing** — per-task model/effort map (graph-maintenance cheap, planning expensive). **[later]**
- **Arbiter input contract** — decide a batch in dependency order vs one at a time. **[later]**

### Space 2 — Skills & agents  *(roster closed; bodies still v1)*
- **The D36–D45 skill-body deltas** — **DONE** (authored 2026-07-01; D66 added the prerequisite-repair
  two-commit carve-out + machine-actionable divergence `tier`). Bodies written **forward-compatible with the
  D65 gate**, so only a light second pass on `commit`/`prioritize` remains — folded into the drift-defense
  wiring below.
- **`rules/` baseline + `/start` enforcement wiring** (D40) + **two-tier drift defense** (D65/D67) —
  **AUTHORED 2026-07-01.** Thin `rules/*.md` (enforced-by tags), the `/start` step-4 enforcement wiring
  (auto-write greenfield / adopt-and-gap-fill brownfield), the `commit` mechanical-gate step + git `pre-commit`
  backstop + generated `.workflow/checks.sh`, and the `prioritize` drift-ticket queue. What makes output
  *disciplined*, not just working. **Remaining sliver:** the per-stack `checks.sh` generator (a `/start`
  runtime detail, unexercised until a real bootstrap). **[core — done bar the generator]**
- **Proportional-rigor decision gate (D69)** — a cheap O(seconds) triage in `planner` grades **every** output by
  reversibility × blast-radius → a rigor tier (0 judgment · 1 `research` · 2 pressure-test-if-cheap · escalate to
  the human), escalating to `decision-engineer` at that tier. The D68 **impact lens is the mechanical floor**
  (auto-escalate high-blast-radius touches), the alignment scan the backstop; `decision-record` gains
  `predicted_outcome` (rationale, checked opportunistically — **no back-eval stage**). Formalizes the
  engineering-feasibility pass; **no new agent** (answers the old "engineer agent?" slot). **[stageable]**

### Space 3 — Website / console + bus  *(role decided; unbuilt — NOT merely "later")*
- **C1 — read-only console** — render live loop state (roadmap, knowledge graph, activity, checkpoints) from
  files that already exist (`state.json`/`backlog`/`handoff`/`loop.md`/git). No bus needed → the quickest
  visible payoff. **[stageable, doable now]**
- **C2 — comms bus** (the local HTTP loopback, Space 5) — **on the critical path for unattended autonomy:** the
  dogfood showed every step self-drives *except* the blocking qa `checkpoint`, which needs the bus to deliver
  the human verdict away from the terminal; it also unblocks the airtight outward-gate (the `cd x && push`
  chaining-gap checkpoint-queue). **[core for unattended autonomy]**
- **C-map — project map + flow view** (D70) — a read-only cluster diagram over the code-map `graph.json`
  (impact-lens sizing, directory clusters, semantic zoom); static skeleton + a reserved **flow-overlay** layer
  (runtime differential capture — a direction, mechanism OPEN), and a **node→ticket** intake action (D69-triaged).
  Structural face of the project-state view. Stageable read-only atop C1; overlay + capture need later arms.
  Plus **remote control** = opt-in Cloudflare-tunnel serve (warning-only now, auth later). **[stageable; overlay later]**
- **Open design** — screen list (map **tab vs home**, D70/`07`); the "contact the orchestrator" UX (node→ticket
  reserved); stream-live vs snapshots; the stack. **[design-first]**

### Space 4 — Checkpoints & the demo skill
- **Demo skill mechanics** — `create-demo`'s *body* exists, but **how the sandbox is served/run, the
  refine-round limits, and where it lives on disk** are open (`09`). The product-alignment loop ("did we agree
  *what* to build") depends on it. **[core]**
- **Checkpoint data model + triggers** — finalize "what a checkpoint IS" (more examples), the **demo/setup
  triggers** (qa resolved via D30), and **which help features are MVP** (doc links / screenshots /
  screen-share / live feedback). **[stageable]** *(richer help needs the bus.)*
- **Engineering-feasibility pass** — the spike that de-risks the technical unknowns the demo deliberately
  skips (`09`). **[stageable]**
- **Automated testing · test-from-anywhere · paid device/QA platform** — designed-for, not built. **[later]**

### Space 5 — Shared state & bus
- **Read/write ownership per file + the request/response protocol** — the bus contract (couples with Space 3
  C2). **[core with C2]**
- **Outward-action permission mechanics** — standing pre-auth vs per-action, batching/queuing; the robust gate
  (beyond `ask` prefix-match) needs the bus checkpoint-queue (D35). **[stageable → core with bus]**
- **Symbol-level knowledge paths** — the seam left in Space-6 granularity. **[later]**

### Space 6 — Knowledge generation & ingest
- **Knowledge generation** — **DESIGNED (D68, pressure-tested on a real repo):** an **own per-stack code-map
  generator** (own script, emitted by `/start` like `checks.sh` — not an external tool), `graph.json`
  carrying **two centrality lenses** (impact + orchestration), and a **three-tier node seed** (`[G]` structural
  eager · `[X]` extractive purpose · `[D]` durable `why`/Sessions on touch). **Engine + tier-0 floor + 2 precise
  arms BUILT (D73/D74, 2026-07-02):** `scripts/codemap/codemap.py` — a shared language-agnostic driver over
  pluggable arms. Precise arms: **Python** (`ast`, ported verbatim + exact regression) and **JS/TS** (`JsTsArm` —
  tsconfig/jsconfig `paths`+`baseUrl` aliases + extension/index resolution; beats the floor **4-vs-1** on an alias
  fixture; no tsconfig → == the floor). Every other recognized language falls to the **tier-0 generic floor**
  (precision-first shallow-regex; D75 = nodes *any* source language, edges where a regex exists — "never nothing"). Any recognized language now gets nodes + clusters + both lenses; **`/start`
  step 4's `codemap.sh`** is a single auto-dispatching call. Validated on real `express`/`query-string`/`mux` + a
  13/13 multi-language fixture. *Remaining (D72 build set, research-ranked by prevalence):* the next precise arms —
  **Java** → **C#** → **C++**, then **Go/Rust/PHP** — as **zero-dep resolver arms** like `JsTsArm` on the same driver
  + `graph.json` contract (D74 revised D72: the default arm is a zero-dep resolver, not tree-sitter — tree-sitter is
  **reserved** for parse-hard languages, a graceful optional upgrade). Go pulled early for fast ROI (compiler-grade
  graph); C++ last in-wave (needs a compile-DB). `planner`/`debug` depend on it.
  **Five precise arms built + independently ground-truth measured — arm build thread CLOSED (D77/D79):** Python
  (flask: 40/40 sampled edges real) · JS/TS (+ exports/imports subpath) · **Go** (100% intra recall, replaced a
  broken+unsound floor) · **Java** (two-pass, closes the measured 24% no-import gap; same-package precision ≈100%
  on commons-lang/okhttp) · **C#** (namespace-aware two-pass; a **head-token precision filter** lifts intersection
  precision 97.2→98.9% with 0 recall loss, D79 — residual ~1% declaration-name collision, stays `medium`).
  **C++ / Rust / PHP stay on the tier-0 floor deliberately** (sound subset; a precise arm is built on demand by
  prevalence, C++ needs a compile-DB). **Living code-map DESIGNED + verified (D78):** a durable *observed* layer
  (`graph.observed.json`, provenance per edge) the loop accretes via `verify` runs — resolves regenerate-vs-
  incremental; impl rides Phase-2/3 (D70).
  **[core — arm build thread closed (D77/D79, all 5 measured); living-graph observed layer build next (D78)]**
- **Brownfield ingest** — **DESIGNED (D68); the `ingest` skill is being authored.** A thin `ingest` skill over
  existing leaves (`research` read → `document` write, no new agent) that seeds behavioural-core **intent from
  the existing `CLAUDE.md`/spec** (un-derivable from code), builds `docs/knowledge/` + a reconstructed
  `docs/spec/` (default **unspecified**, reconciliation checkpoint locks invariants). `/start` brownfield stays
  a STUB until the skill + generator land. **[core for brownfield — being authored]**
- **Retention script** — **BUILT 2026-07-02 (D71):** `scripts/retention.py` (stdlib Python, idempotent) does the
  three deterministic caps (Sessions cap-and-archive · superseded-decision GC + index tombstone · promoted-item
  prune), wired into `/start` (copy → `.claude/scripts/`) + `document` audit mode (invoke; and `document` writes
  the `promoted.json` prune-gate). Fixture-validated (caps fire, N accumulates, re-run no-op, git-recoverable).
  *Remaining:* `K`/threshold tuning against real runs; **Sessions distillation** deferred (D61). **[done]**
- **Graph regenerate-vs-incremental** — the mechanism for keeping the generated graph current. **[later]**
- **Spec↔implementation alignment scan** — a whole-project, fan-out reconciliation (decisions/spec ↔ code),
  each divergence classified by the commitment model (locked→drift · provisional→finalize · unspecified→
  steering) and scheduled by the D61 audit trigger (interval / threshold / after-big-change). Detection is the
  backstop; prevention (the grep gate, single-source status, capture-time blast-radius checks) shrinks the
  drift upstream. **Manual multi-agent scan runnable now** — proved out 2026-07-01, it found the D59–D62
  ref-leak regression. **Crystallized into a skill after knowledge generation** (which upgrades it from
  brute-force file reads to code-map-driven) and shipped as a **lightweight agent fan-out, not a Workflow** (a
  periodic user-run skill must not consume most of a session). Relates to the project-state view + self-hosting.
  **Promise-adequacy remit (D76):** the scan checks promise *adequacy*, not coverage — it **re-derives** each
  decision's negative class from the design's purpose/archetypes (blind to the code, so it doesn't inherit the
  builder's blind spot) and diffs it against what was exercised; plus an **over-delivery scan** (behaviour not
  traceable to any promise — catches scope creep like graphless files becoming nodes) and a **cross-decision
  invariant re-run** (satisfying promise P re-runs decision Q's invariant tests — catches "honouring one decision
  broke another's"). This is the *late* backstop, not the gate — it already existed and missed the D75-class once;
  the per-commit teeth are the promise-coverage gate + the boundary/property tests.
  **[core; scan doable now, skill knowledge-gated]**

### Cross-cutting — packaging, validation, self-hosting
- **Packaging/distribution** — plugin packaging (`.claude-plugin/`), `shared/` resolution, first-launch
  **trust-UX doc** (D57/D58). **[stageable]**
- **Validation gaps** — real orchestrator→agent **dispatch** in a harness run; `@import`-survives-`/compact`;
  whether `verify` samples the real `git diff` vs trusts the `changelog` (#8). **[stageable]**
- **Commitment-status storage** — where locked/provisional/unspecified is recorded (spec vs node
  frontmatter, `09`). **[stageable]**
- **Project-state view (user-raised)** — a synthesized "where is this project" surface (done · how it
  connects · what's left); likely **generated** (a `status` skill / console screen). Prereq for
  **self-hosting** this project with itself. **[stageable]**
- **Framework version-update skill (user-raised)** — `/update` pulls the latest public-repo package +
  **migrates** schema/format changes (not a blind overwrite). Follow-on to packaging. **[stageable]**

## Recommended sequence — phased (user-set, 2026-06-30)
**Phase 1 — Close the foundations + guiding documents.** Finish the decided-but-unwritten core at the spec
level so the engine is *disciplined + knowledge-complete* before any UI: the **D36–D45 skill-body deltas**,
the **`rules/` baseline + `/start` enforcement wiring** (D40), **knowledge generation** → **brownfield
ingest**, the **retention script** (D61), and a coherence/completeness pass tying up the remaining `[core]`
guiding-doc loose ends. *(Done 2026-07-01: the D36–D45 skill-body deltas (D66) **and** the `rules/` baseline +
`/start` enforcement wiring + two-tier drift gate (D40/D65/D67). **2026-07-02: knowledge generation → brownfield
ingest DESIGNED (D68, pressure-tested on a real repo); the `ingest` skill + the Python code-map extractor
(`scripts/codemap/`) authored, validated on the real repo, and wired into `/start` step 4. The **retention
script** (`scripts/retention.py`, D71) built + wired. The code-map recast to a **shared engine + tier-0 generic
floor + Python & JS/TS precise arms** (D73/D74) — any recognized language now gets a graph, and the default precise
arm is a **zero-dep resolver** (tree-sitter reserved for parse-hard languages). **2026-07-02/03: the Go/Java/C#
resolver arms built + independently ground-truth-measured, and the C# head-token precision filter added — the
code-map arm build thread is CLOSED (D77/D79, all five arms measured; C++/Rust/PHP stay on the floor by design).**
Remaining Phase-1: a guiding-doc coherence pass.)*
**Phase 2 — Define the website + demo (design, not build).** Close the Space-3 and Space-4 *design* questions
as a complete spec: the website screen list / contact-UX / stream-vs-snapshot / stack, **and** the demo skill
mechanics (serving/running the sandbox, refine limits, on-disk location) + the checkpoint data model /
triggers.
**Phase 3 — Build the website** (C1 console → C2 bus).
**Phase 4 — Build the demo.**
Everything `[stageable]`/`[later]` — waves coordination, the SDK overnight runner, model/effort routing,
packaging, the state-view, the version-update skill — slots around these phases as it pays off.

## The one-liner
The engine **drives** and is now **self-maintaining** (retention + freshness + docs-root) and **disciplined**
(skill deltas + `rules/` + the drift-gate authored — bar the per-stack `checks.sh` generator). What's left is
to make it **knowledge-complete** (generation → ingest),
**visible** (the console + bus), and **alignment-ready** (the demo + checkpoint mechanics). The bus is the one
"enhancement" that's actually on the critical path for *unattended* autonomy — not merely later.
