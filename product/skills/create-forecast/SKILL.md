---
name: create-forecast
description: Show the human the chain of events the loop proposes to walk for a change — before it walks it — so they can question it, correct it, and answer its human gates up front. Use on a big change, at intake, before create-demo. Skip for small or well-trodden work; the forecast gate below decides.
---

# Create-forecast — the chain of events, before the machine walks it

Core principle: a **prediction over the existing routing graph**, surfaced as a checkpoint, that de-risks the
**process** question ("did we agree *how* the machine will proceed?") — the exact sibling of `create-demo`, which
de-risks the **product** question ("did we agree *what* to build?"). It forecasts the territory from the map; it
never does the work.

**It is not a second routing graph.** Every event names a real `loop.md` node, and
`check_contracts.py --forecast` refuses one that does not. There is one routing owner and this is a *reading* of
it — which is also what makes the forecast lintable at all.

## When — the forecast gate
Forecast only if the change scores high on **at least two** of these three axes:
1. **Blast radius** — it touches several subsystems, or a surface other work depends on.
2. **Reversibility** — undoing it later is expensive (a schema/data migration, an external integration, a public
   contract) rather than a `git revert`.
3. **Ambiguity** — the route itself is genuinely uncertain: it may need a decision the project has not recorded,
   a credential nobody has yet, or a human judgement mid-way.

Default = **no forecast**. A small, well-trodden item does not get one; the loop just runs. This gate is stated
here and evaluated by whoever routes past it — the same shape as `create-demo`'s sandbox gate. *(A general
proportional-rigor triage on `planner` output could later subsume this gate, but could not host it: that triage
fires after planning, and the forecast is a pre-plan checkpoint whose FIRST predicted event **is** planning.)*

Also forecast whenever the human **asks** (`/create-forecast`) — an explicit request never has to pass the gate.

**Where it sits: BEFORE `create-demo`, at intake.** A forecast placed after the demo cannot predict the demo
checkpoint, which is one of the very gates it exists to front-load — and the forecast is cheap while the demo is
expensive.

## Inputs
The **indices**, never a code read: `.workflow/loop.md` (the routing graph), the `spec` (its `integrations[]`,
its open `TBD`s, its commitment tags), `docs/knowledge/graph.json` (blast radius), and the change as asked for.

## Workflow
1. **Walk the graph from the entry node and apply the loop's OWN trigger rules — without firing them.** That is
   what makes this smart yet cheap: it predicts the trigger, it does not resolve it.
   - `planner` will declare a `human-qa` criterion → predict a **qa** checkpoint;
   - the `spec` names an `integrations[]` entry with no credential in the store → predict a **setup** checkpoint,
     and name the key in that event's `gate.prefill.secrets[]`;
   - the sandbox gate's conditions hold → predict a **demo** checkpoint;
   - a decision the change depends on has no recorded answer → predict `decision-engineer` (→ `research`).
2. **Branch only where the HUMAN would do something different** — pre-supply a credential, pick between two
   integration paths, decide a qa is worth their time. `verify → succeeds | fails: debug` is stated once as
   "this step self-corrects"; it is **never** unrolled into every verify→debug→refine cycle. Unrolling redraws
   `loop.md` per item and drowns the one signal a human is here to give.
3. **State the horizon.** Say which event the chain stops being able to see past, and say plainly that the tail
   is unforeseeable — execute-discovered needs are unforecastable by definition. `forecast.py` **refuses a
   record with no `horizon`**: a chain that does not mark its own blind spot reads as a complete plan, and a
   silent cap reads as "all clear".
4. **Write `.workflow/forecasts/<id>.json`** per `shared/schemas.md § forecast`. It is **committed** — so it
   carries credential **key NAMES only, never values**, exactly like `config.json`'s `secrets_required[]`.
5. **Lint it before you park it — both halves, they check different things:**
   ```bash
   python3 .claude/scripts/check_contracts.py --forecast .workflow/forecasts/<id>.json \
     --loop .workflow/loop.md          # graph facts: every event names a real node
   python3 .claude/scripts/forecast.py lint .workflow/forecasts/<id>.json
                                       # lifecycle facts: shape, horizon, names-only
   ```
   A failure names the file and the problem — **fix and regenerate**, never park a forecast that fails either.
