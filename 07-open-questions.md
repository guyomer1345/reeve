# 07 — Open Questions Register

Deliberately deferred — known unknowns, to close during build or later.

## Must close before build
- **Rest of the macro-loop** — **CLOSED**: the spine lives in `10` + renders as `.workflow/loop.md` (D47);
  the **orchestrator `CLAUDE.md` driver** is specced in `01` (D46); checkpoint = `04`, reset = the
  handoff/resume model (D48). *Intake stage closed in `09`.*
- **Intake follow-ons** (`09`) — engineering-feasibility pass **designed as the proportional-rigor decision gate
  (D69); implementation deferred to `11`**; demo-skill mechanics (serving,
  refine-round limits, on-disk location); commitment-status storage (spec doc vs Space 6 node frontmatter).
  *(Interrupt model closed: pure queue, D26.)*
- **`init` / bootstrap capability** (`10`, D28) — greenfield is straightforward; brownfield **ingest**
  (build the knowledge base + reconstructed spec from existing code) is **DESIGNED (D68) and the `ingest` skill
  is being authored** — the ingest *mechanics* (own per-stack generator, two lenses, three-tier seed,
  `CLAUDE.md`-seeded intent, unspecified-default + reconciliation checkpoint) are closed; the **Python
  code-map extractor is built + validated + wired into `/start`** — only other-language extractor arms remain
  (same `graph.json` contract).
- **Commit-message convention** — **CLOSED (D32):** Conventional Commits + `Refs:`/`Closes:` trailers.
  Remaining sliver: whether the workflow's own generated commits carry the `Co-Authored-By` trailer.
- **Agent roster v1** — **CLOSED in `10`** (names, I/O contracts, skill-vs-agent, topology). Remaining
  sliver: the collision-model **independence test** (`02`) — waves decided the grouping (D36); the
  `prioritize` interrupt model is closed (pure queue, D26).
- **What a checkpoint is** (`04`) — data model now in `shared/schemas.md` (demo/qa/setup + verdict).
  Remaining: which help features are MVP.
- **Outward-action permission model** (`04`, D35) — mechanics of the local-autonomous / outward-gated
  boundary: per-action checkpoint vs standing pre-authorization (config allowlist), batching/queuing of
  pending outward actions, and whether this is a new checkpoint kind (`publish`) or a flavour of the
  existing gate. Affects `commit`'s deferred push, `create-issue` (`gh issue create`), `close-issue`
  (`gh issue close`). MVP-safe default = always-gated per-action; the open part is standing auth + batching.
  **`.workflow/checkpoints/` persistence rides here (D60):** whether outward/setup approvals get a durable
  approval ledger (and its retention) is decided with this model; qa/demo verdicts stay disposable bus messages.
  *Surfaced 2026-06-29 (live: the harness gated a push to `main`).*
- **Website screen list** (`03`).
- **Disk layout** (`05`) — the full file tree + read/write protocols. *(Docs-root unified under
  `<project_root>/docs/` — spec + architecture + knowledge + decisions — D62; diagrams inline, D41.)*
- **Orchestrator hooks** (D58) — `hooks/guard.sh` now enforces **secret-scan** + **verify-before-commit**
  (hard blocks); **outward-action** gating is the settings `ask` rule (deliberate prompt). Still open:
  **build-once-per-wave** (a wave-coordinator, not a command gate); **outward gating under full bypass**; and
  the **command-chaining gap** — broad `Bash` allow + `ask` prefix-match misses `cd x && git push`, so the
  robust outward gate ultimately needs the guard-hook/bus checkpoint-queue, not just `ask` rules.
- **First-launch workspace trust** (D58) — the shipped `settings.json` + hooks are **ignored until the folder
  is trusted**, and the trust **dialog doesn't render in some terminals (e.g. WSL)**; `/start` + setup docs must
  give the manual `hasTrustDialogAccepted` flag method, not just "accept the dialog." (Validated: after trust,
  the dogfood run took **zero** local permission prompts.)
- **`@import`-survives-`/compact`** — a one-session test; if it re-resolves, the brownfield install (D50) can
  switch from the inline marked block to a cleaner `@import`.
- **Console + comms bus** (`03`/`05`) — the **critical-path runtime dependency**: the dogfood showed every
  step autonomy-drives *except* the blocking qa `checkpoint`, which needs the bus to deliver the human verdict.
- **Real dispatch validation** — the dogfood *simulated* the `research` agent dispatch; the orchestrator→agent
  call + structured return is validated in the harness-real run.
