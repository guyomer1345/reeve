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

## parked-ticket  · written by the orchestrator when a ticket parks on a checkpoint · *`.workflow/parked/<id>.json`; RUNTIME, gitignored, kept on a native filesystem; every entry mirrored in `handoff.parked[]` for cold-start rebuild*
- `{ ticket_id, token, worktree?, branch?, loop_position, checkpoint: {kind, request}, predicted_outcome, deadline }` — `worktree`/`branch` are **absent for a pre-build (intake-stage) park** (a `demo`/`reconcile` checkpoint parks before any build worktree exists); a build-stage park always carries them. The **absolute `deadline` is also the alert-dedup key** (`ticket_id` + `deadline`): a ticket that parks, resolves, and re-parks stamps a fresh `deadline`, so the daemon alerts on the new checkpoint rather than treating it as already-seen.
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

**`message_id`** — the filename stem (`<ts>-<uuid>-<pid>`) **is** the message's canonical, bus-assigned id. **One id,
no second one:** it is the `Location` ticket the `202` returns, the console's `localStorage` key, the consumed-set
entry, and the `source` stamp on a promoted item. A client-supplied `ticket` field is therefore *not* carried — the
caller cannot know the id at POST time, and a second id would correlate "my requests" against the wrong one.

**Ids are issued in VISIBILITY order, and the watermark depends on it.** The bus allocates a message's name and
publishes it under one lock, and never re-issues a name at or below the last (its floor is the higher of the newest
name on the inbox and the published `consumed_through` — the inbox's steady state is *empty*, so the disk alone is
not a floor). Without this a message can become visible carrying a ts *below* one already visible, the orchestrator
publishes a watermark over a message it never saw, and the bus GCs a message nobody consumed — measured, and silent.

**Consume = record, never delete.** The bus is the sole writer of `inbox/`, so the consumer **never removes a
message** (delete-on-consume would make the inbox two-writer). Instead the orchestrator keeps a durable
**consumed-set** of `message_id`s in its own partition (`handoff.md`): at each boundary it lists `inbox/`, **skips
ids already in the set**, applies the rest, adds their ids, and atomically republishes. A cold start re-lists
`inbox/` and the set makes the re-read a no-op — this is what stops a restart from re-promoting an
already-consumed intake or re-firing a control op.

**The drain is split, and only one half is prose.** *Which* messages are new, in what order they apply, what the
watermark is, and what may be pruned is a pure function of (`inbox/`, `handoff.md`) with exactly one right answer —
that half is `scripts/drain.py` (`list` → apply → `record`), which also gives `handoff.md` the atomic+durable
publish a text-writing tool cannot express. *Applying* a message is judgment and stays in the orchestrator's brief.
The line is measured, not stylistic: driven against real sessions the apply half was right every time, while the
bookkeeping half silently produced an unbounded set.

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
- **`kind: intake`** — `{ ask, node_ids? }` — a new-work request; the orchestrator **promotes** it into
  `backlog.md` through triage — **never a direct backlog write** (that would make the backlog two-writer).
  `node_ids` present when the project-map screen emitted it. **Anchor:** promotion **stamps the source `message_id`
  into the new item's `source`**, and re-promotion is skipped when an item already carries it — the same stamp that
  lets the console's "my requests" surface correlate an intake to the item it became.
- **`kind: control`** — `{ op: reprioritize|pause|resume }` — a loop-control command honored at the next
  boundary (non-preemptive). **Anchor:** none is possible (a control op leaves no durable artifact to check), so
  **control ops MUST be idempotent** — re-applying one is a no-op by construction (`reprioritize` re-orders the same
  backlog to the same order; `pause`/`resume` each re-set a flag). The enum is therefore **closed and
  bus-validated**: a non-idempotent op cannot be added without bringing its own anchor, and an open set would admit
  one through the front door.
- **`kind: release`** — `{ action_ids[] }` — a human **batch-approval** of pending outward actions; the
  orchestrator executes each named `outbox` entry (re-run through `guard.sh`) at the next boundary and marks it
  `executed`. **Always by explicit `action_ids`** (a snapshot of what the human saw — items enqueued after the glance
  are simply not in the set); never an "approve-all-pending" wildcard. Distinct from `verdict`: it resumes **no**
  parked ticket (an outward action never parked the loop), it just fires a deferred side-effect. **Anchor:** the
  outbox entry's `status` — an entry already `executed` is skipped, so a re-applied release is a no-op. (The
  *message* dedups here; an external side-effect with no natural idempotency — `issue-create` — carries its own
  key on the outbox entry.)

