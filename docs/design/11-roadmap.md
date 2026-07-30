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
  mechanical step + git `pre-commit` backstop + the fixed `checks.sh` runner + generated `checks.env` ·
  `prioritize` drift-ticket queue — D40/D65/D67; `checks.sh` shipped fixed + driven, D127).
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
  (`config.runner.enabled`), and it retires D92's manual-`/clear` stopgap. **BUILT 2026-07-19 (D123)** as Phase-3
  increment 6 — the `orchestrator.lock` liveness marker + the `loop.sh` launcher; driven end-to-end on a real model.
  **[core — DONE]**
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
  backstop + the fixed `.workflow/checks.sh` runner (+ generated `.workflow/checks.env`), and the `prioritize`
  drift-ticket queue. What makes output *disciplined*, not just working. **[core — DONE; `checks.sh` shipped
  fixed + driven end-to-end, D127]**
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
     dead-letter escalation), the thrash/crash arm deferred to increment 6 with its liveness signal (**now closed — D123**); the **doorbell**
     webhook payload carries no request body. *Away becomes triggerable.*
  5. **The remote socket** — **BUILT 2026-07-19 (D122)**: the structural two-socket split — Socket B loopback/full-
     surface unchanged, Socket A the reduced remote surface (reads · opinion verdicts · static demo) bound only when
     `config.remote` declares a transport, gated by a distinct **persisted** token as second factor over the transport
     identity. Building sharpened four points (the token never on the surface it gates · stable-not-per-boot
     coordinates · a **structural** `returns`/`tasks` credential boundary, not the `_is_sensitive` heuristic ·
     `public_url` load-bearing for the forwarded-Host allowlist); pairing ships **copy-paste**, the QR deferred as a
     scoped fast-follow. *Away becomes actionable.*
  6. **The relaunch-runner** — **BUILT 2026-07-19 (D123)**: the daemon hosts a runner job that, when there is a
     pending `verdict`/`intake` and no orchestrator holds `orchestrator.lock`, spawns a fresh `claude -p` (a clean
     window per ticket) which cold-starts and drains the durable verdict — resuming the loop autonomously. Liveness is
     a published `flock` (a human via the shipped `loop.sh` launcher, the runner via `flock -n`; a `/proc` scan was
     measured unsound); a crash/stall relaunch backs off → hard-stops → fires the away alert (closing D120's thrash
     arm). *Away becomes **completing**.* This is the LAST increment — **the console + bus component is COMPLETE.**
  **[core for unattended autonomy — fully designed (D93/D94/D95 + D108/D111/D112/D113); build = Phase 3 — **COMPLETE**.
  **Increments 1+2 BUILT 2026-07-16 (D115/D116** — `scripts/bus.py` + 39 fixture tests, gate suite 89 → 128);
  **increment 3 BUILT 2026-07-16 (D117/D118/D119** — `scripts/drain.py` + the POST surface; gate suite 128 → 177);
  **increment 4 BUILT 2026-07-18 (D120** — the notifier; gate suite 181 → 199);
  **increment 5 BUILT 2026-07-19 (D122** — the remote socket / two-socket split; gate suite 199 → 235);
  **increment 6 BUILT 2026-07-19 (D123** — the relaunch-runner + the `loop.sh` launcher; +13 fixture tests).
  **The away channel now closes END-TO-END: a verdict lands durably (increment 3), the daemon alerts an away human
  (increment 4), who acts from a phone over a declared identity transport (increment 5), and the runner resumes the
  whole-parked loop autonomously (increment 6). All six increments are BUILT; the component is done.]**
- **C-map — project map + flow view** (D70) — a read-only cluster diagram over the code-map `graph.json`
  (impact-lens sizing, directory clusters, semantic zoom); static skeleton + a reserved **flow-overlay** layer
  (runtime differential capture — a direction, mechanism OPEN), and a **node→ticket** intake action (D69-triaged).
  Structural face of the project-state view. Stageable read-only atop C1; overlay + capture need later arms.
  Plus **remote control** = opt-in phone access — **now a two-socket split behind a declared identity transport
  (D112: Cloudflare Access | Tailscale), not the old unauthed warning-only tunnel** (which was unbuildable). **[stageable; overlay later]**
- **Open design** — **CLOSED (D99–D101):** the console model + screen list (map = **tab**, not home, not the first
  cut) + snapshot-poll refresh + the contact-UX (verdict/intake forms + a "my requests" surface) (D99); the stack —
  a stdlib-Python detached daemon + a zero-build CSP-clean page (D100); the two-event notification taxonomy (D101).
- **Console as the bootstrap front door + cockpit bootstrap-progress render (D132/D133)** — daemon-ensure early in
  `/start` (now step 5), prominent URL + best-effort browser auto-open, the stated interaction contract, and the
  cockpit "Now" rendering the bootstrap `phase`/step from `state.json` (`bus.py` snapshot + page row). Decided from
  the first lived onboarding; built same day. **[core — BUILT (D132/D133); RE-DRIVEN (D138)]**

