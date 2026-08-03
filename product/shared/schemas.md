# Shared Artifact Schemas

The data formats that flow between capabilities. One source of truth — skills/agents reference these by
name. On-disk paths are fixed; each schema notes its **write-mode** (rewrite-in-place · append ·
new-record-supersede · create-per-item) and **tier** (see `shared/memory-model.md`). *Retention bounds (the
read law) live in `shared/memory-model.md`.*

<!-- doc-budget: detail split -> schemas-runtime.md -->

> **The runtime substrate lives in [`schemas-runtime.md`](schemas-runtime.md).** This file owns the artifacts
> the loop *produces and consumes*; the sibling owns the records the package's own **processes** own — the
> config `/start` writes, the runtime-root pointer, the daemon's locks and published state, the hook markers.
> Split when this file crossed the **25 000-token Read ceiling** and could no longer be loaded in one call
> (`check_doc_budget.py`). The sibling is **live**, not an archive — those schemas are still edited there, which
> is why the marker above carries no `@ <sha>`.
>
> **A consumer that _parses_ these schemas must read both halves**, and the marker is machine-followable for
> exactly that reason — read it through `check_doc_budget.read_with_splits`, as the contract linter does.
> Parsing the survivor alone reads strictly less than the schema declares; measured on this split, that costs
> two `kind:` values and every `kept on a native filesystem` claim below.
>
> Moved there: `config.json` · `runtime.json` · `.workflow-runtime` · `install-set.json` · `orchestrator-brief managed block` · `statusline.delegate` · `bus.lock` · `orchestrator.lock` · `bus.json` · `remote_token` · `alerts.json` · `session-start warn-once markers`.

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

## knowledge-node  · seeded by `ingest`, authored/refreshed by `document` · *one `.md` per source file at `<project_root>/docs/knowledge/<source-path>.md` (mirror the source tree); STABLE frontmatter + APPEND-ONLY `# Sessions`*
The prose layer over `graph.json`: the structural fields are **copied from `graph.json`** (regenerated, never hand-edited); the `Purpose`/edge-`why`/`# Sessions` are the durable layer. Write each node **exactly** this shape so `retention.py`/`document` can parse it — no hunting the format:
- **Frontmatter** (structural, from `graph.json`): `path` · `type` · `lang` · `tier` · `centrality: { impact, orchestration, in_degree, out_degree }` (the two lenses + degrees) · `commitment` ∈ `{ locked, provisional, unspecified }` · `seeded_by` (e.g. `ingest`).
- **`## Purpose`** — cheap extractive intent (signatures/docstrings); `ingest` seeds it, `document` sharpens intent-vs-actual on touch.
- **`## Edges out`** — one line per `graph.json` edge: `` `<target>` (import|call) — why: `` with the **`why` left empty at seed time** (`document` authors it on first real touch). *(`## Key symbols` is an optional extractive aid.)*
- **`# Lessons`** — APPEND-ONLY, top-level, and placed **immediately before `# Sessions`**; one line per distilled postmortem, written by the `audit` item *before* `retention.py` caps (compression beats raw retention — see `memory-model.md`). **Never capped**, because it is already the compressed form. The placement is a hard requirement, not a style: `# Sessions` is terminal and its region runs to EOF once entries begin, so a `## Lessons` nested under it would be parsed as a session entry and dropped by the cap it exists to survive.
- **`# Sessions`** — the node's **terminal** section, APPEND-ONLY; each entry headed **`## [date] kind | title`** (the strict form `retention.py` splits on); empty until a postmortem (`debug-report`) applies.

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

