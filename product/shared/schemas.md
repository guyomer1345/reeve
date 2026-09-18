# Shared Artifact Schemas

The data formats that flow between capabilities. One source of truth — skills/agents reference these by
name. On-disk paths are fixed; each schema notes its **write-mode** (rewrite-in-place · append ·
new-record-supersede · create-per-item) and **tier** (see `shared/memory-model.md`). *Retention bounds (the
read law) live in `shared/memory-model.md`.*

<!-- doc-budget: detail split -> schemas-runtime.md -->
<!-- doc-budget: detail split -> schemas-config.md -->
<!-- doc-budget: detail split -> schemas-bus.md -->
<!-- doc-budget: detail split -> schemas-loopstate.md -->

> **This file is one of FIVE parts, split by who the artifact belongs to.** It owns what the **build loop**
> produces and consumes — a spec, a plan, a changelog, a verdict, a receipt, a forecast, an issue. The four
> siblings own the other four belongings:
> - [`schemas-config.md`](schemas-config.md) — the **operator's control surface**: every setting a human turns,
>   wherever it physically lives: `config.json` · `subagentPromptCacheTtl`.
> - [`schemas-runtime.md`](schemas-runtime.md) — the records the package's own **processes** own, never authored
>   by a skill as work and never hand-edited: `dispatch_return.py` · `runtime.json` · `.workflow-runtime` ·
>   `install-set.json` · `orchestrator-brief managed block` · `statusline.delegate` · `bus.lock` ·
>   `orchestrator.lock` · `wave-build slot` · `bus.json` · `remote_token` · `alerts.json` ·
>   `session-start warn-once markers`.
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

## goal  · derived from the `spec` by `planner` (decompose mode), read by `converge.py` · *`.workflow/goal.json`; **COMMITTED** (it outlives every item it is measured over, and a lost goal is a driver with no stop condition); rewrite-in-place — a new goal REPLACES it*
The record **above the item level** that an autonomous drive converges on. At most one is active: the
single-orchestrator run-constraint means a second would be a second thing to stop on.
**Two producers, one per bootstrap path, and both are required.** `planner:decompose` writes it for a
**greenfield** project from the roadmap it just emitted; the **reconcile checkpoint** writes it for a
**brownfield** one from the acceptance the human just confirmed — because the brownfield path never runs
decompose (`/start` → `ingest` → reconcile → `prioritize` → `plan-one`). Miss the second and a brownfield project
has no goal at all: `converge.py` reports *"nothing to converge on"*, nothing binds a `goal_ref`, and a driver's
`met`/`stalled` stops can never fire.
- `id` · `statement` — what the drive is for, in one line
- `created_sha` — the commit the acceptance set was derived against
- `status` ∈ `{ active, stopped }` — an **operator switch** (should a driver run against this goal), never a
  progress field. **`met` is deliberately NOT a value here:** it is derived by `converge.py` from the ledger, and
  a stored copy would be a second encoding of the one fact the driver stops on, and one fact never gets a second
  owner.
  Ask `converge.py met` (exit 0/1); never read doneness off this file.
- `acceptance[]` — `{ id, text, source }`, the enumerated definition-of-done. **This is the only place a goal's
  acceptance carries an `id`, and that is the whole reason the record exists.** `docs/spec.md` states acceptance
  as *prose* (`features[].acceptance_criteria` is a sentence), and a sentence has nothing a plan's criterion can
  be bound to. `source` points back at the spec element each entry was derived from.
- **The enumeration is a DERIVED copy, and its staleness already has an owner.** Re-derive when the spec's
  acceptance changes — which is not a new discipline to remember: *the autonomy floor already treats a changed
  hunk inside an `acceptance_criteria` region as goal-affecting* (§ the autonomy floor) and routes it to a human.
  That routing is the moment to re-derive, so the copy cannot drift silently past a gate that already exists.
