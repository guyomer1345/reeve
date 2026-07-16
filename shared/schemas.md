# Shared Artifact Schemas

The data formats that flow between capabilities. One source of truth — skills/agents reference these by
name. On-disk paths are fixed; each schema notes its **write-mode** (rewrite-in-place · append ·
new-record-supersede · create-per-item) and **tier** (see `shared/memory-model.md`). *Retention bounds (the
read law) live in `shared/memory-model.md`.*

## spec  · *rewrite-in-place · STABLE (changes only with the code it specifies) · on disk at `<project_root>/docs/spec.md`*
The product definition `discuss` produces and the whole build runs against.
- `audience` — who it's for
- `runtime` — where it runs
- `purpose`
- `screens[]` — `{ name, role, commitment }`
- `features[]` — `{ name, purpose, acceptance_criteria, commitment }`
- `data_model`
- `integrations[]` — `{ name, kind: auth|payments|…, → triggers a setup checkpoint }`
- `tech_stack` — value | `"TBD → decision-engineer"`
- `commitment` ∈ `{ locked, provisional, unspecified }` — tagged per element

## roadmap  · produced by `planner` (decompose mode) · *emitted as items into the live `backlog.md` queue*
- `phases[]` — `{ name, goal, depends_on[], acceptance, commitment }`

## plan  · produced by `planner` (plan-one mode) · *created per item under `.workflow/items/<id>/` (planner `mkdir`s it on demand); the item **dir** is committed while the item is open (crash-survival), pruned once closed by the audit pass*
> **`committed while open` ≠ a second code commit.** What rides these interim commits is the item's `.workflow/`
> *artifacts* (plan / changelog / verdict) — not the product code. The product code is still **one commit at
> item close** (the one-commit-per-item rule); a mid-item reset re-runs only the uncommitted *code* work, while
> the artifacts survive to rebuild position. Two different objects, no contradiction.
- `goal`
- `source_spec_ref`
- `decisions[]` — refs (by `id`) to the `decision-record`s this plan implements; every one must map to ≥1
  step or `planner` blocks the plan (coverage gate). `planner` writes the `{ id, steps }` mapping into
  `promises.json` (`decisions[]`); `check_decision_coverage.py` blocks an unmapped one mechanically.
- `risk_class` ∈ `{ code-only, data-additive, data-destructive, prod-touching }`.
- `backup` — required when `risk_class` is destructive: `{ what, mechanism, verification, restore }`.
  `execute` refuses a destructive plan without it and runs+verifies it before the destructive step.
- `files_touched[]`
- `steps[]` — ordered, each independently verifiable
- `acceptance_criteria[]` — the definition-of-done; each `{ id, criterion, gate: artifact | human-qa,
  boundary?: bool, discharge? }`. `artifact` → checked by `verify`; `human-qa` → confirmed by a `checkpoint`
  (kind=qa). **`discharge` is required on every `artifact` criterion** — it names the concrete mechanical check
  that settles it: a test ref, or a token `type` / `lint` / `structural` (a structural predicate the model can
  point at). A criterion with **no nameable discharge is not artifact-checkable → it is `human-qa`** — the
  classification is mechanical (*can you name a check?*), not a judgment call. This makes "**every criterion is
  one or the other, `planner` emits no un-checkable criterion**" *enforceable* rather than aspirational: `verify`
  **never passes an `artifact` criterion whose discharge produced no signal**, and
  `check_criterion_discharge.py` blocks a plan whose `artifact` criterion lacks a discharge. A plan with zero
  `human-qa` criteria never triggers a QA checkpoint. `boundary: true` marks a criterion whose case is drawn
  from **outside the implementation's own enumerated set** (the discharge a universal promise requires).
