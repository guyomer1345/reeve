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
- **Space 2 — Roster + contracts.** The full roster (its count and the skill/agent split live in the roster
  doc's table, which is the owner — the three heavy leaves moved to `agents/` in D178), I/O schemas,
  hub-and-spoke topology (D24–D34, D53);
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
- **Model + effort routing** — per-task model/effort map (graph-maintenance cheap, planning expensive). Premise
  re-checked 2026-08-05 (D175) and **intact but unbuilt**: no `model:` frontmatter exists on any shipped agent or
  skill, so everything inherits the session model today. Stays deferred — it is a cost optimization with no
  correctness claim behind it, and nothing in the tree asserts otherwise. **[later]**
- ~~**Arbiter input contract** — decide a batch in dependency order vs one at a time.~~ **RETIRED as a line item
  (D175, 2026-08-05): the component does not exist.** `grep -rn 'arbiter'` over `product/` and `10-roster.md` is
  **empty** — the name died into `adjudicate` (the base compare-realities procedure) and `decision-engineer`. The
  *substance* — batch-vs-one-at-a-time ordering — is `prioritize`'s live concern, which already emits independent
  parallel-safe items; if it needs a contract, it gets one there, under its own name. **[retired]**

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
  engineering-feasibility pass; **no new agent** (answers the old "engineer agent?" slot). *(That clause is why the
  separate "engineering-feasibility pass" line item in Space 4 is retired as a duplicate — D175.)*
  **DEFERRED OUT of Phase 10 with a written trigger (D175, 2026-08-05).** Not a blank slate: `grep -rn
  'proportional\|rigor' product/` returns **one** hit — `skills/create-forecast/SKILL.md`, where D162 shipped a
  narrower *skill-owned forecast gate* and recorded that a later universal triage would **subsume** it. So the case
  that actually fires today is already covered. A universal triage over **every** `planner` output is a phase-sized
  capability, not a cleanup item, and folding it into a truth-in-shipping phase would make that phase a backlog with
  a new name. **Promotion trigger — promote when a SECOND narrow gate wants the same triage**; at that point the
  duplication is real rather than hypothetical, and the triage has two callers to be designed against instead of
  one. **[stageable — deferred past Phase 10 on a trigger, D175]**

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
     *(The browser-render residual this once carried was CLOSED by D120 — headless Chrome, read as legible.)*
  3. **POST → inbox + the orchestrator drain** — **BUILT 2026-07-16 (D117/D118/D119)**: `POST
     /api/{verdict,intake,control,release}` → validate → atomic append → `202` + a `Location` ticket that **is** the
     `message_id`; the console's forms + a "my requests" surface that resolves off the per-kind effect anchors (so it
     still answers after GC); inbox GC on the watermark; and the drain **split** — its bookkeeping is `scripts/drain.py`
     (`list` → apply → `record`/`secret`), its apply stays the brief. *The verdict job lands here — the first
     increment to meet an MVP goal* (D93 protocol + the D108 consume model) (*the old "C2"*).
     **3b — the setup verdict form — BUILT 2026-07-31 (D147), DRIVEN 2026-08-02 (D148 + D149).** Increment 3 shipped a form carrying `{outcome,
     notes}` only, against a D99 spec that named `returns` / plural `tasks[]` / steps + verified deep-links +
     breadcrumbs — so **no client could produce a `returns` payload at all**, and D122's Tailscale credential arm
     guarded a payload nothing could emit. Now: per-task rows (own outcome), one labelled input per credential named
     from `request.tasks[].secrets[]`, the `how` steps rendered, a `bus-credentials` page fact so the inputs appear
     only where the socket may carry a key (the `403` stays the boundary), and `returns` **declared** as a
     name-keyed map the bus validates. *The increment-3 tag was BUILT against a spec it did not meet, and the stated
     residual named legibility — which is how a capability gap read as polish.*
     **The browser residual DISCHARGES (D148)** — driven in Chrome against a cloned bed, every phase: the render,
     both graceful-degradation paths, the structured `how` + its scheme filter, the whole credential byte-trail
     (`202` → `0600` inbox → redacted `list` → `0600` store → itemized `rebind`), and every negative path. **The
     credential path did not fail once; the interaction shell around it failed twice**, and only at a human's hands —
     `type="password"` both hid whether a paste landed AND let Chrome offer to save the key to its password manager
     (`autocomplete="off"` cannot suppress that), and a sent verdict left **no evidence it had been sent**, re-arming
     a pristine form that invited a second live credential onto the wire. Both fixed: the input is `type="text"`, and
     `answered_at` is now stamped server-side on the parked record. **Re-driven once more (D149)**, which confirmed
     the unmask at the keyboard (no save-password prompt) and found three more shell defects: the answered card was
     inert but not *legible* (it now dims, keeping the banner and the one live control at full strength); `hidden`
     was **not hiding** (`.verdict` is `display:flex`, which outranks the attribute — fixed globally, since every
     `hidden` toggle on the page rode on it); and the requested "override" **did not exist** — two verdicts for one
     token both sat on the inbox and the FIRST won, so a corrected credential would have lost to the typo. A verdict
     now supersedes an undrained one (the unlink is its shred) and the button appears only while that is possible.
     *The lesson the tag records: six increments of headless rendering could not have caught any of them — every
     defect this increment produced lives in the interaction shell, and every one needed hands. Twice, a DOM
     assertion passed while the page disobeyed it.* **Residual: the re-answer click path has not been exercised by a
     human.**
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
  ~~Plus **remote control** = opt-in phone access — a two-socket split behind a declared identity transport
  (D112: Cloudflare Access | Tailscale), not the old unauthed warning-only tunnel.~~ **The remote half is BUILT and
  this line was stale (corrected D175, 2026-08-05): D122 shipped it as Phase-3 increment 5** — `scripts/bus.py`
  carries the two-socket split, the fixed remote port, the "Pair a phone" surface, the stable (not per-boot) remote
  credential, and A's verdict-only POST allowlist. Only the **project-map tab** remains unbuilt here, and its cost
  is understated: the console is a flat list of `<section>`s with **no tab machinery at all**, so the first cost is
  inventing navigation, not drawing a map. Stays deferred on that basis. **[stageable — remote half DONE (D122); tab + overlay later]**
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
  content-atomic on 9p (a transient open blip self-heals via a read-retry). (`09`.)
  **DRIVEN 2026-08-02 (D150)** — the first runtime validation, which found the demo had never rendered at all: the
  opaque origin makes every subresource `Sec-Fetch-Site: cross-site` and the CSRF gate refused them, so any bundle
  with a sibling file was silently blank. Fixed; isolation re-verified in a browser; the `kind:demo` card, the
  refine round and the terminal prune all exercised. **D154** then put a mechanical floor under "edit the spec
  first, then regenerate" — a refine round that did not move the spec is now refused, because the terminal
  `approve` deletes the bundle and a decision living only in those bytes dies exactly when it is approved.
  **[DONE — built + DRIVEN]**
- **Checkpoint data model + triggers** — **DONE (D96–D98):** the judgment/action taxonomy + trigger rule (setup =
  spec `integrations[]` + execute-discovered; qa=D30, demo=D22 gate, reconcile=ingest), the verb-enum verdict +
  plural machine-verified setup gate, and the MVP help set (contextual steps + verified deep-links + breadcrumbs;
  screenshots/screen-share/agent-automation deferred). **[done]**
- ~~**Engineering-feasibility pass** — the spike that de-risks the technical unknowns the demo deliberately
  skips (`09`).~~ **RETIRED as a separate line item (D175, 2026-08-05) — it is a DUPLICATE.** The proportional-rigor
  gate entry in Space 2 already says, in its own words, that D69 "**Formalizes the engineering-feasibility pass**".
  Same work, listed twice at two places. It travels with that entry, which is itself **deferred with a promotion
  trigger** (below). **[retired — folded into the D69 proportional-rigor gate]**