### Space 4 — Checkpoints & the demo skill
- **Demo skill mechanics** — **DESIGNED (D102–D104) → BUILT 2026-07-19 (D124), Phase-4 first half:** the D94
  daemon now serves `/demo/<id>/` on both sockets under a `sandbox`-CSP opaque origin (D102), with the refine cap
  (D103) and on-disk location (D104) wired. The build **drove the isolation in a real browser** (opaque origin at
  top-level *and* framed) and **`create-demo` on a real model** (a self-contained bundle that renders under the
  CSP), and sharpened the design: the `sandbox` CSP enforces *isolation*, not the format discipline (a shipped
  `check_demo_bundle.py` lint does that); the refine count lives at `demos/<id>/.refine.json`; the bundle is pruned
  on terminal resolve by the verdict-apply path with retention's `prune_demos` as the backstop; `os.replace` is
  content-atomic on 9p (a transient open blip self-heals via a read-retry). (`09`.) **[DONE — built]**
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
  invariants). **DRIVEN end-to-end (D130, Phase-5 Wave-2):** brownfield `/start` (§3) → `ingest` → codemap-at-scale
  over a real ~720-file repo → real `research` GATHER → `spec` reconstructed (`unspecified`) → schema-correct node
  seeds → blocking `checkpoint:reconcile` (relocation-aware, daemon-surfaced); adopt-without-clobber held. The drive
  hardened the skill: the `knowledge-node` format got an authoritative `schemas.md` owner, and adopt-existing-docs
  is now case-insensitive (the `architecture.md`/`ARCHITECTURE.md` clobber on a case-insensitive mount).
  **[core for brownfield — DONE: skill authored + driven (D130)]**
- **Ingest bootstrap-context law (D134)** — `graph.json` is machine-data, never read whole into LLM context
  (the mechanical `codemap.py --seed-list` emission replaced the step-3 whole-file read — pins `06`'s deferred
  `[X]` mechanism); `[X]` extraction in batched subagents; a `research` findings bound; the bootstrap motion
  ends the context window at the reconcile park. **[core — BUILT (D134); drive-verified on the real 374-node
  graph; RE-DRIVEN ingest-side (D138 — 744 nodes/2.8s, 36 seeds, graph.json never read whole)]**
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
- **Packaging/distribution** — **plugin packaging BUILT (D125):** the repo is its own marketplace
  (`.claude-plugin/marketplace.json`, `source: ./product`), the plugin root is `product/` with a minimal
  `plugin.json`, and **`product/MANIFEST.json`** is the single ship boundary the leak gate, `/start` install, and
  the release build all derive from — validated + installed + release-built. Residual: the first-launch
  **trust-UX doc** (D58) and `shared/` resolution polish. **[core — packaging built (D125); trust-UX doc stageable]**
- **Public-repo identity + onboarding — DONE (D125, Phase-4 second half).** The one-repo-vs-two fork closed as
  **ONE transparent repo**: `product/` is the plugin root, `product/MANIFEST.json` the authoritative ship boundary,
  the construction record moved to `docs/design/`, a product front-door `README.md` replaced the spec-index (local
  "Home" path dropped), and the skill `description:` fields were scrubbed of construction vocabulary — validated +
  installed + release-built, all gates + the full suite green after the move. Full record: D125 (`07` fork CLOSED).
  **[DONE — D125]**
