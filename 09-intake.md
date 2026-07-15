# 09 — Intake & Task Lifecycle (the front of the spine)

Extends `01`. Covers how a human request becomes an autonomous-ready unit of work. The rest of the
macro-loop (execute → test → document → audit → next) is still **[OPEN]** in `01`; this doc closes only
the **intake** stage.

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
- **Why it matters:** this drives the test/audit phases *and* the Space 6 intent-vs-actual divergence
  check. **Provisional changes must not trip the drift alarm**, or the system spends its autonomy
  chasing ghosts.
- **Provisional = tracked debt, not a shrug** — every provisional element generates a finalize-later
  backlog item so "later" actually arrives.

## Universal invariants **[DECIDED — D23]**
Failures that are bugs regardless of what the spec says: **crash, data loss or corruption, security
hole, core flow broken.** These bound the "unspecified → undefined behaviour" rule above.

## Still open (this doc)
- The rest of the macro-loop (execute → test → document → audit → next) — `01`.
- **Engineering-feasibility pass** — the spike that de-risks the technical unknowns the demo skips.
  **[DESIGNED — D69: the proportional-rigor decision gate; implementation deferred to `11`.]**
- **Backlog / prioritization + interrupt model** — e.g. a bug found mid-feature: queue vs interrupt; how
  urgency is assigned. *(Interrupt model closed: pure queue, D26. **Continue-while-parked interleaving decided —
  D91:** while a ticket is parked on a checkpoint, `prioritize` picks the next **eligible** ticket — dependency-ready
  ∧ file-disjoint ∧ ¬1-hop-neighbor — capped ≤3, prefer-serial.)*
- **Demo skill mechanics** — how the sandbox is served/run, refine-round limits, where it lives on disk.
  *(The demo **trigger** and the checkpoint data model / help set are now closed — D96–D98, `04`; this is the
  sandbox **serving** mechanics only, cluster D.)*
- **Setup checkpoints** — **closed (D96–D98, `04`):** foreseeable ones declared in the spec `integrations[]` +
  an execute-discovered path; verb-enum verdict, machine-verified, plural+coalesced; MVP help = steps + verified
  deep-links + breadcrumbs.
- **Commitment-status storage** — where locked/provisional/unspecified is recorded (spec doc vs Space 6
  node frontmatter).
- **Engineer agent** in the roster — **resolved (D69): no new agent** — the feasibility role is the
  proportional-rigor gate reusing `planner`/`decision-engineer`/`research` (`02`).