- **Automated testing · test-from-anywhere · paid device/QA platform** — designed-for, not built. **[later]**
- **`artifacts` has a producer — `request.tasks[].provides[]` (D152 residual, closed by D156).** The non-credential
  half of the `returns` split shipped declared, validated and unproducible: the console's setup form rendered one
  input per declared `secrets[]` name, and `secrets[]` *means* credential. It now renders a second, mirrored input
  per `provides[]` name, emitting `artifacts`. Two declared lists rather than one list with a flag — **which list a
  name came from is what decides the value's protection**, which is the one thing the deleted `sensitive` marker
  could not be. The request-side field is **not** called `artifacts[]` (as this entry previously proposed): request
  and reply deliberately share no key name, and that non-overlap is the only reason `park` can refuse a reply-side
  field on a request at all. It also buys a capability — the inputs are not gated on the credential-socket check, so
  a paired **remote** console can hand back a value for the first time.
  **[BUILT (D156) — NOT browser-driven.** Six tests drive the real shipped `renderTasks`/`collectVerdict` through
  node into the real validator, five of them proven to fail against the unfixed source. But this is the surface that
  broke under human hands in D148/D149/D153, where a passing assertion hid the defect every time — a shim answers
  *"does the code do X"*, never *"does the page do X"*. **Owed: one browser pass on both sockets** (loopback: a
  credential and a provided value in one task land in different fields; remote: the `provides[]` input renders and
  the credential input does not).**]**
- **Specs locked BEFORE the D154 floor may be missing what was approved.** The refine ledger stops the drift going
  forward; nothing checks backwards. Any project whose history contains an approved demo can hold a spec that never
  learned a decision made in a refine round — and the evidence is gone, because the terminal `approve` deleted the
  bundle. Detection is the honest limit here: there is no artifact left to diff against, so this is a **read the
  spec against the item's history** job, not a mechanical one — precisely the shape `align` exists for (spec vs
  decisions vs promises vs the actual code). The one measured instance was repaired by hand during the D154 drive.
  **[DONE — D155 gave `align` the lens; D157 made it able to fire.** D155's cold audit found `align` had been
  *named* the detector and never *given* one, and added the **approved-demo lens**. Reading that lens against the
  shipped mechanics before relying on it found it could not perform the detection: its trigger was "a terminal
  approval with an **absent ledger**", but `.refine.json` lives inside the directory `approve` deletes, so *every*
  approved item matches, forever — a tautology, not a condition. It was also a standing check inside a **diff-scoped**
  pass, so a historical item never entered the work-list at all. D157 fixes all three legs: `check_demo_bundle.py
  --promote` folds the ledger's summary into a committed **`demo-approvals.json`** before the delete (so a promoted
  item is settled mechanically and the un-promoted set is finite and shrinking); `align` step 1 **admits** that
  backlog where scope is decided; and the anchor's `cleared_demo_items[]` remembers a clean read, which the findings
  register cannot — it dedups findings, and a clean read produces none.**]**

### Space 5 — Shared state & bus
- **Read/write ownership per file + the request/response protocol** — **DECIDED (D93):** a single-writer partition
  (zero co-written files; intake promoted through the inbox, not written to the backlog) + atomic-publish + the
  two-mechanism protocol (sync reads · async commands); **the orchestrator is never an HTTP responder.** Bus
  lifecycle D94, trust D95. **[core — designed; build Phase 3]**
