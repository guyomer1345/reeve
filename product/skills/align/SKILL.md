---
name: align
description: Periodic reconciliation of the spec, decisions, and promises against the actual code — scoped to what changed, classified by commitment, routed as ordinary tickets. Two layers — a cheap decidable pass that always runs whole, and an expensive semantic pass scoped to the changed surface and budget-bounded so it never halts production. Knowledge-gated (uses the code map for blast-radius). Run after a merge or phase boundary, or on demand — never every commit.
---

# Align — reconcile intent vs code, at scale

Core principle: **detection is the backstop, not the gate.** The per-commit teeth are the mechanical gates on
the commit hook; `align` is the *periodic* wider sweep. It has two layers with opposite scaling, and conflating
them is the trap:

- **Mechanical layer — always runs whole.** The package's own wiring (routing graph, skill I/O, schema enums,
  promise/decision coverage) is *fixed-size* — it does not grow with the product. Linting it is milliseconds, so
  it is never scoped. A finding here is a **fact** (the graph is decidably broken), so it can hard-block.
- **Semantic layer — scoped + budget-bounded.** Spec↔code alignment grows with the product. This pass is the
  one that must be scoped to the changed surface and capped, or a large repo gets re-audited whole and
  production halts. Reserve model judgment for what a script cannot decide.

## When
- After a **big change** — a merge, a completed phase/wave, or N commits since the last scan (the drift
  threshold `prioritize` trips on; **decoupled** from the retention threshold — memory pressure ≠ drift risk).
- **On demand** — the maintainer asks.
- **Not every commit.** The per-commit teeth are the mechanical gates (`checks.sh --check` + the commit hook).

## Inputs
- The **last-scan anchor** (`.workflow/align/anchor.json`: `base_sha`, `describes_sha` (org mode only — see
  *Org mode* below), the carried findings register, and
  `cleared_demo_items[]` — item ids the approved-demo lens has already read and found clean). The cleared set is
  there because the register dedups **findings**, and a clean read produces none: without it, every item that passes
  is re-read on every scan forever, which is a budget leak in the one pass that is budget-bounded.
- **`.workflow/demo-approvals.json`** — the promoted refine ledgers. An item listed here is settled mechanically;
  an item with a terminal demo approval and **no** entry is the only kind the approved-demo lens must read.
