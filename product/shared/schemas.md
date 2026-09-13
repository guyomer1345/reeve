# Shared Artifact Schemas

The data formats that flow between capabilities. One source of truth — skills/agents reference these by
name. On-disk paths are fixed; each schema notes its **write-mode** (rewrite-in-place · append ·
new-record-supersede · create-per-item) and **tier** (see `shared/memory-model.md`). *Retention bounds (the
read law) live in `shared/memory-model.md`.*

<!-- doc-budget: detail split -> schemas-runtime.md -->
<!-- doc-budget: detail split -> schemas-bus.md -->
<!-- doc-budget: detail split -> schemas-loopstate.md -->

> **This file is one of FOUR parts, split by who the artifact belongs to.** It owns what the **build loop**
> produces and consumes — a spec, a plan, a changelog, a verdict, a receipt, a forecast, an issue. The three
> siblings own the other three belongings:
> - [`schemas-runtime.md`](schemas-runtime.md) — the records the package's own **processes** own, never authored
>   by a skill as work: `config.json` · `runtime.json` · `.workflow-runtime` · `install-set.json` ·
>   `orchestrator-brief managed block` · `statusline.delegate` · `bus.lock` · `orchestrator.lock` · `bus.json` ·
>   `remote_token` · `alerts.json` · `session-start warn-once markers`.
> - [`schemas-bus.md`](schemas-bus.md) — the records that cross the **console↔orchestrator boundary**, where the
>   other end is a human: `parked-ticket` · `inbox-message` · `conversation-thread` · `refine-ledger` ·
>   `demo-approvals` · `outbox / pending-outward-action` · `secret store`.
> - [`schemas-loopstate.md`](schemas-loopstate.md) — not artifacts at all, but **where the loop keeps its own
>   working set**: `state.json` · `handoff.md` · `per-item artifacts` (with `scratch` and the
>   `forecast ANCHOR TABLE`).
>
> Split — three times — when this file reached the **25 000-token Read ceiling** and could no longer be loaded in
> one call (`check_doc_budget.py`). All three siblings are **live**, not archives — those schemas are still edited
> there, which is why no marker above carries an `@ <sha>`.
>
> **A consumer that _parses_ these schemas must read all four parts**, and the markers are machine-followable
> for exactly that reason — read them through `check_doc_budget.read_with_splits`, as the contract linter and the
> meta-repo's enum gate do. Parsing the survivor alone reads strictly less than the schema declares, and the
> splits have made that progressively worse: the first cost two `kind:` values, the bus split took two more enums
> (`inbox.kind`, `inbox.control.op`), and after the loopstate split **not one** `kept on a native filesystem`
> claim remains in this file — all eleven now sit in the three siblings. Measured rather than assumed: with the
> pointers unfollowed, `check_enum_coherence.py` fails **closed** with 13 errors — two enum anchors it can no
> longer find, plus the *entire* `layout.pin` set reported as unclaimed. That it fails loudly is the only reason
> a split can't ship past the gate unnoticed; it is not a reason any reader may parse one part and stop.

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
- **Frontmatter** (structural, from `graph.json`): `path` · `type` · `lang` · `tier` · `centrality: { impact, orchestration, in_degree, out_degree }` (the two lenses + degrees) · `seeded_by` (e.g. `ingest`).
  - **`commitment` is NOT a node field.** The **`spec` element owns it** and is the only place it lives; every consumer (`align`, `commit`, `prioritize`, `document`) already resolves it there. A node field was declared here and had neither producer nor consumer — `graph.json` is structural and has no commitment to supply. Do not re-add it: a stale second copy would silently mis-route a *locked* contradiction as ordinary debt.
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

## commit-receipt  · produced by the non-item motion itself (`align` / `document:audit` / `doc-budget` / `update`) · *on disk at `.workflow/maintenance/<item-id>.json`; COMMITTED (it must ride the commit it describes), and self-collecting — each pass deletes any earlier receipt as it writes its own, so the directory holds one file and the history lives in its git log*
**The verify-free counterpart of `verify-verdict`, and the same kind of load-bearing on-disk contract.** Some
motions reach `commit` with no `planner`/`execute`/`verify` behind them — the three maintenance nodes, which run
their own pass and flow straight to `commit` (`loop.md` § Maintenance items), and the `/update` package refresh,
which is a bounded command motion rather than a loop node. None of them has a verdict, and the commit gate
cannot otherwise tell a legitimately verify-free commit from one whose verify was skipped. The receipt is how
the motion *says which one it is*.
- `item` — the motion's item id; **must equal the filename stem** · `kind: align|document:audit|doc-budget|update`
  — the motion that ran · `summary` — one line, human-readable.
