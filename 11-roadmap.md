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
- **Space 2 — Roster + contracts.** 17 skills + 2 agents, I/O schemas, hub-and-spoke topology (D24–D34, D53);
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
- **Waves coordination** — the **collision independence test is now DECIDED (D91)** (dependency-ready ∧
  file-disjoint ∧ ¬1-hop-neighbor); it powers both waves and **continue-while-parked interleaving (MVP, D91)**.
  Residual: `build-once-per-wave` (a wave-coordinator, not a command gate). **[core — predicate done; build-once
  stageable]**
- **Context / checkpoint reset — DECIDED (D90/D92); the runner is now MVP (D113).** Checkpoint = durable park +
  `claude --resume`; context is disposable (subagents keep the orchestrator thin; auto-compact = within-run
  seatbelt). The thin **local relaunch-runner** (fresh `claude -p` per ticket — the *only* self-`/clear`-free path;
  triple-solves context + checkpoint-resume + overnight; NOT the cloud Agent SDK) is **pulled into MVP**: it is the
  last link that makes the away-channel pay off (without it an away verdict lands durably in the inbox and simply
  *waits* for a human to reach the terminal), and D92's reason for deferring it — "preserve the pure-config MVP" —
  **is obsolete**, since D94 already ships a detached always-alive daemon. It **hosts on that daemon**
  (`config.runner.enabled`), and it retires D92's manual-`/clear` stopgap. **[core — decided; builds as Phase-3
  increment 6]**
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
- **The console + bus are ONE component, built in increments (D113 — replaces the old "C1 read-only console → C2
  comms bus" split).** That split was stale against D94/D100: a read-only console *is* a detached daemon serving a
  browser — **the console IS the bus**, so "C1, no bus needed" describes nothing buildable, and C1-alone cannot
  deliver the console's one critical-path job (a verdict needs the POST + drain). Sequence, value-ordered — each
  step adds a real capability, and **no MVP goal is met until step 3**, so step 2 is a de-risking checkpoint, *not*
  a shippable milestone:
  1. **Daemon skeleton** — **BUILT 2026-07-16 (D115/D116)**: detached (`setsid`), `flock` liveness on its own
     `bus.lock`, `bus.json`, loopback bind, capability token, `POST /shutdown` + the jobs-frame idle janitor
     (D94/D95/D100). Ships as `scripts/bus.py` → copied to `.claude/scripts/` (closes register F10); idle is a
     conjunction of per-job votes an open checkpoint suppresses (closes F11). **The substrate it needed did not
     exist and is now built (D115):** the `runtime.json` pointer (a pinned path could not be *found* — `bus.json`
     is itself pinned), a separate `bus.lock` (a lock on the renamed record is silently defeated), and
     mode-verified-not-requested (a 0600 create returns 0777 on the repo mount, silently).
  2. **Reads + the cockpit page** — **BUILT 2026-07-16 (D116)**: the synthesized ETag'd snapshot over
     `state.json`/`parked/`/`outbox/`/`backlog.md` + `git log`, and the zero-build vanilla page (embedded in the
     daemon; `<meta>`-tag token bootstrap, strict `script-src 'self'`, chained-`setTimeout` poll). *(The old "C1".)*
     **Residual: nobody has rendered the page in a browser** — correctness is driven, legibility is not.
  3. **POST → inbox + the orchestrator drain** — **BUILT 2026-07-16 (D117/D118/D119)**: `POST
     /api/{verdict,intake,control,release}` → validate → atomic append → `202` + a `Location` ticket that **is** the
     `message_id`; the console's forms + a "my requests" surface that resolves off the per-kind effect anchors (so it
     still answers after GC); inbox GC on the watermark; and the drain **split** — its bookkeeping is `scripts/drain.py`
     (`list` → apply → `record`/`secret`), its apply stays the brief. *The verdict job lands here — the first
     increment to meet an MVP goal* (D93 protocol + the D108 consume model) (*the old "C2"*).
     **Residual (carried from increment 2, now twice): nobody has rendered the page in a browser** — the forms were
     added to an unreviewed surface; correctness is driven, legibility is not.
  4. **The notifier** — **BUILT 2026-07-18 (D120)**: the daemon watches `parked/` → alerts on a new open checkpoint
     → re-alerts every `config.checkpoint.reminder_hours` → escalates once past the absolute `deadline` (never
     auto-proceeding), as a **term on the existing `parked` job**. Alert state lives in a fourth daemon-owned path
     (`alerts.json`, fail-toward-noise, survives restart); event 2 ships its **real-source arms** (deadline +
     dead-letter escalation), the thrash/crash arm deferred to increment 6 with its liveness signal; the **doorbell**
     webhook payload carries no request body. *Away becomes triggerable.*
  5. **The remote socket** — **BUILT 2026-07-19 (D122)**: the structural two-socket split — Socket B loopback/full-
     surface unchanged, Socket A the reduced remote surface (reads · opinion verdicts · static demo) bound only when
     `config.remote` declares a transport, gated by a distinct **persisted** token as second factor over the transport
     identity. Building sharpened four points (the token never on the surface it gates · stable-not-per-boot
     coordinates · a **structural** `returns`/`tasks` credential boundary, not the `_is_sensitive` heuristic ·
     `public_url` load-bearing for the forwarded-Host allowlist); pairing ships **copy-paste**, the QR deferred as a
     scoped fast-follow. *Away becomes actionable.*
  6. **The relaunch-runner** — (D113): away becomes *completing*.
  **[core for unattended autonomy — fully designed (D93/D94/D95 + D108/D111/D112/D113); build = Phase 3.
  **Increments 1+2 BUILT 2026-07-16 (D115/D116** — `scripts/bus.py` + 39 fixture tests, gate suite 89 → 128);
  **increment 3 BUILT 2026-07-16 (D117/D118/D119** — `scripts/drain.py` + the POST surface; gate suite 128 → 177);
  **increment 4 BUILT 2026-07-18 (D120** — the notifier; gate suite 181 → 199);
  **increment 5 BUILT 2026-07-19 (D122** — the remote socket / two-socket split; gate suite 199 → 235).
  **The first MVP goal is met (a verdict lands durably and unparks the loop), away is *triggerable* (the notifier),
  and away is now *actionable* (act on a checkpoint from a phone over a declared identity transport).**
  Next is **increment 6 — the relaunch-runner** (D113): away becomes *completing*.]**