## verify-verdict  · produced by `verify` · *on disk at `.workflow/items/<id>/verify-verdict.md`; item-scoped ephemeral*
**On-disk contract (load-bearing — both git-native commit gates read it):** the filename is
`verify-verdict.md` (Markdown, never `.json`), and its **first line is exactly `pass: true` or `pass: false`**
(lowercase, one space after the colon) — the machine token `guard.sh` / `pre-commit.sh` parse. The mismatches
and confidence follow as prose on later lines. The consumer **fails closed**: it proceeds only on a well-formed
`pass: true`; a missing file, a wrong extension, or a reworded/absent token **blocks** (a real failure must never
wave through on a format slip). So `verify` MUST emit this token verbatim — never reword it, never move it off
line 1.
- `pass` — line 1, as above
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
`demo`, `qa`, `reconcile`, `forecast` — the verdict is an opinion) or an **action** boundary (do something in the world
the loop can't reach: `setup` — the verdict is "I did it" + a returned artifact, then machine-verified).
- `request` — `{ kind: demo|qa|setup|reconcile|forecast, what, expected, how?(←setup-guide), tasks?[], blocking: true, token }`.
  **`token`** (`{ticket}:{step}:{uuid}`) correlates the async verdict back to this parked ticket. **`tasks[]`** is the
  *set* of setup items a `kind=setup` checkpoint carries (a lone setup is a one-element set); the orchestrator
  coalesces a plan's foreseeable setups (spec `integrations[]`) into one checkpoint **at first-setup-contact** (not
  front-loaded at intake) — an unforeseen setup is raised by `execute` on hitting the wall.
  - **`tasks[]` entry — `{ id, what, secrets?[], provides?[] }`.** `id` is the **task** id (`polar-webhook`), stable
    across the reply so a per-task outcome routes back; `what` is the one-line ask the console shows. **`secrets[]`
    names the credential **KEY NAMES** this task will hand back** (`POLAR_WEBHOOK_SECRET`) — never values. It is what
    lets the console render a *labelled* input per credential instead of asking a human to hand-compose a payload, and
    it is the **source** `config.json`'s `secrets_required[]` accumulates from (that key is the running projection of
    every task's `secrets[]`, not a second declaration of the same fact).
    **`provides[]` is the non-credential mirror** — the NAMES of values the task hands back that are *not* secrets
    (`POLAR_WEBHOOK_URL`, a project id). It renders the same labelled input and lands in the reply's **`artifacts`**,
    never `returns`, so the value stays readable to the orchestrator instead of being shredded into the secret store.
    Two declared lists, not one list with a flag: **which list a name was declared in is what decides the value's
    protection**, and that is a property a composer cannot forget to set (the `sensitive` marker is deleted, not
    renamed). It also carries the one thing a **remote** console can return — those inputs are not gated on the
    credential-socket check, because a webhook URL is not a credential and withholding it left a paired phone able to
    answer a setup task with an outcome and nothing else.
    **Request and reply share NO key name, deliberately** — the request declares NAMES to ask for (`secrets[]` /
    `provides[]`), the reply carries VALUES (`returns` / `artifacts`). That non-overlap is the only reason `park` can
    refuse a reply-side field on a request at all; naming the request half `artifacts[]` would forfeit it.
    **`bus.py park` refuses a request task carrying `outcome`** — that is the *reply's* field (see `verdict` below),
    and a request wearing it reads to a later human as though the question had already been answered. The refusal is
    deliberately narrow: other undeclared request fields are still accepted, because `park` is how the machine ASKS
    for help and a park that hard-fails is a checkpoint that never opens — a worse failure than an extra field.
  - **`how` — `[{ step, url?, breadcrumb?, query? }]`**, the `setup-guide` return: one action per `step`, each with
    the verified deep-link and the still-findable fallback. Structured because the console **renders** it beside the
    form; a plain string is accepted and shown as text, so a guide written before this shape still displays.
- `verdict` — `{ outcome: approve|changes|reject, notes, returns?, artifacts? }` (`pass` ≡ `outcome=approve`); a
  `kind=setup` verdict replaces the single `outcome` with **`tasks[]` — `{ id, outcome, returns?, artifacts? }` per
  task**, so a mixed reply routes each item on its own (`id` matches the `request.tasks[]` id).
- **`returns` is a NAME-KEYED MAP — `{ "<KEY_NAME>": { value } }` — and `returns` MEANS CREDENTIAL.** Every entry is
  protected; there is nothing to mark. The key **is** the credential's name, which is what makes a returned secret
  matchable against the declared set without a second identifier to get wrong; task identity already lives at
  `tasks[].id`, so `returns` never carries one. Multiple credentials from one task are simply more keys.
  **The bus rejects any other shape at `POST /api/verdict` with a `400`** — a payload that cannot be matched must
  fail loudly at the boundary rather than reach the store and read later as total credential loss.