- **`status: building` with no current item is a LEGAL state and never needs correcting.** The three statuses
  describe the loop's MODE, not item occupancy: at a scheduler boundary the loop is driving and has not yet
  picked, so `building` with a null item is the only honest pair — `idle` means *backlog empty, awaiting
  steering* and is not a synonym for it. **No commit may be obtained by editing `state.json`.** Flipping
  `status` to `idle`, committing and flipping back is the gate being OFF for the duration, with a window where a
  crash leaves the file lying about the loop's position, and it misreports the loop to the console while a wave
  is in flight. A motion that needs a commit takes a receipt.
- **The directory name is narrower than the set it holds**, and that is deliberate rather than overlooked: this
  is the maintenance receipt generalized, not a second mechanism, and relocating it would put a migration inside
  `/update` — the very motion that joining this set exists to unblock.
- **Consumer fails closed, exactly like the verdict's:** `verify_check.py` accepts the receipt only when it is
  **staged in the commit under review**, parses, and agrees with its own filename; anything else is not a receipt
  and the commit blocks with the reason named. An unstaged receipt exempts nothing — a marker sitting in the tree
  would be a standing exemption for every later commit.
- **Why this and not a `state.json` field:** the bootstrap escape (`phase: bootstrap`) is safe because it fires
  once and then disappears forever; maintenance recurs for the life of the project, so a volatile marker re-arms on
  every threshold hit and, left stale by a crashed pass, disarms the gate for the next **product-code** commit — the
  fail-open shape the gate exists to prevent. A marker carried in the commit cannot go stale.
- **Why not a trivial `pass: true` verdict:** `project_state.py` derives an item's `verified` from that first line,
  so a courtesy verdict would make the console report an item as verified that never ran `verify`. The anchors are
  evidence; an anchor that lies is worse than an absent one.
- **Not a forecast anchor** (§ the forecast ANCHOR TABLE) and deliberately so: maintenance items are *injected* by
  `prioritize`, never forecast, so an anchor for them would fire for a node no chain ever named — which that table
  reads as a **structural divergence** and would re-forecast the tail on every routine maintenance pass.

## directive  · written by a human (or by the orchestrator on their instruction), validated by `check_directives.py` · *`.workflow/directives.md`; **COMMITTED** and **ALWAYS-LOADED**, so it is budgeted in the always-loaded set and inside its TOTAL ceiling (§ commit-receipt's sibling law in `memory-model.md`); PROJECT-OWNED — `/start` seeds it and no update ever overwrites it*
**A standing operator instruction about how the LOOP behaves.** Neither `docs/decisions/` (build decisions,
append-only, on-demand — a directive the loop does not see every turn is not in force) nor `rules/**` (about
product CODE, each carrying an `— enforced by:` tag). Without this file such an instruction lives in the
conversation and dies at the next `/clear`, which is why it is re-typed every session.

**MECHANICAL-FIRST IS THE ENTRY RULE, and it is decidable rather than a matter of taste.** One question decides
the type: *does the directive name a condition a script could evaluate?* A threshold, a file state, an event —
then it is mechanizable, and it **is wired** as a hook, a `config.json` knob, a gate or a daemon term. Only a
directive with no observable trigger stays as text. Prose is the fallback, never the default: an always-loaded
file that accepts anything is unbounded growth in the most expensive place in the system.

- `type` ∈ `{ mechanized, behavioural }` · `entered` — `YYYY-MM-DD` · `retire` — see below ·
  `mechanism` — **required iff `type: mechanized`, forbidden otherwise**: the path or config key where the rule
  actually lives.
- **A `mechanized` entry states what it ACHIEVES and never restates the rule.** This is the second-copy hazard at
  its sharpest, on a file whose whole purpose is to be obeyed — a directive written once here as prose and once
  there as a hook gives the loop two masters that drift apart. The entry is an **index row**: a pointer, not a
  copy, which is exactly what the one-owner law permits and what a restatement violates. It
  is held to that mechanically — a `mechanized` body is capped at **one line**, and a one-line body cannot be a
  second copy of a hook's logic. The mechanism is also checked to EXIST; a dangling pointer is how an index rots.
- **Every entry carries a retire path, and none of them is "a human remembers":**
  - `on:YYYY-MM-DD` — expires. `check_directives.py` FAILS once the date has passed, so an expired directive
    stops the build rather than quietly staying in force.
  - `when:<path>` — retires when that mechanism exists. The gate fails once the path is present, which is what
    makes mechanical-first hold *over time* rather than only at entry: the prose is a placeholder that is
    forced out the day its hook lands.
  - `standing` — no expiry. Permitted, and deliberately the least convenient: standing entries are listed on
    every `--report` so they are re-confirmed rather than accumulated.