- **Validation gaps** — real orchestrator→agent **dispatch** ✅ **validated (D128, real-model loop)**; `@import`-survives-`/compact`;
  whether `verify` samples the real `git diff` vs trusts the `changelog` (#8); **shipped bash glue assumes a
  bash interpreter on the target OS — unverified on native Windows (D89; the D71 split stands, no refactor)**. **[stageable]**
- **Commitment-status storage** — where locked/provisional/unspecified is recorded (spec vs node
  frontmatter, `09`). **[stageable]**
- **Project-state view (user-raised)** — a synthesized "where is this project" surface (done · how it
  connects · what's left); likely **generated** (a `status` skill / console screen). Prereq for
  **self-hosting** this project with itself. **[stageable]**
- **Framework version-update skill (user-raised)** — `/update` pulls the latest public-repo package +
  **migrates** schema/format changes (not a blind overwrite). Follow-on to packaging. **Promoted into Phase 6
  (D135)** — the first real out-of-tree install now exists and will go stale; constraints pinned (version-stamped
  installs · regenerate `[G]`/never clobber `[D]`-or-adopted · additive over a pre-existing `.claude/`); the
  version-stamp half is BUILT and the **design is SETTLED (D137)**; **BUILT (D139)** — a fixed reconcile runner
  (`update_reconcile.py`) owns the arithmetic, `commands/update.md` the judgment, and `install-set.json` makes an
  orphan provable. **[core — promoted (D135); designed (D137); BUILT (D139) — unexercised on a real target]**
- **Onboarding-experience hardening (D131–D134) — user-lived, decided + BUILT 2026-07-21:** the first real
  brownfield onboarding "performed the task but the process wasn't what it should be" — one-motion `/start` (D131) ·
  console front-door + stated interaction contract (D132) · bootstrap progress signal (D133) · bootstrap context
  law (D134). Record = **Phase 6** (below). **[core — BUILT; RE-DRIVEN (D138)]**

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

**Recommended next slice — Phase 5: pre-test hardening (D126).** Phase 4 is **build-complete** (the demo D124 +
the release surface D125), but "release-ready" was a *build-completeness* claim: the whole **install → `/start` →
loop** runtime has **never been driven end-to-end once** (every Phase-3 increment was driven in isolation; the only
prior loop run — D52 — was a pre-D66 throwaway that *simulated* dispatch). A pre-first-run audit (two independent
sweeps — doc-status vs shipped-code) found a hardening gauntlet that must close before a clean first test,
**including three latent bugs verified against the artifacts** (not just unexercised paths): `checks.sh` ships no
generator yet gates every commit · the hooks read a `state.json` `/start` relocates off a 9p mount (verify-before-
commit silently no-ops on `/mnt/c`) · `verify-verdict` is an unwritten hook↔artifact contract. Sequenced
**greenfield-on-a-Linux-native-path first, then brownfield-on-`/mnt/c`** (the native-path first test collapses the
FS-relocation family out of run #1). Full worklist in `### Phase 5` below; capture rationale in D126.

### Phase 5 — Pre-test hardening: the gauntlet before a first clean end-to-end test (D126)
The unexercised `/start`→loop runtime, audited before a first real run. Tags: **[blocker]** a first run can't
complete without it · **[bug]** a defect reading confirmed against the artifact · **[drive]** authored-but-
unexercised, expected to break on first contact. Two waves; Phase 5 owns the *sequencing* — each item's status
stays in its space above.

**Wave 1 — greenfield on a Linux-native path (the smallest gauntlet). BUILT + DRIVEN end-to-end (D127) — bar two
items.** The three blockers are shipped and driven on a real native-path bootstrap (`~/p5-test`); driving confirmed
the predicted codemap bug **and found a second silent-gate defeat the audit missed**. DONE:
- ✅ **`checks.sh`** — shipped as a FIXED runner (`templates/checks.sh`, copied verbatim) + a generated
  `.workflow/checks.env` data file (stack commands; empty ⇒ skip). The `--fix`/`--check` dispatch + the
  coverage-gate loop over open items are **never LLM-freehand** again (refines D67). **[blocker · bug — DONE D127]**
- ✅ **`verify-verdict` contract** — pinned both sides (`schemas.md`/`verify`: first line exactly `pass: true|false`)
  and the hooks flipped **fail-closed** (proceed only on a well-formed `pass: true`; `.json`/missing/reworded all
  block). Closes a measured fail-OPEN hole. **[blocker · bug — DONE D127]**
- ✅ **Manual workspace-trust** — `/start` writes `projects["<abs>"].hasTrustDialogAccepted` into `~/.claude.json`
  (merge-preserving, idempotent, atomic, safe on an unparseable file). **[blocker — DONE D127]**
- ✅ **`codemap.py` greenfield import-root** — confirmed live (0 edges) + fixed (Python module names relative to the
  scan root, not cwd; brownfield `root="."` unchanged; only `PythonArm` touched). **[bug — DONE D127]**
- ✅ **`checks.sh` `cd`-leak (NEW — off-audit)** — a natural `cd project && pytest` stack command moved the runner's
  CWD via `eval` and **silently skipped every coverage gate**; fixed by running each stack command in a subshell.
  Unit tests missed it (cd-free stubs); only driving surfaced it. **[bug — DONE D127]**
- **Findings folded in (D127):** greenfield can't detect a stack at `/start` (bootstrap `checks.env` is
  coverage-gates-only; stack-enforcer + `rules/` `enforced by:` tag wiring deferred to `tech_stack` lock) · stack
  commands must be scoped to `project_root` · `/start`'s install must honour the manifest `exclude` (test files leak
  into the target today).

**Wave 1 — REMAINING: DRIVEN end-to-end (D128) — both items closed.** The first real greenfield loop ran on
`~/p5-test` against a real `claude` running the **installed plugin**, and found three wrong-mechanism bugs (F1–F3,
below — captured, fix next session per the maintainer). DONE:
- ✅ **Real orchestrator→subagent dispatch + one full real-model loop iteration** — drove `/start → discuss →
  decompose → prioritize → plan-one → decision-engineer → execute → verify → document → commit → setup-checkpoint →
  outbox → release` with a real model. **Both leaf agents dispatched via Task** (`research` through
  `decision-engineer`, `setup-guide` through a setup checkpoint — namespaced `dev-autonomous-workflow:<name>`);
  context stayed clean. codemap resolved the real greenfield import edge; `verify-verdict` first line `pass: true`;
  the **outbox → console `release` → guard push** fired end to end (feature branch, nothing pushed until released).
  **[drive — DONE D128]**
- ✅ **`handoff.md` session-end crash-durability — RESOLVED, no new code (D128).** The premise was largely false:
  the harness `Write`/`Edit` tools are **atomic** (temp + `rename`, inode-verified), so a mid-write kill leaves the
  previous file whole; git backstops the residual power-loss case (committed each item). Fix = **downgrade the
  `schemas.md` claim** to the real guarantee + one rule (**never rewrite `handoff.md` via a `Bash` redirect**);
  **rejected** a shipped publisher (re-buys only what git backstops, adds an F2/F3-class must-call-it fail-open).
  **[design — DONE D128]**

**Wave 1 — FIX SLICE: BUILT + DRIVE-VERIFIED (D129) — all three closed, fail-closed not signal-restored.** Each
finding was reproduced live, fixed, and re-verified by driving on the real `~/p5-test` tree (not by reading). The
spine: **fail closed / derive from the artifact** — never restore the missing signal that made the defeat silent. DONE:
- ✅ **F1 — hollow-scaffold `/start`.** `/start` is now **interactive-only by design** (the `.claude/` write-guard
  above the settings allowlist makes headless self-install impossible for settings/hooks — and the relaunch-runner
  never runs `/start`, so away-autonomy is untouched). Step-0's re-run guard keys on install-**completeness**
  (incomplete → *resume the install*, never "already initialised" over a hollow tree); **step 7 verifies every
  manifest `install[].dest` landed + no excluded test leaked + the daemon answered, and refuses to commit if not**.
  Folded: the install copy honours the manifest `exclude` (the `test_codemap.py` leak), the trust message no longer
  implies the `.claude/` install is prompt-free, and the stale console-write-path "Expand later" bullet is removed.
  **[bug · design — DONE D129]**
- ✅ **F2 — greenfield stack-wiring owner + fail-closed backstop.** *Owner:* the **stack-wiring step** (the
  stack-dependent half of `/start` step 5) is deferred by greenfield to `tech_stack` lock, where **the orchestrator
  re-runs it** (new `loop.md` section) — a one-time transition, router-owned so leaf skills stay in lane. *Teeth:*
  `checks.sh --check` now **fails closed when `project_root` holds source but no `--check` stack command is wired** —
  a forgotten trigger stops the loop loudly instead of waving a failing test through. **[bug — DONE D129]**
- ✅ **F3 — verify-before-commit fails closed (folds the Wave-2 `state.json` bug).** A shared **`hooks/verify_check.py`**
  both hooks call derives the item from the staged `.workflow/items/<id>/` diff (immune to the shape drift *and* the
  path drift), runtime-resolves `state.json` via `runtime.json`, tolerates `current_item` ∪ `position.item`, and
  **fails closed**. Both drift vectors now block on both hooks; the genuine ROADMAP-1 commit still passes off the
  staged diff alone. **[bug — DONE D129; the Wave-2 `state.json` path-drift fail-open is resolved with it].**

**Wave 2 — brownfield on `/mnt/c` — DRIVEN end-to-end (D130); the design HELD, three issues fixed + re-driven.**
Driven on a real full-stack repo (the `stock simulator`, ~720 source files, rich docs) copied under `/mnt/c` (9p):
- ✅ **Hooks hard-code `.workflow/state.json`; `/start` relocates it off a 9p mount** → the verify gate silently
  no-op'd on a relocated tree. **RESOLVED (D129, folded into F3); VERIFIED on a *real* relocation (D130)** — with
  `state.json` genuinely on native ext4 off `/mnt/c`, `verify_check.py` runtime-resolves it and **fails closed**
  (the decisive test + shape-drift + failing-verdict + genuine-pass + an end-to-end `git commit` block; session 12
  had only a synthetic `runtime.json`). **[bug — DONE D129, verified D130]**
- ✅ **The FS-relocation step itself** — driven on the mount it targets. Real model detects the 9p mount → relocates;
  the runtime half lands native ext4 at `0600` (token not world-readable), rename atomic, per-project daemon keying
  holds, and `probe_mode` is load-bearing (warns on 9p, silent on ext4 — the `0777` bug re-measured live). No
  findings — the design was right *and* the mechanism was right. **[drive — DONE D130]**
- ✅ **Brownfield `ingest` entry path** — driven end-to-end (first ever): codemap-at-scale (752 nodes / 0 fails /
  2.8s, both lenses, per-lang tiers) → real `research` GATHER (hub-and-spoke held) → `spec` reconstructed
  (`unspecified`) → node seeds (schema-correct, mirrored tree) → **blocking `checkpoint:reconcile`** parked
  relocation-aware + daemon-surfaced. Adopt-without-clobber held. **[drive — DONE D130]**
- ✅ **`docs/architecture.md` case-collision on case-insensitive mounts (NEW — D130).** The `document`-owned
  `docs/architecture.md` case-collides with an adopted `docs/ARCHITECTURE.md`; on the 9p/Windows/macOS
  case-insensitive mount they are one file, so `document` would silently clobber the adopted doc (measured: same
  inode). Fixed — `document`/`ingest`/`start.md` adopt an existing case-variant **in place**, never a lowercase
  twin; re-driven (no clobber). **[bug — DONE D130]**
- ✅ **`ingest` re-derived the node/spec/parked formats each bootstrap → missed the blocking checkpoint (NEW — D130).**
  The knowledge-node `.md` format had **no owner** in `schemas.md`, so the model hunted 5 files and ran out of budget
  before parking reconcile. Fixed — a new authoritative **`knowledge-node`** section in `schemas.md` (D80) + precise
  pointers from `ingest`/`checkpoint`; re-driven: format reads dropped 5 files → `schemas.md`-only, ingest completed
  in **one session**. **[bug — DONE D130]**

**Opportunistic (real bugs a first run won't reach):** ✅ the `align` skill listed meta-repo-only gates
(`check-status-coherence.sh`/`check-no-spec-refs.sh`) absent from the install manifest and meaningless in a target —
**fixed (D130):** the shipped `align` lists only the gates it installs (`check_contracts.py` + coverage), and
`format.md`'s meta-script reference is dropped **[bug — DONE D130]** · ✅ `start.md`'s "Expand later" prose claiming
the console write-path/forms are unbuilt — **fixed (D129, folded into F1):** the stale bullet is removed **[doc — DONE]**.

Everything past Phase 5 stays `[stageable]`/`[later]` (the living code-map observed layer, D84 reclassification, the
proportional-rigor gate, build-once-per-wave, model/effort routing, the project-map tab, the project-state view,
`align`'s semantic layer, the away-channel config prerequisites) — none sit on "run the loop once." *(Amended
2026-07-21: the first **lived** onboarding opened **Phase 6 — onboarding-experience hardening** (D131–D135, below),
and `/update` left this list into it — D135.)*
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
Three of the four were re-measured before the build, one surfaced in it. **Increment 6 held it into the process model,
and this one spawned a REAL `claude`:** the obvious liveness mechanism — a `/proc` scan for a live `claude` — was
measured **unsound** (Claude Code runs a constellation of claude-named helper processes sharing the repo cwd), forcing
a *published* `flock` marker and the `loop.sh` launcher (real orchestrator-side scope, exactly as predicted); and the
drive surfaced a mechanism wrong only when run — an **untrusted workspace makes `claude -p` ignore the settings
allowlist and stall**, which no static read shows, and which drove a stall-timeout the crash-only design lacked. The
resume path was **driven end-to-end on a real model** (a runner-spawned `claude` drained a durable verdict and advanced
the watermark), not reasoned. **The Phase-5 Wave-1 drive held it a seventh time — the first *whole loop* on the
*installed* plugin (D128):** three findings, two of them **silent safety-gate defeats** — `checks.sh --check` passes a
failing test because nothing fills `checks.env` at stack-lock (F2), and verify-before-commit disarms itself when the
orchestrator writes a `state.json` shape the hook can't read (F3) — plus `/start` half-installing to a hollow scaffold
non-interactively (F1). None was reachable by reading; F2/F3 survive green unit tests exactly as the pattern predicts.
And the *opposite* also held: the feared `handoff.md` tear **couldn't be reproduced** — the harness write is already
atomic, so a spec mandate was over-stated, not unmet. **And the Wave-1 FIX SLICE held it an eighth time, from the
other side (D129):** fixing F2/F3 confirmed the *cure* is the same shape as the disease's discovery — **fail closed /
derive from the artifact, never restore the missing signal** that made the defeat silent — and each fix was proven
only by re-driving on the real tree (the fix that passes the genuine model-produced commit off the staged diff while
blocking the drift vectors is not one a re-read would have trusted). **Drive them on the real filesystem, with a real
model — and fix them fail-closed.**)*
**Phase 4 — BUILD-COMPLETE (not yet runtime-validated).** The demo (Space 4) is **built (D124)** and the
**public-release surface is built (D125)**: one transparent repo, `product/` as the plugin root,
`product/MANIFEST.json` as the single ship boundary, the construction record reframed into `docs/design/`, a product
front-door `README.md`, and the skill `description:` user-language pass. But the MVP is **not yet release-ready**: a
pre-first-run audit (D126) opened **Phase 5 — pre-test hardening** (the unexercised `/start`→loop runtime + three
latent bugs), the next slice before a clean end-to-end test. Everything past Phase 5 is `[stageable]`/`[later]`.

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
packaging, the state-view, **and the D84 skill→agent reclassification** (`execute` +
`create-demo` → leaf agents: the file moves, agent-format rewrites, orchestrator dispatch-by-kind wiring, and the
`17 skills + 2 agents` → `15 + 4` count update — a dedicated session; **the loop has now run (D128), so this is no
longer validation-blocked**) — slots around these phases as it pays off. *(The **local relaunch-runner** left this list: D113 pulled it onto the
critical path as Phase-3 increment 6. The **version-update skill** left it too: D135 promoted it into Phase 6.)*

### Phase 6 — Onboarding-experience hardening (D131–D139) — **COMPLETE: D131–D136 BUILT + RE-DRIVEN (D138); `/update` BUILT (D139). Residual: the D136 governor's cycle is still unexercised.**
Born from the first **lived** onboarding — the maintainer's real brownfield run on `idea testing` (WSL over
`/mnt/c`, 2026-07-20). The *process* held (D130's correctness stood: full bootstrap → ingest → reconcile → a real
feature item landed and parked cleanly), but the *experience* failed: the motion split into two chats at the
scaffold commit, the console never surfaced (the daemon was live the whole time), ~52 silent minutes read as
"stuck," and the session ended at ~600k tokens. **The `product/**` pass landed same-day (330 tests green; the
seed-selection drive-verified against the real run's 374-node graph). The phase's exit test is a re-driven live
onboarding — not yet run.** Tags: **[ux]** first-run experience · **[ctx]** context economy · **[fwd]** install
lifecycle.

- **One-motion `/start` (D131)** — `start.md`: the bootstrap-phase ledger in `handoff.md` (written at each phase
  boundary); §0's guard keys on **bootstrap**-completeness (installed-but-not-ingested → *resume at
  `ingest`/`discuss`*, never "already initialised"); §2/§3 are continue-in-this-session imperatives; §0's
  "install complete → fully initialised" conflation fixed. Motion ends at the first human gate (reconcile park /
  discuss). **[ux — BUILT (D131); RE-DRIVEN (D138)]**
