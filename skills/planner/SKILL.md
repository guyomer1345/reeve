---
name: planner
description: Turn a settled spec or a backlog item into an executable plan. Two modes — decompose a whole project or heavy change into a phased roadmap, or plan a single item into a step-by-step plan file. Runs after discussion settles or when prioritize picks an item.
---

# Planner — spec/item → executable plan

Core principle: produce the plan others execute against; raise any real build decision rather than guessing.

## Modes
- **decompose** (new project / heavy change): `spec` → `roadmap` of phases, each with goal, deps,
  acceptance. Each phase becomes a backlog item with its own plan → execute → verify → document sub-loop, tagged
  `kind` (feature/debt) + `severity` so `prioritize` orders it by the same key as an `issue`.
- **plan-one** (a picked item): item + project knowledge graph → a `plan` (goal, files_touched, ordered
  verifiable steps, `acceptance_criteria` = the definition-of-done).

## Inputs
- decompose: the `spec`.
- plan-one: the picked backlog item + the project knowledge graph. **Optionally a `plan-delta`** (from
  `refine`) — when present, *amend* the item's existing `plan.md` per the delta rather than re-plan from scratch.

## Workflow
1. Read the `spec` (decompose) or the item + knowledge graph (plan-one).
2. Map purpose → concrete changes; list the files touched; write ordered, independently-verifiable steps.
3. Tag each `acceptance_criterion` `gate: artifact | human-qa` and **name its `discharge`** — the concrete
   mechanical check that settles an `artifact` criterion (a test ref, or `type`/`lint`/`structural`). If you
   cannot name a mechanical discharge, the criterion is **not artifact-checkable → tag it `human-qa`** (the
   classification is mechanical — *can you name a check?* — not a guess about perceptibility). Prefer *authoring
   a discharging test* to keep a criterion `artifact`: that keeps the loop autonomous. `human-qa` (→ qa
   `checkpoint`, or `handoff.parked[]` when unattended) is the fallback for the genuinely perceptual/runtime,
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

## Output
`roadmap` (decompose) → backlog · or `plan` (plan-one) → `execute`. In plan-one, `planner` `mkdir`s
`.workflow/items/<id>/` on demand and writes `plan.md` there — the first per-item artifact.

## Route
→ `execute` (plan-one) · → backlog / `prioritize` (decompose).

## Calls
`decision-engineer` (when an open decision blocks the plan).
