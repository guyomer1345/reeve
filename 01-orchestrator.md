# 01 — Orchestrator (Space 1: the spine)

## Role **[DECIDED]**
The one long-running Claude Code session the human talks to. It is a **thin dispatcher/router**, not a
doer — it holds the vision/goals and routes work to agents, keeping its own context as clean as
possible. Its context window is the scarce resource.

## Three-layer memory model **[DECIDED]**
1. **Orchestrator** = thin router; only distilled questions + decisions flow through it.
2. **Persistent agents** = working memory; each specialist holds its own deep context and can be
   re-messaged (SendMessage). (Corrects the earlier "ephemeral/stateless" assumption — see D4.)
3. **Shared disk state** (Space 5) = durable artifacts; heavy outputs live on disk, agents pass thin
   pointers/summaries up.

## The open-question-resolution pattern **[DECIDED]**
The core autonomy primitive — how any agent unblocks itself without dirtying the orchestrator or
stopping to ask the human:

> Agent hits an open question → reports it UP to the orchestrator → orchestrator (knowing the vision)
> spawns an **Investigation agent** (best practices in comparable products) → then an **Arbiter**
> (makes the call) → reports the decision UP → orchestrator hands it back DOWN to the still-alive
> originating agent, which continues.

- Arbiter open detail: decides a batch in dependency order vs one at a time (changes its input
  contract). **[OPEN]**

## Concurrency **[DECIDED — D36/D91]**
Parallel by default — run as many agents concurrently as the work allows; serialize only when tasks
collide. Realized as **waves** (D36): `prioritize` groups independent ready items into a wave, runs it in
parallel, then re-picks; dependents fall to the next wave; build hooks run **once per wave** (parallel
agents hitting build tools cause lock contention).
- **The collision / independence test is now DECIDED (D91):** a candidate is eligible iff **dependency-ready** ∧
  **file-disjoint** from every in-flight/parked ticket (*hard gate*) ∧ **not a 1-hop code-map neighbor** of one
  (*soft gate → start flagged for a speculative-merge verify*). It runs off the code-map `graph.json` (dependency
  graph, not co-change — D78). This same predicate powers **continue-while-parked interleaving** (D91): while one
  ticket is parked on a checkpoint, the single orchestrator picks the next eligible ticket (each in its own **git
  worktree** + branch), capped ≤3 concurrent, **prefer-serial**; whole-loop park is the degenerate case. Scheduler:
  non-preemptive, item-level, **resume-a-ready-parked-ticket first (+aging) → start-new → sleep**; the boundary
  check is plain code, not an LLM call.

