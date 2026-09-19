# Loop — the long-form detail

The on-demand half of the routing graph. [`loop.md`](loop.md) holds what the
orchestrator needs **every turn** — the routing table, the side doors and the boundary order — and is
budgeted as an always-loaded doc (`doc_budget.always_hard`, and its share of `always_total_hard`). This file holds the parts that are read
**when the situation arises**: the per-kind drain semantics, the context gate, the forecast divergence
check, the one-time stack-wiring transition, and the maintenance-item contract. Each has a one-line pointer
from `loop.md`.

Split out of `loop.md` when that file crossed its always-loaded hard budget, per the split-and-pointer
convention in [`memory-model.md`](../shared/memory-model.md). `loop.md § <name>` for any section below resolves
here — the name is the anchor, and the two files are one document.

## the boundary drain, by kind
The order itself is in `loop.md`. What each kind *does*, and the **anchor** that makes a repeat a no-op:

- **verdict** — resumes the parked ticket whose `token` matches; an unknown or already-closed token →
  dead-letter and surface it. The ticket is then closed with `bus.py unpark --id <ticket_id>`, which removes
  the record and re-projects `handoff.md`'s parked block. *Anchor:* the token itself (already closed →
  no-op) — and "closed" means the record is gone, which is why `unpark` is the step that makes the anchor real.
- **intake** — promoted into `backlog.md` through triage, stamped with the source message id. *Anchor:* that
  stamp (an item already carrying the id is already promoted → skip).
- **control** — reprioritize / pause / resume, honored here only (non-preemptive; never mid-item). The ops split
  by **who can be trusted to apply them**, the same line this drain is built on (§ `drain.py`: apply is judgment,
  bookkeeping is arithmetic). `reprioritize` is **judgment** — which item matters more is not a function of the
  inputs — and stays yours. `pause`/`resume` are a **flag**, so `drain.py record` latches them mechanically into
  the runtime `control.json`; you do not have to remember a pause, and **must not** treat having read one as
  having honoured it. *Anchor:* for `pause`/`resume`, the latch itself (`drain.py paused`, exit 0 ⇒ paused); for
  `reprioritize`, none possible — which is why every op here must still be idempotent under redelivery.
  **Why the latch exists at all:** a pause used to live only in the reading session's head, so it expired at that
  session's exit — precisely when an unattended driver decides whether to start another one, and precisely when a
  human who paused expects it to hold.
- **release** — fires the named `outbox/` entries through `guard.sh`. *Anchor:* the entry's status (already
  fired → skip).
- **question** — run `answer`: reply from this project's own record and append the turn to
  `.workflow/thread/thread.json`. *Anchor:* that turn's source message id (a reply already carrying it →
  skip). **Last, and it advances nothing** — a question is a read, so it never delays a parked resume or a
  promotion, and it must never be promoted into the backlog on its own.

### recording what you applied
`python3 .claude/scripts/drain.py record --applied <id> [<id>...] [--dead-letter <id>="why"]`

Record each id **as soon as** its apply succeeds, **not** in one batch at the end. A crash between applying
and recording re-applies that message on restart, so the window should be as small as you can make it. Each
kind's effect is *also* idempotent, via the anchors above — that is what covers the window you cannot close.

`record` recomputes the watermark, prunes the consumed-set and republishes `handoff.md` durably. **It owns
the machine block in that file** — never hand-write, hand-edit or delete that block. The prose around it is
yours to rewrite freely.

### a returned credential never passes through the orchestrator
If `list` marks a message `sensitive`, **do not open the file.** Run
`python3 .claude/scripts/drain.py secret --id <id>`: it moves the value into the secret store, unlinks the
message and records it, without the value ever reaching a context window or a log. This is also the **one**
exception to "the consumer never deletes an inbox file" — a credential must not sit waiting on a janitor.

**The drain is split, and the split is the point.** *Which* messages are new, in what order they apply, what
the watermark is now, and what may be pruned are all a pure function of the inbox and `handoff.md` — that
half is `drain.py`'s (`list` → apply → `record`), and it is not re-derived by hand. *Applying* a message is
judgment — which ticket a verdict resumes, whether an ask is worth promoting and at what priority, how a
rejection routes — and that half stays with the orchestrator. `record` recomputes `consumed_through` (the
low-watermark: every message at or below it is consumed, so the bus may collect it) and **prunes the
consumed-set to ids above it**, which is what keeps `handoff.md` bounded — a cold start reads that file whole.