- `promises[]` — mirrors the impact-flagged `decision-record.promises[]` this plan implements; each promise's
  `test_ref` resolves to an `acceptance_criteria.id` here, and a `universal` promise's linked criterion must be
  **`boundary`-tagged** (one in-scope example can't discharge a "for-any" claim). `planner` writes these + the
  resolvable ids to `.workflow/items/<id>/promises.json`; the **promise-coverage gate**
  (`check_promise_coverage.py`, run by `checks.sh --check`) **blocks** an unlinked or non-boundary promise — the
  mechanical sibling of the decision-coverage gate. It proves *linkage*, not adequacy: a universal's adequacy
  rests on a property/structural test drawn from outside the enumeration (e.g. the code-map floor invariant).
  The same `promises.json` also carries the plan's `criteria[]` (`{ id, gate, discharge, boundary }`) — so
  `check_promise_coverage.py` resolves a universal's `boundary` off its **linked criterion** (where the tag
  lives), not off the promise; its sibling gate
  `check_criterion_discharge.py` (also in `checks.sh --check`) **blocks** an `artifact` criterion with an empty
  or missing `discharge` — the presence check behind the "no vacuous artifact-pass" rule (adequacy of a named
  discharge stays `verify`'s read + a deferred hardening, not this gate's).

## plan-delta  · produced by `refine` · *item-scoped ephemeral in `.workflow/items/<id>/`*
The correction `refine` hands to `planner` (plan-one) so a re-plan *amends* the existing `plan` instead of
rebuilding it from scratch. `{ target_plan_ref, change — what to add/alter/drop, why — the failure/finding it
answers, source ∈ { debug-report, checkpoint-fail, new-need } }`. `planner` (plan-one) takes it as an optional
input and edits `plan.md` in place; a delta with no `target_plan_ref` is a fresh plan-one.

## changelog  · produced by `execute` · *append within the item's lifetime; `.workflow/items/<id>/`; item-scoped ephemeral*
- `plan_ref`
- `actions[]` — `{ step, files, result }`
- `divergences[]` — `{ step, tier: cosmetic|prerequisite-repair|structural, expected, actual, why }`. A
  `prerequisite-repair` is committed separately from the item's planned change; a `structural` divergence
  stops execution and escalates.

## verify-verdict  · produced by `verify` · *created per item in `.workflow/items/<id>/`; item-scoped ephemeral*
- `pass`
- `mismatches[]` — `{ expected, actual }`
- `confidence`

## decision-record  · produced by `decision-engineer` · *append-only — one record per decision; a reversal is a NEW record that supersedes (status flip), never an edit; global under `<project_root>/docs/decisions/`*
- `id` — stable id (e.g. `D-001`); `plan.decisions[]` reference these, and coverage is checked id → step
- `status` ∈ `{ active, superseded }` · `supersedes` / `superseded_by` — the reversal chain; a flip writes a
  NEW record and sets these. Retention GCs superseded bodies to git, keeping a tombstone in
  `decisions/index.md`
- `index.md` — VOLATILE table `| id | title | status | ref |`. `decision-engineer` writes the active row
  (`| <id> | <title> | active | - |`); retention flips it to a tombstone (`| <id> | <title> | superseded->X |
  git <sha> |`) when it GCs the body — one row per id, keyed by the first column.
- `question`
- `options[]`
- `chosen`, `why`
- `confidence`
- `sources[]` — the durable distillate of any `research` dispatched for this decision (the heavy research
  notes are ephemeral scratch, discarded)
- `promises[]` — the load-bearing claims the design must hold; **only for impact-flagged decisions** (the
  code-map impact lens marks a high-blast-radius touch, or the decision is a design's raison d'être) — a
  reversible tier-0 call carries none, so this stays empty on most records. Each `{ text, kind ∈ { universality,
  idempotence, preservation, monotonicity, graceful-degradation, isolation, backward-compat }, universal: bool,
  falsifier` (the input that would break it — a promise with no interesting falsifier is a knob-restatement,
  dropped)`, test_ref` (the acceptance-criterion that discharges it — **unbound (`null`) at decision time;
  `planner` binds it when it writes that criterion**, since the criterion doesn't exist while `decision-engineer`
  runs pre-`planner`) `}`. **Elicited adversarially by a pass
  distinct from the decision's author** (see `decision-engineer`), never self-listed — the author shares the
  blind spot that hid the promise, and a promise nobody writes is the one that ships untested.

