# 09 — Intake & Task Lifecycle (the front of the spine)

Extends `01`. Covers how a human request becomes an autonomous-ready unit of work — the **intake** stage.
The rest of the macro-loop (execute → test → document → audit → next) is **CLOSED**: the spine lives in `10`
and renders as `.workflow/loop.md` (D47).

## Core framing: one spine, variable-depth intake **[DECIDED — D16]**
The "two loops" (existing project / new project) converge. Both end in the same place: a defined,
testable unit of work that runs the same autonomous spine. The only variable is **how much discussion
intake needs** before the work is set:
- bug → near-zero intake
- feature → short scoping discussion
- project (inception) → heavy inception

Inception is just the deepest intake; its output is a **backlog**, which the Roadmap phase sequences;
then it is the steady-state spine for the project's life. Steering injects new items into the same
backlog. (Maps to D8 Inception/Steering.)

## The autonomy gate: definition-of-done **[DECIDED — D17]**
Every task carries **acceptance criteria / a testable definition-of-done**. That — not "bug vs feature"
— is what makes a task safe to run unattended; it is also what checkpoints (Space 4) and the
test/audit phases verify against. Intake's job is to produce work defined enough to self-verify.

## Three intake types **[DECIDED — D18]**

### Bug **[DECIDED — D19]**
| Origin | Contract | Ends with |
|---|---|---|
| Found by an autonomous session (testing, audit…) | Already reproducible → no human context needed | Autonomous fix |
| Reported by user | Either (a) explained until the system can reproduce it itself, or (b) the full flow that triggered it | (b) → a checkpoint where the user verifies the fix |
| Non-reproducible even after explanation | — | **Guided diagnosis WITH the user** (logging / screen-share via the checkpoint machinery) — never blind fix-then-verify |

- A fix's definition-of-done includes a **regression test** (reproduce-then-pass).
- **"Can replicate ≠ knows what's correct."** Autonomous fixing needs *recorded intent* (Space 6). For
  **specified** behavior, deviation from it = bug. For **unspecified** behavior, see the commitment model.

### Feature **[DECIDED]**
Needs **purpose defined** + **visuals agreed** (if it has a visible surface). Flow: short scoping
discussion → written spec → (if the sandbox gate fires) demo validation → autonomous build. Acceptance
criteria are written before the build.

### Project / inception **[DECIDED — D20]**
The heaviest intake. Required inputs:
- tech stack, initial screens, purpose, initial features (the originally-listed musts);
- **audience** (who it is for) and **runtime/environment** (where it runs) — the product-side framing of
  engineering constraints;
- data model + integrations (carried in the spec).

Output: vision + spec + a prioritized **backlog** → Roadmap sequences it → steady-state spine. Audience +
runtime feed an **engineering-feasibility capability** that derives technical constraints and weighs *how* to
implement — separate from the product alignment the demo does. **[DESIGNED — D69:** it is the proportional-rigor
decision gate (a triage in `planner` → tiered `research`/pressure-test via `decision-engineer`), **not** a new
"engineer agent"; implementation deferred.]

## The demo / sandbox **[DECIDED — D21]**
A **"create demo" skill** (config-package primitive) that emits a **throwaway, minimal, non-integrated
sandbox** (no backend, no realistic data) — a runnable alignment artifact surfaced as a **checkpoint**
(Spaces 3 + 4). Feature-demo and project-demo are the *same primitive at two scales*.

- **What it de-risks:** the **product** question (did we agree *what* to build?). NOT the engineering
  question — a no-backend mock cannot validate data model / integration / stack. "Demo approved"
  certifies only the **visual/behavioral subset** of the spec. (Engineering risk → a separate
  feasibility pass — **[DESIGNED — D69: the proportional-rigor decision gate; implementation deferred]**, see `07`.)
- **Spec-first, demo-validates:** conversation → written spec → demo *tests* the spec against the user's
  actual mental picture. The demo is generated *from* the spec; the user reacts with plain-language
  change requests → spec is edited → demo regenerated → retest (a refine mini-loop). These intake-stage
  spec edits are owned by **`create-demo`** (not `refine` — no plan exists pre-build; D96). The spec never
  lags the demo; **the spec state that produced the approved demo is what gets locked.**