- **C-map — project map + flow view** (D70) — a read-only cluster diagram over the code-map `graph.json`
  (impact-lens sizing, directory clusters, semantic zoom); static skeleton + a reserved **flow-overlay** layer
  (runtime differential capture — a direction, mechanism OPEN), and a **node→ticket** intake action (D69-triaged).
  Structural face of the project-state view. Stageable read-only atop C1; overlay + capture need later arms.
  Plus **remote control** = opt-in phone access — **now a two-socket split behind a declared identity transport
  (D112: Cloudflare Access | Tailscale), not the old unauthed warning-only tunnel** (which was unbuildable). **[stageable; overlay later]**
- **Open design** — **CLOSED (D99–D101):** the console model + screen list (map = **tab**, not home, not the first
  cut) + snapshot-poll refresh + the contact-UX (verdict/intake forms + a "my requests" surface) (D99); the stack —
  a stdlib-Python detached daemon + a zero-build CSP-clean page (D100); the two-event notification taxonomy (D101).

### Space 4 — Checkpoints & the demo skill
- **Demo skill mechanics** — **DONE (D102–D104):** the sandbox is a build-free, self-contained bundle the D94
  daemon serves under a `sandbox`-CSP opaque origin (D102); the refine loop caps at 3 → escalate to `discuss`
  (D103); it lives at `.workflow/demos/<item-id>/`, pruned on resolve (D104). (`09`.) **[done]**
- **Checkpoint data model + triggers** — **DONE (D96–D98):** the judgment/action taxonomy + trigger rule (setup =
  spec `integrations[]` + execute-discovered; qa=D30, demo=D22 gate, reconcile=ingest), the verb-enum verdict +
  plural machine-verified setup gate, and the MVP help set (contextual steps + verified deep-links + breadcrumbs;
  screenshots/screen-share/agent-automation deferred). **[done]**
- **Engineering-feasibility pass** — the spike that de-risks the technical unknowns the demo deliberately
  skips (`09`). **[stageable]**
- **Automated testing · test-from-anywhere · paid device/QA platform** — designed-for, not built. **[later]**