## debug-report  · produced by `debug` · *item-scoped ephemeral in `.workflow/items/<id>/`; its **durable form** is the per-file `# Sessions` entry `document` promotes — a report not promoted leaves no durable trace*
- `symptom`, `cause`, `fix`, `avoid`
- `confidence`

## checkpoint  · the `checkpoint` gate · *a **durable park boundary**: the orchestrator writes handoff + the request, yields, and resumes via `claude --resume` with the verdict as an authoritative prompt*
A checkpoint sits at **a boundary only a human can cross** — either a **judgment** boundary (does this match intent:
`demo`, `qa`, `reconcile` — the verdict is an opinion) or an **action** boundary (do something in the world the loop
can't reach: `setup` — the verdict is "I did it" + a returned artifact, then machine-verified).
- `request` — `{ kind: demo|qa|setup|reconcile, what, expected, how?(←setup-guide), tasks?[], blocking: true, token }`.
  **`token`** (`{ticket}:{step}:{uuid}`) correlates the async verdict back to this parked ticket. **`tasks[]`** is the
  *set* of setup items a `kind=setup` checkpoint carries (a lone setup is a one-element set); the orchestrator
  coalesces a plan's foreseeable setups (spec `integrations[]`) into one checkpoint **at first-setup-contact** (not
  front-loaded at intake) — an unforeseen setup is raised by `execute` on hitting the wall.