- `git diff <base_sha>..HEAD` — the changed surface (the semantic layer's scope; the mechanical layer ignores it).
- The **code map** (`docs/knowledge/graph.json`) — expands the changed files into their blast-radius (impact
  lens) and maps them to the decisions / skills / schema contracts they touch. **This is the index that makes
  the semantic pass cheap on a large repo — it reads the graph, not the tree.**
- The `spec` (commitment tags), the decision records (+ their promises), the routing graph, the schemas.

## Workflow
1. **Scope the semantic surface — build a work-list, never the whole project.** Diff since the anchor; expand
   via the impact lens to the affected nodes; map those to the governing decisions, skills, and schema
   contracts. Order by blast-radius. *This bounded work-list is the only thing the semantic pass looks at.*
   (The mechanical layer, step 2, is not scoped by this — it runs whole.)
   - **One admission the diff cannot make: the approved-demo backlog.** Also add every item with a **terminal demo
     approval** that has no entry in `demo-approvals.json` and is not in the anchor's `cleared_demo_items[]`. These
     are history, not change — an item approved two years ago has no diff since the anchor, so a diff-scoped
     work-list can never reach the very items the approved-demo lens exists for. Scope is decided here, so the
     exception belongs here rather than as a lens quietly reading outside its own work-list. The set is finite and
     shrinks: every promoted item and every cleared item leaves it permanently.
2. **Mechanical layer (free, decidable, always whole).** Run the decidable checks:
   - the **contract linter** (`.claude/scripts/check_contracts.py`) — the routing graph is real structured
     data, so its consistency is a fact: every routing target resolves; every `node:mode` a skill invokes is
     routed; every skill is a node or a declared side-door; commitment/kind tags stay in their schema enum.
     The graph it lints is **`.workflow/loop.md`** — the copy the orchestrator actually routes from, not the
     package template — while the skills and `schemas.md` it lints against are **never installed**; they stay
     under the plugin root. So the plugin root is passed explicitly, and its absence **degrades to the
     graph-only half** rather than failing the layer (the script says which checks it skipped):
     ```bash
     P="${CLAUDE_PLUGIN_ROOT}"
     if [ -d "$P/skills" ]; then
       python3 .claude/scripts/check_contracts.py \
         --skills-dir "$P/skills" --schemas "$P/shared/schemas.md"
     else
       python3 .claude/scripts/check_contracts.py
     fi
     ```
   - the **coverage gates** — promise-, criterion-, and decision-coverage (`check_promise_coverage.py`,
     `check_criterion_discharge.py`, `check_decision_coverage.py`); the same ones `checks.sh --check` runs.
   These are the gates the package **installs** (see `MANIFEST.json`) and that mean something in a product repo.
   Decidable → a finding is a *fact*, not a suspicion. Hard-graph breaks block; auto-fixable drift → fix + log;
   anything needing judgment → step 3, never auto-resolved. *(Honest ceiling: the linter settles only what the
   graph structure makes decidable — schema producer/consumer mismatches and spec↔code alignment are NOT
   decidable from prose and belong to step 3, not here.)*
3. **Scoped semantic pass (bounded fan-out).** For each affected decision/contract on the work-list, dispatch
   **one finder** (a ground-truth read of the decision + its implementing files) to check: (a) **spec↔code
   alignment, classified by commitment** — a *locked* contradiction is drift, *provisional* is a finalize
   signal, *unspecified* is steering; (b) **promise adequacy** — re-derive the decision's negative/tail class
   *blind to the code* and diff it against what the code actually exercises; (c) **over-delivery** — behaviour
   that traces to no promise. Three lenses are baked in as standing checks: the **status-ownership** lens (one
   owner per fact-domain; a second copy is drift), the **promise↔plan mirror** lens (every
   `decision-record.promises[]` has a matching `plan.promises[]`), and the **approved-demo** lens (below).
   Stop dispatching at the budget cap (Rules).
   - **The approved-demo lens — the one thing here with no artifact left to compare against.** Approving a demo
     is terminal, and it **deletes the bundle**. So a change the human agreed to during a refine round that was
     never written back into the `spec` is destroyed at the exact moment it is approved, leaving a locked spec
     that is confidently missing it. The `refine-ledger` refuses a round that did not move the spec, and
     `--promote` copies its summary into `demo-approvals.json` before the delete — so an item **listed there is
     already settled** and never reaches this lens. What reaches it is step 1's admitted backlog: items approved
     before that floor existed, which carry no promoted entry and never will. For each, read the item's `spec`
     slice against its own checkpoint request, verdict `notes`, and commit history, and flag any agreed change the
     spec does not carry. **A read, not a gate** — there is nothing left to diff, so it can only ever be judgment;
     a hit leaves as an ordinary ticket at the spec element's `commitment`. A **clean** read is recorded in the
     anchor's `cleared_demo_items[]` (step 5), which is what makes this converge: an absent finding is not
     something the register can dedup, so without the cleared set the same item is re-read on every scan forever.
4. **Judgment verification — principle-class only.** Each finder tags its findings `decidable | judgment`.
   Decidable/contract findings are already settled by the read. **Only judgment findings** go to a small
   **2-vote skeptic panel** — two *orthogonal* lenses, **occurrence** (can this actually happen?) and
   **materiality** (does it matter if it does?); a finding **dies on ≥1 solid refutation** (precision-biased —
   a periodic scan that cries wolf gets muted, and a miss is re-caught next scan). Contract facts never enter
   the panel — that is the lever that keeps the scan affordable.
5. **Register + route.** Merge into the findings register (dedup against the carried one), rank by severity ×
   blast-radius, classify `principle | skill | gap`. Route: mechanical → auto-fix or ticket; semantic →
   `create-issue` (severity from the affected element's commitment) → `prioritize` → the normal loop. **Never
   auto-resolve an authority call.** Write the new anchor + a one-screen summary (scoped / found / deferred).
   The anchor also gains **`cleared_demo_items[]`** — every approved-demo item read clean this scan, appended to the
   carried set. Only a *clean* read clears an item: one that produced a finding stays in the backlog until the
   finding is resolved, because the ticket, not the scan, is what closes it.

## Rules
- **Budget-bounded, with honest truncation.** A hard cap on semantic fan-out agents (`config.align.max_agents`,
  small default). Cover highest-blast-radius surface first; if the work-list exceeds the budget, **log exactly
  what was deferred** — a silent cap reads as "all clear." Deferred surface rides the next scan.
- **Scoped, never whole (semantic layer).** Only the changed surface + its blast-radius. A full cold audit of
  the whole project is a **separate, explicit, one-off mode** (heavier orchestration allowed there) — not the
  periodic path. *(The mechanical layer is exempt: it is fixed-size, so it always runs whole.)*
- **Ground-truth-first.** A decidable/contract finding is adjudicated by *reading the file*, never by a model
  panel. The panel is reserved for judgment.
- **Knowledge-gated, degrades gracefully.** Uses the code map for blast-radius; if the map is thin (generic
  floor / a new stack), fall back to git-diff + directory scope — reduced precision, **never a halt.**
- **Detection, not authority.** The scan proposes; it never rewrites the spec or a decision inline. A locked
  contradiction routes as a high-severity ticket; the loop/maintainer resolves it.

## Org mode — a second anchor, not a second skill
In org mode the tree is a private clone of a product the operator does not own, so drift arrives from a
direction the ordinary scan cannot see: **other people push to the upstream.** That is still drift, and it is
still this skill — it needs one more anchor and one more diff base, and **nothing else**. If you find yourself
writing new machinery here, stop: this is `align` with a different base.

- **`describes_sha`** — the upstream commit the current knowledge *describes*. Stamped into `anchor.json` at the
  end of every org-mode scan, alongside `base_sha`. The two answer different questions and neither substitutes
  for the other: `base_sha` is "how far have **we** moved", `describes_sha` is "how far has **the product**
  moved underneath us".
- **Fetch read-only, then compare.** `git fetch` (never pull, never merge — the clone has no push path and must
  gain no automatic write path either), then `git rev-list --count <describes_sha>..FETCH_HEAD`. Non-zero is
  coworker drift.
- **Scope is the union**, and both halves must be in it: `git diff <base_sha>..HEAD` (our own work, the ordinary
  case) ∪ `git diff <describes_sha>..FETCH_HEAD` (theirs). A coworker's push is then just the ordinary drift
  case with a bigger diff — already budget-capped and already honestly truncated, so it needs no new policy.
- **A non-trivial upstream conflict is the HUMAN's, always.** If their changes and ours touch the same surface,
  raise a `checkpoint` and stop — never an autonomous merge, never a rebase. Detection is not resolution, and
  the human is applying the bundle into their own checkout anyway, which is where a real conflict has to be
  settled. Recording it as a finding and moving on would be the failure mode: it reads as handled.
- **Stamp last, and only on a completed scan.** A scan that halted or was truncated must leave `describes_sha`
  where it was — stamping it early would silently mark unread upstream commits as read, which is the one error
  this anchor exists to make impossible. **Absent `describes_sha`** (the first org scan) → treat the whole
  upstream as undescribed and scope from the clone's own merge-base, rather than skipping the upstream half.

## Output
The updated findings register + the routed tickets + the new scan anchor (`.workflow/align/anchor.json`, carrying
`describes_sha` in org mode), and a one-screen summary of what was scoped, found, and deferred.

## Route
→ `commit` (the mechanical auto-fixes + the new anchor). Each *semantic* finding leaves as a `create-issue`
ticket (the side-door) → `prioritize`. Injected by `prioritize` on the drift threshold; see `loop.md`
§ Maintenance items.

## Calls
`create-issue` — one per surviving semantic finding. `research` — only when a finding needs external context
(e.g. "is this a known issue?"). The finders are the fan-out; they are leaf reads and never spawn further agents.