- **Package install** — loose `.claude/` files are MVP (D57); plugin packaging + `shared/` resolution open.
- **Adoption follow-ons (D38–D51)** — the **retention & archival law** is **CLOSED**: Layer 0 write-law leak
  closures (D59–D60) + Layer 1 cap-and-archive read law (D61). What remains under it: **Sessions distillation**
  (deferred — lossy/model-authored), `K`/threshold tuning, and **authoring the retention script** (depends on
  the strict `# Sessions` format + the `decision-record` `status` + `handoff.base_sha` fields landing). Also:
  whether `verify` samples the real `git diff` vs trusts the `changelog` (#8).
- **Rules baseline + `/start` enforcement wiring (D40) + two-tier drift defense (D65/D67) — AUTHORED
  2026-07-01.** The `rules/*.md` baseline (enforced-by tags), the `shared/format.md` rules convention, the
  `/start` step-4 enforcement wiring, the `commit` mechanical-gate step, and the `prioritize` drift-ticket note
  are written. **Remaining sliver:** `/start`'s per-stack **`checks.sh` generator** (detect the stack → emit
  the concrete `--fix`/`--check` runner + configs) — a `/start` runtime detail, not yet exercised in a real
  bootstrap.

## Deferred (post-MVP or later)
- **Knowledge graph regenerate-vs-incremental** (`06`) — **RESOLVED (D78):** static layer regenerates + the durable
  *observed* layer is merged on regenerate. New open follow-ons from D78: node-ID stability across renames;
  observed-edge staleness/decay (couples with retention D71); the non-Python runtime-capture mechanism (per stack).
- **Model + effort routing** map (`01`).
- **Collision-model independence test** (`01`/`02`) — waves grouping decided (D36).
- **Arbiter** batch-vs-one input contract (`01`).
- **Optional SDK "runner"** for fully-autonomous restart (`01`) — deferred add-on; MVP uses
  human-prompted restart. Decided in principle; build + verify SDK auth (subscription vs API key) later.
- **Website stack** (`03`).
- **Project map + flow view (`03`, D70) — feature + architecture decided, these bits open.** (1) Map as its
  **own tab vs the console home/overview** (lean: home/overview — it's the structural face of the project-state
  view below). (2) A captured flow as a **first-class knowledge artifact** (versioned, regenerable, `06`) vs
  **ephemeral** (on-demand, discarded — but D78 leans **durable [D] layer**). (3) The **runtime-capture mechanism**
  — **decided (D78):** `verify` is the observer (it already runs the affected flow); mechanism = `sys.monitoring`
  fire-once (Py 3.12+, measured 1.0×) with coverage-harvest (~1.5×) as the universal fallback; trigger selectively
  where an arm's `known_gaps` flag dynamism. Open: the per-stack mechanism for non-Python (reasoned, not measured).
  (4) **Remote-control auth** (Cloudflare Access / token) — reserved, warning-only for now.
- **Automated testing**, **test-from-anywhere**, **paid device/QA platform** (`04`) — designed-for,
  not built.
- **Project-state view (`03`/`05`/`06`) — user-raised 2026-06-30.** No single synthesized "where is this
  project" surface — *what's done · how the pieces connect · what's left*. The data exists but is scattered
  (`00–11` + `08` decisions + this register + `handoff.md` + `backlog.md` + the `docs/knowledge/` graph). The user
  feels the gap **in this spec project itself**, and it bites harder on code projects — and it's a prerequisite
  for eventually **self-hosting** (driving this project's development with this project). Likely a **generated**
  view (D38 — not a hand-maintained doc that rots): a `status`/`map` skill or a console screen synthesizing
  roadmap + backlog + decisions + graph on demand. **The `graph.json` cluster map (D70) is its "how the pieces
  connect" face** — the structural half of this surface.
- **Framework version-update skill (`10`, D57) — user-raised 2026-06-30.** The package is now a **public
  repo**; consuming projects install a snapshot (`.claude/` skills/agents/commands + `templates`/`shared`/
  `hooks`). As the framework evolves (fixes, new skills, schema/format changes) installed copies go **stale**,
  and stale references mislead the loop. Need an `/update` skill that pulls the latest package and re-applies
  it, **reconciling local customizations + migrating schema/format changes** (a version bump can change
  `state.json`/`schemas` shapes — not a blind overwrite). The natural follow-on to packaging (D57); the
  framework-level analogue of the retention/freshness law.
- **Doc-authoring agent (reserved — D65; trigger fired, still not added — D68).** A specialized
  heavy-doc-reconstruction worker (e.g. brownfield `ingest` building a spec from code — a generative task that
  doesn't fit `execute`'s plan-driven model). The "revisit when building brownfield `ingest`" trigger **fired
  (D68)** and the call held: **`ingest` is a thin skill over the existing leaves** (`research` read →
  `document` write), **no new agent** — reserved still, added only if the generic workers prove insufficient in
  a real ingest run. Cousin of the open "engineer agent?" slot (`02`).