- `verdict` — `{ outcome: approve|changes|reject, notes, returns? }` (`pass` ≡ `outcome=approve`); a `kind=setup`
  verdict carries a **per-task** outcome, so a mixed reply routes each item on its own. **Routing keys off `outcome`,
  per kind:**
  - **demo** — approve → lock the spec state · changes → `create-demo` (refine) · reject → `discuss`.
  - **qa** — approve → `document`/`commit` · reject → `debug` (`changes` ≡ reject here).
  - **setup** — approve|changes → the orchestrator **verifies the external precondition actually works** (probe the
    key/webhook) *before* proceeding; reject → replan or hard-stop. A `returns` value marked `sensitive` is written to
    the gitignored **secret store** (`.workflow/secrets/`, below), **never logged**, and its inbox record **unlinked
    immediately after that write**.
  - **reconcile** — approve → `prioritize` · else → `ingest`/`discuss`.
  A **timeout never auto-proceeds** — it re-surfaces + reminds (a missing credential can't be skipped). A rejection is
  not always a defect — hence routing by kind, not a universal `debug` sink.

## parked-ticket  · written by the orchestrator when a ticket parks on a checkpoint · *`.workflow/parked/<id>.json`; RUNTIME, gitignored; every entry mirrored in `handoff.parked[]` for cold-start rebuild*
- `{ ticket_id, token, worktree?, branch?, loop_position, checkpoint: {kind, request}, predicted_outcome, deadline, parked_seq }` — `worktree`/`branch` are **absent for a pre-build (intake-stage) park** (a `demo`/`reconcile` checkpoint parks before any build worktree exists); a build-stage park always carries them.
- `deadline` — an **absolute** timestamp stamped at park time as *now + `config.checkpoint.deadline_hours`*
  (default 24h). Absolute, not a duration, because the process that *acts* on it is the console daemon, which
  compares against wall-clock and was not present when the ticket parked. Past it → the daemon **escalates**
  (never auto-proceeds).
- **This record is the alert trigger.** Writing it *is* the signal: the daemon watches `parked/`, raises the alert
  on a new open checkpoint, re-alerts every `config.checkpoint.reminder_hours`, and escalates once overdue. The
  parking skill sends nothing itself.

## inbox-message  · appended to the inbox by the bus when the console POSTs · *`.workflow/inbox/<ts>-<uuid>-<pid>.json`; append-only, durable (atomic write+rename), at-least-once; RUNTIME, kept on a native filesystem*
Every console→orchestrator message is **typed** — `kind: verdict|intake|control|release` — one uniform durable
transport, dispatched at a scheduler boundary **by kind**. **Single consumer** (the one orchestrator) → no `processing/`
claim-by-rename needed; matched **idempotently, single-shot** (duplicate → no-op). The bus returns `202 Accepted` +
a `Location` ticket at POST time; any result surfaces via orchestrator-written state the console re-reads by ticket —
the orchestrator **never responds synchronously** (it is a boundary batch-consumer, not an HTTP responder).

**`message_id`** — the filename stem (`<ts>-<uuid>-<pid>`) **is** the message's canonical, bus-assigned id.

**Consume = record, never delete.** The bus is the sole writer of `inbox/`, so the consumer **never removes a
message** (delete-on-consume would make the inbox two-writer). Instead the orchestrator keeps a durable
**consumed-set** of `message_id`s in its own partition (`handoff.md`): at each boundary it lists `inbox/`, **skips
ids already in the set**, applies the rest, adds their ids, and atomically republishes. A cold start re-lists
`inbox/` and the set makes the re-read a no-op — this is what stops a restart from re-promoting an
already-consumed intake or re-firing a control op.

**Two idempotency layers.** The consumed-set covers the normal path. Because apply-then-record has a crash window
(crash in between → re-apply on restart), **each kind's *effect* must also be idempotent** — its anchor is named
per kind below. Layer 1 = the consumed-set (single-shot); Layer 2 = the per-kind effect anchor (crash-window
safety). Neither alone is sufficient.

**Bounded.** The orchestrator publishes a low-watermark (`consumed_through`) once every message at-or-below it is
consumed; the **bus** GCs inbox files ≤ that watermark (staying the sole writer of its own partition), and the
consumed-set is pruned to ids above it — bounding both the inbox and the set. Volume is human-interaction-paced
(the autonomous loop never writes the inbox), so this is hygiene, not a hot path.
- **`kind: verdict`** — `{ token, verdict: {outcome, notes, returns?} }` — resumes a parked ticket; `token` matches a
  `parked-ticket`; unknown/closed token → **dead-letter + surface** (never a silent resume). **Anchor:** the parked
  `token` — a re-applied verdict finds the ticket already resumed (token closed) → dead-letter/no-op. A `returns`
  value marked `sensitive` (a setup credential) is written to the gitignored secret store and this inbox record is
  **shredded immediately after consume** — a secret is never retained on the durable inbox or echoed to
  `state.json`/logs. This shred is the **one exception** to *consume = record, never delete*: the orchestrator may
  `unlink` a single consumed record **that carried a sensitive payload**, right after extracting it to the store, so
  a secret's latency-to-zero never waits on the bus's GC pass. Nothing else in `inbox/` is ever consumer-deleted.
- **`kind: intake`** — `{ ticket, ask, node_ids? }` — a new-work request; the orchestrator **promotes** it into
  `backlog.md` through triage — **never a direct backlog write** (that would make the backlog two-writer).
  `node_ids` present when the project-map screen emitted it. **Anchor:** promotion **stamps the source `message_id`
  into the new item's `source`**, and re-promotion is skipped when an item already carries it — the same stamp that
  lets the console's "my requests" surface correlate an intake to the item it became.
- **`kind: control`** — `{ ticket, op }` (e.g. `reprioritize`, `pause`) — a loop-control command honored at the next
  boundary (non-preemptive). **Anchor:** none is possible (a control op leaves no durable artifact to check), so
  **control ops MUST be idempotent** — re-applying one is a no-op by construction (`reprioritize` re-orders the same
  backlog to the same order; `pause` re-sets a flag). A non-idempotent control op may not be added without bringing
  its own anchor.
- **`kind: release`** — `{ action_ids[] }` — a human **batch-approval** of pending outward actions; the
  orchestrator executes each named `outbox` entry (re-run through `guard.sh`) at the next boundary and marks it
  `executed`. **Always by explicit `action_ids`** (a snapshot of what the human saw — items enqueued after the glance
  are simply not in the set); never an "approve-all-pending" wildcard. Distinct from `verdict`: it resumes **no**
  parked ticket (an outward action never parked the loop), it just fires a deferred side-effect. **Anchor:** the
  outbox entry's `status` — an entry already `executed` is skipped, so a re-applied release is a no-op. (The
  *message* dedups here; an external side-effect with no natural idempotency — `issue-create` — carries its own
  key on the outbox entry.)