## the context gate
`python3 .claude/scripts/context_band.py --gate --json` at the scheduler boundary. It returns the band
(`hold` / `handoff-at-boundary` / `handoff-now`) plus the two things the band alone never said:

- **`needs_handoff`** — the band says `handoff-now` and `handoff.md` has not moved since it started saying so.
  This is **yours**: rewrite the anchor, then say plainly that a `/clear` is safe and that the cleared session
  needs a bare `continue` — it does not start on its own.
- **`clear_safe`** — the anchor is written, nothing is waiting on a human, **and the session is idle**: no
  parked checkpoint (`parked_open == 0`), **no open dialog** (`awaiting_input` is null — a permission prompt is
  waiting on a person just as much as a checkpoint is, and a live probe found a session sitting in one), and
  **`session_idle` is non-null**. That fourth condition is the one the other three were wrong about: the anchor
  is written *during* a turn, so all three went true while the model was still working, and every reset was
  sent into a running turn. Keys sent then are not queued into it — they land in the prompt box as text and are
  never submitted. This is not for you; it is what the supervisor reads before resetting the session, and
  `blocked_by` says why not.
  **The supervisor** is `loop.sh --supervise` (inside tmux): it polls this gate and sends `/clear` then
  `continue` — two sends, because a cleared session does not start on its own. It never writes the anchor, and
  after three sends that leave the context reading untouched it stops rather than filling the prompt box.

**Why both, when the old rule was one flag.** Writing an anchor is always safe, so nothing may veto it — not an
open checkpoint, not an unreachable runtime root, which is exactly when the anchor matters most. *Resetting* a
session is not always safe. Conflating them either withholds the anchor or clears the screen a person was
mid-conversation with.

**A `Stop` hook enforces the `handoff-now` half.** `hooks/handoff_gate.py` blocks the turn from ending until the
anchor exists. It is a **backstop, not the path**: it fires mid-turn, wherever you happen to be, while a
boundary handoff is written at a clean seam and is both cheaper and truer. Meet it here and it never fires. It
gives up after two demands rather than wedging the session, and says so when it does — a turn that can never end
costs more than an unwritten anchor.

**`handoff-at-boundary` is this boundary.** Finish the drain, write the anchor, stop picking. The hook does not
fire on it, by design: that verdict means there is still runway, and interrupting a turn to spend it would
defeat the floor half of the band.

**The band is derived, and `context.json` is its only input** — published by the status line, which is the one
surface Claude Code exposes a token count to. A session with no status line configured gets `unknown`, and
`unknown` never reads as `hold`.

## the dispatch boundary
`loop.md` carries the rule. This is how the batch is actually formed, and why the failure direction is what it is.

**Form the batch, then dispatch it once.** Concurrency in this harness exists **only** for work dispatched in the
same turn — while a `Task` is in flight the orchestrator is blocked on its result and cannot interleave. So there
is no such thing as "using the wait": the lever is *not waiting alone in the first place*. Judged **at the
boundary, never per turn** — the answer only changes at a boundary, and re-deciding it every turn spends the
router's window (the scarcest thing in a drive) to re-derive a constant.

**Two kinds of member, neither subordinate to the other.**
- **Homogeneous — N `execute` items at once.** When several items' work genuinely does not overlap, running their
  `execute` calls concurrently is the plain intended use and the largest throughput win available. It is not a
  by-product of the rule below and must not be treated as one: the first question at a boundary is *how many
  independent items can run right now*, and the answer is allowed to be several.
- **Heterogeneous — never wait alone.** Before dispatching anything blocking, establish that there is genuinely
  nothing else worth doing, and put what there is in the same batch: research a **queued** item will need, a plan
  already unblocked. **`Viable` means the backlog already implies it** — not invented exploration. Unbounded
  speculative work is its own defect: it spends on output that may be discarded *and* pollutes the knowledge base
  with findings nobody asked for.

