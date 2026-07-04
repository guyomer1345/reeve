---
name: decision-engineer
description: Resolve an open build decision — tech stack, library, architecture — by gathering the options and current market practice and weighing them against the project's spec, returning a confidence-scored verdict. The Arbiter; invoked by planner (or anything) when it hits a decision it must not guess.
---

# Decision-engineer — resolve an open build decision

Core principle: an `adjudicate` specialization (views = {option A, option B, …, market practice}; domain =
engineering choices) — the deciding end of the gather-then-judge pattern.

## When
An open decision blocks planning — a `TBD → decision-engineer` pointer in the `spec`, or a blocker raised
by `planner` / `execute`.

## Inputs
The open decision + the constraints from the `spec` (audience, runtime, scale, integrations) + the code-map
**impact flag** for the nodes it touches (a high-blast-radius touch → triggers the promise-elicitation pass in
step 4; absent it, the decision is treated as reversible tier-0).

## Workflow
1. Frame the decision and the spec constraints.
2. Dispatch `research` to gather options + current best practice for this and similar products.
3. Weigh options × market practice × our spec → best fit, with a confidence score.
4. **Promise elicitation (impact-flagged decisions only** — the impact lens marks a high-blast touch, or the
   decision is a design's raison d'être; reversible tier-0 calls skip it). Run an **adversarial pass distinct
   from the framing above** — *"what does this design promise that isn't written?"* — so it doesn't inherit the
   author's blind spot (an unwritten promise is the one that ships untested). Drive it from two author-independent
   signals: the **archetype checklist** (universality/tail-coverage · idempotence · preservation/no-data-loss ·
   monotonicity · graceful-degradation · isolation · backward-compat — "does the design touch this? then state
   the invariant") and the decision's own **purpose vocabulary** ("floor" ⇒ covers-the-tail; "cache" ⇒
   correctness == source-of-truth; "migration" ⇒ preserves-existing-state). Record each surviving promise with a
   `falsifier` (the input that would break it — a promise with no interesting falsifier is a knob-restatement,
   dropped, so the field can't fill with vacuous pass-the-gate text). Record each promise's `test_ref` as
   **unbound (`null`)** — the acceptance-criterion that discharges it doesn't exist until `planner`; `planner`
   binds it when it writes that criterion (the promise-coverage gate runs there, not here).
5. confidence ≥ threshold → emit a `decision-record`; else gather more / escalate to the human.

## Output
`decision-record` `{ id, status: active, question, options, chosen, why, confidence, sources, promises[] }`
(`promises[]` only on impact-flagged decisions; each promise's `test_ref` is unbound until `planner`), plus its
**active row** in
`docs/decisions/index.md` (`| <id> | <title> | active | - |` — the 4-column format retention later flips to a
tombstone on supersede). The spec's `TBD` flips to `locked`.

## Route
→ back to the caller (`planner` / `execute`) with the decision resolved.

## Calls
`research`.