- **Outward-action permission mechanics** — **DECIDED (D105, Phase-2 E2):** a **transactional-outbox** queue
  (`.workflow/outbox/`, retiring the D60 `checkpoints/`), **not** a checkpoint; `guard.sh` floor + a coarse
  `config.outward` allow|ask allowlist (standing pre-auth); the loop defers + continues, a console `kind: release`
  batch-approval drains it (state-bound, TTL'd, no ledger). Build rides Phase 3 (with the bus). **[core — designed; build Phase 3]**
- **Symbol-level knowledge paths** — the seam left in Space-6 granularity. Premise re-checked 2026-08-05 (D175) and
  **intact**: edges are file-level throughout, and `shared/schemas.md`'s `## Key symbols` is an explicitly *optional
  extractive aid*, not a resolved symbol graph — so the seam is real and genuinely unbuilt. Stays deferred on size:
  it is an engine-level change to `codemap.py`'s arm contract, not a gap between claim and behaviour, so it is out
  of Phase 10's spine on scope rather than on doubt. **[later]**

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
  **Tier settled 2026-08-05 (D175), against the shipped tree — it was tagged `[core — build next]` here while listed
  `[stageable]`/`[later]` twice below, in the doc that OWNS tier (D80).** `graph.observed.json` occurs in `06`, `11`
  and `08` and **nowhere in `product/`**: there is no producer, no schema and no consumer, and "build next" had been
  stale since Phase 2/3 closed. It is **`[stageable]`**, and the D83 charter revisit stays parked with it. What
  D175 *does* schedule is the separable defect this exposed — **two shipped files assert the layer as if it existed**
  (`scripts/codemap/codemap.py` rests its precision-bias rule on it; `skills/verify/SKILL.md` licenses an observer
  for it), which is a live over-claim whether or not the layer is ever built. See **Phase 10a**.
  **[stageable — arm build thread closed (D77/D79, all 5 measured); observed layer + the D83 charter revisit both parked (D78/D83, tier settled D175)]**
- **Brownfield ingest** — **DESIGNED (D68); the `ingest` skill is AUTHORED** (`skills/ingest/SKILL.md`). A thin
  `ingest` skill over existing leaves (`research` *gathers* → `ingest` *synthesizes* the spec → reconciliation
  `checkpoint`; `document` authors the durable `why`/Sessions later, **not** during ingest — no new agent) that
  seeds behavioural-core **intent from the existing `CLAUDE.md`/spec** (un-derivable from code), builds
  `docs/knowledge/` + a reconstructed `docs/spec.md` (default **unspecified**, reconciliation checkpoint locks
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
  to the project-state view (~~+ self-hosting~~ — **dropped, D175**; the project-state view relation stands and is
  now Phase 10c). **Tier-2/3 drift defense added (D89):** a meta-repo
  `check_enum_coherence.py` (enum + registry coherence, per-commit, beside `check-status-coherence.sh`) + the
  full-surface `align` cold-audit adopted as a phase-boundary ritual; the `adjudicate` contract-linter
  false-positive fixed (0 advisories).
  **[core — skill + mechanical layer BUILT (D81); semantic layer validated Phase 2/3]**

### Cross-cutting — packaging, validation
*(Was "packaging, validation, self-hosting" — **self-hosting is DROPPED (D175, 2026-08-05)**: driving this project's
own implementation with the product is not the right thing for this repo. **Dogfood-validation is untouched and
stays** — driving the product against throwaway or foreign repos as evidence (D52, D125, `scripts/drive-org-mode.sh`)
is this repo's entire evidence discipline. Two different words; only the first is gone.)*
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
- **Validation gaps** — real orchestrator→agent **dispatch** ✅ **validated (D128, real-model loop)**. **Re-checked
  against the shipped tree 2026-08-05 (D175); the three residuals split three ways:**
  - ~~`@import`-survives-`/compact`~~ — **RETIRED, premise moot.** `grep -rn '@import' product/` is **empty**;
    `templates/orchestrator-CLAUDE.md` reaches its files by explicit *Read* instructions, not imports. The gap was
    recorded against a wiring the package does not use.
  - **Whether `verify` samples the real `git diff` vs trusts the `changelog` (#8)** — **real, still open, and now
    cheap.** `skills/verify/SKILL.md` still reads plan↔changelog only, while `hooks/verify_check.py` already runs
    `git diff --cached`: the machinery exists and is simply not wired to the verdict. **Scheduled — Phase 10a.**
  - **Shipped bash glue assumes a bash interpreter on the target OS — unverified on native Windows** (D89; the D71
    split stands, no refactor). Real and untouched. **Scheduled — Phase 10b.**
  **[stageable → the two live halves are scheduled into Phase 10 (D175)]**
- ~~**Commitment-status storage** — where locked/provisional/unspecified is recorded (spec **vs** node
  frontmatter, `09`).~~ **CLOSED — and it was never open: D106 decided it in Phase 2** (*"the spec is the sole
  owner … nodes never store a commitment value"*, with node frontmatter under its **Rejected** line). **This
  entry contradicted the E1 line 100-odd lines below it, which records that same D106 closure — same fact, two
  states, in the doc that OWNS it** (the third such conflict this phase; see the observed layer above). Meanwhile
  `shared/schemas.md` had shipped the refused node field anyway. **Field deleted, spec confirmed sole owner —
  D176 (Phase 10a).** *(D175 scheduled this as a live D80 question, which was itself the stale reading; the
  blast-radius sweep is what surfaced D106.)*
- **Project-state view (user-raised)** — a synthesized "where is this project" surface (done · how it
  connects · what's left); likely **generated** (a `status` skill / console screen). ~~Prereq for **self-hosting**
  this project with itself.~~ **Re-argued and re-aimed (D175):** its only recorded justification was the
  self-hosting prereq, which is dropped — but `07`'s original 2026-06-30 entry carries an *independent* one (the
  gap is felt reading a project, and "bites harder on code projects"). It survives on that, and is built **for a
  TARGET project**, not to read this repo's own construction record — which is also the only form dogfooding can
  validate. **Scheduled — Phase 10c.**
- **Framework version-update skill (user-raised)** — `/update` pulls the latest public-repo package +
  **migrates** schema/format changes (not a blind overwrite). Follow-on to packaging. **Promoted into Phase 6
  (D135)** — the first real out-of-tree install now exists and will go stale; constraints pinned (version-stamped
  installs · regenerate `[G]`/never clobber `[D]`-or-adopted · additive over a pre-existing `.claude/`); the
  version-stamp half is BUILT and the **design is SETTLED (D137)**; **BUILT (D139)** — a fixed reconcile runner
  (`update_reconcile.py`) owns the arithmetic, `commands/update.md` the judgment, and `install-set.json` makes an
  orphan provable. **[core — promoted (D135); designed (D137); BUILT (D139); DRIVEN on the real `idea testing`
  install (D143) — that run shipped three package fixes and is what discharged this]**
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
  live `discuss` — **enforced by `check_demo_bundle.py` since D154**, where a refine round must also be shown to
  have MOVED THE SPEC. **D3 on-disk (D104):** `.workflow/demos/<item-id>/`, gitignored runtime, pruned on resolve.
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

**Phase 5 — pre-test hardening (D126). COMPLETE** (as are Phases 6 and 7 below); this paragraph is the
historical framing of *why it opened*, not a live "next slice" pointer — it read as one for four phases after
Phase 5 closed. **`### Phase 8` (opened D155) is now COMPLETE** — both halves: **8a** BUILT (D165) and **8b —
the interaction-model rework — BUILT + browser-driven 2026-08-04 (D169, `ad9d910`)**. **`### Phase 9` is now
COMPLETE too** (D159–D163): `9a` BUILT + browser-driven (D163 + D166), `9b` BUILT (D167), and **`9c` (org mode)
BUILT + DRIVEN 2026-08-05 (D174, `3816b62`→`1ad7707`)** behind the exit-gate drive it was always held behind.
**`### Phase 10` (opened D175, 2026-08-05) is COMPLETE too** (BUILT D176) — see the section below; like the Phase-5
paragraph above, this is now historical framing and **not** a live "next slice" pointer, and **no successor to
Phase 10 is declared**. Phase 9 closed with no
successor because the remainder read as a menu rather than a sequence; **that was a description of the plan, not a
finding**, and D175 supersedes it by *deciding* to sequence the remainder. What forced the decision was dropping
self-hosting (D175), which was the only candidate spine the menu had. Phase 10's spine is **truth-in-shipping**:
close the gap between what the tree *claims* and what it *does*. Historical framing follows. Phase 4 was **build-complete** (the demo D124 +
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

Everything past Phase 5 stays `[stageable]`/`[later]` (the living code-map observed layer, the D84 reclassification
— *since scheduled as `### Phase 11` (D178)*, the
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
allowlist**, which no static read shows, and which drove a stall-timeout the crash-only design lacked. (The "and
then it stalls" half of that reading was **wrong, and corrected by D173**: it answers and exits 0, so the stall
timeout never fires and the trust read had to become a spawn gate.) The
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
**Phase 4 — DRIVEN 2026-08-02 (D150).** The demo's first runtime validation found that it had never rendered
because it structurally *could not*: the `sandbox`-CSP opaque origin makes every subresource read `cross-site`, and
the CSRF gate refused them, so any bundle with a sibling file was silently blank. Fixed, isolation re-verified in a
browser, and the whole lifecycle (card → refine → terminal prune) exercised. **D154** then gave `create-demo`'s
"edit the spec first" rule a mechanical floor. Historical framing follows. The demo (Space 4) is **built (D124)** and the
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
packaging and the state-view — slots around these phases as it pays off. *(The **D84 skill→agent
reclassification** LEFT this list: it is no longer a deferred file move. D178 measured a real drive and found the
dispatch mechanism itself defective — the shipped skills never reach the workers — so the reclassification is now
scheduled as **`### Phase 11`**, widened to include `document` and carrying the brief's dispatch rule and a
blocking `PreToolUse` gate.)* *(The **local relaunch-runner** left this list: D113 pulled it onto the
critical path as Phase-3 increment 6. The **version-update skill** left it too: D135 promoted it into Phase 6.)*

### Phase 6 — Onboarding-experience hardening (D131–D139) — **COMPLETE: D131–D136 BUILT + RE-DRIVEN (D138); `/update` BUILT (D139). The governor-cycle residual is DISCHARGED (D151) — no residual remains.**
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
- **Version-stamped installs (D135)** — `/start` step 7 writes `workflow_version` into
  `.workflow/config.json`; `schemas-runtime.md` owns the field (the `config.json` section moved there at the D168
  split). **Since 8a it is the commit SHA, not a semver**: D164
  deleted `version` from `plugin.json` so the platform keys delivery on the commit, and D165 built the four-rung
  resolver that reads it. **[fwd — BUILT (D135); the stamp became a SHA in 8a (D164/D165)]**
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
  never blocks); `config.context.warn_pct` + `statusline.delegate` are owned by `schemas-runtime.md` (both moved
  there at the D168 split); 20 governor tests + full
  321-test suite + 5 meta-gates green. **[ctx — BUILT (D136); CYCLE DRIVEN 2026-08-02 (D151) — banner → `/dispatch` (a real `claude -p`; both machine blocks preserved byte for byte) → `SessionStart(clear)` rehydrate → a fresh session resumed from the anchor alone and carried a decision that had existed only in the pre-clear conversation]**

**Sequence (set 2026-07-26) — COMPLETE.** Build the governor (D136) **[BUILT 2026-07-26]** → forced-reinstall the
plugin to HEAD (a version-pinned `update` is a no-op — verify `gitCommitSha` == HEAD) → **one clean re-drive on a
pristine p5-brownfield** **[DRIVEN 2026-07-27 — D138]** → design + build `/update` **[D137 designed · D139 BUILT]**
→ **`/update` the real `idea testing` install onto HEAD** — **DONE 2026-07-30 (D143)**. That last step had been
gated on Phase 7 (a machine rebuild stranded that install's runtime half, D140), so it ran *behind* `/rebind` on
the same project, in the order D141 set: force-reinstall at HEAD → `/rebind` → `/update`. It paid for itself — the
install turned out to be missing **five** package files outright, including the `SessionStart(clear)` rehydrate, so
a `/clear` there had been dropping into an empty session while the docs described resuming from `handoff.md`. The
interaction-model rework (browser-primary async chat — `07`) is what now sits behind this.

### Phase 7 — Machine-move / portability hardening (D140 audit → D141 design → D142 build → D143 drive → D144 build → D146 drive) — **COMPLETE: 7a and 7b both BUILT + DRIVEN on the real install**
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

**7b — the durability trio + the environment probe the drive added — BUILT (D144) + DRIVEN (D146).** Every item
below is landed, unit-tested (515 tests) and has now run against a real clone of `idea testing` and the live
harness. The drive shipped **one high-severity fix** (a machine block could be terminated by its own payload —
`_render_fenced`), **retracted one residual that was never real** (the `claude -p` invisibility below), and left
**one finding open for a design call** (the declared-secret diff's undefined payload shape). Phase 7's exit test is
discharged.
- **`checks.sh --check` becomes a bindability probe** — a rebound project can be correctly bound and still unable
  to make a single commit, because the committed `checks.env` names a toolchain that is machine-local and
  gitignored. Run the gate *the way the pre-commit hook runs it* and report whether it exits clean — never a
  toolchain-detection heuristic, which would have to know which side of the WSL/Windows boundary each command
  belongs to. **[bind — BUILT (D144) in `rebind.py apply`, the maintainer's call on the open *where*. NOT `check` (its verified contract is "writes nothing"; `TEST` writes caches) and NOT a standing `SessionStart` probe (a full test suite before a session can begin inverts the master rule). Skipped on BIND/HEALTHY; `--no-probe` opts out. It reports the observable and does not diagnose; the output tail goes to stdout, never into the committed loss. The standing half is one routing clause in the pre-commit block message — visible to `claude -p`. **DRIVEN (D146)** on a real clone: `RE-CREATE` then `bindable: NO` with `tsc: not found`, the loss filed as a typed issue, the tail provably absent from the committed `backlog.md`, idempotence-on-title real, `check` reporting `NOT PROBED` and `--no-probe` skipping in 0.15s. The `HEALTHY` skip is genuinely silent — what covers it is the pre-commit block message, also driven: the commit is refused and the message names the did-not-travel toolchain and routes to `/rebind`, on git's own output stream, which is what actually makes it headless-visible]**
- **`bus.py park` becomes the writer** of `parked/<id>.json` **and** a fenced `<!-- parked:begin/end -->` block —
  parking has no code writer today, so the mirror cannot become a mechanism without one; it also retires
  `checkpoint/SKILL.md`'s "resolve the runtime root yourself". **[dur — BUILT (D144) + 28 tests. Three calls the code forced: the record arrives on STDIN (four flags cannot make a schema-valid record — no `token`, no `request`); **`unpark` had to be built too**, because prose was accidentally self-correcting and a persisted block only ever GROWS; and the deadline is stamped at microsecond precision, closing an accepted `alert_key` collision that a derived stamp made reachable at machine speed. **AMENDED (D145):** the block is written only at a mutation, so an install that parked *before* the writer had a live record and no block — and `/dispatch` had already stopped hand-writing the prose. Fixed with a `bus.py mirror` verb `/dispatch` runs before writing the anchor; caught by the blast-radius sweep, not by the tests. **DRIVEN (D146):** the skill's literal instructions do produce a record `park` accepts — a shell-hostile body arrived byte-exact through the quoted heredoc, the full park→daemon→verdict→drain→`unpark` cycle ran, the mirror carried no body/token/credential, all six refusal paths failed closed, and `mirror` backfilled from the real legacy record. The drive also found the slice's one high-severity bug: **a payload string could forge the block's own end marker**, corrupting the mirror and, in the drain block, taking `consumed_through` from a live watermark to `null` — fixed at `_render_fenced`, the one place both blocks serialize]**
- **`SessionStart` re-asserts `.git/hooks/pre-commit`, non-clobbering** — absent ⇒ install · identical ⇒ silent ·
  different ⇒ warn, never clobber. Proportionate: the git hook backstops *out-of-loop* commits only. **[dur — BUILT (D144); the matcher broadened to `startup`/`resume` (the rehydrate stays `clear`-only) because the motivating case is a CLONE, which runs neither `/start` nor `/rebind`. "Warn once" is keyed by the foreign hook's sha256 in `.git/hooks/`, so a different foreign hook warns again. `/rebind` calls the same code path via `--assert-hook`. **DRIVEN (D146):** both broadened matcher strings fire against harness 2.1.220 — proven by a `.git/hooks/pre-commit` that is sha256-identical to the source, not by a context window — and the foreign arm leaves the hook byte-for-byte untouched. **The stated residual was RETRACTED, not discharged: it was never real.** A headless `claude -p` session is handed the warning and quotes it back verbatim in its rendered form; three-state discrimination (warn / silent on the marker / re-warn on a different hook) rules out both the model reading the source and guessing]**
- **`config.json` `secrets_required[]`** — key names only, written by the `setup` checkpoint at elicitation; absence
  becomes provable; point-of-use fail-closed stays as the floor. `outbox/` loss is reported, not recovered. **[dur — BUILT (D144); "present" is derived by walking store payloads for key NAMES (entries are keyed by `message_id`, not by credential), deliberately generous because a missed match is noise and a false match is silence. Pure reads, so it runs in `check` too; an absent declaration is "we cannot tell", not "nothing is missing". **DRIVEN (D146) — and this is the one item the drive did NOT clear.** The itemized loss, the names-only entry and the never-printed value all held, but "present" is derived from dict KEYS, and `drain.py secret` stores `returns` verbatim from the console, whose natural shape (`[{id, sensitive, value}]`) carries the TASK id, never the credential name. Driven both ways: in the shape the code actually writes **nothing ever matches**, so every declared secret reports lost on every rebind of a machine that lost nothing. Nothing defines `returns`' shape, so this working is currently luck. Left open for a design call → `07`. **CLEARED (D147):** `returns` is now a declared **name-keyed map** the bus `400`s on violation, and the question sat downstream of a bigger one — nothing in the package could *produce* a `returns` at all, so the console gained the setup form D99 specified (increment 3b). The matcher flips with the declaration: "present" now reads `returns` nodes ONLY (collecting every key would let a project declaring a secret called `token` match falsely — a lost key reported present, i.e. silence), and a record that predates the shape is counted as **unreadable** and stated separately rather than folded into the loss]**

**The drive that gated all of this is DONE (D143):** force-reinstall the plugin at HEAD → **`/rebind`** on
`idea testing` (which did stamp the missing `bootstrap: complete` — that install predates D131) → **`/update`**, the
run owed since Phase 6. That project is now bound, updated, and pushed. 7b was then **built against that real
evidence rather than a hypothesis (D144)**, which was the whole point of splitting the phase — and it paid: three of
its calls could only be made with the code in front of it, the largest being that `park` needed an **`unpark`**
sibling nobody had asked for, because turning a self-correcting prose mirror into a persisted machine block turns a
missing remover from a non-issue into a block that reports answered checkpoints as open forever.
**The 7b DRIVE is DONE (D146), and Phase 7 is COMPLETE.** All four items ran, in the shape the exit test named:
a park→verdict→unpark cycle and a `/rebind` on a real clone whose toolchain did not travel. The mirror and the
probe did exactly what they were designed to do; the declared-secret diff did not, and its finding is open in `07`.
One high-severity bug came out of it (the forged end marker) and one stated residual was retracted as never real.

### Phase 8 — Release discipline, then the interaction-model rework **[opened D155; 8a re-designed D164 and BUILT 2026-08-03 (D165, `540d0e0`); 8b BUILT + browser-driven 2026-08-04 (D169, `ad9d910`). COMPLETE]**
Phases 1–7 are complete and the package has a **real installed consumer**. The successor is therefore not the
biggest remaining feature — it is the only open item that **harms a user today**, and it was measured, not feared.
- **8a — a stale install cannot learn it is stale (D151) — `[core]`. RE-DESIGNED 2026-08-03 (D164, owner);
  BUILT 2026-08-03 (D165, `540d0e0`) — DONE.** Two mechanisms changed under measurement and D165 owns both: the
  SessionStart hook gets **no `CLAUDE_PLUGIN_ROOT`** (it is wired from the *project's* settings, so hop B reads
  the resolved key from `installed_plugins.json`), and the warn-once state lives in **`.git/hooks/`**, not under
  `.workflow/` — machine-local facts, and untrackable by construction so it needs no `.gitignore` line the stale
  installs would not have. The delivery call is **proven end-to-end**: the install now keys on the commit SHA,
  hop A fired on a genuinely stale install and went silent by itself once reinstalled. The shape D164 described:** Installing **copies** `product/` into
  `~/.claude/plugins/cache/<plugin>/<version>/`; `claude plugin update` compares **versions**, and
  `plugin.json` has been pinned at `0.1.0` since the first install. The D151 drive measured the consequence: the
  install had silently drifted **12 commits and 17 shipped files behind** HEAD — including the `SessionStart(clear)`
  rehydrate, so a `/clear` there dropped into an empty session while the docs described resuming from `handoff.md`
  — while `claude plugin update` reported *"already at the latest version (0.1.0)"*. `11` already prescribed a
  manual force-reinstall; **the drive is the proof that the manual step did not hold.** A control nobody runs is
  not a control. **A second data point landed 2026-08-03:** the install sat six commits stale and was fixed only
  because the maintainer was told to reinstall — `dev-reinstall.sh` had shipped the day before and did not run.
  **What changed at re-design (D164):** the plugin `version` is **DELETED, not disciplined**. It is optional, and
  omitting it makes the platform key delivery on the **commit SHA** — so staleness becomes structurally impossible
  to forget instead of ritually prevented, and **the sixth meta-gate is deleted from the plan, not deferred**. The
  objection that this collides with D135 **does not survive reading the code**: `workflow_version` does an equality
  test, a display string and an absent-check — **no ordering anywhere** — because `/update`'s whole migration is
  content-hash driven through `install-set.json`. The four build calls:
  - **delete `version`** from `plugin.json` (and never add one to the marketplace entry — a version there re-pins);
    `plugin_version()` falls back to `basename(CLAUDE_PLUGIN_ROOT)`, which *is* the resolved cache key;
  - **`config.workflow_version` becomes that SHA** — the equality test gets strictly *more* correct under it;
  - **a two-hop DETECTOR** on the existing `SessionStart` hook (already wired at `startup`): **hop A** installed SHA
    vs the on-disk marketplace anchor → *reinstall*; **hop B** `config.workflow_version` vs the running package →
    *run `/update`*. Local-only, everywhere, **warn-once per distinct SHA**, always fails open. A *preventer* is not
    buildable — the automatic delivery path is CLI-side and broken (issue #17361, live on 2.1.220);
  - **a keep-2 cache prune in `scripts/dev-reinstall.sh`** (meta-only): SHA versioning abandons a ~2.4MB dir per
    update and nothing — not even `uninstall` — reclaims it.
  **Why the detector covers two hops:** `/update` is **bounded by the install** (it runs
  `${CLAUDE_PLUGIN_ROOT}/…/update_reconcile.py` and never reaches back to the source), so a stale install does not
  merely run old code — it **propagates** old code into every project it updates, reporting success. **D158's call
  stands** (the maintainer's fix must not depend on a version) but its *"two halves, different in kind"* is partly
  superseded: one detector, two anchors. That also sharpens why 8a leads: the user harmed by a stale install
  **today** is the maintainer, so this is first a correctness argument about the project's own evidence — a drive
  that silently runs commits-old code and reports it as HEAD — and only second a user-facing one.
- **8b — the interaction-model rework** (browser-primary conversation — `07`) — **`[core]`, sequenced second,
  deliberately. BUILT + browser-driven 2026-08-04 (D169, `ad9d910`) — DONE.** Its blocker had cleared (D132 parked
  it behind a proper re-drive; D138 ran one), so the sequencing was a scheduling call, not a dependency: shipping a
  large new surface onto a fleet that cannot learn it is stale multiplies the exact problem 8a exists to fix. **The
  three researched constraints held** and none was re-derived (`07` owns them). **The three open calls closed at
  design, before code** (D169): the thread is **RUNTIME**, the **human** splits question from request at the
  console, and chat is **loopback-only**. What shipped: a `question` inbox kind sorted last, the **`answer` skill**
  (the one net-new capability, a `loop.md` side-door), `.workflow/thread/` RUNTIME + pinned, the runner's trigger
  set extended with a **separate answer-only prompt**, and a Conversation panel. **The scope was smaller than
  "chat" and the reason is the finding that inverted the premise:** the *request* arm was already built end-to-end
  (intake → ticket → "my requests"), so the whole substance of 8b was the **question** arm, which had no
  capability at all. The browser drive caught two shell defects a green suite missed — see D169.
  **DRIVEN 2026-08-04 (D170): both residuals D169 logged are CLOSED.** Answer quality is **measured and good** on the
  shipped `claude -p` argv (both designed traps passed; it also flagged a fabrication it did not author), and the
  **200k rotation EXECUTED** — proven by shrinking the threshold and driving it, after the check that `07`'s proposed
  unit test had **no code seam to test**. The drive found three new defects, and **all three are FIXED 2026-08-04
  (D172)**: `answer`'s prescribed **step order could double-answer** (record now precedes rotate, so the anchor is
  never destroyed before the message is consumed); **rotation laundered a fabrication** into the durable handoff,
  answered **structurally** — the handoff keeps only what is not re-derivable and carries no project prose answer,
  under a general **distillation law** stated once in `memory-model.md`; and a **rotated thread rendered as a cold
  start**, now shown as a handoff. The last thing the drive left open — the away path burning an answer it cannot
  persist — is **CLOSED (D173)**: the runner now refuses to spawn into an untrusted workspace and alerts once with
  the fix, after measurement corrected the remedy twice over (the detectable signal is a trust-record read, and the
  predicate is *not `True`*, since the platform writes no record at all for a project never opened interactively).

*Everything else stayed `[stageable]`/`[later]` and was picked off the by-space list above, not this sequence — the
living code-map observed layer, the D84 reclassification (*since scheduled as `### Phase 11` — D178*), the proportional-rigor gate, build-once-per-wave,
model/effort routing, the project-map tab, and the project-state view (then still framed as the self-hosting
prerequisite it had been since 2026-06-30). **Superseded 2026-08-05 (D175):** self-hosting is dropped, so the
project-state view is re-argued on the product's own merits and scheduled as **Phase 10c**; the rest of that list
is now split by D175 into what Phase 10 sequences and what stays deferred, each with a stated reason.*

### Phase 9 — Three new capabilities: the chain-forecast, the context-budget law, org mode **[COMPLETE 2026-08-05 — D159–D163 designed; 9a BUILT + browser-driven 2026-08-03 (D163; D166 closed its render residual and fixed two shell defects); 9b BUILT 2026-08-03 (D167); 9c BUILT + DRIVEN 2026-08-05 (D174) behind its own exit gate — 27/27 against a real foreign repo. Built BY HAND — and **self-hosting is now DROPPED outright (D175)**, not the "separate later experiment on a clone" this header used to promise. The D164 sequence `8a → drive 9a → 9b` is COMPLETE. **Phase 9 was the last phase as PLANNED; D175 opened `### Phase 10` over the remainder** — the "no Phase 10" claim this header carried was a description of the plan then, superseded by decision, not corrected as an error]**
Born from a design conversation on four maintainer asks (the fourth — a console config tab — was **dropped**, D161;
its "change credentials over Cloudflare" arm violated D112). All three build **ON** existing machinery, not beside it —
that is the through-line and the reason none is large. Capture is design-only; the deep-doc edits ride each build.
- **9a — the chain-forecast (D159) `[core-ish]`.** A `/create-forecast` command (+ orchestrator self-invoke on the
  D69 triage) emits a **cheap, conditional forecast of the loop's own routing** for a requested change — ordered events
  each naming a real `loop.md` node, decision-meaningful branch points explicit, predicted setups elicited early
  (front-loading D97's elicitation, never its probe). Surfaced as a **new judgment checkpoint kind** (reuses the whole
  park/verdict/away stack — no new inbox kind); `approve` freezes it, reality renders as a **derived** column, a
  structural divergence re-forecasts. `create-demo` de-risks the *product* question; the forecast de-risks the
  *process* question. Loopback-only. Full call + rejected alternatives: **D159** (owner); the build + the seven calls
  it had to make: **D163**. **[core-ish — BUILT 2026-08-03]**
  - **BUILT by hand (D163, `5a77aba`), then BROWSER-DRIVEN (D166, `613d230`) — the never-rendered residual is
    CLOSED.** The drive found two shell defects, both fixed: every event was numbered **twice** (an `<ol>` marker
    never suppressed beside the record's own `n` — invisible to any `textContent` assertion), and the reality probe's
    `parked` arm was **not item-scoped**, so any open checkpoint project-wide marked a chain's `checkpoint:*` row
    `open` and raised a **false structural divergence** — which re-forecasts the tail, and with parallel items would
    have fired most of the time. Still true: **no real project has forecast a real change yet.** Shipped:
    `skills/create-forecast` (the skill-owned gate, placed BEFORE the sandbox gate at intake) · `scripts/forecast.py`
    (lifecycle owner: required horizon, linted names-only invariant, freeze + chain digest, reality, divergence) ·
    `check_contracts.py --forecast` (the graph half) · the committed `.workflow/forecasts/<id>.json` · the `forecast`
    checkpoint kind through schemas/bus/checkpoint/roster · the anchor table in `schemas.md` · a `#fc-list` console
    panel. **Seven calls D162 did not settle** were taken at build and are recorded in **D163** — five of them
    correcting a prior entry: the prune lives in `retention.py` (not `forecast.py`) and reads closure *positively* ·
    no command file (plugin skills already give the slash command) · the per-item artifact filenames are PINNED · a
    fourth reality state `unknown` · divergence exempts the item-complete tail · re-forecast is a SUPERSEDE, not an
    in-place edit · the loopback gate is keyed on KIND, not payload (a bare approve was riding the remote socket).
    **Two live shipped bugs fixed on the way:** `check_contracts.py` crashed in *every* product repo (align's whole
    mechanical layer was dead in situ) and `bus.py`'s `PARK_KINDS` was an unguarded second copy of the kind enum.
  - **The deferred mechanics were SETTLED before the build (D162).** The forecast is a **committed**
    `.workflow/forecasts/<id>.json` with the item-dir lifecycle (pruned at close, history in git) — it *cannot* live
    in the parked record, which `unpark` deletes at the instant of approval (D154's defect one layer up). The
    self-invoke rides a **skill-owned forecast gate** on D69's axes, not D69's triage (which does not ship, and fires
    after the forecast is useful). The pre-fill rides the forecast card with **blank = ask me at the gate**, making a
    judgment verdict able to carry an optional action payload (a `04` taxonomy *refinement*, not a break). Reality
    derives from a per-effect **anchor table**, never `state.json`. Lint splits by fact-domain: graph facts →
    `check_contracts.py --forecast`. *(D162 also assigned the forecast's whole lifecycle to `scripts/forecast.py`;
    the build split that — semantics there, **deletion in `retention.py`** with every other prune. D163, call 1.)*
    It built in the planned two increments — 9a-1 generate · lint · park · freeze · approve, then 9a-2 the derived
    reality column · divergence · re-forecast — and the `align` crash D162 folded in is **fixed** in the same commit.
- **9b — the context-budget law (D160 designed it; D167 BUILT it) `[core]`.** The enforcement
  `memory-model.md`'s "bounded by construction" claim never had: `check_doc_budget.py` token-counts every
  workflow-owned doc against a **role budget**, runs in `checks.sh` and as a **third decoupled maintenance item**
  `prioritize` injects (beside retention + `align`). Over-budget → a ticket (trim/split-and-pointer/distill), never
  auto-mangle; it does **not** re-check truth (`align` owns "wrong"). **Un-defers Sessions distillation** (D61).
  **What measurement changed at build (D167, owner):** the budget is **TWO-TIER per role** — hard fails `checks.sh`,
  advisory schedules a trim — because the package's *own* always-loaded templates measure ~3.3k/3.4k tokens, i.e.
  3.3–3.4× the sub-1k target D160 cited, so an aggressive-only budget would be **red on every clean install**, and a
  gate that fires on a fresh bootstrap is one a human learns to skip. And the estimator is **calibrated on this
  repo's own paging failure** (the roadmap: 85 083 chars at the 25k ceiling ⇒ ≤3.40 chars/token), which **kills
  `chars/4`** — it would have scored that exact file *under* a wall it could not fit. **[core — BUILT 2026-08-03]**
  - **BUILT — 741 tests + all meta-gates green.** Shipped: `scripts/check_doc_budget.py` (+ a `checks.sh` hard-tier
    call on every commit — cheap, decidable, always-whole, since it reads sizes not content) · `config.doc_budget`
    (`shared/schemas.md` owner) · the `doc-budget` maintenance item in `prioritize` + `loop.md` · the context-budget
    law and the **split-and-pointer** convention in `memory-model.md` · distil-before-cap in `document`'s audit mode,
    with `# Lessons` **top-level and before `# Sessions`** (nested under it, the cap would eat it — proven both ways).
    **First real customer, and it is ours:** `product/shared/schemas.md` measured **28 520 tokens**, already past the
    hard wall in a shipped file the package names as its schema owner.
  - **The first customer is now SPLIT — D168, 2026-08-04 (`b4e2c25`).** `schemas.md` 28 520 → **18 670 tok**, with
    the runtime substrate in a live sibling `shared/schemas-runtime.md` (**10 832 tok**); all 33 sections preserved,
    diffed section-by-section. Executing the convention found two things reasoning had not: it needed a **second
    marker form** (D167's `@ <sha>` assumes the detail is *frozen in git*; this detail is a **live sibling** still
    being edited), and the pointer had to become **machine-followable** — two shipped consumers parse `schemas.md`
    whole, and the split line could not dodge them because the native-FS headers *are* the moved half. Measured both
    ways: the meta-gate hard-fails with 5 false errors, the contract linter loses `generic`/`slack` from its
    kind-union — **both loud, in opposite directions, so not the silent-defeat class** (a first draft claimed it was;
    the measurement refuted it). Also closed a gap in 9b's own gate: the sizer prescribed a remedy whose output fell
    outside its glob, so a **detail file is now budgeted as its own row**, always on-demand. **[BUILT 2026-08-04]**
- **9c — org mode (D161, corrected + built by D174).** A **third `/start` mode** (`config.org`; absent ⇒ inert,
  and there is deliberately **no toggle** — a live topology switch is a migration, not a setting) for a company
  product the maintainer does not own. **The topology D161 recorded was incoherent and D174 corrected it: the brain
  IS the private clone, `project_root: "."`** — org mode is brownfield *cloned* rather than in-place, so every
  single-repo guarantee (`verify_check.py`'s staged-diff binding, `checks.sh`'s backstop, `align`'s single anchor)
  holds unchanged. There is **no third `project_root` value**. The operator's own checkout is a separate directory
  the workflow never reads or writes; the clone's push path is removed with git's own `no_push` idiom while `fetch`
  keeps working. Derived artifacts are namespaced under **`docs_root: .workflow`** (a key D174 **adopted with its own
  owner**, absent ⇒ `project_root`) and the brief goes to **`.claude/CLAUDE.md`**, so the brain owns exactly
  **`.workflow/` + `.claude/`** — which is what keeps the review bundle's exclusion list two entries long instead of
  a per-file list that must stay correct forever. `checks.env` declares **`STACK_GATE_NONE`** (the third stack-gate
  state: off *by declaration*, refusing rather than obeying any command set alongside it), because nothing out of
  that tree may ever execute here. The net-new **review-bundle producer** is a per-item **squashed diff** + a sidecar
  outside it (D171), and it **verifies its own output** — parsing paths back out of the bytes it produced and
  refusing a bundle that still names a brain path. **org-align is `align` with a second anchor** (`describes_sha`),
  not new machinery. The governance caveat is now a **rendered fact**: `guard.sh` gates the act of adding a push
  path on `org.archive_remote_ack`, and the console badges the state for as long as one exists.
  **DRIVEN 27/27** against pallets/click at a pinned SHA with 42 of its own later commits replayed as coworker drift
  → pristine / no-push / drift-detected / no-leak. Full call: **D174** (owner; corrects D161 and re-grounds D171).
  **[done — BUILT + DRIVEN 2026-08-05]**

*Sequencing note:* 9a → 9b → 9c was fixed (9b makes everything cheaper; 9c is riskiest and evidence-blind). **All
three are done** — 9a (D163 + D166), 9b (D167), 9c (D174) — so the D164 sequence `8a → drive 9a → 9b` is COMPLETE
and **Phase 9 carries nothing further**. Ordering 9c last was vindicated rather than merely tidy: building it
required *correcting its own recorded design* before any code (D174), and the correction was only visible because
the machinery it had to fit already existed and could be read. The reasoning it was ordered that way, kept because
it is the argument: not on
8a's user-facing payoff, but because **a stale install corrupts the evidence of every drive that follows it** — do 8a
first and every later drive is trustworthy by construction, and **the 9a browser drive then doubles as 8a's exit
test**, closing 9a's never-rendered `#fc-list` residual in the same pass. **The dogfooding half of that call was MADE for
9a: it was built BY HAND** (2026-08-03), and self-hosting the workflow on itself is a **separate later experiment on
a clone**, deliberately not entangled with shipping the feature. That kept 9a off the `[stageable]` project-state
view it would otherwise have waited on. *(**The clone experiment never happened and is now cancelled — D175 drops
self-hosting outright.** The half of this call that was about not entangling a first run with a new capability was
right and is kept; the half that deferred a run is moot, because there is no run.)*

### Phase 10 — Truth-in-shipping: close the gap between what the tree CLAIMS and what it DOES **[COMPLETE 2026-08-05 — opened D175, BUILT D176 (`1d52783`→`5b0d09b`+). All three increments shipped: 10a (three over-claims), 10b (the portability claim measured, one defect fixed), 10c (the project-state view — a `status` skill over `project_state.py`). 853 tests (835→853), 5 meta-gates green, release boundary clean. **One residual, stated not hidden: 10b could not be closed on native Windows** — Git for Windows is not installed on this machine, so execution under its bash is unverified]**
Phase 9 was the last phase *as planned*, and the remainder was described as "a menu, not a sequence". D175 reverses
that **by decision, not by finding an error** — and the reversal was forced by the other one: **self-hosting is
dropped**, which was the only spine the menu had. So the spine had to be found rather than assumed, and the
premise-check found it: **six of ten candidates were stale in the same direction — the tree asserts things nothing
produces or checks.** That is the theme, and it is honest rather than imposed. It also explains the unusual shape of
this phase: **more of it is correction than construction**, and the corrections are already applied above.

*Scoping rule this phase is held to: `[later]` means deliberately deferred, and a phase that swallows the whole
backlog is a backlog with a new name. Four candidates are deferred with stated reasons, and each carries what would
promote it.*

- **10a — the over-claims.** Three shipped assertions with nothing behind them. **[core]**
  - **The observed layer.** `scripts/codemap/codemap.py` rests its standing *precision-over-recall* rule on the
    layer ("a missed edge self-heals: the durable observed layer accretes the recall the arms leave on the table"),
    and `skills/verify/SKILL.md` licenses `verify` to drive flows as a pure observer *for* it. `graph.observed.json`
    exists in **no product code**. **Retract both claims** — the precision bias is right on its own terms (a
    fabricated edge is sticky and unretractable) and does not need a layer that does not exist to justify it.
    Do **not** build the layer; its tier is settled `[stageable]` above. **[DONE — D176]**
  - **`verify` #8.** The skill claims artifact conformance while reading only plan↔changelog. Wire the verdict to
    sample the real staged diff. **[DONE — D176]** It needed TWO git reads, both verified by measurement: `git diff HEAD` is blind to a newly created file (untracked until staged), and is fatal on a repo with no commits.
  - **Commitment dual-carriage.** `shared/schemas.md` carries `commitment` in the spec *and* in node frontmatter.
    Settle it under D80: one declared owner with the second copy **derived**, or an explicit statement that
    dual-carriage is deliberate and why. **[DONE — D176, and it was neither: the node field had no producer and no consumer, so it is DELETED and the spec element is the sole owner.]**
- **10b — the portability claim.** Shipped bash glue claims a target-OS interpreter it has never been tested against
  (**D89**): `pre-commit.sh`, `guard.sh`, `checks.sh`, `codemap.sh`, `loop.sh`. **Verify on native Windows** — not
  WSL, which is the environment every prior drive used and the one that hides this. Carries the **D58 first-launch
  trust-UX doc** with it (the weakest fit to the spine — a missing doc, not a false claim — taken in as cheap and
  adjacent, not because it belongs). **[DONE — D176, with a stated residual: the stock-Windows `python3` stub and `bash` stub were measured and the fail-closed gates HOLD; `loop.sh`'s missing-`flock` misdiagnosis was found and fixed; execution under Git for Windows' bash remains UNVERIFIED — it is not installed here.]**
- **10c — the project-state view.** The synthesized "where is this project" surface (done · how it connects ·
  what's left), **generated**, not hand-maintained (D38). Re-argued after losing its self-hosting premise: `07`'s
  original 2026-06-30 entry carries an independent justification that survives. **Built for a TARGET project** —
  it may not be built to read this repo's own `docs/design/`, which is both the D125 boundary and the only form
  dogfooding can validate. **A surface: it gets a render before it is called done.** **[DONE — D176: the `status` skill (side door, advances no node) over `scripts/project_state.py`, which is GENERATED and writes nothing. Rendered against a fixture and against its own degraded paths before being called done.]**

**Deferred, each with its trigger:** the **proportional-rigor triage** (promote on a *second* narrow gate wanting it
— D162's forecast gate covers today's case) · the **project-map tab** (the console has no tab machinery; inventing
navigation is the real first cost) · **model + effort routing** (a cost optimization with no correctness claim) ·
**symbol-level knowledge paths** (an engine-level change to the arm contract — out on scope, not on doubt) ·
**automated testing / device-QA platform** (unchanged `[later]`).
**Retired outright:** the *engineering-feasibility pass* (a duplicate of the D69 triage, by this doc's own wording) ·
the *arbiter input contract* (the component exists nowhere; its substance is `prioritize`'s) · *`@import`-survives-
`/compact`* (the package uses no imports).

### Phase 11 — Dispatch fidelity: make the shipped roles actually reach the workers **[11a–11e BUILT + DRIVEN 2026-08-07 (designed D178, built D179); 11f OPEN. Opened by measurement of a real drive, not by a premise re-check — and closed the same way: the exit test is a real-model drive, not an argument]**
Phase 10 closed with **no successor declared**. This is it, and it was not chosen from the deferred menu — it was
**found**. A design question about whether one-execute-agent-and-wait is right *practice* (it is — D178) required
measuring a real drive to size the writer, and the measurement found that **the package's capability layer is not
reaching the workers at all**: 51 subagent transcripts, **0** `Skill` invocations, 33 of 50 dispatches to
`general-purpose` carrying a paraphrase the orchestrator typed itself. `research` works because it is the only one
of those nodes that is a declared agent. Full finding, cause and rejected alternatives: **D178**.

*This phase supersedes the `[stageable]`/`[later]` framing of the **D84 reclassification** wherever this doc still
carries it. D84's deferral rested on "the context saving can't be measured until the loop runs"; it ran, and the
number is 191.3k tokens per `execute` dispatch. It is no longer a file move — it is a dispatch-mechanism fix.*

- **11a — declare the leaf agents.** **DONE (D179)** — the three are `agents/` files, `Route` stripped, with
  `tools:` carrying both invariants (no `Task`/`Agent`, no web). Two things the move forced: the contract linter
  now scans `agents/` too (moving `document` out had silently taken `document:audit` out of its check), and the
  sandbox gate left `create-demo` — a dispatched agent's file is the *worker's* context, so a gate living there
  could never be evaluated by the router. **[core]**
- **11b — the dispatch rule in the brief.** **DONE (D179)** — `:17` is gone; the two axes are stated as a
  mechanism rule (dispatch by name / run inline by name / never `general-purpose`), plus **pass inputs, not
  instructions**, which is the half that actually killed the paraphrase. **[core]**
- **11c — the mechanical gate.** **DONE (D179)** — `hooks/dispatch_guard.py`, blocking, reading the node names
  from the project's own `loop.md` rather than carrying a list. Verified firing in a live session, and replayed
  against the original drive: **34/34 non-namespaced dispatches blocked, 17/17 namespaced allowed**. **[core]**
- **11d — make the measurement repeatable.** **DONE (D179)** — `scripts/measure-dispatch.py`. It reports token
  *components* rather than one figure (the CLI's per-dispatch number is not in the transcript), and an empty scan
  says "nothing measured" instead of reporting a clean bill. **[core]**
- **11e — drive it.** **DONE (D179) — the exit test is GREEN.** A real project migrated onto the package through
  `/update`'s own runner, one full item driven to commit: **4/4 dispatches namespaced, 0 loop nodes on a general
  worker, 0 nested spawns**, and dispatch prompts down from **2794–9663 chars to 289–1188**. The drive also found
  two defects in this slice's own work — the fix had blown the always-loaded doc budget, and `dev-reinstall.sh`
  was silently shipping stale bytes into every drive. Both fixed. **[core]**
- **11f — THEN re-measure the writer's scope. THE ONLY PART STILL OPEN.** `planner` has **no sizing rule** — but
  a scoped `execute` with no web tools may burn materially less, and the attribution
  (discovery-read cost vs production-write cost, re-read ratio, off-`files_touched` reads) must be taken against
  the fixed system. Two diagnoses, opposite fixes: read-dominated → `planner` under-supplies context (D134's
  resolution); write-dominated → a plan-size budget splitting on the D91 predicate, **serially**. **The fixed
  system's first numbers are in (D179) and they say READ-dominated** — `execute` 335.6k fed in against 24.1k
  written, `document` 175.0k vs 15.7k — which points at the first diagnosis. One item is not a sample; this
  increment takes it properly, and it is deliberately not acted on until then. **[core]**

**Not in scope, deliberately:** the **cold-context reviewer** (Cognition's Code-Review-Loop — the loop has no
per-item correctness review: `verify` is conformance-only by design and `debug` is on-fail only). It is a real gap
and a *read-only* addition that does not touch single-writer, but it was worth nothing while the workers weren't
running their own instructions — **that condition is now met (11e is green), so it is promotable**: it is the
first candidate for whatever follows this phase, alongside 11f. Still out: **within-item parallel writers**,
rejected in D178 with a stated re-open trigger.

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
phase: ~~the D136 governor's `/dispatch → /clear → rehydrate` **cycle is still unexercised**~~ (the banner never
fired — the context law kept the window too lean to trip it) — **DISCHARGED by D151**, which forced it and drove the
whole cycle, ending with a cleared session resuming from the anchor alone; and ~~`/update` has never run against a real install~~ —
**that second one is DISCHARGED by D143**, which ran it on `idea testing`, the real machine-move casualty, and shipped
three package fixes out of it (`idea testing@8e03d1e`). *It sat here stale for six decisions: the residual was written
into the OWNER of what's-left, discharged elsewhere, and never repointed — the exact drift D80 exists to stop. The
coherence gate does not catch it, because it checks roster counts, `D1–DN` ranges and `**[…]**` tags, not prose
residuals. **A discharged residual is a status fact and needs the same blast-radius sweep as any other.***
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
provable. **7b is now DRIVEN (D146) and Phase 7 is COMPLETE** — the drive proved the broadened `SessionStart`
matcher fires (by file identity, not by a context window) and the bindability probe reports the exact D143 symptom,
found and fixed the slice's one high-severity bug (**a machine block could be terminated by its own payload**,
taking the drain's watermark to `null` from a console-reachable field), retracted a D144 residual that was never
real, and left one open finding — the declared-secret diff depends on an undefined `returns` shape and is inert in
the shape the code actually produces. **That finding is CLOSED by D147**, which found it sat downstream of a bigger
one: `returns` had **no producer** — the console's verdict form posted `{outcome, notes}` only, against a D99 spec
that named `returns`/`tasks[]`/steps/deep-links, so D122's Tailscale credential arm had been guarding a payload
nothing could emit. `returns` is now a declared name-keyed map, the console gained the setup form (increment 3b),
and the matcher went exact. **`### Phase 8` (D155) is COMPLETE** — release discipline (D165) ahead of the
interaction-model rework (D169), because shipping a new surface onto a fleet that cannot receive fixes multiplies
the problem. **`### Phase 9` (D159–D163)** adds three new capabilities — the chain-forecast, the context-budget
law, and org mode — all **designed 2026-08-03**, each built ON existing machinery. **9a is BUILT** (D163, by hand,
same day; self-hosting was split off as a later experiment on a clone — and is now **DROPPED**, D175), **9b is BUILT**
(D167), and **`9c` (org mode) is BUILT + DRIVEN** (D174, 2026-08-05) — so **Phase 9 is COMPLETE**. It was the last
phase *as planned*; **`### Phase 10` (D175, 2026-08-05) then sequenced** the part of the by-space
`[stageable]`/`[later]` menu that survived a premise re-check, and **is itself COMPLETE (D176)**. **`### Phase 11`
(D178, 2026-08-07) is the live pointer — dispatch fidelity.** It was not picked from the deferred
menu: measuring a real drive to size the execution agent found that the shipped skills never reach the workers
(51 subagent transcripts, **0** `Skill` invocations), which makes every judgment-layer contract in the package
advisory in practice. It supersedes the `[stageable]`/`[later]` framing of the **D84 reclassification** wherever
this doc still carries it. **`11a`–`11e` are BUILT + DRIVEN (D179, same day) and the exit test is green** — the
three heavy leaves are declared agents, the brief carries the mechanism rule, a blocking gate enforces it, the
measurement is repeatable, and a real-model drive of a full item produced **4/4 namespaced dispatches, zero on a
general worker**, with dispatch prompts collapsing from thousands of characters to hundreds. **`11f` — the
writer's scope — is the one part still open**, and it now has its first honest numbers to work from.
