# 08 — Decision Log (provenance)

Every decision from the planning conversation: the call, why, what was rejected, and the evidence.
This folder is the source of truth and supersedes prior-session memory where they conflict.

## D1 — This spec folder is the source of truth **[DECIDED]**
The decisions captured here (originally from the planning conversation) supersede prior-session memory /
architecture notes where they conflict; prior memory is background, re-verified here. *Evidence:* user
instruction.

## D2 — Build shape: pure Claude-Code-native config package **[DECIDED]**
Skills + subagents + hooks + slash commands + MCP + CLAUDE.md, run locally on the user's own
subscription. NOT a program that drives Claude.
*Rejected:* own-loop-on-raw-API; headless cockpit + website + watchdog that drives Claude (both sit in
the request path).
*Evidence:* master rule (D3); GSD / Spec Kit precedent (config packages, ~64k / 112k stars).

## D3 — Master rule: never in Claude's request path **[DECIDED]**
Everything local; components talk via local bus + files, never by routing Claude. A hosted router on
behalf of users = prohibited.
*Evidence:* Anthropic ToS posture (third-party routing banned); carried from prior analysis, reaffirmed.

## D4 — Agents persist (correction) **[DECIDED]**
Agents hold context and are re-messageable (SendMessage); not one-shot/stateless → three-layer memory
model; orchestrator stays a thin router.
*Rejected:* the earlier "ephemeral/stateless subagents" assumption.
*Evidence:* current harness Agent/SendMessage capability; user confirmation. (A research agent repeated
the stale "stateless" claim — flagged and overridden.)

## D5 — Six-space decomposition **[DECIDED]**
Orchestrator / Agents / Website / Checkpoints / Shared disk state / Knowledge structure. Shared state
added (5th) as the connective tissue for local-only comms; Knowledge added (6th) at user's request.
*Evidence:* planning conversation.

## D6 — Open-question-resolution pattern **[DECIDED]**
planning → up to orchestrator → Investigation → Arbiter → back down; keeps the orchestrator clean.
"Arbiter" chosen over the placeholder "sequential decision maker."
*Evidence:* user's described flow.

## D7 — Operating scope: single local project / user / machine **[DECIDED]** (A1)

## D8 — Human-in-the-loop: two modes + checkpoints **[DECIDED]** (B1)
Inception (heavy) + Steering (ongoing) + in-flight checkpoints.

## D9 — Concurrency: parallel by default, serialize on collision **[DECIDED]** (B2)
→ collision model needed.

## D10 — Session lifecycle + graceful handoff **[DECIDED]** (B3)
Start command boots orchestrator + website; finite context → graceful handoff (park → document →
commit → write `handoff.md`). Reset is now definitively understood:
- Pure config **cannot** self-`/clear`/restart (`/clear` is human-only; no hook/MCP/setting; `/compact`
  + delegation ceiling ~300–500 turns / ~2–4 hrs).
- **MVP path:** website prompts human to `/clear` + restart from `handoff.md` (one click).
- **Full-autonomy path (optional, deferred):** a thin local SDK runner triggers handoff + restart with
  no human action — the only path to true overnight autonomy.
- Correction to earlier framing: the runner does **not** break the master rule. The rule bans routing
  *others'* Claude via a hosted service; a locally-run runner on the user's own auth (even if published,
  each user runs their own) is ordinary individual use. Tradeoff is purity, not legality. Caveat: verify
  SDK subscription-vs-API-key auth when building it.
*Evidence:* B3 research, definitive, doc-cited.

## D11 — No fixed dogfood target **[DECIDED]** (C1)
General design from cross-project use, not built around one project. *Evidence:* user.

## D12 — Comms: local HTTP loopback bus **[DECIDED]** (A3)
Bus = website's local backend; `state.json` for the viewer; checkpoints = explicit wait-on-bus steps.
File-watching rejected for control-flow.
*Evidence:* A3 research (native-primitive + general-IPC angles).

## D13 — Knowledge format: OKF-adapted + LLM-Wiki pattern + llms.txt manifest **[DECIDED]** (D1)
`.knowledge/` dir; per-file nodes; typed edges with `why`; `# Sessions` log; `graph.json`; steal
Aider's tree-sitter extraction for structural edges. Maintenance model deferred.
*Evidence:* D1 research + prior art (Aider repomap, Code Property Graph).

## D14 — MVP scope line **[DECIDED]**
*In:* loop, persistent agents, website, manual checkpoints + help, knowledge base, graceful handoff.
*Out (designed-for):* automated testing, test-from-anywhere, paid device/QA platform.

## D15 — Spec-only; exported to a clean folder **[DONE]**
No implementation during planning. The spec was written in the planning chat, then moved to its
permanent home (`dev-autonomous-workflow/`) — now the source of truth, edited directly. *Evidence:* user.

---

## Intake stage (session 2026-06-29; full detail in `09`)

## D16 — One spine, variable-depth intake **[DECIDED]**
The two work-loops (existing project / new project) converge on a single autonomous execution spine; the
only variable is intake depth (bug → shallow, feature → short, inception → deep). Inception's output is a
backlog → Roadmap sequences it → steady-state spine; Steering injects new items into the same backlog.
*Rejected:* modeling them as two independent loops. *Evidence:* this session; consistent with D8. → `09`.

## D17 — Definition-of-done is the autonomy gate **[DECIDED]**
Every task carries testable acceptance criteria; that (not the task type) is what makes it safe to run
unattended and gives checkpoints + test/audit something to verify against. *Evidence:* this session. → `09`.

## D18 — Three intake types + contracts **[DECIDED]**
Bug / feature / project, each with a distinct intake contract = what the user must supply before the work
goes autonomous. *Evidence:* user's task taxonomy. → `09`.

## D19 — Bug intake contract **[DECIDED]**
Autonomous-found = already reproducible → fully autonomous fix; user-reported = explained-until-reproducible
OR full-flow (the latter ends with a user-verify checkpoint); non-reproducible-after-explanation → guided
diagnosis WITH the user, never blind fix-then-verify. A fix's DoD includes a regression test. "Can replicate
≠ knows what's correct" → autonomous fixing needs recorded intent (Space 6).
*Rejected:* "reproducible ⇒ safe to autonomously fix" as sufficient. *Evidence:* user + this session. → `09`.

## D20 — Required inception fields incl. audience + runtime **[DECIDED]**
Inception must capture tech stack, screens, purpose, features, **plus audience (who) and runtime/environment
(where)** — the product-side framing of engineering constraints — and data model + integrations. Output =
vision + spec + prioritized backlog. Audience/runtime feed an engineering-feasibility capability ("engineer
agent" — role real, exact agent OPEN). *Evidence:* user. → `09`, `02`.

## D21 — Demo/sandbox = throwaway product-alignment checkpoint **[DECIDED]**
A "create demo" skill emits a throwaway, minimal, non-integrated sandbox surfaced as a checkpoint;
feature-demo and project-demo are one primitive at two scales. It de-risks the *product* question only
(certifies the visual/behavioral subset of the spec), NOT engineering. Spec-first / demo-validates: the demo
is generated from the spec, change requests edit the spec and regenerate it (refine loop), and the spec state
behind the approved demo is what gets locked. Throwaway by default (no reuse as the real scaffold). Fidelity
matches the question (low-fi first).
*Rejected:* demo as the spec's producer; demo as design/engineering validation; reusing the sandbox as
scaffold. *Evidence:* user + this session. → `09`.

## D22 — The sandbox gate **[DECIDED]**
Sandbox iff (①) it's an open product decision the user owns, (②) it changes a user-visible surface, and (③)
the look/behavior is underdetermined (new pattern w/o precedent OR two materially-different valid builds).
Default = no sandbox; a genuine fence at ③ → a one-line ask. System-discovered work is never sandboxed
(escalated as steering instead). *Evidence:* user examples (A/B) + this session. → `09`.

## D23 — Three-state commitment model **[DECIDED]**
Every spec element is locked / provisional / unspecified, which dictates how a later deviation is treated:
locked → bug/drift; provisional → expected (and spawns a finalize-later backlog item — tracked debt);
unspecified → undefined behaviour → steering question, unless it hits a universal invariant
(crash / data-loss / security / broken core flow) → bug. Status defaults by fidelity + category, overridable.
Provisional changes must not trip the Space 6 drift check.
*Rejected:* monolithic demo approval; treating every demo detail as locked. *Evidence:* user's
locked-vs-change-later distinction + edge-case=undefined agreement. → `09`, `06`.

---

## Roster → package (session 2026-06-29; map in `10`, contracts in the package files)

## D24 — Capability roster v1 + skill/agent taxonomy + adjudicate base **[DECIDED]**
Derived by walking a full new-project loop end-to-end. 16 capabilities, each with an I/O contract (its
package file) over shared artifact schemas (`shared/schemas.md`); loop order + call-graph pinned (`10`).
- **skill** = procedure/controller (the *how*); **agent** = context-heavy persistent worker (D4).
  Controllers dispatch workers (e.g. `debug` the skill fans out mapping + `research` agents).
- **adjudicate** = one base skill (gather views → judge → confidence-gate → loop/escalate), specialized by
  `verify` / `debug` / `decision-engineer` — the Investigation→Arbiter pattern (D6) reified; collapses the
  prior Arbiter / engineer-agent / decision-engineer overlap into one adjudicator.
- `refine` routes corrections back through `planner`→`execute` (never fixes directly — preserves execute's
  zero-decision invariant); `verify` (artifacts) vs `debug` (runtime) split by object; one `checkpoint`
  gate behind demo/qa/setup; `planner` has decompose + plan-one modes; `document` ingests the
  decision/event stream, not just the changelog.
*Closes the `02` roster open item.* *Rejected:* a flat capability list with overlapping deciders; `refine`
as a second executor. *Evidence:* the dry-run walkthrough + user confirmation. → `10`, `02`.

## D25 — Package layout = Claude-Code-native plugin source **[DECIDED]**
The distributable is a CC-native plugin: `skills/<name>/SKILL.md`, `agents/<name>.md`, `shared/schemas.md`
at the repo root (later `commands/`, `hooks/`, `CLAUDE.md`, `.claude-plugin/plugin.json`). The repo is now
both the spec (`00`–`10`) and the package source. *Evidence:* user ("the Claude Code native default").
→ `10`, `05`.

## D26 — Interrupt model: pure queue **[DECIDED]**
The scheduler never self-preempts. In-flight work always runs to its item boundary, then `prioritize`
re-picks; ordering is urgency × dependency-readiness. Rationale: a critical bug found mid-execution is the
current item's own `verify→debug→refine` loop, not a competing backlog item, so preemption never applies;
a genuinely external emergency is handled by the human's manual override (steering), not by the machine.
This removes all parking / mini-handoff / anti-thrash machinery from `prioritize`.
*Rejected:* always-preempt (thrash); tiered-preempt-on-universal-invariants (over-engineered for MVP —
revisit only if the deferred overnight-autonomy runner makes the bounded wait unacceptable).
*Evidence:* user. → `10`, `09`.

## D27 — Agent topology: agents are leaf workers; adjudicators are skills **[DECIDED]**
**skill** = controller/procedure, run by the orchestrator, may dispatch agents. **agent** = a leaf worker
with its own tools that never spawns sub-agents. Consequences: the only agents are `research` and
`setup-guide`; all adjudicators (`verify`, `debug`, `decision-engineer`) are skills — so `decision-engineer`
is reclassified skill (was agent in the first roster draft). *Closes the `02` topology open question:*
strict hub-and-spoke, agents don't spawn agents. *Evidence:* surfaced writing the package files; user-flagged.
→ `10`, `02`.

## D28 — `init` / bootstrap capability **[DECIDED in principle]**
The workflow's start command (D10) is a capability `init` with two modes: **greenfield** (repo-setup →
scaffold workflow structure → launch console → hand to `discuss`) and **brownfield/integrate** (the above
plus an **ingest** pass that builds the initial Space-6 knowledge base + reconstructed spec from existing
code — "map to our standard"). `repo-setup` folds in as a step; `gh auth` and similar are `checkpoint`
(kind=setup) walkthroughs. Brownfield ingest depends on the still-open knowledge-ingest mechanics (`06`).
*Evidence:* user. → `10`, `01`, `06`.

## D29 — `init` / `/start` bootstrap, design v1 **[DECIDED — partial; expand]**
The bootstrap capability (D28) is realised as a human-invoked **slash command `/start`** (conceptually
"init"; not `/init`, which is a Claude Code built-in) → `commands/start.md`. Adds a third primitive class:
**commands = human-invoked entry points** (alongside skills = model-invoked, agents = leaf workers, D27).
- **Mode detect + idempotency:** detect greenfield (empty) vs brownfield (existing code), confirm with the
  user; if `.workflow/` already exists, don't clobber (offer resume from `handoff.md`).
- **Shared steps:** repo-setup; scaffold the workflow layout; install orchestrator framing (CLAUDE.md —
  STUB); launch console (STUB); commit.
- **Greenfield:** empty spec/knowledge → hand to `discuss` (inception). **Fully buildable now.**
- **Brownfield:** ingest existing code → `.knowledge/` + reconstructed spec, then a reconciliation
  checkpoint. **Mostly STUB** — depends on the open Space-6 ingest mechanics (`06`).
- **Provisional disk layout (Space 5, EXPAND):** `.workflow/` (state.json runtime/gitignored; handoff,
  backlog, decisions/, checkpoints/ committed) + `spec/` + `.knowledge/`.
*Evidence:* user (design what's buildable now, note the rest to expand). → `10`, `01`, `05`, `06`.

## Skill review + format pass (session 2026-06-29)

## D30 — Human QA is plan-declared, not a blanket post-verify gate **[DECIDED]**
The plan owns the "does a human need to look at this?" decision, upstream where intent lives. Each
`acceptance_criterion` is tagged `gate: artifact | human-qa`: `artifact` criteria are checked by
`verify`; `human-qa` criteria are confirmed by a `checkpoint` (kind=qa) on the live app. `verify` stays a
**pure artifact check** and always routes `pass → document/commit`; the orchestrator inserts a qa
checkpoint *only* when the plan declared ≥1 `human-qa` criterion. Most changes (internal/refactor) declare
none and flow straight through — no human gate after every verify.
*Rejected:* the old `verify` route `pass → checkpoint (human QA) → document/commit`, which implied
mandatory human QA on every pass; a `needs_human_qa` flag computed *by* verify (puts product-intent logic
into an artifact checker). *Evidence:* user, this session. → `shared/schemas.md` (plan), `skills/verify`,
`skills/planner` (tags the gate), closes the `04` open item "who decides a checkpoint is needed" for kind=qa.

## D31 — Canonical authoring format for skills & agents **[DECIDED]**
Every package file follows one canonical shape so the roster reads as a graph of typed nodes
(`Inputs → … → Output → Route`). A **menu, not a mandatory skeleton**: a required spine + optional sections
included only when they earn their tokens. Definitions live in the contract sections (Inputs/Output name
`schemas.md` artifacts) — the current files are under-*defined* (jargon like `adjudicate`, implicit artifact
contents), not under-described; the fix is defining contracts, not adding prose. Recorded in
`shared/format.md`; imperative node-names kept on purpose (they double as routing-graph labels).
*Rejected:* a mandatory all-sections skeleton (fights "concise is key", forces padding); the
background-research read of "don't template at all" (over-applies generic large-skill guidance to small
orchestrated nodes — Anthropic separately endorses a "cohesive skill library"); "describe more" via prose.
*Evidence:* Anthropic skill-authoring best-practices doc + this session. → `shared/format.md`, applied
skill-by-skill starting with `verify`.

## D32 — Commit message convention **[DECIDED]**
`commit` writes **Conventional Commits** + linking trailers. Type from the item's `kind`
(`bug → fix`, `feature → feat`, `debt → refactor`/`chore`); `Refs: item #<backlog-id>` always;
`Closes: #<gh-issue>` when the commit resolves a tracked issue. Rationale: the commit log becomes
machine-readable loop state, and the trailer is the hinge `close-issue` keys off.
*Evidence:* user. → `skills/commit`.

## D33 — Issue lifecycle: real GitHub issues + close-at-commit-tail **[DECIDED]**
`create-issue` **dual-writes**: files the backlog `issue` **and** opens a real GitHub issue
(`gh issue create`, labels from `kind`/`severity`), storing the number as `issue.github_ref`. GitHub is the
durable external tracker; the backlog references it. A new leaf-tail skill **`close-issue`** closes the
resolved issue at **item completion (commit tail)** — not after `execute` (which runs pre-`verify`, so
closing there would retire work that may still fail). MVP: close the completed item's own `github_ref` 1:1
and comment the commit SHA.
*Rejected:* closing after `execute` (wrong point in the loop); relying on the `Closes:` commit keyword to
auto-close (only fires once pushed, and push is out of `commit`'s scope, so an explicit `gh issue close` is
needed regardless); building incidental-resolution detection now (deferred).
*Evidence:* user (delegated the create-issue mechanics), this session.
→ `skills/create-issue`, `skills/close-issue` (new), `shared/schemas.md` (issue), `10`.

## D34 — Package files carry no spec-internal references **[DECIDED]**
The shippable package (`skills/`, `agents/`, `shared/`) states behaviour and rationale in plain language
with **no spec-internal citations** — neither decision IDs (`Dxx`) nor design-doc numbers (`05`, `09`, …).
Those are provenance and live only in the numbered design docs (`00`–`10`) and this log. Provenance is
**one-directional**: the log names the file a decision governs; the file never cites back (only the
citation is removed — the rationale stays inline). Temporary markers are fine *during* design, not in the
finished file.
*Rejected:* leaving internal IDs in package files (leaks design-process artifacts into the runtime context,
costs tokens, means nothing to a Claude using the skill). *Evidence:* user, this session.
→ applied across `skills/`, `agents/`, `shared/`; rule added to `shared/format.md`.

## D35 — Local work autonomous; outward actions gated **[DECIDED]**
The workflow runs **local/reversible work autonomously** (edits, `commit` — local only) but **gates every
outward, side-effecting action behind explicit human permission**: `git push`, `gh issue create`
(`create-issue`), `gh issue close` (`close-issue`), and later deploys / message-sends. The loop **never
stalls** on this — it keeps committing locally and **queues** outward actions for approval; one approval can
release a batch. **Default = gated** (a checkpoint-style "authorize an outward action" — a new flavour
distinct from demo/qa/setup, which verify or do); users may **opt into standing pre-authorization**, a
config allowlist exactly like Claude Code's own Bash permission rules.
*Why:* validated live this session — the harness let commits proceed but **gated a push to `main`** and
required explicit human auth. Mirrors the master rule (D3) and the existing commit/push split (commit =
autonomous checkpoint marker; push = beyond the skill).
*Rejected:* treating push / `gh` actions as fully autonomous (publishes irreversibly; surprises the user;
would demand standing outward permission they may not grant). *Mechanics OPEN → `07`* (per-action vs
standing, batching, which checkpoint kind).
*Evidence:* user + live harness behaviour, this session. → `04`, `skills/commit`, `skills/create-issue`,
`skills/close-issue`, `07`.

---

## Inspiration / adoption pass — workflow-kit + GSD (session 2026-06-29)

A full read of the user's prior `workflow-kit` (the human-driven `/stage-a → execute → verify → refine →
document` kit that inspired this project), the GSD ("Get Stuff Done") spec-driven system, and best-practice
research. Framing: **both inspirations are human-driven; this project is the autonomous version**, so the
transferable parts are the *content of each phase* and the *discipline gates* — and the gates matter **more**
here, because no human watches each step. Verbosity deliberately **not** taken (their prose is one team's
scar tissue; this roster stays terse, D31).

## D36 — Waves = the collision-model realization **[DECIDED]**
Parallelism (D9) is realized as **waves**: `prioritize` dependency-analyses the ready set, groups independent
items into a wave, runs the wave in parallel, then re-picks; dependent items fall to the next wave. Build
hooks run **once per wave** (parallel agents hitting build tools cause lock contention). Partially closes the
collision open: the *grouping mechanism* is decided; the *independence test* (file/module/area overlap) stays
open.
*Rejected:* ad-hoc per-item independence checks; always-sequential. *Evidence:* GSD waves + user. → `01`,
`10`/`prioritize`, `07`.

## D37 — Execute divergence convergence tiers **[DECIDED]**
`execute`'s divergence handling is tiered: **cosmetic** (helper moved, line drift) → adapt + record;
**discovered-prerequisite-repair** (in-scope-adjacent fix the plan didn't name) → apply as a **separate
commit**, record, continue; **structural** (plan assumes something untrue) → stop + escalate. Preserves
execute's zero-decision invariant — the escalation *is* the decision boundary, and a prerequisite repair is
never silently folded into a planned commit.
*Rejected:* a flat "record a divergence" with no tiering; rolling prerequisite repairs into planned commits
(hides that the executor stumbled into them). *Evidence:* workflow-kit execute taxonomy + user. →
`skills/execute`, `10`.

## D38 — Knowledge/docs design law + three-tier memory invariant **[DECIDED]**
**The law:** a file earns its place only if it holds **non-derivable intent** or is the loop's **cross-session
memory**; everything else is **generated on demand** or **enforced by CI** — because prose rots silently while
code and checks fail loudly. **Three-tier memory invariant** every skill obeys:
- **VOLATILE** — rewrite freely each iteration (`state.json`, `handoff.md`).
- **STABLE** — change only in the **same item as the code that changes it**, CI-gated (`spec/`, diagrams).
- **APPEND-ONLY** — supersede, never edit (`decisions/`, the audit / `# Sessions` stream).
*Rejected:* undated prose docs a human must refresh (the observed rot); Diátaxis's four-quadrant tree
(multiplies surface a loop must keep in sync). *Evidence:* best-practice research (primary: ADR immutability,
CLAUDE.md size discipline, docs-as-code) + the `idea-testing` rot pattern (empty `diagrams/`, undated
research, documented-not-enforced `logging.md`). → `05`, `06`, `shared/memory-model.md`, `07`.

## D39 — Space-6 split: generated structure vs experiential memory **[DECIDED — sharpens D13]**
The two halves of Space 6 sit on opposite sides of D38's law. **Structural code graph = GENERATED**
(tree-sitter/repomap, regenerable, never authoritative prose, never hand-edited — a hand-maintained map goes
stale and lies). **Experiential per-file memory = the only durable hand-written layer** (the non-derivable
`why` + the `# Sessions` postmortems). Names the boundary D13 already leaned toward.
*Rejected:* a hand-maintained structural map; Code Property Graph as agent context (overkill — security-scan
step only). *Evidence:* Aider repomap (generated → cannot drift) + research. → `06`.

## D40 — Baseline rules + `/start` enforcement wiring **[DECIDED]**
The package ships a **thin baseline `rules/`** (code-style / testing / security / ops — *principles only*, not
workflow-kit's volume); projects override via **nearest-file-wins** (package < project < path-scoped).
`/start` **specializes** them per project **and wires the enforcement layer** — `.editorconfig`,
linter/formatter/typechecker config, test runner, and the **CI/hook gates** that make enforceable rules fail
loudly. The orchestrator `CLAUDE.md` (≤~200 lines) holds only non-enforceable behavioural guidance, governed
by the deletion test (*"would removing this line cause a specific mistake? if not, cut it"*). Discipline is
mostly **CI-enforced, not prose** — closes the day-one "no baseline guardrail" gap.
*Rejected:* shipping all discipline as prose (the documented-not-enforced rot); folding everything into
`CLAUDE.md`. *Evidence:* Google eng-practices (nearest-file-wins) + Cursor/Claude rules conventions +
`idea-testing` `logging.md` rot + user. → new package `rules/`, `commands/start`, `10`; complements D34.

## D41 — Diagrams-as-code + loop-owned freshness + prune pass **[DECIDED — mechanisms closed by D61]**
Architecture diagrams are **Mermaid C4 L1/L2 inline** in the architecture doc, updated by `document` in the
**same item as the code** (skip L3/L4 — auto-generate the code level). Two freshness behaviours the loop owns:
**staleness must be machine-detectable** (not a date a human forgets) and a periodic **prune pass** (deletion
test over `CLAUDE.md` + `rules/`) in the audit phase — bloat makes the agent ignore its own instructions. The
two **mechanisms are OPEN** (`07`) — decided that they exist, not how.
*Rejected:* separate `.mmd`/binary diagram tools (don't diff); human date-stamps; hand-maintained C4 code
level. *Evidence:* C4 + Mermaid-in-GitHub + the empty `idea-testing` `diagrams/`. → `skills/document`, `06`,
`07`.
*Closed by D61:* the prune-pass + staleness-detection mechanisms are cap-and-archive + a script/LLM-split
`audit` pass; distillation deferred.

## D42 — Plan risk-class + Backup contract **[DECIDED]**
The `plan` carries **`risk_class`** ∈ `{code-only, data-additive, data-destructive, prod-touching}` and, when
destructive, a required **`backup`** block (what / mechanism / verification / restore). `planner` sets the
class; `execute` **refuses** a destructive plan with no verified backup, runs+verifies the backup **before**
the destructive step, and records it. The **local-irreversible** twin of D35 (which gates only outward
actions) — an unattended executor must not run a `DROP`/migration without a proven rollback.
*Rejected:* relying on D35 (covers push/`gh`, not a local destructive op); operator confidence as the gate.
*Evidence:* workflow-kit `risk_class`/Backup, sharpened for unattended execution + user ratify. →
`shared/schemas.md` (plan), `skills/planner`, `skills/execute`.

## D43 — Decision-coverage gate **[DECIDED]**
`planner` cross-checks that **every decision** in the item's decision records maps to **≥1 plan step**; an
unmapped decision **blocks/escalates** the plan. The `plan` gains a `decisions[]` reference so coverage is
machine-checkable; the records live in the product's append-only `decisions/` (D38). Stops resolved intent
from silently evaporating between `discuss`/`decision-engineer` and `execute`.
*Rejected:* trusting decisions to survive into the plan implicitly. *Evidence:* GSD decision-coverage gate +
user ratify. → `shared/schemas.md` (plan), `skills/planner`; connects D24 (`document` ingests the decision
stream).

## D44 — Secret-scan gate in `commit` **[DECIDED]**
Before committing, `commit` scans the staged diff for high-signal secret patterns (key prefixes, private-key
headers, `password|secret|api_key|token` set to a non-placeholder literal); on a hit it **stops and
escalates** rather than committing. An autonomous committer needs this more than a human one — a committed
secret lives in history forever.
*Rejected:* trusting the executor never to stage a secret. *Evidence:* workflow-kit `commit` secret scan +
user; fits D32/D35. → `skills/commit`.

## D45 — Conjunction-of-signals for AI judges **[DECIDED]**
In `adjudicate`: an LLM verdict **gates** (fail/block) only when a **deterministic signal corroborates** it (a
failing test, a thrown error, a lint/type violation, a tree mismatch); an AI-only finding is **advisory /
low-confidence**, never a hard gate. Propagates to `verify` / `debug` / `decision-engineer` (which specialize
`adjudicate`, D24). False-positive control so AI judgment alone can't stall or whipsaw the loop.
*Rejected:* AI-verdict-alone gating. *Evidence:* workflow-kit `verify-ui` conjunction rule, generalized +
user ratify. → `skills/adjudicate`; strengthens D24's confidence-gate.

## D46 — Orchestrator `CLAUDE.md` = the launch-root brief; advisory backbone + hooks enforce **[DECIDED]**
The package's driver is the target project's **root `CLAUDE.md`** (Claude Code's always-loaded,
post-`/compact`-re-injected brief) — "orchestrator" names its *role*, not a separate file; the always-loaded
session at the launch root **is** the orchestrator. Written lean (a frame, not the per-capability *how*), it
encodes: identity + three-layer memory (D4), a pointer to the loop, the read→place→advance control algorithm,
the invariants, checkpoints, handoff. Because `CLAUDE.md` is **advisory context, not enforced configuration**,
the loop *sequence* runs model-on-rails while the **non-negotiable invariants become deterministic hooks**
(no commit before `verify` passes; secret-scan D44; outward-action gate D35; build-once-per-wave D36) — the
brief marks which lines are hook-enforced vs disposition. Exempt from `shared/format.md` (it is the
always-loaded brief, not a typed node) but shares the voice + carries no spec-internal refs (D34).
*Rejected:* `CLAUDE.md` prose as enforced control flow (Claude treats it as context, not config); a
workflow-script driving the whole loop (poor fit for a long-running human-in-the-loop session).
*Evidence:* Claude Code docs (CLAUDE.md advisory; hooks enforce; root survives `/compact`); industry —
hard-code routing, LLM inside nodes (Anthropic *Building Effective Agents*, LangGraph, Step Functions,
Temporal); + user ratify. → `01`, `commands/start.md`, future `hooks/`.

## D47 — Loop graph lives in a pointed-to file; definition vs position **[DECIDED]**
The routing graph (nodes + pass/fail edges + Mermaid diagram) is the single source of truth in
**`.workflow/loop.md`**; the root `CLAUDE.md` carries only a **pointer** and the orchestrator **reads it on
demand** to route. The pointer (plain text) survives `/compact`; the file is read fresh — so we never depend
on `@import` re-resolution (undocumented). Split **definition** (the fixed topology — STABLE) from
**position** (`state.json` — volatile); `loop.md` never accumulates run-history. Each skill keeps a
**one-line local `Route`** (its own successors, self-description); `loop.md` owns the global graph; `10`
stays a design doc, not loaded at runtime.
*Rejected:* inlining the full graph in `CLAUDE.md` (triple-maintenance vs `10` + skill `Route`s);
`@import`-ing the graph (compaction re-resolution undocumented); stripping `Route` from skills (breaks D31
format, makes skills non-self-describing).
*Evidence:* single-source-of-truth for the graph (LangGraph `StateGraph`, Step Functions ASL, Airflow DAG);
Claude Code `@import` is eager + 4-hop but compaction behaviour unconfirmed; + user (his "point at a live
graph file" proposal). → `01`, `05`, `.workflow/loop.md`.

## D48 — Resume/state model: volatile pointer + durable anchor + git log **[DECIDED]**
"Where am I in the loop" splits per durable-execution practice: **`state.json`** = the volatile live pointer
(item / phase / wave; gitignored console view, rewritten in place); **`handoff.md`** = the durable resume
anchor (program counter — current item + loop position + parked work, committed); **git history** = the
append-only completed-step log (each item ends in a `commit`, D32). Mid-run reads `state.json`; a cold start
reads `handoff.md` + `git log` and rebuilds. Replay is idempotent — `prioritize` (pure queue, D26) never
re-picks a committed item.
*Rejected:* `handoff.md` only (conflates console view + anchor, loses live state); `state.json` only
(gitignored — not durable across clone/machine, too fragile as the authority).
*Evidence:* Temporal event-sourced history + replay; LangGraph checkpoint `next` pointer + idempotency keys;
Martin Fowler event sourcing; + user ratify. → `01` (session lifecycle), `05`.

## D49 — Per-mode repo layout; the launch-root constraint **[DECIDED — docs-root sliver closed by D62]**
Only the **launch-root `CLAUDE.md`** (and parents) is always-loaded + re-injected post-`/compact`; a subdir
`CLAUDE.md` loads on-demand and is not restored. So the orchestrator brief must be the launch-root brief, and
layout splits by mode (D28/D29): **greenfield** — the launch root holds the orchestrator `CLAUDE.md` +
`skills/`/`agents/`/`commands/`/`loop.md`, and the product lives in **`project/`** with its own untouched
`CLAUDE.md`. **brownfield** — the product stays at the repo root (no relocation), the workflow machinery is
added in subdirs, and the orchestrator framing is a marked block in their root `CLAUDE.md` (D50). A committed
**`.workflow/config.json`** carries `project_root` (`./project` | `.`) so code-touching skills stay
path-agnostic.
*Rejected:* always-product-subdir (relocating a live brownfield repo breaks paths/CI + nested-git friction);
always-flat-root + marked block (gives up the clean greenfield `CLAUDE.md` separation).
*Evidence:* Claude Code load/compaction hierarchy (only launch-root re-injected); + user (his `workflowdir/`
+ `project/` proposal) + ratify. → `commands/start.md`, `05`, `10`.

## D50 — Brownfield `CLAUDE.md` install = inline marked self-gating block **[DECIDED]**
Integrating into a project that already has a root `CLAUDE.md`, `/start` **appends a sentinel-marked block**
to it (inline = guaranteed `/compact` survival), idempotent on install/update/uninstall via the markers,
never touching user content. The block **self-gates** ("act as orchestrator only when a run is active; else
an ordinary session") so casual human sessions in the repo aren't hijacked. The existing `CLAUDE.md` is also
read as a **primary ingest source** for `rules/` + the reconstructed `spec/` (highest-signal artifact in the
repo).
*Rejected:* `@import`-ing a separate orchestrator file (cleaner separation, but compaction re-resolution
undocumented — too risky for the bootloader; kept as a cheap one-session test to adopt later); always-on
(no self-gate — intrusive on a shared repo).
*Evidence:* root text survives `/compact` (confirmed) vs `@import` (unconfirmed); marked-block idempotency
precedent; + user. → `commands/start.md`, `06` (ingest).

## D51 — Always-read files bounded by construction; retention law deferred **[DECIDED — retention closed by D61]**
The files the orchestrator reads **every turn** — root `CLAUDE.md`, `state.json`, `handoff.md`, `loop.md` —
are **rewritten in place, never appended to**: current state only, no history, within a small size budget
(history lives in git). The master rule (context is scarce, D3) applied to disk. The complementary
**retention & archival law** for the genuinely unbounded set — the **append-only** tier (`decisions/`, the
`# Sessions` stream), plus indexed retrieval for large `.knowledge/`/`spec/` — is
**deferred to its own pass** and **closes D41** (prune-pass + staleness mechanisms); the cheap archive is
rollup-and-link with git as the cold store.
*Rejected:* letting any always-read file accumulate history (fatal to context).
*Evidence:* master rule (D3); D38 tiers (only append-only grows unbounded); + user (raised the growth-bound
concern). → `shared/memory-model.md`, `01`; OPEN → `07`/D41.
*Amended by D59:* `backlog.md` reclassified as a live open queue (closed items leave, GC'd by `prioritize`) —
removed from the append-only retention set above; only `decisions/` + the `# Sessions` stream remain unbounded.

## D52 — Orchestrator dogfood: the driver is validated **[DECIDED — validated]**
A throwaway greenfield repo (`~/Documents/dogfood-orchestrator`) was scaffolded with the package + authored
`CLAUDE.md`/`loop.md`/`config.json`, and Claude **drove it as the orchestrator** (design-drive simulation)
across two tasks — a happy-path feature (G1) and a fail/decision feature (G2). The `read → place → advance`
control algorithm held across **both** the happy path and the failure/decision/human-gate paths
(`decision-engineer → research → decision-record`; `verify-fail → debug → refine → planner → execute →
re-verify-pass`; a real qa `checkpoint`; `create-issue → close-issue` with outward gating). Confirmed live:
the loop-graph pointer (lean `CLAUDE.md` + on-demand `loop.md`); the resume model (cold-start reconstruction
from `handoff.md` + `git log`); gitignored `state.json`; plan-declared QA (D30 — G1 no checkpoint, G2 one);
conjunction-of-signals (D45 — a real `KeyError` gated, not an AI hunch). Surfaced findings → **D53–D57**.
*Evidence:* two-task simulation, real Bash/edits/commits (3 clean commits). → `10` build status.

## D53 — Disk layout + artifact/state schemas (dogfood) **[DECIDED]**
Closes `schemas.md`'s "paths TBD." **Per-item working artifacts** live under `.workflow/items/<id>/`
(`plan.md`, `changelog.md`, `verdict.md`, `debug-report.md`); **per-type append-only records** stay global
(`.workflow/decisions/`, `.workflow/checkpoints/`). The **resume contract** gets real schemas: `state.json`
`{ status, node, current_item, wave, note }` (`node` ∈ the `loop.md` node labels) and `handoff.md`
`{ current_item, loop_position, parked[] }`. Rule: per-item ephemeral artifacts are item-scoped; cross-item
memory is type-scoped.
*Rejected:* a flat `.workflow/` (plan/changelog/verdict collide across items); leaving paths TBD (resume needs
a defined `state.json`). *Evidence:* dogfood (had to invent `items/<id>/`). → `shared/schemas.md`, `05`.

## D54 — Item-tail ordering: bookkeeping rides the item commit **[DECIDED — amended by D66: a prerequisite-repair rides its own commit]**
The completion tail flips the backlog item → **done** and rewrites `handoff.md` **before** `commit`, so the
durable bookkeeping is captured by the item's own commit. (Sim-1 committed first and left them orphaned;
sim-2 with flip-first produced a clean tree.) `close-issue` is the one **post-commit** step (it needs the
commit SHA) and writes no loop-bookkeeping (see D55).
*Rejected:* commit-then-flip (orphans durable files); a separate bookkeeping commit (breaks
one-commit-per-item). *Evidence:* dogfood (clean vs dirty tree). → `01`, `10`, `skills/commit`.

## D55 — GitHub owns issue open/closed state **[DECIDED]**
The backlog `issue` carries only `github_ref` (+ local `kind`/`severity`/`source`); the **open/closed state
lives in GitHub**, not duplicated in `backlog.md`. So `close-issue` (post-commit) changes no local
loop-bookkeeping — it just closes the GitHub issue + comments the SHA. Removes the post-commit orphan and a
stale duplicate.
*Rejected:* mirroring `state ∈ {open,closed}` locally (duplicates state an external system owns → drift +
post-commit bookkeeping). *Evidence:* dogfood (the close-issue ordering snag). → `shared/schemas.md` (issue),
`skills/close-issue`, `skills/create-issue`, `shared/memory-model.md`.

## D56 — `decision-record` id + machine-checkable coverage **[DECIDED — sharpens D43]**
The `decision-record` gains an **`id`** (e.g. `D-001`); `plan.decisions[]` holds those ids; the D43 coverage
gate checks each id maps to ≥1 step. Makes the decision↔plan link real, not convention.
*Rejected:* referencing decisions by prose/title (not machine-checkable). *Evidence:* dogfood (the plan's
`decisions:[D-001]` had no id field to point at). → `shared/schemas.md` (decision-record, plan).

## D57 — Package install location for MVP **[DECIDED — partial]**
The capability package installs as **loose `.claude/` files** in the target — `.claude/commands/`,
`.claude/skills/<name>/SKILL.md`, `.claude/agents/<name>.md` — so `/start` + skills are harness-discoverable;
`shared/` co-locates and is referenced by relative path. Resolves the D25/D49 "at the launch root" ambiguity
for MVP. **Open:** plugin packaging (`.claude-plugin/plugin.json`) + robust `shared/` resolution.
*Rejected:* package dirs at the bare repo root (Claude Code discovers commands/skills under `.claude/`).
*Evidence:* dogfood install. → `10`, `commands/start.md`; OPEN → `07`.

## D58 — Autonomous permission model: shipped allowlist + `ask` gate + guard hook **[DECIDED]**
The harness-real `/start` ran but **prompted constantly for routine local actions** (fatigue) and **pushed to
`origin/main`** — the outward gate (D35) wasn't enforced (advisory prose only), so it collapsed into the same
prompt stream and got approved. Both are one problem: permission-prompts as the *only* enforcement. Fix
(Claude Code best practice): the package **ships `.claude/settings.json`** with `permissions.allow` **broad for
local** work (`Bash` + `Edit`/`Write`/`Read` + `Task`/`Web*`) → prompt-free, and a **thorough `ask` list** for
**outward** actions (`git push`, `gh`, publish/deploy/cloud CLIs, `ssh`/`scp`/`rsync`, `curl`/`wget`) → a
deliberate gate. (Broad-allow chosen over an enumerated safelist because per-toolchain enumeration can't
anticipate every project and `cd x && cmd` chaining defeats prefix-matched allows.) Precedence is **deny > ask > allow**,
so local runs silently while outward always asks — exactly D35, *without* full bypass. The "never do this"
gates become a **PreToolUse hook** (`hooks/guard.sh`): **secret-scan** (block a staged secret) +
**verify-before-commit** (block a commit whose item's verify failed) — legitimate hard-blocks (exit 2, which
overrides allow and fires even under bypass). `/start` surfaces a **one-time message** (accept the
workspace-trust dialog; outward stays gated; you don't need `--dangerously-skip-permissions`). Modes are
**user-controlled** — a `CLAUDE.md`/command cannot set them, so `/start` only recommends.
*Rejected:* recommending full `--dangerously-skip-permissions` (auto-approves outward → destroys D35);
hard-blocking `git push` in the hook (kills the approve-and-push flow — outward is an *ask*, not a forbid);
leaving gates as advisory prose (the run pushed). *Still open:* **build-once-per-wave** (a wave-coordinator,
not a command gate) and **outward gating under full bypass** (needs the console/bus checkpoint-queue).
*Evidence:* dogfood `/start` (constant prompts + a push to `origin/main`); Claude Code permission/hook docs
(deny>ask>allow; hooks precede + override permission rules; modes user-controlled). → `commands/start.md`,
`templates/settings.json`, `hooks/guard.sh`, `01`, `10`, `07`; realizes D46, protects D35.

## D59 — Write-law leak closures (Layer 0 of the retention pass) **[DECIDED]**
Before the retention *read* law (D41) can land, the *write* law (D38) had unwired leaks — append-only
artifacts with no writer, no on-disk home, or no stated write-mode. A three-agent doc-surface sweep mapped
them; closed as one set:
1. **Per-item dirs are created on demand.** `planner` (plan-one) `mkdir`s `.workflow/items/<id>/` when it
   writes the first per-item artifact (`plan.md`). `start.md` cannot scaffold `items/<id>/` — no `<id>`
   exists at init and git ignores empty dirs — so it scaffolds only the `items/` *role*, not an instance.
2. **`backlog.md` is a live open queue, not append-only** (corrects D51). Rewrite-in-place; closed items
   **leave** — `prioritize` GCs at pick time (drops roadmap items `commit` flipped done; filters `issue`
   entries whose `github_ref` is closed), honoring D55 (close-issue still writes no local bookkeeping). It is
   read on-demand by `prioritize`, bounded by open-WIP, not by age.
3. **`research` heavy notes are ephemeral scratch** with no durable home — the durable distillate is the
   caller's record (`decision-record` `why`+`sources[]`, or `debug-report`); notes are discardable (the
   `create-demo` throwaway pattern). No new durable surface.
4. **`document` owns the architecture doc** (inline Mermaid-C4 L1/L2), updated same-item — D41 named it owner
   but `document` never wrote it. The step is **location-agnostic** (the doc's home is the open docs-root
   question).
5. **`schemas.md` hygiene:** a **write-mode + tier** line per schema (cross-linked to `memory-model.md`) and a
   `config.json` schema; `debug-report`'s durable form is named as the per-file `# Sessions` entry; the
   `# Sessions` log is **per-file sections**, not one global stream (fixes `05`/`11` wording); the ghost
   `log.md` (Karpathy lineage in `06`) is dropped — its role is the per-file `# Sessions`.
*Rejected:* adding `items/<id>/` to the static scaffold (id is runtime, not init-time); keeping `backlog.md`
append-only (D51's lump — closed items grow it forever); a durable home for research notes (duplicates the
`decision-record`). *Evidence:* the three-agent sweep — every age-growing artifact unbounded; `checkpoints/`
and the architecture doc had **zero** writers; `items/` referenced everywhere but never scaffolded. →
`shared/schemas.md`, `shared/memory-model.md`, `05`, `06`, `11`, `skills/{planner,prioritize,document}`,
`agents/research`, `commands/start.md`; amends D51; precedes the D41 retention law (Layer 1 — closed in D61).

## D60 — `checkpoints/` demoted to reserved; disposition deferred to the outward-permission model **[DECIDED — defer]**
`.workflow/checkpoints/` was an orphan — listed as a durable append-only dir, but **no skill writes it**
(`checkpoint` only posts to the bus and blocks). Its disposition is **not a retention question**: qa/demo
verdicts are disposable (the consequence is already in git on pass / `# Sessions` on fail), but **setup /
publish-approval** verdicts are *outward-action approval events* the open outward-permission model (D35, `07`)
may want as a **durable approval ledger**. Deciding persist-vs-drop now would pre-empt that model. So
`checkpoints/` is **demoted to reserved** (writer + retention TBD), pulled out of the retention-bound set, and
its disposition folds into the outward-permission pass — whatever persists there carries its own retention rule.
*Rejected:* dropping it now (discards a possible outward-action audit trail before the model that needs it
exists); keeping it active-but-unbounded (the orphan we are fixing). *Evidence:* the skills sweep (`checkpoint`
writes only to the bus; `checkpoints/` has no writer). → `05`, `commands/start.md`, `shared/schemas.md`, `07`
(outward-permission model, D35).

## D61 — Retention/read law: cap-and-archive + mechanical/judgment split **[DECIDED — closes D41]**
The append-only tier is bounded by **read-cost** (what loads per pass), not disk — the working tree is a
**bounded cache; git is the ledger**. Closes D41's open mechanisms. Two moves:
**(1) Bound = cap-and-archive, NOT distillation.** Keep the last *K* raw entries on disk; drop older ones to
git (the file carries a one-line archive pointer). Bounds the read with **zero judgment** — counts, moves,
deletes. Per stream: **`# Sessions`** (per node) caps last-K raw + a deferred `Lessons` zone, oldest → git;
**`decisions/`** keeps a VOLATILE `index.md` (`id · title · status · one-line`) + active bodies, superseded
bodies dropped to git (tombstone in the index); **`items/<id>/`** stays committed while the item is open
(crash-survival) and the dir is **pruned once closed** in the audit pass (essence already moved:
debug-report→Sessions, decisions→`decisions/`, diff→git); the **`git log` cold-start read** is bounded by
recording `base_sha` in `handoff.md` and resuming `<base_sha>..HEAD` (one session's delta, not project age).
**(2) Mechanical vs judgment split.** The four caps are **deterministic → a shipped retention script**; only
the D41 **deletion-test over `CLAUDE.md` + `rules/`** needs an LLM. Both run in an **`audit` maintenance item**
that `prioritize` injects when a **count/size threshold** trips (machine-detectable) or every *N* items. So
retention is **enforced** (a script), not advised — D40 applied to disk hygiene. **Sessions distillation**
(postmortems → lessons) is the lossy, model-authored part and is **DEFERRED** — cap-and-archive bounds the read
without it; distillation is a later signal-quality feature.
**Prerequisites (deltas):** `decision-record` gains `status` + `supersedes`/`superseded_by`; `handoff.md` gains
`base_sha`; nodes gain an archive-pointer line; the `# Sessions` entry format is **strict/lint-parseable**
(`## [date] kind | title`) so the script can split entries.
*Rejected:* shipping distillation in v1 (model-authored compression of safety memory — high leverage if wrong);
handoff git-tags (per-item handoff → tag explosion, D54); an LLM doing the mechanical file-surgery (a script is
more reliable for memory removal). *Open:* exact `K`/thresholds (build-time tuning); authoring the script
(depends on the format/fields landing); `decisions/` final location (docs-root pass) — the design is
location-agnostic. *Staleness* (a doc that's *wrong*, not *big*) stays a separate diff-based signal that
schedules a doc-fix, not a prune. *Evidence:* the Layer-0 sweep (only append-only grows unbounded); D38 tiers;
D40 (mechanical→enforced); D54 (per-item handoff). → `shared/memory-model.md`, `shared/schemas.md`, `05`, `06`,
`skills/{document,prioritize}`, `11`, `07`; closes D41; built on D59–D60.

## D62 — Unified docs-root under `<project_root>/docs/` **[DECIDED — closes D49's sliver]**
Decides the four docs-root forks from first principles. **(1) Unify + locate:** `spec/`, the code-map, and the
inline-C4 `architecture.md` live under one **`<project_root>/docs/`** root, in **both modes** — because the
launch-root↔`project_root` line *is* the process↔product line (`.workflow/` = how it was built, `docs/` = what
was built + why), and because **brownfield forces `project_root`** (a repo's docs go in its own `docs/`), so
consistency forces greenfield to match (one rule, resolved via `config.json:project_root`). The purity counter
dissolves: extracting `project/` yields a *self-documented* product (code + spec + architecture + code-map)
while `.workflow/` — the only machinery — stays behind. Nothing in `docs/` is always-loaded, so depth costs no
hot-path context (D49/master rule). **(2) `decisions/` joins → `docs/decisions/`:** decision records are
**ADRs** (durable "why" = non-derivable intent, D38), and D38's own evidence base is ADR-immutability +
docs-as-code; they're product knowledge, not run bookkeeping, so they move docs-side while **`checkpoints/`**
(run-approval events) stays in `.workflow/`. **(3) Un-hide `.knowledge/` → `docs/knowledge/` (visible):** half
of it is the *durable hand-written* layer (D39), not pure machine output, and docs-as-code wants it reviewable
in PRs; the dotfile misrepresented it. **(4) `llms.txt` stays a thin root manifest** at `<project_root>/llms.txt`
(the convention is a root entry point) pointing **into** `docs/knowledge/` — progressive disclosure.
**Brownfield rule:** ingest **adopts-and-merges** into an existing `docs/` (write members to known subpaths,
never clobber; namespace ours on a name collision). `/start` scaffolds an empty `<project_root>/docs/` at init
so `discuss`'s spec has a home before code exists.
*Rejected:* docs at the launch root for greenfield (splits the rule across modes — brownfield can't); leaving
`decisions/` in `.workflow/` (an ADR is product knowledge, not machinery); keeping `.knowledge/` hidden
(implies untouchable, but it's half hand-written); burying `llms.txt` under `docs/` (breaks the root-manifest
convention). *Evidence:* D38 (docs-as-code + ADR immutability), D39 (hand-written experiential layer), D49
(per-mode, path-agnostic via `config.json`), master rule (on-demand → no hot-path cost). → `05`, `06`,
`commands/start.md`, `templates/orchestrator-CLAUDE.md`, `shared/{schemas,memory-model,format}.md`,
`skills/{document,execute,prioritize}`, `07`, `11`; closes D49's docs-root sliver.

---

## Alignment-scan pass (session 2026-07-01)

## D63 — Alignment scan: scan-first, then a knowledge-gated lightweight-fan-out skill **[DECIDED]**
The maintainer's "are the docs + planning aligned with the implementation?" concern is realized as a
whole-project reconciliation between the design docs + decision log and the shippable package. Two-part call:
**(1) run it first as a manual, one-off multi-agent scan** and **derive the skill from what the run teaches** —
the fan-out decomposition and the finding schema are discovered empirically, and a *complete* skill can't be
authored before knowledge generation exists anyway; **(2) the eventual skill is knowledge-gated and ships as a
lightweight agent fan-out, NOT a Workflow** — a periodic, every-project scan must not consume most of a user
session (a full Workflow is acceptable only for a one-off on our own repo). Method: **bidirectional** (the
decision log as a top-down checklist + a filtered bottom-up file sweep); each divergence classified by the
**commitment model** (locked → drift/bug · provisional → finalize-later · unspecified → steering), known tracked
gaps excluded; candidates **adversarially verified** before they count. Scheduled by the D61 `audit` trigger
(interval / threshold / after-big-change); detection is the backstop, prevention (D64) shrinks the drift upstream.
*Rejected:* skill-first (the fan-out shape is exactly what the run discovers, and a pre-knowledge-gen skill is a
stub to rewrite); a Workflow-based shipped skill (too costly for a periodic user-run scan).
*Evidence:* the 2026-07-01 run — 8 area finders + a 2-lens adversarial verify, 15 confirmed findings — surfaced a
systemic regression (D64) no eyeball pass had caught. → `11`, `06`, `09` (relates to the project-state view +
self-hosting); complements `document` freshness + brownfield `ingest`.

## D64 — No-spec-internal-refs extended to the whole package + mechanically enforced; four body fixes **[DECIDED]**
The alignment scan (D63) found a **systemic regression**: the D59–D62 doc-surface capture pass (commit
`852179e`) reintroduced **52 spec-internal reference lines** (31 `Dxx` tokens + doc-numbers + `Space N`) into the
shippable package — violating locked D34 because **D34 was advisory prose with no gate** (the project's own
D38/D40 thesis — prose rots silently, only checks fail loudly — demonstrated on itself). Calls:
- **Scope:** D34's no-refs rule covers the **entire shipped package** (`skills/ agents/ shared/ commands/
  templates/ hooks/`), not just the three dirs D34 literally named — `commands/start.md` + templates are
  runtime-loaded, so the same rationale applies (extends D46). The numbered design docs + decision log keep their
  refs (they are the down-pointing provenance).
- **Enforcement:** a committed **grep gate** (`scripts/check-no-spec-refs.sh`) fails on any leak — D40 applied to
  the meta-repo (mechanical, not advised).
- **Four fork resolutions:** `discuss` owns spawning provisional → debt tickets on the **no-demo path** (closes a
  D23 coverage hole; `create-demo` owns the demo path); `planner`'s ungoverned ~200k **session-split rule cut**
  (context exhaustion is the handoff model's job, D10/D48); `verify`'s "skippable" **narrowed** to
  skip-the-fan-out-not-the-step (D30 makes the step unskippable); the orchestrator brief **corrected** to separate
  hook-enforced gates (verify-before-commit, secret-scan) from the permission-rule outward gate from the
  **deferred** build-once-per-wave (it was mislabeled as an uncrossable hook gate no hook enforces).
- **Prevention follow-ons (OPEN → `07`):** **single-source status** (kill "done/open" duplication across
  roadmap/roster/bodies — the root of the stale-status findings) and a **capture-time blast-radius sweep** for
  cross-cutting decisions (the root of the topology/owner/over-claim findings).
*Rejected:* leaving D34 advisory (the observed regression); auto-fixing findings from AI-only judgment (D45);
relaxing D34 to allow provenance breadcrumbs in the package (leaks design artifacts into runtime context, wastes
tokens). *Evidence:* git-traced to `852179e` (+31 `Dxx`); the gate now reports zero. → `shared/format.md`,
`scripts/check-no-spec-refs.sh`, the affected package files, `10`, `11`; closes scan findings #1–15; complements
D34/D40/D46.

## D65 — Two-tier drift defense: mechanical auto-fix at the gate, semantic drift → ticket → `prioritize` → the existing loop **[DECIDED]**
Keeping docs aligned with code splits by the mechanical-vs-judgment law (D61), and **both tiers feed the normal
queue rather than blocking** (the loop never stalls):
- **Mechanical tier (per commit):** a deterministic checker (the `scripts/check-no-spec-refs.sh` no-refs gate,
  plus project lint/format/dead-node) runs at commit time and **auto-fixes what a script can fix with zero
  judgment** (strip a leaked ref, reformat), re-checks, and lets the commit proceed — and **logs what it fixed**
  (no silent masking of the upstream generator, per D59). It runs as a step in `commit` (visible in the loop)
  with a **git pre-commit hook** as the human/catch-all backstop, both calling the same script. Hard blocks stay
  reserved for the never-want-irreversible class only — secrets + committing over a failed `verify` (the existing
  `guard.sh` gates).
- **Semantic tier (judgment):** drift a script can't safely fix (a stale/contradictory/over-claimed doc, a
  missing owner) is **never auto-resolved inline** — an unreviewed commit-time agent deciding *which side is
  right* can "fix" in the wrong direction and launder a code bug into resolved docs (foreclosed by D45/D64).
  Instead the detector files a `create-issue` ticket into `backlog.md` with the evidence, **severity set from the
  commitment-class** (a locked contradiction rides high so it isn't starved; cosmetic drift sits as low `debt`).
  The **authority call is deferred to remediation:** `prioritize` schedules the ticket in normal urgency ×
  dependency order (D26), and the fix runs through the **existing loop** — `decision-engineer`/`adjudicate`
  decides authority (locked → fix the code · provisional → finalize · unspecified → **steering to the human**),
  then `planner` → `execute`/`document` → `verify` → `commit`. **No new agent.**
- **One queue, two detectors:** the fast per-commit gate and the periodic alignment scan (D63) are
  shallow-vs-deep detectors that file tickets the same way, so all drift converges on one backlog.
*Rejected:* hard-blocking doc drift (stalls the loop — hard blocks are only for the never-want-irreversible
class); auto-resolving authority inline at commit (an unreviewed AI guess that can mask a code bug — D45/D64); a
standalone **docs-engineer** agent (its sub-roles are already owned — detection by the D63 scan + `research`
readers, authority by `decision-engineer`, the edit by `execute`/`document`; a specialized doc-authoring worker
is **reserved** for heavy generative reconstruction, e.g. brownfield `ingest` spec-from-code, and added only if
the generic workers prove insufficient — `07`).
*Evidence:* this session — the alignment scan surfaced the drift, and the discussion turned on remediating it
without stalling or laundering code bugs. Builds on D63 (scan), D26 (pure queue), D40 (mechanical → enforced),
D45 (no AI-only action), D23/D64 (commitment-based authority), D33 (`create-issue` → backlog). →
`skills/{prioritize,commit,decision-engineer,execute,document}`, `hooks/`, `scripts/check-no-spec-refs.sh`,
`07`, `11`; extends D40's enforcement wiring; complements D63.

---

## Phase 1 build — skill-body deltas (session 2026-07-01)

The decided-but-unwritten D36–D45 deltas were authored into the shippable bodies (`prioritize` waves;
`execute` divergence tiers + refuse-destructive; `planner` `risk_class`+`backup` + decision-coverage gate;
`adjudicate` conjunction-of-signals, with `verify`/`debug` nods; `commit` secret-scan). `schemas.md` already
carried the fields, so this was body prose, not schema work — except one gap surfaced below. Scope call:
**pure D36–D45 now**, bodies written **forward-compatible** with the D65 gate (a light second pass on
`commit`/`prioritize` remains, tracked under the drift-defense wiring). The no-spec-refs gate stayed green.

## D66 — Prerequisite-repair rides its own commit; the divergence record gains a machine-actionable `tier` **[DECIDED — amends D54, sharpens D37]**
Authoring the deltas surfaced one genuine tension: D37 isolates a discovered **prerequisite-repair** as a
**separate commit**, but D54 fixed **one commit per item** and `execute` never commits (`commit` is a tail
skill). Resolution:
- The repair rides its **own** commit, **emitted by `commit` at the item tail** — not by `execute`, which
  stays commit-free and decision-free. An item that hits a prerequisite-repair therefore yields **two
  commits** (the isolated repair, then the planned change) — a **narrow carve-out to D54's
  one-commit-per-item**. Bookkeeping (the backlog done-flip + `handoff.md` rewrite) rides the
  **planned/completing** commit, after any repair commit.
- `changelog.divergences[]` gains a **`tier`** ∈ `{ cosmetic, prerequisite-repair, structural }` so the tier
  is **machine-actionable** — `commit` reads it to decide whether to split — rather than prose only `execute`
  understands.
*Why:* D37's point is that a stumbled-into fix stays **independently reviewable/revertible**, which a
call-out inside a bundled commit can't give. Keeping the commit in the `commit` skill (not `execute`)
preserves the **single-committer** design (Conventional-Commit formatting + the secret-scan gate live in one
place) and `execute`'s zero-decision/commit-free invariant. Typing the divergence stops a body naming a tier
the schema doesn't define — the exact doc↔implementation drift the alignment scan exists to catch (D64).
*Rejected:* one commit per item with an in-message call-out (weakens D37 — no independent revert, and edges
toward the fold-in D37 rejected); `execute` committing the repair itself (duplicates commit formatting +
secret-scan into the executor, breaks its commit-free invariant); leaving the tier as prose only
(unactionable → drifts). *Evidence:* this session — the delta-authoring pass; user picks (separate-commit for
the repair · author the full wave model now · pure D36–D45 now). → `skills/{execute,commit}`,
`shared/schemas.md`, `templates/loop.md`, `10`, `11`; amends D54, sharpens D37, complements D64.

---

## Phase 1 build — rules baseline + enforcement wiring + drift gate (session 2026-07-01)

The decided-but-unwritten D40 (`rules/` baseline + `/start` enforcement wiring) and the D65 drift-gate wiring
were authored. Shipped: four thin **`rules/*.md`** (code-style · testing · security · ops — principles only,
each enforceable one carrying an `— enforced by: <mechanism>` tag that doubles as the wiring manifest); a
**rules-file convention** in `shared/format.md`; a new **`/start` step 4** that specializes the rules and wires
the enforcement layer (auto-write greenfield, adopt-and-gap-fill brownfield, externals → setup checkpoint); the
**mechanical-gate `commit` step** (auto-fix zero-judgment drift → log → proceed; semantic drift → `create-issue`
ticket, never resolved inline) and the **`prioritize`** note that drift tickets ride the normal queue at
commitment-severity. No schema change — the fields (`commitment`, issue `severity`/`source`, divergence `tier`)
were already carried. The new `rules/` dir was added to the no-spec-refs gate; the gate stayed green. One
mechanism call surfaced its own entry below (D67). **Brownfield boundary:** rules + enforcement are adopted
now; the docs → `knowledge/` ingest stays the tracked stub.

## D67 — The mechanical drift gate ships as a generated per-project `checks.sh`; the git hook is check-only **[DECIDED — sharpens D65, extends D40]**
Authoring the drift gate forced two mechanism calls D65 left open:
- **What ships downstream is not this repo's `check-no-spec-refs.sh`.** That script enforces *this package's*
  no-spec-refs authoring law — meaningless in a consuming project. The downstream mechanical checker is a
  **`/start`-generated `.workflow/checks.sh`**, built from the project's detected enforcers (format · lint ·
  typecheck · dead-link) — the single "same script" both callers invoke.
- **One runner, two modes.** `checks.sh --fix` auto-applies zero-judgment fixes, re-stages, and logs them —
  run **in-loop by `commit`** (visible). `checks.sh --check` fails non-zero on residual drift — run by the git
  **`pre-commit` backstop** for commits made *outside* the loop. The backstop **never silently rewrites** a
  human's tree; auto-fix stays in the visible loop step.
*Why:* D65 said "both call the same script" but left the script's provenance and the fix-vs-check split open;
naming a repo-specific gate as the downstream checker would ship an inapplicable check, and a git hook that
auto-fixes + re-stages would surprise a human's manual commit.
*Rejected:* shipping `check-no-spec-refs.sh` as the project gate (checks the wrong invariant downstream); a
single-mode script that auto-fixes everywhere (silent tree rewrites under a manual commit); putting the
auto-fix only in the hook (invisible to the loop). *Evidence:* this build pass — the no-spec-refs gate is
authoring-specific; the human-manual-commit case needs a non-mutating backstop. → `commands/start.md`,
`hooks/pre-commit.sh`, `skills/commit`, `scripts/check-no-spec-refs.sh`; sharpens D65, extends D40.

## D68 — Knowledge generation: own-script per-stack code-map, two centrality lenses, three-tier node seed; ingest seeds intent from `CLAUDE.md` **[DECIDED — sharpens D39, opens brownfield ingest]**
Pressure-tested on a real full-stack repo before deciding (D63 method — run first, derive the design). Calls:
- **The generator is an own script per stack, not an external tool.** `/start` emits a `.workflow/`
  code-map generator the way it emits `checks.sh` (D67): Python uses stdlib `ast`, other stacks tree-sitter /
  the native parser — regenerable, near-zero-dep, cheap enough to re-run freely (satisfies D39's "generated →
  cannot drift"). Rejected the two external candidates on evidence: `repomix` solves the *adjacent* problem
  (pack context for an LLM — signatures + token counts), not a typed import graph; aider-repomap does produce a
  PageRank import graph but is a heavyweight Python+LLM install to drag into every consuming project.
- **Layer 1 carries TWO labeled centrality lenses from one import graph — not a single "importance" rank.**
  *Impact* (forward PageRank: most-depended-upon → blast-radius, for `debug`/`planner`) and *orchestration*
  (reverse PageRank / fan-out: where flows compose → "where does feature X live"). Both fall out of the same
  extraction for free. Treating either as "importance" would mislead the loop — proven below.
- **Three-tier node seed makes "eager graph, lazy semantics" safe.** `[G]` generated-structural (path, type,
  edge targets, the lenses) for **all** files, eager; `[X]` cheap LLM-extractive `purpose.actual` + tags for a
  prioritized set; `[D]` the durable, non-derivable `why` / intent-vs-actual / `# Sessions` — authored **on
  touch** by `document`. A not-yet-touched node is skeleton + plausible purpose, **never an empty shell that
  lies** (the D38 rot the lazy path otherwise risks). `[D]` is the layer that earns its tokens — the product.
  **The `[X]` prioritized set = the union of *both* lenses (impact ∪ orchestration) plus the spec's declared
  core flows — never impact alone**, or seeding documents the plumbing and under-serves the behavioural core
  (the same miss the two lenses exist to prevent — the impact lens buried the engine + ingestion in the run
  below); and **no consumer treats a lens as "importance"** (`debug` → orchestration + impact; `planner`
  "where does X live" → orchestration). *Principle captured; the selection mechanism is deferred to
  implementation.*
- **Brownfield ingest is a thin `ingest` skill over existing leaves, and its first job is to seed
  behavioral-core intent from the existing `CLAUDE.md` / spec.** The product narrative and "what is core" are
  **un-derivable from code** (see evidence) — they live only in the human's prose. `ingest` drives `research`
  (read code + existing docs) → `document` (write nodes/graph/reconstructed spec); **no new agent** (the
  doc-authoring agent stays reserved, D65). Reconstructed spec defaults to **unspecified**, with a
  **reconciliation checkpoint** that locks only the load-bearing invariants the human confirms (avoids D23's
  finalize-ticket flood that all-provisional would cause on a large repo). Full structural graph eager; `[D]` +
  spec lazy with a prioritized seed.
*Rejected:* an external tool as the generator (wrong problem / too heavy — above); one "importance" ranking
(buries the behavioral core — evidence); eager `[D]` authoring (expensive, and unnecessary once `[X]` seeds
the gap); all-provisional reconstructed spec (backlog flood, D23); a new doc-authoring agent (reserved until
the generic workers prove insufficient, D65). *Evidence:* the 2026-07-02 run on a real repo (stock simulator,
225 source files / 805 intra-project edges): own-script `ast` produced the typed graph + PageRank in ~9s with
zero deps and zero parse failures; PageRank **diverged from naive in-degree** (`repositories/base.py` #1 over
`log.py` despite fewer importers → recursive centrality is real signal); **yet it buried the core the
maintainer named** — the simulation engine and ingestion logic ranked low, while the orchestration lens
surfaced exactly `simulation_engine/{run_lifecycle,advance_service}`, `ingestion/ingest`, and the run/advance
routes; the product narrative ("filter by sector/cap/volatility, drop into a random market moment, trade")
appeared in **neither** lens. → `06`, `commands/start.md`, `skills/{ingest,document}`, `10`, `11`, `07`;
sharpens D39, uses D67's per-stack-generator pattern, complements D62/D63.

## D69 — Proportional-rigor decision gate: a cheap triage in `planner` → tiered depth via `decision-engineer`; no back-eval **[DECIDED — implementation deferred to `11`; formalizes the engineering-feasibility pass]**
An autonomous loop removed the senior-dev gut-check that normally catches a bad *irreversible* decision in
review — so the loop needs to inject rigor on high-stakes calls **without** stalling the fast path or burning
tokens. Reframe that makes it principled rather than a budget hack: **rigor ∝ (cost-of-being-wrong −
cost-of-reversal)**, not rigor-vs-speed — even for free you would not validate a cheap-to-reverse decision, since
trying-and-reverting beats validating up front. Calls:
- **A cheap O(seconds) triage runs on EVERY `planner` output** — an inline checklist (no dispatch) grading
  reversibility × blast-radius × approach-ambiguity. Universal on purpose: it is the net for the **silent
  critical decision** that would otherwise be built at tier-0 because nobody flagged it as a decision. It assigns
  a **rigor tier**:
  - **Tier 0 — judgment.** LLM decides from its own knowledge; proceed. The default (~85–95% of outputs).
  - **Tier 1 — research.** Dispatch `research` to weigh standard/market approaches against project fit (bounded
    fan-out → synthesise). ~5–15%.
  - **Tier 2 — pressure-test.** Run a real experiment — but **only when critical AND a cheap empirical test
    exists**; else fall back to Tier 1 and record the residual risk. Rare.
  - **Escalate.** A genuinely ambiguous / product-shaping call is not "research harder" → a one-line steering
    question to the human (reuses the sandbox fence + the unspecified→steering rule).
- **The triage lives in `planner`, not `decision-engineer`** — `decision-engineer` only fires once a decision is
  *recognised*, and the whole point is to catch the *unrecognised* ones. `planner` triages, then escalates to
  `decision-engineer` at the chosen tier (extends planner's decision-coverage gate).
- **A mechanical floor + a backstop so the LLM triage need not be perfect:** the **impact-centrality lens**
  (D68's code-map) auto-escalates any decision touching a high-blast-radius node regardless of the model's gut
  (deterministic); the periodic **alignment scan** (D63) catches misses — prevention upstream, detection as
  backstop.
- **Record a prediction, don't run a back-eval.** At Tier 1/2 the `decision-record` gains
  `predicted_outcome` / `success_signal` — **recorded rationale** (ADR consequences), checked *opportunistically*
  by the alignment scan or a human, **not** by a per-item automated eval.
*Rejected:* a **post-implementation quality "eval"/back-gate** (an AI grading AI-written code is inherently
judgment → advisory-only per D45, overlaps `verify`/`code-review`/the alignment scan, and is a token sink — the
maintainer's point: it will never say "perfect, pass"); a **binary research yes/no** gate (misses the
proportionality — a ladder is right); putting the triage **in `decision-engineer`** (misses unrecognised critical
decisions — must be upstream); **always-pressure-test** (waste on reversible decisions even when free, and
unbounded time); a **separate engineer/feasibility agent** (roster bloat — the gate reuses the existing
hub-and-spoke). *Evidence:* this session — the maintainer ran a market-weighing research pass on
tree-sitter+PageRank in a separate chat (it *confirmed* the choice, and the **process** proved its worth even on
a confirm), and we pressure-tested the same decision empirically on a real repo (D68); the discussion generalised
both into one proportional-rigor gate, with D68's impact lens supplying the mechanical criticality signal.
Builds on D22 (cheap gate → expensive validation), D23 (unspecified→steering / the fence), D43 (planner
decision-coverage), D45 (AI-only → advisory), D63/D64 (detection backstop), D68 (impact lens). →
`skills/{planner,decision-engineer}`, `shared/schemas.md` (`decision-record` gains `predicted_outcome`), `07`,
`09`, `11`; **answers the open "engineer agent?" slot (no new agent) and formalizes the engineering-feasibility
pass.** Implementation deferred (`11`).

---

## D70 — Project map + flow view: a console tab over the code-map — static skeleton, dynamic overlay **[DECIDED — feature + architecture; the runtime-capture mechanism is a direction, tracked OPEN in `07`; the arm-vs-fallback coverage binary superseded by D72; the flow-overlay realised by D78; the *unauthed opt-in tunnel* arm superseded by D112 — remote access now requires a declared identity transport behind a two-socket split]**
The console gets a **project-map screen** rendering the code-map `graph.json` (D68) as a cluster diagram: nodes
sized by the **impact lens**, grouped by the **directory tree**, with **semantic zoom** (cluster → file →
[later] symbol). It is the structural face of the deferred **project-state view** (`07` — "how the pieces
connect") and a **self-hosting** aid. Free-text search over node paths/labels is a nice-to-have, not MVP. Calls:
- **Two layers, complementary — the flow view is an *overlay*, not a second graph.** The static map (always
  available, no run needed) is the skeleton; a **flow** ("watch a message get sent") is a **highlighted subgraph
  laid over it**, captured by **observing an actual run** — the union of nodes that execute during one exercised
  behaviour *is* the flow (empirical, not a guessed semantic slice). A trace is a **lower bound** (only exercised
  paths); the **orchestration lens** fills un-exercised branches.
- **Noise-filter protocol (direction).** A raw trace is dominated by framework/infra. Filter =
  **baseline-subtract** (action-trace − a null/unrelated-action trace) → **specificity-rank across flows** (a node
  in every flow = infra → demote; in one flow = characteristic → promote — an IDF that sharpens as more flows are
  captured) → **static-reconcile** against the orchestration lens (fill branches; flag characteristic-but-
  disconnected nodes as noise) → optional human trim (QA-harness pattern — machine-driven where possible, human QA
  only if necessary). Runtime differential tracing is a **working direction, not decided** — a static-slice
  approach may still win for some stacks; the trace tooling is a **per-stack arm** on the same discipline as the
  code-map.
- **Interaction = a scoped intake ticket, subject to D69 — never a privileged fast-path.** Clicking a node emits a
  **normal backlog item** (payload: node ID(s) + the ask) onto the existing loopback bus (`05`) — the decided
  "website talks to the orchestrator only via bus + files, never routes Claude" model. It rides the **same
  prioritization + proportional-rigor triage (D69)** as any work; the map is a *precision scoping aid for intake*,
  **not** an edit console — else it becomes a backdoor around the disciplined intake the project exists to enforce.
- **Three reserved seams (foundation must not foreclose the view).** (1) `graph.json` node IDs stay **stable +
  addressable** — today **relative paths at module granularity** (`type:"module"`); **symbol-level** addressing is
  the existing later seam (`11` Space-5/6), needed for fine-grained node-tickets/overlays and the "change how the
  timestamp renders" case. (2) A **reserved bus action** "node/subgraph → ticket" (`05`), UX deferred. (3) A
  **reserved flow-overlay layer** in the console data contract (`03`) — a labelled list of node IDs + edges the
  renderer can highlight. Build nothing now; reserve the seams.
- **Per-stack arm rule (resolves D68's "others follow").** No calendar trigger, no speculative arms. **(a)** the
  code-map has a **stack-agnostic degraded fallback** (directory tree + shallow import graph) so "no arm" ≠ "no
  map"; **(b)** a new arm is **demand-built** the first time a real target in that stack hits `ingest`/`/start`,
  against the fixed `graph.json` contract (both lenses, stable IDs); **(c)** the **Phase-4 demo forces exactly one
  more arm**, so we ship with ≥2 proving the contract generalizes. Same rule governs the trace-capture arm.
- **Remote control.** The console stays **local-served by default**; an opt-in **"remote control" mode** serves it
  over a temporary **Cloudflare tunnel** (already in `00`'s vision for QA phone-ping — one capability, two
  consumers). Tunneling breaks the loopback trust model (anyone who can POST can steer the orchestrator), so remote
  mode ships **off by default + an explicit "unsafe" warning now**; **auth (Cloudflare Access / token) is a
  reserved future requirement**, not built now (nothing important is wired to it yet → not worth targeting).
- **Undecided (→ `07`):** map as its **own tab vs the console home/overview**; a captured flow as a **first-class
  knowledge artifact** (versioned, regenerable, `06`) vs **ephemeral**; the capture **trigger/boundary** UX (leans
  on the QA harness).
*Rejected:* **algorithmic community detection** for clustering (unstable run-to-run, doesn't match devs' mental
model — directories are stable + self-labeling); **live browser→Claude routing** (violates the master rule +
`03`/`05` — the bus is a ticket channel, not a request path); **static-only semantic slicing** as *the* flow
mechanism (nothing in `graph.json` defines "the message flow" — observing a run is more grounded); a **privileged
node-ticket fast-path** (backdoor around D69); **pre-committing a language set** for arms (speculative — fallback +
demand-build is leaner). *Evidence:* the code-map already emits `graph.json` with both lenses (D68) and the WhatsApp
"dive into the message-send flow, then re-scope the timestamp render" case — the visualization is a read-out of an
artifact the knowledge space already produces, and the runtime-capture idea dissolves the semantic-slicing problem
by *observing* rather than *inferring* the flow. Builds on D68 (code-map + two lenses = the map's data), D69
(node-tickets ride the proportional-rigor triage), `03`/`05` (loopback bus, never routes Claude), `00` (tunnel
in-vision), the `07` project-state view (this is its "how pieces connect" face) + the `11` symbol-level seam.
**Feature + architecture DECIDED; runtime-capture mechanism a direction (OPEN in `07`); build deferred to Phase 2/3.**
→ `03`, `05`, `07`, `11`.

## D71 — Retention script built: the deterministic `audit` enforcer (shipped stdlib Python) **[DECIDED + BUILT — implements D61]**
The cap-and-archive retention law (D61) becomes an enforced artifact: **`scripts/retention.py`** (stdlib Python,
idempotent), shipped like the code-map extractor and run in the `audit` maintenance item. Four build decisions,
each the leaner of the alternatives:
- **Archive-state = an inline visible marker, not a manifest or frontmatter counters.** Correctness comes from
  *counting* entries > K, so a marker is needed only for human/PR traceability of what left the working tree: a
  one-line `<!-- retention: N Sessions entries archived -> git @ <sha> -->` at the **`# Sessions` head** (parsed
  back so N **accumulates** across passes), and a `docs/decisions/index.md` tombstone row `| id | title |
  superseded->X | git <sha> |`. No new file.
- **Closed-item prune is gated on a `document`-written `promoted.json` marker.** A mechanical script can't judge
  whether an item's essence was folded (debug-report→Sessions, decisions→`decisions/`); pruning a closed-but-
  unpromoted dir would destroy the only durable copy. So the prune touches **only** dirs carrying
  `promoted.json {promoted:true}`; unmarked → skipped. The safety gate is a fact `document` asserts, never a guess.
- **Thresholds are config-overridable with shipped defaults.** `config.retention` = `sessions_k` (the script's
  only knob) + the `prioritize` scheduling trips `decisions_active_n` / `items_closed_m` / `every_p_items`; absent
  → 10 / 30 / 10 / 15. Cheap now, avoids a retrofit when a real project wants different numbers.
- **Shipped-shared stdlib Python — not per-stack-generated, not bash.** Retention edits only our OWN stack-agnostic
  `.workflow/`+`docs/` layout, so per-stack generation (à la `checks.sh`/`codemap.sh`) buys nothing. Python over
  bash because the work is date-arithmetic + text-parse + rewrite — where portable bash (macOS bash-3.2 / BSD vs
  GNU `sed`/`date` / Git-Bash) is fragile, while stdlib Python is byte-identical cross-OS and is **already a hard
  package dependency** (the code-map extractor). Emergent rule: **thin shell glue = bash; parse/rewrite = Python.**
Deletions are made in the working tree and left **staged for the `audit` item's `commit`** (`git add -A`); content
stays recoverable at the recorded anchor. Two refinements to the pressure-tested previews: the marker lives at the
**section head** (so `document`'s append-only entries land below it, not after it) and the item marker is
**`promoted.json`** (not the loop's `state.json` — name collision). **Validated** on a git fixture: the three caps
fire, N accumulates (2→5), and a re-run is a clean no-op; archived content recoverable via `git show <anchor>:path`.
*Scope:* the three size-caps only. The prose deletion-test over `CLAUDE.md`+`rules/` stays a separate model-run
step in the same audit item (judgment, not the script); `base_sha` bounding the git-log read is a read convention,
not a script action; **dead-node prune** (deleted source → delete node) is a staleness signal owned by `document`,
not this size-cap script; **Sessions distillation** stays deferred (D61).
*Rejected:* frontmatter counters / a separate `archive-index.json` (correctness needs neither — counting decides,
the marker is only for humans); pruning by "closed" alone (unsafe without the promotion fact); hardcoded thresholds
(config is a cheap hedge); per-stack generation (the layout is identical everywhere); bash (OS-divergent for
parse-heavy work, and no dependency saving since Python is already required). *Evidence:* D61 (the law implemented),
D67 (the `checks.sh` shipped-mechanical-enforcer precedent), D68 (the sibling stdlib-Python shipped script + the
"Python already required" fact). → `scripts/retention.py`, `skills/{document,decision-engineer,prioritize}`,
`commands/start.md`, `shared/{schemas,memory-model}.md`, `11`; implements D61.

## D72 — Multi-language code-map: three-tier coverage + a prevalence-ranked build set **[DECIDED — supersedes D70's arm-vs-fallback binary; research-backed; tier-1 mechanism revised by D74 to a zero-dep resolver, tree-sitter demoted to reserved]**
D70 left non-Python coverage as a binary — a per-language *arm* or a *degraded fallback* — and gated arms on a
real target arriving (validate-on-demand). Neither survives contact: the fallback was **never built** (only
`python_codemap.py` exists), so **today a non-Python repo gets no graph at all** — empty, not degraded — and the
whole graph-backed half goes dark (`ingest` can't seed structural nodes, `planner`/D69 lose the impact lens,
`debug` loses the graph, the D70 map has nothing to render). And the "can't validate without a real target"
rationale is false — any public GitHub repo in the language is a fixture (that is how the Python `__init__` edge
bug was caught). Recast:
- **What varies by language is *edge resolution*, nothing else.** The node set (files) and directory clusters are
  identical quality in every language; only import→file resolution is language-specific, and the two lenses inherit
  edge quality. So "arm vs no-arm" is *trustworthy vs noisy weighting on the same skeleton* — once a floor exists.
  The cost of a language is its **resolver**, not its parser.
- **Three-tier coverage model** (replaces the binary):
  - **Tier 0 — generic floor** (directory tree + regex-shallow imports, zero-dep): the **long-tail safety net** so
    an un-armed/exotic repo still gets nodes + clusters, never nothing. NOT the strategy — just the floor.
  - **Tier 1 — shared tree-sitter engine**: one parser front-end + a per-language *query* (find import nodes) +
    *resolver* (map to files) → the existing `graph.json`/PageRank emitter. Each language is "query + resolver," not
    a whole tool (tree-sitter was already D68's non-Python mechanism).
  - **Tier 2 — deep bespoke arm** where resolution is baroque (JS/TS aliases/barrels/extensions; C/C++ preprocessor
    + a compile-DB). Python's stdlib-`ast` arm is a tier-2 that happened to be cheap.
- **Build set chosen by PREVALENCE, not ease** (research across Octoverse 2024/2025, SO 2024/2025, RedMonk Jan-2025,
  PYPL, TIOBE, JetBrains 2024): Python (done) → **JS/TS** (one arm — top of every source, the web substrate + Node;
  TS is a JS superset sharing the module system) → **Java** (top-4 everywhere) → **C#** (top-5) → **C++** (completes
  GitHub's "≈80% of new repos = six languages" set). **Second wave:** **Go**, **Rust**, **PHP**. Cutoff ≈5 arms
  covers ~80% of new repos, and because repos are polyglot (median ~3 / mean ~4.5 languages) five arms resolve most
  of *most* repos, not just the #1 language. **Set aside as graphless** (not arms — no file-to-file import graph):
  SQL, HTML/CSS, shell/PowerShell, JSON/YAML/TOML, Markdown, Dockerfile, HCL.
- **Ease breaks ties on ORDER only, never on set membership.** The prevalence-#5 slot **C++** is the hardest graph
  (textual `#include`, resolution needs `compile_commands.json` + macros/conditional-compilation) → it is the
  heaviest lift and sequences **last in the first wave** despite its rank; **Go** (prevalence ~#9 but a
  compiler-grade `go/packages` graph, package = directory) is pulled **early** as the fast-ROI add. Java is
  near-compiler-grade (`package`→dir); C# is medium (namespaces decoupled from files — needs the `.csproj`
  project-graph / Roslyn); JS/TS is the hard-but-essential tier-2.
- **Arms are no longer demand-gated.** With validation free, the common set is **built up front**, ordered by
  prevalence×effort; tier-0 covers the tail. The **Phase-4 demo still forces exercising ≥1 non-Python arm**
  end-to-end (proves the contract generalizes).
Kept from D68/D70: the `graph.json` contract (both lenses, stable module-relpath node IDs), tree-sitter as the
non-Python mechanism, Python stays stdlib, the symbol-level granularity seam.
*Rejected:* the flat "degraded fallback" as strategy (demoted to the tail floor); demand-gated arms (the validation
rationale was false); pure-prevalence C++ in an early slot (front-loads the worst graph, stalls coverage); heavy
per-project tooling / LSP-per-language (D68 — needs the toolchain + a build); shipping arms for rare languages
(tier-0 covers the tail more cheaply). *Evidence:* the language-prevalence research (sources above; polyglot stats
Wen et al. TOSEM 2024) + the current-state audit (only `python_codemap.py`, no fallback) + D68 (tree-sitter, two
lenses, stdlib Python) + D70 (the binary this supersedes). → `06`, `commands/start.md`, `11`; supersedes D70's
arm-vs-fallback + validate-on-demand.

---

## D73 — Multi-language code-map BUILT: shared engine + tier-0 generic floor **[DECIDED + BUILT — implements D72's tier-0 + the arm skeleton; the floor corrected by D75; tier-1 became a zero-dep resolver (D74), not tree-sitter]**
Refactored the single-language `python_codemap.py` into `scripts/codemap/codemap.py` — a shared,
language-agnostic driver (discover → dispatch → resolve → dual-lens PageRank → emit `graph.json`) over
pluggable per-language **arms**. Adding a language is a `class` with `extensions` + `index()` + `edges()`;
the driver is untouched (this is D72's "the cost of a language is its resolver, not the tool"). Two arms ship:
- **`PythonArm`** (tier 2) — the existing stdlib-`ast` logic ported **verbatim**; regression is exact
  (identical node/edge/centrality output on real `psf/requests`, 37 nodes / 73 edges).
- **`GenericArm`** (tier 0) — the zero-dep **generic floor**: ~15 recognized source languages, shallow-regex
  import extraction, and **precision-first** resolution keyed to each language family's import semantics —
  `rel` (JS/TS/ESM: only `.`-relative specs are intra-repo; a bare specifier is an external package) ·
  `include` (C/C++ quoted `#include`) · `pkg` (Java/C#/Kotlin/…: dotted, ≥2-segment suffix match, no bare
  collision) · `path` (Ruby/Go/Dart) · `mod` (Rust `mod foo;`). An unresolved specifier yields **no edge**
  (intra-project only) — over-broad regex is harmless because the floor **misses an edge before it invents one**.
This closes the gap D72 named: before, a non-Python repo produced **nothing** (empty, not degraded); now any
recognized language gets nodes + directory clusters + both centrality lenses. `graph.json` gained per-node
`lang`/`tier` + a top-level `languages` coverage map (a consumer can tell precise tier-2 edges from best-effort
tier-0), added **backward-compatibly** (every prior field kept). `/start`'s `codemap.sh` is now a single
`codemap.py <root>` call that auto-dispatches per file, not a per-language invocation. `python_codemap.py`
**removed** — the engine's `PythonArm` supersedes it (keeping both would be the duplication the memory law forbids).
*Validated:* 13/13 controlled multi-language fixture assertions (JS · C/C++ · Java · Ruby · Rust, incl.
dir-index resolution, `<system>`-include ignore, and bare-external drops for `lodash`/`json`/`java.util.List`);
real repos `expressjs/express` (JS — 141 nodes / 152 edges, 0 phantom / 0 `node_modules` edges; caught + fixed a
bare-`require('ejs')` false edge that a naive basename matcher produced), `query-string` (TS/JS), `gorilla/mux`
(Go — clusters present, honest bare-package non-resolution). Empty-repo, mixed py+js, and syntax-error-file cases
degrade cleanly (a parse failure is recorded but the file stays a node). Spec-ref gate + `py_compile` green.
*Rejected:* one script per language (the driver is shared — only resolution differs); a recall-first floor that
guesses on bare specifiers (a floor that invents edges is worse than one that misses them). *Deferred (Option B /
next):* the **tier-1 tree-sitter engine + the JS/TS bespoke arm** (aliases / barrels / `tsconfig` path-maps /
re-exports), shipped as a **graceful optional upgrade** — tree-sitter absent in a consuming project → that
language falls back to the tier-0 floor, never a crash. → `scripts/codemap/codemap.py`, `commands/start.md`,
`06`, `11`; implements D72.

---

## D74 — JS/TS arm is a zero-dep tsconfig resolver, not tree-sitter; tree-sitter demoted to reserved **[DECIDED + BUILT — revises D72's tier-1 mechanism; implements D73's Option B as B1]**
D72 named **tree-sitter as the tier-1 mechanism** for every non-Python language, and D73 deferred the JS/TS arm to
it. Building it flipped the call on evidence:
- **tree-sitter is fragile in practice.** The Python binding drifts hard across versions (`Tree.root_node`
  property-vs-method, `Parser.parse` bytes-vs-str, `QueryCursor` present-vs-absent) and `tree-sitter-language-pack`
  ships a vendored `builtins.Parser` that diverges from the documented API. Shipping that into arbitrary consuming
  environments — each resolving its own tree-sitter — is a reliability liability, not the near-zero-dep tool D68 wanted.
- **The parser was never the bottleneck (D73's own insight — a language's cost is its resolver).** The floor's regex
  extraction already produced 152 correct JS edges on real `express` (0 false positives); what the floor *cannot* do
  is resolve **tsconfig/jsconfig `paths`+`baseUrl` aliases** and TS extension/index/barrel resolution — and that is
  dependency-free **resolver** logic, not parsing.
- **The resolver is needed under tree-sitter too**, so the zero-dep arm is a strict subset — never wasted work.
Call: the **JS/TS arm = `JsTsArm`** (subclasses the floor) = the floor's regex extraction + a resolver that reads the
root `tsconfig.json`/`jsconfig.json` (JSONC-tolerant — strips comments + trailing commas), applies `paths` aliases +
`baseUrl`, and does TS/JS extension + `index` resolution. **No tsconfig → it degrades exactly to the floor.** This
makes the **default precise-arm mechanism zero-dep** (regex extraction + a per-language resolver — Python's `ast` and
JS/TS are both this); **tree-sitter is demoted from "the mechanism" to a reserved tool** for the few languages whose
lexical structure genuinely defeats regex extraction (e.g. C++ preprocessor/templates), still shipped as a **graceful
optional upgrade** (absent → the floor). *Validated:* a tsconfig-paths fixture — the floor resolves **1** edge
(relative only), `JsTsArm` resolves **4** (the three `@/`-alias/baseUrl edges the floor drops), bare `react` correctly
external; `express` regression identical (152 edges, no-tsconfig == floor), Python + `query-string` regressions exact,
no-spec-refs gate + `py_compile` green; tree-sitter uninstalled (env left clean). *Rejected:* B2 (tree-sitter
extraction for JS/TS) — fragile cross-env deps for a marginal extraction gain the resolver still has to backstop.
*Kept from D72/D73:* the `graph.json` contract, the prevalence-ranked build set, tier-0 as the floor, and the
graceful-optional-upgrade principle (now applied to *reserved* tree-sitter, not the default path). *Consequence for
the build set:* future arms (Java, C#, Go, …) default to a zero-dep resolver arm like `JsTsArm`; reach for tree-sitter
only when a language's **parsing** (not resolution) is the real obstacle. → `scripts/codemap/codemap.py`, `06`,
`commands/start.md`, `11`; revises D72, implements D73's Option B.

---

## D75 — Tier-0 floor: node-recognition set ≠ edge-extraction set (widen the tail net) **[DECIDED + BUILT — corrects D73's floor to honour D72's "never nothing"]**
D72 promised tier-0 as *"the long-tail net so an un-armed/exotic repo still gets nodes + clusters, never nothing."*
The D73 build under-delivered: the floor recognised **only the ~15 languages that had an import regex**, so an
exotic-language repo (Elixir, Haskell, Lua, R, …) got **zero nodes** — a net only *inside its own fence*. Fix:
**split the two sets the floor had conflated** — a broad **node-recognition** set (`_NODE_LANGS`: every recognized
programming language, edge-capable or not) vs the narrow **edge-extraction** set (`_LANGUAGES`: the subset with an
import regex). Any source file → a node + directory cluster; edges only where a regex exists. Graphless data/markup/
config/doc artifacts (json/yaml/md/html/css/sql/lockfiles) stay **excluded** — no import graph, and they'd flood the
node set. Widening the node set surfaced a **latent cross-language false-edge bug** (a Ruby `require 'utils'` could
suffix-match an unrelated `utils.go`/`utils.lua`) — fixed by scoping resolution to the importer's **family**
(intra-language, C/C++ sharing headers). *Validated:* an Elixir+Haskell+Lua+R+Go repo now yields 5 nodes+clusters
(was 1); json/md/css excluded; Ruby→Ruby only; express / Python / JS-TS / multi-lang regressions all unchanged; gate
+ `py_compile` green. → `scripts/codemap/codemap.py`, `06`, `11`; corrects D73, honours D72.
**The process failure that let this ship — all gates green on a build *narrower than the decision* — is the real
lesson; the workflow-rule fix is D76.**

---

## D76 — Promise-adequacy discipline: mechanical gate + independent elicitation + honest residual **[DECIDED + BUILT — red-teamed; prevents the D75 class; supersedes the naive promise-coverage proposal]**
D75 exposed a failure class the loop must defend against autonomously: a build **silently narrower than the
decision's promise, passing every gate** — because the tests were drawn from the implementation's own scope, so
nothing exercised the promise's boundary. The first fix proposed (decision-record `promises` field → planner maps
each to a criterion → verify exercises a boundary test "outside the builder's fixtures" → a `rules/testing` line →
alignment-scan coverage → D69 escalation on universal-keyword) was **stress-tested by five parallel red-team agents
and unanimously rejected (HOLE-major).** Their kill-shots, all kept:
- **Lexical detection is wrong both ways.** Universal words ("any/all/never/floor") are the *default register* of
  engineering intent (~6 per backlog item) → a boundary test per word inverts D69's 85-95% tier-0 distribution and
  violates the lean master rule; *and* the invariants that actually break carry **no keyword** (idempotent,
  backward-compatible, no-false-positive — the real D75 cross-family bug had none).
- **A single out-of-fixture witness is ∃, not ∀** — it *shifts* the tail (add Elixir → Haskell still fails), never
  closes it; and "outside the builder's fixtures" is defeatable (D73 tested JS/C/Java/Ruby/Rust — outside the
  Python fixture, still inside the 15). You cannot ask a blinded party to test outside a fence invisible to it.
- **The schema field is not the root.** D72 already stated "never nothing" in prose; relocating it to a list written
  by the same author in the same pass adds no independent recognition. Root = **recognition**, not storage.
- **Advisory ≠ teeth.** Six model-run prose steps re-enact the pattern this project already fixed thrice (D34→D64
  grep gate · D35→D58 hook · D40/D67→`checks.sh`). The D63 alignment scan *already existed* as the backstop for
  "build narrower than decision" and D75 shipped straight past it (model-run, same prose, periodic/late).
Redesign — three layers, **impact-scoped**, honest about the residual:
1. **Mechanical property invariant (the real teeth).** Where a promise is a property of a **deterministic
   artifact**, encode a check whose input is drawn from **outside the build's own enumeration** — model-free,
   blocks. Built: `scripts/codemap/test_codemap.py::test_floor_invariant_never_nothing` (recognized-source-file ⇒
   node, over exotic languages) — the airtight D75 regression gate and the template for the class.
2. **Promise→test *linkage* gate.** `decision-record`/`plan` gain `promises[]` `{ text, kind (archetype),
   universal, falsifier, test_ref }`, **only on impact-flagged decisions** (the D68 impact lens / a design's
   raison d'être — *not* D69 reversibility, which tier-0's a cheap-to-reverse floor; ~85-95% of records carry
   none). `scripts/check_promise_coverage.py` (shipped fixed, in `checks.sh --check` + pre-commit) **blocks** an
   unlinked promise, a dangling `test_ref`, or a `universal` promise whose linked criterion isn't `boundary`-tagged.
   Decidable, model-independent. **Ceiling (stated, not hidden): proves linkage, not adequacy** — a sham link
   (in-scope test labelled as covering a universal) passes; adequacy rests on layers 1 + 3.
3. **Independent adversarial elicitation (reduces the un-written-promise root).** `decision-engineer` runs a pass
   **distinct from the decision's author** — *"what does this design promise that isn't written?"* — driven by an
   **archetype checklist** (universality · idempotence · preservation · monotonicity · graceful-degradation ·
   isolation · backward-compat) + **derive-from-purpose** ("floor" ⇒ covers-the-tail), each promise carrying a
   `falsifier` (kills vacuous knob-lists — the Goodhart guard).
The **alignment scan (D63) is reframed coverage → adequacy**: re-derive the negative class from the design's
purpose (code-blind, so it doesn't inherit the builder's blind spot) + an **over-delivery scan** (behaviour not
traceable to a promise — catches scope creep) + a **cross-decision invariant re-run** (satisfying promise P re-runs
decision Q's invariants — catches D75's own shape: honouring D72 broke D73's no-phantom-edge). The *late* backstop,
not the gate.
*Dropped from the naive version:* the lexical trigger; verify "exercises the boundary" (violates its artifact-only
charter — verify reads the linkage, the test-runner runs the test); D69 as the trigger (wrong axis).
**Irreducible residual (captured, not laundered):** the *un-written* promise cannot be mechanically sealed where
the promise isn't a deterministic-artifact property; layer 3 reduces it, the gate raises the bar to *omit-or-lie*,
neither eliminates it. Where the artifact IS self-describing, derive the invariant from the tool's own output —
no promise need be written (layer 1). Claiming more would re-enact D75's laundering at the spec level.
*Built + tested:* `check_promise_coverage.py` + `test_check_promise_coverage.py` (blocks unlinked/dangling/
non-boundary-universal — 6 tests) and the codemap floor-invariant suite (6 tests), all green. *Wired:*
`shared/schemas.md` (decision-record + plan `promises[]`, acceptance_criteria `id`/`boundary`), `skills/planner`
(promise-coverage gate), `skills/decision-engineer` (elicitation), `skills/verify` (linkage artifact-check, stays
artifact-only), `rules/testing.md` (principle + `enforced by`), `commands/start.md` (copy + `checks.sh` wiring),
`11` (alignment-scan remit). *Evidence:* the 5-agent red-team (2026-07-02) + the D75 incident + the project's
advisory→mechanical history (D34/D46/D64/D67). → the files above; extends D43's coverage gate, corrects D75's
process gap.

---

## D77 — Four more precise code-map arms (Go · Java · C# · JS/TS exports-subpath), measured on real repos **[DECIDED + BUILT — implements D72's prevalence build set; fidelity is measured, not asserted; C# arm amended by D79 (head-token precision filter)]**
D72 set the build order Python → JS/TS → Java → C# → C++ then Go. This session built the next wave as
**zero-dep resolver arms** on the D73 driver (D74's default mechanism), each pressure-tested with the D76
loop — a blind promise-elicitation agent (that cannot see `codemap.py`) writes the resolution spec + property
tests, then the arm is measured against **ground truth** (`_resolve` per specifier vs `package.json`/`go.mod`,
NOT a proxy count):
- **A prior-session audit first.** The prior "27% JS/TS monorepo gap" was a **measurement artifact** — a proxy
  metric that counted external `node_modules` specifiers as misses. Corrected measurement (per-specifier vs
  `package.json`): on express/vue/vite **0 fabricated edges** despite 1337 (vite) + 215 (vue) external specifiers
  correctly dropped; relative recall ~87–100%, workspace ~95–100%. Fixed three real bugs the audit surfaced:
  `.d.ts` extension resolution, a `glob.glob` that traversed `node_modules` on an installed repo (→ EXCLUDE-pruned
  walk; a false-workspace-package + perf risk), and a `str.lstrip("./")` char-strip bug.
- **`GoArm`** (package == directory): reads `go.mod` module paths, resolves module-prefixed imports to the target
  dir, edges to every non-test `.go` file. **100% intra-repo recall (gin 31/31, cobra 11/11), 0 soundness bugs.**
  Replaces a **broken + unsound** tier-0 floor — the `path` mode resolved **0%** of Go intra-imports AND
  *fabricated* edges (`import "errors"`/"context" — Go stdlib — hit the repo's own `errors.go`/`context.go`).
- **`JavaArm`** (two-pass symbol resolution): pass 1 indexes top-level types → FQN (brace-depth filters nested);
  pass 2 resolves three channels — explicit imports **+ same-package simple-name refs + inline FQNs**. The latter
  two carry **no import statement** and are a **measured 24%** of intra-repo type edges on gson (the "~50%"
  estimate was repo-dependent; gson has disciplined imports). Wildcard `import pkg.*` resolves to *used* names
  only. Soundness = every channel gates on repo-declared types, so `java.*`/third-party never edge.
- **`CSharpArm`** (namespace-aware two-pass): namespace is decoupled from directory *and* file, so the floor was
  near-useless (newtonsoft **945 files → 107 edges**). Pass 1 tracks a namespace stack (file-scoped `;` +
  block-scoped `{`, nested) → `(namespace, type) → {files}` (partial types → a set); pass 2 resolves `using`
  (to the **intersection** of the namespace's types with the file's used simple names — never the whole
  namespace, or the graph is a hairball), same-namespace refs, inline FQNs, `using static`. **107 → 3731 edges**
  (3.9/node, not a hairball), 0 non-`.cs` targets.
- **JS/TS exports/imports subpath** (closes the documented `hono/jsx` residual): a local workspace package's
  subpath (`@acme/core/jsx`, `hono/basic-auth`, `#db/client`) resolves via its `package.json` exports/imports map
  — exact keys, `*` patterns, source-preferring conditions, and **dist→src derivation** when exports point at an
  unbuilt dist (the common unbuilt-monorepo case). hono workspace-subpath **9 → 22/23**; register a workspace
  package even without a resolvable main entry (vite 91 → 267). 0 fabricated edges.
- **C++ stays on the floor** (deliberate, per D72): a precise arm needs `compile_commands.json`; the floor's
  quoted-`#include` relative resolution is the sound subset.
Every measured gap is fed into each arm's **`fidelity` + `known_gaps`** honestly (a tier-2 arm can still be a poor
approximation — the fidelity signal, D-prefix in graph.json, is *measured*, not inferred from tier). *Rejected:*
the proxy-count measurement (the 27% artifact); strict Node "encapsulation" for local subpaths (it *hurt* recall
on unbuilt monorepos — a code map wants the real intra-repo dependency, not runtime encapsulation); tree-sitter
(D74 — parsing was never the bottleneck). *Evidence:* the four blind specs + ground-truth measurements on
gin/cobra/gson/newtonsoft/express/vue/vite/hono; 28/28 property tests. → `scripts/codemap/codemap.py`,
`scripts/codemap/test_codemap.py`, `06`, `11`; implements D72, corrects the prior JS/TS measurement.

---

## D78 — The code-map is a LIVING artifact: a durable *observed* layer that self-corrects through the loop's own runs **[DESIGNED + EMPIRICALLY VERIFIED — implementation deferred; resolves `07` regenerate-vs-incremental; realises D70 flow-overlay + D68 `[D]`]**
Premise (user): 80% static accuracy on a language is worthless if it *stays* 80% — the graph should improve as the
loop works in the codebase. Static arms are precision-first but recall-imperfect (dynamic imports, DI, reflection,
C# source-gen, Go build-tags, dynamic dispatch are structurally invisible to static analysis). The design makes the
loop's *own activity* close that recall gap. **Design-first, then verified before adopting** (user: "do the tests
and verifications before adopting").
- **Two superimposed graphs, kept DISTINCT** (merging corrupts both): a **dependency graph** ("A needs B") = static
  arms **+** observed runtime **+** observed debug-causal, precision-first; and a **temporal-coupling graph** ("A
  changes with B") = co-edit affinity, correlational. "Changed together" ≠ "depends on." The D70 map overlays both.
- **The load-bearing insight: activity buys RECALL, not precision.** Runtime/debug can *reveal* a missed edge (add
  it); almost nothing the loop does can *retract* a fabricated one ("not exercised" ≠ "not a dependency"). False
  negatives self-heal; false positives are sticky. ⇒ keep arms precision-first (this *validates* the D77 soundness
  discipline) and let the loop accrete the missing recall.
- **Two-layer storage → resolves regenerate-vs-incremental (`07`).** `graph.json` = the static layer, regenerated
  freely by the arms. `graph.observed.json` = the **durable `[D]` layer** (D68), *accreted* from activity, keyed by
  stable node IDs (the D70 reserved seam). Regenerate = re-run arms **+ merge** the durable layer whose endpoints
  still exist. Neither pure-regen (loses learned truth) nor pure-incremental (static drifts). Every edge carries
  **`provenance`** (`static-arm` | `observed-runtime` | `observed-debug`) + confidence — this subsumes the D77
  `fidelity` signal (static edges inherit the arm's fidelity; observed edges are ground truth).
- **Capture home = `verify`, as a pure OBSERVER.** `verify` already *executes the affected flow* end-to-end
  (its charter: distrust the static artifact, observe real behaviour — the same principle as the observed layer).
  So the execution cost is sunk; the marginal cost is harvesting what the run touched. `verify` stays artifact-only
  (D76); the graph **write** lives in a thin post-step (`document`/`commit`). **Emergent property:** because
  `verify` only exercises the *changed* flow, the graph becomes most accurate exactly where the project is most
  active — where `planner` blast-radius and `debug` need it most; quiet regions never pay.
- **`debug` is the premium supplement** — rarest, highest truth (a verified cause→effect link), writes
  `provenance: observed-debug` at top confidence.
- **Mechanism is the gate (empirically decisive).** A naive Python call hook (`sys.settrace`/`setprofile`) is **14×**
  overhead — reject. `sys.monitoring` (3.12+) with **fire-once + `DISABLE`** (each call-site records once then
  disables) is **1.0×** — adopt. Universal fallback where 3.12+/native is absent = **harvest the coverage artifact**
  the test run already produces (~1.5×, often already on) → file co-execution. Trigger **selectively**: only where an
  arm's own `known_gaps` flag dynamism (the static layer self-reports where the observed layer should look).
- **Verified (Python prototype, before adopting):** a controlled fixture proved runtime catches a dynamic-dispatch
  edge static *cannot* (`registry.py → plugins/alpha.py` via a runtime-populated dict), **soundly** (0 non-repo
  edges; a stdlib `json` call correctly dropped), and *confirms* static edges (provenance overlap). On clean code
  (requests, explicit imports) runtime added **0** new edges — **benefit is conditional on dynamism**, coverage per
  run is narrow (12/65 exercised → "accurate where active"). Costs measured as above.
*Rejected:* merging co-edit affinity into the dependency graph (corrupts dependency semantics); a bespoke Python
tracer in `verify` (14× — and widens verify's charter); strict Node-encapsulation semantics for the observed layer;
pure-regenerate or pure-incremental graph maintenance. *Open (next):* node-ID stability across renames; observed-edge
staleness/decay (couples with retention D71 — a debug-causal edge decays far slower than a coverage co-activation);
precision-retraction (accepted as unsolved — lean on precision-first); the non-Python capture mechanism per stack
(coverage/native profiler — reasoned, not yet measured). *Evidence:* the prototype measurements (fixture +
requests + `sys.monitoring` cost); the D77 fidelity signal it builds on; D70 (flow-overlay), D68 (`[D]` layer).
→ `06`, `07`, `11`; implementation is Phase-2/3 with the console (D70).

---

## D79 — C# head-token precision filter; the D78 bias-precision rule applied to a measured-noisy channel **[DECIDED + BUILT — executes D78; closes the code-map arm build thread with all five arms measured on independent real repos]**
The five precise arms (D77) had a measurement gap: Java + C# precision each rested on **one** repo with a
self-consistent (not independent) check. This session measured the last two arms against **independent
ground truth** (D77 discipline — real repos, edges sampled + classified by channel, not a proxy count) and
applied the **D78 bias-precision rule** where a channel came back noisy:
- **Java (`JavaArm`) — no change.** The same-package channel measured **≈100% precision** on commons-lang
  (976 same-package edges) + okhttp: every flagged candidate resolved to a genuine reference. Java's
  **camelCase members** make the theoretical PascalCase type/member collision structurally rare, so the
  arm's stated over-edge risk essentially doesn't materialize. Fidelity comment updated with the number.
- **C# (`CSharpArm`) — the fix.** On AutoMapper (a fluent-DSL worst case) the collision-prone type channels
  (same-namespace + `using`-intersection) over-edged: C# member access is **PascalCase by convention**, so
  `_CAP` matched fluent method calls (`.Include<>()`, `.ForPath()`), property access (`x.Order`), and enum
  members (`MemberList.Source`) that collide with same-namespace **type** names. Fix (`_head_used`): a
  capitalized token qualifies for the type channels only if it appears **≥1× as a HEAD token** — not
  immediately preceded by a member-access `.`. A genuine type is always referenced head-position at least
  once (`new Order`, `Order x`, `: Order`, `<Order>`); genuinely-qualified `Ns.Type` refs still resolve via
  the untouched **inline-FQN channel**, so qualified type use isn't lost. Measured: precision **97.2 → 98.9%**
  on AutoMapper (fluent-DSL worst case) with **0 recall loss** (every dropped edge verified a real FP), and
  −2 FPs / 0 loss on eShopOnWeb (app code). **Residual ~1%** = a property/enum-member **DECLARED** with a
  same-namespace type's name (`public string Source`) — a head token in a non-type position, unreachable by a
  regex arm — so C# **stays `fidelity=medium`** (honest, not bumped). Locked with a regression test
  **verified to fail without the filter** + a recall-preservation control.
- **Python (`PythonArm`) — re-confirmed, no change.** Fresh ground-truth pass on flask: **40/40 sampled edges
  real** (0 fabricated), both `known_gaps` present (8 dynamic-import files, 5 `__init__` edges — the exact
  recall surface the D78 observed layer is meant to close).
This makes **precision a bias, not an afterthought**, a **standing rule** for the static arms (now documented
where the arms live): a fabricated edge is **sticky** (the D78 observed layer can only ADD missed edges, never
retract a false one — "not exercised" ≠ "not a dependency"), while a missed edge **self-heals** through runtime
capture, so a noisy channel is tightened toward precision at the cost of recall. **Rust (`mod`) / PHP
(`require`) / C++** stay on the **tier-0 floor** deliberately (sound relative/sibling subset; precise arm
built on demand by prevalence; C++ additionally needs `compile_commands.json`) — recorded as the one-line
defer rationale. *Rejected:* leaving the noisy C# channel (D78 — sticky false positives mislead blast-radius /
orchestration reads forever); a full type-position parser (heavier, risks recall — the head-token heuristic
captured nearly all the gain for ~5 lines); bumping C# to `high` (dishonest — the declaration-name residual
survives); an up-front Rust/PHP/C++ arm (prevalence-gated, floor covers them soundly today). *Evidence:*
independent ground-truth measurements on AutoMapper / eShopOnWeb / commons-lang / okhttp / flask; the
gate verified failing without the filter; 30/30 tests green; committed + pushed `39d391f`. → `scripts/codemap/
codemap.py`, `scripts/codemap/test_codemap.py`, `06`; executes D78's bias-precision rule, completes D77's
build set (**amends D77's C# description, which now describes the pre-filter arm**).

---

## Phase 1 close — guiding-doc coherence pass (session 2026-07-03)

## D80 — Status is single-source via an OWNERSHIP MAP, not one file: derive-or-point + mechanical ownership gates + deliberate adoption of new sources **[DECIDED + BUILT (meta-repo); shipped side rides D70 — resolves D64's two prevention follow-ons; extends D38/D40/D65]**
The 2026-07-03 coherence pass (a lightweight fan-out over the whole guiding-doc surface, the D63 method) found a
**systemic status-drift regression**: ~10 sites across `README`/`00`/`CLAUDE.md`/`07`/`10`/`11`/`02` asserted a
stale count / phase / done-vs-open. **Root cause (high-certainty):** status is *derived* data that had been
**denormalised into hand-maintained prose across ~8 files with no single owner and no propagation** — the same
disease D38's memory law cures for knowledge, never applied to the status layer. Three reinforcing mechanisms:
(1) no single owner → the update set is unbounded and non-obvious, so a capturer updates some copies and misses
the rest; (2) the capture ritual touched a decision's named `→ files`, not the transitive set that restated the
status — **D64 designed exactly this "capture-time blast-radius sweep" and that follow-on was itself never tracked**
(the disease shown on its own cure); (3) no mechanical status check, only prose, so drift stayed invisible until a
human read across files (the project's own D38/D40/D64 thesis proven on itself).

**A first cut ("designate `11-roadmap.md` as *the* single file") was pressure-tested and rejected as the frame:**
it repeats the move that already failed (we had *declared* SSOT in D38 / `README` and it drifted anyway — a
*declaration* is not a *mechanism*), it cannot answer a legitimately-new or brownfield source (rules break; real
repos carry many status surfaces — a board, a CHANGELOG, release notes, the code), and the single file even
drifted against *itself* (`11:125` vs `11:111`). The failure is never *multiplicity* — it is multiple
*independently-maintained copies* (denormalisation); a *derived* surface is not a competing source. Calls
(general — for **any** single-source-of-truth claim, not just status):
- **Ownership map — one OWNER per fact-domain, not one file for everything.** Owners: roster count →
  `10-roster.md`'s table (list = count) · decisions/why → `08` · open *design* questions → `07` · phase /
  what's-left / build-status → `11-roadmap.md` · code structure → `graph.json`. Multiple owners are fine; multiple
  *copies of one fact* are the bug. This is the partition the machine-state layer already runs on (loop-position →
  `state.json`, open-work → `backlog.md`, issue-state → GitHub, history → `git`) — zero drift by construction.
  Extends D38 (pointers > duplication).
- **Derive-or-point, never a second copy.** Every non-owner surface *points* to the owner or is *generated* from
  it; generation is the strongest form (a derived surface cannot drift) — the shipped project-state view (D70) is
  this, the meta-repo uses pointer-collapse (a generator is disproportionate for a repo this size; revisit if `11`
  keeps self-drifting).
- **Mechanical ownership gates (detection, loud) — for what's checkable.** `scripts/check-status-coherence.sh`
  fails a commit when (a) a roster count or `D1–DN` range drifts from the tree, or (b) a roadmap build-status tag
  (`**[core]/[stageable]/[later]/[done]**`) surfaces **outside** its owner `11-roadmap.md` — (b) is what makes a
  *new* status source trip the gate instead of waiting for the periodic scan. Companion to `check-no-spec-refs.sh`
  (D40/D64: check, not advice). **Honest residual:** the gate covers *structured* status (counts, ranges, tags);
  *prose* phase-narrative ("Phase 1 = start with X") is **detect-not-prevent** — the D63 alignment scan is its
  enforcement, not the gate. Named, not hidden.
- **Capture-time blast-radius sweep (prevention, upstream).** On capture: grep every guiding doc for the fact
  just changed, update the source, repoint the rest — a judgment step in the `CLAUDE.md` working brief. Two tiers
  (mechanical + judgment) exactly per D65.
- **Deliberate adoption, not prohibition (rules break — handle it).** A genuinely-new source, or a brownfield
  repo's pre-existing several, is handled by **discover → declare its owner (update the map) → derive/point the
  rest** at a reconciliation checkpoint — never accreted silently. The D68 ingest / commitment model applied to
  sources-of-truth; also the brownfield answer (you cannot collapse an existing repo to one file — you map it).
- **The meta-repo dogfoods it.** A repo-local `.git/hooks/pre-commit` now runs both gates, closing the hole the
  scan found — the no-refs gate was "mechanical, not advised" (D64) but nothing auto-ran it here.
- **Shipped workflow (target projects): decided now, built with the console.** In a target project status is
  **generated** — the project-state view / console (D70) over `state.json`+`backlog.md`+GitHub+`git`+`graph.json`,
  never hand-written prose; the machine-state layer already has true single sources (D48/D55/D59). `document` owns
  status-narration freshness. The generated status surface + the shipped status-coherence gate ride the console
  build (Phase 2/3); the principle is fixed now.
*Rejected:* the naive single-file framing (above — repeats a failed declaration, can't handle new/brownfield
sources, ignores intra-source drift); generating a `STATUS.md` in the meta-repo now (a generator is
disproportionate for a small repo; pointer-collapse + gate suffices, and the shipped generator rides D70);
discipline-only with no gate (the root cause is that checklists get forgotten — D64's own follow-on proved it); a
gate that polices arbitrary status *prose* (brittle / false-positive — the mechanical tier checks only counts,
ranges, and bold tags; the judgment tier + the D63 scan cover the prose residual). *Evidence:* the 2026-07-03
sweep — ~10 drift sites, one root cause; the new gate reproduced the drift then went green after the
pointer-collapse, and blocks an injected out-of-owner tag; established practice (SSOT · derive-don't-store ·
docs-in-CI freshness gates). → `11-roadmap.md` (phase/what's-left owner), `scripts/check-status-coherence.sh`,
`.git/hooks/pre-commit`, `CLAUDE.md`, `README.md`, `00`, `07`, `09`, `10`, `02`, `06`; the shipped side → the
console build (D70). Resolves D64's single-source-status + capture-time-blast-radius follow-ons; extends
D38/D40/D65; complements D63.

## D81 — The alignment scan crystallized as the `align` skill + a decidable contract linter (`check_contracts.py`): two layers (mechanical-always-whole · semantic-scoped-budgeted), drift-triggered, principle-only panel **[DECIDED + BUILT (skill + mechanical layer + wiring); the semantic layer is specced, validated Phase 2/3 — realises D63/D76, closes the D63 cost lead, fixes G2]**
Origin: the pre-Phase-2 adversarial pressure-test (2026-07-03/04; `pressure-test-2026-07/`) both harvested the
scan's shape and produced a ~57-finding register that is now the skill's validation oracle. D63 designed the scan
as a *lightweight fan-out, not a Workflow*; D76 grew its remit (promise-adequacy) without re-deriving that cost
envelope — the pressure-test's own cost (~450 agents ≈ 3 usage windows over the whole surface) is the datum that
forces the answer. **Calls:**
- **Two layers with opposite scaling** — the trap D63/D76 left implicit. The **mechanical layer** (the package's
  own wiring — routing graph, skill I/O, schema enums, coverage gates) is *fixed-size*, so it always runs WHOLE
  and its findings are *facts* that hard-block. The **semantic layer** (spec↔code) *grows with the product*, so
  it alone is scoped to the diff-since-anchor + capped at `config.align.max_agents` with honest truncation.
  Conflating them is what would halt a large repo.
- **`check_contracts.py` = a routing-graph linter, not a producer/consumer linter.** Decidable from `loop.md`'s
  table structure: every routing target resolves, every invoked `node:mode` is routed, every skill is a node or a
  side-door; commitment/kind tags stay in their schema enum. Hard-blocks a broken graph; advisories for
  coverage/enum drift. Built + fixture-tested (11/11), wired into the meta-repo `.git/hooks/pre-commit` and
  copied by `/start` for `align`'s mechanical layer.
- **Trigger = drift, decoupled from retention.** `prioritize` injects an `align` maintenance item on
  `config.align.every_n_commits`-since-anchor / a phase boundary — a *separate* threshold from `document:audit`'s
  retention counts (memory pressure ≠ drift risk). Both are self-contained maintenance items that flow straight
  to `commit` (`loop.md` § Maintenance items).
- **Verify = principle-only, 2 orthogonal lenses.** Contract/decidable findings are settled by the read; only
  *judgment* findings enter a small panel — occurrence + materiality (drop `mitigation`, it overlaps occurrence)
  — dying on ≥1 solid refutation (precision-biased: a periodic scan that cries wolf gets muted). The D80
  status-ownership + D76 promise↔plan-mirror lenses are baked in as standing checks.
- **Wiring fixes G2 en route.** A single general maintenance-routing row routes `align` AND its sibling
  `document:audit`, resolving the register's G2 (an injected maintenance mode with no `loop.md` edge);
  `check_contracts.py` now guards that whole class.
**Rejected:** a *producer/consumer* contract linter (would need a machine-readable skill-I/O manifest = a second
copy of the prose Inputs/Output → a NEW drift surface `align` itself exists to catch: the disease posing as the
cure); *whole-project* semantic scope (halts a large repo — the reason for the two-layer split); a
*retention-coupled* trigger (conflates two independent signals); a *3-lens panel over every finding* (the
pressure-test proved the panel earns its keep only on judgment attacks — it killed ~19 weak ones, but
ground-truth reading adjudicated ~40 contract facts faster and at higher integrity). **Evidence:** the register
is the oracle — a baseline run of `check_contracts.py` re-found **G2** (hard), **G4** + **S3** (advisory) with 0
false positives, while correctly NOT firing on G11 (prose, not a token) or the producer/consumer class (out of
decidable scope by design); post-wiring the gate is green and G2 is resolved. **Honest residual:** the *semantic*
layer has no test surface yet (no built product) — specced, validated in Phase 2/3; the pressure-test's
~57-finding register is triaged in a separate **resolve phase** (5 principle leads upheld with a direction, D27
refuted → a resolve-phase skill→leaf-agent reclassification). → `skills/align/SKILL.md`,
`scripts/check_contracts.py` (+ `test_`), `templates/loop.md`, `skills/prioritize`, `shared/schemas.md`,
`commands/start.md`, `.git/hooks/pre-commit`; register + adjudications in
`pressure-test-2026-07/EXPLORATION-LEDGER.md`.

---

## D82 — The verifiability contract: every acceptance-criterion carries a mechanical `discharge`; `verify` never vacuously passes an `artifact` criterion; classification is mechanical, not a blind judgment **[DECIDED + BUILT]**
Origin: the pressure-test **resolve phase** (cluster 1, "un-verifiable-in-autonomy": P1 + the D22/D17 & D30 leads,
`pressure-test-2026-07/`). `schemas.md` already *asserted* the invariant "every criterion is one or the other;
`planner` emits no un-checkable criterion" — but nothing enforced it, and `verify`'s conjunction rule (D45) let an
untested `artifact` criterion pass **vacuously**: a behavioral-correctness criterion (e.g. "retry backs off
exponentially") the model reads as wrong, but with no failing test / type error / plan↔changelog mismatch, was
downgraded to advisory → auto-committed (P1). The design asserted the invariant; nothing made it true. **Calls:**
- **`discharge` is a required field on every `artifact` criterion** (`acceptance_criteria[] { …, discharge }`) — it
  names the concrete mechanical check (a test ref, or `type`/`lint`/`structural`). A criterion with **no nameable
  discharge is not artifact-checkable → it is `human-qa`**. Classification becomes **mechanical** (*can you name a
  check?*), which dissolves the D30 blind-author worry — the author *demonstrates a mechanism or fails to*, rather
  than *judging* perceptibility. This **replaces** the ledger's "distinct classification pass" direction with
  something leaner and crisper (maintainer's Q2 ruling).
- **`verify` never vacuously passes.** An `artifact` criterion whose `discharge` produced *no signal* (its named
  check didn't run or didn't pass) is a **hard fail**, not a silent pass. And a **sharpening of D45**: a
  criterion↔artifact contradiction the model can *demonstrate* (point at the artifact) is itself a *structural*
  deterministic signal → hard fail; only genuinely *inferential* suspicions stay advisory. This draws the
  demonstrable/inferential line D45 always implied — it does **not** reopen D45.
- **Default = author a test to keep it `artifact`; park is the rare fallback (D22/D17).** Soundness never
  auto-commits an unverified criterion — but the loop's *autonomy* depends on most criteria staying mechanically
  checkable, so `planner` prefers *authoring a discharging test*; `human-qa`→`checkpoint` (or `handoff.parked[]`
  when unattended) is reserved for the genuinely perceptual/runtime. **Park over vacuous-pass, but test over park.**
- **A mechanical presence gate.** `check_criterion_discharge.py` (+ test; in `checks.sh --check`, copied by
  `/start`) **blocks** a plan whose `artifact` criterion lacks a `discharge` — the sibling of
  `check_promise_coverage.py`, giving the invariant teeth pre-plan, not only at `verify`.
*Rejected:* `verify` computing a `needs_human_qa` flag itself (D30 already killed that — keeps product-intent out
of the artifact checker; here the classification lives in `planner`, `verify` only *gates* on the signal); a
distinct adversarial *adequacy* pass (heavier — mechanical discharge-naming suffices; **Q2**); a procedural,
no-field enforcement (leans on `verify`'s model-only judgment at gate time — the exact softness P1 flags; **Q1**);
reusing the promise `test_ref` for every criterion (blurs the promise/criterion distinction; **Q1**). **Honest
residual (deferred hardening):** a plausible-but-*insufficient* discharge (a "renders without error" test named
for a "looks right" criterion) still slips the presence gate — adequacy stays `verify`'s read + a future
adversarial adequacy lens (the one the promise `boundary` rule + `align`'s semantic layer use). *Evidence:*
register §6 P1 (`adjudicate:18-21`, `verify:33`) + the D22/D17 & D30 leads (§2B); the maintainer ruled the two
design forks (AskUserQuestion — explicit `discharge` field · discharge-naming self-suffices). Refines D45
(demonstrable = signal) and D17/D30 (mechanical + enforced classification). → `shared/schemas.md`,
`skills/{planner,verify}`, `scripts/check_criterion_discharge.py` (+ `test_`), `commands/start.md`,
`scripts/check-no-spec-refs.sh`.

---

## D83 — `verify`'s artifact-purity governs its *verdict*, not its *observation*: it may drive a flow to capture the D78 observed layer **[DECIDED — small reconciliation; the concrete revisit rides the living code-map build, Phase 2/3]**
Origin: the resolve phase (P6) — a live *spec-internal contradiction*, exactly the class `align` exists to catch.
`verify`'s skill said "never run or **observe** the live app," while D78 makes `verify` the capture home for the
living code-map's observed layer ("it already executes the affected flow", `06-knowledge.md:148`). **Call:**
"artifact-only" governs `verify`'s **verdict/gate**, not its **observation** — `verify` **may drive** the affected
flow to observe *which edges fire* (D78's `[D]` layer), but strictly as a **pure observer**: what it observes never
feeds the conformance verdict; runtime *behaviour* correctness stays `debug`, live-app confirmation stays
`checkpoint`. *Rejected:* keep `verify` fully pure + move D78's capture home elsewhere (reopens an
empirically-settled decision — D78 chose `verify` *because* it exercises the flow); let `verify` judge runtime
behaviour (collapses the D24 verify/debug split). *Evidence:* register P6 (`verify:9-10,30` vs D78;
`06-knowledge.md:148`, which already frames `verify` as a "pure observer" and so stays consistent as written).
**Phase-2 revisit:** the reconciliation is wording-level today (D78's observed layer is unbuilt) — revisited
concretely when the living code-map lands. → `skills/verify/SKILL.md`, `11-roadmap.md` (deferred note).

---

## D84 — The skill/agent line gains a context-isolation axis: heavy non-fan-out nodes are leaf agents; fan-out controllers stay thin skills (refines D27) **[DECIDED — rule + roster annotation; the physical reclassification is deferred to a dedicated session]**
Origin: the pressure-test **resolve phase** (cluster 2 — the residual left when the D27 "skills-as-subagents
barred" lead was *refuted*). D27 drew the skill/agent boundary on **one** axis — *does it fan out?* (adjudicators
fan out → skills; leaves never spawn → agents). It missed the second: **a skill runs *inline in the
orchestrator's context*; an agent runs *isolated* and returns a thin pointer.** So a heavy skill like `execute`
(reads a plan, edits many files, runs tools) pollutes the very context the orchestrator brief swears to protect
(`orchestrator:5-6`, `:11-15` — "thin router… context is the scarce resource"). **Calls:**
- **The boundary is drawn by BOTH axes.** A node is a **leaf agent** (isolated) when it does heavy autonomous
  work AND neither fans out nor holds the human conversation — its context cost stays off the hub. It stays an
  **inline skill** when it is (a) a **fan-out controller** — *must* be a skill, since a leaf can't spawn
  (`verify`/`debug`/`decision-engineer`/`planner`/`prioritize`/`align`); (b) **human-interactive**
  (`discuss`/`checkpoint`); or (c) **thin bookkeeping** (`commit`/`create-issue`/`close-issue`/`refine`).
- **Fan-out need beats heaviness** (maintainer's ruling). A heavy controller is **not** demoted to an agent —
  that would break its view-gathering (a leaf can't spawn). The discipline instead is *authoring-thinness*: push
  the heavy reads into the agents it spawns, hold only thin summaries inline (`orchestrator:13-14` already asks
  this; D84 makes it the controllers' standing rule).
- **Reclassification targets: `execute` + `create-demo` → leaf agents.** `execute` = heavy, zero-decision, no
  fan-out (a structural divergence already escalates to the hub); `create-demo` = heavy sandbox build whose
  `checkpoint` call is hub-sequenced anyway. `document` **stays a skill** for now (borderline weight). `ingest`
  **stays a skill** — it spawns `research` (can't be a leaf), and its cost is a one-time brownfield-init, not
  per-loop.
- **Reclassifying CLEANS the node:** routing leaves the agent and lives in the hub/`loop.md` where it belongs (an
  agent returns a result; the hub follows the edge — a leaf shouldn't own its own `Route`).
- **Rule + roster annotation captured now; the physical work is DEFERRED to a dedicated session** —
  validation-blocked (the context saving can't be measured until the loop runs; the bus is unbuilt). That session
  does the `skills/{execute,create-demo}` → `agents/` file moves, the agent-format rewrites, the orchestrator's
  **dispatch-by-kind** wiring, and the resulting `10` count + `11` (`17 skills + 2 agents` → `15 + 4`) update.
*Rejected:* reclassify-by-heaviness-alone (demotes `verify`/`debug` to leaves → breaks fan-out → needs a
two-level-agent topology, reopening D27); a **hub-mediated leaf-agent `ingest`** (adds hub round-trips to a
one-time init path — deferred; S13's `ingest`↔`research` charter issue is a later cluster); doing the physical
moves **now** (unvalidated until the loop runs — churn risk the maintainer chose to avoid). *Evidence:* register
§2B D27 adjudication (refuted lead → this residual); `orchestrator:5-6,11-15` (thin-router invariant) vs the fact
that skills run inline; the roster kinds (`10`). Refines D27 (adds the context-isolation axis); serves the master
rule (protect the orchestrator's context). → `10-roster.md` (annotation), `11-roadmap.md` (deferred item); the
physical reclassification → a dedicated future session.

---

## D85 — Resolve phase, cluster 3: routing/contract gaps closed — brownfield routed, checkpoint fail-by-kind, a `reconcile` kind, escalation off-ramps **[DECIDED + BUILT]**
Origin: the pressure-test **resolve phase** (cluster 3 — routing/contract gaps in `loop.md` × the skill Routes,
the class `check_contracts.py` re-finds). **Design calls:**
- **Brownfield is routed (G4).** `ingest` had no `loop.md` node. Added a brownfield **start-branch**:
  `/start`(brownfield) → `ingest` → `checkpoint:reconcile` → `prioritize`. Chosen over "ingest is a bootstrap
  step *outside* the loop" — routing it makes the graph total and satisfies the contract linter.
- **A `reconcile` checkpoint kind (G11).** ingest's reconstructed-spec confirmation is neither a feature-test
  (`qa`) nor a manual external step (`setup`) — a fourth kind `reconcile`, added to the checkpoint enum + skill +
  loop.
- **Checkpoint fail routes by KIND (S2).** All-fails→`debug` was wrong — a demo rejection or a failed manual
  setup is not a defect. Now qa→`debug`, demo→`create-demo`, setup→`setup-guide`/human, reconcile→`ingest`/`discuss`.
- **Escalation off-ramps (G21/G22/G25).** `adjudicate`'s `escalate?` was promised but unconsumed and `debug`'s
  confidence loop could spin. Now `debug`/`verify` **escalate → a human `checkpoint`** when no resolution
  survives a bounded retry budget (bounded, not infinite).
- **Mechanical edges, same commit:** `execute` structural-divergence → `planner:plan-one` re-plan (G3); a
  **per-item** `create-demo` gate → `execute` (G17); `idle`→`prioritize` wake on steering/side-door (G19);
  `refine`'s input is a `debug-report` *via* `debug`, never a raw `verify-verdict` (S17); `plan-delta` defined in
  `schemas.md` + accepted by `planner` (G14); create-issue "prioritize re-runs" reworded to the next-pick /
  idle-wake truth (G30); close-issue comments the SHA only **post-push** (G29).
*Rejected:* ingest-as-bootstrap-outside-the-loop (leaves the brownfield entry unrouted — the linter's whole
point); all-fails→`debug` (conflates a product-fit rejection with a defect); an unbounded `debug` confidence loop
(spins forever). *Evidence:* register §6 G3/G4/G11/G14/G17/G19/G21/G22/G25/G30/S2/S17; `loop.md` × the skill
Routes; `check_contracts.py` re-finds the routing class. → `templates/loop.md`,
`skills/{checkpoint,refine,planner,debug,verify,create-issue,close-issue}`, `shared/schemas.md`, `10-roster.md`.

---

## D86 — Resolve phase, cluster 4: schema producer/consumer contracts aligned — `boundary` on the criterion, unbound `test_ref`, one backlog ordering key, closeable local issues **[DECIDED + BUILT]**
Origin: the resolve phase (cluster 4 — schema producer/consumer mismatches, mostly caught by ground-truth
reading, not the linter). **Design calls:**
- **`boundary` lives on the criterion, and is resolved there (S5).** `check_promise_coverage.py` read `boundary`
  off the *promise*, but schemas/planner put it on the acceptance-*criterion* → false-block. The `promises.json`
  `criteria[]` now carries `boundary`; the gate resolves a universal's boundary via its **linked criterion**
  (legacy-promise fallback kept). +3 tests.
- **Promise `test_ref` binds at `planner`, not `decision-engineer` (S7).** decision-engineer runs *pre*-planner,
  so the criterion a promise discharges doesn't exist yet — it emits `test_ref: null`; `planner` binds it when it
  writes that criterion (promise-coverage runs there).
- **One uniform backlog ordering key (G13).** `prioritize` orders on `depends_on × kind × severity`, but no
  producer emitted all three. Now `issue` carries `depends_on[]` and `planner:decompose` tags each phase-item
  `kind` + `severity` — one key across both producers.
- **Local-only issues are closeable (G8).** `github_ref` is now **optional**; a greenfield issue with no ref is
  closed by its backlog **done-flip** (rides the item-tail commit) → `prioritize` GCs it, `close-issue` exits
  quietly. No backlog leak.
- **`locked-candidate` resolved into the enum (S3).** `discuss` tagged flow/scope `locked-candidate` (∉ the
  three-state enum; nothing resolved it). Now flow/scope are `provisional` + flagged **lock-on-approval** (the
  demo/reconcile gate flips them to `locked`); the linter's enum advisory clears.
- **Contract fixes:** decision-engineer Output emits `id`/`status` (S6) + takes the code-map **impact flag** as
  an Input (G15); `document` Inputs add the `spec`/`commitment` its own rules need (S11); `ingest` **seeds nodes
  itself** — `document` is not called during ingest (S12).
- **G16** (nothing mirrors `plan.promises` ↔ `decision-record.promises`) is owned by **`align`'s semantic layer**
  (the promise↔plan-mirror lens baked in at D81) — no new mechanical gate.
*Rejected:* boundary-on-the-promise (the tag's home is the criterion); a decision-time `test_ref` (points at a
criterion that doesn't exist yet); a 4th commitment state for `locked-candidate` (the three-state enum + a
lock-on-approval *behavior* suffices); a standalone promise-mirror gate (`align` covers it). *Evidence:* register
§6 S3/S5/S6/S7/S11/S12/G8/G13/G15/G16. → `scripts/check_promise_coverage.py` (+ test),
`skills/{discuss,decision-engineer,document,ingest,planner}`, `shared/schemas.md`.

---

## D87 — Resolve phase, cluster 5: guard/permission hardening — the ≥5 guard bypasses closed, obscured outward actions gated, staged-diff atomicity + a git-native backstop **[DECIDED + BUILT — two corrections by D110: (1) the chaining-block's *rationale* changed — a direct `git push`/`gh issue` no longer meets a settings `ask` prompt (it would block the away-release), so the block now exists to keep the refspec parseable by `guard.sh`'s own push floor; (2) claim (b) below was FALSE AS BUILT — `git -c core.pager=cat commit` **did** slip past (the flags-only regex breaks on any global option taking a *separate value*: `-c k=v`, `-C path`). Empirically re-found and fixed in D110 by parsing the subcommand.]**
Origin: the resolve phase (cluster 5 — the highest-severity attacker surface: `guard.sh` was crossable ≥5 ways
[S1], the outward gate had holes [G7], the commit-split was non-atomic [P8]). **The fixes (all tested):**
- **guard.sh (S1):** (a) **fail-CLOSED without python3** — matches the raw hook payload when the parsed command
  is empty, so removing python3 can't disable the gate; (b) **robust `git … commit` detection** — a regex that
  tolerates `-c`/`--flag` args (`git -c core.pager=cat commit` no longer slips past the old literal
  `*"git commit"*`); (c) **secret-scan expanded** — adds GitHub PAT (`gh[pousr]_`), Slack (`xox[baprs]-`), Google
  (`AIza…`), Stripe (`[sr]k_live_`) to the AKIA/PEM/assignment set; (d) **verify-gate hardened** — a set item
  with a **missing** verdict now blocks (not only a failing one), and the pass-regex tolerates markdown
  (`- **pass:** false`) so a fail can't hide behind emphasis.
- **Obscured outward actions (G7).** A *direct* `git push`/`gh` still goes to the settings `ask` prompt; guard.sh
  now **blocks ones hidden in a chain/subshell** (`x && git push`, `$(git push)`, `; gh pr create`) — the
  literal-prefix `ask` matcher can't see those, so they'd otherwise run under `allow`. Deploy/release scripts
  (`npm run deploy`, `make release`, …) added to the `ask` list. **Accepted trade-off:** `WebFetch`/`WebSearch`
  stay in `allow` — web egress is inherent to the autonomous research loop; the exfil-sensitive gate is on
  outward *writes*, not reads.
- **pre-commit.sh (P8 + the S1 git-native backstop).** Now (a) **validates the STAGED diff** — stashes unstaged
  changes `--keep-index` (trap-restored) so a two-commit split stays atomic; and (b) carries the **secret-scan +
  verify-gate itself**, so a commit via a path the PreToolUse hook never sees (a `make` target, an editor/IDE
  commit) still hits both gates.
*Rejected:* hard-blocking a *direct* `git push` (the design keeps push an `ask`, not a forbid — only obscured
ones are blocked); moving `WebFetch`/`WebSearch` to `ask` (prompts on every research call → breaks autonomy); a
bare-AWS-secret-key pattern (40-char base64 is false-positive-prone — the AKIA access-key id is the high-signal
catch). *Evidence:* register §6 S1 (`guard.sh:15,26,29-30,37`), G7 (`settings.json:11-12,16`), P8
(`pre-commit.sh`); tested — robust commit detection, obscured-outward blocked, all 5 secret patterns caught,
markdown verdict handled, no false positive on `cat deploy.md &&`. → `hooks/guard.sh`, `hooks/pre-commit.sh`,
`templates/settings.json`.

---

## D88 — Resolve phase, cluster 6: ingest hardened, principle clarifications, a decision-coverage gate, and the P/S/G tail **[DECIDED + BUILT]**
Origin: the resolve phase (cluster 6 — the principle tail, the retention/codemap script bugs [landed in the 6a
commit], and the gap/skill tail). **Design calls:**
- **Ingest hardened (S13/P9/G12) — one decision.** (a) `research` **gathers** only; **`ingest` synthesizes** the
  reconstructed spec (S13 — respects research's gather-only charter); (b) the behavioural core is recovered
  **first**, so node-purpose seeding prioritises **spec-core ∪ both centrality lenses, never centrality alone**
  (P9 — honors D68's core≠central); (c) a **thin/absent-docs fallback** (the common case) — recover from
  entry-points + both lenses, tag more `unspecified`, widen the reconcile checkpoint (G12).
- **`--fix` ordering + scope (P5).** `checks.sh --fix` is **scoped to the item's staged files** (never a
  repo-wide sweep into the atomic commit) and is **zero-semantic** (format/lint/ref-strip) so it needs no
  re-verify; anything behavioural is never auto-fixed. A **hard, non-auto-fixable** check error now routes
  `commit` → `debug`/`refine` (G23), not "proceed."
- **D48/D54 reconciled (P7).** "Committed while the item is open" applies to the `.workflow/items/<id>/`
  **artifacts** (crash-survival), not the product **code** — the code is still one commit at item close. Two
  objects, no contradiction.
- **Side-door boundary (P10) + drive-trigger (D50).** blocking-THIS-item's-DoD → in-loop (`debug`/`refine`); an
  independent incidental find → `create-issue` → backlog, never a competing this-item failure. The orchestrator
  drives only when `state.json.status` is an active run (`building`/`intake`), not merely because `.workflow/`
  exists.
- **A decision-coverage gate (G6).** `check_decision_coverage.py` (+ test) — the third mechanical plan-coverage
  sibling — blocks a governing decision mapped to no plan step; `planner` writes the `{id,steps}` mapping to
  `promises.json`; wired into `checks.sh`/`start.md`.
- **Contract/skill tail:** `execute` runs each artifact criterion's **discharging test** (G5 — completes D82);
  `document` ships the strict `## [date] kind | title` Sessions header retention parses (G24); the sandbox gate
  is **single-owner** so debt is filed exactly once (G18); `create-demo` Calls += `create-issue` (S14);
  `research` output is consistent — `findings` is returned, the caller persists the distillate (S16);
  `adjudicate`'s threshold is sourced from `config.run` (G26); the `spec`'s on-disk path is pinned
  (`docs/spec.md`, G28); `commit` type defaults `chore` when `kind` is absent + bookkeeping is a workflow step
  (G23).
- **Deferred (recorded, not lost):** P2 — retention **distills** a postmortem to a one-line Lessons pointer
  before drop (rule captured; the Lessons mechanism stays deferred); P3 — wiring `risk_class` into the D69
  proportional-rigor triage rides D69's deferred impl; P4 — the static impact-lens inversion for DI/indirection
  code is an accepted limitation, mitigated by D78's observed layer; G16 owned by `align`'s semantic layer.
  Script bugs (S4/S8/S9/S15, G27; **S10 refuted** — already disclosed as a `known_gap`) landed in the 6a commit.
*Rejected:* research-synthesizes-the-spec (over-charter); seed-by-centrality (core≠central); re-verify after
formatting (zero-semantic needs none); an active-decision retention trigger (retention can't reduce it → thrash).
*Evidence:* register §6 P2/P3/P4/P5/P7/P9/P10/S13/S14/S16/G5/G6/G12/G18/G23/G24/G26/G28 + the D50 lead. →
`skills/{ingest,commit,execute,document,create-demo,discuss,planner,adjudicate}`, `agents/research`,
`templates/orchestrator-CLAUDE.md`, `shared/schemas.md`, `scripts/check_decision_coverage.py` (+ test),
`commands/start.md`, `scripts/check-no-spec-refs.sh`; the script fixes are in the 6a commit.

## D89 — Doc↔artifact drift: a three-tier defense + the base-skill linter fix; bash/python split reaffirmed **[DECIDED + tier-2 BUILT]**
The pre-Phase-2 `align` **cold-audit** (the full-surface read-only fan-out the `align` skill reserves as an
explicit one-off, D81) found **10 doc↔artifact coherence findings** (+ the earlier `ingest`-"being authored"
drift), all one root cause: a later decision **superseded a state** (checkpoint `reconcile` kind D68; five-arm
closure D77/D79; interrupt-model close D26) and the **capture-time blast-radius sweep (D80) was skipped for the
terse/secondary surfaces** (skill frontmatter, roster rows, roadmap snapshots). The existing mechanical gates are
prose-blind (`check-status-coherence.sh` = counts/D-ranges/tags; `check_contracts.py` = routing graph), and most
drift was **born before `align` existed** (2026-07-02/03 vs D81 2026-07-04), so diff-scoped `align` never saw it —
the D80/D64 "honest residual" proven on the repo itself.
- **Tier 1 — prevent at capture:** the D80 blast-radius sweep stays primary; tiers 2–3 back it, not replace it.
- **Tier 2 — mechanize the decidable slice (per-commit, BUILT):** `scripts/check_enum_coherence.py` — **ENUM**
  presence-coverage (owner declares the set: checkpoint `kind` in `shared/schemas.md` → every restating consumer
  must mention every value) + **COUNT** (a registry's size: code-map precise arms in `codemap.py`'s `ARMS` → each
  "N precise arms" claim must equal it). Presence/count only (prose stays `align`'s semantic layer); meta-repo only
  (reads spec docs that never ship) → wired into `.git/hooks/pre-commit` beside `check-status-coherence.sh`.
  Reproduced the fixed drift → green.
- **Tier 3 — detect the rest (periodic):** the full-surface cold-audit adopted as a **phase-boundary ritual**,
  since diff-scoped `align` is pre-anchor-blind.

**Linter FP:** the `adjudicate` coverage-gap advisory was a false positive — `adjudicate` is an **abstract base
skill** (specialized by `verify`/`debug`/`decision-engineer`, "not invoked directly"), consumed by inheritance not
routing. `check_contracts.py` now exempts base skills → **0 advisories** (a standing false advisory trains you to
ignore the gate).

**Bash/python split reaffirmed (D71 stands, no refactor).** A maintainer question ("didn't we move everything to
Python for all OSes?") was a scope error: D71 decided **thin glue = bash; parse/rewrite = Python** (cross-OS was
the *Python* rationale for parse-heavy work, not a blanket move). The real residual is narrower and now tracked:
the **shipped bash glue** (`guard.sh`, generated `checks.sh`/`codemap.sh`) assumes a **bash interpreter on the
target OS**, unverified on **native Windows** (git-invoked `pre-commit.sh` likely survives via Git-Bash; the
Claude-Code-invoked glue is the risk). Since `python3` is already a hard dependency, the eventual fix is a targeted
fallback (thin Python launcher / documented Git-Bash requirement), NOT a rewrite.
*Rejected:* a blanket `.sh→.py` refactor (contradicts D71, trades "needs bash" for "needs python3-in-hook",
clumsier glue); a prose-negation lint flagging "remaining/stub" near an artifact (NLP-fragile, high false-positive
→ stays `align`'s semantic layer); folding the enum check into the shipped `check_contracts.py` (it reads
`10-roster.md`, which never ships → keep it a meta-repo gate).
*Evidence:* the cold-audit register (10 findings across `checkpoint`/`create-demo`/`planner`/`commit`/`02`/`06`/
`10`/`11`, 2 dropped as non-drift after reading `loop.md`); D80/D64, D71, D81/D63. → `scripts/check_enum_coherence.py`
(+ test), `scripts/check_contracts.py` (+ test), `.git/hooks/pre-commit`, `07`, `11`.

---

## D90 — Checkpoint block/resume: a checkpoint is a durable *park boundary*, resumed by `claude --resume` with the verdict as an authoritative prompt **[DECIDED — empirically verified, Phase-2 A1; the *notify* mechanism corrected by D111 (the always-alive daemon owns the alert — the `Notification` hook cannot fire while the loop interleaves, cannot reach an away human, and is dead when the loop whole-parks); the deferred restart-runner pulled into MVP by D113]**
A blocking human checkpoint is a **durable park boundary**, not a live in-session wait. At a checkpoint the
orchestrator writes the graceful handoff (park → `document` → `commit` → `handoff.md`) + the verdict-request to
disk, then **yields**. Resume is **`claude --resume <id> -p "<verdict>"`** — the verdict rides as the *resume
prompt* (an authoritative user message); a `SessionStart` hook only re-points to durable state (hook-injected
context is treated as *untrusted background*, so it can **not** carry the load-bearing verdict). If the session
store is gone, cold-start from `handoff.md` + `git log` (D48). The restart **trigger** scales with autonomy on one
unchanged contract: **manual in MVP** (a console prompt) → an **OS-scheduler / headless-loop runner later**. Notify
an away human via the `Notification` hook (desktop native; opt-in Slack/HTTP webhook; phone/tunnel later).
- **Why:** nothing inside Claude can self-wake (no background-exit re-invoke, no hook that wakes an idle model, no
  scheduler) — so "hold the session open and block" can never be the foundation; resurrection is inherently an
  *external* trigger. The durable park reuses D48 and is crash-safe by construction. Verdict-as-prompt because
  `SessionStart`-injected context is under-weighted by the model.
- **Runner reframe:** the deferred autonomous-restart path is a **local relaunch loop**, NOT the Claude Agent SDK —
  the SDK runs *cloud* managed agents and **cannot resume a local session** (verified); the only legal autonomous
  path is a thin local process that relaunches `claude` on the user's own machine/auth (supersedes `01`'s "SDK
  runner" wording).
*Rejected:* an in-session blocking **MCP tool** as the foundation (~5-min idle ceiling, per-server timeout override
currently broken, dies on machine sleep — kept only as an optional *user-present* fast-path); a **background-waiter
/ wake-on-exit** (Claude Code does **not** re-invoke the loop when a background task exits — verified); a **cloud
SDK / managed-agent** runner (off-machine, breaks local-only); a **model-driven poll loop** (token burn).
*Evidence:* four research fan-outs (harness wake/blocking · MCP-as-bus · restart/resume/notify · divergent HITL
patterns) + empirical tests on shipped **`claude v2.1.209`**: `--resume <id>` restores full context across process
death (same session id); `SessionStart`/`Stop` fire headless (even untrusted); `SessionStart(source=resume)` injects
context but the model flags it *untrusted*; `/clear` is scriptable but **not** self-invokable; store =
`~/.claude/projects/<cwd>/<uuid>.jsonl`. Reuses D48; refines `01` Session-lifecycle + `04`. → `01`/`03`/`04`/`05`/`07`/`11`.

## D91 — Continue-while-parked: the single orchestrator **interleaves** to the next *independent* ticket while one is checkpoint-parked (Design 2) **[DECIDED — Phase-2 A1 extension]**
While a ticket is parked awaiting a human verdict, the **single** orchestrator continues to the next *independent*
ticket rather than idling; the whole-loop park ("Design 1") is the **degenerate "nothing eligible"** case. It is
**interleaving, not parallelism** — exactly one ticket in active development at a time, others suspended on disk.
Mechanics (three ground-truth research fan-outs — industry standard, not reinvented):
- **Isolation** — `git worktree`-per-ticket on its own branch + a `WIP:` park-commit for durability; park = leave
  the dirty worktree on disk; resume = un-WIP (`reset --soft`) → `rebase` onto trunk (`rerere` on) → `verify` →
  final commit → merge → `worktree remove`. Raw `git worktree` — **not** `claude --worktree` (which spawns a
  session-per-worktree, violating the single-orchestrator call). **Reject `stash`** (private LIFO, not for an
  hours-long hold).
- **Independence predicate** (off the code-map `graph.json`) — a candidate is eligible iff **dependency-ready** ∧
  **file-disjoint** from every parked ticket (*hard gate*) ∧ **not a 1-hop code-map neighbor** of a parked ticket's
  files (*soft gate*). Pass all → clean start; pass-hard/trip-soft → start **flagged** for raised integration rigor
  (full `verify` + rebase-onto-current-base = a local speculative-merge); fail hard → **never start**. No hard-clean
  candidate → **park the whole loop**, spend the wait on read-only work (plan/research). Dependency graph, **not**
  co-change (D78).
- **Scheduler** — non-preemptive, **item-level**; boundary order = **resume-a-ready-parked-ticket first**
  (oldest-verdict-first + **aging** anti-starvation) → start-new → sleep. The boundary check is **plain code, not an
  LLM call**.
- **Correlation** — a per-checkpoint **token** (`{ticket}:{step}:{uuid}`) + an on-disk parked record (token, resume
  state, `predicted_outcome` (D69), deadline) + an **append-only file inbox** the bus writes into (atomic
  write+rename = durable, at-least-once), matched at boundaries **idempotently, single-shot**; token→unknown/closed
  ticket = **dead-letter + surface** (never a silent resume); duplicate = no-op; timeout → **escalate**. Crash
  recovery rebuilds from `parked/` + `inbox/`.
- **Bounded** ≤3 concurrent parked+active (DORA "≤3 active branches"); **prefer serial — interleave only when
  forced by a park.**

This **pulls Space-1 "waves" into MVP** as *bounded interleaving* (not a parallel farm) and **closes the long-open
collision-independence test** (`01`/`10`/`07`).
*Rejected:* preemption / mid-item interrupt (D26 pure-queue stands); real concurrency / parallel writers
(Cognition's incoherence warning; single machine); a distributed token store / broker (files suffice); heartbeating
(the decider is a human — a deadline timer is enough); per-item Claude sessions or a scheduler-daemon for the
interleaving itself (single orchestrator).
*Evidence:* three research fan-outs (execution isolation → worktrees, incl. Claude Code's native worktree support;
task-independence → monorepo affected-set + merge-queue optimistic-integration; async-HITL scheduling+correlation →
Step-Functions `.waitForTaskToken` shrunk to one machine). Reuses D24/D26/D48/D69/D78; extends `handoff.parked[]` to
load-bearing; `prioritize` gains the predicate; `verify` owns the rebase/speculative-merge; the bus owns the inbox.
→ `01`/`03`/`05`/`07`/`09`/`10`/`11`/`shared/schemas.md`.

## D92 — Context management: the conversation is disposable; the orchestrator stays thin via subagents; auto-compact is a *within-run seatbelt*, not the cross-ticket strategy **[DECIDED — Phase-2 A1 extension; the runner **deferral is REVERSED by D113** (it is the away-channel's last link, and this decision's "preserve the pure-config MVP" reason expired once D94 shipped a detached daemon) — which also retires the manual-`/clear` MVP stopgap below]**
The orchestrator's **conversation is disposable — `handoff.md` + git are authoritative** (D48/D51). Heavy per-ticket
work runs in **fresh subagent windows** (each returns a thin summary), so the orchestrator's resident context stays
thin and barely grows across tickets — the mature long-running-harness pattern (Anthropic: fresh window + progress
file + git). **Auto-compact is a *within-run seatbelt* only — NOT the cross-ticket memory strategy.** In-session
self-`/clear` is **impossible** (no `SlashCommand` tool; skills can't invoke slash commands; `/clear` waits for
human input; `SessionStart` can't trigger an autonomous turn interactively) → the "skill that runs `/clear`+`/start`"
idea is **dropped**. A true per-ticket clean-reset is a property of the **deferred headless-loop runner** (each
ticket = a fresh `claude -p` process = a clean window for free; the loop lives in stateless bash/SDK, so nothing
accumulates) — the **same** runner as D90's autonomous-resume path, now **triple-justified** (context-reset +
autonomous checkpoint-resume + overnight). **MVP stopgap** for the single interactive session: a **manual alert**
prompts the human to clear context + re-run `/start` (rehydrate from `handoff.md`) once the orchestrator is
polluted — accepted; there is no autonomous in-session way around it for now.
- **Why:** leaning on auto-compact cross-ticket imports real failure modes over hours-long unattended runs
  (thrash-stall — a *safe hard-stop*, cross-ticket amnesia, silent constraint-drop, re-derivation) and context-rot;
  we've already paid the expensive part (externalized state), so clean-reset is nearly free and keeps every ticket
  in the model's high-accuracy short-context regime.
*Rejected:* a skill that self-invokes `/clear`+`/start` (mechanically impossible — verified); auto-compact as the
cross-ticket memory strategy (lossy, cumulative failure); pulling the runner into MVP (kept deferred to preserve the
pure-config MVP — the manual-alert stopgap bridges it).
*Evidence:* measured `/compact` reclaim **~63%** (66.9k→24.6k) on `claude v2.1.209`; `autoCompactEnabled` (on/off) +
**`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`** (threshold) confirmed; a documented `Autocompact is thrashing` hard-stop (only
on a single huge output — avoided by subagent/code-map offloading); official tools reference has **no `SlashCommand`
tool**; two fan-outs (auto-compact mechanics · long-loop context best-practice → Anthropic "Effective harnesses for
long-running agents" + "context engineering", Manus, Cognition, context-rot benchmarks). Reuses D4/D48/D51; refines
`01` Session-lifecycle. → `01`/`07`/`11`.

## D93 — Bus contract: single-writer ownership + atomic-publish + a two-mechanism protocol (sync reads · async commands); one typed inbox — the orchestrator is never an HTTP responder **[DECIDED — Phase-2 A2, research-backed; two arms revised by D114: this decision's *enumerations* (the served-read set + the native-FS pin set) are retired as prose and re-owned by `05`'s layout tree — they had drifted at every touch — and the "the committed artifacts stay in the repo (git doesn't need rename-atomicity)" rationale is corrected as a non-sequitur (three committed files are `bus:read`, so the *bus* reads them across the weak mount; the exposure is bounded to GC lag + a self-healing render, and now says so)]**
The A2 bus contract closes on three rules. **(1) Ownership = a single-writer partition, zero co-written files:** the
orchestrator is the sole writer of `state.json` / `handoff.md` / `backlog.md` / `parked/` / `items/` + git; the bus is
the sole writer of `inbox/`; everyone else reads. **UI-originated work never writes the backlog directly** (that would
make it two-writer) — it lands in the bus-owned inbox and the orchestrator **promotes** it into `backlog.md` at a
boundary (through D69 triage). `flock` is **unneeded** — single-writer removes the write-conflict class (and the
advisory-lock minefield with it). **(2) Atomic-publish** (write-temp → `fsync` → `rename` → `fsync(dir)`) on **every**
file that crosses the process boundary — including `state.json` (its "rewritten in place" is *logical*, not physical;
a torn read is the failure mode), with `handoff.md` additionally needing the dir-fsync **durability** (the resume
anchor). **(3) Protocol = two mechanisms, no third:** synchronous **reads** the bus serves straight from disk (GET, no
orchestrator involvement) + asynchronous **commands** (`202 Accepted` + a `Location` ticket → append to `inbox/` →
consumed at a scheduler boundary → result surfaces via orchestrator-written state the UI re-reads by ticket). **The
orchestrator is never an HTTP responder** — the direct consequence of D90 (a boundary batch-consumer, not a server),
so a synchronous request→orchestrator→response path *cannot exist*. **One typed inbox** (`kind: verdict|intake|control`),
**single consumer** (the one orchestrator, so no `processing/`-claim dance), matched **idempotently, single-shot** (D91).
SQLite-WAL is the **reserved escape hatch** — adopt only on a genuine cross-file atomic invariant / consistent
multi-file snapshot / indexed large-backlog query, never hand-roll a second writer instead.
- **Conversation model (the conversation corollary):** because the loop is a batch consumer, the console is **not and cannot be
  a real-time chat**. New-feature *dialogue* happens at the **terminal** (the live session = the `discuss` stage); the
  bus carries only *requests* (async intake → a D69-triaged backlog item) + *bounded clarifications* (an
  orchestrator-parked checkpoint question). A future console "chat" would be async-turn-based (latency = the boundary
  cadence), never live. So conversation isn't lost to the async reframe — it lives in the live session, not on the bus.
- **Why:** single-writer + atomic-rename is the sound DB-free coordination substrate for a single host (Maildir/spool
  discipline) and dissolves the advisory-lock problem entirely; "no synchronous orchestrator response" is *forced* by
  A1, not chosen — naming it stops a later impossible build. The backlog is the one file that would otherwise be
  two-writer; routing intake through the inbox is what preserves the invariant.
*Rejected:* intake written straight to `backlog.md` (two-writer → corruption); `flock`/advisory locks (unreliable over
NFS, silently drop on any-fd-close, unneeded under single-writer); a synchronous orchestrator endpoint (physically
impossible); SQLite up front (premature — files suffice until a cross-file invariant appears); a real-time console chat
(the batch loop forbids it — any console chat is async-turn-based).
*Evidence:* a file-IPC / async-comms research fan-out — POSIX `rename` atomicity + the `write→fsync→rename→fsync-dir`
recipe (lwn), Maildir + systemd-journal single-writer/lock-free discipline, at-least-once + idempotent-consumer,
Microsoft **Async Request-Reply** (`202` + status-resource + correlation id), SSE-vs-poll (SSE is ergonomics not
architecture for a batch worker), the `EXDEV`/Windows-`os.replace` caveats, and the SQLite-WAL escape trigger. Reuses
D26/D48/D51/D69/D90/D91. → `03`/`04`/`05`/`shared/schemas.md`/`07`/`11`.

## D94 — Website/bus lifecycle: a session-independent detached daemon, ensure-running via lock-authority, stop via HTTP + idle-janitor **[DECIDED — Phase-2 A3, research + empirical; BUILT and three arms corrected by D115/D116: (1) the lock lives on its own `bus.lock` — a lock held on the atomically-renamed `bus.json` is silently defeated, measured on both filesystems, and this entry named no lock path at all; (2) the "`flock` on DrvFs is weak-to-broken" premise behind pinning it native-FS is **false as measured** — `flock` excludes correctly and releases on death on 9p, so the pin survives on *mode* and *rename*, not this; (3) "heartbeat-aware idle-timeout" defined neither word — D116 makes idle a conjunction of per-job votes that an open checkpoint suppresses, and the heartbeat is explicitly never the orchestrator's]**
The bus is a **session-independent detached daemon** — its lifecycle is **decoupled** from the orchestrator
conversation, because it must receive verdicts *while the orchestrator is parked or dead*. Detach with a **new session**
(`setsid` / `start_new_session`, **not** `nohup`/`disown`) — empirically confirmed to survive `/clear`,
`claude --resume`, and session death on `claude v2.1.209` (Claude Code does **not** reap background children and ships
no cleanup). `/start` is **ensure-running (adopt-or-spawn), idempotent**: liveness authority is a **held `flock`**
(kernel-released on death → race-free singleton election, PID-reuse-immune) **plus** a token'd `/health` 200; the daemon
publishes `{pid, port, token, started_at}` to `.workflow/bus.json` (atomic write, gitignored, dynamic **loopback** port
bound `127.0.0.1:0` and read back, per-project). **Never spawn-fresh per session** (drops in-flight verdicts). **Stop =
an authenticated `POST /shutdown`** (OS-uniform; Windows has no SIGTERM) + a long, heartbeat-aware **idle-timeout
self-shutdown** (the orphan janitor Claude Code doesn't provide). **WSL2 caveat (owner-accepted):** a detached Linux
daemon can't hold the distro VM open, so on WSL the bus dies ~8s after the last terminal closes and re-spawns on the
next `/start` — the durable inbox loses nothing already-written; `loginctl enable-linger` / `.wslconfig
vmIdleTimeout=-1` are the documented opt-in upgrade.
- **Why:** nothing may block a live session (D90), so the away-channel must outlive session churn and therefore can't be
  a session child. Lock-as-liveness beats a pidfile (immune to PID reuse); HTTP-stop beats signals (cross-OS). Closest
  real-world analog is **Syncthing** (loopback API on a discovered port, token in config, self-managed process,
  service-install optional).
*Rejected:* spawn-fresh-per-session (drops verdicts — a trap worth naming so nobody "simplifies" into it); a pidfile as
liveness authority (PID reuse); a per-user service manager for MVP (systemd `--user` / launchd — only buys
reboot-survival we don't need, with WSL the sole asterisk); `nohup`/`disown` (stay in-session, die on process-group
reap).
*Evidence:* a detached-daemon research fan-out (new-session vs SIGHUP-ignore mechanics, `flock` singleton +
health-check adopt, ephemeral-`:0` + portfile discovery, idle-timeout precedent `git-credential-cache--daemon`, the
WSL2 VM-lifecycle kill) + a Claude-Code process-reaping fan-out with **empirical v2.1.209 tests** (background children
orphan to PID 1 and survive; `--resume` loads context not processes; `/clear` is context-only; no `SessionEnd` default
cleanup). Reuses D48/D90/D92. → `03`/`05`/`07`/`11`.

## D95 — Local-bus trust: the browser/network is the untrusted caller, not same-UID; capability token + Host-allowlist + loopback bind **[DECIDED — Phase-2 A4, research-backed; the loopback stack STANDS unmodified on the full-surface socket, but two arms are revised by D112: the *unauthed tunnel* is retired (it contradicted this decision's own token rule), and "token never in a URL" is sharpened to "never in the query/path" — a URL *fragment* never leaves the browser and is the QR pairing channel. Two further arms completed by D115/D116: (1) **the "atomic 0600 create" discipline is a NO-OP on a mount that ignores mode** — measured, the WSL repo mount returns 0777 silently, so a faithful implementation of this entry yields a world-readable token and reports success; the rule becomes *create with the mode, then `stat` it and surface a filesystem that ignored it*, and "Windows has no 0600" widens to "any mount that ignores mode" (this entry's framing made it read as a portability footnote about a platform we don't ship on — it is live on the maintainer's own machine); (2) the **local page's token bootstrap**, left unspecified here and conceded in the register, is a `<meta>`-tag injection whose concession is now stated: whoever can GET the page from an allowlisted Host holds the token, which is exactly the audience the token-free static class already conceded, and the *Host check* — not the token — is what stops a rebound page]**
The trust boundary is **not** "same-UID local processes" — a same-UID process can already `ptrace` the orchestrator and
read its files, so defending against it is theater — it is **"the browser and the network are untrusted callers."** The
MVP **loopback** stack (all mandatory; they compose to three independent failures for a rebinding attacker): a **CSPRNG
capability token** (atomic **0600** create, *not* write-then-chmod; **header-only**, never in a URL — the Jupyter
`?token=` CVE lineage; **no cookie** — a cookie re-opens CSRF; **required on read endpoints too** — a rebind must not
scrape it); a **strict Host-header allowlist on every endpoint** (`127.0.0.1:<port>` / `localhost:<port>` only — the
sole browser-independent DNS-rebinding defense every peer tool converged on after being bitten); **`Content-Type:
application/json` + a custom header** (forces the CORS preflight a form-CSRF can't satisfy) with `Sec-Fetch-Site`
reject-cross-site, fail-closed; explicit **`127.0.0.1` bind, never `0.0.0.0`**; IPv4/`::1` kept consistent. The
**dynamic port is not a secret** (anyone `lsof`s it) — token + Host-check do the work. **Two distinct tokens, never
conflated:** the **bus token = authentication** (the secret gating POST) vs the **checkpoint token = correlation only**
(D91 — it lives in user-readable `parked/`, so it is *not* a secret). **Windows has no `0600`** → the token file needs
explicit ACLs, folded into the **D89** "target OS/FS isn't POSIX-ext4" family. **Tunnel (owner-accepted):** D70
stands unchanged — remote-control is opt-in / off by default / warning-only / **no auth**, an owner-accepted risk; the
one hard rule retained is that the **loopback token is never reused as tunnel auth** (over the wire there is no 0600
file to gate it → it degrades to a replayable bearer with no identity), so real tunnel auth (Cloudflare Access / HMAC
short-lived requests) stays the reserved upgrade for when the risk is no longer acceptable.
- **Why:** loopback ≠ authenticated, and a forged verdict/command drives an autonomous executor (privilege escalation);
  the live vectors are the confused-deputy browser + DNS-rebinding, not same-UID code. Token-in-a-0600-file pins the
  audience to the user's UID (= the workflow's own trust level), header placement doubles as CSRF defense, and the
  Host-allowlist is the one rebinding defense that survives a same-origin post-rebind.
*Rejected:* investing in same-UID isolation (already-game-over theater); token-in-URL (log/history/`Referer` leak — the
Jupyter CVE class); a session cookie (re-opens CSRF); reusing the loopback token over the tunnel (unsound); treating the
dynamic port as a secret (it isn't).
*Evidence:* a loopback-security research fan-out — github.blog CORS/DNS-rebinding, Ollama **CVE-2024-28224**,
Vite/webpack-dev-server/Chrome-CDP Host-check convergence, Jupyter `secure_write` 0600 + the `?token=` CVE lineage
(2023-39968 / 2024-22421 / 2025-59842), OWASP CSRF + Fetch simple-request rules, Cloudflare Access deny-by-default.
Reuses D35/D70/D89/D91. → `03`/`05`/`07`/`11`.

## D96 — Checkpoint taxonomy = judgment vs action boundary; the trigger rule closes C2 **[DECIDED — Phase-2 C, research-backed]**
A checkpoint is raised at **a boundary only a human can cross**, and there are exactly two boundary *types*, which
organize every trigger and verdict:
- **Judgment boundaries** ("is this what we meant?") — `demo` (spec vs mental picture, intake-stage), `qa`
  (behaviour vs intent, build-tail), `reconcile` (reconstructed spec vs reality, brownfield-intake). Verdict is an
  opinion.
- **Action boundaries** ("do something in the world I can't reach") — `setup` (perform an external action, obtain a
  credential). Verdict is "I did it" + a returned artifact, then **machine-verified** (D97).

**Trigger rule — declared upstream wherever the intent lives**, with setup's one exception:
- **qa** = `planner` declares a `human-qa` acceptance criterion (D30).
- **demo** = the sandbox gate (D22) in `create-demo`'s `When`, evaluated per work-item — **the gate *is* the
  trigger; there is no separate demo-trigger to invent.** The intake-stage demo refine-loop's spec edits are owned
  by `create-demo` (it edits the spec slice it owns and regenerates — explicitly licensed to write the spec;
  `refine`'s `plan-delta` machinery is build-stage and does not apply pre-plan).
- **reconcile** = `ingest` after spec reconstruction (D68).
- **setup** = **spec `integrations[]`** for the foreseeable (pre-declared → inherits the D97 deadline/reminder
  machinery) **+ an execute-discovered path** for the unforeseen (a new licensed `execute → checkpoint(setup)` edge —
  the outward-facing sibling of a `prerequisite-repair` divergence, D66). Even a discovered setup is materialized as
  a **durable parked record**, never an in-memory block.

Closes C2 (`04`'s "what triggers a checkpoint").
- **Why:** the judgment/action split *predicts* the whole cluster — action boundaries return artifacts and need
  verification, judgment boundaries don't, which is why only setup gets D97's richer machinery. Declared-upstream is
  the near-universal model across Step Functions / Camunda / GitHub-GitLab gates / n8n; runtime-discovery is a
  deliberate exception the mature engines still materialize durably — matching D90/D91's on-disk parked record.
*Rejected:* a separate demo "trigger" (the D22 gate already is one); routing intake-stage demo edits through `refine`
(no plan exists pre-build); enumerating all setups upfront (unforeseeable — hence the discovered path); an in-memory
setup block (D90 forbids it).
*Evidence:* two research fan-outs (external-action setup-gate patterns; async-HITL scheduling) + the cluster-A
substrate. Reuses D22/D30/D66/D68/D90/D91. → `04`/`09`/`10`/`shared/schemas.md`/`skills/checkpoint`/`skills/create-demo`.

## D97 — Checkpoint verdict is a verb-enum + a returns payload; setup is a plural, machine-verified action gate; timeout never auto-proceeds **[DECIDED — Phase-2 C, research-backed; completed by D111 — the "gitignored secret store" is located + owned (`.workflow/secrets/`), the shred is a narrow inbox carve-out, and the timeout's deadline/reminder are pinned to `config.checkpoint` with the daemon as their timer owner]**
The checkpoint verdict data model + the setup lifecycle. Closes C1's remaining data-model gap.
- **Verdict = a verb-enum, not a boolean.** `verdict { outcome ∈ {approve, changes, reject}, notes, returns? }`;
  `pass` derives from `outcome=approve`. A boolean throws away the information the agent most needs
  (industry-unanimous: LangChain approve/edit/reject, Temporal `CHANGES_REQUESTED`). Routing keys off `outcome` **per
  kind**: demo approve→lock spec / changes→`create-demo` / reject→`discuss`; qa approve→`document`/`commit` /
  reject→`debug` (changes≡reject); setup approve|changes→**verify-external** / reject→replan-or-hard-stop; reconcile
  approve→`prioritize` / else→`ingest`/`discuss`. **Applied uniformly across all kinds** (one enum the coherence gate
  guards; the changes/reject split earns its keep on demo too), *not* setup-only.
- **Setup is machine-verified on resume — never trusted on "done."** approve/changes unblocks the agent to *probe the
  external precondition actually works* (the key authenticates, the webhook fires); only then does it proceed; a
  failed probe **re-guides (loop)**, it does not `debug`. Setup is the one kind whose human verdict is an *input to* a
  `verify`, not the terminal signal — which simultaneously delivers resume-idempotency (a re-run-from-park must be
  safe), handles "did it differently," and catches a premature "done."
- **Setup checkpoint is plural (the no-refactor shape):** `request.tasks[]` — a *set* of setup items (a lone setup is
  a one-element set), each with a per-task `{outcome, notes, returns?}` in the verdict, so a mixed reply (Stripe
  `approve` + Clerk `reject`) routes each on its own. **Coalescing policy = within-plan, at first-setup-contact:** the
  build is *not* front-loaded at intake; when it first hits setup territory, the orchestrator sweeps *this plan's*
  declared-but-unraised `integrations[]` and bundles them into one checkpoint. **Cross-ticket coalescing** (one
  verdict resuming several parked tickets) is **deferred** — the `tasks[]` schema accommodates it, so adopting it
  later is additive, not a refactor.
- **A returned secret rides the inbox, sensitive + shred:** a setup `returns` value marked `sensitive` is written by
  the orchestrator to the **gitignored secret store**, **never echoed to `state.json`/logs**, and its inbox file is
  **shredded post-consume** (not retained). Away-capable; the bus is already scoped to the user's own UID over
  loopback (D95), so the residual exposure equals `.env` itself. (User-present terminal-only placement is the
  documented hardening if the durable-inbox exposure is later unacceptable.)
- **Timeout never auto-proceeds.** Invert the n8n/Zapier skip-and-continue default: a checkpoint deadline
  **re-surfaces + reminds** (aging via the `Notification` hook, D91), never advances the work — a missing key cannot
  be skipped.
- **Why:** the whole point of an action boundary is a returned artifact + a real-world effect that must be *verified*,
  not asserted; the verb-enum is what lets one reply carry done/can't/changed with the payload the agent needs;
  plural-from-day-one buys the coalescing upgrade without a schema refactor.
*Rejected:* a boolean verdict (loses done/can't/changed); trusting "done" without probing (premature-done +
non-idempotent resume); a single-task setup request (forces an A→B refactor); front-loading all setups at intake
(blocks early, mocks unreached work); secret placement gated to the terminal for MVP (defeats away-autonomy);
timeout auto-skip (a missing credential can't be skipped).
*Evidence:* two research fan-outs (setup-gate pending-request/verdict data models across Step Functions / Camunda /
LangChain-LangGraph / Temporal / n8n-Zapier; guidance richness) — verb-enum outcome + a "done-differently" payload +
verify-on-resume idempotency + deadline-in-the-record were unanimous. Extends the `checkpoint` + `inbox-message`
schemas; reuses D90/D91/D93/D95. → `04`/`09`/`shared/schemas.md`/`skills/checkpoint`/`10`.

## D98 — Checkpoint help set: MVP = contextual steps + a live-resolved, verified deep-link + breadcrumb; screenshots / screen-share / live-feedback / agent-automation deferred **[DECIDED — Phase-2 C, research-backed]**
Closes C3 ("which help features are MVP"). The async/park model (D90/D93 — nothing live happens while parked;
dialogue lives at the terminal) draws the line: only guidance that fits a durable request→verdict round-trip is MVP.
- **MVP (async, durable, auto-generatable, self-healing):** a **contextual step-list** (one action per step,
  delivered *at* the step — not front-loaded) + **per-step a deep-link resolved at guide-time via live web search and
  verified to resolve, always paired with a human-readable breadcrumb** ("Settings → Payments → Webhooks") + the
  search query. The breadcrumb is the graceful-degradation path — cheaper than a screenshot and robust to UI churn +
  link rot; `setup-guide` (WebSearch/WebFetch) does the resolve-and-verify. This pair directly kills the "where does
  this setting live?" hunt (the Polar motivating example).
- **Deferred:** **screenshots** (image models can't faithfully render a current UI; the only accurate path is a
  live-browser capture — infra, not one-shot — and it goes *silently* stale, mis-pointing a user who trusts it);
  **screen-share + live-feedback** (intrinsically synchronous → needs a live watching model, which by D90 exists only
  in the user-present terminal session, never on the parked bus — a "stuck" escalation, not the default);
  **agent-driven browser automation that performs the setup** (30–60% real-site task-failure + a hard
  credential/irreversibility trust gate — the human stays the actor).

`setup-guide`'s "screenshot references / screen-share cues" wording is **dropped** (it now emits steps + verified
deep-links + breadcrumbs); `00`'s vision list keeps screenshots/screen-share as the *designed-for* aspiration
(deferred), not MVP.
- **Why:** the cheap async channel should carry only guidance whose accuracy is *resolved-and-verified at generation
  time* and that *degrades gracefully*; a controlled study (NN/G) found richer, front-loaded tutorials don't raise
  success and make tasks feel harder — contextual *timing*, not media richness, is what helps.
*Rejected:* auto-generated screenshots (hallucinated/garbled + silently stale); screen-share in MVP (synchronous,
breaks the park model); agent-does-it-for-you (unreliable + unsafe for account settings); a bare deep-link with no
breadcrumb (link rot ~8%/yr + ungrounded-LLM fabrication 3–13% → a landmine).
*Evidence:* a guidance-richness research fan-out — NN/G tutorial study, Ahrefs link-hallucination + link-rot, Pew
link-rot, WebVoyager/OSWorld agent success rates, Anthropic's own "experimental" computer-use framing. Reuses
D90/D93. → `04`/`00`/`agents/setup-guide`/`skills/checkpoint`/`11`.

## D99 — Console model: a read-only supervision cockpit (not an explorer); snapshot-poll refresh; async requests get a first-class "my requests" surface **[DECIDED — Phase-2 B (B1/B2/B3), research-backed]**
The console has two latent modes — **supervise a live run** (A) and **explore the project** (B) — and **only Mode A is MVP** (the
dogfood's one critical-path job: deliver a checkpoint verdict + status away from the terminal, C2).
- **Home = a run-status cockpit:** current item · wave/parked tickets · **pending checkpoints** · recent activity — read
  straight from the files the bus serves (`state.json` / `backlog.md` / `parked/` / `handoff.md` / git — D93 sync-reads).
- **The project-map (D70) is a tab, not the home, and not the first cut** — Mode B's structural face, stageable, its value
  gated on the deferred flow-overlay + later code-map arms. "Structural face of the project-state view" (`07`) is about the
  *eventual* state-view, not the MVP console home — the two were being conflated.
- **Screen list (MVP → later):** cockpit (home) · checkpoint console · **"my requests"** · roadmap/backlog (read-only) →
  *later* tabs: project map, knowledge exploration.
- **Refresh = snapshot polling, no SSE in MVP.** One chained-`setTimeout` loop (~2–5 s) reads the whole state JSON; a
  monotonic `version`/`ETag` returns `304` → skip the re-render; polling pauses on `document.hidden`. inotify→SSE stays the
  reserved "re-read" hint (D93). In-page freshness is deliberately lazy because urgency rides the Notification hook (D101),
  not the page.
- **Contact-orchestrator UX** (the D93 principle made concrete) = two POST forms + a feedback surface: a **verdict** form
  (carries D97's `{outcome, notes, returns?}` / plural `tasks[]`; renders D98's steps + verified deep-links + breadcrumbs for
  `setup`), an **intake** form (the D70 node→ticket click is a pre-filled intake), and the **"my requests" view** — each POST
  returns `202` + a `Location` ticket saved to `localStorage`; the view is the same polled state *filtered* by my ticket ids,
  so `pending→consumed→resolved` is legible with **no new endpoint** and no per-ticket polling.
- **Why:** the MVP job is supervision, not browsing; map-as-home front-loads the heaviest, most-deferred, code-map-dependent
  screen and buries the load-bearing checkpoint surface. Lazy poll is forced-correct by D93 (the bus serves state from disk;
  the orchestrator is never an HTTP responder) and safe because the one latency-sensitive event is delivered out-of-band
  (D101). The async model (D90/D93 — never a synchronous response) has **no feedback home without a requests view**; it's
  nearly free (rides the existing state read).
*Rejected:* map = home/overview (front-loads a deferred, code-map-dependent screen; conflates the eventual project-state view
with the console home); a real-time chat console (D93 forbids it — dialogue lives at the terminal); SSE/file-watching as
load-bearing MVP refresh (D93 keeps it rejected for control-flow; SSE is ergonomics-not-architecture for a batch worker);
`setInterval` (overlapping reads on a slow read); clearing the form on POST with no requests surface (the async model then
feels like a void).
*Evidence:* D90/D93 + the dogfood's single critical-path finding; the file-IPC research (Async Request-Reply — `202` +
status-resource + correlation id); the frontend research fan-out (chained-`setTimeout` single poll loop + `version`/`ETag`
gate + `localStorage` ticket set + `document.hidden` pause = the standard 202→poll dashboard). Reuses D70/D90/D93/D97/D98.
→ `03`/`05`/`07`/`11`.

## D100 — Console stack: a stdlib-Python detached HTTP daemon + a zero-build, CSP-clean static page (vanilla default, Preact+htm escape hatch) **[DECIDED — Phase-2 B (B4), research-backed]**
Closes B4 — and the coupling runs *from* A2/A3/A4, so the stack was more constrained than "deferred" implied, not less.
- **Backend = a single-file stdlib-Python daemon on `http.server.ThreadingHTTPServer` + a custom `BaseHTTPRequestHandler`.
  No vendored dependency, no framework.** It *is* the D94 detached daemon (dynamic loopback bind-and-read-back, `flock`
  liveness, per-request token + Host checks, `202`+inbox, `POST /shutdown` + idle self-shutdown). Three footguns are part of
  the build contract: (1) `POST /shutdown` spawns a **one-shot thread** to call `server.shutdown()` — never inline on the
  `serve_forever` thread (documented deadlock); `daemon_threads=True` is already the `ThreadingHTTPServer` default so workers
  never block exit. (2) The request body is **not** size-capped by default → read at most `Content-Length`, `413` on oversize,
  set `handler.timeout` so a slow client can't pin a worker. (3) Leave `protocol_version` at **HTTP/1.0** (connection-per-request
  is trivially correct at ~1 concurrency and kills a whole class of keep-alive `Content-Length` hang).
- **Frontend = zero-build static files the daemon serves.** **Vanilla JS** (`<template>` clone + `textContent`) is the
  default; **Preact+htm** (~4.5 KB, plain ESM, tagged-template → **no eval**) is the one pre-vetted escape hatch for when the
  render layer sprawls.
- **The daemon serves a strict `Content-Security-Policy: script-src 'self'` (no `unsafe-eval`)** — the concrete teeth of D95's
  CSP posture on the page itself, and the *mechanism* that forces the frontend choice: it **disqualifies Alpine-standard and
  petite-vue** (both use `new Function`/eval and would break silently under the policy). So B4's frontend is *downstream of
  A4*, not an independent preference.
- **The D70 map does not constrain this** — a lazy isolated later screen; when built, cytoscape.js is vendorable as one UMD
  (built-in layouts CSP-clean; avoid the eval-using `spread` extension) or hand-rolled Canvas + a vendored `d3-force` module.
- **Why:** the stack is over-determined, not chosen. **No install/build step we control** (the pure-config master rule) rules
  out npm/bundlers/pip; **`python3` is already the one hard dependency** (D71 — shell glue = bash, logic = python); **CSP-tight
  loopback** (D95) rules out CDNs + eval-libs — which triangulates to exactly this shape. Every comparable local-first tool
  (Syncthing, Ollama, Jupyter) uses its language's *built-in* HTTP server, never a vendored framework — HTTP because a
  *browser* consumes it (git-credential-cache uses a Unix socket, having no browser). The docs' "not for production" warning
  targets `SimpleHTTPRequestHandler`'s file-serving surface, not a custom handler serving fixed files behind a token.
*Rejected:* a web framework (Flask/FastAPI) or SPA toolchain (React/Vite) — break no-install / force an unrunnable build;
vendoring `bottle.py` or threaded-`wsgiref` (zero capability gain at ~6 endpoints/~1 concurrency, a file to patch/audit,
weakens install-free); Alpine-standard / petite-vue (need `unsafe-eval`; Alpine's CSP build works but forces a restricted
dialect); htmx (CSP-clean but architecturally mismatched — HTML-fragment swaps vs JSON-from-disk); a Unix-domain socket
(right only with no browser; we have one).
*Evidence:* two research fan-outs — Python `http.server`/`socketserver` docs + CPython source (`daemon_threads=True`;
`handle_error` prints + continues; the cross-thread `shutdown()` deadlock note); Syncthing/Ollama/Jupyter/git-credential-cache
daemon patterns; a CSP eval-audit (Alpine-standard/petite-vue need eval, vanilla/Preact+htm/Lit don't); cytoscape UMD size +
CSP notes. Depends on D71/D89/D93/D94/D95; realises D70 (deferred). → `03`/`05`/`07`/`11`.

## D101 — Console attention: notify on exactly two events (checkpoint-raised · loop hard-stop/escalation); reminders ride the D97 timeout **[DECIDED — Phase-2 B (B5); the taxonomy STANDS, but its mechanism is corrected by D111 — the bus daemon fires the alert, not the D90 `Notification` hook, and `config.notify`'s webhook is the away channel]**
Closes B5. The notification *mechanism* is settled (D90 — the `Notification` hook → desktop-native + opt-in Slack/HTTP
webhook; phone/tunnel later); this fixes the MVP **event taxonomy**.
- Fire on exactly **(1) a checkpoint being raised** (the reason the away-channel exists) and **(2) the loop hard-stopping /
  an escalation** — a D92 thrash/auto-compact hard-stop, or a D91/D97 dead-letter / stale-deadline escalation.
- **Reminders are not a new event** — they ride D97's timeout-resurfacing (a checkpoint deadline re-surfaces + reminds via
  the Notification hook and its aging, D91; never auto-proceeds).
- Everything else (per-step progress, per-item completion, the outward-action gate) is **out of MVP**.
- **Why:** an away-channel's value is inversely proportional to its false-positive rate; the only events that justify
  interrupting an away human are *something needs you* / *something broke*. The checkpoint ping is what makes unattended
  autonomy unattended; the hard-stop ping is the safety valve for the D92/D91/D97 states that otherwise sit silent. Folding
  reminders into D97's existing machinery avoids inventing a second aging system.
*Rejected:* progress / per-item-done pings in MVP (high-frequency, low-actionability — trains the human to ignore the
channel); a separate reminder/aging subsystem (D97 already owns deadline resurfacing); outward-gate notifications now (couple
to the unbuilt E2 outward-permission model; deferred with it).
*Evidence:* D90 (mechanism) · D91 (aging anti-starvation, dead-letter/timeout escalation) · D92 (thrash hard-stop) · D97
(timeout re-surfaces, never auto-proceeds). → `03`/`04`/`11`.

## D102 — Demo serving + format: the throwaway sandbox is a build-free, self-contained static bundle the console daemon serves under a CSP `sandbox` opaque origin; format = vanilla / vendored htm+preact (the D100 idiom) **[DECIDED — Phase-2 D (D1), research-backed; BUILT + sharpened by D124 — the `sandbox` directive was MEASURED to enforce ISOLATION ONLY (opaque origin proven in real Chrome, top-level AND framed), NOT the format discipline: `eval`/`new Function`/external hosts all run under it, so this entry's "runs without `'unsafe-eval'`" is misleading and the no-eval/no-external invariants are create-demo discipline enforced by the shipped `check_demo_bundle.py` lint, not the CSP]**
Closes D1 — and like D100 it is **over-determined by the A/B substrate**, not a fresh design: a demo is *more files on disk*, so D93's "the daemon serves files; the orchestrator writes them, never responds" already answers "who serves it."
- **Serve:** the sandbox is a **build-free, self-contained static bundle** (a `.workflow/demos/<id>/` dir: `index.html` + optional local assets — a small file set over HTTP, not one data-URI-inlined file). `create-demo` writes it **before the park** (D90); the always-on **D94 daemon serves it** — no sibling server, no second port (a second origin is only for *untrusted third-party* code — CodeSandbox/StackBlitz; ours is first-party — Storybook / Jupyter-post-CVE are the precedents).
- **Isolate:** serve `/demo/*` with **`Content-Security-Policy: sandbox allow-scripts allow-forms`** — the `sandbox` *directive* forces an **opaque origin server-side** (the demo can't read the console's storage or reach its token-gated endpoints, inline scripts run without `'unsafe-eval'`, **and it's isolated even at top-level navigation** — the D98 deep-link / away-tab case the iframe attribute alone misses). Belt-and-suspenders: the header **+** the embedded iframe `sandbox="allow-scripts allow-forms"` attribute; **never `allow-same-origin` / `allow-top-navigation`**. The console keeps its strict `script-src 'self'`. **Demo = look, console = the D97 verdict form around it** — the demo is read-only, no POST, no token, no authority to abuse.
- **Format discipline** (the `create-demo` body): **self-contained, no external hosts, no `eval`** — the two invariants a CSP actually enforces, and what makes the demo render identically local + over the tunnel, offline, never phoning home. **Vanilla JS + `<template>` + hash routing** by default; **htm + preact vendored locally** (~10 KB, tagged templates, not JSX) as the escape hatch — the *same idiom D100 chose for the console*. Hard-ban CDN `<script src=https://…>`, `@babel/standalone` / `type="text/babel"` JSX (6 MB + needs `unsafe-eval`), npm/bundlers. (The Claude Artifacts discipline.)
- **Static-asset serving class (the D95 clarification, folded into `05`):** a browser can't attach a token header to a document/iframe *navigation*, so the daemon has **two serving classes** — a **static app-shell class** (the page, its assets, the demo: Host-allowlisted, token-free — no secrets) vs the **sensitive data/command class** (state reads + POSTs: token-gated). D95's "token required on reads too" means the *sensitive data* reads; the demo joins the static class. Implicit in D100; the iframe navigation forced it into the open.
- **Build-contract footguns** (the D100-style list): path-traversal guard (`realpath` + `startswith(demo_root)`, a dedicated dir never cwd), explicit MIME map + `X-Content-Type-Options: nosniff`, `Cache-Control: no-store` on regenerated demos, **atomic write (`os.replace`)** so a concurrent reader never sees a half-written file.
- **Away human (tension resolved upstream):** the demo **rides the existing console tunnel for free** (a path on the one port) — remote *seeing* works (static GET); remote *verdict submission* inherits D95's pre-existing owner-accepted tunnel degradation (the POST is token+Host-gated). Cluster D neither worsens nor must solve it.
*Rejected:* a sibling ephemeral static server / second port (reinvents the D94 lifecycle, breaks the free tunnel; a second origin buys nothing for first-party content); a *relaxed `script-src`* instead of the `sandbox` directive (leaves the demo in the console's real origin — the **Jupyter CVE-2021-32797/8** shape: same-origin generated HTML → stored XSS → `/api` authority + kernel RCE); reusing the real app's dev server as the demo (D21 — throwaway, non-integrated, never the scaffold); Babel-standalone / runtime JSX (6 MB + `unsafe-eval`, not self-contained); a single data-URI-inlined file (fragile; a small file set over HTTP is cleaner and dodges the `file://` ESM-CORS trap).
*Evidence:* two research fan-outs — preview-isolation (Storybook same-origin sandbox-iframe · CodeSandbox/StackBlitz/VS Code separate-origin *for untrusted code* · Jupyter CVE = missing sandbox CSP · MDN/web.dev: the `sandbox` directive = opaque origin, header-only, covers top-level; `allow-scripts`+`allow-same-origin` self-defeats) + build-free rendering (Claude Artifacts + SingleFile = self-contained-HTML proven · htm+preact ~5–10 KB no-build no-eval, vendorable offline · Babel-standalone ~6 MB + `unsafe-eval`, "don't use in prod"). Reuses D21/D90/D93/D94/D95/D98/D100. → `04`/`05`/`09`/`skills/create-demo`/`11`.

## D103 — Refine-round cap: a config-overridable bound (default 3) on demo regenerations; the cap never auto-proceeds → it escalates to live `discuss` **[DECIDED — Phase-2 D (D2)]**
The intake-stage refine mini-loop (human sees demo → "change X" → `create-demo` edits the spec slice → regenerate → re-checkpoint; D96) is **bounded**: cap at **N regenerations** (config-overridable `config.demo.max_refine_rounds`, **default 3**), **counted plainly** (no grading big-change-vs-tweak — the cap is a circuit-breaker, not a fairness meter; the "count, don't judge" discipline of D61). On the cap: **never auto-approve / auto-abandon** (D97's "timeout never auto-proceeds") — **escalate to a live `discuss` session**, carrying the refine history; the human realigns and the loop resumes (or the cap is bumped).
- **Why:** the refine loop is a **low-bandwidth async channel**; a human is in every round, so this isn't AI-on-AI (no D45 back-eval concern). Failing to converge in a few rounds *is the signal* that the alignment gap is too big for the async keyhole — and D93's conversation model already puts open-ended **dialogue at the terminal (`discuss`)**, not on the bus. So the escalation target is *high-bandwidth conversation*, not another async checkpoint. Low-fi demos are meant to converge fast; round 4 is either bikeshedding or deep misalignment — both want a human conversation.
*Rejected:* unbounded regeneration (burns autonomy/tokens chasing a moving target); auto-proceed at the cap (D97 forbids it — a mock the human never approved isn't a lock); grading rounds by size (needless judgment); escalating to a *bigger async checkpoint* (the same low-bandwidth channel that just failed).
*Evidence:* D97 (never auto-proceeds) · D93 (dialogue = terminal, bus = bounded requests) · D61 (count-don't-judge) · D45 (no AI-on-AI eval); the house bounded-loop→escalate pattern (D24). → `09`/`skills/create-demo`/`11`.

## D104 — Demo on-disk location: `.workflow/demos/<item-id>/` — gitignored runtime, under the served tree, pruned on resolve **[DECIDED — Phase-2 D (D3); sharpened by D114 — this entry's closing "co-located with the served root wherever D93 pins it" presumes a single served root that does not exist (the bus reads across both the pinned runtime subtree and the committed repo tree), so `demos/` is now marked explicitly: `bus:static` + `no-pin`, exactly on this entry's own atomicity-light reasoning; BUILT + sharpened by D124 — "pruned on resolve" is owned by the verdict-apply path (approve→lock / reject→discuss delete; changes keeps it) with retention's `prune_demos` as the straggler backstop; the refine count lives at `demos/<id>/.refine.json` (a dotfile the server refuses); and "self-heals on next poll" was MEASURED to be a transient `ENODATA` open failure on 9p during `os.replace`, not a torn render (content never tore) — handled by a bounded read-retry]**
The throwaway sandbox lives at **`.workflow/demos/<item-id>/`** — nearly forced by the substrate: **gitignored runtime** (rules out committed `items/<id>/`, which D61 keeps for crash-survival — committing throwaway bytes bloats git and contradicts D21) · **under the D94 daemon's served tree** (must be servable) · **durable across the park** (the human may look hours later — D90/D91; rules out `/tmp` scratch). **Not** the build worktree (the demo is *intake-stage*, before the build ticket/worktree exists — D91). Regenerated **in place via atomic write** (`os.replace`; D21's "regenerate, never hand-edit" = overwrite). A thin pointer (the demo path) rides the **`parked/<id>` record** so console/orchestrator find it. **Pruned on checkpoint-resolve** (throwaway + gitignored → just delete; the audit prune (D61) sweeps stragglers) — nothing to archive: **D21 makes the *locked spec* the durable artifact, not the demo bytes**. New runtime dir → owner declared (D80): **`create-demo` writes, the audit prune deletes**; gitignored with the rest of the runtime view (D53/D62). On WSL the demo bundle is write-once-then-serve (atomicity-light), co-located with the served root wherever D93 pins it.
*Rejected:* `items/<id>/` (committed — bloats git with throwaway bytes); `/tmp` scratch (not durable across an hours-long park); the per-ticket worktree (build-stage, doesn't exist yet at intake); archiving the demo on resolve (D21 — the spec is what's kept).
*Evidence:* D21 (throwaway, spec-is-locked) · D53/D60/D61 (gitignored runtime, cap-and-archive, items-committed-while-open) · D62 (docs-root/disk layout) · D90/D91 (durable park, worktrees are build-stage) · D93/D94 (served tree, FS pinning). → `05`/`09`/`skills/create-demo`/`11`.

## D105 — Outward-action permission: a *transactional-outbox* queue (not a checkpoint); a deny-floor + a coarse `config.outward` allow|ask layer; batch-release over a new inbox `kind: release`; state-bound + TTL'd; no durable ledger **[DECIDED — Phase-2 E (E2), research-backed; closes D35's open mechanics + D60; two premises corrected by D110 — the harness `ask` is NOT a backstop for the outbox classes (it cannot coexist with the away-release), and "never auto-push `main`" is an absolute `guard.sh` block, now built]**
The mechanics D35 left open. The decisive reframe: **an outward action does not park the ticket.** A checkpoint (D90) parks-and-resumes because the *work is blocked* (no verdict → can't proceed); an outward action blocks nothing — the commit is already local, the ticket **completes and the loop advances** (D35's "never stalls: keep committing, queue the action, one approval releases a batch"). So the real fault line is **blocks-the-ticket (checkpoint) vs defers-a-side-effect (outbox)**, not judgment-vs-action (D96) — and `publish` is therefore **not** a fifth checkpoint kind and **not** a parking checkpoint on the bus. It is a distinct mechanism, the **outward-action outbox** — the industry **transactional-outbox** pattern (write the local change + a `PENDING` outbox record; a *release* drains it), reusing the bus/console transport + the D97 verb-enum but **not** the park/resume core.
- **Two-layer permission.** **Layer 1 = the mechanical floor, non-overridable:** `guard.sh` (secret-scan + verify-before-commit + the D87 chaining-block) fires on *every* outward action regardless of config, fail-closed. **Layer 2 = human approval, overridable:** a **`config.outward` allowlist in Claude Code's own `permissions.{allow,ask,deny}` shape** (deny→ask→allow, first-match-wins), **coarse per-action-class** (`push` / `issue-create` / `issue-close` / later `deploy` / `send`), **default all `ask`** (MVP-safe = always-gated). Standing pre-auth waives *the human*, never *the checks*. **Fine-grained scoping lives in `guard.sh`, not config allow-patterns** — Claude Code's docs call arg-constraining allow-patterns fragile ("use deny + hooks"), so "never auto-push `main`" is a guard rule, not a config glob.
- **Mechanism.** The skill **self-gates against `config.outward`** — match `allow` → run the command (still through `guard.sh`); else **append a record to `.workflow/outbox/` and continue** (it never attempts-the-command-and-lets-the-harness-`ask`, which blocks and can't work away-from-terminal; the harness `ask`-prefix is only the backstop for a mis-coded skill). `outbox/` = **runtime, gitignored, single-writer (orchestrator)** — the mirror of the bus-owned `inbox/`. **Release** = a batch-approval the human sends from the console → a **new `kind: release` inbox message** carrying **explicit action-ids** → consumed at a boundary → each approved action executes (re-runs `guard.sh`) → marked executed. New inbox kind (not a `control` op) so each kind stays crisp: verdict=resume-parked · intake=new-work · control=scheduling · **release=fire-queued-outward**.
- **Queue-safety mechanics (research-forced, against the outbox anti-patterns).** (1) **State-binding + re-validate on release (TOCTOU):** each entry is bound to the state that triggered it; on release the floor re-scans the *actual* outgoing change and divergent history **invalidates + re-surfaces** rather than firing (push: bound branch + floor-SHA, `guard.sh` re-scans the outgoing range, rebased-away floor → re-surface; issue-create: local item closed meanwhile → **drop**; issue-close: idempotent no-op). *Push-range semantics — "exactly the approved SHAs" vs "current tip, floor-re-scanned" — is a build-time sub-detail; the lean is current-tip-guard-rescanned to avoid per-commit re-approval noise.* (2) **TTL → drop on expiry, never silently fire stale** (config-overridable; drop ≠ escalate — an outward action isn't blocking). (3) **Release is always by explicit action-id** (batch snapshot) — items enqueued after the human's glance are simply not in the approved id-set; no live "approve-all-pending" wildcard.
- **No notification, no durable ledger.** D101 excluded outward-gate pings (noise) → the outbox is a **pull** surface on the D99 cockpit (a release form + a pending count); checkpoints notify because they block, the outbox doesn't because it doesn't. **No approval ledger:** SoD/SOX needs one only because *approver ≠ author*; a single-user local agent is author-is-approver → SoD is moot → the action's own **external consequence** (the moved git ref / the GitHub issue event / the deploy record) *is* the audit — the exact logic that made qa/demo verdicts disposable (D60). The away-run digest is the console activity feed + the handoff summary, not a new artifact.
- **D60 resolved — `.workflow/checkpoints/` retired.** It was reserved on the guess that setup/publish approvals might need a durable ledger *there*. But **setup is a real checkpoint** (its record lives in `parked/`) and **publish is not a checkpoint** (its record lives in `outbox/`) — the reserved dir has **no remaining claimant**, so it is **renamed to `outbox/`** (runtime, gitignored; owner = the orchestrator writes a pending record when a skill defers an outward action, and the release-consumer clears it — D80 owner declared).
*Why:* the "never block, queue, batch-release" principle *is* the transactional-outbox shape, the opposite of every CI/CD environment-protection gate (which blocks-in-place) — naming it stops a later wrong build that models publish as a blocking gate; the two-layer split keeps the mechanical floor un-waivable while letting a user opt into standing pre-auth; state-binding + TTL + id-snapshot are the three named outbox anti-patterns (TOCTOU / stale-fire / batch-changed-underneath) closed up front.
*Rejected:* `publish` as a checkpoint kind / a parking checkpoint (parks a ticket with no reason to park — violates D35 never-stall, wastes a worktree hold; there is no ticket to resume); a `control` op instead of a new `release` kind (overloads scheduling with approval); a CI/CD block-in-place gate (blocks the loop — the anti-principle); a durable approval ledger (SoD-moot for single-user; the external consequence is the audit); fine-grained config allow-patterns for branch/target scoping (Claude-Code-documented-fragile → guard.sh); relying on the harness `ask` prompt as the primary gate (blocks + fails away-from-terminal); firing a stale queued action silently on late release (drop on TTL instead).
*Evidence:* an outward-action-gate research fan-out — the transactional-outbox pattern (AWS prescriptive guidance) as the durable-pending-queue shape; Claude Code `permissions.{allow,ask,deny}` (deny→ask→allow, first-match-wins, arg-patterns-are-fragile→use-deny+hooks) as the allowlist; CI/CD environment-protection (GitHub Environments required-reviewers/wait-timer/branch-filter, GitLab deployment-approvals, Spinnaker/Argo/Step-Functions) all **block-in-place** (the anti-model, borrow the *vocabulary* not the semantics); merge-queue as the one async-batch precedent; SoD/SOX ⇒ ledger-only-when-approver≠author; the TOCTOU/expiry/batch-snapshot anti-patterns (GitHub regenerates approval on head-move). Reuses D35/D58/D60/D87/D90/D93/D97/D99/D101. → `04`/`05`/`07`/`09`/`03`/`shared/schemas.md`/`skills/{commit,create-issue,close-issue}`/`commands/start.md`/`templates/orchestrator-CLAUDE.md`/`11`.

## D106 — Commitment-status storage: the spec owns it inline (intent-side); the drift check reads it code→intent; nodes never store a commitment value **[DECIDED — Phase-2 E (E1); closes the D23 storage gap under D80; the *storage* call stands unchanged, but this entry's resolver phrasing is corrected by JF5 — "nodes already carry `purpose.intent`" overstates it: `intent` is `06`'s tier-`[D]` layer, **authored on touch** by `document`, so an untouched node has none, while the drift check must resolve *any* changed node. The resolution is **judgment** over the eager `[G]` graph + decision records + the STABLE spec (`purpose.intent` an input when present, never a foreign key); the mechanism stays open in `07`]**
Where `locked`/`provisional`/`unspecified` (D23) is recorded. **The spec is the sole owner — commitment lives inline on each spec element** (`screens[]`/`features[]`/`phases[]` already carry a `commitment` field; STABLE tier, human-owned, written at intake by `discuss`/`create-demo`, and the demo locks the spec state that produced the approved sandbox — D21/D103). **Nodes never store a commitment value.** The drift check (`align`/`verify`/`audit`) resolves the changed **code node → its spec element** (nodes already carry `purpose.intent`, the spec-derived projection — `06`) and **reads `commitment` on the intent side**. So storage is intent-side; the lookup traverses code→intent.
- **Why intent-side, not node frontmatter:** (1) **D80 single-source** — the spec field is the owner; a node copy is a second copy that drifts (spec `locked`, node stale at `provisional`). (2) **Regeneration** — nodes are code-derived and regenerated (D78 living map); commitment is human intent and must not be clobbered on regen or need [D]-layer preservation. On the STABLE spec the problem doesn't exist. (3) **Granularity** — commitment is per *spec element*; one element maps to *N* code nodes → store-once-on-the-element vs N-copies-on-nodes.
- **MVP:** the drift check reads the spec directly (small, STABLE, always-loaded). *If* that ever bottlenecks, cache commitment into the node's **generated** layer as a projection (rebuilt on regen, **never hand-authored** — D80 derive-don't-copy); deferred, not now.
*Rejected:* node frontmatter as the owner (a second copy — D80 violation; regen-clobber; N-way fan-out of one fact); a separate `commitments.json` (splits a property from its subject — the spec element is its natural home).
*Evidence:* the schema already models `commitment` inline (`shared/schemas.md`); D80 (one owner, derive-or-point); D78 (nodes regenerate); D23/D76 (commitment drives the drift/promise-adequacy checks, so it must be readable by verify/align/audit). → `09`/`06`/`07`/`shared/schemas.md`/`skills/{align,verify}`.

## D107 — Project-map residuals confirmed parked; the one E2-forced call: outward-release is loopback-only over an unauthed tunnel **[DECIDED — Phase-2 E (E3); the release-loopback-only *intent* is realized structurally by D112 (a never-fronted socket, since a Host policy cannot enforce it), and its "verdict = local, low-consequence" rating is CORRECTED there — D90 makes a verdict an authoritative prompt, so any forged verdict is agent control, and credential-bearing setup verdicts join release]**
The D70 project-map/flow-view residuals, mostly confirmed correctly parked elsewhere: **tab-not-home** (resolved → tab, D99); **flow ephemeral-vs-durable** ≈ the **D78** durable **[D]** observed layer (regenerable static + durable observed, merge-on-regen); the **runtime-capture mechanism** decided for Python (`verify` observes; `sys.monitoring` fire-once — D78), **non-Python reasoned-not-measured stays open** (per-stack); **remote-control auth reserved / owner-accepted** (D70/D95). No new build.
- **The one refinement E2 forces:** outward-**release** (D105) is the **highest-consequence** console interaction — a forged *verdict* drives *local* work (qa-approve → document/commit), a forged **release** fires an *outward, irreversible* effect (push/deploy). So over the **unauthed, owner-accepted tunnel** (D70/D95 F4): **release stays loopback-only** (served/accepted on loopback only); **read + verdict** inherit the pre-existing owner-accepted tunnel caveat (as D102 already scoped remote demo-viewing/verdict). **Real tunnel auth** (Cloudflare Access / HMAC) moves from *reserved-optional* to **required-before-remote-release** — the tunnel carries low-consequence interactions at owner-accepted risk but not "authorize an outward side-effect" until auth lands.
*Rejected:* exposing release over the unauthed tunnel like read/verdict (release is a strictly larger blast radius — an outward irreversible effect, not local work); forcing real tunnel auth into MVP now (release-over-loopback needs none; the tunnel stays opt-in/off-by-default).
*Evidence:* D70/D95 (tunnel warning-only, owner-accepted, token-never-reused-as-tunnel-auth); D99/D78 (tab, durable observed layer); the outward-gate research ("the approval channel must be at least as trusted as the action is destructive"). → `03`/`07`/`05`/`11`.

## D108 — Inbox consume: a `handoff.md` consumed-set + a per-kind effect anchor; the consumer never deletes, the bus GCs on a watermark **[DECIDED — pre-Phase-3 F1; folds JF1 + JF9]**
The inbox advertised "idempotent, single-shot" but only *implied* the mechanism, and only `verdict` (parked-token) and
`release` (outbox `executed`) had a natural anchor — so a routine cold start re-read `inbox/` and **re-promoted an
already-consumed intake** / re-fired a `control` op. The model closes on three rules:
- **(1) Consume = record, never delete.** D93 makes the bus the *sole writer* of `inbox/`, so "delete-after-consume"
  was a latent **D93 violation hiding in a footnote**. Instead the orchestrator keeps a durable **consumed-set** of
  the bus-assigned `message_id` (the filename stem `<ts>-<uuid>-<pid>` — already unique, now canonical) on
  **`handoff.md`**: each boundary it lists `inbox/`, skips ids in the set, applies the rest, records their ids,
  atomically republishes. On `handoff.md` because that is *the* durable cold-start rebuild anchor — the exact moment
  the set is load-bearing; `state.json` is volatile + republished per iteration (wrong tier). Ids only → small, no
  secret, git-safe.
- **(2) Two idempotency layers — neither alone suffices.** The consumed-set covers the normal path; apply-then-record
  has a **crash window** (crash between → re-apply on restart), so each kind's *effect* must also be idempotent:
  **verdict** → the parked token (already-closed → dead-letter/no-op) · **release** → the outbox `executed` status ·
  **intake** → the **source `message_id` stamped on the promoted item** · **control** → a standing rule that
  **control ops MUST be idempotent** (no durable artifact exists to anchor on; `reprioritize`/`pause` already are —
  a non-idempotent op may not be added without bringing its own anchor).
- **(3) Bounded by a watermark.** The orchestrator publishes `consumed_through`; the **bus** GCs inbox files ≤ it
  (staying sole writer of its own partition) and the set prunes to ids above it — bounding inbox *and* set while
  adding a second writer to neither. Volume is human-interaction-paced (the autonomous loop never writes the inbox),
  so this is hygiene, not a hot path. **Sole carve-out:** a consumed **sensitive** record is unlinked by the
  orchestrator immediately after the credential lands in the secret store (D111) — a secret's latency-to-zero must
  not wait on a janitor.
- **JF9 is the same mechanism, not a second one.** Intake's missing dedup anchor and "my requests"' missing
  correlation key are one gap: the source-`message_id` stamp closes both. The register asked for two things; they
  cost one field.
- **JF1 wired — the drain step.** The boundary drain was fully decided (D91/D93/D26) yet present in **neither driver
  artifact**: an orchestrator following its brief literally would park at a checkpoint and never consume the verdict
  that unparks it. Now in `templates/orchestrator-CLAUDE.md` (read→place→advance becomes
  **drain**→read→place→advance), `templates/loop.md` (a prose *Scheduler boundary* section — the drain is plain
  control-flow, **not** a routing node, so the contract linter stays clean), and `01`. **Cadence = all kinds, every
  boundary**; order = `drain → apply control → resume ready-parked (+aging) → promote intake → start-new → fire
  release → sleep`.
- **Why:** single-shot is advertised to the entire console→orchestrator contract and is the one correctness backbone
  C2 cannot be built without — and the mechanism had to be one the single-writer partition actually permits, which
  delete-on-consume did not.
*Rejected:* delete-after-consume by the consumer (the register's own proposed wording — a D93 violation); a monotonic
**cursor** (unsafe under at-least-once + out-of-order writes: an earlier-ts message written after the cursor advanced
is skipped forever); a bus-side ack round-trip (the orchestrator is never in a synchronous path — D93); the
consumed-set on `state.json` (volatile, wrong tier) or in a dedicated `consumed.json` (a second single-writer file +
D80 owner for no gain); a separate consumed-intake ledger (redundant with the set + the stamp); `retention.py`
sweeping `inbox/` (wrong owner — retention is orchestrator-side, the inbox bus-owned); leaving the inbox an unbounded
durable log (an undefined bound is exactly the gap-class this pass exists to close).
*Evidence:* the pre-Phase-3 pressure-test register F1 — **corroborated by 5 independent finders** (A2, foundations×2,
buildability, E-outbox), the buildability instance verifier-CONFIRMED, every refutation conceding the residual
("delete-on-consume is implied rather than stated"; "intake lacks an explicit dedup key"). Reuses
D26/D48/D51/D69/D90/D91/D93/D105. → `01`/`05`/`shared/schemas.md`/`templates/orchestrator-CLAUDE.md`/`templates/loop.md`/`11`.

## D109 — Single-orchestrator election: deliberately NOT enforced — an operator-guaranteed run-constraint; the liveness marker exists only as the runner's precondition **[DECIDED — pre-Phase-3 F2]**
D93 removed `flock` on the premise "single-writer removes the write-conflict class" — but **nothing elects the single
orchestrator**: two concurrent `/start`/`--resume` processes each believe they are sole writer, and atomic-publish
stops a torn *read*, never a **lost update** (B advances item 3 and renames `state.json` over A's item-5 progress).
**The call: do not defend against it.** Electing the orchestrator is **not the package's job** — it is a documented
**run-constraint** (*run a single orchestrator per repo*), carried in `templates/orchestrator-CLAUDE.md`'s
invariants. This sits on exactly the same footing as D93's own single-writer premise, which was always an **asserted
invariant, not a mechanism** — so the call makes an existing assumption explicit rather than inventing machinery to
police it.
- **The scary vector is narrower than it looks:** F2's live case (an away human firing `claude --resume -p
  "<verdict>"` at a still-live session) assumes a usage the design already routes elsewhere — the away path is the
  **console POST → inbox** (D93/D99); `--resume` is D90's *restart* mechanism for a yielded/dead session, not a
  live-session verdict channel.
- **And a lock would cost something:** a hung (not dead) orchestrator holding a `flock` blocks a clean restart —
  friction on precisely the recovery path D90 wants frictionless.
- **The one exception (D113):** the relaunch-runner is *itself* a spawner, so a duplicate there would be **our**
  defect rather than operator error — this decision's reasoning does not reach it. The runner therefore checks a
  **liveness marker** before spawning; the marker is justified as *the runner's precondition* only, and nothing else
  consults it.
- **Honest residual (accepted):** an operator can still hand-start two `/start`s (e.g. over a session they believe
  dead but which is merely hung) and silently clobber state. Documented, not fenced.
*Rejected:* a held `flock` on `.workflow/orchestrator.lock` as a general election (the register's proposal — declined
as out of scope, and it adds restart friction); a pidfile + liveness check (PID-reuse races — D94 already rejected
this for the bus); a loser process that forwards its `-p "<verdict>"` prompt into the inbox (needs the verdict
machine-extracted from a prompt; the console POST is already the designed away path — kept as a noted additive
upgrade); silent undefined behaviour with no documented constraint (the gap between *documented constraint* and
*undefined behaviour* is ~free to close).
*Evidence:* the pre-Phase-3 pressure-test register F2 (verifier-corrected critical→high; the adjudicator concurred
that D92's `/clear`+re-`/start` arm is same-session and therefore not a second writer). Reuses D48/D90/D92/D93/D94.
→ `01`/`05`/`templates/orchestrator-CLAUDE.md`/`11`.

## D110 — Outward binding: the harness leaves the outward path; `config.outward` is the sole policy owner; the `guard.sh` push floor is BUILT and absolute on protected branches **[DECIDED + BUILT — pre-Phase-3 F3; corrects two D105 premises]**
`config.outward=allow` was **inert**: the skill self-gated, saw `allow`, ran `git push` — and the harness then
matched `settings.json`'s static `Bash(git push:*)` `ask` and prompted, **blocking away-from-terminal**. Standing
pre-auth could not waive the human, and the only workaround (hand-edit `settings.json` too) created a **second
owner** for one fact (a D80 violation).
- **The forcing constraint — this was not a free choice.** The outbox **away-release** is incompatible with a
  static harness `ask` on the same command, full stop. A release is approved in the console and **fired later**, at
  a scheduler boundary; the `ask` prompts into the Claude session's terminal, which the away human is not watching
  (and even D112's loopback-only release does not help — *loopback ≠ sitting at the Claude prompt*). So the harness
  must leave the outward path for the model to work at all. **Projecting `config.outward` into `settings.json` does
  not fix it** — the default `ask` projects to `ask` and still blocks the fire.
- **The call.** `settings.json` carries **no `ask` for the outbox-covered classes**: `Bash(git push:*)` removed,
  `Bash(gh:*)` narrowed to the non-queued surfaces (`gh pr|release|repo|api|auth|secret|workflow|gist`) — the
  existing broad `Bash` `allow` then covers `git push`/`gh issue`. The gate becomes **skill self-gate
  (`config.outward`) → outbox/release (the human) → `guard.sh` (the floor)**, making `config.outward` the **sole
  owner** of the allow/ask fact. Un-queued outward commands (deploy/publish/cloud/network) keep their `ask` — they
  have no outbox record, so removing their prompt would gate nothing.
- **Corrects D105 #1 — the harness `ask` is NOT "the backstop for a mis-coded skill."** It cannot be: the same
  prompt that would catch a mis-coded skill blocks the legitimate away-release. The two are mutually exclusive and
  away-release wins. **Accepted cost:** a mis-coded skill (or a stray model-run `gh issue`) is now caught only by
  the floor — skills are first-party and tested, so that is a bug to fix, not to fence. The
  **release-authorization marker** (guard checks an orchestrator-set "I am firing approved action X" signal) was
  designed and **deferred**: the absolute rule below removes any need for guard to tell an approved `main`-push
  from a stray one.
- **Corrects D105 #2 and BUILDS the missing mechanism — the push floor.** D105 delegated "never auto-push `main`"
  to `guard.sh` in three places and **it did not exist** (a plain `git push --force origin main` hit only the
  chaining check and passed). Now built: resolve the target refspec (`origin main`, `HEAD:main`, leading `+`,
  `--force`, `--delete`, `--all`/`--mirror`, and a bare `git push` via upstream/`push.default`) → **block ANY push
  to a protected branch, not merely a force-push** → secret-scan the **outgoing range** (a commit can reach a
  branch by a path the commit-time gate never saw). Protected = `{main, master}` **always** +
  `config.guard.protected_branches` (**add-only** — a config typo can never empty a safety floor; un-protecting
  costs a visible edit to `guard.sh` itself). Fails **closed** (an unparseable refspec is refused, not guessed).
  `guard.sh`'s exit-2 precedes the permission decision, so the floor holds even though the harness now `allow`s
  the command — which is exactly what makes handing the harness's job to the floor safe.
- **Why absolute, not a Layer-2 skill rule** (the maintainer's call, and the stronger reading of D105's own words):
  a skill-level rule rests on skill correctness, whereas the hard block is bug-proof *and* forgery-proof, and it is
  what lets the release-authorization marker stay unbuilt. Cost — no autonomous `main` push even in a solo repo —
  is the right price: moving `main` is the highest-blast-radius outward act, and feature-branch-push + human-merge
  is the disciplined norm regardless.
- **A live D87 bypass found and closed in passing (the reason the floor parses rather than regexes).** Building the
  floor on D87's `git … commit` regex shape exposed that **D87's own claim (b) was false as built**: `git -c
  core.pager=cat commit` — the *exact example D87 names as closed* — **slipped past with a secret staged**
  (empirically confirmed against the pre-slice `guard.sh`, so it is a pre-existing hole, not a regression). Cause:
  a `(-flag)*` pattern breaks on any git global option carrying a **separate value** (`-c k=v`, `-C path`) because
  the value token doesn't start with `-`, so the walk to the subcommand stops. The new push floor would have
  **inherited the same hole** (`git -c k=v push origin main`). Fix: resolve the git **subcommand** by parsing
  (`shlex`, honouring the value-taking global options, and tolerating `sudo git` / `/usr/bin/git`), with a
  generous regex retained **only** for the no-`python3` path (a false positive there is safe; a miss is a bypass).
  Both gates now key off the parsed subcommand.
- **Verified on a fixture repo:** `push origin main` · `HEAD:main` · `--force origin main` · `+main` · `master` ·
  a config-added `release` · `--all` · `--delete main` all block; `feature-x`, `-u origin feature-x`, and a bare
  `git push` on a feature branch pass; a bare `git push` on `main` blocks (upstream/current-branch resolution); an
  `AKIA…` in the outgoing range blocks and passes once reset; a chained `cd /tmp && git push` blocks. **Bypass
  regression set:** `-c core.pager=cat` / `-C /tmp/x` / `-c a=b -c c=d` / `sudo git` now block on **both** commit
  (secret staged) and push (protected branch); `git status`, `git log --oneline`, `git -c a=b push origin
  feature-x` and `echo commit` stay clean (no false positives).
*Rejected:* projecting `config.outward` → `settings.json` at `/start` (keeps config the authored owner and makes
settings generated — but cannot deliver the away-release, which is the point); keeping the static `ask` and
accepting no away-release in MVP (guts D105's away-autonomy — against the project thesis); moving `Bash(gh:*)`
wholesale to `allow` (ungates `gh release`/`gh repo delete`, which the outbox does not cover); hard-blocking only
*force*-push to protected (leaves a plain unapproved `main` push resting on skill correctness); a fully
config-defined protected set (a hard floor whose scope a config typo could empty); building the
release-authorization marker now (real coupling, unnecessary under the absolute rule).
*Evidence:* the pre-Phase-3 pressure-test register F3 — the `config.outward` inertness independently re-verified
against `templates/settings.json`, and the bare "guard has no branch logic" finding (refuted on its own as
specced-but-unbuilt) folded in here, because F3's own resolution makes the floor load-bearing rather than
deferrable. Claude Code `permissions` precedence (deny→ask→allow, first-match-wins) + its "arg-constraining
patterns are fragile → use deny + hooks" guidance, which bars an allow-glob for branch scoping but not a *list of
names read by a hook*. Reuses D35/D58/D80/D87/D105. →
`01`/`05`/`07`/`shared/schemas.md`/`hooks/guard.sh`/`templates/settings.json`/`templates/orchestrator-CLAUDE.md`/`commands/start.md`/`11`.

## D111 — Away-alert: the always-alive daemon owns notification (not the Claude `Notification` hook); deadline/reminder pinned; the secret store adopted at `.workflow/secrets/` **[DECIDED — pre-Phase-3 F4; folds JF2 + JF4 + the A6 shred fork; corrects the D90/D101 mechanism; one arm completed by D114 — this entry's "added to … the native-FS pin list" was singular where there were **two** copies, so `secrets/` reached `05` and not `07`; that miss is the direct evidence D114 cites for retiring the hand-kept lists]**
The console's one critical-path job — alert an away human that a verdict is needed — **had no working trigger**.
F4 reported three gaps; they are **one root error**: D90/D101 hung the alert on the harness **`Notification` hook**,
the one mechanism that structurally cannot do it.
- **Why the hook can never work (the three F4 facets collapse into this).** It is **event-bound**
  (permission-prompt / ~60 s idle), so at checkpoint-raise — when D91 interleaving has the orchestrator **busy** on
  the next ticket — neither trigger fires (and `settings.json` wired no such hook anyway). It is **desktop-native**,
  reaching only the machine running the loop, which is by definition not where an away human is. And it is **dead**
  exactly when the orchestrator is whole-parked or crashed — the state the away-channel exists for. So "no fire
  point", "no reachable-away default" and "no timer owner" are not three bugs; they are one wrong owner.
- **The call: the bus daemon is the sole notifier.** It is the only process alive across *all* those states (D94),
  it already has janitor duty, and it is stdlib-Python (so a webhook POST + a `parked/` scan cost nothing). It
  **watches `parked/`** → alerts on a new open checkpoint → **re-alerts every `config.checkpoint.reminder_hours`**
  → **escalates** once the absolute `deadline` passes (never auto-proceeding — D97), and raises D101's second event
  off an orchestrator-written hard-stop marker. **The `checkpoint` skill sends nothing: writing the parked record
  *is* the trigger.** D101's two-event taxonomy is untouched — only the mechanism beneath it changes. Consequence:
  the shipped `settings.json` needs **no `Notification` hook at all** (the register read its absence as a gap; it
  was never the hook's job).
- **Why one notifier, not skill-fires-initial + daemon-does-reminders:** the reminder half *needs* the daemon
  regardless, so splitting buys nothing and costs a second send-path plus a double-fire race. One owner (D80).
  Initial-alert latency = one poll interval — irrelevant to a human who is away.
- **The away channel is BYO-webhook, stated plainly (JF-adjacent honesty).** `config.notify = { webhook {url, kind:
  generic|slack}, desktop }`. The **webhook is the real channel** (reaches a phone; works from a detached daemon);
  a **desktop toast is best-effort only** — it needs a session bus, has none on WSL/headless, and reaches only
  someone already at the machine. **No webhook configured ⇒ no away alerting**, and the docs say so: a channel that
  silently reaches nobody is worse than a documented absence.
- **JF4 pinned.** `config.checkpoint = { deadline_hours: 24, reminder_hours: 4 }`, both overridable. The parked
  record's `deadline` is stamped **absolute** (park-time + `deadline_hours`), because the process that acts on it
  is the daemon — comparing wall-clock, and not present when the ticket parked.
- **JF2 closed — the secret store adopted under D80.** Referenced 4× and located 0×: now **`.workflow/secrets/`**
  — gitignored runtime, on the native-FS pin (it needs a mount that honours the mode), **atomic `0600`-create**
  (never write-then-`chmod`; explicit ACLs on Windows — the D89 OS/FS family), reusing the D95 token-file
  discipline. **Owner: the orchestrator writes** (on consuming a `sensitive` `returns`) **and reads** (the setup
  verify-probe). One correction to the finding's own suggestion: it proposed "audit-prune deletes" — **wrong**.
  These are **live credentials, not memory**; retention bounds the append-only *memory* tier, and a cap deleting a
  working key is a defect. Removal is **explicit** (rotation/teardown), never automatic. Added to the `05` layout,
  the commit-policy gitignore set, the native-FS pin list, and the `start.md` gitignore scaffold.
- **A6 resolved — the shred is a narrow carve-out.** D97 says a `sensitive` inbox record is "shredded post-consume",
  but D108 makes the orchestrator a non-writer of `inbox/`. Resolution: the orchestrator **may `unlink` exactly one
  consumed record that carried a sensitive payload**, immediately after the credential lands in the store. Scoped
  and stated as *the* exception; a secret's latency-to-zero must not wait on the bus's watermark GC.
- **Drift fixed in passing:** `skills/checkpoint` still said "post it to the console and **block on the local bus**
  — an explicit wait step", the pre-D90 live-wait model the doc-review's pass fixed in `01`/`04` but never reached
  in the skill itself. Now park-and-yield.
*Rejected:* the `Notification` hook (the root error — cannot fire while interleaving, cannot reach away, dead when
parked/crashed); the `checkpoint` skill firing the initial alert with the daemon doing reminders (two send-paths, a
double-fire race, and *more* code — the daemon is needed either way); desktop-toast as the default away channel
(reaches nobody away, and unreliable from a detached daemon); implying away-alerting works with no webhook set
(a channel that silently reaches nobody); a duration-relative `deadline` (the actor is a different, later process —
it needs an absolute instant); the finding's "audit-prune deletes the secret store" (conflates live credentials
with memory — would silently delete a working key); a synchronous bus **shred command** (a synchronous
orchestrator→bus call — against D93 — and the secret lingers until the bus acts); the **bus extracting the
credential at ingress** (genuinely better — no plaintext ever lands in the durable inbox — but it expands the bus
into a credential-store writer; **noted as the future hardening**, deferred).
*Evidence:* the pre-Phase-3 pressure-test register F4 (facet 1 verifier-CONFIRMED — the hook is event-bound and
`settings.json` wires none; facets 2–3 refuted-with-conceded-residuals, both of which resolve to the same missing
owner). D94 (the detached always-alive daemon + its existing janitor role) · D100 (stdlib-Python: `urllib` POST +
a dir scan) · D97 (timeout never auto-proceeds) · D101 (the taxonomy, kept) · D95 (the 0600 atomic-create token
discipline reused) · D80 (owner + location for every runtime artifact). Reuses D89/D90/D91/D93/D108. →
`01`/`03`/`04`/`05`/`07`/`shared/schemas.md`/`skills/checkpoint`/`commands/start.md`/`11`.

## D112 — Remote access: a structural two-socket split behind a declared identity transport; the unauthed tunnel is retired **[DECIDED — pre-Phase-3 F6; supersedes D70/D95/D107's unauthed warning-only tunnel]**
The tunnel **could not be built as specced**, and the reason is not the one the register found first.
- **(1) The specced tunnel is self-contradictory.** D95: the loopback token is **never** reused as tunnel auth.
  D107: read+verdict ride the tunnel. But every one of those endpoints is **token-gated**, so a verdict-capable
  remote browser **must** present the token. Both cannot hold: either the token goes over the wire (violating D95)
  or the tunnel serves nothing useful. The register found the near half of this (the token cannot *discriminate*
  verdict from release); the deeper half is that it cannot *authenticate* anything remotely either.
- **(2) The register's own proposed fix is unsound.** A **per-endpoint `Host` policy** makes a security boundary out
  of a header the untrusted proxy controls: if `cloudflared` forwards the tunnel Host the allowlist rejects all
  tunnel traffic; if it rewrites Host to loopback, tunnel traffic is byte-indistinguishable from loopback and
  release **cannot** refuse it — and that failure is **silent**. A boundary must be **structural**, not header-based.
- **(3) The bar is higher than D107 assumed — a forged verdict is *agent control*.** D107 rated verdicts
  low-consequence because "a forged verdict drives *local* work". But D90 makes the verdict ride as
  `claude --resume -p "<verdict>"` — an **authoritative prompt** — and `notes` is free text. So POST access to a
  verdict endpoint = arbitrary authoritative instructions into an autonomous code agent. **D107's rating is wrong
  twice:** once via credential-bearing setup verdicts (F6's finding), and once via `notes`, for *every* verdict.
  That kills "a bare bearer token on a public URL" as the gate and makes real identity the requirement.
- **The model.** **Socket B — loopback-only, never fronted:** the full surface (outward `release` +
  returns-bearing `setup` verdicts). D95's blanket Host-allowlist stands here **unmodified**, and "loopback-only"
  becomes a fact about **port topology** — nothing to spoof. **Socket A — the reduced remote surface** (reads ·
  **opinion verdicts** · the static demo), served **only** when `config.remote` declares an **identity transport**
  (`access` | `tailscale`); absent → A is not served at all. A **distinct remote token** (never the loopback one —
  D95 respected) is a **second factor** over the transport identity, applying D95's own "three independent
  failures" logic so a misconfigured Access does not instantly expose the surface. **Pairing = QR + URL fragment**,
  which **amends D95's "never in a URL"** precisely: that rule targeted the Jupyter **`?token=` *query param***
  (server-logged, `Referer`-leaked); a **fragment never leaves the browser**. A's Host-allowlist survives but its
  role changes to **anti-DNS-rebinding** (A is loopback-bound, so a local browser can hit it), *not* the boundary.
- **Risk taxonomy (corrects D107):** *a verdict carrying an **opinion** may ride A; a verdict carrying a **payload**
  may not.* Release never rides A. **One transport-confidentiality carve-out:** a credential may ride an **E2E**
  private transport (**Tailscale**/WireGuard — nobody in the middle sees it) but **never** a **TLS-terminating
  proxy** (**Cloudflare Access** — the edge sees plaintext, so a returned key would transit a third party). This is
  load-bearing for autonomy: `setup` is the *hardest* away-blocker (D97 — a missing credential cannot be skipped),
  so the carve-out makes **Tailscale the recommended transport** (no domain, E2E, strictly more capable).
- **Cost stays small because we do not own the tunnel lifecycle.** The operator runs `cloudflared`/`tailscale
  serve` against `bus.json`'s `remote_port` and is responsible for the declared transport being real — the same
  operator-responsibility stance as D109's run-constraint. Build = a second socket + a second token + a QR + one
  config key. **No JWT library** (D100's stdlib-only holds): we don't verify the Access assertion — A is
  loopback-bound and only the proxy reaches it.
*Rejected:* the per-endpoint `Host` policy (the register's lean — a proxy-controlled, silently-failing boundary);
keeping an unauthed warning-only tunnel (unbuildable, and it would hand agent control to a bearer token on a public
URL); **deferring remote entirely** (my first-cut recommendation — the maintainer's push was right: away-alerting
without away-*acting* is not worth building, and the two-socket split is exactly what makes remote safe enough to
ship); token-in-query (the Jupyter CVE class — the fragment is a different mechanism, not a loosening); picking one
transport (supporting both costs ~zero code — the daemon serves A either way — and Tailscale is the no-domain,
E2E-capable path); owning the `cloudflared` lifecycle (real build cost for an opt-in feature the operator can wire).
*Evidence:* the pre-Phase-3 register F6 (an adjudicator override of two verifier over-refutations — both invoked
"a tunnel client lacks the 0600 token", which fails precisely because a verdict-capable remote client must hold
it). D90 (verdict-as-authoritative-prompt — the fact that sets the bar) · D95 (token discipline, three-independent-
failures, the `?token=` CVE lineage) · D97 (a missing credential can't be skipped) · D100 (stdlib-only → no JWT
verify) · D102 (the static-asset serving class the demo joins) · D107 (the taxonomy this corrects) · D109 (the
operator-responsibility stance reused). → `03`/`05`/`07`/`09`/`shared/schemas.md`/`11`.

## D113 — MVP away-autonomy: the relaunch-runner is pulled onto the critical path; the C1→C2 split is retired for one component's six increments; the boundary is stated **[DECIDED — pre-Phase-3 F14 (scoping); reverses D92's deferral]**
The composite lock F14 asked for. Three calls.
- **(1) The runner is MVP, not deferred — it is the away-channel's last link.** Trace the overnight run with
  everything else decided: the loop parks on a setup checkpoint at 1am, interleaves through the independent tickets,
  then **runs out of independent work and whole-parks** — it yields, and **nothing inside Claude self-wakes** (D90).
  At 8am the human is alerted (D111), submits the verdict from a phone (D112), and the bus writes it durably to the
  inbox — **and nothing happens.** It waits until a human reaches the terminal, where they could have typed it
  anyway. So without the runner, D111's alert and D112's remote surface deliver a verdict that *queues*: away-
  autonomy stays bounded to the **interleaving-alive window** (real only while independent work remains, since
  read-only fill-work is finite). **The maintainer's own F6b standard settles it** — *if the human can't act from
  their phone, the away system isn't worth it* — because its sequel is *if the phone verdict doesn't resume the
  work, it still isn't worth it.*
- **Why D92's deferral expired:** D92 deferred the runner "to preserve the pure-config MVP". **D94 already ships a
  detached, always-alive Python daemon** — purity was spent there. The runner is not a new *category* of thing, only
  a capability of a process we already ship, so it **hosts on that daemon** (`config.runner.enabled`, off → the
  console still works but nothing resumes a whole-parked loop). D90 already blessed its shape (a thin local
  relaunch on the user's own machine/auth, explicitly *not* the cloud SDK), so the master rule — never sit in
  Claude's request path — is untouched. Bonus: it **retires D92's manual-`/clear` stopgap** (a fresh `claude -p` per
  ticket is a clean window for free), which is why D92 called it *triple-justified* in the first place.
- **(2) It reopens D109 — and honestly.** D109 declined an election as *"not ours: operator responsibility"*. That
  reasoning covers **operator error**; it does **not** reach a duplicate the *runner* creates, which would be **our**
  defect. So the runner **checks a liveness marker before spawning** — justified strictly as the runner's
  precondition, not as general operator-policing; nothing else consults it. (Batching the capture paid for itself
  here: D109 was still in flux, so this is a revision in place rather than a decision superseded two entries later.)
- **(3) The C1→C2 split is retired.** `11` sequenced *"C1 read-only console (**no bus needed** → quickest visible
  payoff) → C2 comms bus"* — **incoherent against D94/D100**: a read-only console *is* a detached daemon serving a
  browser, so **the console IS the bus** and there is no bus-free C1. They are not two phases but **increments of
  one component**: (1) daemon skeleton → (2) reads + cockpit page *(the old C1)* → (3) POST + inbox + drain *(the
  old C2 — where the verdict job actually lands)* → (4) the notifier → (5) the remote socket → (6) the runner. Each
  adds a real capability, and **no MVP goal is met until step 3**, so step 2 is a de-risking checkpoint, **not a
  shippable milestone**. (This also dissolves the JF7 C1/C2 label collision.)
- **(4) The boundary, stated (the point of F14).** With the runner in, away-autonomy is **real end-to-end**:
  alerted anywhere → act from a phone → the verdict lands durably → the runner resumes the loop. Residual bounds,
  eyes open: **release + credential-bearing setup verdicts are loopback-only** (D112 — unless the transport is
  E2E/Tailscale, which unlocks the credential case) · **protected-branch pushes never auto-fire** (D110, absolute —
  a human moves `main`) · **remote needs a declared identity transport** (D112) · **no webhook ⇒ no away alerting**
  (D111) · **one orchestrator is operator-assumed** (D109), the runner's marker being the one exception.
*Rejected:* keeping the runner deferred (leaves the away-channel one link short — F4 and F6 would be well-built
paths to a verdict that waits for you to come home); a **sibling runner process** (cleaner separation, but one more
thing to supervise when the daemon is already always-alive and already watching `inbox/`+`parked/` for D111);
extending D109's operator-responsibility stance to cover the runner ("the runner owns launches — don't `/start`
alongside it": consistent, but forgetting the runner is on is an *easy* mistake and the failure is a silent
state-clobber); keeping C1→C2 as two phases (describes a bus-free console that cannot exist, and ships a milestone
that misses the console's one job).
*Evidence:* the pre-Phase-3 register F14 (scoping) + the composite of this session's own decisions — D111 (alert)
and D112 (remote act) are what make the missing resume link visible. D90 (nothing self-wakes; the local-relaunch
shape is the legal path, the cloud SDK is not) · D92 (the deferral being reversed, and its own triple-justification)
· D94 (the detached always-alive daemon that makes the purity argument moot and hosts the runner) · D100 (stdlib
Python) · D109 (the stance this narrowly reopens). → `01`/`07`/`shared/schemas.md`/`templates/orchestrator-CLAUDE.md`/`11`.

## D114 — Disk-layout properties: `05`'s tree is the single owner of per-path `bus:` + `pin` markers; the prose lists are retired and two shipped consumers are gate-held **[DECIDED — pre-Phase-3 JF3 (the last enumeration gap); adopts an owner under D80, corrects a D93 rationale, sharpens D104]**
JF3 asked whether `outbox/` and `demos/` should be added to two enumerations (the served-read list and the native-FS
pin list). The finding **understated the problem**: those two facts had **no owner and six copies**, three of which
were wrong at the time of writing. The fix is therefore an **adoption**, not an addition.
- **The evidence that enumeration-by-hand is the wrong shape — it had already failed three times.** **D105** added
  `outbox/` and reached **neither** list. **D111** added `secrets/` and reached the pin list in `05` but **not** the
  second copy in `07`:135 — the miss is visible in D111's own capture note ("Added to … the native-FS pin list",
  singular; there were two). And `parked/` was pinned by `05` while `shared/schemas.md` never said so. The most
  recent hand-edit, made by the person actively thinking about the list, still missed a copy — so "add both to both
  lists" would have repaired three copies and left the mechanism that produced them.
- **The word "served" was hiding two different facts.** `03`:104 has the console polling **one synthesized, ETag'd
  snapshot** — so the bus was never a static file server, and "the files the bus serves" is really its **read-model
  input set**. Meanwhile `demos/` genuinely *is* raw bytes at `/demo/*`. Those are **D102's two serving classes**,
  already decided; collapsing them into one list is what made "is `handoff.md` served?" unanswerable and let `05`
  (`graph.json`) and `03` (`handoff.md` + git) hold two lists that were never the same question.
- **The call.** `05`'s **disk-layout tree is the OWNER** of three per-path properties: commit-class, **`bus:`**
  (`read` = feeds the read-model, token-gated · `static` = the D102 static class, raw bytes token-free · `write` =
  the bus is the writer · `none`), and **`pin`/`no-pin`** — a **RUNTIME-only** question, since a committed file
  lives on the repo mount by construction. Every prose list is **retired**: `05`'s own three, `07`:135, `03`:99 now
  point. The tree is the right owner because it already *was* one — it enumerates every path exactly once and
  already carried the commit-class per line; the doc-review's **A4** was that same tree being right while a prose
  list drifted from it.
- **What is retired is the *enumeration*, not the *mention*.** A doc may still state one path's property in context
  (`04`:74's "`.workflow/secrets/`, native-FS-pinned" stands). The drift class is the **list that must be complete**,
  because incompleteness is **invisible** — nothing about `05`'s pin list looked wrong while `outbox/` was missing
  from it. A single-path mention carries its own subject, so a wrong one is visibly wrong and is `align`'s job.
- **The substance, settled.** `outbox/` = **`bus:read` + `pin`** (it crosses the process boundary — the orchestrator
  writes, the bus reads it for the console's release panel — so it needs rename-atomicity, exactly like `parked/`).
  `demos/` = **`bus:static` + `no-pin`** — the register's warning was right and D104 already said why (write-once-
  then-serve, atomicity-light; a torn read is cosmetic and self-heals on a throwaway). **The two lists take
  different members**, which is precisely why a blanket "every runtime dir is pinned" rule was rejected.
- **`handoff.md` was already decided — by D108, not by the console.** Rule (3) has the orchestrator publish
  `consumed_through` and **the bus GC the inbox on it**; the watermark lives on `handoff.md`. So the bus **must**
  read it to do its own job — `bus:read`, settled, independent of any UI question. `05`:41 was under-listing;
  `03`:99's "renders from" was loosely right for the wrong reason.
- **A D93 rationale corrected (same sentence as the pin list, so it lands here).** `05` justified leaving the
  committed artifacts on the repo mount with *"git doesn't need rename-atomicity"* — a **non-sequitur**: three
  committed files are `bus:read` (`handoff.md`, `backlog.md`, `graph.json`), so the **bus** reads them across the
  weak mount whether or not git cares. Chased as a message-loss path, it **is not one**: a torn read interleaves old
  and new bytes and so cannot fabricate a `consumed_through` *higher* than one the orchestrator actually published —
  inbox GC can only **lag, never over-collect** (and D108 already scopes GC as hygiene) — while a torn
  `backlog.md`/`graph.json` render self-heals on the next 2–5 s poll. So: **bounded and accepted, now stated**
  rather than resting on a wrong reason. Corollary made explicit: `.workflow/` is **split across two filesystems**
  whenever `/start` relocates — one logical layout, not one mount.
- **The gate, because a rule nothing enforces is how these lists drifted.** Three rules in
  `scripts/check_enum_coherence.py` (its existing *owner-declares → consumers-cover* shape, presence-only):
  **R1** every `.workflow/` leaf declares a `bus:` marker, and every RUNTIME leaf declares `pin`/`no-pin` — a **new
  dir cannot land without answering both**, which is the D105/D111 failure at its root; **R2** the tree's `pin` set
  == `shared/schemas.md`'s "kept on a native filesystem" headers, **both directions**; **R3** every RUNTIME path is
  in `commands/start.md`'s gitignore scaffold (the **A2** drift class). Verified by **replaying the real history**:
  each of D105, D111/`parked/`, and A2 goes **red**, the live tree green. The two consumers are the **shipped** ones
  (which cannot point at a spec doc — the shipped-ref rule); the spec-side readers just point, so there is nothing
  left to check there.
*Why:* the two facts are load-bearing for the first build increment (the daemon must know what it reads and where
rename-atomicity actually holds), and they had drifted every single time they were touched. A general inheritance
rule was the tempting fix and the wrong one — "atomicity-sensitive" is **not mechanically decidable** (it is exactly
the judgment D104 made for `demos/`), so a blanket rule would not remove the human step, it would **hide** it and
silently reclassify the next dir nobody decided about. Marking the property **at the artifact** keeps the judgment
explicit and makes it inherit *by construction*: the question is asked where the path is declared.
*Rejected:* adding `outbox/`+`demos/` to both lists (the fix that had already failed three times; repairs the copies,
keeps the mechanism); a blanket "every atomicity-sensitive runtime dir is pinned / every `.workflow` file is served"
rule (an undecidable predicate — it relocates the judgment out of sight and silently classifies new dirs); putting
both members on both lists (**wrong on the facts** — `demos/` is served-not-pinned); making `shared/schemas.md` the
owner (it is shipped, so it cannot point at the spec — and it has no header for `demos/`, `backlog.md` or
`graph.json`, so it is not a complete registry); making `commands/start.md` the owner (it is a *scaffold* list — it
deliberately omits the dirs created at runtime — and shipped besides); a fourth meta-gate script (this is the same
invariant shape `check_enum_coherence.py` exists for); treating the `bus-read ∧ committed` exposure as a new
decision (chased and **downgraded** — the failure is bounded to GC lag and a self-healing render, so it is a
rationale fix, not a mechanism change).
*Evidence:* the pre-Phase-3 doc-review register JF3, **re-verified against the artifacts and found to understate the
gap** — the three prior drifts (D105's, D111's, and `parked/`'s) were found by reading the files, not the register.
D80 (one owner per fact + the blast-radius sweep) is the law being applied; D89 tier-2 is the gate this extends; A4
is the precedent (the tree right, the prose list drifted). Reuses D53/D62 (layout) · D93 (the pin + the corrected
rationale) · D99/D100 (the synthesized ETag'd snapshot — why "served" was the wrong frame) · D102 (the two serving
classes, the `bus:` vocabulary) · D104 (`demos/` atomicity-light; its "co-located with the served root" phrase
sharpened — there is no single served root) · D105 (`outbox/`) · D108 (`handoff.md` is `bus:read`) · D111
(`secrets/`). → `03`/`05`/`07`/`shared/schemas.md`/`scripts/check_enum_coherence.py`.

---

## Not yet decided (tracked in `07`)
Graph regenerate-vs-incremental **now resolved (D78 — static-regenerate + durable-observed-merge)**; the D78
follow-ons (node-ID stability across renames, observed-edge staleness/decay, non-Python capture mechanism) are the
open threads. Model/effort map; collision **independence test** (**decided — D91 eligibility predicate:
dependency-ready ∧ file-disjoint ∧ ¬1-hop-neighbor**; waves grouping D36); Arbiter input contract; **checkpoint
block/resume + autonomous reset now decided (D90/D92 — durable park + `claude --resume`; the runner is the deferred
autonomous path)**; **the A2 bus contract / A3 lifecycle / A4 trust now decided (D93/D94/D95 — single-writer +
atomic-publish + a two-mechanism protocol · a session-independent detached daemon · a capability-token +
Host-allowlist loopback trust)**; **the console cluster B now decided (D99–D101 — a read-only supervision cockpit +
screen list + snapshot-poll + "my requests" surface · a stdlib-Python detached daemon + zero-build CSP-clean page ·
the two-event notification taxonomy)**, so the **website stack (B4) is closed**. Intake follow-ons:
engineering-feasibility pass **designed as the proportional-rigor gate (D69), implementation deferred**;
**checkpoint cluster C now decided (D96–D98 — judgment/action taxonomy + trigger rule · verb-enum verdict +
plural machine-verified setup gate · MVP help set)**; **the demo-skill cluster D now decided (D102–D104 —
serving/format + sandbox-CSP isolation · refine-round cap · on-disk location)**; **the cross-cutting cluster E
now decided (D105–D107 — the outward-action *outbox* [not a checkpoint] + `config.outward` allow|ask + a new
`release` inbox kind, retiring `checkpoints/`; commitment-status stored spec-inline read code→intent; the
project-map residuals parked + outward-release loopback-only)** — **Phase-2 DESIGN is COMPLETE (next = Phase 3,
build the website).** `init` follow-ons: brownfield
ingest **designed (D68); the `ingest` skill is authored**; **console launch + disk-layout read/write protocols now
decided (D94/D93)** (the `spec/`+`.knowledge/` docs-root placement closed — D62). Skill-review follow-ons:
incidental-issue-resolution detection — deferred; outward-action permission mechanics **decided (D105 — the
outbox model)**. Adoption
follow-ons: the **retention & archival law** is **closed** (D59–D60 write-law leaks + D61 cap-and-archive read
law) and the **retention script is built** (D71); what remains is **Sessions distillation** (deferred) and
`K`/threshold tuning against real runs. Plus whether `verify` samples the real diff vs trusts the `changelog` (#8); **shipped-glue Windows portability is a new open validation gap (D89)** — the
shipped bash glue assumes a bash interpreter on the target OS, unverified on native Windows (the D71 split
stands, no refactor). **Two new (user-raised):**
a synthesized **project-state view**, and a **framework version-update** skill. **Alignment pass (D63/D64):**
the alignment-scan **skill** (`align`) + its decidable contract linter are **built (D81)** — the semantic layer
is validated Phase 2/3; two prevention follow-ons — **single-source status** and a **capture-time blast-radius
sweep** — are **resolved (D80)** (an ownership map + the `check-status-coherence.sh` gate + a capture-time
blast-radius step). The **doc-authoring agent** is
reserved (D65). The **drift-gate wiring** is **authored** (D65/D67 — `commit` mechanical step + `pre-commit`
backstop + generated `checks.sh`); what remains is `checks.sh`'s per-stack generator, which rides the `/start`
enforcement-wiring build. All → `07`.

## D115 — The runtime substrate made resolvable + verifiable: a `runtime.json` pointer, a separate `bus.lock`, and mode-verified-not-requested **[DECIDED + BUILT — Phase-3 increment 1; corrects D93/D94's pin rationale and completes D95's token discipline; three findings MEASURED, not reasoned]**
The pin marker was **declared but never actionable**, and the reasons given for it were substantially wrong. Both
surfaced on the first line of the first build increment, and all three findings below are **measurements on the real
`/mnt/c` 9p mount**, not arguments.
- **(1) A pinned path could not be FOUND — the design was unbuildable here.** D93/D114 say every runtime path marked
  `pin` is relocated to a native filesystem and "the tree is one logical layout, not one mount". Nothing recorded
  *where* the relocation went, and nothing could compute it. The circularity is exact: **`bus.json` is itself
  pinned**, so the discovery record lived inside the tree you needed it in order to discover — the daemon could not
  publish, `/start` could not adopt, the browser could not be pointed anywhere, and a cold-start orchestrator could
  not find `parked/`. **The call: a gitignored `.workflow/runtime.json` pointer** (`{runtime_root}`) written by
  `/start`; **absent ⇒ `.workflow/` is the runtime root** (the common non-WSL case, zero indirection). A pointer
  naming a missing root **fails loudly** — a silent fallback to the repo mount would land the token and the inbox on
  the exact filesystem the relocation exists to avoid.
- **(2) You cannot `flock` the file you atomically rename — MEASURED, on ext4 *and* 9p.** A rename swaps the inode
  out from under a held lock: the next daemon opens the **new** inode, finds no contention, and starts. Two daemons,
  no error, on the mechanism that D94 makes the singleton election. Nothing in the spec named the lock's path at all,
  so "lock `bus.json`" was the obvious build — and it is broken. **The call: a separate `bus.lock`, created and
  written in place, never renamed over.** A fixture test pins the measurement so a platform change fails loudly
  rather than silently re-opening the hole.
- **(3) A mode is a request, not a guarantee — the silent, open failure.** On `/mnt/c`, a file created `0600` comes
  back **`0777`**: from Linux, with no error. So D95's "atomic 0600 create, never write-then-`chmod`" is **a no-op on
  that mount** — necessary, but not sufficient. A faithful implementation yields a **world-readable capability token
  and reports success**. **The call: `stat` the achieved mode after creation and surface a filesystem that ignored
  it**, never assume it. This widens past the token: `secrets/` holds live credentials under the same discipline, and
  was protected only by the luck of its placement, since the rule was never generalized. It also **re-frames the
  D89 family** — this was filed under "Windows lacks 0600", which read as a portability footnote about a platform we
  don't ship on; it is live on the maintainer's own machine, and the honest statement is **any mount that ignores
  mode**.
- **Two of the pin's three stated reasons were wrong; the pin survives on the third.** Measured on 9p: **mode FAILS**
  (the strongest reason, previously mis-filed as a Windows concern) · **`rename` atomicity** stands as the D93
  concern · **`flock` DOES NOT FAIL** — it excludes correctly and the kernel releases on death, exactly as on ext4.
  So **"flock is weak-to-broken on DrvFs" is false as stated** and is retired as a reason to pin anything. It is a
  Linux-kernel-mediated lock within one distro — which is precisely the only case that matters, since the daemon and
  `/start` are both Linux processes there. It would not coordinate with a *Windows* process: a real limit, and a
  different claim than the one that was made. `bus.lock` stays pinned for **co-location** with the record it guards,
  and that reason is stated rather than borrowed.
- **Why one entry, not three:** they are one root — the substrate's paths were declared (`pin`, `0600`) without
  anything making them **resolvable or verifiable**. D114 retired the hand-kept pin *lists* because they drifted, but
  never asked whether the marker could be *acted on*. The tree said `pin`; no process could obey it.
- **Why measurement, not review:** this is the third consecutive session where the design was right about the *gap*
  and wrong about the *mechanism* (F3's config projection, F6's Host policy, D87's push-floor claim). Two of the
  three findings here are the reverse of what the spec asserts, and **no amount of re-reading would have produced
  them** — the 9p mount reports success in both failing cases. The discipline that earned them is driving the real
  thing on the real filesystem.
*Rejected:* `config.json` gaining a `runtime_root` key (it is **committed**, and this is a machine-specific absolute
path — a clone would carry another machine's `/home/...`; the option that looks obvious and is wrong, named here so
it is not re-proposed); **deriving** the runtime root from a hash of the repo path (no state, but a repo move or
rename silently orphans live parked tickets, invisibly and unfixably by hand); **symlinking** each pinned path from
`.workflow/` (preserves one literal tree and rename stays native, but depends on DrvFs symlink support, confuses
Windows-side tooling, and needs repair on every `/start`); locking `bus.json` itself (measured broken); trusting the
mode argument (measured broken, and it fails *open*); pinning `bus.lock` for `flock`'s sake (the measurement says
otherwise — the honest reason is co-location).
*Evidence:* direct measurement on the maintainer's WSL2 machine (`/mnt/c` = 9p, `/` = ext4), both filesystems, each
probe run as separate processes: second-holder exclusion, kernel release on `kill -9`, lock-vs-rename, and achieved
`0600` mode. Re-pinned as fixture tests in `scripts/test_bus.py`. Reuses D53/D62/D80/D89/D93/D94/D95/D114. →
`03`/`04`/`05`/`07`/`shared/schemas.md`/`commands/start.md`/`scripts/bus.py`/`11`.

## D116 — The daemon's build contract: a per-project copy, a jobs frame whose idle is a conjunction, and a meta-tag token bootstrap **[DECIDED + BUILT — Phase-3 increments 1+2; closes register F10 + F11; closes the local half of the F6 token-bootstrap residual]**
The three calls the daemon could not be built without, none of which had an owner.
- **F10 — where the daemon lives.** `start.md`'s copy list enumerates every shipped script and contained **no
  daemon**; the layout tree had `bus.json` (the record) but no daemon *path*; step 5 was still a stub. **The call: a
  per-project copy at `.claude/scripts/bus.py`**, exactly like `retention.py` / `codemap/` / the gates. That
  consistency is worth more than the copy it saves, and it **dissolves F10's keying question** rather than answering
  it: lock, record, and port all derive from that project's runtime root, so two projects cannot collide by
  construction. The frontend is **embedded in the same file** (a placeholder-substituted page + its script and
  style, served as separate responses so `script-src 'self'` holds) — one file to copy, and no asset-resolution
  class of bug. Revisit if it outgrows the single file; the code-map's directory is the precedent.
- **F11 — what "idle" means.** D94 said "heartbeat-aware idle-timeout" and defined neither word. F11's horn is real:
  key the janitor on an **orchestrator** heartbeat and it starves exactly when the orchestrator is dead — the state
  the daemon exists to cover. **The call: the daemon owns JOBS, and `is_idle()` is the conjunction of their votes**
  (plus no HTTP for T; default 72h). Each job answers "anything outstanding?" — so the notifier and the runner each
  add a **term**, not a rewrite. An **open, within-deadline checkpoint suppresses shutdown**: reaping the away
  channel while a verdict is owed defeats the daemon's purpose in the one scenario it was built for. The
  `parked/` scan therefore ships in increment 1 **even though nothing alerts yet** — the janitor is correct from the
  first line instead of being wrong-by-construction until increment 4. `status` names *which* job is holding it open,
  so the predicate is legible rather than a mystery.
- **The local token bootstrap** — conceded in F6, closed for remote only by D112 (QR + fragment), left open for the
  loopback page. The page cannot be token-gated (a browser cannot set a header on a document navigation), yet every
  read needs the token. **The call: the daemon injects it as a `<meta>` tag** when serving the page. Not a script, so
  no nonce and no `unsafe-inline`; no secret ever printed. **The concession is stated, not hidden:** whoever can GET
  the page from an allowlisted Host holds the token — which is a local browser, the token's intended audience anyway.
  It adds no surface D95 did not already concede when it put the page in the token-free static class; the **Host
  check, not the token, is what stops a rebound page** from reaching that far.
- **Verified by driving, never by type-checking** — the failures here are all invisible to a static read: a
  deadlocked shutdown is a *hang*, a defeated lock is *silence*, an ignored mode is *success*. Driven end-to-end:
  detachment (own session leader, outlives the spawning terminal) · 5 concurrent `ensure` → exactly one daemon, one
  listener, one lock holder · `kill -9` recovery through a stale record naming a plausible pid · `POST /shutdown`
  actually exits · token / Host / cross-site / 415 / 413 all refuse · ETag 200→304→200 · the pointer relocating the
  runtime half while committed files stay put · an open checkpoint suppressing the reap, and the suppression lifting.
  **Windows→WSL loopback preserves the `Host` header** (tested from the Windows side), so the allowlist does not
  reject the operator's own browser — the one deployment risk flagged before the build.
*Rejected:* a shared `~/.claude/scripts/bus.py <project_root>` (saves N copies, but invents an invocation shape with
no precedent in the package and makes cross-project lock/port collision a live question the per-project copy simply
does not have); the daemon under `.workflow/` (that tree is state, not code); loose frontend assets (a second
copy-path and an asset-resolution question, for editing comfort); an idle timer keyed on the orchestrator (starves
when the orchestrator dies — F11's own horn); a serve-only daemon with the notifier retrofitted (the janitor would
be wrong until increment 4); printing the token in the console URL as a fragment, mirroring D112 (one mechanism for
both sockets is genuinely attractive — but it puts the token in terminal scrollback **and the session transcript**,
widening the audience D95 bounds to a 0600 file); token-free reads behind the Host check alone (collapses one of
D95's three independent failures).
*Evidence:* the pre-Phase-3 register F10 (independently confirmed against `start.md`'s copy list + `scripts/`) and
F11 (the verifier named the heartbeat-vs-survive-death tension as a genuine residual); F6's conceded token-bootstrap
residual. Driven end-to-end on WSL2 + verified from the Windows host; 39 fixture tests in `scripts/test_bus.py`
(gate suite 89 → 128). Depends on D94/D95/D99/D100/D115; reuses D71/D80/D102/D111/D112/D114. →
`03`/`05`/`commands/start.md`/`scripts/bus.py`/`scripts/test_bus.py`/`11`.

## D117 — The drain is SPLIT: its bookkeeping is code (`drain.py`), its apply stays the brief — a rule stated only in a decision log is not a rule the consumer follows **[DECIDED + BUILT — Phase-3 increment 3; realizes D108's consume model, corrects the half of it that was never wired to a consumer; MEASURED against real sessions]**
D108 closed "the inbox consume mechanism is asserted, not realized" — and then **reproduced its own defect one level
down**. The mechanism was written into `08` and `shared/schemas.md`, and the *drivers* the orchestrator actually
follows got a subordinate clause: `consumed_through` appeared **once** across `templates/` ("once you publish the
`consumed_through` watermark"), never defined; `prune` appeared **nowhere**; `loop.md` did not mention the watermark
at all. The bound was real in the decision log and absent from the consumer.
- **The split, drawn by measurement rather than taste.** Three real `claude -p` sessions were driven against the
  actual brief over a seeded inbox (an already-consumed intake · a valid verdict · an unknown-token verdict · a
  control op stamped *later* than the rest · a new intake · a release naming one pending + one already-`executed`
  action). **The apply half was right 3/3** — control first despite its later ts, the token match, the dead-letter
  instead of a silent resume, the doubly-anchored skip (set *and* `source` stamp), the `executed` skip. **The
  bookkeeping half failed 2/3**: both sonnet runs kept every id, producing an **unbounded consumed-set** on the file
  every cold start reads whole. The opus run pruned correctly *and flagged the spec as ambiguous unprompted* ("both
  readings agree the watermark is …-9006 … collapsing is the only reading that respects bounded-by-construction").
  So: **apply = judgment, stays prose; bookkeeping = a pure function of (inbox, `handoff.md`), becomes
  `scripts/drain.py`** (`list` → apply → `record`). Not a routing node — plain control-flow — so the contract linter
  stays clean; `retention.py` is the precedent (a tool the orchestrator *calls*).
- **A second reason the brief could not have worked, whatever it said.** D93 mandates `handoff.md` be published
  write-temp → `fsync` → `rename` → `fsync(dir)` — "the one file where crash-durability, not just atomicity, is
  mandatory". **A model holding a text-writing tool cannot express a rename**, so that mandate was unmet at the drain
  no matter how the prose was worded. `drain.py record` is what makes it true. (The *handoff step* still writes the
  anchor by hand and remains unmet — logged in `07`, bounded because `handoff.md` is committed, so git holds the last
  good copy.)
- **The machine block.** Prose and machine state share one file, so the machine half is a fenced, delimited block
  (`<!-- drain:begin -->` … `<!-- drain:end -->`) carrying `consumed[]` / `consumed_through` / `dead_letters[]`.
  `drain.py` rewrites only the block; the orchestrator rewrites only the prose. Format + parser live together in
  `bus.py` (the bus reads the watermark to GC its own partition — `bus:read`); `drain.py` is the sole writer.
  **Dropped-block residual, accepted:** a session that rewrites `handoff.md` wholesale can drop it; `drain.py`
  rebuilds the structure but the *set* is gone → the next drain re-applies → **layer 2 (the per-kind effect anchor)
  catches it**. That is the crash window's twin, and it is exactly why D108 has two layers rather than one.
- **The watermark froze — found only by driving, after 27 unit tests passed.** The brief tells the orchestrator to
  record each id **the moment its apply succeeds** (smallest crash window), so ids arrive **one at a time**. Pruning
  drops an id from the set as soon as the mark passes it — so on the next pass that id is no longer "in consumed",
  the contiguous-prefix walk **stops dead on it, and the mark never moves again**: GC halts, the inbox grows
  forever, and the bound D108(3) exists to provide silently does not hold. Every batch-at-once test passed while
  this was broken. **The rule: an id at or below the mark counts as consumed** — that is what the mark *means*, and
  the set has legitimately forgotten it. The real session also **rationalized the frozen output as correct** ("not
  yet a contiguous prefix … that's expected" — they *were* a contiguous prefix), which is the argument for the split
  restated: a model takes its tool's output as authoritative and explains it rather than catching it.
- **Why:** single-shot is advertised to the whole console→orchestrator contract, and it is the one correctness
  backbone the POST path cannot ship without. D108 made the mechanism *decidable*; this makes it **followed**.
*Rejected:* fixing the prose alone (the bound stays an assertion about a model, re-testable only by re-driving one,
at a measured 2/3 — and it cannot reach the atomicity mandate at all); `drain.py` owning the apply too (triage and
per-kind routing are judgment — measured right 3/3, so there is nothing to fix); a shadow copy of the consumed-set
against the dropped block (a second source of truth — D80 — to cover a case layer 2 already bounds); recording ids in
one batch at the end (widens the crash window the two-layer model exists to narrow).
*Evidence:* three driven `claude -p` sessions on v2.1.211 over a seeded inbox (2/3 unbounded set; the third flagged
the ambiguity itself); a fourth driven session against the *fixed* brief that produced the frozen watermark on real
state; the fix re-verified against that session's own output (mark unfroze 9001 → 9004, stopping correctly at the
unapplied id) and the regression test confirmed to fail against the pre-fix code. 27 fixture tests in
`scripts/test_drain.py`. Reuses D71/D80/D90/D91/D93/D105/D108/D116. →
`01`/`05`/`07`/`shared/schemas.md`/`templates/orchestrator-CLAUDE.md`/`templates/loop.md`/`commands/start.md`/`scripts/drain.py`/`scripts/bus.py`/`11`.

## D118 — The inbox's ordering contract: filename order ≡ VISIBILITY order, or the watermark deletes a message nobody consumed **[DECIDED + BUILT — Phase-3 increment 3; completes D108's rule (3), whose safety rested on a guarantee nothing provided; MEASURED]**
D108's GC rule is "the bus collects every inbox file at or below the watermark the orchestrator published", and the
orchestrator computes that watermark **from what it can see**. That is sound only if a message can never *become
visible* carrying a ts lower than one already visible — a guarantee **nothing in the design provided, and nothing
named**.
- **Measured, not argued.** The naive build (stamp the name from the clock, then write + rename) loses messages: a
  thread that names itself *first* can be descheduled and rename *last*. Replayed directly — the drain sees only the
  later message, publishes the watermark above it, the stalled write lands beneath, and the janitor deletes a
  **verdict a human submitted, silently**. `ThreadingHTTPServer` makes this live, not theoretical.
- **The call: allocate the name AND publish it under ONE lock** (so the interval where a name exists but is not yet
  visible cannot overlap another allocation), **plus a monotonic floor** so no id is ever re-issued at or below the
  last. The floor is the higher of *the newest name on disk* and *the published watermark* — and the second half is
  not belt-and-braces: **the GC's whole job is to empty this directory**, so the steady state is an inbox with
  nothing to prime from, and a daemon restarting there under a backwards clock step (NTP, a suspended laptop) would
  issue an id beneath the watermark that the janitor collects before the orchestrator ever drains it. The watermark
  is the durable high-water record of what has been issued, so it is the honest floor.
- **The same hole, one door over.** The sensitive carve-out unlinks a consumed message before the janitor reaches
  it, so the watermark computation reads *visible ∪ consumed*, never the directory alone — computing over the disk
  would let that hole stall the mark permanently beneath it.
- **Why:** the watermark is the only thing bounding the inbox, and its failure mode is the loss of exactly the
  message class the away channel exists to carry. A mutex is a cheap price for turning an assumption into a
  guarantee.
*Rejected:* an mtime grace period on the GC (narrows the race, never closes it, and buys a tunable nobody can reason
about); GC-on-the-explicit-consumed-set instead of a watermark (unbounds the set — the thing the watermark exists to
bound); priming the id sequence from disk alone (measured hole: the collected inbox is the steady state); trusting
wall-clock monotonicity (a clock step is exactly when this fails, and it fails silently).
*Evidence:* direct measurement — the naive build replayed to message loss ("never-consumed files the bus would GC:
[…]"), the append-lock replay then reporting none; both pinned as fixture tests, including the 40-way concurrency
case and the restart-under-a-backwards-clock case. Reuses D93/D94/D108/D115. →
`05`/`shared/schemas.md`/`scripts/bus.py`/`scripts/test_bus.py`/`11`.

## D119 — The POST surface's four unowned calls: one canonical id, a dead-letter that exists, a closed control enum, and a credential that never enters a context **[DECIDED + BUILT — Phase-3 increment 3; completes D95/D97/D111/D115's discipline on the paths this increment opened]**
The calls the POST path could not be built without, none of which had an owner.
- **`ticket` ≡ `message_id` — the vestigial field is retired.** `intake`/`control` carried a `ticket` in the body,
  which **the client cannot know at POST time**, while JF9's `source: message_id` stamp is what correlates a request
  to the item it became. Two ids for one thing would have made "my requests" correlate the wrong one. The **bus
  assigns one canonical id** (the filename stem), the `202`'s `Location` names it, and the same string is the
  consumed-set entry, the backlog `source` stamp, and the console's `localStorage` key. **"My requests" therefore
  needs no mechanism of its own** — the per-kind effect anchors D108 already required *are* the status, which is why
  a ticket still resolves after the message is collected and the set pruned (verified: an intake reads "became
  item-9", a dead-letter reads its reason, both after GC emptied the inbox).
- **The dead-letter surface existed nowhere, and every session invented one.** All three driven runs improvised a
  section into `handoff.md` — a **committed, `bus:read`** file — and invented **two different schemas**
  (`dead-letters[]` ×2, `needs-human[]`). It is now `dead_letters[]` in the machine block, `drain.py`-owned, capped
  at 20 and **deliberately not pruned by the watermark**: a dead-lettered verdict is the one message a human most
  needs told about, and collecting it the moment the mark passes would erase the notice before it was read.
- **`control.op` is a CLOSED set — `{reprioritize, pause, resume}`.** A control op has no durable artifact to anchor
  on, so the *only* thing making a redelivered one safe is that re-applying it is a no-op; an open set admits a
  non-idempotent op through the front door and silently breaks the drain's crash-window safety. **`resume` is a
  named addition** (it is in no prior decision): `pause` without an un-pause means a human can halt the loop from
  their phone and must then be *at the terminal* to restart it — the exact failure the away channel exists to
  prevent. It is idempotent (re-clears a flag). Closed, so `check_enum_coherence.py` can guard it.
- **A returned credential never enters a context.** D97 says a `sensitive` `returns` is written to the secret store
  and never logged — but the orchestrator was to do it, and an orchestrator reading the file puts the key in its
  transcript, which is precisely the audience-widening D116 rejected for the token. So `drain.py list` **redacts**
  it and `drain.py secret` moves the value to `.workflow/secrets/`, verifies the achieved mode, unlinks the record,
  and records it consumed — in one step, without the value being printed. Verified end-to-end: zero occurrences of
  the key in the drain's output, the value intact in a 0600 store, the inbox record gone.
- **D115's mode finding, generalized and made to fire.** D115 stat'd the *token*. From this increment the same tree
  holds inbox messages carrying live credentials, so the daemon now **probes the runtime root once at boot** and
  says what is exposed. Measured: on `/mnt/c` it reports "does not honour file modes (a 0600 create came back
  0o777) … the capability token, any credential returned at a setup checkpoint while it sits on the inbox, and the
  secret store are all readable by other users"; on ext4 it is silent. The pin was always justified by this; nothing
  had ever checked it on the paths that carry the secrets.
*Rejected:* a client-generated ticket (a second id to reconcile against the `source` stamp, for nothing); leaving the
dead-letter surface to the brief (measured: three runs, two schemas, into a committed file); an open control enum
with a documented idempotency rule (unenforceable — the D108 concern); the orchestrator reading a sensitive message
itself (puts the key in the transcript); per-file mode checks instead of a tree probe (answers the question one file
too late, and only for files that happen to be checked).
*Evidence:* the three driven sessions (the improvised dead-letter schemas); direct measurement of `probe_mode` on the
real 9p mount vs ext4; the sensitive path driven end-to-end (redaction, store, unlink, mode); the "my requests"
lifecycle driven through GC. Fixture tests in `scripts/test_bus.py` + `scripts/test_drain.py` (gate suite 128 → 177).
Reuses D93/D95/D97/D99/D105/D108/D111/D115/D116. →
`03`/`05`/`07`/`shared/schemas.md`/`scripts/bus.py`/`scripts/drain.py`/`11`.

## D120 — The notifier built: alert state gets a home, event 2 ships its buildable arms, and three stated mechanisms measured wrong **[DECIDED + BUILT — Phase-3 increment 4; realizes D101/D111's away-alert; corrects D94's linger framing, D101/D111's event-2 sequencing, and D93/schemas' desktop rationale; MEASURED, not reasoned]**
The daemon now watches `parked/` and alerts an away human — the console's one critical-path job. It is a **term on
the existing `parked` job**, not a rewrite (the idle vote and the alert read the same open-checkpoint set — D116's
jobs frame is exactly this). But four of the mechanism's load-bearing details had no owner or were stated wrong, and
the wrong ones were only reachable by driving.
- **Alert state had no home — the likeliest gap, and it is a fourth daemon-owned path.** D111 specified watch →
  alert → re-alert → escalate but never said where "already alerted" is recorded. The daemon **cannot** write
  `parked/` (single-writer, orchestrator's — D93) and **cannot** use `bus.json` (boot-scoped, rewritten at the
  restart the state must survive). In memory ⇒ **every restart re-alerts every open checkpoint**, and on WSL
  restarts are routine, so an away human gets spammed and learns to ignore the channel — D101's own failure mode.
  **The call: `.workflow/alerts.json`, a fourth path the daemon alone writes** (`{checkpoints, dead_letters}`),
  loaded at start so a restart is quiet, atomic-`0600`, pinned. Its governing rule is **fail toward noise: a lost
  or corrupt file re-alerts rather than going silent** — a missed alert is the one failure this increment exists to
  prevent. Not a second writer of anyone's partition (the daemon writing its own state), so D93 holds.
- **Event 2 ships its two real-source arms; the third was a sequencing error.** D101/D111 said the daemon raises the
  loop-hard-stop event "off an orchestrator-written hard-stop marker" — which **has no writer, and a crash cannot
  write one anyway** (it needs orchestrator liveness, which D109 declined and D113 schedules as the runner's
  precondition, increment 6). So two of the three D101 escalation arms are buildable **today** with zero new
  writers — the record's absolute-`deadline` escalation, and the `handoff` **dead-letter** escalation (`drain.py`
  writes `dead_letters[]`, the bus already reads it) — and the thrash/crash arm is **deferred to increment 6**,
  where its liveness signal lands. This ships a *truthful* two-event taxonomy rather than one-and-a-half arms hung
  on a marker no orchestrator could reliably write.
- **`loginctl enable-linger` is the wrong lever for the WSL death — it would not have helped.** D94 filed the
  daemon's death-with-terminal as an "owner-accepted caveat" with "`enable-linger` / `.wslconfig`" as the opt-in
  upgrade, in one breath, as if alternatives. **Measured false:** `KillUserProcesses=no` (logind kills nothing on
  session end), and both a shell and a `setsid` child land in **`/init.scope`, not `user-1000.slice`** — linger
  keeps alive a slice the daemon never lives in. The real killer is the WSL **VM lifecycle**, Windows-side,
  reachable only from `.wslconfig` (`vmIdleTimeout`), which **no setting inside the distro and no line of `bus.py`
  can veto.** So the question "is linger a `/start` step or a precondition" has no useful answer — linger is not on
  the menu. **The call: probe and surface, never block.** The daemon detects WSL at boot and reports away-channel
  readiness — webhook configured?, currently failing?, and the WSL death caveat — in the boot log and `status`,
  because a notifier that cannot notify must be *visible*, not silent (D111's own standard). Refusing to boot was
  rejected: it would break increments 1–3, which lose nothing without alerting (the inbox is durable).
- **`config.json` was `bus:none` — "the bus never touches it" — and this increment makes the daemon read it.** A
  straight contradiction under D114 (the tree is the single owner of `bus:` markers). Now `bus:read`. The daemon
  reads `notify`/`checkpoint` across the committed repo mount; static after init, and a parse failure degrades to
  **no away channel, surfaced** — the safe direction. And the **desktop-toast rationale was measurably wrong**
  (small, but the pattern again): `schemas.md` said a toast "needs a session bus, has none on WSL/headless."
  Measured: the session bus **exists** (`/run/user/1000/bus`) and `notify-send` is installed; it fails because **no
  daemon owns `org.freedesktop.Notifications`**. Right conclusion (toast is best-effort), wrong reason — corrected,
  and the failure now reaches `status` instead of vanishing.
- **`parked_seq` is removed, not given a writer.** It appeared once repo-wide — in the parked-ticket field list —
  with no writer, no reader, no semantics. It was the only field that could distinguish two *different* checkpoints
  on the *same* ticket, which the alert-dedup key needs. Rather than invent a writer for a speculative field, the
  key is **`ticket_id` + the absolute `deadline`** — which has stated semantics and is stamped fresh at each park,
  so a resolve-then-re-park alerts again. Its one bound (two parks landing the same `deadline` second collide) is
  accepted and recorded in `07`: a re-park almost always yields a later deadline, and the cost is one missed
  *second* alert on one ticket, never a lost verdict.
- **The webhook is a doorbell, not a letter, and not a D105 outward action.** Gating an *alert* behind human
  approval is circular (the human is away — that is why we alert), so it does not join the outbox. SSRF is a
  non-threat: the URL is the operator's own committed `config.json`, and whoever can edit it already owns
  `CLAUDE.md`. The real concern is the payload — so it carries **only `{event, ticket_id, deadline, overdue,
  console}`, never the request body or notes** — project content (and any credential a request field might carry)
  does not leave the machine for a third party like Slack. Verified: the driven POST carried the ticket, not the
  request text. Delivery failure is a **channel** property — a failing webhook backs off the whole channel
  (doubling, capped at `reminder_hours`) and does not mark the checkpoint alerted, so a dead URL neither storms nor
  loses the alert; the reminder path retries once it recovers.
- **Escalation continues, it does not go quiet.** Past the deadline the daemon escalates **once** (a distinct
  overdue alert), then reminders **continue marked overdue** — going silent after escalating loses the ticket; a
  reminder storm trains ignoring. And **no backlog replay**: a daemon gone 10h with a 4h interval fires **one**
  reminder on wake, not three.
- **Driven, never type-checked (the failures here are invisible to a static read).** A real detached `bus.py ensure`
  daemon POSTed a real HTTP sink (doorbell payload, no request body); `stop` → `ensure` (a fresh daemon, same disk)
  fired **zero** duplicate alerts — the restart idempotency that in-memory state would have spammed; reminders,
  escalate-once-then-overdue, re-park-re-alerts, no-backlog-replay, dead-URL-backoff, slack-vs-generic,
  no-webhook-⇒-no-POST, and desktop-failure-surfaced all driven; the three pre-measurements (`Linger=no`, no
  notification name owner, `/init.scope`) reproduced. 18 fixture tests (gate suite 181 → 199). **The twice-carried
  browser-render residual is CLOSED** — the live cockpit was rendered in headless Chrome and read as legible; one
  non-blocking nit (raw-ISO deadline) is filed in `07`.
*Rejected:* in-memory alert state (re-alerts every open checkpoint on every restart — WSL spam); folding it into
`bus.json` (boot-scoped — destroyed at the restart it must survive); building the hard-stop marker now (cannot catch a
crash — the main case — and pulls increment-6 liveness work forward); `enable-linger` as the WSL fix (wrong layer —
the daemon is in `/init.scope`, and the VM is Windows-side); a hard boot precondition (breaks increments 1–3, which
work without alerting); desktop toast as the default away channel (reaches nobody away, and fails on this box); a rich
payload echoing the request body (data egress to a third party, and can leak a credential — against D119's
keep-secrets-out-of-context discipline); keeping `parked_seq` (a field with no writer, invented for a speculative
re-park); going silent after escalation (loses the ticket) or storming (trains ignoring).
*Evidence:* three pre-measurements re-measured on the real machine (`loginctl show-user … Linger=no`; `GetNameOwner
org.freedesktop.Notifications` → `NameHasNoOwner` with the session bus present; `/proc/self/cgroup` = `/init.scope`
for a `setsid` child, `KillUserProcesses=no`); the away channel driven end-to-end against a real HTTP sink from a real
detached daemon; the restart-no-duplicate path driven at the CLI boundary; `notify-send` observed failing with
`ServiceUnknown`; the cockpit rendered in headless Chrome. Fixture tests in `scripts/test_bus.py` (gate suite 181 →
199). Depends on D93/D94/D101/D111/D116; reuses D80/D95/D97/D105/D108/D109/D113/D114/D119. →
`03`/`05`/`07`/`shared/schemas.md`/`commands/start.md`/`scripts/bus.py`/`scripts/test_bus.py`/`11`.

## D121 — The public-facing repo identity is a recognized gap: owned now, work scheduled for Phase 4; the one-repo-vs-two fork stays OPEN **[DECIDED — scoping + ownership; the fork it left OPEN is now CLOSED by D125 (ONE transparent repo), and the Phase-4 work it scheduled is DONE (D125) — this entry is the ownership record, D125 the resolution]**
The end goal is a **public repo** others install and integrate (`00`), but the repo today is a dense *construction
record*: the numbered docs `00–11`, the `D<N>` vocabulary, and internal codenames ("the drain", "the notifier",
"waves", "away becomes triggerable") are design scaffolding, not a product front door. The only public-facing
surface is a spec-navigation `README.md` that even hardcodes the maintainer's absolute local path as "Home" — there
is no getting-started, no separation of construction-record from shipped product, and the skill `description:` fields
(the one internal vocabulary that ships *inside* the package) still carry design terms.

**The call:** *own the concern, defer the work.* The concern gets a home now — an open-question entry (`07`) and a
Phase-4 cross-cutting roadmap item (`11`) — so it stops floating; the *work* rides **Phase 4** (the last build phase
before release). That work is: (1) decide the **one-repo-vs-two fork**; (2) write a **product front-door README +
getting-started**; (3) reframe `00–11`/`08` as explicitly-labeled construction-record provenance; (4) a
**user-language pass over the skill `description:` fields**. The fork's two arms — a **transparent monorepo** (publish
as-is, design docs + decision log included; the reasoning trail is a distinctive asset, but the front door must
redirect "use it" away from `08`) vs a **distilled package** (publish only the package + clean docs, keeping the
spec/log as `docs/design/` or a private construction record; clean surface, but a sync seam and the "shows its work"
credibility is lost). **The fork is left OPEN** (`07`) — the maintainer's lean is the transparent monorepo (one
source of truth, no sync seam), but it is not closed here.

*Why defer:* onboarding/narrative prose written against a still-moving Phase-3 product churns and rots — you write
the front door once the thing behind it stops moving. The one exception carved out: keep skill `description:` fields
honest in user language *as they are touched*, since those ship inside the package regardless of timing.

*Rejected:* writing the README/onboarding now (churns against a moving target); leaving the concern unowned or
folding it into "Packaging/distribution" (it is broader than plugin mechanics — a distinct front-door/narrative
deliverable, and burying it is how it stays an orphan); deciding the fork now (premature — the right call depends on
how the packaged surface actually looks at Phase 4); two permanently hand-maintained repos (the drift the whole
project exists to avoid).

*Evidence:* `README.md` is titled "Dev-Workflow Spec — working draft" and indexes the spec for a maintainer, not a
consumer (it hardcodes a local absolute path as "Home"); `07` already tracks the *project-state view* (a navigation
surface + self-hosting prereq) and the *framework version-update skill* (keeping installed copies fresh) but had
**no** entry for the front-door/identity gap; the skill descriptions carry design vocabulary today. Relates to the
project-state view and self-hosting; revisited at Phase 4. → `00`/`07`/`11`.

## D122 — The remote socket built: a structural two-socket split, and four points the design didn't have — the token never on the surface it gates, stable-not-per-boot coordinates, a structural (not heuristic) credential boundary, and a load-bearing public host **[DECIDED + BUILT — Phase-3 increment 5; realizes D112's two-socket split; corrects D112/schemas' per-boot framing and the meta-tag-token reading; MEASURED on a real detached daemon]**
Increment 5 makes away **actionable** — act on a checkpoint from a phone. The split is buildable exactly as D112
framed it — two `ThreadingHTTPServer`s in one process, each tagged at bind with a `SocketPolicy` the handler reads
via `self.server.policy` (a structural per-server boundary, never a per-request Host guess — the header a proxy
controls). Socket B is unchanged (loopback, full surface, meta-tag token); Socket A binds only when `config.remote`
declares a transport. Building sharpened **four** points, three re-measured before the build and one surfaced by it:
- **(1) The remote token is never served in the remote page.** The naive reading of the meta-tag bootstrap — inject
  `remote_token` into A's page as B injects its own — **nullifies the second factor**: D112 wants the token so that
  "a misconfigured Access does not *instantly* expose the surface", but a token *in the page* is handed to anyone who
  reaches A in one GET. So A's page carries **no** token; it bootstraps from the pairing **fragment** → `localStorage`
  (loopback origin and A origin are different origins, so their stores never cross). An attacker past a misconfigured
  proxy but without the paired token lands on a token-less dead-end and reads nothing.
- **(2) The remote coordinates are stable, not per-boot.** The loopback `port`/`token` are minted fresh each boot —
  fine, because `/start` re-discovers them via `bus.json` every session. The remote pair **cannot** work that way: a
  phone pairs once and the operator points a tunnel once, so a per-boot `remote_token` goes stale on **every restart**
  — routine on WSL, the platform increment 4 bent over backwards to keep the away channel alive on. So `remote_token`
  is **persisted** (`.workflow/remote_token`, 0600-verified, minted once, delete-to-rotate) and `remote_port` is
  **config-declared and fixed**; `bus.json` echoes both for discovery but sources them from durable state.
- **(3) The credential boundary is structural, not the `_is_sensitive` heuristic.** Using the "shallow and permissive"
  `_is_sensitive` as the A/B gate rebuilds the exact anti-pattern D112 outlaws — a boundary that **false-negatives
  silently**, except the silent failure is now a live key crossing Cloudflare's plaintext edge. The gate is the crisp
  **presence of a `returns`/`tasks` payload** (a bare opinion verdict has neither); `_is_sensitive` keeps its jobs
  (file-mode tightening, the shred prompt) but is never the gate. On `access` a payload verdict is `403`; on
  `tailscale` (E2E) it is admitted — the one carve-out.
- **(4) A's Host-allowlist must add the declared public host.** Left as loopback-only, a proxy that **forwards** the
  original Host has **all** its traffic `403`'d. So A's allowlist = loopback names ∪ the `public_url` host, which makes
  `config.remote.public_url` **load-bearing for the transport itself**, not merely the pairing link. The port topology
  stays the boundary; the Host check is anti-DNS-rebinding defense-in-depth.
- **A's positive POST allowlist is verdict-only.** `release` / `control` / `intake` / `/shutdown` / `/api/pairing`
  all `404` on A (the surface simply does not have them); the pairing secret is served only on loopback, so the page
  that hands out the token can never itself be the remote surface.
- **Pairing ships copy-paste; the QR is a scoped fast-follow.** No stdlib QR encoder, `qrcode`/`segno` absent, the
  page is `script-src 'self'` (no CDN) — so a QR means hand-rolling Reed-Solomon+masking, and the decisive fact is
  that an unscannable QR passes every structural test and only fails against a real phone camera (unverifiable
  in-harness — the surface this project refuses to accrue). A tapped `#t=` link pairs with zero typing; pairing is
  one-time. The not-yet-built demo's `/demo/*` route joins A's static class in Phase 4, unbuilt here.
*Rejected:* the meta-tag token on A (defeats the second factor — the finding above); per-boot remote coordinates
(breaks pairing + the tunnel every WSL restart); `_is_sensitive` as the credential gate (a silent false-negative =
a key on a plaintext edge); a loopback-only Host-allowlist on A (403s a forwarded-Host proxy entirely); `intake`/
`control` on A (kept off the reduced surface — fail-closed for MVP, a one-line widening later); building the QR now
(unverifiable in-harness; copy-paste + a tapped fragment link is a complete one-time pairing).
*Evidence:* driven on a real detached daemon — the remote page carries neither token; each socket accepts only its
own token (loopback token → `401` on A, remote token → `401` on B); `release`/`control`/`intake`/`/shutdown` → `404`
on A; an opinion verdict → `202`, a returns-bearing verdict → `403` **and the secret never reached the inbox**;
`/api/pairing` → `404` on A / `200` on B with a well-formed fragment link; a forged Host → `403`, the public host →
`200`. 36 new fixture tests (bus suite 77 → 113; full suite 199 → 235), all green; the leak gate holds (no `D<N>`
slugs in the shipped `bus.py`). D112 (the split this realizes) · D95 (token discipline, never-reuse) · D90 (verdict-
as-authoritative-prompt, the bar) · D97 (a missing credential can't be skipped) · D100 (stdlib-only → no QR lib, no
JWT) · D116 (the meta-tag bootstrap this scopes to loopback) · D119 (the POST validation this partitions per socket).
→ `03`/`05`/`shared/schemas.md`/`11`.

## D123 — The relaunch-runner built: liveness had to be PUBLISHED (a `/proc` scan is unsound), the launcher holds it, and a REAL drive found an untrusted `claude` ignores the allowlist and stalls **[DECIDED + BUILT — Phase-3 increment 6, the LAST of the console+bus; realizes D113's runner + closes D120's deferred thrash arm; MEASURED end-to-end on a real model]**
Increment 6 makes away **completing** — a phone verdict now RESUMES the loop autonomously instead of queuing, closing
the away channel end-to-end (alerted D111 → act D112 → lands durably D108 → **the runner resumes** D123). The runner is
a **job on the D94 daemon** (`config.runner.enabled`): when `drain.py list` shows a pending `verdict`/`intake` and no
orchestrator holds `orchestrator.lock`, it spawns a fresh `claude -p` that cold-starts and **drains** (D117) the durable
verdict. Four design calls were taken up front (all as recommended); the build then measured the mechanism, as every
increment has.
- **(1) Liveness is a PUBLISHED marker — the crux, and the obvious mechanism is unsound.** The runner must see BOTH a
  runner-launched AND a human-`/start`-ed orchestrator, or "forgot the runner was on" becomes a silent state-clobber
  (D113's own stated failure). There is **no ambient signal**: a `/proc` scan for a live `claude` was **measured
  unsound** — Claude Code runs a constellation of claude-named processes (`claude daemon`, `bg-pty-host`, `bg-spare`,
  a versioned session process whose `comm` is the *version string*) sharing the repo cwd, so it cannot separate a
  driving orchestrator from a helper or a casual session; and a `state.json` mtime lies both ways (stale-recent on a
  hung loop, absent on an idle-parked one). So liveness is an `flock` a launch **explicitly holds** — a human via the
  shipped **`loop.sh`** launcher (`exec flock -n orchestrator.lock claude …`; MEASURED to survive the `exec` and hold
  for the session, the lock file carrying claude's real pid), a runner-launched `claude -p` via `flock -n` itself. The
  runner probes the lock; held ⇒ back off. This is the orchestrator-side scope the design predicted — a launcher +
  `/start`/CLAUDE.md run-constraint, not just a daemon job.
- **(2) The runner's own `flock -n` spawn IS the double-launch latch** — measured: a second acquire while a launch is
  live is BLOCKED, so even a human starting in the probe→spawn window aborts rather than doubling. No separate flag. The
  kernel drops the lock on death (measured on `kill -9`), so it never goes stale like a pidfile.
- **(3) The launch, and the permission floor.** `flock -n orchestrator.lock claude -p "<resume prompt>"`, detached
  (`setsid`, DEVNULL), cwd = launch root, user's own `~/.claude` auth. **Never `--dangerously-skip-permissions`:**
  `guard.sh` (D110) fires even under bypass, but bypass *skips the settings `ask` floor* (deploy/network/`gh pr`) — a
  runner-launched loop must never fire those unattended. So it inherits `settings.json` exactly like the interactive
  loop. The resume prompt is **dedicated** (not `/start`, which re-scaffolds), and forces the drain rather than trusting
  the "drive only if an active run" guard. **Driven end-to-end on a real model:** a runner-spawned `claude -p` ran
  `drain.py list` → applied the verdict → `drain.py record`, advancing `consumed_through` from null to the id (rc 0).
- **(4) The trust finding — wrong only when RUN.** A `claude -p` in a workspace Claude Code has not trusted **ignores
  `settings.json`'s allowlist** ("Ignoring N permissions.allow entries … not trusted") and **stalls** — the loop cannot
  run its own tools. No static read shows this. In practice `/start`'s trust dialog establishes trust, so a real project
  is fine, but a `runner.enabled` project never trusted would spawn inert sessions. This drove a mechanism the
  crash-only design lacked: a hung launch never *exits*, so it would pin the runner in-flight forever. **The call:** a
  **stall-timeout** kills a relaunch that hasn't drained within a window and scores it no-progress (a *drained* launch is
  productively working and runs freely); and untrusted-workspace is surfaced in `status` as a **warning, never a spawn
  gate** — a misread must not silently disable the runner.
- **(5) Trigger = applicable work only, and crash-safety closes D120's arm.** Spawn only for a pending `verdict`/`intake`
  (advance a dead/parked loop) via `drain.py list` — never a lone `control` (nothing to drive) nor a `release`
  (loopback-only ⇒ a human was present to approve it). A relaunch that neither advances the watermark nor drains backs
  off (doubling) and, after a cap, **hard-stops and fires a distinct `loop-stall` away alert** — this IS D120's deferred
  event-2 thrash/crash arm, which waited for exactly this liveness signal; the two-event taxonomy is now whole.
- **(6) WSL, carried not solved.** The runner is the overnight mechanism, but the hosting daemon dies with the last
  terminal unless `.wslconfig` sets `vmIdleTimeout=-1` (the D120 wall) — surfaced in `status`, never implied.
*Rejected:* a `/proc` scan for a live `claude` (measured unsound — CC's own helper-process constellation); a
`state.json` mtime heartbeat (idle-parked looks dead, hung looks live); a pidfile (PID reuse — D94/D109); tracking only
the runner's own launched PID (misses the human `/start`); `--dangerously-skip-permissions` for the launch (bypasses the
`ask` floor — catastrophic autonomy overreach); `release` in the trigger (fires outward side-effects from a headless
loop with nobody present, past D110/D112's boundary); an **up-front trust *gate*** that blocks the spawn (a misread
would silently disable the runner — a warning is the ceiling, the stall-timeout the real backstop); crash-only relaunch
handling with no stall-timeout (an inert/hung launch pins the runner in-flight forever); `/start` acquiring the lock for
the session (a session is not a process that naturally holds an fd, and `/start` runs *inside* an already-live claude —
it cannot retro-acquire). *Residual (accepted, D109-consistent):* a human who enables the runner but starts **bare
`claude`** is invisible to it — documented, not fenced.
*Evidence:* `/proc` enumerated against a real running `claude` (the helper constellation); `loop.sh` driven (flock
survives `exec`, second launcher refused, kernel-drops on `kill -9`); the runner's own acquire measured BLOCKED while a
launch is live; a detached DEVNULL `claude -p` measured to run + exit (rc 0); the resume path driven end-to-end (a
runner-spawned real `claude` drained a durable verdict, watermark advanced null→id, rc 0, ~15s); the untrusted-workspace
stall observed in a real transcript, driving the stall-timeout. 13 new fixture tests in `scripts/test_bus.py` (disabled
/ lone-control / held-lock / verdict→drain / intake / in-flight-no-double / crash-loop→hard-stop→alert /
stall-timeout-kills-inert / progress-resets / readiness / idle-vote), all green; full suite green (one pre-existing
notifier *timing* test flakes under the longer runtime, passes in isolation — not this change). Depends on
D90/D92/D94/D108/D109/D111/D112/D113/D117/D120; reuses D80/D95/D100/D110/D114/D115/D119. →
`01`/`03`/`05`/`07`/`shared/schemas.md`/`templates/orchestrator-CLAUDE.md`/`commands/start.md`/`scripts/bus.py`/`scripts/loop.sh`/`scripts/test_bus.py`/`11`.

## D124 — The demo serving built: the sandbox CSP isolates but does not discipline, `os.replace` on 9p tears availability not content, and the demo checkpoint rides the verdict machine unchanged **[DECIDED + BUILT — Phase-4 (build the demo), the first of its two halves; realizes D102/D103/D104 as built and sharpens D102/D104; folds the refine-count home, the prune owner, and the console embed; MEASURED in a real browser + a real model + on the 9p mount, not reasoned]**
Phase 4 opens by building what D102–D104 designed: the D94 daemon now serves `/demo/<id>/` so a `create-demo` bundle renders under isolation beside the verdict form. The serving is **over-determined by the A/B substrate** (a demo is more files on disk — D93), so the build was mostly wiring; what it *found* by driving is the value.
- **The build.** `/demo/<id>/` is served on **both sockets** (loopback B + remote A — the "static demo" A's reduced surface already carried, D112) under a **per-path** `Content-Security-Policy: sandbox allow-scripts allow-forms`; token-free (the D102 static class — a browser cannot header an iframe/document navigation), Host-gated, and guarded by a **realpath + `startswith(base+sep)`** check anchored at the real `demos/` root (climbs to `bus.json`/the token 404, measured over a raw socket). Explicit MIME map + `nosniff` + `no-store`. The console keeps its own strict `script-src 'self'` — **two per-path CSPs from one daemon** — and gains **`frame-src 'self'`** so it can EMBED the demo in a `sandbox="allow-scripts allow-forms"` iframe (never `allow-same-origin`) beside the verdict form. `demos/` stays on the repo mount (`no-pin`), not the relocated runtime half.
- **(1) The `sandbox` directive enforces ISOLATION, not the format discipline — D102 conflated the two.** Driven in real headless Chrome: at **top-level navigation** the served demo gets an **opaque origin from the header alone** (`window.origin === "null"`), `localStorage`/`document.cookie` throw, and `fetch` of the token-gated `/api/*` and of the token-bearing console page both fail — it cannot read the console. **Framed by the console** (proven via a minimal CDP driver) it is equally sealed: the parent's `iframe.contentDocument` is null and `contentWindow.localStorage`/`location.href` throw. **But `eval`, `new Function`, and external hosts all RUN under the directive** (measured — no `script-src`/`connect-src` to block them). So D102's "inline scripts run without `'unsafe-eval'`" is misleading and the "self-contained / no-eval / no-external" invariants are **not** CSP-enforced — they are `create-demo` authoring discipline, now backed by a shipped mechanical floor **`scripts/check_demo_bundle.py`** (external hosts, protocol-relative URLs, `eval`/`new Function`, `text/babel`/`@babel`, bundler deps; run before the park, fix-and-regenerate on a hit). A **real-model `create-demo` drive** confirmed a competent model produces a compliant single-file bundle that renders under the CSP with zero violations; the lint is the deterministic backstop for a slip, which would otherwise render locally and blank over the tunnel.
- **(2) `os.replace` under serve on the 9p repo mount tears AVAILABILITY, not content — D104's "self-heals" holds, its mechanism was wrong.** Measured (400 in-place refines × 6 concurrent readers): **zero torn/truncated reads** (the rename is content-atomic) and `no-store` on every response (no stale cache). BUT a concurrent `open` of the target transiently fails with `ENODATA` during the rename — which the handler had surfaced as a 404. So the demo does self-heal on the next poll, but via a transient open failure, not a torn render. Fix: the handler distinguishes a genuinely-absent file (`ENOENT`/`FileNotFoundError` → fast 404) from the transient error (brief retry), making a refine invisible to a viewer; at realistic cadence the residual is ~1 blip in 60 reads at 50 ms polling (≈never at the real 2.5 s poll), self-healing.
- **(3) The refine count and the prune had no owner; both are now pinned (D80).** The D103 cap spans park → resume → a possibly-relaunched fresh session, and the loop is stateless glue (D92/D123 — nothing accumulates in context), so the count lives on disk at **`.workflow/demos/<id>/.refine.json`** — inside the bundle dir (a **dotfile the server refuses to serve**, a new general hygiene rule), whose lifetime is exactly the refine loop. The bundle is **pruned on TERMINAL resolve by the verdict-apply path** (approve → lock the spec / reject → `discuss`), **kept on `changes`** (still refining); retention's new **`prune_demos`** (a demo dir with no open `parked/` record is a resolved leftover — the same "delete only when provably done" discipline as the item prune) is the **straggler backstop** for a crash between resolve and delete.
- **The demo checkpoint rides the whole Phase-3 machine unchanged** (driven): it parks at **intake stage with no worktree** (D96 pre-build park), the daemon's notifier **alerts** on it (D120, kind-agnostic), a **demo verdict is an opinion** that rides the remote **Socket A** (D112), and the drain (D117) + relaunch-runner (D123) pick it up as a **plain `verdict`** — no demo-specific path. `templates/loop.md`'s demo edge was corrected (it had conflated *changes* and *reject*): **approve → lock the spec + prune · changes → `create-demo` (keep the bundle + counter) · reject → `discuss` (prune)**.
*Rejected:* **hardening the demo CSP** to enforce the discipline (`script-src` under an opaque origin matches nothing, so `'self'` would block the bundle's own sibling `app.js` and the vendored htm+preact escape hatch — forcing single-file inline; the lint enforces the discipline without fighting the format); the **parked record or `config`** as the refine-count home (deleted-on-resolve / per-project — neither survives the item-scoped refine loop); **audit-prune-only** for the bundle (leaves served bytes across the resume — the terminal apply prunes promptly, retention only backstops); a **second server/port** for the demo (D102 — reinvents the daemon lifecycle, breaks the free remote surface).
*Evidence:* real-Chrome drives — top-level opaque-origin + `/api` unreachable, and a framed console that cannot reach in (via a stdlib CDP driver); a real-model `create-demo` drive (a self-contained Reading Queue bundle, independently scanned clean, rendered under the CSP with zero violations, screenshotted); the 9p `os.replace` measurement (0 torn over 400×6); +54 tests (`scripts/test_bus.py` demo/remote serving, `scripts/test_check_demo_bundle.py`, `scripts/test_retention_demos.py`), full suite green (302), all gates clean. Realizes D102/D103/D104; reuses D90/D92/D93/D94/D95/D96/D108/D112/D117/D120/D122/D123; single-source per D80/D114. → `04`/`05`/`09`/`shared/schemas.md`/`skills/create-demo`/`skills/checkpoint`/`commands/start.md`/`templates/loop.md`/`scripts/{bus.py,check_demo_bundle.py,retention.py}`/`11`.

## D125 — The public release surface: ONE transparent repo, a top-level `product/` plugin root, and `product/MANIFEST.json` as the authoritative ship boundary; the construction record reframed into `docs/design/` **[DECIDED + BUILT — Phase-4 second half; CLOSES the D121 one-repo-vs-two fork (`07`); realizes the D57 plugin-packaging item as built; MEASURED — validated + installed + release-built + gate-reproven, not reasoned]**
The end goal was always a public repo others install (`00`); D121 owned the identity gap but left the *one-repo-vs-two* fork OPEN and deferred the work, because onboarding prose written against a moving Phase-3 target churns. D124 built the demo — the last moving piece — so the reason to defer expired, and this slice executes the whole surface as a design + heavy-refactor pass.

**The call.** *One transparent repo*, restructured so a consumer sees a product and a contributor sees a cleanly-separated construction record:
- **`product/` is the plugin root** — everything that ships (`skills` · `agents` · `commands` · `hooks` · `shared` · `rules` · `templates` · the shipped scripts). Its **`.claude-plugin/plugin.json`** is minimal (`name` is the only required field; components are convention-discovered). The repo is **its own marketplace**: a root **`.claude-plugin/marketplace.json`** lists one plugin with **`source: ./product`** (the monorepo/subdir pattern), so `claude plugin marketplace add <repo>` + `claude plugin install dev-autonomous-workflow` works.
- **`product/MANIFEST.json` is the authoritative ship boundary (D80 single owner).** It draws the ship line ONCE — `ship` (published paths) · `exclude` (`**/test_*.py`) · `install` (the `{src,dest}` copy map) — and the three consumers **derive** from it: the **leak gate** scans the manifest's ship set (retiring its `dirs=()`), **`/start`** copies the `install` map from **`${CLAUDE_PLUGIN_ROOT}`** (retiring start.md's enumerated copy list — the one that had already silently missed `loop.sh`, then `check_demo_bundle.py`), and a new meta **`scripts/build-release.py`** emits a clean product-only tree. **Physical location is not the ship line — the manifest is**, which is exactly what lets the tests sit beside the code they import (`product/scripts/`) while the manifest `exclude`s them.
- **The construction record moves to `docs/design/`** — the numbered docs `00–11`, the decision log, `reviews/`. **Meta-only tooling stays at repo-root `scripts/`** (`check-no-spec-refs.sh` · `check-status-coherence.sh` · `check_enum_coherence.py` · `build-release.py`), all re-pointed at the moved owners. The **dual-use gates** (`check_contracts.py` + the coverage gates) live on the product side; the meta-repo just invokes them against itself (`check_contracts.py`'s defaults self-heal — `dirname(dirname(__file__))` is now `product/`).
- **Identity:** the product name stays **`dev-autonomous-workflow`**; "the disciplined builder" is its tagline. A **product front-door `README.md`** (what it is → install → getting-started → how it works → one link to `docs/design/`) replaces the maintainer spec-index and drops the hardcoded local "Home" path. The skill **`description:` fields** — the one internal vocabulary that ships — are scrubbed of construction-era terms (`wave` · `LLM-wiki` · `behavioural-core` · the D6 role-codenames `The Arbiter`/`Investigation worker` · `inception`).

*Why:* one repo kills the sync seam AND preserves the dogfooding / "shows its work" credibility — the construction record IS the workflow's own docs/decisions output; a hand-maintained twin re-introduces the exact drift this project exists to kill. The manifest-as-single-boundary kills the drift class that had already bitten twice (two hand lists, each of which silently missed a new shipped file).

*Rejected:* the **distilled-package twin** (a sync seam + lost dogfooding — D121's own rejected arm, now closed); a **second copy-list** beside the manifest (two owners = the drift; and plugin.json cannot express `/start`'s install destinations); **tests → a top-level `tests/`** (re-couples location to shipping and adds ~10 risky `sys.path` edits — the manifest `exclude` makes beside-code clean *and* lower-risk, and is what makes that option viable at all); **renaming the repo** to the product name (breaks the public URL + every clone); the assumed plugin schema (a `components{}` block + repo-root-only plugin — MEASURED false against the installed official marketplace: `plugin.json` needs only `name`, components are convention-discovered, and a marketplace `source` can be a repo subdir).

*Evidence — driven, not reasoned:* `claude plugin validate --strict` passes both manifests; a real `claude plugin marketplace add ./` + `install` discovered the full roster (17 skills + `/start` + 2 agents; **Hooks 0**, correctly — `guard.sh`/`pre-commit.sh` ride along for `/start` to copy, they are not plugin lifecycle hooks) and uninstalled clean; `build-release.py --check` emits a clean **44-file** product-only tree (no construction record, no tests); all five meta gates re-pointed and **each re-proven by revert-a-fix** (a `D<N>` ref in a shipped file, a wrong roster count, an owner enum value no consumer declares); the full **302-test** pytest suite green after the move. Driving found a real `build-release` defect a read would miss: a prior pytest run littered `__pycache__/*.pyc`, which `os.walk` swept into the release and which dodge the `test_*.py` exclude (a `.pyc` basename is not `*.py`) — fixed by pruning build cruft, the leak gate's grep hardened (`-I --exclude-dir=__pycache__`). **`/start`'s full bootstrap runtime stays unexercised** (the pre-existing residual), but its source-resolution mechanism is now correct: the plugin docs confirm `${CLAUDE_PLUGIN_ROOT}` substitutes in command content. Closes the D121 fork; realizes the D57 plugin-packaging item as built (the version-update/migration skill remains its follow-on). Reuses D6/D57/D80/D100/D114/D121/D124. → `00`/`07`/`11` + `README.md`/`CLAUDE.md` + `product/MANIFEST.json`/`product/.claude-plugin/plugin.json`/`.claude-plugin/marketplace.json` + the re-pointed meta gates.

## D126 — Pre-test hardening is a real slice, not a residual: "release-ready" was build-completeness, the install→`/start`→loop runtime is unexercised end-to-end, and a pre-first-run audit found three latent bugs reading confirmed **[DECIDED — scoping + gap audit → Phase 5; reopens D125's "release-ready" at the RUNTIME level (build-complete ≠ runtime-validated); promotes `07`'s "standing residual" to a sequenced slice; VERIFIED against the shipped artifacts, not a summary]**
D125 declared Phase 4 build-complete and the MVP "release-ready." The maintainer, moving to actually *test the product*, pushed the right question: what looks done but isn't *runnable*? "Release-ready" was true as a **build-completeness** claim (every component is authored + the daemon/gates are driven) and misleading as a **runtime** one: the whole **install → `/start` bootstrap → loop** path has **never been driven end-to-end even once** — every one of the six Phase-3 increments was driven in *isolation* (fixtures, real models on single pieces), and the only prior loop validation (D52) ran a pre-D66 throwaway that *simulated* dispatch.

**The audit.** Two independent sweeps — one auditing what the docs *admit* is undone, one auditing the *shipped code* without trusting the doc labels (the standing lesson: claims drift from what runs). The code sweep earned its keep: it surfaced three miscouplings the docs never state, and **the two load-bearing ones were re-verified against the files, not the summary** (this project's own rule): (1) `find product -iname '*checks.sh*'` → nothing ships to produce or scaffold `.workflow/checks.sh` — it exists only as *references*; (2) `guard.sh:89`/`pre-commit.sh:33` hard-code `json.load(open(".workflow/state.json"))` while `bus.py:180` resolves `state.json` under the `runtime.json`-relocated root and `start.md:53` puts `state.json` in the set relocated off a 9p mount — so the `json.load` throws, is swallowed by `2>/dev/null || true`, and **verify-before-commit silently no-ops on `/mnt/c`.**

**The call — capture Phase 5 (pre-test hardening) as the next slice**, tiered by first-run break-risk and **sequenced greenfield-on-a-Linux-native-path → brownfield-on-`/mnt/c`** (the maintainer's two forks: *both, greenfield first* + *native path* — the native-path first test collapses the entire FS-relocation family, incl. the `state.json` bug, out of run #1). The full tiered worklist lives in `11`'s `### Phase 5`; its spine:
- **Wave-1 blockers (greenfield/native):** `checks.sh` has **no generator/template** (LLM-freehand, gates every commit) · `verify-verdict` is an **unwritten hook↔artifact contract** (the hook greps a file+token `verify`/`schemas.md` never pin) · `/start` ships **no manual workspace-trust path** (the WSL dialog doesn't render → the loop stalls on the first prompt).
- **Wave-1 drive-and-fix:** rules specialization + enforcer wiring · `codemap.sh` gen + the **greenfield import-root bug** (`codemap.py` names modules relative to CWD, `/start` runs it from the launch root → greenfield Python edges silently unresolved) · **real** orchestrator→subagent dispatch (`research`/`setup-guide`, only ever simulated) + outbox firing · `handoff.md` session-end crash-durability (a text-tool model can't express an atomic rename).
- **Wave-2 (brownfield/`/mnt/c`):** the `state.json` hook-path **bug** (resolve via `runtime.json` like `bus.py`) · the unexercised FS-relocation step · brownfield `ingest` (codemap-at-scale → spec reconstruction → reconciliation checkpoint).
- **Opportunistic bugs a first run misses:** `align` invokes meta-repo-only gates absent from the install manifest · stale `start.md` "Expand later" prose (the console write-path shipped in increment 3).

*Why:* the recurring evidence — increments 1–6 each surfaced a *wrong mechanism* only when driven on the real filesystem with a real model; a build-complete engine that has never run end-to-end is exactly where that class of bug lives. Three of these are **latent defects reading found**, categorically worse than the maintainer's prompting example (the living code-map = "designed, not built"): they are shipped code that breaks or *silently disables a safety gate* on first contact. And "release-ready," left unqualified, is the drift this project exists to kill.

*Rejected:* **"just drive it and fix as it breaks"** (three items are verified bugs — fix them as bugs *before* the drive, so the drive tests the loop, not the scaffolding) · **a flat backlog dump** (the greenfield-native→brownfield-`/mnt/c` *ordering* is load-bearing — it's what removes the FS family from run #1; a flat list loses that) · **deleting the "Phase 4 COMPLETE / release-ready" claim** (the *features* are built — qualify build-complete-vs-runtime-validated, don't erase) · **a new status owner** (Phase 5 owns the *sequencing*; each item's status stays in its space, like Phase 2's agenda — no second copy).

*Evidence:* two sweeps (docs-status + shipped-code); the two load-bearing claims re-verified against the artifacts as above; `git status` clean on `9549ac3`, 302 pytest green — i.e. the gap is *runtime*, not *build*. No new code this slice — capture only. Reopens D125's readiness framing; promotes the `07` "standing residual" (`/start` bootstrap unexercised) + the "Validation gaps" (real dispatch, `@import`-survives-`/compact`) into the tracked Phase 5. Reuses D52/D58/D66/D111/D113/D115/D117/D125. → `11` (`### Phase 5` + reframed next-slice/Phase-4/one-liner) + `07` (residuals → slice).

## D127 — Phase-5 Wave-1 built + driven: the three first-run blockers shipped, and driving greenfield-on-native found+fixed two more wrong-mechanism bugs (one NOT on the audit list) **[DECIDED + BUILT — Phase-5 Wave-1 (greenfield/native); realizes D126's three blockers + the codemap drive-fix; refines D67 (checks.sh) and D58/D113 (trust); MEASURED end-to-end on a real greenfield bootstrap at a native `~` path, not reasoned]**
D126 scoped Phase 5 and named three first-run blockers + a codemap import-root bug. This slice **built the three blockers** and **drove the greenfield `/start` bootstrap on a real native-path repo (`~/p5-test`)** — and driving earned its keep exactly as the standing lesson predicts: it **confirmed the predicted bug and found a second one the audit missed**, both silent-gate defeats surfaced only by running.

**The build — three blockers:**
- **`checks.sh` → a shipped FIXED runner + a generated data file** (refines **D67**). `templates/checks.sh` ships fixed and pytest-tested and is copied **verbatim** to `.workflow/checks.sh`; its only per-project input is `.workflow/checks.env`, a `KEY="value"` **data** file `/start` writes (empty ⇒ skip). The invariant, error-prone half — the `--fix`/`--check` dispatch, the loop over each open item's `promises.json` running the three stack-agnostic coverage gates, the exit aggregation — is **never LLM-freehand** again. `FMT_FIX`/`LINT_FIX` are command **prefixes** (the runner appends the item's staged files in `--fix`, honouring `commit`'s staged-scope rule); `FMT_CHECK`/`LINT`/`TYPECHECK`/`TEST` run repo-wide in `--check`. This mirrors the `codemap.sh` shipped-engine/thin-wrapper split, so it's coherent with the design rather than a new pattern.
- **`verify-verdict` contract pinned both sides + hooks flipped FAIL-CLOSED.** `shared/schemas.md` + `verify/SKILL.md` now mandate `.workflow/items/<id>/verify-verdict.md` (never `.json`) whose **first line is exactly `pass: true|false`**. `guard.sh` + `pre-commit.sh` proceed **only** on a well-formed `pass: true`; a missing file, a wrong extension, or a reworded token **blocks**. This closes a fail-**OPEN** hole measured live: the old grep-for-`false` waved a reworded fail (`Result: FAIL`) straight through.
- **Manual workspace-trust path.** `/start` writes `projects["<abs path>"].hasTrustDialogAccepted: true` into `~/.claude.json` (merge-preserving, idempotent, atomic `tmp`+`replace`, bails safe on an unparseable file). Necessary because the WSL trust dialog frequently does not render, and an untrusted workspace makes `claude -p` **ignore `settings.json`'s allowlist and stall** (the **D113** runner "Trust precondition (MEASURED)"). The disciplined-autonomy default: `/start` establishes trust itself (the equivalent of clicking *trust this folder*) and surfaces it, rather than printing a command for the human.

**The drive found two wrong-mechanism bugs, both verified live:**
- **`codemap.py` greenfield import-root** (the one D126 predicted) — **CONFIRMED live** (`app.py` imports `pkg.util`; the module was named `project.pkg.util` relative to cwd → **0 edges**, the whole greenfield Python graph silently empty). **Fixed:** name Python modules relative to the **scan root**, not cwd; a no-op for brownfield (`root="."`, all prior tests unchanged). Node paths stay repo-relative (graph.json contract unchanged). Only `PythonArm` was affected — Go/Java/C#/JS resolve via manifests/path-suffix and are position-independent. 2 regression tests exercise the `ROOT≠cwd` case the old harness never did.
- **`checks.sh` `cd`-leak** (**NEW — not on the audit list**) — a natural `TEST="cd project && pytest"` ran the `cd` in the runner's **own** shell via `eval`, moving its CWD so the coverage-gate loop (`.workflow/items/*/promises.json`, CWD-relative) then found zero items and **silently skipped every plan-coverage gate**. A bad `promises.json` returned exit 0. **Fixed:** run each stack command in a **subshell**. My own unit tests missed it (they used `cd`-free stubs `true`/`false`); only driving a real `cd`-ing stack command surfaced it — the exact "right about the gap, wrong about the mechanism" pattern, this time in code I had just written.

**Three sequencing findings the drive surfaced (captured, with resolutions):**
- **Greenfield can't detect a stack at `/start`.** A faithful greenfield runs on an *empty* `project/`; `tech_stack` doesn't exist until `discuss`/`decision-engineer`. So the bootstrap `checks.env` is **coverage-gates-only**, and stack-enforcer wiring (the `checks.env` commands **and** the `rules/*.md` `enforced by:` tag rewrite) is **deferred to `tech_stack` lock**. `start.md` §5's "detect the stack" holds at bootstrap only for **brownfield**.
- **Stack commands must be scoped to `project_root`.** `ruff check .` from the launch root would lint the workflow's own installed `.claude/scripts` + `.workflow/`; in greenfield it must be `ruff check project`. `start.md` should say so when it writes `checks.env`.
- **`/start`'s install does not honour the manifest `exclude`.** The `install` copytree of `scripts/codemap/` drags `test_codemap.py` + `__pycache__` into the target's `.claude/scripts/` (the release build filters `**/test_*.py`; the install step doesn't). Harmless but drift — the install step should apply `exclude`.

**Verified end-to-end on the real bootstrap:** scaffold commits clean through the real `.git/hooks/pre-commit`; a good item passes; the **teeth fire** (a decision-mapped-to-no-step `promises.json` blocks the commit); `verify-verdict` pass→allow / fail→block / malformed→block through the real hook (which also proved it validates the **staged** diff via the `--keep-index` stash); `codemap.sh` resolves edges on real greenfield code. **287 pytest green**; `check-status-coherence` + `check-no-spec-refs` green.

*Why:* the Phase-5 thesis — a build-complete engine that never ran end-to-end is where wrong-mechanism bugs live — held again, and the `cd`-leak is the sharpest instance yet: a *silent plan-coverage-gate defeat* triggered by a perfectly ordinary stack command, invisible to reading and to `cd`-free unit tests. Shipping the runner **fixed + tested** (writes data, never code) is the strongest form of D126's mandate.

*Rejected:* **pure stack-detecting generator for `checks.sh`** (freehand each bootstrap — what Phase 5 exists to kill) and **template-with-slots** (still `/start`-authored) — chose the **fixed-runner + data-file** (`/start` writes data, never code). **`verify-verdict.json` + python-parse** (bigger blast radius) — chose **`.md` + pinned token + fail-closed flip** (smallest change, closes the hole regardless of phrasing). **`/start` prints the trust command for the human** — chose **`/start` writes the key itself** (disciplined-autonomy default). **`os.chdir(root)` for the codemap fix** (would flip node paths to project-relative, breaking graph.json's repo-relative node-path contract) — chose **root-relative module naming only**.

*Evidence:* `~/p5-test` greenfield bootstrap on a native `~` path; codemap `0→1` edge after the fix; `checks.sh` teeth `exit 0 → exit 1` after the subshell fix (with the coverage loop now demonstrably reaching the item); the guard/pre-commit block matrix (pass/fail/missing/reworded/`.json`/no-item); 287 pytest green; both meta gates green. Refines **D67** ("generated per-stack `checks.sh`" → "installed fixed; per-stack surface is a data file"), resolving the `07`/`10`/`11` "per-stack `checks.sh` generator remaining sliver." Reuses **D58/D113** (trust), **D30/D43/D66** (coverage gates), **D89** (bash-glue interpreter — still open), **D115** (native path removes the FS family from run #1), **D126** (this slice's scope). **Remaining Wave-1 (next slice):** real orchestrator→subagent dispatch (`research`/`setup-guide`) + one full **real-model** loop iteration — to be driven next session via `claude -p`; `handoff.md` session-end **crash-durability** — fix shape still a **design question** (inclination: a shipped publisher helper the orchestrator calls, `drain.py`-style, git as the recovery backstop). → `11` (`### Phase 5` Wave-1 statuses + Phase-4/one-liner framing), `07` (checks.sh sliver → resolved; handoff-durability stays open), `10` (roster note), `05` (layout: `checks.sh` fixed + `checks.env`), `product/` (built).
