# 04 — Checkpoints (Space 4: the manual human-test gate)

## MVP scope **[DECIDED]**
Structured **manual** checkpoints surfaced through the website. Flow:

> orchestrator hits a checkpoint → blocks (waits on the bus) → posts to the website WHAT to verify and
> HOW (step-by-step, each step a verified deep-link + a breadcrumb path — see the help set below) → human
> reports an **outcome** (approve / changes / reject) + notes (+ any returned values) → bus delivers the
> verdict → orchestrator resumes.

## Two boundary types (the taxonomy) **[DECIDED — D96]**
A checkpoint sits at a boundary only a human can cross, of one of two types — this organizes every trigger and
verdict below:
- **Judgment** ("is this what we meant?") — `demo` (spec vs mental picture, intake), `qa` (behaviour vs intent,
  build-tail), `reconcile` (reconstructed spec vs reality, brownfield). The verdict is an opinion.
- **Action** ("do something in the world I can't reach") — `setup` (perform an external action, obtain a
  credential). The verdict is "I did it" + a returned artifact, then **machine-verified**.

**Not a checkpoint: authorizing an *outward* action (D105).** Approving a `git push` / `gh issue create|close` /
deploy is *not* a fifth checkpoint kind — the real fault line is **blocks-the-ticket (a checkpoint parks and resumes)
vs defers-a-side-effect**. An outward action blocks nothing (the commit is local, the ticket completes, the loop
advances — D35 never-stall), so it never parks; it rides the **outbox** queue (`05` / `shared/schemas.md`), gated by
`config.outward` + `guard.sh` and released in batches over the `kind: release` inbox message. `setup` (the human
*does* an external action the loop can't) is a genuine checkpoint; `publish` (the human *authorizes* the loop to do
one) is not — don't conflate them.

## Block/resume mechanism **[DECIDED — D90, empirically verified]**
A checkpoint is a **durable park boundary**, not a live in-session wait (nothing inside Claude can self-wake — no
background-exit re-invoke, no hook that wakes an idle model). The orchestrator writes the graceful handoff +
verdict-request to disk and **yields**; the verdict lands on the local bus into a durable **append-only inbox**
(D91 correlation); resume is **`claude --resume <id> -p "<verdict>"`** — the verdict rides as an *authoritative
prompt* (a `SessionStart` hook only re-points to durable state; hook-injected context is under-weighted), cold-
starting from `handoff.md` + `git log` if the session store is gone. Restart trigger = **manual in MVP** (a console
prompt) → a **local relaunch runner** later. **Not** a hook exit-code trick (a `Stop` hook exiting 2 forces
*continue*, not pause). While parked, the orchestrator **interleaves** to the next independent ticket (D91).

**The away-channel for a bounded question (D93 conversation corollary).** A checkpoint is also how the orchestrator
asks the *away* human a bounded question — it parks with the request, the human answers async via the bus, it
resumes. Open-ended new-feature **dialogue** is *not* a checkpoint; it's a terminal activity (the live `discuss`
session). The bus carries only bounded clarifications + `intake` requests, never a real-time chat (the loop is a
batch consumer — see `05`).

## Motivating example (user)
Setting up a Polar account: each time Claude said to change a setting, the human had to go find exactly
where it lives in Polar's docs/UI. The workflow should instead surface the doc location / a screenshot,
or take a screen-share and give live feedback.

## Triggers — who decides a checkpoint is needed **[DECIDED — D96]**
Declared upstream wherever the intent lives, with setup's one exception:
- **qa** — `planner` declares a `human-qa` acceptance criterion (D30).
- **demo** — the sandbox gate (D22) in `create-demo`, evaluated per work-item; the gate *is* the trigger. The
  intake-stage refine loop's spec edits are owned by `create-demo` (it edits the spec slice and regenerates —
  `refine`'s plan-delta machinery is build-stage, so it doesn't apply pre-plan). The **sandbox is surfaced** in
  the checkpoint page as a **bus-daemon-served, `sandbox`-CSP-isolated bundle beside the verdict form** (demo =
  look, form = verdict); its serving / refine-cap / storage mechanics live in `09` (D102–D104).
- **reconcile** — `ingest`, after brownfield spec reconstruction (D68).
- **setup** — spec `integrations[]` for the foreseeable + an **execute-discovered** path for the unforeseen (a
  licensed `execute → checkpoint(setup)` edge). Either way it becomes a durable parked record, never an in-memory
  block.

## Verdict + the setup lifecycle (the data model) **[DECIDED — D97]**
- **Verdict is a verb-enum, not a boolean:** `{ outcome: approve|changes|reject, notes, returns? }` (`pass` ≡
  approve). Routing keys off `outcome` per kind (see `shared/schemas.md` / `skills/checkpoint`).
- **Setup is machine-verified on resume** — "done" unblocks the agent to *probe the key/webhook actually works*
  before proceeding; a failed probe re-guides. Setup is the one kind whose human verdict is an input to a `verify`,
  not the terminal signal.
- **Setup is plural + coalesced:** `request.tasks[]` (a lone setup is a one-element set), per-task outcomes;
  foreseeable setups are bundled **within-plan at first-setup-contact** (not front-loaded). Cross-ticket coalescing
  is deferred (the schema already fits it — additive, not a refactor).
- **A returned secret rides the inbox, sensitive + shred** — written to the gitignored secret store, never logged,
  the inbox record shredded after use (D95 scopes the bus to the user's own UID; residual exposure equals `.env`).
- **Timeout never auto-proceeds** — it re-surfaces + reminds; a missing credential can't be skipped.

## Help set — how the human is told what to do **[DECIDED — D98]**
The async/park model draws the line (nothing live happens while parked): only guidance that fits a durable
request→verdict round-trip is MVP.
- **MVP** — a **contextual step-list** (one action per step, at the step, not front-loaded) + per-step a
  **deep-link resolved live and verified to resolve**, always paired with a **breadcrumb** ("Settings → Payments →
  Webhooks") + the search query (graceful degradation against link rot). `setup-guide` produces this.
- **Deferred** — screenshots (need a live-browser capture; go silently stale), screen-share + live-feedback
  (synchronous → a user-present terminal escalation, never the parked bus), agent-driven browser automation
  (unreliable + a credential/irreversibility trust gate). The human stays the actor.

## Out of scope (designed-for, not built) **[DEFERRED]**
Automated testing; test-from-anywhere (run-while-away → test env → Cloudflare tunnel → phone ping);
the paid device/QA platform.