- **Console = the bootstrap front door (D132)** — `start.md`: daemon-ensure is now step 5, immediately after the
  step-4 install (rules-wiring moved to step 6); URL surfaced as a headline + best-effort browser auto-open
  (`wslview` → `xdg-open` → `open` → `explorer.exe` chain, printed URL as fallback); the one-paragraph
  interaction contract (terminal = dialogue · console = progress + intake + checkpoints) stated at daemon-up and
  motion-end; intake-during-bootstrap semantics documented (queued in `inbox/`, drained at the first boundary
  after reconcile). **[ux — BUILT (D132); RE-DRIVEN (D138)]**
- **Bootstrap progress signal (D133)** — the motion writes `state.json` `phase: bootstrap` + node + a
  human-readable step marker at every stage boundary (`start.md` §1 preamble + `ingest`'s stage rule); the
  cockpit "Now" renders the `phase` row (`bus.py` snapshot + page); the fields have their `schemas.md` owner
  (D80). **[ux — BUILT (D133); RE-DRIVEN (D138)]**
- **Bootstrap context law (D134)** — `codemap.py --seed-list K --include <spec-core>` emits the bounded seed
  list + per-node frontmatter (spec-core first, then top-K per lens; 2 new tests; drive-verified read-only on
  the real 374-node graph → 30 seeds); `ingest` step 3 forbids whole-graph reads and runs the extractive
  `purpose` pass in batched subagents; `research`'s charter bounds `findings` (pointers, never file bodies);
  `ingest`/`start.md` state plainly that the motion ends the context window at the park.
  **[ctx — BUILT (D134); RE-DRIVEN (D138)]**
- **Version-stamped installs (D135)** — `/start` step 7 writes `workflow_version` (from the plugin's
  `plugin.json`, currently `0.1.0`) into `.workflow/config.json`; `schemas.md` owns the field.
  **[fwd — BUILT (D135)]**
- **`/update` — BUILT (D139)** — constraints pinned by D135 (regenerate `[G]`/`graph.json` under the new schema ·
  never clobber `[D]`/adopted docs (D39/D50/D130) · diff against the manifest `install[]` map over a pre-existing
  `.claude/`); **design (D137):** a 3-way file taxonomy (package-refresh · target-preserve · regenerate-from-code),
  version-stamp-driven, + four calls (a **command** sibling of `/start` · package-owns-`settings.json`/user-owns-`.local` ·
  record-install-set→proven-orphan-removal · unify-greenfield-on-marked-block). **Built (D139)** as a split:
  `scripts/update_reconcile.py` ships **fixed** and owns the arithmetic (`plan`/`apply`/`record`; writes only
  package-owned paths, proven by a whole-tree snapshot test; `apply` **exits 2** rather than overwrite an edited
  `settings.json`/brief without `--confirm-overwrite`), `commands/update.md` owns the judgment. `install-set.json`
  (committed) is the ledger that makes an orphan provable; both `/start` tweaks landed. **Unexercised on a real
  target** — a read-only `plan` against `idea testing` is all that has run (it found the `.pyc` exclude hole).
  **[fwd — promoted D135; designed D137; BUILT D139 — `/update` on a real install still pending]**
- **Interactive context governor (D136)** — a shipped **statusline** budget-warning (`config.context.warn_pct` %,
  never a hardcoded 300k) → **`/dispatch`** on-demand `handoff.md` → `/clear` → **`SessionStart`**(clear)
  auto-rehydrate, with a **`PreCompact`** backstop. The context-management mechanism interactive (`runner:false`)
  sessions never had — the away-runner (D123) retires the manual `/clear` cycle only in away-mode; detection must
  live in the statusline (the one surface the running token count reaches). **BUILT 2026-07-26** (`product/**`):
  `scripts/statusline.py` (composes over a `/start`-captured `statusline.delegate`, never clobbers), `commands/dispatch.md`,
  `hooks/session_start.py` (SessionStart `clear` → re-inject `handoff.md`), `hooks/precompact.py` (both `manual`+`auto`,
  never blocks); `config.context.warn_pct` + `statusline.delegate` own their `schemas.md`; 20 governor tests + full
  321-test suite + 5 meta-gates green. **[ctx — BUILT (D136); installed + rendering, but the /dispatch→/clear→rehydrate CYCLE stays UNEXERCISED — the banner never fired in the D138 re-drive because the context law kept the window lean]**

**Sequence (set 2026-07-26) — COMPLETE.** Build the governor (D136) **[BUILT 2026-07-26]** → forced-reinstall the
plugin to HEAD (a version-pinned `update` is a no-op — verify `gitCommitSha` == HEAD) → **one clean re-drive on a
pristine p5-brownfield** **[DRIVEN 2026-07-27 — D138]** → design + build `/update` **[D137 designed · D139 BUILT]**
→ **`/update` the real `idea testing` install onto HEAD** — **DONE 2026-07-30 (D143)**. That last step had been
gated on Phase 7 (a machine rebuild stranded that install's runtime half, D140), so it ran *behind* `/rebind` on
the same project, in the order D141 set: force-reinstall at HEAD → `/rebind` → `/update`. It paid for itself — the
install turned out to be missing **five** package files outright, including the `SessionStart(clear)` rehydrate, so
a `/clear` there had been dropping into an empty session while the docs described resuming from `handoff.md`. The
interaction-model rework (browser-primary async chat — `07`) is what now sits behind this.

### Phase 7 — Machine-move / portability hardening (D140 audit → D141 design → D142 build → D143 drive → D144 build) — **7a BUILT + DRIVEN on the real install; 7b BUILT and awaiting its drive**
Opened by a real loss, not a hypothesis: a PC rebuild renamed `$HOME`, so `idea testing`'s `runtime.json` names a
directory that no longer exists and its whole runtime tree is unreachable. The audit (D140, measured against that
real install) found the durable half **is** portable — committed, no absolute paths, package included — and the
runtime half is not, with **correct detection everywhere and a repair path nowhere**. **D141 settles the
remediation** (all five `07` questions + two findings the audit missed) and splits it in two, deliberately: 7a is
what `/update` on `idea testing` is gated on; nothing in 7b blocks it. Tags: **[bind]** re-binding a per-machine
artifact · **[dur]** durability of state that should have survived.

**7a — the bind capability — BUILT (D142) + DRIVEN (D143).** Every item below is landed, unit-tested, and has now
run against the real stranded install: `/rebind` classified `RE-CREATE`, the judgment half did all four of its jobs
(rejected the placeholder position and rebuilt it from `handoff.md`, re-opened the parked checkpoint with a fresh
token, wrote `bootstrap: complete`, filed the losses), and `/update` followed on the same project. **Three package
fixes came out of the drive** — `/update` crashing on `chmod` (`38065aa`), the push floor generating an out-of-band
push that skipped the secret scan (`df5440d`), and `/rebind` pointing at the project copy of its own runner
(`b48fdc0`).
- **`/rebind` + `scripts/rebind.py`** — a third sibling on a third axis (*this machine is not the machine that
  installed*), the runner fixed + unit-tested (`check` = dry-run, `apply` = no-op when healthy), the command owning
  the judgment. `apply` classifies **RE-POINT** (literal old path → old path with `$HOME` re-prefixed → canonical
  derived path) · **ADOPT-IN-PLACE** · **RE-CREATE**. **[bind — BUILT (D142): `scripts/rebind.py` + 41 tests; `check` dry-run VERIFIED against the real `idea testing` install (RE-CREATE, wrote nothing). A fourth verb `bind` split out for `/start` — same arithmetic, no loss accounting]**
- **Four routing arms** — `bus.Paths`' raise, `/start` §0 (a fourth completeness state: installed + bootstrapped +
  *unbound* — a **guard that stops and routes**, never a repair), the daemon's exit, and `/update` (**warn and
  proceed** — it is repo-side only, and blocking would deadlock the delivery of `rebind.py` itself). **[bind — BUILT (D142); the daemon's arm is `Paths`' raise, which now names the cure]**