## outbox / pending-outward-action  · written by the orchestrator when a skill defers an outward action, cleared by the `release` consumer · *`.workflow/outbox/<id>.json`; RUNTIME, gitignored, single-writer (orchestrator), kept on a native filesystem; read by the bus to render the console's release panel; the mirror of the bus-owned `inbox/`*
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
  daemon; a desktop toast is **best-effort only** (Linux `notify-send`, and it needs a notification daemon to own
  the `org.freedesktop.Notifications` bus name — absent on a headless/WSL box even though the session bus itself
  exists, so the toast fails there — and it reaches only someone already at the machine, who is by definition not
  away). Absent → desktop best-effort and **no away alerting at all**: the human polls the console. That
  degradation is deliberate and must be stated plainly rather than papered over — an alert channel that silently
  reaches nobody is worse than a documented absence, so the daemon reports away-channel readiness in `status`.
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
- `runner` — the relaunch-runner, read by the daemon that hosts it as a **job**: `{ enabled }`. When on, the
  daemon relaunches `claude` (a fresh `claude -p` process per ticket = a clean context window for free — this retires
  the manual-`/clear` stopgap) whenever there is **applicable** unconsumed work and **no orchestrator is live** — the
  last link that lets an away verdict actually *resume* the loop rather than sit in the inbox until someone reaches the
  terminal. Absent → off: the console still works, but nothing resumes a whole-parked loop without a human at the
  terminal. The behaviour is fixed (no user knobs in MVP); the load-bearing rules:
  - **Trigger = applicable work only.** It spawns only for a pending `verdict` or `intake` (the kinds that advance a
    dead/parked loop) via `drain.py list` — never for a lone `control` (nothing to drive) and never for a `release`
    (loopback-only, so a human was present to approve it). A message that can't resume anything doesn't spawn a loop
    that would immediately re-park.
  - **Liveness precondition** = the `orchestrator.lock` `flock` probe (above): a duplicate orchestrator would be the
    package's own defect rather than operator error — the single exception to the otherwise operator-assumed
    one-orchestrator run-constraint. The runner's own spawn goes through `flock -n`, which is also the double-launch latch.
  - **The launch** = `flock -n orchestrator.lock claude -p "<resume prompt>"`, detached (`setsid`, DEVNULL stdio),
    cwd = the launch root (so it loads the project's `CLAUDE.md` + `.claude/settings.json`), on the user's own
    `~/.claude` auth. **Never `--dangerously-skip-permissions`** — that would bypass the settings `ask` floor
    (deploy/network); `guard.sh` still gates it. The resume prompt forces the boundary drain rather than
    relying on the "drive only if state.json shows an active run" guard.
  - **Trust precondition (MEASURED):** a `claude -p` in a workspace Claude Code has not trusted **ignores
    `settings.json`'s allowlist** and stalls, so the loop can't run its own tools. `/start`'s trust dialog establishes
    it; the daemon **surfaces** an untrusted workspace in `status` (a warning, never a spawn gate — a misread must not
    silently disable the runner).
  - **Crash-loop + stall safety.** A relaunch that exits **without advancing the watermark** backs off (doubling) and,
    after a cap, **hard-stops and fires an away alert** — closing the notifier's deferred thrash/crash alert arm. A relaunch
    that **hangs without draining** (an inert/untrusted `claude`) is killed after a stall timeout and scored the same
    way, so it can't pin the runner in-flight forever. A relaunch that *drains* is doing real work and runs freely.
  - **WSL:** the runner is the overnight mechanism, but the daemon hosting it dies with the last terminal unless
    `.wslconfig` sets `vmIdleTimeout=-1` — surfaced in `status`, never implied.
- `remote` — opt-in remote (phone) access, read by the daemon: `{ enabled, transport: access | tailscale, port?,
  public_url? }`. **Absent / `enabled: false` / no transport → the remote socket is not served at all** (loopback
  only). The transport is a **declaration**: the operator stands up Cloudflare Access or `tailscale serve` in front of
  `bus.json`'s `remote_port` and is responsible for it being real — the same operator-responsibility stance as the
  single-orchestrator run-constraint. It is *not* a free-text URL: the value picks what the daemon will serve.
  `transport: tailscale` additionally unlocks **credential-bearing `setup` verdicts** on the remote surface,
  because WireGuard is **end-to-end encrypted**; `transport: access` does **not** — Cloudflare terminates TLS, so a
  returned key would transit their edge in plaintext. Everything else on the remote surface is identical.
  - `port` — the **fixed loopback port** the remote socket binds (default `8799`). Fixed, not daemon-chosen: the
    operator points a tunnel at it once and the phone is paired against it once, so a per-boot port would break the
    away channel every restart. Bind-in-use degrades to no-remote with a warning, never a dead daemon.
  - `public_url` — the tunnel's `https://` origin. **Load-bearing for the transport, not just the pairing link:**
    the daemon builds the copy-paste pairing URL from it (`<public_url>/#t=<remote_token>`), *and* adds
    its host to Socket A's Host-allowlist — a proxy that forwards the original Host would otherwise have all its
    traffic rejected. Absent → the pairing link and the forwarded-Host allowlist are both unavailable (surfaced in
    `status`); only loopback-Host proxy traffic (Host-rewriting proxies) still reaches A.
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
- Same atomic-`0600`-create discipline as the bus token (create *with* the mode, never write-then-`chmod`) **and the
  same verification**: the achieved mode is `stat`'d, because the create-with-mode discipline is a no-op on a mount
  that ignores mode — the WSL repo mount returns `0777` for a `0600` create, silently. That is not a Windows-only
  gap (the original framing); it is **any mount that ignores mode**, and it is why this path is pinned. Windows has
  no `0600` → explicit ACLs, the same target-OS/FS family as the other runtime pins.

## runtime.json  · written by `/start` when it relocates the runtime tree, read by every process that touches a runtime path · *`.workflow/runtime.json`; RUNTIME, gitignored, atomic write; deliberately NOT on a native filesystem — it is the pointer TO it*
- `{ runtime_root }` — an absolute path. The workflow tree spans **two filesystems** whenever the repo lives on a
  mount whose file-mode or `rename` guarantees are weak: the atomicity- and mode-sensitive runtime paths are
  relocated to a native filesystem, while committed artifacts stay in the repo by construction. This pointer is what
  makes that relocation **findable** — without it nothing could locate the relocated half, since the daemon's own
  discovery record lives inside it.
- **Absent ⇒ no relocation happened ⇒ the workflow dir IS the runtime root.** That is the common case and costs zero
  indirection; the file exists only on a relocated install.
- **Never committed, never pinned.** The path is machine-specific, so committing it would hand another machine a
  wrong root; and it cannot itself be relocated, since it is the thing that says where the relocation went — it must
  sit at a fixed, known spot on the repo mount.
- A pointer naming a **missing** root is a hard error, never a fallback to the repo mount: falling back silently
  would land the capability token and the inbox on the very filesystem the relocation exists to avoid.

## bus.lock  · created and held by the bus daemon for its process lifetime · *`.workflow/bus.lock`; RUNTIME, gitignored, created-never-replaced; kept on a native filesystem*
The daemon's **singleton election**. Holding it *is* the liveness claim: the kernel releases it when the holder dies,
which is what makes it immune to the PID reuse a pidfile would suffer. Contains the holder's pid for humans; nothing
reads that value as authority.
- **It is a separate file from `bus.json`, and that is load-bearing, not tidy.** `bus.json` is republished by atomic
  rename, and a rename **swaps the inode out from under a held lock** — the next daemon opens the *new* inode, finds
  it unlocked, and starts. Two daemons, no error. (Measured true on ext4 *and* on the WSL 9p mount; a fixture test
  pins it, so a platform change is a loud failure rather than a silent regression.) A lock file is therefore only
  ever created and written in place — **never renamed over**.
- Liveness = **the held lock plus a token'd `/health`**: the lock proves *someone* is alive, the health check proves
  it is ours. A free lock means any `bus.json` is stale, whatever pid it names.

## orchestrator.lock  · held by an orchestrator launch for its session lifetime, probed by the daemon's relaunch-runner · *`.workflow/orchestrator.lock`; RUNTIME, gitignored, created-never-replaced; kept on a native filesystem*
The **single-orchestrator liveness marker** the relaunch-runner checks before it spawns, so it never launches a
duplicate alongside a live orchestrator (the single-orchestrator run-constraint's honest residual would become the
runner's own defect). **Distinct from `bus.lock`** — that is the *daemon's* election; this is the *orchestrator's* liveness.
- **Both launch paths hold it via an `flock`.** A human starts the orchestrator through the shipped **`loop.sh`**
  launcher (`exec flock -n .workflow/orchestrator.lock claude …`), which holds the lock across the `exec` for the
  session's whole life; a **runner-launched `claude -p`** is spawned as `flock -n .workflow/orchestrator.lock claude -p …`,
  so it holds it too. The runner probes the lock (a non-blocking `flock`); **held ⇒ someone is driving ⇒ back off**.
- **The kernel drops it on death**, so it never goes stale the way a pidfile would — the same property that makes
  `bus.lock` trustworthy. A `flock -n` probe is the whole liveness test; a free lock means no orchestrator is live.
- **The runner's own spawn goes through `flock -n`,** so even if a human starts in the probe→spawn window the launch
  aborts rather than doubling — the latch is the lock, not a flag. **Why not a `/proc` scan for a live `claude`:**
  measured unsound — Claude Code runs a constellation of claude-named helper processes (`claude daemon`, `bg-pty-host`,
  `bg-spare`, a versioned session process) sharing the repo cwd, so it cannot separate a driving orchestrator from a
  helper or a casual session.
- **The bare-`claude` bypass is the one operator residual** (same footing as the single-orchestrator run-constraint): a human who enables `config.runner` but
  starts bare `claude` instead of `loop.sh` is invisible to the runner, which may then spawn a duplicate. Documented,
  not fenced — the same footing as the single-orchestrator run-constraint itself.

## bus.json  · written by the bus daemon at boot, read by `/start` + the browser · *`.workflow/bus.json`; RUNTIME, gitignored, atomic write; kept on a native filesystem*
- `{ pid, port, token, started_at, remote_port?, remote_token? }` — the daemon's discovery + auth record. `port` =
  a dynamic **loopback** port (bind `127.0.0.1:0`, read back — the port is **not** a secret). `token` = the CSPRNG
  **capability token** required as a header on every request (authentication; **distinct** from a checkpoint
  correlation `token`). `/start` health-checks `port`+`token` to **adopt-or-spawn** the daemon; the daemon holds the
  `bus.lock` (above) for its lifetime as the liveness authority — **never a lock on this file**, which it renames.
- **The token file is created 0600 and then `stat`'d to confirm it.** A mode is a request, not a guarantee: on the
  WSL repo mount a 0600 create silently returns 0777, so the token would be readable by other users on the machine
  with nothing reporting a failure. This is the primary reason this path is pinned. If the achieved mode is looser
  than asked, the daemon **surfaces it to the human** rather than pretending the file is protected.
- `remote_port` / `remote_token` — present **only** when `config.remote` declares an identity transport. This is
  the **reduced remote surface** (reads · opinion verdicts · the static demo); the operator points their
  `cloudflared` / `tailscale serve` at `remote_port`, and **never** at `port` — `port` is the full-surface loopback
  socket (outward `release`, returns-bearing `setup` verdicts) that must never be fronted. **Both are echoed here for
  discovery but SOURCED from durable state, not minted per boot:** `remote_port` is `config.remote.port`
  (fixed), and `remote_token` is read from the persisted `.workflow/remote_token` file (below). This is the load-
  bearing difference from the loopback `port`/`token`, which are freshly minted each boot — a phone paired once must
  keep working across restarts. `remote_token` is a **separate** CSPRNG secret, never the loopback `token`, paired to
  the phone by a copy-paste link (a QR is a scoped fast-follow) whose URL fragment never leaves the browser.

## remote_token  · minted once by the bus daemon on first remote-enabled boot, read on every boot thereafter · *`.workflow/remote_token`; RUNTIME, gitignored, atomic `0600`-create + `stat`-verify; kept on a native filesystem*
- A single CSPRNG line — the **stable second factor** gating Socket A, over the transport identity. **Distinct from
  the loopback `token`** in `bus.json` (the loopback token is never reused remotely), and unlike it
  **persisted, not per-boot**: a phone pairs against this token once and the operator points a tunnel once, so a
  token reminted each boot would go stale on **every restart** — routine on WSL, the platform the away channel most
  needs to survive. Minted only on first use; every later boot reuses the file. `bus.json` echoes its current value
  for discovery, but this file is the source of truth.
- **Never served on the surface it gates.** The remote page carries no token in its HTML — it would hand the surface
  to anyone past the transport in one GET. The token reaches the phone only through the pairing fragment (loopback
  `/api/pairing` → a copy-paste link), which never leaves the browser.
- **Same atomic-`0600`-create + `stat`-verify discipline as the loopback token and the secret store** (a mount that
  ignores mode returns `0777` silently). **Deleting the file re-pairs everyone** — the only rotation path, and a
  deliberately visible, owner-level act.

## alerts.json  · written and read by the bus daemon alone, to record which checkpoints it has already alerted on · *`.workflow/alerts.json`; RUNTIME, gitignored, atomic write; kept on a native filesystem*
- `{ checkpoints: { "<ticket_id>|<deadline>": { first_alert, last_alert, escalated } }, dead_letters: { "<message_id>": { at } } }`
  — the daemon's own away-alert bookkeeping. It **cannot** live in `parked/` (the orchestrator's single-writer
  partition, not the daemon's) nor in the boot-scoped `bus.json` (rewritten at boot, so it would be destroyed at
  exactly the restart it must survive), so it is a **fourth daemon-owned path**. Loaded at daemon start, so a
  routine restart — frequent on WSL — does **not** re-alert every open checkpoint (which would train the human to
  ignore the channel). **A lost or unparseable file re-alerts rather than going silent** — a missed alert is the
  failure this exists to prevent, so the safe direction is noise. Delivery failure is a *channel* property: a
  failing webhook backs off the whole channel (doubling, capped at `reminder_hours`) and does **not** mark the
  checkpoint alerted, so the reminder path retries it once the channel recovers. Keys are pruned when the
  checkpoint resolves / the dead-letter clears, which bounds the file and is what makes a re-park re-alert.

## state.json  · the live loop pointer (volatile, gitignored) · *`.workflow/state.json`; published atomically each iteration (write-temp → `fsync` → `rename`) — logically in-place, physically a rename so a bus reader never catches a torn file; RUNTIME, kept on a native filesystem*
- `status` ∈ `{ intake, building, idle }`
- `node` — current loop node; value ∈ the `loop.md` node labels (e.g. `planner:plan-one`, `verify`)
- `current_item` — backlog id or `null` · `wave` — wave id or `null` · `note` — human-readable cursor

## handoff.md  · the durable resume anchor (committed) · *`.workflow/handoff.md`; rewritten whole each handoff, never appended; published atomically **and durably** (write-temp → `fsync(file)` → `rename` → `fsync(dir)`) — the one file where crash-durability, not just atomicity, is mandatory. Committed, so it stays on the repo mount (never relocated); the bus reads it for the `consumed_through` watermark, and a torn read can only make inbox GC lag, never over-collect*
- `current_item`, `loop_position`, `parked[]`, `base_sha` — the commit it was written against; a cold start
  reads this + `git log <base_sha>..HEAD` (bounded to one session's delta) and rebuilds position. **Prose, written
  by the orchestrator.**
- **The machine block** — a fenced, delimited region (`<!-- drain:begin -->` … `<!-- drain:end -->`) holding
  `consumed[]`, `consumed_through` and `dead_letters[]`. **Two authors, one file:** `drain.py` rewrites only the
  block, the orchestrator rewrites only the prose around it, and neither touches the other's half. The orchestrator
  **never hand-writes or deletes the block** (a session that rewrites the file wholesale and drops it loses the
  *set* — recoverable only in the sense that each kind's effect anchor then catches the re-application; the block
  structure itself is rebuilt).
- `consumed[]` + `consumed_through` — the inbox **consumed-set** (bus-assigned `message_id`s already applied) and
  its low-watermark. Lives here because this is the durable anchor a cold start rebuilds from — exactly the moment
  the set is load-bearing (it makes the post-restart inbox re-read a no-op). Ids only, never message bodies, so it
  stays small and carries no secret; **pruned to ids above `consumed_through`** — which is what bounds it, and is
  the rule a prose brief demonstrably did not carry. **An id at or below the mark counts as consumed even though the
  set no longer lists it** — that is what the mark means, and a walk that reads only the set freezes the watermark
  permanently the first time pruning drops an id beneath it.
- `dead_letters[]` — `{ message_id, reason, at }` for a message that applied to nothing (a verdict whose token is
  unknown or already closed). **Capped (20) and deliberately NOT pruned by the watermark**: this is the one message
  a human most needs told about, and collecting it when the mark passes would erase the notice before it was read.
  It is a defined field precisely because it wasn't — every driven session improvised its own section here, in a
  committed file.

## per-item artifacts  · on disk
`plan` / `changelog` / `verify-verdict` / `debug-report` live under `.workflow/items/<id>/` — `planner`
`mkdir`s the dir on demand when it writes `plan.md`; the dir is **item-scoped**, committed while the item
is open (crash-survival) and **pruned once closed** by the `audit` pass — but **only** after `document` folds
its essence and writes a `promoted.json` (`{ "promoted": true }`) marker into the dir; without it the prune
skips the dir, so retention never deletes un-promoted memory. `decision-record`s stay global +
append-only under `<project_root>/docs/decisions/`, with a VOLATILE `index.md` + superseded bodies GC'd to git;
the previously-reserved `checkpoints/` is **retired → `outbox/`** (the pending-outward-action queue). Rule: per-item
ephemeral artifacts are item-scoped; cross-item memory is type-scoped.