- **Throwaway by default** — the sandbox is not reused as the real scaffold (avoids
  prototype-rots-into-production; an autonomous agent will not resist the shortcut unless told).
- **Fidelity matches the question:** low-fi first for new projects (validate scope/flow; prevents
  premature styling debate), high-fi only when the *look itself* is the decision. A rough first demo is
  correct, not a defect.

## The sandbox gate — when a demo is needed **[DECIDED — D22]**
Build a sandbox **iff all three** hold; the default is **no sandbox** (build straight from spec):
1. **Open product decision the *user* owns.** System-discovered work is never sandboxed; if the system
   thinks a *new* product surface is warranted, it escalates that as a steering question rather than
   mocking it unilaterally.
2. **Changes what the user sees or touches.** Not backend / refactor / perf / internal logic.
3. **Look/behavior is underdetermined** — *either* it introduces a **new interaction pattern with no
   precedent** in the app/design system, *or* a competent engineer could ship **two materially-different
   versions** the user would care between. Determined (→ no sandbox) if it reuses an established pattern
   or the request pins the outcome.

Genuine fence at (3) → a **one-line yes/no** to the user ("build directly, or mock it first?") — cheaper
than a wrong build.

| Work item | ① user-owned | ② visible | ③ ambiguous | Sandbox? |
|---|---|---|---|---|
| System-found behavior fix | ✗ | — | — | **No** |
| New "stories upload" screen | ✓ | ✓ | ✓ new pattern | **Yes** |
| Add a field to an API | — | ✗ | — | **No** |
| Add a row to an existing settings list | ✓ | ✓ | ✗ reuses pattern | **No** |
| "Move logout to top-right" | ✓ | ✓ | ✗ pinned | **No** |
| "Add dark mode" | ✓ | ✓ | design-system-dependent | **Fence → ask** |

## The sandbox — serving, refine loop, storage **[DECIDED — D102–D104; BUILT + sharpened — D124]**
The demo mechanics are **over-determined by the A/B substrate** (like the console stack was, D100): a demo is
just *more files on disk*, so D93's "the daemon serves files; the orchestrator writes them, never responds"
already answers who serves it. The build (D124) drove the isolation in a real browser and `create-demo` on a real
model, and corrected two things below.
- **Format (D102) + the discipline's real enforcer (D124):** a **build-free, self-contained static bundle** —
  **no external hosts, no `eval`** (the two invariants that make it render identically local + over the tunnel,
  offline, never phoning home; the Claude Artifacts discipline). **Vanilla JS + `<template>` + hash routing** by
  default; **htm + preact vendored locally** (~10 KB, tagged templates, not JSX) as the escape hatch — the *same
  idiom the console uses* (D100). Banned: CDN `<script>`, `@babel/standalone` / `text/babel` JSX (needs
  `unsafe-eval`), npm/bundlers. **The `sandbox` CSP does NOT enforce this** — measured (D124), `eval`/external
  hosts run under it; it enforces *isolation* only. So the discipline is `create-demo`'s, backed by a shipped
  mechanical floor **`check_demo_bundle.py`** run before the park (fix-and-regenerate on a hit) — the format
  enforcer, the CSP the isolator.
- **Serve (D102), built (D124):** the always-on **bus daemon (D94) serves `/demo/<id>/`** on **both sockets** —
  no sibling server, no second port. `create-demo` writes the bundle **before the park** (D90). Isolation =
  **`Content-Security-Policy: sandbox allow-scripts allow-forms`** (the `sandbox` *directive* → an **opaque
  origin** server-side, **proven in real Chrome**: the demo can't touch the console's storage or token-gated
  endpoints, at **top-level** navigation from the header alone — the D98 deep-link / away-tab case — **and** when
  the console **embeds** it in an iframe). Reinforced by the embedded `sandbox="allow-scripts allow-forms"`
  attribute — **never `allow-same-origin`**; the console gains `frame-src 'self'` to embed it while keeping its own
  strict `script-src 'self'` (two per-path CSPs from one daemon). Guarded by a realpath check + a **no-dotfile**
  rule; MIME + `nosniff` + `no-store`; a bounded read-retry so an in-place refine never flashes a 404 (below).
  **Demo = look, console = the D97 verdict form around it** (read-only, no POST, no token — the **static-asset
  serving class**, token-free, Host-gated; `05`). The **away human** reaches it for free over the **reduced remote
  socket** (D112): a `demo` verdict is an *opinion* (no payload), so submitting it remotely is in-scope. That
  surface needs a **declared identity transport**; with none, the demo is loopback-only like everything else.