## outbox / pending-outward-action  · written by the orchestrator when a skill defers an outward action, cleared by the `release` consumer · *`.workflow/outbox/<id>.json`; RUNTIME, gitignored, single-writer (orchestrator); the mirror of the bus-owned `inbox/`*
The **transactional-outbox** queue behind the "never stalls — queue the outward action, one approval releases a
batch" rule. An outward action (`push`, `issue-create`, `issue-close`, later `deploy` / `send`) is **not** a
checkpoint — it doesn't park the ticket (the commit is local, the ticket completes, the loop advances). When the
skill's `config.outward` check (below) yields `ask`, it appends a record here and continues; a console `release`
fires it.
- `{ id, action ∈ { push, issue-create, issue-close, deploy, send }, args, item_ref, created_at, ttl, state_binding, status ∈ { pending, executed, rejected, dropped } }`.
- **`state_binding`** — what the action was queued against, re-validated at release (TOCTOU defense): `push` binds
  `{ branch, floor_sha }` (release re-scans the outgoing range through `guard.sh`; a rebased-away floor →
  invalidate + re-surface); `issue-create` binds the local backlog item (closed meanwhile → **drop**); `issue-close`
  is idempotent. **Divergent state invalidates + re-surfaces, never silently fires.**
- **`ttl`** — a queued action **drops on expiry** (never silently fires stale); drop ≠ escalate (an outward action
  isn't blocking). Config-overridable.
- **Two-layer gate:** **Layer 1** = `guard.sh`, the non-overridable mechanical floor — secret-scan +
  verify-before-commit + the command-chaining block, **plus the push floor** (resolve the refspec — including
  `HEAD:main`, a leading `+`, `--all`/`--mirror` and a bare `git push` via upstream/`push.default` — and **block
  any push to a protected branch**, plus secret-scan the outgoing range). It fires on execute regardless of config
  and cannot be waived, because `guard.sh` exits non-zero *ahead of* the permission decision. **Layer 2** =
  `config.outward` (below), the overridable human-approval layer. Standing pre-auth waives the human, never the
  checks.
- **No durable ledger:** single-user = author-is-approver → segregation-of-duties moot → the action's own external
  consequence (moved git ref / GitHub issue event / deploy record) is the audit; the away-run digest is the console
  activity feed + `handoff.md`, not a new artifact.

## issue  · produced by `create-issue`, closed by `close-issue` · *filed into `backlog.md` — a **live open queue** (rewrite-in-place; closed entries leave, GC'd by `prioritize`), not append-only*
- `{ title, kind: bug|feature|debt, description, severity, source, depends_on[] }` — `prioritize` orders on all
  of `depends_on` × `kind` × `severity`; `depends_on` is `[]` for a standalone issue. **Roadmap-derived backlog
  items carry the same three** — `planner:decompose` assigns each phase-item a `kind` + `severity` (a phase's
  `depends_on` comes from the roadmap), so `prioritize` has one uniform ordering key across both producers.
- `source` — where the item came from. For an item **promoted from an inbox `intake`** it carries that message's
  bus `message_id`; that stamp is doing two jobs at once — it is the intake's **idempotency anchor** (a re-run
  promotion finds the item already present and no-ops) *and* the key the console's **"my requests"** surface uses to
  correlate a submitted request to the item it became.