- **`artifacts` is the non-credential half — the same `{ "<NAME>": { value } }` shape, never redacted, never stored.**
  A webhook URL or a project id the task hands back goes here, and stays readable to the orchestrator that has to act
  on it. It is validated exactly as strictly as `returns`: the only thing separating the two is which field a value
  arrived in. **Its producer is the setup form's `provides[]` inputs** (above) — the same row as the credential
  inputs, a different input class, a different field. It shipped declared-but-unproducible for a while and said so
  in place; that is now closed, because a field specified as if it works while nothing can emit it is the same defect
  that made the old `returns` shape a coin toss.
  - **Why the split, and why there is no `sensitive` marker.** There was one, and it was the *sole* trigger for three
    protections at once — redaction out of the orchestrator's context, eligibility for the shred/store path, and
    therefore whether the value was ever removed from the inbox. A **fully conforming** entry that simply omitted it
    was printed verbatim, key and value, and never stored. Protection now comes from the FIELD, which no producer can
    forget to set, rather than from a boolean somebody had to remember. A composer still sending `sensitive` gets a
    `400` naming the field and pointing here.
  **Routing keys off `outcome`, per kind:**
  - **demo** — approve → lock the spec state · changes → `create-demo` (refine) · reject → `discuss`.
  - **qa** — approve → `document`/`commit` · reject → `debug` (`changes` ≡ reject here).
  - **setup** — approve|changes → the orchestrator **verifies the external precondition actually works** (probe the
    key/webhook) *before* proceeding; reject → replan or hard-stop. Every `returns` value is written to
    the gitignored **secret store** (`.workflow/secrets/`, below), **never logged**, and its inbox record **unlinked
    immediately after that write** — the field is what triggers this, not a marker on the entry.
    **The console's setup form is the producer** — the per-task rows (outcome + one labelled input per
    `request.tasks[].secrets[]` name) are what emit a conforming `returns`, and they are the *only* shipped way to
    deliver one. The credential is typed into the page, POSTed once, and never stored browser-side: no
    `localStorage`, inputs cleared on send, and the "my requests" memory records the **outcome only**. It renders
    **only where the socket may accept a credential** (loopback, or a remote socket over an end-to-end-encrypted
    transport) — but that is UX, not the boundary: the `403` at the socket stays the enforcement, because a page is
    never allowed to be the thing that decides. The **`provides[]`** inputs beside it are the producer of
    `artifacts`, and they render on **every** socket: the credential gate exists to keep secrets off a socket that
    cannot carry them, and a non-credential is not one. **The input is deliberately `type="text"`, not a password field** —
    driving the form in a real browser showed masking cost a human the ability to confirm a paste landed whole, and
    made Chrome offer to save the key into its password manager, which `autocomplete="off"` cannot suppress on a
    password field. Masking defended a loopback (or WireGuard) socket against a shoulder while costing correctness
    and copying the credential somewhere nobody asked for.
  - **reconcile** — approve → `prioritize` · else → `ingest`/`discuss`.
  A **timeout never auto-proceeds** — it re-surfaces + reminds (a missing credential can't be skipped). A rejection is
  not always a defect — hence routing by kind, not a universal `debug` sink.

## parked-ticket  · composed by the orchestrator, **written by `bus.py park`** · *`.workflow/parked/<id>.json`; RUNTIME, gitignored, kept on a native filesystem; projected onto `handoff.md`'s **`parked` machine block** for cold-start rebuild*
- `{ ticket_id, token, worktree?, branch?, loop_position, checkpoint: {kind, request, demo_id?, forecast_id?}, predicted_outcome, deadline, opened_at, summary, answered_at? }` — `worktree`/`branch` are **absent for a pre-build (intake-stage) park** (a `demo`/`reconcile`/`forecast` checkpoint parks before any build worktree exists); a build-stage park always carries them. **`checkpoint.demo_id`** is present only for `kind: demo` — the id of the served bundle under `demos/`, so the console builds the `/demo/<id>/` iframe (validated to the served-id shape before it is rendered). **`checkpoint.forecast_id`** is the same passthrough for `kind: forecast` — a **pointer** to the committed `forecasts/<id>.json`, never the chain itself, because `unpark` deletes *this* record at the instant of approval and approval is exactly when the forecast must be frozen (see § forecast). Both are shape-validated before the console is allowed to resolve them. The **absolute `deadline` is also the alert-dedup key** (`ticket_id` + `deadline`): a ticket that parks, resolves, and re-parks stamps a fresh `deadline`, so the daemon alerts on the new checkpoint rather than treating it as already-seen.
- **`bus.py park` is the writer, and the split is the usual one.** The orchestrator composes the **judgment**
  (`token`, `checkpoint.request`, `predicted_outcome`, `loop_position`) and pipes the record in on **stdin**; the
  runner does the **arithmetic** — resolves the runtime root through `Paths`, stamps `deadline` + `opened_at`,
  writes atomically at `0600`, and re-projects the mirror. It **refuses** a record that cannot do its job (no
  `ticket_id`, no `token`, an unknown `kind`, an empty `request`) and writes nothing on refusal. Before this the
  skill hand-wrote the JSON *and* resolved the runtime root itself — a second owner for a rule `Paths` already
  owns, and the reason the mirror could never become a mechanism.
- `deadline` — an **absolute** timestamp stamped at park time as *now + `config.checkpoint.deadline_hours`*
  (default 24h). Absolute, not a duration, because the process that *acts* on it is the console daemon, which
  compares against wall-clock and was not present when the ticket parked. Past it → the daemon **escalates**
  (never auto-proceeds). Stamped at **microsecond** precision: it is the alert-dedup key, and second-resolution
  let two machine-speed re-parks of one ticket collide into "already alerted" — i.e. silence.
- `opened_at` + `summary` — stamped by the runner, and they exist **for the mirror**: they are the two fields the
  projection needs that are not already on the record. `summary` is a one-line label (capped, backticks
  neutralized so it cannot break out of the block's JSON fence), defaulting to `checkpoint.request.what`.
- **`answered_at`** — stamped by the **daemon** the moment a verdict quoting this `token` lands durably on the inbox,
  and published on the console snapshot so the card renders as answered with its form closed. It exists because the
  ticket stays parked until the *orchestrator* drains and unparks it, so "still listed" is correct while "looks
  unanswered" is not — and a setup card that looks unanswered invites a human to type a live credential a second
  time. It is a **timestamp only**: the reply never touches this record (a credential belongs in the secret store or
  nowhere), it is written *after* the message is durable so a display fact can never cost an answer, and the first
  answer wins so a re-send is not a new event. Server-side deliberately, so the state survives a reload and holds on
  a second device — a verdict sent from a paired phone reads as answered on the laptop.
- **A verdict SUPERSEDES an undrained earlier verdict for the same token**, and the console offers "answer again" on
  exactly that condition. Without it, two verdicts for one ticket both sat on the inbox and the drain applied
  **whichever it reached first** — so a human correcting a mistyped credential would leave the *typo* live and
  believe it fixed. Replacement is bounded by the only window in which it can be honest: once the orchestrator has
  consumed the answer it is applied, a later verdict dead-letters against the closed token, and the page stops
  offering to replace it. The superseded inbox record is **unlinked, which is also its shred** (it may hold a live
  credential the human has just replaced), and the new record is durable *before* the old is removed — a failure
  mid-way leaves two answers, never none.
- **This record is the alert trigger.** Writing it *is* the signal: the daemon watches `parked/`, raises the alert
  on a new open checkpoint, re-alerts every `config.checkpoint.reminder_hours`, and escalates once overdue. The
  parking skill sends nothing itself.
- **`bus.py unpark --id <ticket_id>` closes it**, at the drain that applies the verdict: it removes the record —
  which is what makes the "already-closed token" anchor real — and re-projects the mirror. Idempotent, so a
  re-applied verdict no-ops. Not optional: without it the mirror only ever **grows**, and a machine block that
  reads as authoritative would report answered checkpoints as open forever.

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
- **`kind: verdict`** — `{ token, verdict: {outcome, notes, returns?} }` (a `setup` reply carries `tasks[]` instead
  of the single `outcome`; `returns` is the **name-keyed map** declared above and is validated on the way in) — resumes a parked ticket; `token` matches a
  `parked-ticket`; unknown/closed token → **dead-letter + surface** (never a silent resume). **Anchor:** the parked
  `token` — a re-applied verdict finds the ticket already resumed (token closed) → dead-letter/no-op. A non-empty
  `returns` (a setup credential — the field *is* the marker) is written to the gitignored secret store and this inbox record is
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

## refine-ledger  · written by `create-demo` on every regeneration, enforced by `check_demo_bundle.py` · *`.workflow/demos/<item-id>/.refine.json`; RUNTIME, gitignored, lives and dies with its bundle; a dotfile so the daemon never serves it*
- `{ round: N, rounds: [{ round, spec_ref: { path, sha256 }, note? }] }` — `round` is the count of regenerations
  (the circuit-breaker against `config.demo.max_refine_rounds`), and `rounds[]` holds one entry per round.
  **`spec_ref` names the spec file that round was regenerated FROM, and its `sha256` at that moment** (`path` is
  repo-relative — a brownfield project's adopted spec is not `docs/spec.md`). `note` is the human's verdict note
  that drove the round, kept for the escalation's refine history.
- **Why the hash and not just a counter.** `create-demo` says a `changes` verdict edits the **spec** first and
  regenerates from it, and that was prose with nothing behind it. A terminal `approve` **deletes the bundle**, so a
  decision that reached only the demo bytes is destroyed at the moment it is approved and the locked spec never
  learns it — silent, permanent, and precisely the decision the checkpoint existed to capture. The hash is what a
  producer cannot satisfy by remembering to set a flag: `check_demo_bundle.py` refuses a round whose latest
  `spec_ref.sha256` does not match the file on disk, and one whose hash is **unchanged from the previous round**.
  Only the latest round is pinned to current bytes — earlier rounds legitimately describe superseded revisions.
- The lint also refuses `round` over the cap, so the cap stops being a number two documents state and no code reads.
- **It dies with its bundle, so its summary is promoted out first.** On a terminal verdict the route runs
  `check_demo_bundle.py --promote` before deleting the directory, folding `{item_id, approved_at, rounds, spec_ref}`
  into the committed **`demo-approvals.json`** (below). Otherwise nothing later can tell an item that was checked
  from one approved before this floor existed.

## demo-approvals  · written by `check_demo_bundle.py --promote` on a terminal demo verdict, read by `align` · *`.workflow/demo-approvals.json`; **COMMITTED** (ids, counts and a hash — no bytes, no values, so it is small and carries nothing that needs protecting); atomic write; append-with-replace, keyed on `item_id`*
- `{ approvals: [{ item_id, approved_at, rounds, spec_ref: { path, sha256 } | null }] }` — one entry per item whose
  demo reached a **terminal** verdict, written **immediately before the bundle is deleted**. `spec_ref` is the last
  round's, or `null` for a demo approved at round 0 (never refined, so there is no spec-moving claim to record).
- **Why it exists: the refine ledger dies with the bundle.** `.refine.json` is what proves a refine round moved the
  spec, and it lives *inside* `demos/<item-id>/`, which the terminal `approve` deletes. So the moment an item is
  approved, every trace that it was ever checked is gone — and "approved with no ledger" becomes true of **every**
  approved item that has ever existed. That is not a detectable condition, it is a tautology, and a backwards-looking
  check built on it would re-read the whole history on every scan and never clear anything.
- **What it buys.** An item **with** an entry is settled mechanically (the lint already refused any round that did
  not move the spec). An item **without** one was approved before this floor existed, and is the only kind `align`'s
  approved-demo lens has to read by judgment. The set is finite and shrinks to nothing; the promote is a **command
  the route runs**, not a step it is asked to remember. Idempotent on `item_id`, because applying a verdict is
  itself re-appliable after a crash and two entries would later read as two approvals.

## forecast  · written by `create-forecast`, frozen by `forecast.py freeze`, read by the bus's Forecast-chains panel · *`.workflow/forecasts/<id>.json`; **COMMITTED** (key NAMES only — no bytes, no values); atomic write; the item-dir lifecycle — committed while the change is open, pruned by the `audit` pass when it closes, history in git*
The loop's **prediction of its own routing** for one change: an ordered chain of events shown to the human before
the machine walks it. It de-risks the **process** question, the orthogonal axis to `create-demo`'s product one.
- `{ forecast_id, created_at, status: draft|frozen, for: { what, item_id? }, events: [...], horizon: { beyond, note },
  frozen_at?, events_sha256? }` — `forecast_id` is the change/item id and **becomes the filename**, so it is a safe
  single path component (the `ticket_id` rule).
- **`events[]` entry — `{ n, node, what, likely?, fallback?, branch?[], gate? }`.** `n` runs **1..N in sequence** — the
  chain is an ORDER, read as "then", and reality is matched against it position by position. **`node` NAMES A REAL
  `loop.md` NODE** (or a mode of one, a side-door, or a terminal): the forecast is a *prediction over the existing
  graph*, never a second graph, which is the one property that keeps a single routing owner **and** the one
  that makes it lintable — `check_contracts.py --forecast` refuses an event that resolves nowhere.
  - **`branch[]` — `{ if, then }`, and only where the HUMAN would do something different** (pre-supply a credential,
    pick between two integration paths, decide a qa is worth their time). A mechanical self-correcting edge
    (`verify → fails: debug`) is stated once in `fallback`, never unrolled: unrolling redraws `loop.md` per item and
    drowns the one signal the human is here to give.
  - **`gate` — `{ kind, prefill?: { secrets?[], provides?[] } }`** on an event that predicts a checkpoint. `secrets[]`
    holds the credential **KEY NAMES** the step will need, and the console renders a labelled input per key on the
    forecast card. It is the setup **elicitation** front-loaded, never its verification: filled → the secret store; **blank
    → simply not front-loaded**, and the ordinary within-plan ask stands unchanged. That blankness is the whole
    vocabulary for a skippable ask — there is no `defer` outcome, because the stack needs no new state to express it.
- **`horizon` is REQUIRED — `{ beyond, note }`.** The event number past which the chain is guesswork, and a note
  saying so plainly. Execute-discovered needs are unforecastable *by definition*, so a chain that does not mark its
  own blind spot reads as a complete plan; a silent cap reads as "all clear". `forecast.py lint` refuses a record
  without one — the honest-truncation rule, made mechanical rather than asked for.
- **Why COMMITTED, and why that is safe.** The frozen chain is the anchor reality is compared against for the *life
  of the change* — across sessions, cold starts, and a `/rebind` to a machine where the runtime tree explicitly may
  not survive. It is safe to commit because it carries credential **key names only, never values** (the same class as
  `config.json`'s `secrets_required[]`), and `forecast.py lint` enforces that as an **invariant**: a `secrets[]`/
  `provides[]` entry must be a plain `UPPER_SNAKE` name, never an object, and no field named `value` may appear at
  any depth.
- **It CANNOT live in the parked record.** `bus.py unpark` *removes* `parked/<id>.json`, and the `handoff.md` mirror
  deliberately carries ids + kind + summary + opened-at and never a `request` body. So the thing `approve` is meant
  to **freeze** would be destroyed at the exact instant it is approved. The parked record therefore carries only
  **`checkpoint.forecast_id`**, a pointer — the `demo_id` passthrough pattern, one artifact along.
- **`frozen_at` + `events_sha256` are what make the freeze real** rather than a label: the digest is a stable hash of
  `events[]` (key order and whitespace cannot move it), and `lint` refuses a frozen record whose chain no longer
  matches it — a frozen forecast that was edited is not the thing the human approved. `freeze` is **idempotent on
  `frozen_at`**, because applying a verdict is re-appliable after a crash and a moved timestamp would silently
  re-baseline the comparison.
- **Lint ownership splits by fact-domain.** Graph facts (does this event name a real node) → `check_contracts.py
  --forecast`, which already owns `loop.md` parsing. Lifecycle facts (shape, horizon, names-only, the freeze) →
  `forecast.py`. The **prune** is neither: it lives with every other prune in `retention.py`, keyed off the *same*
  `promoted.json` marker that closes the item dir — which is what "copies the item-dir lifecycle exactly" means.

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

## secret store  · written by the orchestrator when a `setup` verdict carries a `returns` value, read when the loop needs that credential · *`.workflow/secrets/`; RUNTIME, gitignored, kept on a native filesystem; each entry created `0600` (restricted ACL on Windows) with an atomic write*
The home for the **live credentials** a human hands over at a `setup` checkpoint (an API key, a webhook secret) —
the one place the loop keeps a secret.
- **Owner:** the orchestrator **writes** it (on consuming any non-empty `returns`) and **reads** it (the setup
  verify-probe). Nothing else writes it.
- **Never** logged, never echoed to `state.json`/`handoff.md`, never committed. The inbox record that carried the
  value is **unlinked immediately** after the write (the one consumer-delete carve-out).
- **These are credentials, not memory — the retention/`audit` prune never sweeps them.** Retention bounds the
  append-only *memory* tier; a cap deleting a live key would break a working setup. Removal is **explicit**
  (rotation / teardown), never automatic.
- **An entry is named by the `message_id` that carried it, so which credentials it holds is read from the
  `returns` maps inside it — EXACTLY, never by guessing.** `/rebind` collects the **keys of `returns` nodes only**
  (never every key in the record, which would sweep in `token`/`value`/`id` and let a project that declares a secret
  named `token` match falsely — a false match reports a *lost* credential as present, which is silence). Values are
  read into memory and never returned, printed, or filed. A record whose `returns` does not conform is **not**
  folded into the loss: it is reported separately as an unreadable-shape entry, because "I cannot read this" and
  "this is gone" are different facts and only one of them is an emergency.
- Same atomic-`0600`-create discipline as the bus token (create *with* the mode, never write-then-`chmod`) **and the
  same verification**: the achieved mode is `stat`'d, because the create-with-mode discipline is a no-op on a mount
  that ignores mode — the WSL repo mount returns `0777` for a `0600` create, silently. That is not a Windows-only
  gap (the original framing); it is **any mount that ignores mode**, and it is why this path is pinned. Windows has
  no `0600` → explicit ACLs, the same target-OS/FS family as the other runtime pins.

## state.json  · the live loop pointer (volatile, gitignored) · *`.workflow/state.json`; published atomically each iteration (write-temp → `fsync` → `rename`) — logically in-place, physically a rename so a bus reader never catches a torn file; RUNTIME, kept on a native filesystem*
- `status` ∈ `{ intake, building, idle }`
- `phase` — **present only during the `/start` bootstrap motion**, value `bootstrap`; absent once the loop
  drives. With it, `node` carries the bootstrap stage (`start:<step>` / `ingest:<stage>`) and `note` the
  human-readable step marker (`"seeding knowledge nodes 40/95"`) — the console's "Now" panel renders these, so
  the motion is visible from the first minute. Written at every stage boundary, same atomic publish.
- `node` — current loop node; value ∈ the `loop.md` node labels (e.g. `planner:plan-one`, `verify`)
- `current_item` — backlog id or `null` · `wave` — wave id or `null` · `note` — human-readable cursor.
  `current_item` (top-level) is the canonical active-item key. **The verify-before-commit gate does not depend on
  it:** it derives the item(s) under commit from the staged `.workflow/items/<id>/` diff and reads state.json only
  runtime-resolved (via `runtime.json`) and tolerantly (`current_item` **or** a nested `position.item`), and it
  fails **closed** — so neither a state.json shape slip nor a relocated runtime tree can silently disarm it.

## handoff.md  · the durable resume anchor (committed) · *`.workflow/handoff.md`; rewritten whole each handoff, never appended. **Atomicity is real but harness-provided:** the orchestrator rewrites the prose with the `Write`/`Edit` tools, which publish via a temp-file + `rename` (the inode changes on overwrite), so a session killed mid-write leaves the **previous** file whole, never torn. The model cannot *express* the atomic `rename`/`fsync`, but the tool provides it — the one thing it must never do is rewrite this file via a `Bash` `>`/`tee` redirect, which truncates in place and **would** tear. **Durable floor = git:** the file is committed each item, so the one case a bare `rename` may not survive — power-loss/kernel-panic before the pages flush — recovers from `git show HEAD:.workflow/handoff.md`, the same `handoff.md + git log` a cold start already rebuilds from. Committed, so it stays on the repo mount (never relocated); `drain.py` writes its own machine block fully durably (write-temp → `fsync` → `rename` → `fsync(dir)`); the bus reads the file for the `consumed_through` watermark, and a torn read can only make inbox GC lag, never over-collect*
- `bootstrap` ∈ `{ installed, ingesting, discussing, reconcile-parked, complete }` — the bootstrap-motion
  ledger `/start` §0 keys its re-run guard on ("initialised" = bootstrap-complete, not install-complete).
  Written at each phase boundary: step 7 writes `installed`; §2/§3 advance it; the session that consumes the
  reconcile verdict (brownfield) or lands the spec (greenfield) writes `complete`. Absent = an older install —
  treated as bootstrap-incomplete, resume the motion.
- `current_item`, `loop_position`, `base_sha` — the commit it was written against; a cold start
  reads this + `git log <base_sha>..HEAD` (bounded to one session's delta) and rebuilds position. **Prose, written
  by the orchestrator.**
- **Two machine blocks** — fenced, delimited regions a SCRIPT owns, each rewritten independently of the prose and
  of each other. **Three authors, one file:** each writer rewrites only its own region, and none touches another's.
  The orchestrator **never hand-writes or deletes either block**.
  - `<!-- drain:begin -->` … `<!-- drain:end -->` (**`drain.py`**) — `consumed[]`, `consumed_through`,
    `dead_letters[]`. A session that rewrites the file wholesale and drops it loses the *set* — recoverable only in
    the sense that each kind's effect anchor then catches the re-application; the block structure itself is rebuilt.
  - `<!-- parked:begin -->` … `<!-- parked:end -->` (**`bus.py park`/`unpark`/`mirror`**) — `parked[]` as
    `{ ticket_id, kind, summary, opened_at }` plus `projected_at`, capped at 50 with the overflow reported as
    `not_mirrored`. This replaces the prose `parked[]` a session used to write by hand. It is a **PROJECTION of
    `parked/`, re-derived on every mutation**, never patched: prose was accidentally self-correcting (the whole file
    was rewritten each handoff, so a resolved checkpoint simply stopped being written) and a persisted block is
    not. It carries **ids + kind + summary + opened-at ONLY — never a `request` body and never the `token`**,
    because a `setup` checkpoint's body is exactly where a credential appears and this file is **committed**. The
    record does not *move* to the committed half, it *projects* onto it. (Which is also why `parked/` itself stays
    uncommitted: committing it would put that body in git, and the runtime tree exists for `rename`/`0600` reasons
    committing does not satisfy.) **`bus.py mirror` re-projects on demand** — `/dispatch` runs it before writing
    the anchor, which is what makes the block *exist* on an install that parked a checkpoint before the block did.
    An **empty** block is a positive statement ("nothing is parked"); an **absent** one means only that nothing has
    projected yet, which is why `/dispatch` projects rather than assuming.
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
**The filenames are FIXED, because they are anchors, not just storage.** Under `.workflow/items/<id>/`:
`plan.md` · `promises.json` · `changelog.md` · `verify-verdict.md` · `debug-report.md` · `plan-delta.md` ·
`promoted.json`. Two mechanisms read them by name and neither can guess: the coverage gates key off
`promises.json`, and the **forecast anchor table** (below) derives "did this event happen?" from the *presence*
of the artifact its node produces. An artifact written under a different name is an event that silently reads as
never having happened.

### the forecast ANCHOR TABLE  · read by `forecast.py reality`, written by nobody
Reality is **derived**, never recorded — there is no second ledger to keep in step, and no writer to forget. Each
`loop.md` node is resolved through the durable effect it leaves behind:

| node | anchor | proves |
|---|---|---|
| `planner` | `items/<id>/plan.md` | the item was planned |
| `execute` | `items/<id>/changelog.md` | the plan was carried out |
| `verify` | `items/<id>/verify-verdict.md` | the artifacts were checked |
| `debug` | `items/<id>/debug-report.md` | something failed and was diagnosed |
| `refine` | `items/<id>/plan-delta.md` | a correction was routed |
| `document` | `items/<id>/promoted.json` | the essence was folded into knowledge |
| `create-demo` | `demos/<id>/` | a sandbox was built |
| `create-forecast` | this record's `frozen_at` | the chain itself was approved |
| `checkpoint:<kind>` | a `parked/` record of that kind — `answered_at` set ⇒ **done**, unset ⇒ **open** | the human was asked |

This table is **exhaustive**: a node not listed here has no anchor and resolves to `unknown` (below). In
particular **`commit` is deliberately unanchored** — it is divergence-exempt, so a probe would buy one column
cell and never a signal; `document`'s `promoted.json` runs *before* it and already says the item reached its
tail; and every anchor here is a pure presence check in a module the console daemon imports, which a `git`
subprocess is not. If it is ever wanted, the exact probe is `git log --grep='^Refs: item #<id>$'` — the trailer
`commit` actually pins, not the subject.

- **`state.json` is deliberately NOT the source.** It is volatile and holds only the *current* node — never a
  history — so "which events have happened" is not a question it can answer at all.
- **Four states, and the fourth is the honest one.** `done` (the anchor is there) · `open` (a checkpoint is parked
  and unanswered) · `pending` (the node has an anchor and it is absent — it has not happened yet) · **`unknown`**
  (the node has *no* anchor in this table, e.g. `decision-engineer`, whose output is a global decision record that
  cannot be tied to one item). `unknown` renders as unknown and never as "did not happen".
- **Divergence is the same table read the other way.** An anchor that fired for a node the forecast never
  named is a **structural divergence** — the machine took a turn nobody saw coming. It does not silently
  continue: the tail is re-forecast and re-shown. The item-complete tail (`commit`, `document`, `close-issue`,
  `prioritize`) is exempt, because it runs for every item and its absence from a chain is the horizon talking,
  not a surprise.
- **The check fires at the SCHEDULER BOUNDARY only, never mid-item** — which is what keeps non-preemption and
  never-stall intact, and is why it is plain control-flow in `loop.md` rather than a routing edge.

`plan` / `changelog` / `verify-verdict` / `debug-report` live under `.workflow/items/<id>/` — `planner`
`mkdir`s the dir on demand when it writes `plan.md`; the dir is **item-scoped**, committed while the item
is open (crash-survival) and **pruned once closed** by the `audit` pass — but **only** after `document` folds
its essence and writes a `promoted.json` (`{ "promoted": true }`) marker into the dir; without it the prune
skips the dir, so retention never deletes un-promoted memory. `decision-record`s stay global +
append-only under `<project_root>/docs/decisions/`, with a VOLATILE `index.md` + superseded bodies GC'd to git;
the previously-reserved `checkpoints/` is **retired → `outbox/`** (the pending-outward-action queue). Rule: per-item
ephemeral artifacts are item-scoped; cross-item memory is type-scoped.