**Eligibility, and why it fails towards serial.** `check_wave_independence.py` decides, on the retained predicate:
**dependency-ready ∧ file-disjoint ∧ ¬1-hop code-map neighbour**. It reports, per rejected candidate, which clause
rejected it and against which other member — enough to act on without re-deriving it. A candidate whose
independence cannot be *proven* — no plan, no `files_touched`, no code map, an unparseable entry — is **not
eligible** and runs serially. **The burden of proof is on fanning out, never on staying serial:** a wrong "serial"
costs wall-clock, a wrong "parallel" costs correctness, and those are not comparable. Note this is narrower than
the predicate's original grading, which admitted a near-miss as a *flagged* start with raised integration rigor —
that concession made sense when the candidate would run **later**, and does not when it runs **concurrently**.

**The wave sequence, and why refresh sits where it does.** A wave is *plan-N-then-execute-M*, because the
independence predicate reads `files_touched` from a plan and a backlog row has none until it is picked — so
planning has to run ahead of dispatch for there to be anything to prove disjoint. Order:

1. `prioritize` emits the **plan batch**: the head of the queue, up to `config.run.wave.plan_max`.
2. **Plan the batch — dispatched, in one turn.** `planner` is a leaf agent for exactly this reason: an open
   build decision comes back to you as a **blocker** to route rather than being resolved by a spawn, and that
   is what lets several planners run at once. They are deliberately blind to each other — each writes only its
   own item directory, so they cannot collide, and where two claim the same source file the independence gate
   catches it in step 3. Coordinating them would make a wave plan differently depending on who finished first,
   which cannot be reproduced or reviewed. Hand each one the **wave manifest** — the other members' ids, titles and
   dependencies — which is a *tiebreaker only*: equivalent approaches prefer to stay out of each other's way,
   non-equivalent ones take the better design and declare the overlap. Never let a plan narrow `files_touched`
   to look separable; `verify` treats a wave diff outside the declaration as a hard finding.
3. **Run `check_wave_independence.py`.** It classifies plan freshness *itself* — a caller cannot switch that off
   by forgetting a flag — and reads a stale plan **pessimistically**, at two code-map hops rather than one.
   Widening can only hold an item back, never admit one, so the wave can be chosen before anything is refreshed.
4. **Refresh only the batch.** Every member the report marks `REFRESH FIRST` goes through `planner:refresh`;
   `cannot refresh` sends it back through `planner:plan-one`. **Do not refresh candidates the gate declined** —
   the batch you are about to dispatch will land on them and undo the work. The gate proves the batch disjoint
   from *itself*, not from what it left behind.
5. **Re-run the gate on the batch alone** (pass the ids). A refreshed plan's real scope can have grown into a
   co-member; the re-run is a script call and costs nothing next to discovering it in a merge.
6. **Mint and record the wave id** before dispatching: `wave_build.py mint <ids…>` → `state.json`'s `wave`.
   Clear it back to `null` when the batch drains.

A plan is durable, so the members that did not make the batch are **not wasted** — they keep their plans and
walk into the next wave already eligible. Only the first wave pays full price.

**A held item that says `held ONLY by pessimistic widening` is a real signal, not noise.** Widening is
deliberately over-cautious, and an item in a churning area can be pushed out wave after wave. Force a refresh on
it (or dispatch it serially) rather than letting it starve invisibly.

**The rule is enforced, and here is exactly how far.** `--record` publishes the verdict to
`.workflow/wave-decision.json`, and `hooks/dispatch_guard.py` (`PreToolUse`) **refuses a `reeve:execute`** when:
there is no record · it was made at another `HEAD` (a commit per item is the boundary's cadence, so that is the
staleness test rather than a TTL) · this item is not among `considered` · or the record puts it in a batch of
N>1 and `state.json.wave` is null, i.e. it is going alone while the gate said N could run together.
**What that cannot prove, stated rather than left to be found:** a `PreToolUse` hook fires once per tool call and
cannot see the call's siblings, so minting a batch of three and then dispatching one is the residual. Scope is
narrow on purpose too — `execute` is the blocking dispatch the rule is about and the only one the gate grades;
`document`, `create-demo`, `research` and `setup-guide` block too and are **not** covered, because no gate
computes what may run beside them and inventing one would be new judgement rather than a check.

**Build once per wave.** The authoritative gate (`checks.sh --check`, the one a commit depends on) runs **once per
wave**, not once per member — N workers each triggering it collide on shared build state, caches, ports and
fixtures. That is distinct from a worker validating its own work inside its own worktree, which is legitimate and
may happen many times.