- **Why not `state.json` or `handoff.md`:** `handoff.md` is prose for a stranger, rewritten whole at every
  `/dispatch`, so nothing in it survives as an instruction; `state.json` is volatile and gitignored, and a
  standing instruction that does not survive a crash is not standing.

### the autonomy floor  · read by the orchestrator before taking a decision, computed by `check_autonomy_floor.py`
**The loop takes every decision that does not change the goal, and routes anything that may.** That criterion is
sharper than reversibility × blast-radius, which grades *how carefully to decide* rather than *whose decision it
is*, and it already has an owner: the spec's commitment model. *Goal-affecting* ≈ *would change a `locked`
element, or change what an acceptance criterion demands.*

**The judgment does not stand alone, because a loop grading its own decisions drifts toward "not fundamental" —
that is the direction that lets it keep working.** So there is a mechanical floor, and judgment may escalate
above it and never below it. The floor is computed from the **spec diff**:
- a changed hunk in `docs/spec.md` whose enclosing block carries a `locked` commitment marker;
- a hunk that removes or weakens a `locked` marker;
- a changed hunk inside an `acceptance_criteria` region — editing a criterion's text *is* altering what it demands.
Either condition ⇒ **auto-route to the human, regardless of the model's read.**

**Its limit is stated rather than implied, because a floor that is really a judgment in a gate's clothes is worse
than no floor.** This is a *spec-diff* floor: it catches a change that rewrites the goal **in the spec**. A code
change that quietly abandons a locked behaviour **without touching the spec** is not caught here — that is
`align`'s drift scan and `verify`'s conformance check, and it is exactly the case judgment is expected to
escalate on. The floor is a minimum, not a cap.

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

## dispatch-return  · produced by every DISPATCHED agent (`execute` · `document` · `create-demo` · `research` · `setup-guide`), consumed by the caller that dispatched it · *in-context only — never a file, never persisted; the heavy material it stands for is written to `scratch/` (§ per-item artifacts) and stays there*
**One contract for every dispatched worker, so the rule has one owner instead of five paraphrases that drift.**
Which nodes dispatch is not this file's call — the orchestrator brief's *How to run a node* owns that list, and
this covers exactly the agents it names. Each agent file points here; none restates it.

**A return is a CONDENSED RESULT PLUS POINTERS.** Paths, line anchors, ids, counts, the verdict, the blocker —
what the caller needs in order to *route*, and nothing it could re-read for itself. Never a whole file body,
never long raw tool output, never a transcript, never the diff. The caller carries this for the rest of the item,
so anything re-derivable from a path is rent charged on every turn after the dispatch.

**The worker's OWN window is the scarcer half, and it is the half that is easy to get backwards.** Measured on a
real drive: an `execute` dispatch runs ~66 turns and a worker's entire context is re-read on every one of them,
so a token it accumulates early is re-read **~41 times** and costs roughly **4.1× its base input** before the
dispatch ends — two thirds of everything a worker costs is those re-reads. The caller's window is a real
constraint too, but under a third of a drive's tokens. That puts the halves in their true order: **bounding the
return is second-order; keeping bulk out of the worker is first-order.** So "heavy reading happens in here and
stays here" is half the rule. Nothing a worker has read can be un-read:
- **Write heavy output; never print it.** A long draft, a generated file, a big report goes out through `Write`
  into `scratch/` and the tool result is a filename. The same bytes echoed into the transcript buy nothing and
  are then paid for on every remaining turn.
- **Redirect, then grep.** A command with large output is redirected into `scratch/` and searched, not run bare —
  raw stdout lands in the window permanently.
- **Read narrowly, and point at disk rather than re-carrying.** Grep for the anchor and read the range around it;
  once material is in `scratch/` it is addressable by path, and a second copy in the window is the same bytes at
  4.1×.

**What is enforced, and what is not — a judgement wearing a gate's clothes is worse than an honest advisory.**
This contract is **ADVISORY**: nothing stops a worker pasting a body back or loading one it did not need. One
half of it has a **detector** — `hooks/dispatch_return.py` sizes what came back and warns — and it cannot block,
is an absurdity ceiling rather than a budget, and cannot see the worker-window half at all. What it does, what it
deliberately ignores, and the gap it leaves: [`schemas-runtime.md § dispatch_return.py`](schemas-runtime.md).
