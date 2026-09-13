---
name: planner
description: Turn a settled spec or a backlog item into an executable plan. Three modes — decompose a whole project or heavy change into a phased roadmap, plan a single item into a step-by-step plan file, or refresh an existing plan whose tree has moved under it. Runs after discussion settles, when prioritize picks an item, and before a wave dispatches a plan that is no longer fresh.
---

# Planner — spec/item → executable plan

Core principle: produce the plan others execute against; raise any real build decision rather than guessing.

## Modes
- **decompose** (new project / heavy change): `spec` → `roadmap` of phases, each with goal, deps,
  acceptance. Each phase becomes a backlog item with its own plan → execute → verify → document sub-loop, tagged
  `kind` (feature/debt) + `severity` so `prioritize` orders it by the same key as an `issue`.
- **plan-one** (a picked item): item + project knowledge graph → a `plan` (goal, files_touched, ordered
  verifiable steps, `acceptance_criteria` = the definition-of-done).
- **refresh** (an existing plan the tree has moved under): re-point a plan at the current tree **in place**,
  keeping its reasoning. Exists because plan-ahead lets a plan sit unbuilt while sibling waves land, and
  `execute` is built to stop dead on an untrue assumption rather than improvise — so a stale plan does not
  produce a wrong build, it produces a **dead dispatch**. Dispatched by the wave coordinator for every plan
  `plan_freshness.py` calls `suspect`, and **only for those**: a `fresh` plan is spent as written.

**Every mode stamps `base_sha`** — the commit the plan now stands on — because a plan that cannot say what it
was planned against is re-planned rather than refreshed. **`refresh` also increments `refresh_count`.** A
`refine` amendment does neither of those things to the counter: a `plan-delta` is *new intent* arriving, not a
patch over drift, so it restamps `base_sha` and leaves the count alone. One counter, one meaning.

## Inputs
- decompose: the `spec`.
- plan-one: the picked backlog item + the project knowledge graph. **Optionally a `plan-delta`** (from
  `refine`) — when present, *amend* the item's existing `plan.md` per the delta rather than re-plan from scratch.
  **Optionally a wave manifest** — the other items being planned in the same wave (see step 9).
- refresh: the existing `plan.md` + the diff from its `base_sha` to `HEAD` (`git diff <base_sha>..HEAD`) + the
  knowledge graph.

## Workflow
1. Read the `spec` (decompose) or the item + knowledge graph (plan-one).
2. Map purpose → concrete changes; list the files touched; write ordered, independently-verifiable steps.
3. Tag each `acceptance_criterion` `gate: artifact | human-qa` and **name its `discharge`** — the concrete
   mechanical check that settles an `artifact` criterion (a test ref, or `type`/`lint`/`structural`). If you
   cannot name a mechanical discharge, the criterion is **not artifact-checkable → tag it `human-qa`** (the
   classification is mechanical — *can you name a check?* — not a guess about perceptibility). Prefer *authoring
   a discharging test* to keep a criterion `artifact`: that keeps the loop autonomous. `human-qa` (→ qa
   `checkpoint`, which parks and mirrors onto `handoff.md` when unattended) is the fallback for the genuinely perceptual/runtime,
   and it is what later triggers the checkpoint. Default to `artifact` **with** a real discharge — never a bare
   `artifact` tag.
4. **Set `risk_class`** (`code-only` · `data-additive` · `data-destructive` · `prod-touching`). When it is
   destructive, author the required **`backup`** block (`what / mechanism / verification / restore`) —
   `execute` verifies it before the destructive step and refuses the plan without it.
5. **Decision-coverage gate:** list every governing decision in `plan.decisions[]` and confirm each maps to
   ≥1 step. Write the `{ id, steps }` mapping into `.workflow/items/<id>/promises.json` (`decisions[]`);
   `check_decision_coverage.py` (in `checks.sh --check`) **blocks** an unmapped decision mechanically — resolved
   intent must not silently evaporate between the decision and execution.
6. **Promise-coverage gate (impact-scoped):** for each impact-flagged decision, map every
   `decision-record.promises[]` entry to an `acceptance_criterion` (its `test_ref`). A `universal` promise's
   criterion must be **`boundary`-tagged** — a case drawn from *outside* the implementation's own enumerated
   set, because one in-scope example can't discharge a "for-any" claim (a floor is only a floor at the edge it
   must cover; prefer a property/structural check over the complement of the build's enumeration). Write the
   resolved links + criterion ids **and the `criteria[]` (`{ id, gate, discharge }`)** to
   `.workflow/items/<id>/promises.json`; `check_promise_coverage.py` **blocks** an unlinked or non-boundary
   promise and `check_criterion_discharge.py` **blocks** a discharge-less `artifact` criterion (both in
   `checks.sh --check`). Reversible tier-0 decisions carry no promises → nothing to map. These gates prove
   *linkage/presence*, not adequacy — the boundary/property test is what makes the discharge real.
7. Raise any genuine build decision to `decision-engineer` rather than guessing (e.g. a `TBD → stack`
   pointer left by `discuss`).
8. **Setup gate:** when an item builds a `spec.integrations[]` entry (auth / payments / …), mark it so the
   loop inserts a `setup` `checkpoint` for the manual external steps (it calls `setup-guide`) — the integration's
   headline path, otherwise orphaned.

9. **Wave manifest (plan-one, when one is supplied).** It lists the other items being planned in this same
   wave — ids, titles, dependencies. It is a **tiebreaker and nothing more**: *if two approaches are genuinely
   equivalent on the merits, prefer the one that stays clear of what a peer will obviously touch; if they are
   not equivalent, take the better one and declare the overlap.* **Separability is a constraint, never a goal**
   — a plan that picks a worse design to win a dispatch slot has been corrupted by the scheduler, and the burden
   of proof is always on fanning out rather than on staying serial. Never shorten `files_touched` to look
   separable: it is a **safety input** the independence gate trusts completely, and `verify` treats a real diff
   exceeding it as a hard finding. A deliberate overlap you declare is useful signal, not noise — it usually
   means two backlog items are one item, or that one belongs behind the other.
10. **refresh mode.** Read the diff, then answer one question: *does the plan's approach still hold, or only its
   details?* Update `files_touched`, steps and any criteria the move invalidated; re-run gates 5 and 6, because a
   changed scope can orphan a decision or a promise. Then **restamp `base_sha` to `HEAD` and increment
   `refresh_count`.**
   - **Return `cannot refresh` whenever the premise moved, not just the details, and whenever you are unsure.**
     Patching steps over a dead premise yields a plan that looks fine and is wrong — strictly worse than a stale
     one, because staleness is detectable and a quietly-patched plan is not. The caller re-plans from scratch;
     that is cheap next to a doomed dispatch, so the bar for `cannot refresh` is deliberately low.
   - The mechanical tripwires (deleted declared file · missing `base_sha` · `refresh_count` at
     `config.run.wave.refresh_max`) are already handled upstream — those plans never reach this mode.

## Output
`roadmap` (decompose) → backlog · or `plan` (plan-one) → `execute`. In plan-one, `planner` `mkdir`s
`.workflow/items/<id>/` on demand and writes `plan.md` there — the first per-item artifact.

## Route
→ `execute` (plan-one) · → `create-demo` (plan-one, when the per-item sandbox gate fires) · → backlog /
`prioritize` (decompose) · → the wave coordinator (refresh: `refreshed`, which re-runs
`check_wave_independence.py` on the batch, or `cannot refresh`, which sends the item back through plan-one).

## Calls
`decision-engineer` (when an open decision blocks the plan).
