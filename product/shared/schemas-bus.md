# Shared Artifact Schemas — the console & bus substrate

A sibling of [`schemas.md`](schemas.md). That file owns what the **build loop** produces and
consumes — a spec, a plan, a changelog, a verdict, a forecast. [`schemas-runtime.md`](schemas-runtime.md)
owns the records the package's own **processes** own, and [`schemas-config.md`](schemas-config.md) the knobs a
human turns. This file owns the records that
cross the **console↔orchestrator boundary** — the durable queues, the typed transport on them, and the
side-channels a human's answer arrives through. A skill authors and reads these as *work*, which is what
keeps them out of the runtime half; what they have in common is that **the other end of each one is a
human at the console**, not the loop.

Same conventions as its siblings — on-disk paths are fixed, and each schema notes its **write-mode** and
**tier** (see `shared/memory-model.md`). Nearly all of it is RUNTIME and gitignored: these are queues, not
memory, and the two committed exceptions (`demo-approvals.json`, and the `parked` mirror on `handoff.md`)
carry ids and counts rather than bytes for exactly that reason.

*Split out of `schemas.md` when that file again approached the 25 000-token Read ceiling, per the
split-and-pointer convention in `shared/memory-model.md`. A reference of the form `schemas.md § <name>`
for any section below resolves here — the name is the anchor, and the three files are one schema.*