- `github_ref` — the mirrored GitHub issue number (`create-issue` opens it; `close-issue` closes it); **optional**
  — present only when the outward mirror was approved.
- **When mirrored, GitHub owns open/closed state** (the backlog holds only `github_ref`, no duplicated local
  `state`). **A local-only item (no `github_ref`) is closed by its backlog `done`-flip** (which rides the
  item-tail `commit`); `prioritize` GCs on the done-flip, so a greenfield issue with no ref is still closeable +
  collectable — `close-issue` just exits quietly (nothing outward to close).

## config.json  · written once by `/start`, read on demand · *rewrite-in-place · static after init (committed)*
- `project_root` — `./project` (greenfield) | `.` (brownfield); makes code-touching skills path-agnostic
- `run` — per-project run config (model/effort routing, wave caps — fields grow as those land)
- `retention` — the memory-bound knobs the `audit` pass reads: `sessions_k` (per-node `# Sessions` cap — the
  retention script's only knob) + the scheduling thresholds `prioritize` trips on (`decisions_superseded_n` —
  **superseded** decision bodies awaiting GC, the count retention actually lowers, not the active count;
  `items_closed_m`; `every_p_items`). Absent → shipped defaults (sessions_k 10, decisions_superseded_n 30,
  items_closed_m 10, every_p_items 15). The Sessions trigger fires with a **margin** above `sessions_k` (the cap
  restores headroom), so a single append can't re-trip the audit.
- `align` — the drift-scan knobs, read by `prioritize` (trigger) + `align` (budget): `every_n_commits` (commits
  since `.workflow/align/anchor.json`'s `base_sha` before an `align` item is injected) + `max_agents` (hard cap
  on the semantic pass's fan-out; deferred surface rides the next scan). **Decoupled from `retention`** (drift
  risk ≠ memory pressure). Absent → shipped defaults (every_n_commits 20, max_agents 6).
- `demo` — the demo-sandbox knob read by `create-demo`: `max_refine_rounds` (the cap on demo regenerations
  before the refine loop stops auto-proceeding and **escalates to a live `discuss`**). Absent → shipped default
  (`max_refine_rounds` 3).
- `checkpoint` — the park-deadline knobs, **read by the console daemon** (the only always-alive process, so the
  only one that can own a timer): `deadline_hours` (the orchestrator stamps an *absolute* `deadline` onto the
  parked record as *now + this*; once passed, the daemon escalates — a **deadline never auto-proceeds**, it only
  raises the alarm) + `reminder_hours` (how often the daemon re-alerts while the checkpoint is open and not yet
  overdue). Absent → shipped defaults (`deadline_hours` 24, `reminder_hours` 4).
- `notify` — the away-channel, **read by the console daemon**: `webhook` `{ url, kind: generic|slack }` +
  `desktop` (bool). The **webhook is the real away channel** — it reaches a phone and works from a detached
  daemon; a desktop toast is **best-effort only** (it needs a session bus, has none on WSL/headless, and reaches
  only someone already at the machine, who is by definition not away). Absent → desktop best-effort and **no away
  alerting at all**: the human polls the console. That degradation is deliberate and must be stated plainly rather
  than papered over — an alert channel that silently reaches nobody is worse than a documented absence.