### Space 5 — Shared state & bus
- **Read/write ownership per file + the request/response protocol** — **DECIDED (D93):** a single-writer partition
  (zero co-written files; intake promoted through the inbox, not written to the backlog) + atomic-publish + the
  two-mechanism protocol (sync reads · async commands); **the orchestrator is never an HTTP responder.** Bus
  lifecycle D94, trust D95. **[core — designed; build Phase 3]**
- **Outward-action permission mechanics** — **DECIDED (D105, Phase-2 E2):** a **transactional-outbox** queue
  (`.workflow/outbox/`, retiring the D60 `checkpoints/`), **not** a checkpoint; `guard.sh` floor + a coarse
  `config.outward` allow|ask allowlist (standing pre-auth); the loop defers + continues, a console `kind: release`
  batch-approval drains it (state-bound, TTL'd, no ledger). Build rides Phase 3 (with the bus). **[core — designed; build Phase 3]**
- **Symbol-level knowledge paths** — the seam left in Space-6 granularity. **[later]**

### Space 6 — Knowledge generation & ingest
- **Knowledge generation** — **DESIGNED (D68, pressure-tested on a real repo):** a **single multi-language code-map engine** (`scripts/codemap/codemap.py`, shipped whole over pluggable arms —
  not an external tool, and **not** per-stack-generated: `/start` emits only a thin `.workflow/codemap.sh` wrapper;
  D72/D74 revised the original D68 per-stack framing), `graph.json`
  carrying **two centrality lenses** (impact + orchestration), and a **three-tier node seed** (`[G]` structural
  eager · `[X]` extractive purpose · `[D]` durable `why`/Sessions on touch). **Engine + tier-0 floor + precise
  arms (D73/D74 engine → D77/D79 arms):** `scripts/codemap/codemap.py` — a shared language-agnostic driver over
  pluggable **zero-dep resolver arms** (D74 revised D72: the default arm is a zero-dep resolver, not tree-sitter —
  tree-sitter is **reserved** for parse-hard languages, a graceful optional upgrade). Every recognized language
  *without* a precise arm falls to the **tier-0 generic floor** (precision-first shallow-regex; D75 = nodes *any*
  source language, edges where a regex exists — "never nothing"), so any recognized language gets nodes + clusters
  + both lenses; **`/start` step 4's `codemap.sh`** is a single auto-dispatching call. `planner`/`debug` depend on it.
  **Five precise arms built + independently ground-truth measured — arm build thread CLOSED (D77/D79):** Python
  (flask: 40/40 sampled edges real) · JS/TS (+ exports/imports subpath) · **Go** (100% intra recall, replaced a
  broken+unsound floor) · **Java** (two-pass, closes the measured 24% no-import gap; same-package precision ≈100%
  on commons-lang/okhttp) · **C#** (namespace-aware two-pass; a **head-token precision filter** lifts intersection
  precision 97.2→98.9% with 0 recall loss, D79 — residual ~1% declaration-name collision, stays `medium`).
  **C++ / Rust / PHP stay on the tier-0 floor deliberately** (sound subset; a precise arm is built on demand by
  prevalence, C++ needs a compile-DB). **Living code-map DESIGNED + verified (D78):** a durable *observed* layer
  (`graph.observed.json`, provenance per edge) the loop accretes via `verify` runs — resolves regenerate-vs-
  incremental; impl rides Phase-2/3 (D70). **When built, revisit the `verify` observation charter (D83):** the
  skill now licenses `verify` to *drive* a flow as a pure observer, verdict-still-artifact-only — a wording
  reconciliation today, to be made concrete against the real capture mechanism when the observed layer lands.
  **[core — arm build thread closed (D77/D79, all 5 measured); living-graph observed layer build next (D78), then the D83 charter revisit]**
- **Brownfield ingest** — **DESIGNED (D68); the `ingest` skill is AUTHORED** (`skills/ingest/SKILL.md`). A thin
  `ingest` skill over existing leaves (`research` *gathers* → `ingest` *synthesizes* the spec → reconciliation
  `checkpoint`; `document` authors the durable `why`/Sessions later, **not** during ingest — no new agent) that
  seeds behavioural-core **intent from the existing `CLAUDE.md`/spec** (un-derivable from code), builds
  `docs/knowledge/` + a reconstructed `docs/spec/` (default **unspecified**, reconciliation checkpoint locks
  invariants). Residual is **runtime, not spec**: brownfield `/start` (§3) is authored but **unexercised** until a
  real bootstrap run (validation-blocked, like dispatch). **[core for brownfield — skill authored; unexercised]**