- **`runtime_root_for(project_path)` in code** — `$XDG_STATE_HOME/dev-autonomous-workflow/<slug>-<hash-of-abspath>`,
  shared by `/start` step 3 and `rebind.py`. Today the location is model-chosen prose, so two same-named projects
  cross-bind. **[bind — BUILT (D142): `bus.runtime_root_for()`; `/start` step 3 now shells to `rebind.py bind`]**
- **`.workflow-runtime` identity stamp** `{project_path, bound_at, bound_host}` — `Paths` fails on **mismatch**, not
  just absence; tolerant-read / strict-write so no existing install breaks. **[bind — BUILT (D142); written only on a RELOCATED root — inside `.workflow/` identity is true by construction]**
- **`Paths` fails closed on a weak mount with no pointer** — the *silent* mis-bind (a clone under `/mnt/c` resolves
  to the repo mount and lands the token + `secrets/` on a `0600`-ignoring filesystem). Fallback if the mount probe
  proves unreliable cross-platform: the loud-warn arm. **[bind — BUILT (D142) FAIL-CLOSED, not the fallback: `probe_mode` already MEASURES (0600 create → stat), and a tri-state probe whose *undecidable* arm never stops removes the false-positive risk]**
- **Loss filed as typed `issue` entries in `backlog.md`** — durable *and* bounded by D59's closability.
  **Build-time obligation:** confirm `prioritize`'s GC retires a local issue with **no** `github_ref`; extend that
  path first if it does not. **[dur — BUILT (D142); the obligation FIRED — `prioritize/SKILL.md`'s issue rule was `github_ref`-only and disagreed with `schemas.md`; extended to any done-flipped entry]**
- **Per-machine trust closes for free** — `/rebind` is interactive-only, so running it re-grants `~/.claude.json`.
  Nothing to build. **[bind — closed by D141; stated in `commands/rebind.md` (D142)]**

**7b — the durability trio + the environment probe the drive added — BUILT (D144), NOT YET DRIVEN.** Every item
below is landed and unit-tested (507 tests). The phase's remaining exit test is driving it on a real install.
- **`checks.sh --check` becomes a bindability probe** — a rebound project can be correctly bound and still unable
  to make a single commit, because the committed `checks.env` names a toolchain that is machine-local and
  gitignored. Run the gate *the way the pre-commit hook runs it* and report whether it exits clean — never a
  toolchain-detection heuristic, which would have to know which side of the WSL/Windows boundary each command
  belongs to. **[bind — BUILT (D144) in `rebind.py apply`, the maintainer's call on the open *where*. NOT `check` (its verified contract is "writes nothing"; `TEST` writes caches) and NOT a standing `SessionStart` probe (a full test suite before a session can begin inverts the master rule). Skipped on BIND/HEALTHY; `--no-probe` opts out. It reports the observable and does not diagnose; the output tail goes to stdout, never into the committed loss. The standing half is one routing clause in the pre-commit block message — visible to `claude -p`]**
- **`bus.py park` becomes the writer** of `parked/<id>.json` **and** a fenced `<!-- parked:begin/end -->` block —
  parking has no code writer today, so the mirror cannot become a mechanism without one; it also retires
  `checkpoint/SKILL.md`'s "resolve the runtime root yourself". **[dur — BUILT (D144) + 28 tests. Three calls the code forced: the record arrives on STDIN (four flags cannot make a schema-valid record — no `token`, no `request`); **`unpark` had to be built too**, because prose was accidentally self-correcting and a persisted block only ever GROWS; and the deadline is stamped at microsecond precision, closing an accepted `alert_key` collision that a derived stamp made reachable at machine speed. **AMENDED (D145):** the block is written only at a mutation, so an install that parked *before* the writer had a live record and no block — and `/dispatch` had already stopped hand-writing the prose. Fixed with a `bus.py mirror` verb `/dispatch` runs before writing the anchor; caught by the blast-radius sweep, not by the tests]**
- **`SessionStart` re-asserts `.git/hooks/pre-commit`, non-clobbering** — absent ⇒ install · identical ⇒ silent ·
  different ⇒ warn, never clobber. Proportionate: the git hook backstops *out-of-loop* commits only. **[dur — BUILT (D144); the matcher broadened to `startup`/`resume` (the rehydrate stays `clear`-only) because the motivating case is a CLONE, which runs neither `/start` nor `/rebind`. "Warn once" is keyed by the foreign hook's sha256 in `.git/hooks/`, so a different foreign hook warns again. `/rebind` calls the same code path via `--assert-hook`. Residual STANDS: the warning is invisible to `claude -p`]**
- **`config.json` `secrets_required[]`** — key names only, written by the `setup` checkpoint at elicitation; absence
  becomes provable; point-of-use fail-closed stays as the floor. `outbox/` loss is reported, not recovered. **[dur — BUILT (D144); "present" is derived by walking store payloads for key NAMES (entries are keyed by `message_id`, not by credential), deliberately generous because a missed match is noise and a false match is silence. Pure reads, so it runs in `check` too; an absent declaration is "we cannot tell", not "nothing is missing"]**

**The drive that gated all of this is DONE (D143):** force-reinstall the plugin at HEAD → **`/rebind`** on
`idea testing` (which did stamp the missing `bootstrap: complete` — that install predates D131) → **`/update`**, the
run owed since Phase 6. That project is now bound, updated, and pushed. 7b was then **built against that real
evidence rather than a hypothesis (D144)**, which was the whole point of splitting the phase — and it paid: three of
its calls could only be made with the code in front of it, the largest being that `park` needed an **`unpark`**
sibling nobody had asked for, because turning a self-correcting prose mirror into a persisted machine block turns a
missing remover from a non-issue into a block that reports answered checkpoints as open forever.
**What is left in Phase 7 is the 7b DRIVE** — none of the four items has run against a real install. The natural
exit test is the same shape as 7a's: exercise a park→verdict→unpark cycle and a `/rebind` on a project whose
toolchain did not travel, and see what the mirror, the probe, and the declared-secret diff actually say.

## The one-liner
The engine **drives**, is **self-maintaining** (retention + freshness + docs-root), **disciplined** (skill deltas +
`rules/` + the drift gate), **knowledge-complete** (code-map generation → brownfield ingest), **visible + reachable**
(the console + bus, away-autonomy end-to-end), and **alignment-ready** (the demo + checkpoint mechanics). It is now
**packaged for release** — one transparent repo, `product/` behind a `claude plugin install` front door (D125).
It is **build-complete**, and the **whole loop has now been driven end-to-end on the installed plugin with a real
model** (Phase-5 Wave-1, D128): greenfield `/start` → the full build loop → real `research`/`setup-guide` subagent
dispatch → the outbox→release→guard push. That first real run did its job — it surfaced three wrong-mechanism bugs
(F1 hollow-scaffold `/start`; F2 + F3 **silent safety-gate defeats**), and the **Wave-1 FIX SLICE fixed all three
fail-closed and re-drove them on the real tree (D129)**. **Wave 2 is now DRIVEN on the real `/mnt/c` 9p mount (D130):**
the FS-relocation + D129 verify design **held with no findings** (mechanisms re-measured, not trusted — the 9p `0777`
bug is still real, relocation lands native at `0600`, the verify gate fails closed on a genuinely relocated
`state.json`), **brownfield `ingest` ran end-to-end** (codemap-at-scale → real `research` → reconstructed `spec` →
node seeds → the blocking reconcile checkpoint), and three drive-found issues were **fixed + re-driven** (the `align`
meta-gate leak, the `architecture.md` case-insensitive clobber, and an `ingest` format-hunt that a new `schemas.md`
`knowledge-node` owner closed). **Phase 5 is COMPLETE.** The first **lived** onboarding (2026-07-20) then opened
**Phase 6 — onboarding-experience hardening (D131–D139): COMPLETE.** The process held, the experience didn't; the
fixes were decided + built, then its exit test **ran** — the re-drive (D138) confirmed D131–D134 by driving on a
pristine brownfield fixture and found one high-severity integration bug (a D133↔D129 collision that blocked every
brownfield bootstrap commit), and `/update` was designed (D137) then **built** (D139). Two residuals leave the
phase: the D136 governor's `/dispatch → /clear → rehydrate` **cycle is still unexercised** (the banner never fired —
the context law kept the window too lean to trip it), and `/update` has never run against a real install.
**Phase 7 — machine-move / portability hardening** then opened from a real loss: a PC rebuild stranded a live
project's whole runtime tree, and the audit (D140) found no repair path exists for any per-machine artifact. The
remediation was **designed** (D141) then **built** (D142): a `/rebind` command that **binds**, detectors that
**route and never heal**, and a runtime root that finally has a code-owned *derivation* and a verifiable
*identity* — plus the half the audit missed, the **silent** mis-bind on a mount with no pointer, which ships
**fail-closed** because the mount probe measures behaviour rather than guessing a filesystem type. **7a (bind) is
BUILT and now DRIVEN (D143)** on the real stranded install: `/rebind` classified `RE-CREATE` and its judgment half
held, `/update` followed on the same project, and the drive shipped **three package fixes** — `/update` crashing on
`chmod` (the mount it most needed to work on), a push floor that was producing an out-of-band push which skipped
the secret scan, and `/rebind` pointing at the project's own copy of its runner. It also opened the class D140
never enumerated: **the environment**, not the files — a correctly-bound project whose committed `checks.env` names
a toolchain that did not travel cannot make a single commit, and on a mount that cannot `chmod`, a WSL-side agent
cannot install it. **7b — the durability trio + that environment probe — is now BUILT (D144)** against that real
evidence rather than a hypothesis, the reason the phase was split: parking gained a code writer and the handoff
mirror became a re-derived **projection** (with the `unpark` sibling the design had not asked for), the bindability
probe landed **at the machine transition rather than on a timer**, the pre-commit backstop is re-asserted
non-clobbering for the clone that runs neither sibling command, and secrets gained a declared set that makes absence
provable. **What Phase 7 still owes is the 7b drive.** Beyond these, everything is `[stageable]`/`[later]`.