- **A goal with an empty `acceptance[]` is never `met`**, rather than vacuously met — `converge.py` special-cases
  it, because "all zero of them are discharged" is the one shape that would stop a driver having built nothing.

## goal-ledger  · appended by `document` at promote time (via `converge.py record`), read by `converge.py` · *`.workflow/goal-ledger.jsonl`; **COMMITTED**, APPEND-ONLY, one line per promoted item*
- `{ goal, item, refs[] }` — the goal acceptance ids that item discharged; `refs: []` when it discharged none.
**Why a ledger exists in a repo that derives reality rather than recording it** (§ the forecast ANCHOR TABLE in
`schemas-loopstate.md`): because the artifacts it would derive from are *deleted*. `retention.py` prunes the item
dir — `promises.json` and `verify-verdict.md` with it — once `promoted.json` lands. This is not a parallel record
of live state; it is the **promoted form of an item's acceptance evidence**, written at the one moment
promote-then-prune already runs, by the node that already runs it. **While an item is open nothing is recorded
and everything is derived.** An entry is appended for **every** promoted item, including one that discharged
nothing — that is precisely what the stall streak counts.
**Deliberately NOT recorded: per-criterion pass/fail.** `verify` hard-fails an item when any `artifact`
criterion's discharge produced no signal, so a `pass: true` verdict *already entails* that every `artifact`
criterion of that plan discharged. A per-criterion outcome field would be a second encoding of what the verdict
token carries, and the two would eventually disagree.

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
- `base_sha` — the commit the plan was written against, stamped by `planner` in every mode. It is what makes a
  plan's **freshness decidable**: under plan-ahead a plan can sit unbuilt while siblings land, and
  `plan_freshness.py` asks whether anything in `files_touched[]` moved between this sha and `HEAD`. **Absent ⇒
  the plan is re-planned, not refreshed** — a plan that cannot say what it was planned against cannot be shown
  fresh, and guessing (the last commit touching `plan.md`, say) would infer a fact the producer is the only one
  who knows. Plans written before this field existed therefore re-plan once, which is the correct one-time cost.
- `refresh_count` — how many times `planner:refresh` has updated this plan in place; absent ⇒ `0`. The mechanical
  stand-in for "too stale to patch": at `config.run.wave.refresh_max` it re-plans instead. It counts **how often
  we have papered over the tree**, deliberately rather than measuring how far the tree moved — every distance
  metric (commits, files, elapsed time) is wrong in both directions, since a mechanical rename across forty files
  is trivially refreshable and one commit inverting a module's contract is fatal.
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
  **`goal_ref`** — optional; the `goal.acceptance[].id` this criterion discharges. It is the **binding that makes
  convergence acceptance-derived rather than effort-derived**: without it the only measurable thing is how many
  items closed, which is the measure a churning loop passes. `planner` binds it when a goal is active and the
  criterion genuinely settles that acceptance; **unbound is legitimate** (incidental criteria exist) and is never
  a gate — but a goal *acceptance* that no criterion anywhere binds is reported `unbound` by `converge.py`, which
  says the goal cannot be met as planned, and says it before the work is spent rather than after.