- **Retention script** — **BUILT 2026-07-02 (D71):** `scripts/retention.py` (stdlib Python, idempotent) does the
  three deterministic caps (Sessions cap-and-archive · superseded-decision GC + index tombstone · promoted-item
  prune), wired into `/start` (copy → `.claude/scripts/`) + `document` audit mode (invoke; and `document` writes
  the `promoted.json` prune-gate). Fixture-validated (caps fire, N accumulates, re-run no-op, git-recoverable).
  *Remaining:* `K`/threshold tuning against real runs; **Sessions distillation** deferred (D61). **[done]**
- **Spec↔implementation alignment scan** — **BUILT as the `align` skill + `check_contracts.py` (D81).** Two
  layers of opposite scaling: a **mechanical layer** (always-whole, decidable) — the routing-graph contract
  linter (`check_contracts.py`, wired into the meta-repo pre-commit + copied by `/start`) plus the
  coverage/status/no-refs gates — and a **semantic layer** scoped to the diff-since-anchor + budget-capped
  (`config.align.max_agents`), each divergence classified by the commitment model (locked→drift ·
  provisional→finalize · unspecified→steering). **Drift-triggered** (`config.align.every_n_commits` / phase
  boundary, decoupled from the retention trigger), **principle-only 2-lens panel** (occurrence + materiality,
  drop-on-≥1); a *lightweight fan-out, not a Workflow* (D63). **Promise-adequacy remit (D76)** carried in: it
  re-derives each decision's negative class blind to the code + an **over-delivery scan** + a **cross-decision
  invariant re-run** — the *late* backstop, not the gate (the per-commit teeth stay the promise-coverage +
  boundary/property tests). **Validated** by re-finding the pressure-test register (G2/G4/S3, 0 false positives)
  on the surface it scopes; the semantic layer's own validation rides Phase 2/3 (no built product yet). Relates
  to the project-state view + self-hosting. **Tier-2/3 drift defense added (D89):** a meta-repo
  `check_enum_coherence.py` (enum + registry coherence, per-commit, beside `check-status-coherence.sh`) + the
  full-surface `align` cold-audit adopted as a phase-boundary ritual; the `adjudicate` contract-linter
  false-positive fixed (0 advisories).
  **[core — skill + mechanical layer BUILT (D81); semantic layer validated Phase 2/3]**

### Cross-cutting — packaging, validation, self-hosting
- **Packaging/distribution** — plugin packaging (`.claude-plugin/`), `shared/` resolution, first-launch
  **trust-UX doc** (D57/D58). **[stageable]**
- **Public-repo identity + onboarding (D121, user-raised)** — the repo ships publicly, but today it's a dense
  construction record (numbered docs + `D<N>` refs + internal codenames) fronted only by a spec-navigation README.
  The deliverable: decide the **one-repo-vs-two fork** (`07`), write a product front-door README + getting-started,
  reframe `00–11`/`08` as explicitly-labeled `docs/design/` provenance, and do a user-language pass over the skill
  `description:` fields (the internal vocabulary that ships *inside* the package). Onboarding prose written against a
  moving Phase-3 target churns, so it's scheduled for **Phase 4**, owned now so it can't get lost. Cousin of the
  state-view + version-update items. **[core — Phase 4]**