- `outward` — the standing-pre-authorization allowlist for outward actions, in Claude Code's own
  `permissions.{allow, ask, deny}` shape (deny→ask→allow, first-match-wins), **coarse per-action-class**
  (`push` / `issue-create` / `issue-close` / later `deploy` / `send`). Absent → **all `ask`** (MVP-safe:
  every outward action gated per-action, queued to `outbox/`). This is Layer 2 (human approval); it never waives
  Layer 1 (`guard.sh`). Optional `outbox_ttl` sets the pending-action expiry.
  **This key is the sole owner of the outward allow/ask policy.** The harness's own `settings.json` deliberately
  carries **no competing `ask`** for the outbox-covered classes: an outward action is approved through the outbox +
  a console `release` and fired *later*, at a scheduler boundary — a static harness prompt would fire into a
  terminal nobody is watching and block the very away-release the model exists to serve. So the harness stays out
  of the outward path, and the gate is: **skill self-gate (this key) → outbox/release (the human) → `guard.sh`
  (the floor)**. The consequence is deliberate: a *mis-coded skill* that runs an outward command directly is no
  longer caught by a prompt — only by the floor. That trade buys the away-release; a bug in first-party skills is
  fixed, not fenced.
  **Fine-grained scoping** (never auto-push `main`) belongs in `guard.sh`, **not** a config allow-pattern (Claude
  Code documents arg-constraining patterns as fragile → use deny + hooks) — see `guard` below.
- `runner` — the relaunch-runner, read by the daemon that hosts it: `{ enabled }`. When on, the daemon relaunches
  `claude` (a fresh process per ticket = a clean context window for free) whenever there is unconsumed work and
  **no orchestrator is live** — the last link that lets an away verdict actually *resume* the loop rather than sit
  in the inbox until someone reaches the terminal. Because the runner is itself a spawner, it **checks a liveness
  marker before launching**: a duplicate orchestrator would be the package's own defect rather than operator error
  (the single exception to the otherwise operator-assumed one-orchestrator rule). Absent → off: the console still
  works, but nothing resumes a whole-parked loop without a human at the terminal.
- `remote` — opt-in remote (phone) access, read by the daemon: `{ enabled, transport: access | tailscale }`.
  **Absent / `enabled: false` / no transport → the remote socket is not served at all** (loopback only). The
  transport is a **declaration**: the operator stands up Cloudflare Access or `tailscale serve` in front of
  `bus.json`'s `remote_port` and is responsible for it being real — the same operator-responsibility stance as the
  single-orchestrator run-constraint. It is *not* a free-text URL: the value picks what the daemon will serve.
  `transport: tailscale` additionally unlocks **credential-bearing `setup` verdicts** on the remote surface,
  because WireGuard is **end-to-end encrypted**; `transport: access` does **not** — Cloudflare terminates TLS, so a
  returned key would transit their edge in plaintext. Everything else on the remote surface is identical.
- `guard` — the Layer-1 floor's only knob: `protected_branches` (**add-only**). `main` and `master` are **always**
  protected and cannot be removed; this list *adds* to them (e.g. `release`, `prod`). The floor itself is
  non-overridable — the loop never pushes a protected branch and never pushes a secret in the outgoing range,
  regardless of `outward`. Absent → `{main, master}`. (Un-protecting a branch is deliberately not a config toggle:
  disabling a safety floor should cost an edit to `guard.sh` itself, which is a visible, owner-level act.)

## secret store  · written by the orchestrator when a `setup` verdict returns a `sensitive` value, read when the loop needs that credential · *`.workflow/secrets/`; RUNTIME, gitignored, kept on a native filesystem; each entry created `0600` (restricted ACL on Windows) with an atomic write*
The home for the **live credentials** a human hands over at a `setup` checkpoint (an API key, a webhook secret) —
the one place the loop keeps a secret.
- **Owner:** the orchestrator **writes** it (on consuming a `sensitive` `returns`) and **reads** it (the setup
  verify-probe). Nothing else writes it.
- **Never** logged, never echoed to `state.json`/`handoff.md`, never committed. The inbox record that carried the
  value is **unlinked immediately** after the write (the one consumer-delete carve-out).