- `promises[]` — mirrors the impact-flagged `decision-record.promises[]` this plan implements; each promise's
  `test_ref` resolves to an `acceptance_criteria.id` here, and a `universal` promise's linked criterion must be
  **`boundary`-tagged** (one in-scope example can't discharge a "for-any" claim). `planner` writes these + the
  resolvable ids to `.workflow/items/<id>/promises.json`; the **promise-coverage gate**
  (`check_promise_coverage.py`, run by `checks.sh --check`) **blocks** an unlinked or non-boundary promise — the
  mechanical sibling of the decision-coverage gate. It proves *linkage*, not adequacy: a universal's adequacy
  rests on a property/structural test drawn from outside the enumeration (e.g. the code-map floor invariant).
  The same `promises.json` also carries the plan's `criteria[]` (`{ id, gate, discharge, boundary, goal_ref }`)
  — it is what `converge.py` reads for an OPEN item's bindings, and the only reason `goal_ref` is mirrored
  here rather than left in `plan.md`: the plan is prose and this is the machine-readable half. So
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

## commit-receipt  · produced by the non-item motion itself (`align` / `document:audit` / `doc-budget` / `update` / `planner:decompose`) · *on disk at `.workflow/maintenance/<item-id>.json`; COMMITTED (it must ride the commit it describes), and self-collecting — each pass deletes any earlier receipt as it writes its own, so the directory holds one file and the history lives in its git log*
**The verify-free counterpart of `verify-verdict`, and the same kind of load-bearing on-disk contract.** Some
motions reach `commit` with no `planner`/`execute`/`verify` behind them — the three maintenance nodes, which run
their own pass and flow straight to `commit` (`loop.md` § Maintenance items), and the `/update` package refresh,
which is a bounded command motion rather than a loop node, and **greenfield inception** — `planner:decompose`
mints `.workflow/goal.json` and the backlog before any item exists. None of them has a verdict, and the commit gate
cannot otherwise tell a legitimately verify-free commit from one whose verify was skipped. The receipt is how
the motion *says which one it is*.
- `item` — the motion's item id; **must equal the filename stem** · `kind: align|document:audit|doc-budget|update|planner:decompose`
  — the motion that ran · `summary` — one line, human-readable.
- **Inception is in the set because it is NOT bootstrap.** `phase: bootstrap` ends when the spec lands; decompose
  runs after it, and may run much later still (a drive that skipped the node and had it demanded back). The
  escape that fires once and disappears cannot cover a motion that can recur, so inception takes a receipt like
  every other non-item motion. The **orchestrator** stages it, not `planner`: the agent returns a roadmap, the
  router is what materialises `backlog.md` and reaches `commit`. Use an id naming the motion, e.g.
  `decompose-<goal-id>`. **Brownfield needs none** — there the goal is minted at `ingest`, inside bootstrap.
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
> **Consulted at decision time, ENFORCED at commit time (2026-09-13).** `loop.md` asks the orchestrator to run
> this before acting on a goal-affecting decision — which is a consultation, and *a loop that simply does not run
> it is precisely the case the floor exists for*. `checks.sh --check` now runs it as a gate, with
> `spec_approval.py`'s receipt as the escape: a change that crosses the floor commits only when a human approved
> **this exact spec content**. The receipt is bound to a **digest**, not a label, so approving one version and
> committing another blocks again — see `schemas-runtime.md § spec-approval.json`.
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
**A spec the change CREATES is clear, and says so** (`created: true`): every rule asks what the change does to
an *existing* demand, and a criterion that did not exist has none. The first spec always arrives through a
capability that already gates on a human — `discuss`'s requirements conversation, `ingest`'s `reconcile`
checkpoint — so routing it stops the human for a decision they just made. Failures to *compute* are untouched
by this: a created spec that also trips path drift still routes.

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

## checkpoint  → **moved to [`schemas-bus.md`](schemas-bus.md)** (2026-09-13)
Re-homed on **belonging**, not size: `schemas-bus.md`'s rule is that *the other end of each record is a human
at the console*, and a checkpoint is the loop stopping to ask one. It also dissolves the cross-half reference the
original split created — `parked-ticket` lives there and **embeds** `checkpoint: {kind, request, …}`, so the two
halves of one exchange were in two files. `forecast` deliberately did **not** move with it: it is rendered in a
console panel, but its other end is the loop walking the chain, and a view is not a boundary.

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

## dispatch-return  · produced by every DISPATCHED agent (`planner` · `execute` · `document` · `create-demo` · `research` · `setup-guide`), consumed by the caller that dispatched it · *in-context only — never a file, never persisted; the heavy material it stands for is written to `scratch/` (§ per-item artifacts) and stays there*
**One contract for every dispatched worker, so the rule has one owner instead of five paraphrases that drift.**
Which nodes dispatch is not this file's call — the orchestrator brief's *How to run a node* owns that list, and
this covers exactly the agents it names. Each agent file points here; none restates it.

**THE RETURN IS TYPED. Line 1 is `status: done|continue|question|blocked`**, and the rest is the condensed
result. One token the caller can route on, in a fixed place, because the alternative — the caller reading prose
to work out what just happened — is the thing that made every rule below advisory. What each status owes:
- **`done`** — the work is finished. `summary`: one line. The condensed result follows.
- **`continue`** — the worker stopped **because of its window, not its judgement**. It owes `resume:` — the
  `scratch/` path holding everything a successor needs. **The caller re-dispatches the SAME node** with that
  path; it does not re-plan and it does not treat this as a failure. This is the status that makes a worker's
  context bound real: a subagent cannot spawn its own successor, so it yields and the orchestrator — which can —
  starts a fresh one. `hooks/worker_budget.py` is what tells a worker it is time (§ `worker_budget.py` in
  `schemas-runtime.md`).
- **`question`** — an undecided option the worker must not guess. It owes `question:` — the one thing to decide
  and the options it saw. The caller routes it (`decision-engineer`, or a human); the worker never resolves it.
- **`blocked`** — a plan assumption turned out untrue, or something needed is missing. It owes `blocker:` —
  what is untrue or absent. The caller routes to `refine`/`debug`.
`question` and `blocked` are not new behaviour: `execute` and `planner` already stop dead on exactly these two
rather than improvising. What is new is that they arrive as a **token rather than a paragraph**, so the caller
routes them the same way every time.

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
- **`setup-guide` is EXEMPT from the scratch half, and the exemption is stated because the contract above names
  it.** Its `tools:` line is `WebSearch, WebFetch, Read` — no write tool of any kind — so it **cannot** park a
  fetched page and must carry everything it reads in its own window. A contract that named an agent which could
  not satisfy it would be a rule with a silent exception, which is worse than a rule with a stated one. **Its only
  lever is to read narrowly:** fetch the page that answers the step, not the section around it, and never fetch
  speculatively. The return bound still applies in full — that half needs no write access.
- **Redirect, then grep.** A command with large output is redirected into `scratch/` and searched, not run bare —
  raw stdout lands in the window permanently.
- **Read narrowly, and point at disk rather than re-carrying.** Grep for the anchor and read the range around it;
  once material is in `scratch/` it is addressable by path, and a second copy in the window is the same bytes at
  4.1×.

**What is enforced, and what is not — a judgement wearing a gate's clothes is worse than an honest advisory.**
Three different answers, and they are worth separating because this contract used to give one:
- **The `status` line is ROUTED, which is stronger than enforced.** A return that omits it is not blocked, it is
  *unusable*: the caller has nothing to route on and says so. `hooks/dispatch_return.py` marks the omission in
  the caller's transcript at the moment it happens.
- **The worker's own window now has an ACTUATOR**, where it previously had only a measurement.
  `hooks/worker_budget.py` runs inside the worker, reads that worker's own transcript occupancy, and past a
  threshold tells it to wrap up and return `continue`. The orchestrator re-dispatches. This is the half that was
  called impossible on the reasoning that a subagent cannot spawn its own successor — true, and beside the point:
  it does not have to, it only has to **yield**.
- **The SIZE of a return is still ADVISORY, and that is the honest word for it.** Nothing can truncate a payload
  that has already landed; `dispatch_return.py` sizes it and warns, an absurdity ceiling rather than a budget.
  The typed envelope reduces the pressure on this half rather than enforcing it — a schema is a smaller thing to
  fill than a blank page — but a worker that pastes a file body into `summary:` is still only *noticed*.
What each hook does, what it deliberately ignores, and the gaps they leave:
[`schemas-runtime.md § dispatch_return.py`](schemas-runtime.md) · [`§ worker_budget.py`](schemas-runtime.md).