- **Validation gaps** — real orchestrator→agent **dispatch** in a harness run; `@import`-survives-`/compact`;
  whether `verify` samples the real `git diff` vs trusts the `changelog` (#8); **shipped bash glue assumes a
  bash interpreter on the target OS — unverified on native Windows (D89; the D71 split stands, no refactor)**. **[stageable]**
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
**2026-07-03: the guiding-doc coherence pass is DONE** (a lightweight fan-out found + fixed a systemic status-drift
regression) and **single-source status is adopted (D80)** — an ownership map (one owner per fact-domain: roster
count → `10`'s table · phase/what's-left → `11` · decisions → `08`), guarded by a `check-status-coherence.sh` gate
+ a capture-time blast-radius sweep (resolving D64's two prevention follow-ons). **Phase 1 (close the foundations)
is COMPLETE.** 2026-07-04: the **`align` alignment-scan skill + `check_contracts.py` contract linter are built
(D81)** — the mechanical layer validated against the pressure-test register; the semantic layer rides Phase 2/3.
**2026-07-05: the pre-Phase-2 pressure-test RESOLVE PHASE is COMPLETE** — the ~57-finding register triaged +
fixed + captured as **D82–D88** (6 clusters, all committed + pushed), adding two mechanical plan-coverage gates
(`check_criterion_discharge`, `check_decision_coverage`); the sole deferred build-task is the D84 physical
skill→agent moves, listed under `[stageable]` below. **2026-07-06:** a pre-Phase-2 `align` **cold-audit** fixed
10 doc↔artifact coherence findings + built the **tier-2 `check_enum_coherence.py`** gate and the base-skill
linter fix, and reaffirmed the D71 bash/python split (no refactor; the shipped-glue Windows-portability gap is
tracked in `07`) — **D89**.)*
**Phase 2 — Define the website + demo (design, not build).** Close the Space-3 and Space-4 *design* questions
as a complete spec: the website screen list / contact-UX / stream-vs-snapshot / stack, **and** the demo skill
mechanics (serving/running the sandbox, refine limits, on-disk location) + the checkpoint data model /
triggers. *(**COMPLETE — all five clusters A–E CLOSED (D90–D107).** A = the
checkpoint/console runtime + bus substrate (A1 block/resume + interleaving + context, D90–D92, empirically verified
on `claude v2.1.209`; A2/A3/A4 bus contract/lifecycle/trust, D93–D95, four research fan-outs). C = checkpoints (C1
data model, C2 triggers, C3 help set — the judgment/action taxonomy + verb-enum verdict + plural machine-verified
setup gate + the MVP help set, via two research fan-outs). B = the console (D99–D101 — a read-only supervision cockpit +
screen list + snapshot-poll + "my requests" surface · a stdlib-Python detached daemon + zero-build CSP-clean page ·
the two-event notification taxonomy, via two research fan-outs). **D = the demo skill (D102–D104 — serving/format +
sandbox-CSP isolation · refine cap · on-disk location, via two research fan-outs). E = cross-cutting (D105–D107 —
the outward-action outbox · commitment-status storage · project-map residuals, via one research fan-out).**
**Phase-2 DESIGN COMPLETE → Phase 3 (build the website).** The full agenda + per-item status is below.)*
*(**Pre-Phase-3 gate CLOSED — D108–D113, 2026-07-16.** An autonomous pressure-test + coherence cold-audit
(`reviews/pre-phase3/`) surfaced six must-resolve substance findings; all six are now decided, with JF1/JF2/JF4/JF9
folded in: **D108** inbox consume (consumed-set + per-kind anchors + watermark GC + the drain wired into the
drivers) · **D109** single-orchestrator = an operator-guaranteed run-constraint, not enforced · **D110** the harness
leaves the outward path, `config.outward` is sole owner, and the **`guard.sh` push floor is BUILT** (absolute on
protected branches; it also closed a live D87 bypass) · **D111** the bus daemon owns the away-alert (not the
`Notification` hook), deadline/reminder pinned, the secret store adopted · **D112** remote = a structural two-socket
split behind a declared identity transport · **D113** the runner onto the critical path + this section's increment
reframe. No register residual.)*

### Phase 2 — design agenda & dependency sequence *(the resume map)*
The website+demo design decomposes into five clusters; the dependency spine is **A → C → B → D → E**
(A was the linchpin — the runtime block/resume + bus substrate everything else hangs off). Status per item:
- **A — bus / comms substrate. CLOSED (D90–D95).** **A1 block/resume mechanism (D90):** checkpoint = durable park,
  resume via `claude --resume` (verdict-as-prompt), manual restart in MVP / local relaunch-runner later; **+ D91
  interleaving, D92 context.** **A2 bus contract (D93):** single-writer ownership + atomic-publish + a two-mechanism
  protocol (sync reads · async commands) + one typed inbox (`verdict|intake|control|release`) — the orchestrator is never an
  HTTP responder; the conversation corollary (dialogue = terminal, bus = requests + bounded clarifications).
  **A3 website/bus lifecycle (D94):** a session-independent detached daemon, ensure-running via `flock`-authority +
  token'd `/health`, `POST /shutdown` + idle-janitor; WSL2 dies-with-terminal. **A4 local-bus trust (D95):**
  capability token + Host-allowlist + loopback bind. **(The "tunnel stays warning-only/unauthed" arm is superseded
  by D112** — a structural two-socket split behind a declared identity transport; the loopback Host-allowlist stands
  unchanged on the full-surface socket.)
- **B — console. CLOSED (D99–D101).** **B1/B2/B3 console model (D99):** MVP = a read-only supervision cockpit (home =
  run-status; map = a **tab**, not home, not the first cut) + snapshot-poll refresh (chained-`setTimeout` + `version`/`ETag`
  gate; no SSE in MVP) + the contact-UX (verdict + intake POST forms + a **"my requests"** async-feedback surface that
  rides the polled state, keyed by `localStorage` ticket ids). **B4 stack (D100):** a single-file stdlib-Python daemon
  (`http.server.ThreadingHTTPServer`, the D94 detached daemon) + a zero-build static page (vanilla default / Preact+htm
  escape hatch), the daemon serving a strict `script-src 'self'` CSP — over-determined by A2/A3/A4 + the pure-config rule.
  **B5 attention (D101):** notify on exactly two events (checkpoint-raised · loop hard-stop/escalation); reminders
  ride the D97 timeout. **Mechanism corrected by D111** — the always-alive **bus daemon** owns the alert (watch
  `parked/` → alert → re-alert on `config.checkpoint.reminder_hours` → escalate past the absolute `deadline`), not
  the D90 `Notification` hook, which cannot fire while the loop interleaves and is dead when it whole-parks;
  `config.notify`'s webhook is the away channel (no webhook ⇒ no away alerting).
- **C — checkpoints. CLOSED (D96–D98).** **C1 data model** — the verb-enum verdict (`{outcome: approve|changes|
  reject, notes, returns?}`) + plural machine-verified setup gate (`request.tasks[]`, within-plan coalescing) atop
  the D90/D91 park model. **C2 triggers (D96)** — judgment/action taxonomy; declared-upstream (qa=D30, demo=D22
  gate, reconcile=ingest) + setup's spec-`integrations[]` + execute-discovered path. **C3 help set (D98)** —
  MVP = contextual steps + verified deep-links + breadcrumbs; screenshots/screen-share/live/agent-automation deferred.
- **D — demo skill. CLOSED (D102–D104).** **D1 serving/format (D102):** a build-free, self-contained static
  bundle (no external hosts / no eval; vanilla or vendored htm+preact — the D100 idiom) the D94 daemon serves
  under a `sandbox`-directive CSP opaque origin + iframe-sandbox (isolated even top-level); demo = look, console =
  verdict form; joins the daemon's static-asset (token-free) serving class; rides the remote surface for free (D112).
  **D2 refine cap (D103):** ≤3 regenerations (`config.demo.max_refine_rounds`), never auto-proceed → escalate to
  live `discuss`. **D3 on-disk (D104):** `.workflow/demos/<item-id>/`, gitignored runtime, pruned on resolve.
- **E — cross-cutting. CLOSED (D105–D107).** **E2 outward-action permission model (D105):** a **transactional-outbox**
  queue (`.workflow/outbox/`, retiring the D60 `checkpoints/`) — **not** a checkpoint (an outward action never parks
  the ticket); `guard.sh` floor + a coarse `config.outward` allow|ask allowlist; the loop defers + continues, a
  console **`kind: release`** batch-approval (explicit `action_ids`) drains it; state-bound + TTL'd + no durable ledger.
  **E1 commitment-status storage (D106):** **spec-inline**, human-owned (never node frontmatter — a second copy that
  drifts + regen-clobbers); the drift check reads it **code→intent**. **E3 project-map residuals (D107):** the four
  D70 residuals confirmed parked (tab-not-home D99; durable-flow ≈ D78; capture D78; non-Python + remote-auth open) —
  the one E2-forced call: **outward-release is loopback-only** (**realized structurally by D112** — release lives on
  the never-fronted loopback socket, since a Host-header policy could not enforce it; and D112 extends the taxonomy:
  credential-bearing setup verdicts join release, because D90's verdict-as-authoritative-prompt makes *any* forged
  verdict agent control).

**Recommended next slice:** **Phase 3 is UNDERWAY — increments 1–5 are BUILT (D115/D116 · D117/D118/D119 · D120 ·
D122), the first MVP goal is met, and away is now *triggerable* AND *actionable***: a verdict POSTed from the console
lands durably and unparks the loop, the daemon alerts an away human that a verdict is owed, and that human can now act
on a checkpoint from a phone over a declared identity transport. Next is **increment 6 — the relaunch-runner** (D113):
away becomes *completing* — the last link that resumes a whole-parked loop without a human at the terminal.
*(**The build is pressure-testing the design, as intended.** Increment 1 alone found the substrate unbuildable as
specced — a pinned path could not be *found* — and **measured two stated mechanisms to be wrong**: `flock` does not
fail on the repo mount, while file *mode* does, silently and open. Both are the reverse of what the spec asserted,
and neither was reachable by re-reading; the 9p mount reports success in both failing cases. **Increment 3 held the
pattern, and widened it past the filesystem:** the D108 watermark was measured to **delete a message nobody
consumed** (it rested on an ordering guarantee nothing provided — D118), and the drain's rule (3) was **followed by
1 of 3 real sessions** because it lived in this log and never reached the driver artifacts (D117). Both were found
by *driving*, not reading — and the watermark's second bug survived 27 green unit tests, surfacing only when a real
session recorded ids one at a time, exactly as the brief asks. **Increment 4 held it again, and past the
filesystem:** alert state had no home (in-memory ⇒ WSL-restart spam), and three stated mechanisms measured wrong —
`enable-linger` is the wrong *layer* for the WSL death (the daemon is in `/init.scope`, the killer is Windows-side),
`config.json` was marked `bus:none` on the increment that reads it, and the desktop toast fails for the wrong stated
reason (no name owner, not "no session bus"). **Increment 5 held it past the filesystem into the trust model:** the
meta-tag token bootstrap, applied naively to the remote page, would have served the second-factor token to anyone
past the transport — nullifying it; the remote coordinates were framed per-boot, which breaks a one-time phone
pairing on every WSL restart; and A's Host-allowlist, left loopback-only, would 403 a forwarded-Host proxy entirely.
Three of the four were re-measured before the build, one surfaced in it. **Drive them on the real filesystem, with a
real model.**)*
**Phase 4 — Build the demo, then the public-release surface.** The demo (Space 4), plus the **public-repo identity +
onboarding** pass (the one-repo-vs-two fork · a product front-door README + getting-started · the construction-vs-product
reframe of `00–11`/`08` · a user-language pass over skill `description:` fields — D121, `07`).

**The MVP away-autonomy boundary (D113 — locked, eyes open).** With the runner in, away-autonomy is **real
end-to-end**: alerted anywhere (D111 webhook) → act from a phone (D112 remote socket) → the verdict lands durably
(D93/D108) → **the runner resumes the loop autonomously**. The residual bounds, stated plainly:
- **Release + credential-bearing setup verdicts are loopback-only** (D112) — be at the machine to authorize an
  outward action or hand over a credential (*unless* the transport is E2E/Tailscale, which unlocks the credential case).
- **Protected-branch pushes never auto-fire** (D110, absolute) — a human moves `main`.
- **Remote needs a declared identity transport** (D112); **no webhook ⇒ no away alerting** (D111).
- **On WSL, away alerting is conditional on a Windows-side setting the package cannot reach** (D120) — the daemon
  dies with the last terminal unless `.wslconfig` sets `vmIdleTimeout=-1`; the daemon surfaces this in `status`
  rather than implying an alert that will not arrive.
- **One orchestrator is operator-assumed** (D109), with the runner's liveness marker as its one exception.

Everything `[stageable]`/`[later]` — the `build-once-per-wave` coordinator, model/effort routing,
packaging, the state-view, the version-update skill, **and the D84 skill→agent reclassification** (`execute` +
`create-demo` → leaf agents: the file moves, agent-format rewrites, orchestrator dispatch-by-kind wiring, and the
`17 skills + 2 agents` → `15 + 4` count update — a dedicated session, validation-blocked until the loop runs) —
slots around these phases as it pays off. *(The **local relaunch-runner** left this list: D113 pulled it onto the
critical path as Phase-3 increment 6.)*

## The one-liner
The engine **drives** and is now **self-maintaining** (retention + freshness + docs-root) and **disciplined**
(skill deltas + `rules/` + the drift-gate authored — bar the per-stack `checks.sh` generator). What's left is
to make it **knowledge-complete** (generation → ingest),
**visible** (the console + bus), and **alignment-ready** (the demo + checkpoint mechanics). The bus is the one
"enhancement" that's actually on the critical path for *unattended* autonomy — not merely later.