**Interleaving is the degenerate case, not a separate feature.** While an item is parked on a human verdict, the
next *independent* item starts rather than the loop idling — the same predicate, the same boundary, a batch of one.
A whole-loop park is simply "nothing eligible". Non-preemptive and item-level throughout: the human is still the
only thing that preempts.

## the return envelope, and what `continue` means
`loop.md` carries the four statuses and their targets. This is the part that is easy to get wrong.

**`continue` is not a failure, and treating it as one throws away the point.** It says the worker ran out of
*window*, not out of *judgement*: the plan is still good, the work so far is real, and everything a successor
needs is already written to the `scratch/` path the return names. So the move is to **re-dispatch the same node**
with that path — not to re-plan, not to route to `refine`, not to file a blocker, and above all not to start the
item again. A drive that re-plans on `continue` will re-plan forever on any item too big for one window, which is
exactly the item this exists for.

**Where it comes from.** `hooks/worker_budget.py` runs inside the worker, reads that worker's own transcript
occupancy, and past a threshold tells it to wrap up and yield. That is the whole mechanism for bounding a
worker's context, and it works by *yielding* rather than by a subagent spawning its successor — which it cannot
do, and does not need to. The hook **advises**: a worker that ignores it runs to its real limit and dies the way
it always did. What changed is that the yield point is reachable.

**`question` and `blocked` are not new behaviour.** `execute` and `planner` already stop dead rather than guess
at an undecided option, a missing fact, or a plan assumption that turned out untrue. What the envelope adds is
that they arrive as a **token in a fixed place** instead of a paragraph the router has to interpret — so the same
situation routes the same way every time, which it demonstrably did not before.

**An untyped return is UNROUTABLE, not merely untidy.** `hooks/dispatch_return.py` marks a return with no
`status:` line in the caller's transcript. It cannot block — the payload has already landed — so the useful move
when you see it is to decide which of the four it actually was *before* acting on it, and to say in the prompt
that line 1 carries the status if you re-dispatch for that item.

## forecast divergence check
If the item being picked has a frozen `.workflow/forecasts/<id>.json`, run it **before starting work**:
```bash
python3 .claude/scripts/forecast.py reality .workflow/forecasts/<id>.json \
  --workflow-dir .workflow --check
```
A non-zero exit means the loop reached a node the approved chain never predicted — a **structural**
divergence. Do not walk on: re-run `create-forecast` for the remaining tail and re-show it, so the human is
re-consulted on a route they never agreed to. Reality is **derived** from the anchor table
(`schemas.md § the forecast ANCHOR TABLE`), so there is nothing to record and nothing to keep in step.

**This fires at the boundary ONLY, never mid-item** — that is what keeps `prioritize`'s non-preemption and
the never-stall rule intact, and it is why it is plain control-flow rather than a routing edge in the table.
A divergence found mid-item is not lost; it is picked up at the next boundary, which is the first moment the
loop is allowed to change its mind anyway.

## stack-wiring at tech_stack lock
A greenfield project starts with an empty product tree, so `/start` cannot detect a stack and writes only the
**coverage-only** `checks.env` + the unspecialized `rules/` baseline. The stack is chosen later, by
`decision-engineer` resolving the spec's `tech_stack` (a `TBD → decision-engineer` pointer). **The moment that
resolution flips `tech_stack` to `locked` while `.workflow/checks.env` still wires no stack gate, run the
stack-wiring step** (the stack-dependent half of `/start` step 6) before the next `execute`:
- fill `.workflow/checks.env` with the concrete `FMT_CHECK`/`LINT`/`TYPECHECK`/`TEST` (+ `FMT_FIX`/`LINT_FIX`)
  commands for the chosen stack, **scoped to `project_root`**;
- specialize each `rules/` `— enforced by:` tag to the concrete tool, and wire the enforcers (formatter,
  linter, typechecker, test runner, CI) — gap-fill, never clobber;
- add the stack's build-output paths to `.gitignore`; regenerate the code map.

This is a **one-time transition** (stack `unspecified/TBD → locked`), not a per-item step — it is the
orchestrator's to run, so the leaf skills stay in their lane. It is a positive fast-path: `checks.sh --check`
**fails the commit closed** whenever source exists under `project_root` with no stack gate wired, so skipping
this step cannot silently disarm the gate — it stops the loop loudly until the stack is wired.