6. **Surface it via `checkpoint` (kind=forecast).** The parked record carries
   **`checkpoint.forecast_id`** — a *pointer*, never the chain (the `demo_id` pattern). The chain itself rides
   the `request` so the card can show what is being asked, and the committed record is what the console's
   **Forecast chains** panel reads. It has to be this way round: `unpark` removes the parked record at the
   instant of approval, which is exactly when the forecast is supposed to be *frozen*.
   - **The pre-fill rides the card.** For each predicted `setup`, put a `request.tasks[]` entry naming the
     credential in `secrets[]` — the console renders a labelled input per key. **Filled → the secret store.
     Blank → simply not front-loaded**, and the ordinary within-plan ask stands unchanged. Blankness IS the
     vocabulary for "ask me at the gate"; there is no `defer` outcome and none is needed.
   - **What is front-loaded is the ELICITATION, never the VERIFICATION.** A key handed over forty minutes early
     can still be the wrong key, so the machine-verify probe still runs at the step that needs it.
7. **On the verdict** (applied at the scheduler boundary, not here):
   - **approve** → `python3 .claude/scripts/forecast.py freeze .workflow/forecasts/<id>.json`, **before**
     `bus.py unpark`. Freezing stamps `frozen_at` and a digest of the chain, which is what makes the freeze real
     rather than a label — the frozen chain is the anchor reality is measured against for the life of the change.
     Any `returns` on the verdict is written to `.workflow/secrets/` on the setup path's usual terms.
   - **changes** → regenerate the chain with the human's corrections (step 1) and re-park. The record stays
     `draft`; only approval freezes.
   - **reject** → `discuss`. The forecast record stays for the life of the change, as the record of what was
     rejected.

## Afterwards — reality is DERIVED, and a surprise re-forecasts
Once frozen, the chain is what reality is measured against. The console's **Forecast chains** panel renders a
state beside each event, and nothing writes it: each `loop.md` node is resolved through the durable artifact it
produces (`schemas.md § the forecast ANCHOR TABLE`). There is no second ledger and no writer to forget.
```bash
python3 .claude/scripts/forecast.py reality .workflow/forecasts/<id>.json --workflow-dir .workflow
```
- Four states, and the fourth is the honest one: **done** · **open** (a checkpoint is parked and waiting on the
  human) · **pending** (it has an anchor and it has not fired) · **unknown** (the node has *no* anchor — the
  column says it cannot tell, and never that the step did not happen).
- **A structural divergence re-forecasts.** An anchor that fired for a node the chain never named means the loop
  took a turn nobody saw coming. It does not silently continue: re-forecast the remaining tail and re-show it.
  The check runs at the **scheduler boundary only** (`loop.md` § Scheduler boundary) — never mid-item, which is
  what keeps non-preemption and never-stall intact.
- **Re-forecasting the tail writes a fresh draft over the same `<id>.json`** — status back to `draft`,
  `frozen_at`/`events_sha256` dropped, and it parks a new `forecast` checkpoint. It is a **supersede, not an
  edit**: never patch a frozen chain in place, which fails the lint precisely because the result would no longer
  be the thing the human approved. The superseded chain is not lost — the record is committed, so **the previous
  frozen version is in git**, which is the project's own memory law rather than a second retention rule.

## Rules
- **A prediction, not a contract.** What is binding about an approved forecast is not the sequence — it is the
  **corrections made while reviewing it** (which land as ordinary spec edits and decision records) and the human
  gates it front-loads. A deviation is a *divergence event*, which `execute` already has the vocabulary for, not
  a failure.
- **Never resolve what you predict.** Predicting a `decision-engineer` step does not run one. Predicting a setup
  does not create a `setup` checkpoint — spawning a real one for an *optional* ask would deadlock the change on a
  question the human is allowed to ignore, and then re-alert on it every `reminder_hours` forever.
- **Committed, so names only.** No credential value, no token, no `value` field, ever. `forecast.py lint`
  enforces this; it is an invariant, not a promise.
- **Loopback-only.** An approved forecast is an execution plan the agent follows, so its verdict never rides the
  reduced remote surface — the bus refuses it on the remote socket by kind, whatever the body carries.
- **One per change**, keyed on the change/item id.

## Output
A committed `.workflow/forecasts/<id>.json` and an open `checkpoint` (kind=forecast). On approval, that record
frozen.

## Route
→ `create-demo?` (the sandbox gate, next at intake) · → `planner:decompose` when no demo · → `discuss` on
reject. `changes` loops back here.

## Calls
`checkpoint` (kind=forecast).