- **These are credentials, not memory — the retention/`audit` prune never sweeps them.** Retention bounds the
  append-only *memory* tier; a cap deleting a live key would break a working setup. Removal is **explicit**
  (rotation / teardown), never automatic.
- Same atomic-`0600`-create discipline as the bus token (create *with* the mode, never write-then-`chmod`);
  Windows has no `0600` → explicit ACLs, the same target-OS/FS family as the other runtime pins.

## bus.json  · written by the bus daemon at boot, read by `/start` + the browser · *`.workflow/bus.json`; RUNTIME, gitignored, atomic write; kept on a native filesystem*
- `{ pid, port, token, started_at, remote_port?, remote_token? }` — the daemon's discovery + auth record. `port` =
  a dynamic **loopback** port (bind `127.0.0.1:0`, read back — the port is **not** a secret). `token` = the CSPRNG
  **capability token** required as a header on every request (authentication; **distinct** from a checkpoint
  correlation `token`). `/start` health-checks `port`+`token` to **adopt-or-spawn** the daemon; the daemon holds a
  `flock` for its lifetime as the liveness authority.
- `remote_port` / `remote_token` — present **only** when `config.remote` declares an identity transport. This is
  the **reduced remote surface** (reads · opinion verdicts · the static demo); the operator points their
  `cloudflared` / `tailscale serve` at `remote_port`, and **never** at `port` — `port` is the full-surface loopback
  socket (outward `release`, returns-bearing `setup` verdicts) that must never be fronted. `remote_token` is a
  **separate** CSPRNG secret, never the loopback `token`, paired to the phone by QR + URL fragment.

## state.json  · the live loop pointer (volatile, gitignored) · *published atomically each iteration (write-temp → `fsync` → `rename`) — logically in-place, physically a rename so a bus reader never catches a torn file; RUNTIME, kept on a native filesystem*
- `status` ∈ `{ intake, building, idle }`
- `node` — current loop node; value ∈ the `loop.md` node labels (e.g. `planner:plan-one`, `verify`)
- `current_item` — backlog id or `null` · `wave` — wave id or `null` · `note` — human-readable cursor

## handoff.md  · the durable resume anchor (committed) · *rewritten whole each handoff, never appended; published atomically **and durably** (write-temp → `fsync(file)` → `rename` → `fsync(dir)`) — the one file where crash-durability, not just atomicity, is mandatory*
- `current_item`, `loop_position`, `parked[]`, `base_sha` — the commit it was written against; a cold start
  reads this + `git log <base_sha>..HEAD` (bounded to one session's delta) and rebuilds position.
- `consumed[]` + `consumed_through` — the inbox **consumed-set** (bus-assigned `message_id`s already applied) and
  its low-watermark. Lives here because this is the durable anchor a cold start rebuilds from — exactly the moment
  the set is load-bearing (it makes the post-restart inbox re-read a no-op). Ids only, never message bodies, so it
  stays small and carries no secret; pruned to ids above `consumed_through`.

## per-item artifacts  · on disk
`plan` / `changelog` / `verify-verdict` / `debug-report` live under `.workflow/items/<id>/` — `planner`
`mkdir`s the dir on demand when it writes `plan.md`; the dir is **item-scoped**, committed while the item
is open (crash-survival) and **pruned once closed** by the `audit` pass — but **only** after `document` folds
its essence and writes a `promoted.json` (`{ "promoted": true }`) marker into the dir; without it the prune
skips the dir, so retention never deletes un-promoted memory. `decision-record`s stay global +
append-only under `<project_root>/docs/decisions/`, with a VOLATILE `index.md` + superseded bodies GC'd to git;
the previously-reserved `checkpoints/` is **retired → `outbox/`** (the pending-outward-action queue). Rule: per-item
ephemeral artifacts are item-scoped; cross-item memory is type-scoped.
