---
name: charter
description: Run the founding conversation before any build — purpose, users, comparable products, direction, and what must never be true — and land what the human settles as FALSIFIABLE `locked` constraints in the spec. Once per project: greenfield straight after `/start`, brownfield after the `reconcile` checkpoint (reconstruction cannot see what is not there). Human-led and deliberately unbounded; this is the conversation that BUYS the loop's autonomy, because the autonomy floor can only hold what this produces. With no human in the conversation it writes nothing and parks a `steer`.
---

# Charter — the founding conversation → the constraints the build lives inside

Core principle: the human sets **direction and constraints**; from here on `decision-engineer` chooses
**within** them. A decision that would break a charter constraint is product-changing and comes back.

## Why this exists, and why it is not `discuss`
`discuss` refuses this job by design — *"requirements only, never decide the tech stack or any engineering
choice here"* — so architecture, comparable products and the shape of the use cases were either deferred to
`decision-engineer` one decision at a time, with no vision behind them, or never had at all. The separation is
load-bearing and stays; what was missing is the conversation that comes BEFORE it.

**This is the item that earns "don't wake me", not a nicety before it.** The autonomy floor routes a change to
a `locked` element or an acceptance criterion back to the human. A thin inception leaves it **nothing to
hold**, so every architectural question the build hits is either guessed or escalated — and the human who
asked not to be woken is woken for things he is not better at answering than `research` is.

## When
Once per project, and it is the **only** node that may write the charter block.
- **greenfield** — immediately after `/start`, **before** `discuss`. What is settled here bounds every field
  `discuss` then fills.
- **brownfield** — after the `reconcile` checkpoint, never instead of it. Reconcile derives from CODE and asks
  *"is this what it is?"*; this derives from the HUMAN and asks *"what must be true going forward?"* Opposite
  directions, and only one of them can produce a constraint: **reconstruction cannot see what is not there.**
  *"No cloud"* is invisible in a codebase that simply never added one, and every exclusion — every "I would
  never accept that" — is unreachable from artifacts. Brownfield is missing this MORE invisibly than
  greenfield, because `reconcile` makes it feel as though the conversation already happened.
- **Re-run only on a stated change of direction.** It is not a refresh: a charter that is re-derived every so
  often is not a commitment.

## Inputs
The human (conversation) · `spec` if one exists (brownfield: the reconstructed one the human just confirmed).

## Workflow
1. **Purpose.** What is this, who is it for, and what changes for them. Drive to one sentence the human will
   sign; a purpose nobody can state in a sentence produces constraints nobody can test.
2. **Use cases.** The two or three journeys that matter, end to end. Not a feature list — features are
   `discuss`'s, and a charter that drifts into them has stopped constraining anything.
3. **Comparable products.** **Dispatch `research`** for what exists, what those products get right and wrong,
   and where market practice actually sits; bring back the distillate, not the notes. This is the step that
   makes the conversation worth having rather than a form to fill in: the human's opinion of a real product is
   the fastest route to a real constraint.
4. **Direction.** The shape — where it runs, who it must work for, what it must interoperate with, what it
   must keep working without. **Record a stack or a library ONLY where the human states it firmly**; anything
   he does not state is left as `TBD → decision-engineer`, now bounded by what step 5 produces. Do not decide
   it here and do not let the conversation become one: this capability's product is the boundary, not the
   choice inside it.
5. **Exclusions.** *"I would never accept…"* Ask for them explicitly, because they are the half no artifact
   and no reconstruction will ever surface, and they are usually the sharpest constraints in the charter.
6. **THE FALSIFIABILITY PASS — the step this capability exists for.** Every candidate constraint faces one
   question: **could `align` or a reviewer DEMONSTRATE a violation?** If not, it is a slogan, and a slogan
   buys nothing — rewrite it or drop it.
   - ✗ *"local-first"* → ✓ *"no runtime dependency on a network service for core reading and writing"*
   - ✗ *"fast"* → ✓ *"a cold start renders the first screen with no network round-trip"*
   - ✗ *"privacy-respecting"* → ✓ *"no user content leaves the device except through an action the user
     initiated in that session"*
   Read each one back to the human before it lands. A constraint he does not recognise is one the floor will
   later wake him about for no reason.
7. **Emit.** Write the charter block into `docs/spec.md` (Output below), then route.

## Rules
- **Everything tagged `locked` must be something the human SAID in this conversation.** `locked` records that
  an approval happened; it is not a confidence level. Here the human's own statement IS the approving event —
  that is what makes this capability able to write it at all, and it is exactly why nothing else may.
- **With no human in the conversation, write NOTHING** and park a `steer` asking for the founding
  conversation. An unattended session cannot manufacture a commitment, and a forged `locked` marker breaks the
  one signal `check_autonomy_floor.py` carries. Do not fall back to `provisional` "to make progress": an
  unfounded constraint is worse than a missing one, because the floor will defend it.
- **Never a feature list, never a plan, never a stack decision the human did not make.** Those are `discuss`,
  `planner` and `decision-engineer`; a charter that does their work has no authority behind it.
- **No constraint that cannot be demonstrated false.** See step 6; this is the whole product.
- **Its enforcement strength is stated, not implied.** The floor is a *spec-diff* floor: a constraint is
  protected from being **edited away**, not from being **ignored**. Ignoring it is `align`'s semantic pass,
  which is budget-bounded and scoped to the changed surface — so the honest strength is *"align finds it
  eventually"*, the same limit every `locked` behaviour already carries. Say so when the human asks what a
  constraint guarantees.

## Output
A **`## Charter`** section in the `spec` (`<project_root>/docs/spec.md`), commitment-tagged per element like
every other spec element:
- `purpose` — the one sentence · `users` · `use_cases[]` — the two or three journeys
- `comparables[]` — `{ product, what_it_gets_right, what_it_gets_wrong }`, from `research`
- `constraints[]` — `{ text, falsifier }` — **`locked`**, and `falsifier` is the observation that would prove
  it broken. A constraint with no falsifier does not get written.
- `exclusions[]` — same shape; a constraint stated in the negative is still a constraint.
- open engineering questions as `TBD → decision-engineer`, each naming the constraints that bound it.

## Route
→ **greenfield:** `discuss` (which fills the rest of the spec **inside** these constraints).
→ **brownfield:** `prioritize` (the loop picks up; the spec already exists and now has a charter over it).
→ no human in the conversation: `checkpoint` (`kind: steer`) — the founding conversation needs a person, and
this is the one node that cannot proceed without one.

## Calls
`research` — comparable products and market practice (step 3), dispatched, never driven inline.
`create-issue` (kind=debt) — for a direction question the human explicitly defers.