- **Refine cap (D103), with a durable home (D124) and a mechanical floor (D154):** the change-request → regenerate
  mini-loop is bounded at **N regenerations** (config-overridable `config.demo.max_refine_rounds`, **default 3**),
  counted plainly — and since D154 `check_demo_bundle.py` **enforces** both the cap and the rule that each round
  edited the **spec** first (the ledger records the spec's hash per round; an unchanged hash is refused). Before
  that, the cap was a number two documents stated and no code read. On the cap
  it **never auto-proceeds** (D97) — it **escalates to a live `discuss` session** (a low-bandwidth async channel
  that won't converge *is* the signal the gap needs high-bandwidth conversation — D93), carrying the refine
  history. The count spans park → resume → a possibly-relaunched session and the loop is stateless glue
  (D92/D123), so it lives on disk at **`.workflow/demos/<id>/.refine.json`** (a dotfile the server refuses),
  read-and-incremented each round — never in context or the parked record.
- **On disk (D104), with a pinned prune owner (D124):** **`.workflow/demos/<item-id>/`** — gitignored runtime
  (not committed `items/<id>/`; not `/tmp` scratch — it must survive an hours-long park), on the repo mount
  (`no-pin`), regenerated in place via atomic write (`os.replace`; measured **content-atomic** on 9p, `no-store`
  prevents a stale render — a concurrent read only ever hits a transient open blip that self-heals), a `demo_id`
  pointer in the `parked/<id>` record. **Pruned on TERMINAL resolve by the verdict-apply path** (approve → lock the
  spec / reject → `discuss` delete the bundle; `changes` keeps it — the locked *spec* is the durable artifact,
  D21), with retention's **`prune_demos`** (a demo dir with no open `parked/` record is a resolved leftover) as the
  straggler backstop. Owner: `create-demo` writes, the apply path deletes, retention sweeps stragglers.

## Commitment model — locked / provisional / unspecified **[DECIDED — D23]**
Every spec element carries a **commitment status** that tells the loop how to treat a later deviation:

| Status | Meaning | A later deviation means… |
|---|---|---|
| **Locked** | committed; agreed | **bug / drift** → fix |
| **Provisional** | agreed *placeholder*, to be refined | **expected** → not a signal; **spawns a "finalize X" backlog item** (tracked debt) |
| **Unspecified** | never spoken to | **undefined behaviour** → tiny steering question — *unless* it hits a **universal invariant** (crash / data-loss or corruption / security hole / core flow broken), which is a **bug** regardless of spec |

- **How status is set:** default by **fidelity + category**, override on request. A low-fi project demo
  declares up front "structure & flow = locked-candidate, all styling = provisional," so the user tags
  nothing and just reacts; they override specific items in feedback ("that brand color is final," "the
  onboarding is a placeholder").
- **Where status lives (D106):** **inline on the spec element** (`screens[]`/`features[]`/`phases[]` `commitment`;
  STABLE tier, human-owned) — the sole owner. **Never on nodes** (code-derived, regenerated); the drift check reads
  it code→intent by resolving a node to its spec element. See D106.
- **Why it matters:** this drives the test/audit phases *and* the Space 6 intent-vs-actual divergence
  check. **Provisional changes must not trip the drift alarm**, or the system spends its autonomy
  chasing ghosts.
- **Provisional = tracked debt, not a shrug** — every provisional element generates a finalize-later
  backlog item so "later" actually arrives.

## Universal invariants **[DECIDED — D23]**
Failures that are bugs regardless of what the spec says: **crash, data loss or corruption, security
hole, core flow broken.** These bound the "unspecified → undefined behaviour" rule above.

## Still open (this doc)
- **Engineering-feasibility pass** — the spike that de-risks the technical unknowns the demo skips.
  **[DESIGNED — D69: the proportional-rigor decision gate; implementation deferred to `11`.]**
- **Backlog / prioritization + interrupt model** — e.g. a bug found mid-feature: queue vs interrupt; how
  urgency is assigned. *(Interrupt model closed: pure queue, D26. **Continue-while-parked interleaving decided —
  D91:** while a ticket is parked on a checkpoint, `prioritize` picks the next **eligible** ticket — dependency-ready
  ∧ file-disjoint ∧ ¬1-hop-neighbor — capped ≤3, prefer-serial.)*
- **Demo skill mechanics** — **CLOSED (D102–D104, cluster D); BUILT — D124:** the sandbox is a build-free
  self-contained bundle the D94 daemon serves under a `sandbox`-CSP opaque origin (§ *The sandbox — serving,
  refine loop, storage*); the refine loop caps at 3 regenerations → escalate to `discuss`; it lives at
  `.workflow/demos/<item-id>/`, pruned on resolve. The build proved the isolation in a real browser and drove
  `create-demo` on a real model, and pinned the two owners the design left open (the refine-count home + the prune
  path) — D124. (The demo **trigger** + checkpoint data model / help set closed earlier — D96–D98, `04`.)
- **Setup checkpoints** — **closed (D96–D98, `04`):** foreseeable ones declared in the spec `integrations[]` +
  an execute-discovered path; verb-enum verdict, machine-verified, plural+coalesced; MVP help = steps + verified
  deep-links + breadcrumbs.
- **Commitment-status storage** — **CLOSED (D106):** the **spec owns it inline** per element (STABLE, human-owned
  intake), **never node frontmatter** (a second copy that drifts + gets clobbered on regen — D80/D78); the drift
  check (`align`/`verify`/`audit`) resolves the changed code node → its spec element and reads `commitment` on the
  **intent side**. **The resolution is judgment, not a keyed lookup** — over the eager `[G]` graph + the decision
  records + the STABLE spec, with the node's `purpose.intent` as **one input when present**, never a foreign key:
  `intent` is `06`'s tier-`[D]` layer, *authored on touch* by `document`, so a node that has never been touched
  carries none — while the drift check must resolve **any** changed node. (`purpose.actual` can't stand in: it is
  extracted *from* the code, so keying on it to find the spec element is circular.) The **mechanism** is not yet
  built or decided — `07`.
- **Engineer agent** in the roster — **resolved (D69): no new agent** — the feasibility role is the
  proportional-rigor gate reusing `planner`/`decision-engineer`/`research` (`02`).
- **The chain-forecast** — **[BUILT — D159 · D162 · D163, `11` Phase 9a]:** a pre-execution forecast of the loop's own
  *routing* for a requested change (events naming real `loop.md` nodes, conditional branch points, predicted setups
  elicited early), surfaced as a **`forecast` judgment checkpoint** (`04`). The demo's sibling on the intake stage —
  `create-demo` de-risks *what* to build, `/create-forecast` de-risks *how the machine will proceed* — and, like the
  demo's spec edits, it fires **pre-plan**. Front-loads D97's setup *elicitation*, never its verify probe. Owner: **D159**.
- **Org mode** — **[DESIGNED — D161, `11` Phase 9c; unbuilt]:** a third intake mode beside greenfield/brownfield for a
  company product the maintainer does not own — **org-brownfield is `ingest` minus footprint** (never edits the
  company `CLAUDE.md`, `create-issue` is local-only, **nothing out of the checkout is ever executed**), over a
  private-tree brain with `project_root` = the external checkout. **Note (D171, 2026-08-04):** the execution hazard
  is **not** in `ingest`, which runs no gates at all — it is the **commit gate**, where the adopted `checks.env`
  would run the company's own suite on every loop commit. Owner: **D161**; the re-anchoring and the required third
  `checks.sh` state: **D171**.