## Session lifecycle **[DECIDED / partly OPEN]**
- PC must be on (Claude can't run with the machine off).
- Start: a command from a clean session initializes it as the orchestrator + launches the website.
- Finite context → graceful **reset/handoff**: park/finish open tasks, `document`, `commit`, then rewrite
  `handoff.md` as the **durable resume anchor** (current item + loop position + parked work). The split:
  `state.json` = volatile live pointer · `handoff.md` = durable anchor · **git history = the append-only
  completed-step log**; a new session resumes from `handoff.md` + `git log` (committed items never rerun).
- **Checkpoint park/resume [DECIDED — D90, empirically verified]:** a blocking checkpoint is a **durable park
  boundary**, not a live wait (nothing inside Claude can self-wake). Park = write handoff + verdict-request to disk
  and yield; resume = **`claude --resume <id> -p "<verdict>"`** (verdict rides as an *authoritative prompt*; a
  `SessionStart` hook only re-points to durable state — hook-injected context is under-weighted), cold-starting from
  `handoff.md` + `git log` if the session store is gone. Notify an away human via the `Notification` hook.
- **Context / reset mechanism [DECIDED — D92, empirically verified]:** the conversation is **disposable** (handoff +
  git authoritative). Heavy per-ticket work runs in **fresh subagent windows**, so the orchestrator stays thin and
  barely grows. **Auto-compact is a within-run seatbelt only** (~63% reclaim; threshold via
  `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`), **not** the cross-ticket strategy. Pure Claude Code **cannot** self-`/clear`
  or auto-restart (no `SlashCommand` tool; `/clear` is human-only; `SessionStart` can't fire an autonomous turn).
  - **MVP (pure config):** a **manual alert** prompts the human to `/clear` + re-run `/start` (rehydrate from
    `handoff.md`) once the single session is polluted — the only non-autonomous step. The graceful handoff (park →
    `document` → `commit` → write `handoff.md`) happens regardless, so the runner below is an add-on, not a redesign.
  - **Full autonomy (optional, deferred):** a thin **local relaunch "runner"** — a fresh `claude -p` process **per
    ticket** (a clean window for free; the loop lives in stateless bash/SDK, so nothing accumulates). This is the
    ONLY path to true overnight autonomy AND it *triple-solves* context-reset + autonomous checkpoint-resume +
    overnight. It is a **local relaunch loop, NOT the Agent SDK** (the SDK runs *cloud* managed agents and cannot
    resume a local session — D90); each user runs it on their OWN auth. Tradeoff = purity (config + a small
    program), not legality.

## The macro-loop **[DECIDED — spine in `10`; driver above]**
The full spine (`prioritize → discuss/create-demo → planner → execute → verify → debug/refine → checkpoint
→ document → commit → close-issue`) lives in `10` and renders as the routing graph in `.workflow/loop.md`;
the orchestrator drives it via the control algorithm in *The orchestrator `CLAUDE.md`* above. Checkpoint =
`04`; reset = the handoff/resume model in Session lifecycle.
- **Intake stage is now specced in `09`** (task types + contracts, the demo skill + sandbox gate, the
  commitment model; inception + steering covered there). The remaining execute → test → document → audit
  → next phases are still open here.

## The orchestrator `CLAUDE.md` — the driver **[DECIDED]**
The package shipped **no driver** until this: the target project's **root `CLAUDE.md`** is the orchestrator's
always-loaded operating brief (re-injected after `/compact`). "Orchestrator" is its *role* — the always-loaded
session at the launch root **is** the orchestrator — not a separate file. Written lean (a frame, not the
per-capability *how*), it encodes:
- **Identity** — thin router + the three-layer memory model above; *bounded by construction* — the files it
  reads every turn (`CLAUDE.md`, `state.json`, `handoff.md`, `loop.md`) are rewritten in place, never grown.
- **The loop** — a *pointer* to `.workflow/loop.md` (routing graph + diagram), read on demand to route
  (definition vs position — `loop.md` is the fixed topology, `state.json` the live pin).
- **The control algorithm** — *drain* (consume the inbox — see below) → *read* `state.json` (cold start:
  `handoff.md` + `git log`) → *place* (mid-item continue; between items `prioritize`) → *advance* (look up the
  node's edges, dispatch, follow the result, write `state.json`).
- **The boundary drain [DECIDED — D108]** — at every scheduler boundary the orchestrator consumes `inbox/` before
  it schedules, **all kinds, uniformly**: list `inbox/` → skip `message_id`s already in the `handoff.md`
  consumed-set → **apply `control`** (so a reprioritize is honored by the pick that follows) → **resume a
  ready-parked ticket** (oldest verdict first, +aging — D91) → **promote `intake`** into the backlog through triage
  → **start-new** → **fire `release`** through `guard.sh` → sleep. Without this step an orchestrator following its
  brief literally would park at a checkpoint and never consume the verdict that unparks it.
- **Invariants split** — **enforced** (secret-scan + verify-before-commit + the **push floor** — never move a
  protected branch, never push a secret in the outgoing range — = `hooks/guard.sh`; the outward-action gate = the
  `config.outward`/outbox defer-and-release model over that floor, with the harness **out of the outward path
  entirely** — D110 removed the settings `ask` for the outbox-covered classes, because it would block the very
  away-release it was imagined to back up; build-once-per-wave deferred) vs **disposition** (hub-and-spoke; pure
  queue; resolve-don't-stall via `research`→`decision-engineer`; mind the tiers).
- **Checkpoints** (durable park on the bus — D90) and **handoff/resume**.

Driving model: `CLAUDE.md` is **advisory context, not enforced configuration** — so the loop *sequence* runs
model-on-rails while the **hard gates are deterministic hooks**. Layout is per-mode (greenfield launch-root +
`project/`; brownfield a marked block in the existing root `CLAUDE.md`) — see `commands/start.md` + `05`.

## Model + effort routing **[DEFERRED]**
Not every task runs at the same model/effort. The orchestrator assigns a model+effort per task type
(e.g. graph-maintenance cheap; Arbiter/planning expensive). Exact mapping not specced now.