**Skip this entirely when `checks.env` sets `STACK_GATE_NONE`** — a tree whose code must never be executed
here is *declared*, not unwired, and is already transitioned. Wiring commands into it re-arms `eval` on
foreign code; the runner refuses them and reports the conflict, so the attempt is noise, not a fix.

## maintenance items
`prioritize` injects a **maintenance item** on a threshold (§ `prioritize`): a *retention/size* threshold →
`document:audit` (bound the append-only tier); a *drift* threshold → `align` (reconcile spec/decisions/promises
vs code); a *doc-size* advisory → `doc-budget` (trim or split-and-pointer a context-loaded doc that has grown
past its role's budget — the hard tier is already enforced on the commit gate, so only advisories arrive here).
A maintenance item is **self-contained**: it runs its own pass and flows straight to `commit` — there is no
`planner`/`execute`/`verify`, because there is no product-code change to plan and no runtime behaviour to
verify — then `close-issue?` (skip: no linked issue) → `prioritize`. `align`'s *semantic* findings leave as
ordinary `create-issue` tickets (the side-door) and ride the normal queue; only its mechanical auto-fixes + the
new scan anchor ride this commit. The three thresholds are **decoupled** — memory pressure ≠ drift risk ≠ doc
size, and one shared threshold would make each of them fire for another's reason.

**Inception is the one non-maintenance node that lands here.** `planner:decompose` mints `.workflow/goal.json`
and the backlog before any item exists, so it has no verdict either and routes `→ commit` on the same contract.
Two things differ. **The orchestrator stages the receipt, not `planner`** — the agent is a leaf that returns a
roadmap; the router is what materialises `backlog.md` and reaches `commit`. And the **id names the motion**, not
an injected item: use `decompose-<goal-id>` (e.g. `decompose-GOAL-001`), `kind: planner:decompose`, summary one
line. Commit `goal.json`, `backlog.md` and the `handoff.md` rewrite together — that commit is what makes the
drive's stop condition durable, and it must not be left to ride a later feature commit. **Brownfield needs no
receipt here:** there the goal is minted at `ingest`, inside `phase: bootstrap`, which is already exempt.

**No verify means no verdict — and from outside, a verify-free item and a *skipped* verify look identical.** So
the pass **stages a receipt in its own commit**: `.workflow/maintenance/<item-id>.json`
(`{ item, kind, summary }`, `kind` = the maintenance node that ran). That receipt is what the commit gate
accepts in place of a verdict; without it a maintenance item has **no legal commit at all**. It writes its own
and **deletes any earlier one**, so the directory holds only the current commit's receipt and the history of
past maintenance is that directory's git log. Never fake a trivial `pass: true` verdict instead — the console
reads that first line as "verify passed" (`shared/schemas.md § commit-receipt`).

## the review gate — when the cold reader runs, and what its verdict means
`verify` passes, and then one question is still unasked: **is the code right?** Every `verify` check is a
*correspondence* check (plan↔changelog↔diff, criteria↔discharge, promises↔criteria), so a change can satisfy
all of them and be logically wrong — `debug` is on-fail only and `align` is periodic, so that change reaches
`commit` unread. `review` is the leaf agent that reads it cold.

**The gate is decidable, and it is the diff.** Dispatch `review` when the item's diff changed **code under
`project_root`**. Skip it when the item changed only documentation, the spec, or records — there is no logic to
be wrong. A maintenance item never reaches this tail at all. It runs **before** `checkpoint:qa?`: nobody should
be asked to exercise a build a machine reader would have rejected.

**It is an AGENT and not a skill, and that is the mechanism rather than a filing choice.** The orchestrator
watched the plan get written and the worker carry it out, so it reads the diff through the author's intent and
cannot see what a stranger sees. A dispatch is the only cheap way to buy a reader who never watched. For the
same reason `review` is told **not** to read `changelog.md` (the author's own account, written to say the work
was done) or `verify-verdict.md` (a `pass` already recorded) — either one re-warms the context the dispatch was
paid to cool.

**Route on the report's first line** (`gating: true|false`, `shared/schemas.md § review-report`). `false` →
`checkpoint:qa?` → `document`; advisory findings ride the report and gate nothing, and a recurring one belongs
in `create-issue`. `true` → `refine` **directly**, not via `debug`: the demonstration bar means the finding
already names its cause, so `debug` would re-derive it. A corrected item re-enters `review` after `verify`
passes, **capped at `config.review.max_rounds`** (default 2, lower than `demo`'s 3 because a review round
re-runs plan→execute→verify on real code while a demo round regenerates a sandbox). At the cap, escalate to a
`checkpoint` carrying every round's report — never auto-proceed.

**No commit gate reads the report**, unlike `verify-verdict`, and that is deliberate while the node is young: a
hard gate on an unproven reviewer makes the expensive thing compulsory, which selects for avoidance. The
anchor makes the node visible to the forecast and divergence machinery; making it compulsory is a separate
decision that wants its own evidence — a measured false-positive rate first.

## the turn gate
**The two complaints this answers happen at the same instant, which is why one gate answers both:** the loop
*"pauses a lot for no reason ... sometimes its really minor decisions that have no reason to stop and wait for
my intervence, sometimes it says 'okay now doing X' and never dispatches X"*, and the report it leaves behind is
long, jumbled, and full of ids that mean nothing to the reader. Both land at the end of a turn, and the end of a
turn is decidable. `hooks/turn_gate.py` (`Stop`) runs the ladder in `scripts/turn_check.py`; ask it yourself at
any time with `python3 .claude/scripts/turn_check.py`.

**Rung 1 — may this turn end at all?** Only for a reason from a closed, mechanical set: something is **parked**
· the goal is **met** or **stalled** (`converge.py`, the same verdict the driver stops on) · the loop is
**paused** (`control.json`) · the loop is **`idle`** — backlog empty, awaiting steering · `state.json` does not
say `building`, so nothing is in flight to abandon. None of those and the block tells you *which shape* it is,
because they send you to different places: a turn that **moved no anchor** announced an action and did not take
it; a turn that **moved anchors and stopped anyway** finished a piece and quit instead of picking up the next.
The four ways out are in the block itself — continue the loop · resolve it (`decision-engineer` for a build
decision, `refine` for a false plan assumption) · **park** it if it genuinely belongs to a person · or stop
properly, which means `state.json` says `idle` or `converge.py` says met.

**Rung 2 — is the anchor an anchor?** `handoff.md` exists but names no `base_sha`, so a session picking this
project up cannot run `git log <base_sha>..HEAD`. Fix the field; do not rewrite the file.

**Rung 3 — was the work dispatched, and is there a goal to dispatch it at?** Two shapes of the same silence.
An item finished with **no worker behind it anywhere** means the router did the node's work itself — it fires
once, on the turn the item is promoted, and asks for the *next* item dispatched, never a rebuild. And a loop
that has **planned work with no `goal.json`** never ran the node that mints one (`planner:decompose`
greenfield · the `reconcile` checkpoint brownfield): nothing fails loudly, the gates that read convergence
simply have nothing to read, and the drive has no DONE to stop on. Mint it, or park a `steer` saying this
project means to run goal-less — that is a person's call, not a state to arrive in by omission. **It also fires
on the way out at `idle`**, where the rung is otherwise satisfied: a drive that runs its whole backlog goal-less
and hands back is the omission at the exact moment a human returns to steer. Not while a checkpoint is parked
(brownfield's goal comes from the `reconcile` a human has not answered yet) and not under an operator pause.

**Rung 4 — is the report current?** A turn that may legitimately end leaves the four-field, goal-relative block
behind it. Paste it **whole**, including the `[reeve-report state:…]` line: the gate re-renders and compares
digests, so a retyped or summarised block is simply asked for again. The digest covers what the report *says*,
never when it was said, and an unchanged loop is never asked for the same block twice.

**Scoped to an unattended drive** (`REEVE_DRIVE` / `REEVE_SUPERVISE`, exported by `loop.sh`, or
`config.run.drive.gate_turns`), and it **defers while the context gate wants an anchor** — two hooks blocking
one turn with two instructions is how a session obeys neither. It gives up after two demands on a rung rather
than wedging the session, and **fails open on every error**.

**Every id you write beside the block carries its name** — `D-001 (the Postgres-over-SQLite decision)`, never a
bare `D-001`. An id is a pointer, and a pointer the reader cannot dereference is noise that looks like rigour.
`status_report.py --check -` lints prose you are about to send and resolves the names for you.