## checkpoint  · the `checkpoint` gate · *a **durable park boundary**: the orchestrator writes handoff + the request, yields, and resumes via `claude --resume` with the verdict as an authoritative prompt*
A checkpoint sits at **a boundary only a human can cross** — either a **judgment** boundary (does this match intent:
`demo`, `qa`, `reconcile`, `forecast` — the verdict is an opinion) or an **action** boundary (do something in the world
the loop can't reach: `setup` — the verdict is "I did it" + a returned artifact, then machine-verified).
**`steer` is a judgment boundary of a third shape:** it is raised by the machine reaching a **terminal state**
(the goal's acceptance all discharged, or nothing moving for long enough to call it stalled) rather than by a step
that needs a human inside it, so it carries what was achieved and what did not move rather than a thing to look
at. **Raised by the session DRIVER, not by an attended loop** — an attended `converge` stop routes to `idle`,
because the human is already there. Its reason for existing is reachability: an unattended drive that simply goes
quiet is indistinguishable from one that died, and a parked checkpoint is what the away channel already alerts on,
so this kind buys the notification through the machinery that owns it instead of a second sender beside it. Its
ticket id and token are **derived from (goal, reason)**, so a driver relaunched against the same terminal state
rewrites one record rather than filing a ticket per launch — an away channel that repeats itself is one a human
learns to ignore.
- `request` — `{ kind: demo|qa|setup|reconcile|forecast|steer, what, expected, how?(←setup-guide), tasks?[], blocking: true, token }`.
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
    the gitignored **secret store** (`.workflow/secrets/`; § secret store), **never logged**, and its inbox record **unlinked
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
Every console→orchestrator message is **typed** — `kind: verdict|intake|control|release|question` — one uniform durable
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
  of the single `outcome`; `returns` is the **name-keyed map** declared in § `checkpoint` below and is validated on the way in) — resumes a parked ticket; `token` matches a
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
- **`kind: question`** — `{ question }` — a human **asks the project something** and wants prose back, as opposed to
  `intake`, which asks the project to *do* something and wants a ticket back. The two are separated **at the console
  by the human**, not classified by a model: the human already knows which one they meant, and every automatic scheme
  pays a cold start to rediscover it. The orchestrator answers from the knowledge base, the spec and the decision
  record (the `answer` skill) and appends the reply to the **conversation-thread** below. **Anchor:** the thread turn
  **stamps the source `message_id`**, and a re-applied question finds a reply already carrying it → no-op. Same shape
  as `intake`'s promotion stamp, and it is what makes the crash window between *append* and `drain.py record` safe.
  **It is the only kind that changes no build state**, which is why it sorts LAST at a boundary — answering must
  never delay resuming a parked ticket or promoting an item. **Loopback-only** (absent from the bus's remote
  allowlist): the reply path runs the question into `claude -p`, so a question *is* an authoritative prompt — the
  same reason a forecast verdict never rides the remote surface, and strictly sharper, because a verdict's `notes` is
  free text bolted to a bounded decision while a question is the whole prompt.

## conversation-thread  · appended by the orchestrator (or a runner-spawned answerer) when a `question` is drained, read by the bus for the console's thread panel · *`.workflow/thread/thread.json`; RUNTIME, gitignored, atomic write, kept on a native filesystem*
- `{ session_id, turns: [{ message_id, role: human|project, text, at, session_id }], rotations: N }` — one rolling
  conversation, oldest turn first. `role: human` is the question as POSTed; `role: project` is the answer. Every turn
  carries the `message_id` of the question that produced it, which is both the idempotency anchor and the key the
  console's "my requests" surface correlates on — the same id the `202` handed back.
- **RUNTIME, not committed, and the reason is not size.** A committed transcript would be a **second copy of every
  decision it contains**, and the decision record, the spec and the backlog already own those facts — so the thread
  keeps the *conversation* and durable outcomes land with their existing owner (a backlog item, a spec edit, a
  knowledge node). The transcript is a **render**, not the state: the conversation Claude actually resumes lives in
  its own session file, which is machine-local and keyed to the launch directory. Committing the thread would
  therefore buy a readable log and **not** a resumable conversation — a machine move ends the conversation either
  way. Free human prose is also unlintable for secrets, unlike the machine-generated `forecast` record that is
  committed precisely because its safety *is* checkable.
- **`session_id` is the load-bearing field.** Each answer runs `claude -p --resume <session_id>` so follow-ups work;
  a fresh thread has none and the first answer establishes it.
- **Rotation — the thread is cleared and handed off, it is not capped.** Resume **re-sends the accumulated history**,
  so thread length is a *per-message cost*, not merely disk — the one retention arm in this package that governs
  spend rather than bytes. When the estimated context crosses `config.thread.rotate_at_tokens`, the answerer writes a
  **thread handoff** (`.workflow/thread/handoff.md`) — distilling the conversation so far **under the carry-list
  below** — drops `session_id`, clears `turns`, and increments `rotations`; the next question starts a fresh session
  primed with that handoff. **Rotation happens only after `drain.py record`** (`skills/answer` steps 5→6): clearing
  `turns` destroys the idempotency anchor, so rotating first opens a window where the message is unrecorded *and*
  unanchored, and the retry answers twice. This is the same
  disposable-conversation law the orchestrator already runs on (`handoff.md` + rehydrate), applied to the thread —
  and it is deliberately a **separate file**, because `handoff.md` already has two authors (the orchestrator's prose
  and `drain.py`'s machine block) and a third writer on it would break that split.
- **What the thread handoff may CARRY — it keeps only what is not re-derivable.** Rotation is the one distillation
  in this package whose source is **destroyed** (the thread is RUNTIME and gitignored, so the cleared `turns` are
  gone, not archived), which makes `memory-model.md § the distillation law` binding here rather than advisory. The
  handoff carries exactly: **the human's turns verbatim** (once the watermark GCs the inbox message this is the only
  record they were ever asked); **open threads** — what an exchange surfaced that nobody filed, so the next session
  does not re-raise it as new; **outcomes that landed with a real owner, as a POINTER** (backlog id, spec section,
  decision id, knowledge node) and never a summary of what that owner says; **contradictions in the record as the
  two pointers that contradict** ("`state.json` says X, `parked/A.json` says Y"), never a verdict on which is right;
  and **`rotations` plus the number of turns dropped**, so the next session knows it inherited a conversation.
- **It carries NO project prose answer, and that is the structural part.** Every answer came from this project's own
  record by construction (`skills/answer` step 3), so it is **re-derivable** — and an answer that is *not*
  re-derivable is exactly an invented one. Restating answers here would hand the next session the inventions among
  them with the record's authority and none of the doubt, *after* the turns holding the evidence were cleared —
  the failure `memory-model.md § the distillation law` records. Dropping the prose makes it impossible rather than
  policed. A follow-up after a rotation re-derives from the record instead of inheriting a summary: the point, not
  the cost.
- **Estimated, not measured.** Token count comes from the shared `chars_per_token` calibration (`config.doc_budget`),
  the same estimator the context-budget law uses — there is no way to read the live session's true count from
  outside it, and a stdlib-only package has no tokenizer.

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

## outbox / pending-outward-action  · written by the orchestrator when a skill defers an outward action, cleared by the `release` consumer · *`.workflow/outbox/<id>.json`; RUNTIME, gitignored, single-writer (orchestrator), kept on a native filesystem; read by the bus to render the console's release panel; the mirror of the bus-owned `inbox/`*
The **transactional-outbox** queue behind the "never stalls — queue the outward action, one approval releases a
batch" rule. An outward action (`push`, `issue-create`, `issue-close`, later `deploy` / `send`) is **not** a
checkpoint — it doesn't park the ticket (the commit is local, the ticket completes, the loop advances). When the
skill's `config.outward` check (`schemas-config.md § config.json`) yields `ask`, it appends a record here and continues; a console `release`
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
  `config.outward` (`schemas-config.md § config.json`), the overridable human-approval layer. Standing pre-auth waives the human, never the
  checks.
- **No durable ledger:** single-user = author-is-approver → segregation-of-duties moot → the action's own external
  consequence (moved git ref / GitHub issue event / deploy record) is the audit; the away-run digest is the console
  activity feed + `handoff.md`, not a new artifact.

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
