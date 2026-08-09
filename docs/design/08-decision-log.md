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

## D128 — Phase-5 Wave-1 REMAINING driven: the first real end-to-end greenfield loop with real orchestrator→subagent dispatch; three wrong-mechanism findings; handoff-durability resolved (harness Write/Edit are already atomic) **[DECIDED + DRIVEN — Phase-5 Wave-1 REMAINING; closes D126/D127's two remaining items; resolves the D117 handoff-durability question + `07`'s "real dispatch validation"; three findings CAPTURED for a next-session fix slice (maintainer's call); MEASURED by driving a real `claude` on the installed plugin, not reasoned]**
D127 built + drove Wave-1's blockers; the two REMAINING items were **real orchestrator→subagent dispatch + one full real-model loop iteration** (every prior loop *simulated* dispatch — D52) and **`handoff.md` crash-durability**. This slice drove both against a real `claude` (v2.1.214) running the **installed plugin** on a fresh native-path greenfield (`~/p5-test`, a `slugify` one-function library), and — exactly as the standing lesson predicts — the drive found three wrong-mechanism bugs no reading surfaced.

**The full loop ran with real dispatch, and it works.** Driven stage by stage as `claude -p` sessions (each a real model; a human/console stood in at checkpoints): `/start` greenfield → `discuss` (commitment-tagged spec + debt tickets + `TBD → decision-engineer` pointers) → `planner:decompose` → `prioritize` (dependency-gated wave-of-one) → `planner:plan-one` → `decision-engineer` → **real `research` subagent via Task** (`dev-autonomous-workflow:research`, 34.5k tokens; the orchestrator's own context stayed clean — hub-and-spoke holds with a real model) → `execute` (**codemap resolved the real `test → module` import edge** — the D127 import-root fix works on greenfield; 76 tests pass; build green) → `verify` (**`verify-verdict.md` first line exactly `pass: true`** — the D127 contract holds) → `document` → `commit` (fix→check flow, the pre-commit backstop with real teeth, bookkeeping-before-commit) → setup checkpoint → **real `setup-guide` subagent via Task** (verified deep-links against the live PyPI UI, caught that the dist name `slugify` is taken) → **outbox → console `release` → guard push, end to end** (`bus.py` daemon up, POST API works, the push queued to `.workflow/outbox/` on a *feature* branch not protected `main`, waited for a release, then fired through `guard.sh` and landed on the remote — nothing pushed until released, no stall). *Both required subagent dispatches (`research` + `setup-guide`) confirmed via real Task dispatch — the agents resolve only **namespaced** (`dev-autonomous-workflow:<name>`), not bare.*

**Three findings — captured now, to be discussed + fixed next session (maintainer's call), not built this slice:**
- **F1 — `/start` cannot complete non-interactively; the `.claude/` install hard-blocks to a hollow scaffold.** The manifest install writes into `.claude/scripts/` + `.claude/hooks/`, which Claude Code guards as sensitive **above** the settings allowlist (trust + `Write`/`Bash` allow do **not** waive it). In `claude -p` there is no grant path, so all 13 install entries + the daemon are silently skipped — **yet `.workflow/` still commits**, so a re-run reports "already initialised" while `guard.sh`, the coverage gates, and `bus`/`drain` are all absent. Interactively a human accepts the prompts and it works, but there is **no post-install verification** that the files landed, and the start.md permission message implies trust makes local writes prompt-free (false for the install). *(Install completed by hand this slice — honouring the manifest `exclude`, which the install prose still ignores — to keep driving.)*
- **F2 — greenfield stack-wiring has no owner → the commit gate silently has no stack teeth.** The stack locks in `decision-engineer`/`planner` (DEC-A/DEC-B), but **no skill fills `.workflow/checks.env` or specialises the `rules/` `enforced by:` tags** when it locks — D127 *named* the deferral ("to `tech_stack` lock") but built no mechanism to un-defer it. Demonstrated live: with `checks.env` empty, a deliberately failing test (`assert 1 == 2`) fails pytest but **`checks.sh --check` still exits 0** — the pre-commit backstop skips all of format/lint/typecheck/test and runs only the coverage-linkage gates. A silent stack-gate defeat, structurally the D127 `cd`-leak's twin. (Same family: greenfield `.gitignore` lacks build-output patterns.) Filling `checks.env` by hand (scoped to `project/` per D127) armed the teeth immediately (broken test → exit 1).
- **F3 — verify-before-commit fails OPEN on a `state.json` shape drift (Wave-1/native sibling of the Wave-2 `state.json` bug).** `pre-commit.sh:36`/`guard.sh` read top-level `state.json.current_item`, gated by `if [ -n "$item" ]` — a *missing* key silently skips the whole verdict check. `schemas.md` pins `current_item` top-level, but the real orchestrator naturally wrote a richer nested `position.item` and initially omitted the top-level key, disarming the gate; it self-corrected only by its own vigilance. So the Wave-2 fail-open is **not only** a 9p-relocation problem — it is reachable on the native path whenever state.json lacks top-level `current_item`. Robust fix: fail *closed* / derive the item from the staged `.workflow/items/<id>/` diff, not a fragile state.json key.

**Handoff-durability (item 2) — RESOLVED: downgrade the claim, no new code.** Reproduced the failure before designing. The harness **`Write` and `Edit` tools are atomic** (inode changes on overwrite ⇒ temp + rename), so a session killed mid-handoff-write leaves the *previous* `handoff.md` fully intact — the feared torn/destroyed anchor **cannot happen** on a process/terminal/OOM/WSL kill (verified; a naive in-place truncate-write, by contrast, tore a copy to a fragment on the same kill — so it is the *harness* that provides the guarantee the orchestrator "cannot express"). `handoff.md` is committed each item, so `git` backstops the rest (the cold-start rebuild path is already `handoff.md + git log`). Residual is only **fsync durability against power-loss/kernel-panic** — moot for the common kill, git-backstopped otherwise, and not worth a shipped publisher that adds a *fourth* "orchestrator must remember to call it" fail-open surface (the F1/F2/F3 class). *The call:* correct `schemas.md`'s handoff durability line to state the real guarantee (harness-atomic; durable floor = git-commit-per-item + `drain.py`'s atomic machine block) and add the one rule that *is* load-bearing — **never rewrite `handoff.md` via a `Bash` `>` redirect** (that truncates in place and would tear); use the atomic `Write`/`Edit` tools.

*Why:* the Phase-5 thesis held a seventh time — a build-complete engine that never ran end-to-end is where wrong-mechanism bugs live, and this drive (the first with *real* dispatch on the *installed* plugin) surfaced three, two of them **silent safety-gate defeats** (F2, F3) — the exact class this project exists to kill. And the handoff-durability mandate turned out **already met** by the harness for every failure mode short of power-loss: the spec's assertion that a text-tool model "cannot express" the guarantee was true about the *tool call* and false about the *result*.

*Rejected:* **a shipped `handoff.py publish` helper** (the D117 inclination) — it buys only power-loss durability (git already backstops) at the cost of a new script *and* a new discipline the orchestrator must not drift from, i.e. another fail-open surface exactly like F2/F3; chose **downgrade-the-claim + the no-Bash-redirect rule**. **Fixing F1/F2/F3 this slice** — the maintainer's call was **capture now, discuss + fix immediately next session** (they are their own design discussions; F2/F3 are the sharp ones). **`--dangerously-skip-permissions` for the drive** — blocked by the meta-session classifier and unfaithful anyway; used the shipped `"Bash"`-allow settings + pre-seeded trust to run friction-free, and audited the allowlist statically (it is sufficient — confirmed).

*Evidence:* `~/p5-test` full drive (3 commits: bootstrap · `.claude` install completion · the `feat(slugify)` item; `deliver/roadmap-2` pushed to the local bare remote via the release path); `research`/`setup-guide` Task events carry `parent_tool_use_id` + `subagent_type: dev-autonomous-workflow:*`; codemap `2 nodes / 1 edge` on greenfield; `verify-verdict` first line `pass: true`; F2 `checks.sh --check` exit `0` on a failing test then `1` once `checks.env` filled; F3 `pre-commit.sh:36` `current_item` empty-guard confirmed at source; handoff inode-change (Write `217863→232685`, Edit `232685→232686`) + naive-write tear (`3986→991` bytes) + `git cat-file -p HEAD:.workflow/handoff.md` recovers. Resolves `07`'s **"real dispatch validation"** and the **D117 handoff-durability** question; reuses **D52** (prior sim dispatch), **D93/D117** (durability mandate), **D115/D127** (native path, checks.sh, import-root), **D105** (outbox), **D96–D98** (checkpoints). → `11` (`### Phase 5` Wave-1 REMAINING → done + F1/F2/F3 as the next fix slice), `07` (two questions resolved; F1/F2/F3 noted), `product/shared/schemas.md` (handoff durability line corrected + no-Bash-redirect rule).

## D129 — Phase-5 Wave-1 FIX SLICE: the three drive-found findings fixed **fail-closed, not signal-restored**, and re-verified by driving; stack-wiring gets an orchestrator owner, verify-before-commit derives the item from the staged diff, `/start` is interactive-only with a post-install gate **[DECIDED + BUILT + DRIVEN — Phase-5 Wave-1 fix slice; CLOSES D128's F1/F2/F3; resolves `07`'s "F2 has no owner" residual + folds the Wave-2 `state.json` fail-open; MEASURED by reproducing each live then re-driving on the real installed tree (`~/p5-test`), not reasoned]**
D128 captured three wrong-mechanism findings for a dedicated fix slice (maintainer's call). This slice fixed all three; each was **reproduced live before fixing and re-verified by driving**, not reading. **The spine of the slice is one move: fail *closed* / derive from the artifact — never "add the missing signal back."** F2 and F3 were both *silent* because an absent signal (an empty `checks.env`; an empty `$item`) read as "nothing to check" instead of "I cannot prove this is safe"; restoring the signal would leave the next drift silent, so the fix makes the *absent-signal state itself* block.

- **F2 — greenfield stack-wiring now has an owner AND a fail-closed backstop.** *Owner (the positive path):* the stack-dependent half of `/start` step 5 is named **the stack-wiring step**; greenfield `/start` seeds only the stack-independent floor (baseline `rules/`, `checks.sh` verbatim, a coverage-only `checks.env`) and **defers stack-wiring to `tech_stack` lock**, where **the orchestrator re-runs it** (a new `loop.md` section, *Stack-wiring at tech_stack lock*) — a one-time `unspecified→locked` transition, owned by the router so the leaf skills stay in their lane. *Backstop (the teeth):* `checks.sh --check` now **fails closed when `project_root` holds source but no `--check` stack command is wired** (`FMT_CHECK`/`LINT`/`TYPECHECK`/`TEST` all unset) — so a forgotten trigger stops the loop *loudly* instead of waving a failing test through. The backstop is load-bearing; the trigger is the convenience.
- **F3 — verify-before-commit fails closed via a shared helper, folding the Wave-2 `state.json` bug.** A new **`hooks/verify_check.py`** both `guard.sh` and `pre-commit.sh` call (so the two gates cannot drift — the drift is how a safety gate dies): it derives the item(s) under commit **from the staged `.workflow/items/<id>/` diff** (immune to both the shape drift — a nested `position.item`, no top-level `current_item` — and the path drift — a relocated runtime tree, the Wave-2 bug), reads `state.json` **runtime-resolved** (via `runtime.json`, mirroring `bus.py`) and **tolerantly** (`current_item` ∪ `position.item`), and **fails closed** (a `status:building` with no identifiable item, or a missing/failing/malformed verdict, all block). The old `if [ -n "$item" ]` "empty ⇒ skip" is gone. `schemas.md` records that the gate no longer depends on a single `state.json` key/path.
- **F1 — `/start` is interactive-only, and a post-install gate makes a hollow scaffold impossible.** `/start`'s `.claude/` writes are guarded by Claude Code **above** the settings allowlist (correctly — a workspace that could write its own hooks/settings could self-escalate), so a non-interactive `claude -p` has no grant path. Rather than fight that boundary: **step 0's re-run guard now keys on install-*completeness*** (install complete → resume/stop; incomplete → *resume the install*, never "already initialised" over a hollow tree), and **step 7 verifies every manifest `install[].dest` landed + no excluded test leaked + the daemon answered, and refuses to commit if not** — so init is "done" only when the scaffold *and* the files are present. Folded the three nits: the install copy **honours the manifest `exclude`** (the `test_codemap.py` leak — it ships inside the `scripts/codemap` dir entry), the **trust message** no longer implies the `.claude/` install is prompt-free (it is guarded above trust), and the stale **"Expand later" console-write-path** bullet (shipped since increment 3) is removed.

*Why:* the Phase-5 thesis held an **eighth** time in the same shape — reproducing each finding live first both confirmed the mechanism *and* shaped the fix, and re-driving on the real tree (not re-reading) is what proved the teeth bite: F2 blocked a failing test against p5-test's real `slugify` source; F3 blocked both drift vectors on *both* hooks while **passing the genuine ROADMAP-1 commit derived from the staged diff alone** (its `state.json` is gitignored, hence absent in a fresh worktree — the exact case a fragile-key read would have mishandled); F1's gate flagged the real 13-file headless-skip and a planted test leak. The ownership call (orchestrator, not a leaf agent) follows D80's one-owner discipline: stack-wiring is a project-level state transition, not per-item planning.

*Rejected:* **decision-engineer / planner owning stack-wiring** — a leaf agent resolving *any* decision can't cleanly tell it is *the* stack decision, and planner runs per-item (wiring is once-per-project); chose the orchestrator trigger + the shared `/start` routine. **"Restore the top-level `current_item`" as the F3 fix** — it re-buys trust in a fragile key the model already drifted from; chose derive-from-the-staged-diff + fail-closed, with `state.json` only a runtime-resolved cross-check. **Moving the installed scripts/hooks off `.claude/`** (to allow headless install) — it cannot move `settings.json`/the PreToolUse hook off the guarded path, so it does *not* achieve non-interactive completion, only trims interactive friction; chose interactive-only + the verification gate. **Blocking source-only commits in F3** (would harden further) — collides with the D66 prerequisite-repair two-commit carve-out and the bootstrap commit; left out of this slice (maintainer-confirmed). **Two hand-synced hook copies** — chose one shared helper (a single new manifest `install` entry) since a silent divergence between the two gates is precisely the failure mode. **Tightening the orchestrator to stop writing the nested `position.item`** — the hook is robust to it either way; not worth a source-side change (flagged, maintainer left it).

*Evidence:* reproduced-then-fixed on real git trees + the real `~/p5-test`: F2 `checks.sh --check` exit `0→1` against p5-test's `project/slugify.py` with empty `checks.env` (coverage gates still run); F3 both hooks exit `0→block` (pre-commit `1`, guard `2`) on the shape-drift and path-drift vectors, and the ROADMAP-1 replay (`git worktree` at `8333c68`, `state.json` absent) passes off the staged diff (`pass: true`); F1 verification `install verified: 13 entries` on p5-test, `MISSING: …` ×13 on a headless-skipped scaffold, `LEAKED excluded file:` on a planted `test_codemap.py`, and `rsync -a --exclude='test_*.py'` drops the test at the source. **328 pytest** (+9 `test_verify_check.py`, +3 `test_checks_runner.py` backstop); all five meta-gates green; leak gate clean; release boundary **13 install entries / 46 shipped files**. Reuses/relates **D126/D127/D128** (Phase 5), **D67** (`checks.sh` fixed runner), **D40/D65** (rules + enforcement wiring), **D80** (one owner per fact), **D54/D66** (one-commit-per-item + the prereq-repair carve-out), **D93/D115** (`state.json` + the `runtime.json` pointer), **D57/D58/D113** (packaging · trust · runner). Files: `product/templates/checks.sh`, `product/templates/loop.md`, `product/commands/start.md`, `product/hooks/{verify_check.py (new), guard.sh, pre-commit.sh}`, `product/MANIFEST.json`, `product/shared/schemas.md`, `product/scripts/{test_verify_check.py (new), test_checks_runner.py}`. → `11` (`### Phase 5` Wave-1 FIX SLICE → DONE), `07` (F2-no-owner residual → RESOLVED).

## D130 — Phase-5 Wave-2 driven: FS-relocation + the D129 verify gate verified on the real `/mnt/c` 9p mount (design held, no findings); brownfield `ingest` driven end-to-end on a real repo; three drive-found issues fixed + re-driven **[DECIDED + DRIVEN + BUILT — Phase-5 Wave-2; closes `11`'s two Wave-2 `[drive]` items + the opportunistic `align` `[bug]`; VERIFIES D129's fold of the Wave-2 `state.json` fail-open on a *real* relocation (session 12 had only a synthetic `runtime.json`); MEASURED by driving a real `claude` (v2.1.214) on the installed plugin against a real full-stack repo copied under `/mnt/c`, not reasoned]**
Wave 2 added the two families the native-path greenfield run (D126) deliberately collapsed out: **FS-relocation** and **brownfield ingest**, on the maintainer's own 9p mount. Target: a clean copy of a real full-stack app (the `stock simulator` — Python `backend/` + React/TS `frontend/`, ~720 first-party source files, rich `CLAUDE.md`+`docs/`+`diagrams/`) at `/mnt/c/Users/Guy Omer/Documents/p5-brownfield`. The installed plugin was refreshed to HEAD first — the earlier-session install was **stale at `935abaf` (D127)**, which would have tested the pre-D129 code (a version-pinned `plugin update` is a no-op on an unchanged semver; a forced uninstall+reinstall picked up `0b937ab`).

**Item 1 — FS-relocation + D129: the design HELD on the real mount; no findings.** The standing lesson's *opposite* also holds — driving confirmed a *correct* mechanism, not just found a wrong one.
- **Detection works with a real model.** The headless `/start` ran `df -T`, identified the **9p Windows-interop mount**, and concluded the runtime tree must relocate per step 3 — before touching anything.
- **The 0777-on-9p bug is real *today*** (re-measured, not trusted from D94/D95): a `0600` create on `/mnt/c` comes back **`0777`**, silently, from Linux; `~` (ext4) honours `0600`. So relocation is load-bearing.
- **Relocation lands correctly:** the runtime half (`state.json`, `bus.json`, `bus.lock`, `inbox/`, `parked/`, `alerts.json`) goes to the native ext4 `runtime_root`; token + lock are **0600** (not world-readable); the committed half + the gitignored `runtime.json` pointer stay on the mount; **two daemons run side-by-side with no collision** (per-project keying via `runtime.json`). The live daemon's `/health` shows only the two *expected* warnings (WSL death, no webhook) and **no false mode warning**; the shipped `probe_mode` returns the full "0600 came back 0777 → relocate" warning on the 9p path and is silent on ext4 — the detector is load-bearing *and* correct.
- **D129 verified on a *real* relocation (session 12 had only a synthetic `runtime.json`):** the decisive test — `state.json` living *only* on ext4, `status:building` + no item, nothing staged — **blocks (exit 1)**; the old hardcoded `.workflow/state.json` read (confirmed absent on the 9p side) would have proceeded (the old fail-OPEN). Shape-drift (nested `position.item`), failing-verdict, and genuine-pass all correct; a real `git commit` **aborted end-to-end** through the registered hook. Both hooks call the one shared `verify_check.py`.

**Item 2 — brownfield `ingest` driven end-to-end on a real repo (first ever exercise; `07`/`11` had it `authored but unexercised`).** Drove `/start`-brownfield → `ingest` → `checkpoint:reconcile` with a real model (namespaced `dev-autonomous-workflow:ingest`/`:research`): **codemap-at-scale** (752 nodes / 2391 edges / **0 parse failures in 2.8s**; both centrality lenses meaningful — impact → shared leaves, orchestration → entry-points; per-language tiers `python:433 t2`, `typescript:299 t2`, `shell:19 t0`); **`research` GATHER dispatch** with the heavy doc-reading staying in the subagent's context (hub-and-spoke held); the **rich-docs path chosen** over the thin-docs fallback; the **reconstructed `spec` → `docs/spec.md`**, every element `unspecified` (zero mis-tagged provisional); **node seeds** schema-correct (both lenses + `commitment:unspecified` + extractive purpose + empty edge-`why`/`# Sessions`, mirrored source tree); **adopt-without-clobber** (existing `ARCHITECTURE/PRODUCT_SPEC/ROADMAP` intact); and the **reconcile checkpoint** as a **blocking `kind=reconcile`** park, written **relocation-aware** to the native `runtime_root/parked/` and **surfaced by the live daemon** (`/api/state`; `status → "1 parked checkpoint still open"`) — verdict-ready.

**Three drive-found issues → fixed + re-driven (the Wave-2 fix half):**
- **`align` shipped two meta-repo-only gates (`[bug]`, confirmed static).** `align/SKILL.md` listed "the status-coherence and no-spec-refs gates" as mechanical-layer checks; neither `check-status-coherence.sh`/`check-no-spec-refs.sh` is in the install `MANIFEST` and both are meaningless in a product repo (this repo's roster/D-range coherence; the package's own spec-ref hygiene). *Fix:* the shipped `align` lists only the gates it **installs** (`check_contracts.py` + the three coverage gates); `format.md`'s meta-script reference dropped. *(Found by reading — a brownfield run stops at reconcile→prioritize; `align` is a later drift-threshold maintenance item.)*
- **`docs/architecture.md` case-collision on case-insensitive mounts (`[bug]`, latent → mechanism drive-verified).** The scaffold names a `document`-owned `docs/architecture.md`; the adopted repo has `docs/ARCHITECTURE.md`. This mount is **case-insensitive** — a lowercase write silently truncates the uppercase file (same inode, measured). So `document` authoring `architecture.md` would clobber the adopted 2052-line doc. *Fix:* `document`/`ingest`/`start.md` now scan `docs/` **case-insensitively** and **adopt an existing case-variant in place** (never a lowercase twin); the "never clobber" rule is now case-insensitive-aware. *Re-driven:* a real `document` refresh detected the collision (*"on this WSL /mnt/c case-insensitive filesystem they're the same file … refresh the existing ARCHITECTURE.md in place"*), created **no** lowercase twin, left `ARCHITECTURE.md` intact.
- **`ingest` re-derived the node/spec/parked formats each bootstrap (efficiency → reach-the-checkpoint risk).** The first ingest drive burned its turn budget hunting the formats across `schemas.md` + `memory-model.md` + `retention.py` + `bus.py` + `drain.py` (the **knowledge-node `.md` format had no owner** in `schemas.md` at all) and **ran out before parking the blocking reconcile checkpoint** — needing a continuation. *Fix (make templates prescriptive):* a new authoritative **`knowledge-node` section in `schemas.md`** (D80 — the missing owner), and precise pointers from `ingest` (spec + node schemas) and `checkpoint` (parked-ticket schema + the `runtime.json`-resolved park path). *Re-driven:* format-source reads dropped from **5 files to `schemas.md`-only**, and ingest completed **end-to-end in one session** (codemap → research → spec → 65 nodes → reconcile park), reaching the checkpoint it previously missed.

*Why:* the Phase-5 thesis held a **ninth** time and from both sides — a build-complete-but-never-run path (the FS-relocation step + brownfield `ingest`, both `[drive]`) is where mechanism-truth lives, and driving on the *real* 9p mount with a *real* model both **confirmed** the load-bearing relocation/verify design (item 1, no findings — the design was right *and* the mechanism was right, re-measured not trusted) **and** surfaced three issues no reading had (the `align` leak was reachable only by reasoning about the *target* context; the case-collision only reproduces on a case-insensitive mount — the exact platform Wave 2 targets; the ingest format-hunt only shows as a *budget* failure to reach the blocking checkpoint under a real model). The two fixes fit the project's spine: the case-collision fix is *adopt-don't-clobber, case-insensitive-aware* (never write a variant that overwrites adopted work), and the template fix is *one owner + a precise pointer* (D80) so the model reads one place, not five.

*Rejected:* **restore/keep the `align` meta-gates behind a "meta-repo only" guard** — they have no product meaning at all, so listing them at all is the leak; dropped outright. **Fix the case-collision by renaming the scaffold's `architecture.md`** — the collision is general (any adopted doc case-colliding with a workflow-owned lowercase name), so the fix is case-insensitive *adopt*, not a one-off rename. **Fix the ingest budget by duplicating the node/spec/parked templates into each skill** — violates the memory law (pointers-not-duplication); chose one authoritative `schemas.md` owner + precise skill pointers. **A mechanical `codemap`-emits-node-skeletons upgrade** (removes transcription too) — a larger change with a regenerate-vs-durable-prose seam; noted as a possible follow-on, not this slice. **Driving `/start` fully headless** — the nested `claude -p` sandbox blocks the plugin-package read and any write under `~` (the session-11 harness caveat), so the relocation/daemon/verify *mechanisms* were driven as the parent (more faithful for filesystem behaviour), and the model-behaviour halves (detection judgment, `ingest`, `document`-adopt) driven with a real `claude`.

*Evidence:* on the real `/mnt/c/…/p5-brownfield` (9p) + native `~/.dev-workflow/p5-brownfield` (ext4): live probe `0600→0777` on 9p vs `0600` on ext4; relocated `bus.json`/`bus.lock` mode `600`, two daemons keyed by `--workflow-dir`; `/health warnings=[WSL, no-webhook]` (no mode warning), `probe_mode(9p)`=warning / `probe_mode(ext4)`=None; `verify_check.py` exit `1` on the state-off-`/mnt/c` + no-item case, `0` on `pass:true`, and a real `git commit` blocked "FAILING verify-verdict". `codemap.sh` → `752 nodes / 2391 edges / 0 parse failures` in 2.8s; ingest re-drive **format reads schemas.md=3, memory-model/retention/bus=0**, `parked/brownfield-ingest-reconcile.json` `{kind:reconcile, blocking:true, token …:reconcile:…, deadline}`; `document` re-drive left `docs/ARCHITECTURE.md` 2052→2052 lines, no `architecture.md` twin; case-collision proof: `ZZARCH.md`/`zzarch.md` share one inode, lowercase write overwrote. **328 pytest**; all five meta-gates green (no-spec-refs `8 shipped paths`, status-coherence `17 skills + 2 agents; max D130`, enum-coherence, contract linter `0 advisory`). Reuses/relates **D126/D127/D128/D129** (Phase 5 + the D129 fold verified), **D93/D94/D95/D114/D115** (bus substrate · mode-on-9p · relocation + `runtime.json`), **D68/D72–D79** (codemap engine + arms), **D96–D98** (checkpoints), **D80** (one owner per fact), **D61** (memory law), **D81/D89** (`align` + the meta gates). Files: `product/skills/{align,document,ingest,checkpoint}/SKILL.md`, `product/commands/start.md`, `product/shared/{schemas.md (new `knowledge-node` section), format.md}`. → `11` (`### Phase 5` Wave 2 → DONE; brownfield-ingest `unexercised` → driven), `07` (the FS-relocation-step residual → exercised).

## D131 — `/start` is ONE enforced, resumable bootstrap motion: "initialised" = bootstrap-complete, phases anchored in `handoff.md` **[DECIDED — from the first lived brownfield onboarding (2026-07-20, `idea testing`, WSL/`/mnt/c`); extends D129's completeness key; BUILT 2026-07-21 (`start.md`) — re-drive pending (`11` Phase 6)]**
The first real onboarding stopped exactly where the artifact told it to: `commands/start.md` commits the scaffold at step 7; the mode handoffs ("Run `ingest`" §3 / "Hand off to `discuss`" §2) sit *after* that commit in trailing sections with no continue-now cue; and §0 literally says "**Install complete** → the project is fully initialised." The model treated the commit as terminal and the maintainer had to open a second chat to run `ingest` — the run's forensic timeline shows the seam plainly (bootstrap commit 20:56 → a fresh session's first ingest artifact 21:12). **The call: bootstrap is one enforced motion that ends only at the first human gate** — brownfield `/start → ingest → checkpoint:reconcile` (parked); greenfield `/start → discuss` (dialogue open). Concretely: (1) **"initialised" is redefined as bootstrap-complete, not install-complete** — §0's re-run guard keys on a recorded bootstrap *phase*, extending D129's install-completeness key: install incomplete → resume the install (D129, unchanged) · installed-but-not-ingested/discussed → **resume at ingest/discuss, never "already initialised"** · reconcile parked → report the parked checkpoint · reconciled → fully initialised. (2) The durable phase marker lives in **`handoff.md`** — the D48 anchor, written at each phase boundary; no new file, no new mechanism. (3) §2/§3 become imperative continue-in-this-session steps ("the commit is not the end of `/start`"), and §0's "fully initialised" conflation is fixed. The invariant is **resumability, not uninterruptedness**: a context reset mid-motion resumes at the recorded phase, exactly as D129's half-install resume does. Fits D29 (idempotent resume from `handoff.md`), D48/D51 (anchor vs volatile pointer), D85 (routing unchanged); **extends D129**.
*Rejected:* a separate `/init` command (a second entry point to teach; `/start` already owns the motion — the fix is finishing it, not renaming it); `state.json` as the phase authority (volatile + gitignored — not durable across the very reset the motion must survive); forcing the motion *past* the reconcile park (the park **is** the designed human gate; "one motion" ends where a human owes an answer).
*Evidence:* forensics on the real run (commits 7426164 20:56 → 6a2644b 21:40; two sessions); the start.md trace (§0 line 18, §2/§3 placement, no continue cue); maintainer verbatim: "I'd expect installation to be one continuous motion" / "I had to open another chat to run `ingest`." → `01`, `11`; built: `product/commands/start.md` (§0 three-way guard · §1 preamble · step-7 ledger · §2/§3 imperatives), `product/shared/schemas.md` (`handoff.bootstrap`).

## D132 — Interaction model HELD (D93/D99 reaffirmed): the confusion is a *surfacing* defect — the console becomes the bootstrap's front door and `/start` states the contract **[DECIDED — no locked decision amended; BUILT 2026-07-21 (`start.md` step 5, daemon-first) — re-drive pending (`11`)]**
The maintainer ended the first real onboarding believing "the whole interaction happens through the website — and it didn't even launch with `/start`." Forensics show the daemon **did** launch (step 6, 20:51:50, still bound on `127.0.0.1:41101` a day later) — the URL was printed once into a wall of install output and never surfaced again, nothing ever stated the interaction contract, and the console had nothing bootstrap-shaped to show (D133). Two candidate failures were separated: **(a)** the design is wrong — dialogue should live in the browser (overturns D93/D99, presses on D3); **(b)** the design is right but invisible. **The call: (b).** D93's terminal/bus split is physically grounded, not aesthetic — the orchestrator is a batch consumer and never an HTTP responder; a live browser chat needs a component sitting in Claude's request path (D3). And the maintainer's *described want* — "launch the website first, ask for priorities and discuss them while the infrastructure builds, act on the discussed requests once infra is done" — is **exactly the D99 intake form + D108 boundary drain the run never showed him**. The fix: (1) **the console is the bootstrap's front door** — daemon-ensure moves as early as the install allows (immediately after step 4 lands `bus.py`), `/start` surfaces the URL prominently and **best-effort auto-opens a browser** (`wslview` → `xdg-open` → `open` → `explorer.exe`/`cmd.exe /c start` chain; the printed URL stays the always-works fallback — a slash command's Bash can do this, no new mechanism). (2) `/start` **states the interaction contract in one short paragraph** at daemon-ensure and again at motion-end: *terminal = live dialogue (discuss); console = watch progress, file requests (intake), answer checkpoints — anytime, including right now while ingest runs.* (3) **Intake-during-bootstrap becomes defined semantics**: requests filed while the motion runs queue durably in the bus-owned `inbox/` (D93 single-writer, already true mechanically) and are drained at the **first scheduler boundary after reconcile** (D108) — "discuss priorities while infra builds" is now a documented property, not an accident of durable files.
*Rejected:* moving dialogue into the console (overturns D93/D99 against their load-bearing physics); a mandatory auto-open (headless/SSH targets have no browser; best-effort + URL is strictly safer); a third "bootstrap chat" surface (one more channel to explain — the fix is making the two existing ones legible).
*Residual — flagged for the maintainer's explicit call:* if, with the contract stated and the console visible from minute one, he **still** wants live dialogue in the browser, that is a real D93/D99 overturn (and a D3 collision) — his decision, deliberately not taken here; tracked in `07`.
*Evidence:* `bus.json` `{pid 335125, port 41101, started_at 2026-07-20T17:51:50Z}` + `ss` showing it still bound; the D93 conversation corollary + D99's rejected-chat entry; maintainer verbatim confusion. → `03`, `07`, `11`; built: `product/commands/start.md` (daemon-ensure = step 5, rules-wiring = step 6; headline URL + auto-open chain; the contract paragraph at step 5 and motion-end).

## D133 — Bootstrap progress is a first-class signal: the motion writes `state.json` phase/step markers the cockpit renders, and stage banners print at every boundary **[DECIDED — rides existing mechanisms, no new channel; BUILT 2026-07-21 — re-drive pending (`11`)]**
The real run had a 16-minute artifact-silent gap (bootstrap commit 20:56 → `graph.json` 21:12) and ~52 minutes bootstrap-commit→reconcile with **zero** user-visible signal in either terminal or console — the maintainer "felt stuck" while ingest was doing exactly its job. The trace confirms the design gap: `ingest`'s only human touchpoint is the step-4 reconcile checkpoint, and the cockpit renders loop state that bootstrap never writes. **The call: progress rides mechanisms that already exist.** (1) The bootstrap motion **writes `state.json`** (volatile, rewritten in place — D48/D51; orchestrator-owned single-writer — D93) with a bootstrap phase + current node + a human-readable step marker (`"codemap: 374 nodes"`, `"seeding knowledge nodes 40/95"`), updated at every stage boundary — the cockpit's "Now" renders it via the existing snapshot poll (D99), so the console the user just opened (D132) shows live bootstrap progress for free. (2) `ingest` and `/start`'s long steps **print a one-line stage banner at each boundary** in the terminal. The new `state.json` fields get their `schemas.md` owner (D80) at build time.
*Rejected:* a progress log file (a new always-read artifact against D51's bounded-by-construction law); console-side inference from file mtimes (guessing at progress the writer knows precisely); SSE/push (D99 chose snapshot-poll; 2–5s polling is ample for minute-scale stages).
*Evidence:* the mtime timeline (20:56 → 21:12 silent; reconcile commit 21:40); maintainer verbatim: "~30 min in it *felt* stuck (I knew it was building mandatory files, but there's no signal)." → `03`, `05`, `06`, `11`; built: `product/commands/start.md` (§1 preamble), `product/skills/ingest/SKILL.md` (stage rule), `product/scripts/bus.py` (snapshot `phase` + "Now" row), `product/shared/schemas.md` (`state.phase` owner).

## D134 — Bootstrap context law: `graph.json` is machine-data never LLM-context, seed selection is mechanical, `[X]` extraction runs in subagents, and the motion ends the window **[DECIDED — extends D68/D88/D92 into ingest's letter; pins `06`'s deferred `[X]` mechanism; BUILT 2026-07-21 (`--seed-list` drive-verified on the real 374-node graph → 30 bounded seeds) — ingest-side re-drive pending (`11`)]**
The onboarding session ended ~600k tokens. Attribution against the artifacts, not vibes: **(a)** ingest step 3 says "copy the frontmatter fields straight from `graph.json`" — on the real repo that is a **139,812-byte / 374-node** file (~35–40k tokens) pulled whole into the main window just to pick a bounded seed set: D68's bound is on nodes *written*, not bytes *read*. **(b)** `research` returns size-unbounded `findings` and synthesis runs in the main context (D88's charter split is right; its envelope is unbounded). **(c)** The `[X]` extractive pass (95 nodes on the real run) ran from the main window. **(d)** The same window then ran a **full feature item** (21:40→00:17) — D92 declares the conversation disposable with heavy work in fresh windows, but nothing marks bootstrap→loop as a reset point. D92's architecture held wherever it was actually applied (D128/D130: the hub-and-spoke `research` dispatch kept the orchestrator clean; D130's schemas.md fix removed the format-hunt) — the gap is that ingest's *letter* never inherited the law. **The call:** (1) **`graph.json` is never read whole into LLM context.** The seed-set selection (impact ∪ orchestration ∪ spec-core, top-K) is computed *mechanically* by the shipped codemap engine — a `codemap.py` selection mode that emits the bounded seed list + per-node frontmatter fields; the orchestrator reads only that emission. This pins `06`'s "[X] mechanism deferred to implementation" and follows the D129 spine (derive from the artifact; never leave a deterministic computation to judgment). (2) **`[X]` extraction runs in batched subagent windows**, never the main context. (3) **`research` findings get a stated size budget** in the skill (condensed findings + pointers, never file bodies). (4) **The bootstrap motion ends the context window**: the reconcile park (brownfield) / spec-commit + discuss handoff (greenfield) is the designed reset point — the orchestrator says so explicitly, and the loop resumes post-verdict in a fresh session (drain/runner — D108/D123), never by rolling the bootstrap window into feature work. Composes with D131: "one motion" spans `/start`→park — and *only* that.
*Rejected:* raising the ceiling ("600k worked once") — context is scarce by master-rule economics (D92), and the 720-file Wave-2 repo would not fit; "read graph.json carefully" (top-K over two centrality fields is deterministic — exactly what D129 says never to hand to judgment); a summarizer agent over graph.json (the engine already owns the data — D71: parse/compute = Python, and a summary of a machine file is derivable prose D38 forbids storing).
*Evidence:* graph.json 139,812 B / 374 nodes / 294 edges on the real run; one session spanning 20:36→00:18 (install + ingest + a full item); D128's counter-example (34.5k-token research subagent, orchestrator stayed clean); D130's format-hunt fix (same failure family, same cure). → `06`, `11`; built: `product/scripts/codemap/codemap.py` (`seed_select` + `--seed-list`/`--include`, spec-core-first ordering, missing-includes surfaced; +2 tests, 330 green), `product/skills/ingest/SKILL.md` (step-3 rewrite + never-whole-read rule + window-end), `product/agents/research.md` (bounded-`findings` constraint).

## D135 — `/update` is promoted into Phase 6, and the first real install pins its constraints: version-stamped installs; regenerate `[G]`, never clobber `[D]`/adopted; additive over a pre-existing `.claude/` **[DECIDED — priority + constraints only, the skill stays undesigned; the version-stamp half BUILT 2026-07-21 (`start.md` step 7 writes `config.workflow_version` from `plugin.json`; `schemas.md` owner) — Phase 6 (`11`)]**
The maintainer re-raised "how do we update an installed copy / what if the knowledge structure changes" unprompted during the first real onboarding — and that run created the first out-of-tree install that will actually go stale (`idea testing`: 3 commits on main, a live daemon, 95 knowledge nodes). **The call:** the framework version-update skill moves from the undated `[stageable]` pool into **Phase 6's worklist** (design → build), and the run pins three constraints any design must honour: (1) **installs must be version-stamped** — today nothing in a target records which package snapshot it holds, so `/update` has no migration key; `/start` stamping the plugin version into the scaffold is its own Phase-6 item. (2) **The knowledge migration split follows D39**: `[G]` structural nodes + `graph.json` are *regenerated* under the new schema (never text-migrated), while `[D]` durable content, adopted `docs/` (including case-variant adoptees — D130's case-insensitive adopt-in-place), and human-locked spec invariants are *carried, never clobbered* — D50's adopt-without-clobber law applied to updates. (3) **Real targets have a pre-existing `.claude/`** — the run's target carried a May-era workflow-kit the install sat beside; `/update` must diff against the manifest `install[]` map (D125's single ship boundary), never treat `.claude/` as wholly its own.
*Rejected:* designing the skill in this capture (needs its own slice with the migration cases enumerated); leaving it undated `[stageable]` (a live stale-able install now exists — the cost stopped being hypothetical).
*Evidence:* the `idea testing` install forensics (pre-existing `.claude/` skills/agents from May–Jun beside the Jul-20 install; no version marker anywhere in the scaffold); maintainer's unprompted re-raise. → `07`, `11`.

## D136 — Interactive context governor: a statusline budget-warning → `/dispatch` handoff → `/clear` → `SessionStart` auto-rehydrate, with a `PreCompact` backstop — the manual-clear cycle made a first-class, hook-backed mechanism for non-runner sessions **[DECIDED + BUILT 2026-07-26 — extends D92/D131/D134 to interactive sessions; from the second planning pass on the lived onboarding; unit-verified (20 governor tests, full 321-test suite + all 5 meta-gates green); re-drive pending (`11` Phase-6 sequence)]**
An interactive orchestrator session has **no context governor**: the fresh-window-per-ticket reset lives only in the away-runner (D123), so a human driving `/start` + a feature item in one terminal accumulates unbounded context — the real `idea testing` run hit ~600k (a 374-node ingest **and** a full feature item, `zero-cost-ai-stack`, in one window, on pre-D134 code). D134 ends the *bootstrap* window at the park, but nothing governs a long *interactive* run, and D123's "the manual `/clear` stopgap is retired" holds only in away-mode. **The call: ship an interactive context governor built from harness primitives, anchored on the one surface the running token count is exposed to — the statusline.** (1) A shipped **statusline** script (wired via `.claude/settings.json`) reads `context_window.used_percentage` / `total_input_tokens` every turn and, past a **config percentage threshold** (`config.context.warn_pct` — never a hardcoded `300k`, which assumes the 1M model), shows a persistent "run `/dispatch`, then `/clear`" banner; detection **must** live here because hooks and the model receive no token metrics. (2) A new **`/dispatch`** command writes a complete, current `handoff.md` on demand so a clear is always safe. (3) A **`SessionStart`** hook (matcher `clear`) re-injects `handoff.md` (`additionalContext`) so a cleared session **auto-rehydrates** — the resume half of D131's §0 phase-ledger, now automatic. (4) A **`PreCompact`** hook is the automatic backstop: if the human sails past the warning into auto-compaction it writes the handoff first and injects the anchor, so even an ignored warning preserves state (it cannot *block* the hard ceiling — a backstop, not a gate). Composes with D92 (disposable conversation), D131 (resumable motion), D134 (window-end), D123 (the away analogue), D48/D51 (`handoff.md` the durable anchor). New config/state/hook shapes take their `schemas.md` + `MANIFEST` `install[]` owners at build.
*Rejected:* the model self-measuring its own context (not exposed to it — only the statusline gets `context_window.*`); a hook-driven warning (hooks receive no token metrics — verified against the Claude-Code hook contract); a *blocking* `PreCompact` to force the reset (it cannot block the hard ceiling); leaning on D123's runner alone (fresh-window-per-ticket never runs for the interactive, `runner:false` user — the exact mode the maintainer used); raising or ignoring the ceiling (context is scarce by master-rule economics — D92/D134, and the 720-file class of repo will not fit).
*Evidence:* the real `idea testing` scaffold — `config.json` `runner:false` + no `workflow_version` (a stale D130 install, pre-D134), `handoff.md` recording install → 374-node ingest → a full feature item in one window at ~600k; a Claude-Code capability check (statusline `context_window.{used_percentage,total_input_tokens,context_window_size}`; `PreCompact` fires before auto **and** manual compaction, stdout→context, exit-2 blocks manual only; `SessionStart` matcher `clear` injects `additionalContext`; `/clear` preserves hooks/skills/settings/`CLAUDE.md`, wipes conversation). → `11` (Phase 6 governor item), `05`/`shared/schemas.md` (`config.context.warn_pct` + governor state at build).
*Built 2026-07-26 (`product/**`), four shipped surfaces:* (1) **`scripts/statusline.py`** wired in `templates/settings.json` `statusLine`, reading `context_window.used_percentage` (token-math fallback) and showing a persistent bold banner past `config.context.warn_pct` (default **75**, a percentage — never a hardcoded 300k). It **composes, never clobbers**: a `/start`-captured `.workflow/statusline.delegate` (the user's pre-existing global/project statusline command, gitignored + machine-specific) is run with the same stdin and its stdout taken as the base line, with the banner appended only over threshold; no delegate ⇒ a minimal `model · dir · ctx N%` base. (2) **`commands/dispatch.md`** — writes a complete, current `handoff.md` on demand (Write/Edit atomic, never a Bash redirect), leaves `drain.py`'s machine block untouched, does not commit — so a `/clear` is always safe. (3) **`hooks/session_start.py`** (SessionStart matcher `clear`) — re-injects `handoff.md` as `hookSpecificOutput.additionalContext` so a cleared session auto-rehydrates; silent when there is nothing to resume. (4) **`hooks/precompact.py`** (PreCompact, both `manual`+`auto` — the input carries **no `trigger` field**, so the matcher distinguishes them) — injects the anchor + a "run /dispatch to refresh" directive, **exit-0/never blocks**: a deterministic hook cannot *author* a fresh handoff (that needs a model turn), so the backstop *preserves* state through an ignored-warning auto-compaction rather than fighting the ceiling. All three scripts fail safe (statusline never exits non-zero → never blanks the line; the hooks never wedge session-start/compaction; `additionalContext` truncated under the ~10k cap). `config.context.warn_pct` + `statusline.delegate` took their `shared/schemas.md` owners; the three scripts joined `MANIFEST` `install[]` (13→16 entries); `templates/settings.json` gained the `statusLine` + `SessionStart` + `PreCompact` wiring; `templates/orchestrator-CLAUDE.md` Handoff&resume + `start.md` step 4/gitignore describe the interactive-reset path. The Claude-Code contracts were **re-confirmed against the current statusline/hook docs before building** (not reasoned from memory). **Exit test = the live re-drive** (Phase-6 sequence), exercising the governor on a real long interactive run alongside D131/D132/D134 — captured BUILT + unit-verified, drive-verification pending.

## D137 — `/update` design SETTLED: a 3-way file taxonomy (package-refresh · target-preserve · regenerate-from-code) + four best-practice calls (command · package-owns-`settings.json`/user-owns-`.local` · record-install-set→proven-orphan-removal · unify-greenfield-on-marked-block) **[DECIDED 2026-07-26 — design only; build sequenced AFTER the Phase-6 re-drive; realizes D135's constraints; the two small `/start` tweaks (record install-set · greenfield markers) ride the build]**
D135 promoted `/update` into Phase 6 and pinned its constraints but left the skill **undesigned**; pressed to settle the design so the next session can build directly, the maintainer delegated the open calls to best practice. **The call — a version-update mechanism built on a 3-way file taxonomy, version-stamp-driven:**
- **(a) package-owned → refresh** from the new plugin: MANIFEST `install[]` scripts/hooks + the copied templates (`settings.json`, `loop.md`, `checks.sh`, the orchestrator brief). Plugin-loaded commands/skills/agents live in `${CLAUDE_PLUGIN_ROOT}` and refresh with the plugin itself — nothing to copy.
- **(b) target-owned → never clobber** (D50's adopt-without-clobber applied to updates): `[D]` durable bodies (`# Sessions` / `Purpose` / edge-`why`), adopted docs (incl. D130 case-variants), the reconstructed/authored spec, decision-record bodies, human-set `config.json` knobs, and all live loop state (`backlog` / `handoff` / `state` / `items` / `parked` / `outbox` / `secrets` / `checks.env`).
- **(c) regenerate-from-code** (D39, never text-migrate): `graph.json` + the `[G]` node frontmatter via `codemap.sh`; the `[D]` bodies are preserved and re-attached under the regenerated frontmatter.
`config.workflow_version` is the migration key: OLD==NEW → no-op + a change summary; a **missing** stamp = unknown-old → full reconcile + stamp (the `idea testing` case — its parked `zero-cost-ai-stack` RunPod setup checkpoint + ADR `0001` + 95 nodes are all category (b), preserved). Migration is **idempotent reconcile, no migration-script ledger in MVP** — a genuine `[D]`-body format change is flagged for human review, never auto-rewritten.

**Four calls, best-practice (maintainer-delegated):**
1. **A command** (`commands/update.md`), the sibling of `/start` — interactive-only for the same reason (the `.claude/` write-guard sits above the settings allowlist). *Rejected a skill:* `/update` is never loop-dispatched, and the interactive-only argument is `/start`'s exactly.
2. **Package owns `.claude/settings.json`** (overwrite from the new template + re-capture the statusline delegate); the human's personalizations live in `settings.local.json` (Claude-Code-merged, never touched). A pre-overwrite diff surfaces hand-edits for confirmation rather than silently clobbering. *Rejected a per-key merge:* a "which keys are package vs user" registry is a fragile second source of truth (element-level hook-array merge is a trap) — the platform's settings layering already solves it.
3. **Record the applied `install[]` dest-set** in the scaffold at stamp time (both `/start` and `/update`), so `/update` removes only **proven** orphans (recorded-old − new-manifest, printed); an unrecorded file is never touched, and the first update / unknown-old is **flag-only** + writes the set for next time. *Rejected blind removal* (can't tell a retired-package file from a user's own drop-in) *and flag-forever* (cruft accretes; a retired hook file lingers). This is D135's "diff against the manifest `install[]` map" made precise across versions.
4. **Unify greenfield onto the sentinel-marked block** — greenfield `/start` wraps its orchestrator brief in the same markers brownfield uses, so `/update` replaces only the marked block in both modes and never touches project notes outside it. *Rejected whole-file refresh* (clobbers additions to the root `CLAUDE.md`) *and flag-if-changed* (leaves the brief permanently stale).
Calls 3 and 4 are small forward-compat `/start` tweaks that ride the `/update` build (the build depends on them).

*Rejected (scope):* building it in this slice — the Phase-6 sequence puts one clean re-drive of the built-but-undriven governor/onboarding surface first, so the build lands on a driven foundation and the drive can inform it.
*Evidence:* D135's three pinned constraints (version-stamp · regenerate-`[G]`/never-clobber-`[D]` · additive-over-a-pre-existing-`.claude/`); the `idea testing` forensics (no `workflow_version`, a May-era `.claude/` beside the install, a parked checkpoint + ADR + 95 nodes that must survive); Claude Code's own settings layering (`settings.local.json` merges over `settings.json`). → `11` (Phase-6 `/update` item + the version-update-skill bullet), `07` (version-update skill entry). Build pending the re-drive — captured decided so the next session builds directly.

## D138 — Phase-6 re-drive DRIVEN on a pristine p5-brownfield: D131–D134 confirmed by driving; D136's live banner stayed unexercised (the context law kept the window lean); four package findings, the sharp one FIXED **[DRIVEN 2026-07-27 — Phase 6's exit test; a real interactive `claude` running `/start` (brownfield) on the HEAD-installed plugin (`gitCommitSha ed2b01e`, governor included) against the 733-file / 107k-LOC stock-simulator fixture; MEASURED by driving, not reasoned. Entry RE-UNIFIED 2026-07-29 from the original capture and a reconstruction made while the original was believed lost — see *Provenance*]**
The Phase-6 sequence put one clean re-drive of the built-but-undriven onboarding surface before the `/update` build, so the build would land on a driven foundation. The re-drive ran interactively on the pristine `p5-brownfield` fixture (reset to `d707ea9`) against a HEAD-reinstalled plugin carrying the D136 governor.

**Confirmed by driving (not by reading):**
- **D131 (one motion)** — `/start` → detect → install → commit → ingest → `checkpoint:reconcile` → park, one continuous session, no split, no "already initialised"; ended exactly at the human gate. The ledger advanced at each phase boundary and §0's guard keyed on bootstrap-completeness.
- **D132 (console front door)** — the URL (`http://127.0.0.1:45633/`) surfaced as a headline immediately after the install copies, *before* the long half; the browser auto-opened (via `explorer.exe` — see finding 4); the terminal/console contract stated once; the away-channel-absent + WSL-daemon-death caveats relayed, not swallowed.
- **D133 (bootstrap progress)** — `state.json` published at every stage boundary (`start:2→6→7 → ingest:codemap→spec→nodes → checkpoint:reconcile`), which the console "Now" panel renders.
- **D134 (bootstrap context law)** — code map 744 nodes / 2391 edges / 0 fails / 2.8s; `--seed-list 10 --include <22-file spec-core>` → 36 nodes; `graph.json` never read into context; per-file `[X]` purpose extraction in 3 batched subagents (returned `done`, output never entered the main window); ~780k subagent tokens kept off the main context.

**The governor's live banner NEVER fired** — the context law kept the window lean enough that usage never crossed `warn_pct`. So D136 is *installed and rendering*, but its `/dispatch → /clear → SessionStart rehydrate` cycle stays **unexercised**; proving it needs a heavier interactive run or a deliberately lowered `warn_pct`. Recorded as still-pending rather than claimed — a mechanism that never fired is not a driven mechanism.

**The drive-found bug (high severity): `verify_check.py` blocked EVERY brownfield bootstrap commit.** D133 publishes `state.json` `status: building, phase: bootstrap` at the scaffold commit; the D129 verify gate blocks `building` + no-identifiable-item and never checked `phase`. A **D133↔D129 integration bug** — D130 predated D133, so no earlier drive could have hit it, and neither decision is wrong in isolation. **The call:** a surgical carve-out keyed on the **explicit** `phase == bootstrap` marker (never an inference from an absent item), so only a state the bootstrap itself published skips the fail-closed; a `building` state with no item and no bootstrap phase still blocks, and a bootstrap commit that *does* stage an item dir still has that item's verdict checked. *Rejected relaxing the unidentifiable-item block generally* — that is the F3 fail-open D129 closed, and re-opening it to fix a bootstrap edge case trades a loud dead-end for a silent gate defeat.

**Three findings LOGGED, not fixed** (→ `07`): **mid-flow human questions** — the motion interrupted the human for clarifications instead of resolving them (`research`/`decision-engineer`) or batching them to the reconcile gate, which violates the one-motion-to-the-first-gate principle (`ingest` is meant to default `unspecified` and defer confirmation to reconcile); **the `--check` stack lint scoped over the vendored `.claude/scripts/`** — 143 findings on the workflow's own code, which is replaced wholesale on update, so the stack gates must scope to `project_root` (extends D127's project_root-scoping note, still leaking on brownfield); and **`xdg-open` hung ~2 min on WSL** before the `explorer.exe` fallback, so the step-5 browser-open chain needs a per-attempt timeout — it stalls the motion exactly when the human is told to look at the console. Product findings self-filed by the loop as designed (6 debt items + failing tests → the p5-brownfield backlog) — the mechanism worked.

*Also confirmed (not new):* the 9p relocation held again (runtime → native ext4, `0600` honoured, `runtime.json` pointer); 6/6 code spot-checks confirmed; and the **brownfield-adopted-gates open question (`07`) played out live** — the repo fails its own configured gates (ruff/format/Postgres-tests), and the model scoped `checks.env` to the staged diff + filed the debt rather than wedging the bootstrap (a reasonable resolution of that deferred question — worth confirming as the intended behaviour).

*Provenance — this entry was written twice, and the second time on a false premise.* The original capture was made on a machine rebuilt shortly after; with no git auth on the rebuilt machine, even `ls-remote` failed, so the record read as lost and `origin/main` appeared to stop at D137 (`9aaa669`). A reconstruction was written from the session record (landed in D139/D140's commit) on that belief. **It was wrong** — the original had reached `origin` as `7ad17d0`, and surfaced the moment auth was restored. This entry is the two folded into one: the measured specifics (the console port, node/edge counts, seed counts, subagent token volume, the fourth finding, the reconcile token below) come from the original; the reconstruction's framing and its `verify_check.py` analysis are kept. The reconstruction's own caveat — *treat the observations as recalled rather than re-measured* — is now **retired**: they are measured. *The lesson worth keeping is the one that produced the error: "the record did not survive" was inferred from a broken auth path, not established. An unreachable remote is not an empty one.*
*Evidence:* the drive report — one session, 3 commits, tree clean, reconcile parked at `bootstrap-reconcile` / token `rec-27a06449affe`, deadline 2026-07-29. → `11` (Phase-6 tags: D131/D132/D133/D134 re-driven, D136 banner unexercised, findings 2–4 as follow-ups), `hooks/verify_check.py` (finding 1 fixed), `07` (findings 2–4).

## D139 — `/update` BUILT: a fixed reconcile runner owns the arithmetic, the command owns the judgment; the install ledger makes an orphan *provable*; the two `/start` forward-compat tweaks land with it **[BUILT 2026-07-29 — realizes D137's design + D135's constraints; extends D127's ships-fixed precedent to the update path; the last Phase-6 item]**
D137 settled `/update`'s design and its four calls. Building it forced one call D137 had not: **where the mechanical half lives.** The taxonomy's arithmetic — an exclude-filtered expected-set, the proven-orphan set difference, a "was this hand-edited?" hash check, a pre-overwrite confirm gate — is exactly the invariant, error-prone logic **D127** ruled must never be LLM-freehand (the `checks.sh` precedent: `/start` writes *data* and calls a *fixed* runner). **The call — split the command:**
- **`scripts/update_reconcile.py`** (a new MANIFEST `install[]` entry, 16→17) ships **fixed** and does the arithmetic: `plan` (read-only) · `apply` · `record`. It may write **only** package-owned paths — that is enforced by a computed allowlist and asserted by a test that snapshots the whole target and proves every target-owned artifact is byte-identical after an apply. Category (b) is a *mechanism*, not a promise in prose.
- **`commands/update.md`** owns the judgment: the refuse-the-wrong-situation guards (no `.workflow/` → `/start`; mid-bootstrap; mid-item; dirty tree), showing the plan and the real diffs to the human, code-map regeneration with `[D]` bodies preserved, the unmarked-brief path, the daemon restart on the new `bus.py`, the change summary, the commit, and the `/clear`.
*Rejected a pure-markdown command* (literally D137 and no more): nothing to unit-test, and the orphan/ledger arithmetic re-derived from prose on every run — the drift class D127 and D125 each closed once already.

**The install ledger — `.workflow/install-set.json` (D137 call 3, made precise).** It records every path the install wrote **with the hash it wrote**, expanding manifest directory entries file-by-file (so a retired file *inside* an installed directory is detectable too) plus a `CLAUDE.md#brief` pseudo-entry for the managed block's body. That is what makes two otherwise-unanswerable questions answerable at update time: *is this file ours?* (recorded ⇒ ours; unrecorded ⇒ the human's, never touched) and *is it pristine?* (hash matches ⇒ safe to overwrite; differs ⇒ hand-edited). **Committed** — unlike `runtime.json`, its paths are repo-relative and machine-independent. Absent ⇒ unknown-old ⇒ everything still refreshes, nothing is ever removed, and the confirm-required files need explicit confirmation.

**The confirm gate is mechanical, not a reminder.** `apply` **exits 2 and refuses** when `.claude/settings.json` or the brief block holds local edits, until `--confirm-overwrite` is passed. D137 call 2 said "a pre-overwrite diff surfaces hand-edits for confirmation"; a driver that must *remember* to ask is the same shape as F2/F3, so the runner blocks instead.

**Two `/start` tweaks (D137 calls 3+4), plus one correction.** Step 7 now runs `update_reconcile.py record`; step 4 wraps the orchestrator brief in the managed-block markers in **both** modes (greenfield too — a greenfield `CLAUDE.md` accumulates human notes just as surely, and one shape means `/update` has exactly one thing to find). The markers are declared a **byte-stable cross-version contract** in `schemas.md`: changing them orphans every existing install's brief. Correction found while editing: step 7 read `${CLAUDE_PLUGIN_ROOT}/plugin.json`, but the file is at `.claude-plugin/plugin.json`.

**A real bug the dry run found — the D125 `.pyc` class, third occurrence.** Running `plan` read-only against the real `idea testing` install planned `ADD .claude/scripts/codemap/__pycache__/…​.pyc`: a `.pyc` basename does not match a `**/test_*.py` exclude, and a **directory-source** marketplace plugin (the maintainer's dev setup) carries `__pycache__` that a release snapshot would not. `/start`'s install had the identical hole. **Fixed at the owner** — `**/*.pyc` + `**/*.pyo` added to `MANIFEST.json` `exclude`, so all four consumers derive it rather than each hardcoding a prune (`build-release.py` already had its own; the leak gate its own). *The lesson repeats: driving a read-only plan against a real target found in one command what the unit tests, written against a clean fixture, could not.*

**Also folded in (D138 findings):** the `verify_check.py` bootstrap carve-out (re-applied after the D138 loss, + 2 regression tests, one proving it still blocks a failing item) and the `xdg-open` WSL hang (opener detached with a hard `timeout`, exit status ignored — the printed URL is the contract, the auto-open must never cost time). The other two D138 findings stay open in `07`.

*Verification:* 371 tests green (21 new: 19 `test_update_reconcile.py` + 2 `test_verify_check.py`) and all five meta-gates. **Caveat:** the build machine had no `pytest` installed (no `pip`, no `ensurepip`) — the unittest-based bulk ran natively under `python3 -m unittest`, the pytest-style files under a scratchpad shim. A real `pytest` run has not been done on this slice. → `11` (Phase-6 `/update` item + roster), `07`.

## D140 — Machine-local artifact audit: the durable half is portable and the runtime half is not — and there is **no repair path** when a machine changes **[AUDIT + CLASSIFICATION 2026-07-29 — remediation DESIGNED NEXT; opened by a real loss (a PC rebuild renamed `$HOME`, stranding `idea testing`'s whole runtime tree); scope pinned here, `11` Phase 7]**
The maintainer rebuilt his PC. `idea testing`'s `.workflow/runtime.json` still points at `/home/guy/.local/state/dev-autonomous-workflow/idea-testing`; the user on the new machine is `guyo`. The pointer names a directory that does not exist, so **the entire runtime half is unreachable** — and per `schemas.md` that is a hard error, never a fallback, which is the *right* call and also means nothing starts. This audit asks the general question the incident raises: *what else is like this?*

**The audit (measured against the real `idea testing` install, not reasoned):**
- **Portable — committed and machine-independent ✅**: `config.json`, `loop.md`, `checks.sh`, `checks.env` (verified: no absolute paths), `codemap.sh`, `handoff.md`, `backlog.md`, `items/`, `docs/**` incl. `graph.json` (verified: no `/home` or `/mnt/c` strings in 139 KB), the new `install-set.json`, and — because `/start` commits them — `.claude/scripts/`, `.claude/hooks/`, `.claude/settings.json`. A clone on a new machine gets a working *package* and a working *memory*.
- **Regenerable, correctly ✅**: `state.json` (the designed cold start rebuilds it from `handoff.md` + `git log <base_sha>..HEAD`), `bus.json`, `bus.lock`, `orchestrator.lock`, `alerts.json`, `remote_token` (a re-mint changes the remote URL — human-visible, not silent), `statusline.delegate` (degrades to the minimal base line).
- **Lost, and load-bearing ⚠️** — the actual finding, four items:
  1. **`parked/<id>.json`.** `schemas.md` says "every entry mirrored in `handoff.parked[]` for cold-start rebuild" — but that mirror is **prose the orchestrator writes**, i.e. a discipline, not a mechanism. Measured: `idea testing`'s committed `handoff.md` carries **no `parked[]` block at all**, so its parked `zero-cost-ai-stack` RunPod setup checkpoint has no surviving on-disk record. This is the F2/F3 shape exactly — a durability property that depends on the model remembering.
  2. **`.git/hooks/pre-commit`.** Git never clones hooks. A fresh clone therefore loses the mechanical-gate backstop **silently** — the fail-closed gate is simply not installed, and nothing notices.
  3. **`outbox/`** — approved-but-unfired outward actions vanish with no trace; and **`secrets/`** — correctly never committed, but **no re-elicit path is specified**, so the loop later reads a credential that is not there.
  4. **`~/.claude.json` trust** is per-machine, so a moved project is untrusted → `claude -p` and the relaunch-runner **stall** (the D123 finding), with no re-grant path outside `/start`.
- **The structural gap under all of it:** `runtime.json` is gitignored **correctly** (a committed absolute path would hand another machine a *wrong* root, which is worse than none), but **no command can re-point or rebuild it.** `/start` §0 sees a complete install and either reports initialised or resumes the *bootstrap motion* (re-running `ingest`); `/update` deliberately never touches runtime paths; the daemon fails loud and exits. There is a correct *detection* everywhere and a repair path nowhere. **A per-machine artifact needs a per-machine (re)binding step — that is the missing capability, and naming it is this entry's call.**
- **One incidental leak:** `idea testing`'s committed `handoff.md` prose contains the absolute runtime path. It is the only surviving record of where the runtime went — by accident, not by mechanism, and now wrong.

*Deliberately NOT decided here* — the remediation shape (a `/rebind`-style command vs a `/start` §0 arm vs making the daemon self-heal), whether `handoff.parked[]` should become a machine-written block like `drain.py`'s rather than prose, and whether the git hook should be re-asserted on every session start. Those are the next session's design work; this entry pins the *scope* and the *evidence* so it starts from measurement rather than from the incident. → `11` (Phase 7), `07` (the open remediation questions).

## D141 — Machine-move remediation DESIGNED: `/rebind` is a third sibling that **binds**, every detector **routes and none heals**, and the runtime root gains a *derivation* + an *identity* — plus the half D140 missed, the **silent** mis-bind **[DECIDED 2026-07-29 — design only, build sequenced 7a→drive→7b; answers all five of `07`'s Phase-7 questions; two findings BEYOND the audit; corrects one `07` framing and one `07` severity call]**
D140 pinned the scope and the evidence: correct *detection* of a dead runtime pointer everywhere, a repair path nowhere. This entry settles the remediation. Eleven calls, in two slices.

**The shape — a third sibling, discovered *for* the human.** The remediation is **`/rebind`**, backed by a fixed, unit-tested **`scripts/rebind.py`** (`check` = the dry-run · `apply` = a **no-op on a healthy install**). The split is D127/D139's, unchanged: the runner owns the arithmetic (probe · validate · classify · write pointer · stamp · enumerate loss), the command owns the judgment (what is lost, what to re-elicit, what to file). The three commands sit on **three orthogonal axes** — `/start` = *the project isn't bootstrapped* (once) · `/update` = *the package is old* (per release) · `/rebind` = **this machine is not the machine that installed** (per machine move) — so a third command is principled, not accretion. The "yet another command to remember" objection dies on **routing**: four independent detectors already fire on this condition and each now *names* the cure — `bus.Paths`' raise, `/start` §0, the daemon's exit, `/update`'s warn. **Detectors detect and route; none heals.**
*Rejected — daemon self-heal*, hard: the daemon is **non-interactive**, and re-binding is a decision **with loss** (parked verdicts, outbox, secrets), so a background `mkdir` of a fresh root converts a correct loud failure into silent state-loss — the exact "never restore the missing signal" floor. It also cannot re-grant trust or re-elicit a credential.
*Rejected — a `/start` §0 arm as the repair* (accepted only as a **guard**): `/start`'s motion **re-runs `ingest`**, so a mis-detected branch re-ingests a 95-node project — wrong blast radius; and a once-command cannot own an N-times job. §0 still gets a **fourth completeness state** (installed + bootstrapped + *unbound*) because a human on a new machine types `/start` first — it **stops and routes**, it does not repair.
*Rejected — folding it into `/update`*: `/update` is version-gated and a **no-op on an unchanged version**, which is the very trap `idea testing` is sitting in.

**`/update` **warns**, it does not block — a correction made mid-analysis.** The first instinct was one uniform block-and-route rule across all three commands. It is wrong twice: `/update` is **repo-side only** (`update_reconcile.py` reads MANIFEST + project files + `install-set.json`, never a runtime path), so it does not *depend* on the binding; and blocking would **deadlock**, because `rebind.py` ships *inside* the package `/update` installs. Uniformity here buys nothing and costs the escape hatch.

**Re-binding is neither recovery nor re-creation — the runner probes and *classifies*.** `07` framed it as re-creation ("a new machine has no old runtime tree to move"); that declares loss without looking. Three cases, decided mechanically:
1. **RE-POINT (lossless)** — a valid tree is found. Probe order: the literal old path → **the old path with `$HOME` re-prefixed** → the canonical derived path. *That second rule alone would have recovered the incident losslessly had the rebuild renamed the home rather than destroyed it.*
2. **ADOPT-IN-PLACE** — no pointer, runtime files in `.workflow/`: re-run the mount check and relocate, or confirm the local case and write nothing.
3. **RE-CREATE (lossy)** — nothing survives (**`idea testing` is this case**). Reconstructed: `state.json` (`handoff.md` + `git log <base_sha>..HEAD`), `bus.json`/`bus.lock`/`orchestrator.lock`/`alerts.json`, `statusline.delegate`, `demos/`. Re-minted human-visibly: `remote_token` (the remote URL changes ⇒ re-pair). **Genuinely LOST and itemized**: `parked/`, `outbox/`, `secrets/`.

**Two findings BEYOND the audit, both closed here.**
- **The runtime root's location is model-chosen prose.** `/start` step 3 says only "create a runtime tree on a local filesystem (under the user's home)"; `idea testing` got `~/.local/state/dev-autonomous-workflow/idea-testing` because a model picked it. Two projects with the same basename in different parents therefore **derive the same path and cross-bind two live installs** — silent two-project corruption. **Call:** a code-owned `runtime_root_for(project_path)` → `$XDG_STATE_HOME/dev-autonomous-workflow/<slug>-<short-hash-of-abspath>`, called by **both** `/start` step 3 and `rebind.py`. The hash kills the collision; the determinism is what makes the probe's third candidate exist at all.
- **`isdir()` is the entire validity check.** A restored backup, a second WSL distro, or any directory at that path binds clean. **Call:** a **`.workflow-runtime` stamp** inside the root — `{project_path, bound_at, bound_host}` — so `Paths` fails on **mismatch**, not merely absence. Migration is tolerant-read / strict-write: absent stamp ⇒ legacy ⇒ accept **and write it**; no existing install breaks.

**The silent mis-bind — the half D140 missed, and the worse half.** The audit measured the *loud* failure (pointer names a dead dir → `Paths` raises). But when `runtime.json` is **absent**, `Paths` returns the workflow dir by design ("no relocation happened") — right on a native mount, and **wrong on a fresh clone under `/mnt/c`**, where it silently lands the capability token and `secrets/` on the very `0600`-ignoring mount the relocation exists to avoid. The mount check that would prevent it lives in `/start` step 3 *prose*, which a clone never runs, and `bus.py`'s existing mode warning is a notification that the control already failed. **Call: `Paths` fails closed** — no pointer + a weak mount (9p/drvfs/network) ⇒ the same hard error the dead pointer gets, naming `/rebind`. The path resolver, not a prose step, owns "may this filesystem hold the runtime tree". *Fallback if the probe proves unreliable across WSL/macOS/Linux: the loud-warn arm — never a false-positive hard stop on a working install.*

**Loss is filed as typed `issue` entries in `backlog.md` — durable *and* bounded.** A printed loss report is the same failure as the prose parked mirror: durability that depends on a human remembering. `backlog.md` is already the D80 owner of the live OPEN queue and is committed, so no new source is adopted. But the first form proposed — free-prose OPEN lines — **reintroduced unbounded growth**: D59 bounds `backlog.md` by **closability** (`prioritize` GCs roadmap items on their done-flip and `issue` entries whose `github_ref` is closed), and prose matches neither rule, so every machine move would leave permanent sediment. **Call:** file each loss through the existing `issue` schema (local `kind`/`severity`/`source`, no `github_ref`) so it enters in the shape `prioritize` already retires. *Build-time obligation:* confirm `prioritize`'s GC actually collects a local issue with **no** `github_ref` — if it only filters *on* `github_ref`, that path must be extended before this is safe.
*Rejected — a dedicated `rebind-log.md`* (a new D80 source earning nothing `backlog.md` does not already do; a file nothing routinely reads is a file the loss dies in) and *rejected — raising each loss as a parked checkpoint* (it would write the loss record into the very runtime tree whose volatility caused the loss, and block the loop on infra debris; fine as a follow-on the backlog entry triggers, not as the record).

**Trust needs no mechanism at all.** D140 item 4 (`~/.claude.json` is per-machine, so a moved project stalls `claude -p` and the runner) closes for free: `/rebind` is **interactive-only**, so *running it* re-grants trust as a side effect. State it; build nothing.

**Slice 7b — the durability trio (none of it blocks the `idea testing` update).**
- **`bus.py park` becomes the writer.** `07` proposed making `handoff.parked[]` "a machine-written block like `drain.py`'s" — that framing **hides the catch**: `drain.py` already *was* the code writer of the thing it mirrors, whereas `parked/<id>.json` has **no code writer at all** (`checkpoint/SKILL.md` tells the model to write the JSON *and* to resolve the runtime root itself). You cannot bolt a machine block onto a model-authored write. **Call:** a `bus.py park` subcommand takes `{id, kind, summary, deadline}` and writes `parked/<id>.json` **and** a fenced `<!-- parked:begin/end -->` block — the proven two-authors-one-file idiom, unchanged; the skill calls it. It simultaneously deletes SKILL.md's "resolve the runtime root yourself, never assume `.workflow/parked/`" — prose `Paths` already owns. *Rejected — committing `parked/` outright:* a setup checkpoint's body is exactly where a credential or a large payload appears, and `parked/` is runtime for `rename`/`0600` reasons committing does not satisfy. The mirror carries **ids + kind + summary + opened-at only** — the record does not move, it **projects**.
- **The git hook is re-asserted from `SessionStart`, non-clobbering — and `07` over-rates the scrutiny.** `07` says a shipped hook installing another hook "needs the same fail-closed scrutiny as F3". **Corrected:** F3's failure was a safety gate silently *disarmed*; here the gate is **already** disarmed on every clone, so re-asserting can only ever *arm* it. Severity is also lower than it reads — in-loop commits go through the `commit` skill's `checks.sh --fix`, so the git hook backstops **out-of-loop** commits only; missing it narrows coverage, it does not disarm the loop. **Call:** `session_start.py` gains an idempotent three-way — absent ⇒ install + one line · byte-identical ⇒ silent · **different ⇒ never clobber**, warn once that a foreign `pre-commit` is installed and the mechanical gate is not wired. `/rebind` asserts it too. Cost: two `stat`s and a hash. *Known residual:* the warning is invisible to `claude -p`, so a headless clone stays quietly uncovered. *Rejected — `/rebind`+`/start` only:* a fresh clone runs **neither** (it is already bootstrapped and already current), so the case that most needs the assert would never get one.
- **Secrets get a declared required-set, not a scan.** Absence is undetectable by inspection — an empty `secrets/` is indistinguishable from "this project needs none". **Call:** `config.json` `secrets_required[]` (**key names only, never values**), written by the `setup` checkpoint at elicitation; `rebind.py` reports `required − present` as itemized loss; **point-of-use fail-closed stays as the floor** — the manifest is early warning, never a replacement.

**Sequence — deliberately split, on the maintainer's own caveat ("don't let `/update` sit unexercised another cycle").** **7a = the bind capability** (`rebind.py` + `/rebind` + `runtime_root_for()` + the stamp + the two `Paths` hardenings + four routing arms + typed-issue losses) → **drive it on the real `idea testing` install** → **7b = the durability trio**. Nothing in 7b blocks the update, and the parked mirror **cannot recover** `idea testing`'s lost checkpoint anyway, so building it first buys that install nothing — while driving 7a first gets 7b designed from real evidence, the way Phases 5 and 6 earned their findings.
**Run order on `idea testing`: force-reinstall the plugin at HEAD → `/rebind` → `/update`.** Rebind first because the point of the run is to learn how `/update` behaves on a **normal** install; against a knowingly-broken one every surprise is ambiguous between an update bug and an unbound install. `rebind.py` runs from `${CLAUDE_PLUGIN_ROOT}` for that first pass — the legitimate exception to "never invoke a shipped script in place" (that rule exists because the plugin root is replaced on update; a one-shot repair invoked by an interactive command is not exposed to it). The rebind also stamps **`bootstrap: complete`** into that `handoff.md`, which carries no `bootstrap:` line at all (a pre-D131 install), closing the trap where `/start` §0 would read a demonstrably-finished project as bootstrap-incomplete and re-ingest 95 nodes. *Accepted cost:* `/update`'s warn-and-route arm then goes unexercised on a real install.

*Evidence:* measured against the real stranded install, not reasoned — `runtime.json` naming `/home/guy/...` on a machine whose user is `guyo`; `.workflow/` carrying **no** `install-set.json` and `config.json` **no** `workflow_version` (⇒ `/update` reads "unknown-old": nothing provably removable, both human-facing files need explicit confirmation); `handoff.md` with **no** `bootstrap:` line yet a complete brownfield history (`a6df8ee`, 95 nodes, ADR 0001); `.git/hooks/pre-commit` present **only because this is the same working tree, not a clone**; `checkpoint/SKILL.md`'s hand-write instruction read directly; `retention.py` confirmed to prune `items/` + `demos/` **only**, so `backlog.md`'s sole bound is D59's closability. → `11` (Phase 7 → 7a/7b), `07` (the five questions retire; two residuals stay), and on build: `scripts/rebind.py`, `commands/rebind.md`, `scripts/bus.py`, `commands/{start,update}.md`, `hooks/session_start.py`, `skills/checkpoint/SKILL.md`, `shared/schemas.md`, `MANIFEST.json`.

## D142 — Phase 7a BUILT: `/rebind` ships (runner + command + four routing arms), the runtime root gets its derivation and its identity, and `Paths` fails closed on the silent mis-bind — plus three calls the design could only make with code in front of it **[BUILT 2026-07-29 — dry-run VERIFIED against the real stranded `idea testing` install; both `07` residuals discharged; the interactive drive is the maintainer's, still owed]**
D141 settled the design; this is the build. `scripts/rebind.py` (+ `scripts/test_rebind.py`, 41 tests) and `commands/rebind.md` ship, `bus.py` gains `runtime_root_for()` / `slugify()` / the `.workflow-runtime` stamp / a tri-state mount probe and two hardened `Paths` arms (+20 tests), and the four routing arms land in `bus.Paths`, `/start` §0, the daemon (via `Paths`), and `/update`. 427 tests green (371 at `ce30ab4`), all five meta-gates green, MANIFEST `install[]` 17 → 18 with `test_rebind.py` provably not leaking (the release-boundary check reports it).

**The weak-mount call went FAIL-CLOSED, not the fallback — because the probe was already there and it MEASURES.** D141 left this open explicitly ("make that call with real code in front of you"), on the worry that a mount check that could not be made cheap and correct across WSL/macOS/Linux would hard-stop working installs. The worry dissolved on contact: `bus.probe_mode()` has measured this since the console was built — a `0600` create, then a `stat`. There is no fstype table to go stale, because it asks the only question that matters, and it costs one syscall pair. The build split it into `probe_mode_bits()` → `mount_honours_modes()` returning **True / False / None**, and the third value is what removes the risk entirely: **only a measured failure stops**; an unmeasurable tree (read-only, absent, permission-denied) returns the old answer. A false positive would break a working install, which is strictly worse than the silence it replaces — so the undecidable arm is not a nicety, it is the reason fail-closed is safe to ship.

**Three calls D141 could not have made without the code.**
- **`bind` is a separate verb from `apply`.** D141 said `runtime_root_for()` is "called by **both** `/start` step 3 and `rebind.py`", which is true and insufficient: `/start` step 3 calling `apply` would have filed three *"lost in a machine move"* backlog issues against a project on its **first minute**, and written a placeholder `state.json` on top of the position the bootstrap motion publishes at every stage boundary. Same probe, same derivation, same mount floor, same stamp — but on a fresh scaffold there is nothing to have lost and no position to guess, so `bind` does neither. The classification is `BIND`, and the difference is not mechanical, which is exactly why it needed a separate verb rather than a flag buried in prose.
- **Only a RELOCATED root is stamped.** D141 said "a `.workflow-runtime` stamp inside the root". Inside `.workflow/` the binding is true **by construction** — there is no pointer that could be wrong and nothing else can be at that path — so a stamp there would have bought nothing and cost every native-filesystem install a new gitignore entry and a new committed-tree surprise. The identity check now runs only where identity is in question.
- **`prioritize`'s GC needed the extension D141 flagged as a possibility.** The build-time obligation was to *confirm* it retires a local `issue` with no `github_ref`. It did not: `schemas.md` already said a local item closes on its backlog done-flip and `prioritize` collects it, but `prioritize/SKILL.md` step 1 named only two rules and the issue rule was `github_ref`-only — the owner and the skill disagreed, and the skill is what the model reads. Extended to *any entry `commit` flipped done*, naming local issues explicitly. Without it every machine move would have left permanent sediment in `backlog.md`, which is the unbounded growth D59 exists to prevent.

**The dry run against the real stranded install — `RE-CREATE`, exactly as predicted, and the probe's second rule is visibly present.** `check` ran read-only and non-interactive against `/mnt/c/Users/guyo0/Documents/Projects/idea testing`, wrote nothing (`git status` clean, no state dir created), and reported all three candidates missing: the literal `/home/guy/.local/state/dev-autonomous-workflow/idea-testing`, **the same path with this machine's `$HOME` re-prefixed** (`/home/guyo/...`), and the canonical derived location. The middle line is the one worth reading — the rule fired correctly and the tree genuinely is not there, so the rebuild **destroyed** the home rather than renaming it. Losses reported: `parked/` (the `zero-cost-ai-stack` RunPod setup checkpoint), `outbox/`, `secrets/`. Two things the report also settles: the target is `idea-testing-c14000ae`, so the rebind **migrates that install onto the collision-proof scheme** as a side effect; and the runner never guesses the loop position — it writes `status: idle`, no `current_item`, and a `note` that says so, leaving reconciliation against `handoff.md` + `git log <base_sha>..HEAD` to the command, where the judgment belongs.

**The stamp found a real bug on its first run.** `test_bus.py::test_pointer_expands_user` pointed a fixture at `~`, so the new strict-write stamped `.workflow-runtime` into the *developer's actual home directory*. The test now redirects `$HOME`. A mechanism that catches its own test suite writing outside the fixture on day one is the mechanism working.

*Rejected — a `--confirm` gate on `apply`:* `apply` never overwrites an existing runtime file (it creates what is absent and repoints what is dead), so a healthy install is a **fixed point** and a re-run is a no-op. Safety by construction beats a flag a human learns to pass reflexively. *Rejected — reconstructing `bus.json` / `bus.lock` / `orchestrator.lock`:* they are liveness artifacts, not state — a stale bus record advertises a dead daemon and a stale lock blocks a live orchestrator, so both are worse than absent. Restart the daemon instead. *Kept out of scope:* `hooks/verify_check.py` carries its own mirror of the resolver and degrades to the workflow dir on a dead pointer. It is not one of D141's four arms, it fails **closed** on the gate it guards regardless, and touching the verify gate to add a warning it cannot display is a bad trade — noted as a residual, not fixed here.

*Evidence:* the real install dry-run above; `bus.probe_mode()` read in place and found already-empirical; `prioritize/SKILL.md` step 1 read against `schemas.md`'s issue entry and found narrower; the release-boundary check reporting 54 shipped files / 18 install entries / no test leak; 427 tests + five meta-gates green. → `product/scripts/{rebind.py,test_rebind.py,bus.py,test_bus.py}`, `product/commands/{rebind.md,start.md,update.md}`, `product/skills/prioritize/SKILL.md`, `product/shared/schemas.md`, `product/MANIFEST.json`, `10` (roster gains `rebind`), `11` (7a tags), `07` (both residuals discharged).

## D143 — Phase 7a DRIVEN on the real stranded install: `/rebind` held, `/update` **crashed outright** on the mount it most needed to work on, the push floor was producing a *less* safe workaround, and a pre-ledger install was missing five package files — one of them silently breaking a documented flow **[DRIVEN 2026-07-29/30 — Phase 7a's exit test + the `/update` run owed since Phase 6, both on `idea testing`, the real machine-move casualty; three package fixes shipped from it; MEASURED by driving]**
The run order was D141's: force-reinstall the plugin at HEAD (`gitCommitSha` verified == HEAD) → `/rebind` → `/update`. All three ran. `idea testing` is bound, updated, and pushed (4 commits, `6ad3048`…`8e03d1e`); Phase 6's last owed step is discharged with it.

**`/rebind` held, including the half no test covers.** `RE-CREATE` as predicted, all three probes missing, the tree rebuilt at the derived `idea-testing-c14000ae` — so the run also migrated that install onto the collision-proof scheme. The **judgment** half then did every one of its four jobs: it rejected the runner's placeholder `state.json` (`idle`/no item) and reconstructed the real position (`building` / `zero-cost-ai-stack` / `checkpoint:setup`) from `handoff.md` + `git log`, which matters because an idle state would have let `prioritize` re-pick work the handoff says is parked; re-opened the one parked checkpoint from prose with a **fresh** token; wrote the missing `bootstrap: complete`; and filed the losses. *The split held under a real load: the runner refusing to guess a position, and the command recovering it, is the design working rather than a gap.*

**Three package fixes, all found by driving and none reachable by reading.**
- **`/update` crashed outright on the DrvFs mount — `PermissionError` on `chmod` — and that is the worst place in the system for it to fail** (`38065aa`). `_atomic_write` chmod'd unconditionally; a filesystem that does not honour modes (DrvFs without metadata, CIFS/SMB, some bind mounts) raises `EPERM` even though the write succeeded. The failure **deadlocks**: `rebind.py` ships *inside* the package `/update` installs, so a project stranded on such a mount had no path forward at all — the exact trap D141's "`/update` warns, never blocks" call was reasoning about, reached from the other direction. Fixed as best-effort chmod warning **once per run**, plus temp-file cleanup on any failure (the crash had deposited a `guard.sh.tmp.update` that read as unexplained debris). The mode is cosmetic here regardless: every installed hook and script is invoked *through* its interpreter, so no exec bit is load-bearing. **Aborting over an unenforceable permission bit is strictly worse than proceeding.**
- **The main/master push floor was generating a *less* safe workaround** (`df5440d`). `guard.protected_branches` was add-only and the floor had no override, so on a **solo** repo the loop could not push its own default branch and the human pushed out of band — skipping the outgoing-range secret scan entirely. `schemas.md` had argued the opposite deliberately (disabling a floor should cost an edit to `guard.sh`, a visible owner-level act) — and that reasoning **assumed a team**, where "a human moves main" names a *different* human than the loop. On a solo repo it buys no separation of duties. **Call:** a strict, committed, default-OFF `guard.allow_protected_push`; added names survive a lowered floor; fails closed on every degraded read; announces when it lowers. The outgoing secret scan stays non-overridable. The rejected rationale is **recorded in `schemas.md`, not deleted**. *Also closed here: `guard.sh` had **zero** test coverage despite being the Layer-1 hard floor — now 13 cases.*
- **`/rebind` pointed at the project's own copy of the runner** (`b48fdc0`, found pre-drive while writing the run guide). It told a project lacking `rebind.py` to run `/update` first — **inverting the rebind-before-update order for exactly the projects the command exists to serve**, since the installs that most need re-binding are the ones whose `.claude/` predates it. Now `${CLAUDE_PLUGIN_ROOT}`, the same exception `/update` already makes.

**`/update` on a pre-ledger install: five package files were missing entirely, and one was load-bearing for a documented flow.** Unknown-old as expected (`REFRESH?` throughout, nothing removable, human-facing files gated on explicit confirmation, `BRIEF-UNMARKED`). But the reconcile found `session_start.py`, `precompact.py`, `statusline.py`, `update_reconcile.py` and `rebind.py` **absent, not stale** — so the **`SessionStart(clear)` rehydrate had never existed on that project**: a `/clear` dropped into an empty session while the docs described resuming from `handoff.md`. That is the D131-family failure again — *a documented flow whose mechanism was never installed reads exactly like a working one* — and it also means the D136 governor was never present there at all, so its unexercised-cycle residual was never even reachable. A re-run of `plan` now reports `SAME` for all 21 paths with the ledger present; the code map regenerated 381 nodes / 295 edges / 0 failures with all 95 authored `[D]` bodies preserved and **no `node_modules` pollution** (the first machine where `node_modules` existed to leak).

**The environment class the D140 audit never enumerated — and the first blockage the loop provably cannot clear itself.** The audit concluded the durable half "is portable: committed, no absolute paths". True of the *files*, false of their *executability*. `checks.env` is committed and names `cd desktop && npm run typecheck`; `node_modules` is gitignored and correct to be. A correctly-rebound project could not make a **single commit**. Worse, one limitation explains three symptoms previously treated as separate — **DrvFs cannot `chmod`**: a `0600` create comes back `0777` (the reason the runtime relocation exists), `git config` writes fail on their lockfile, and `npm install` fails on package bins. So on the maintainer's own mount **a WSL-side agent cannot install the toolchain at all**; only a human on the Windows side can. Git credentials are a second instance (the HTTPS helper died with the rebuild; SSH was the fix, and `git remote set-url` itself failed on the same `chmod`). **Call: this is a 7b item, and the probe is not "is Node installed?" but "run `checks.sh --check` exactly as the pre-commit hook runs it, and report whether it exits clean"** — same side, same shell, no boundary to get wrong, and it would have said *cannot run* up front instead of at the commit. *Rejected — a toolchain-detection heuristic:* it would have to know which side of the WSL/Windows boundary each command belongs to, which is the thing that just went wrong.

**A machine move is an unintentional clean-room reproducibility audit.** `desktop/package-lock.json` had been broken in **both** directions for ~5 weeks — missing `electron-log@5.4.4` (declared 2026-06-21, never locked) *and* still carrying 19 removed `@clerk/*` packages plus transitives (unlocked 2026-06-15), with `version` trailing 1.0.0 vs 1.1.0 — so `npm ci` failed and **no clean-image install could have succeeded in that window**. A warm `node_modules` hid it completely; a cold machine made it blocking in one step. Nothing in the workflow would have caught it, which is precisely what that project's open *"add a CI workflow"* backlog item is for.

**Two diagnostic traps worth keeping, both of which caught me.** (1) **A WSL→Windows bridge inherits a Windows `PATH` cached at WSL init**, so a freshly-installed Windows tool reads as *absent* until WSL restarts — `cmd.exe /c node -v` returned "not recognized" for an installed Node, and I read that as "not installed". (2) I told the maintainer WSL `npm` would satisfy the gate and Windows Node was unnecessary; **the `chmod` wall makes that false**, and their install was required. Both errors have the same shape as D142's: *a conclusion inferred from a probe that was answering a different question than the one asked.* Also minor, same family: the loss report named one lost outbox push where `origin/main..HEAD` held **three** unpushed commits, having inferred a queued action the handoff explicitly said was never queued — **loss derived from a destroyed queue is a guess, and should be labelled one.**

*Evidence:* the four `idea testing` commits and their messages (`6ad3048` rebind · `7a17c7d` lockfile · `c00cdf7` toolchain anchor · `8e03d1e` update), all pushed; `npm ci --dry-run` exit 0 and the armed `tsc` gate green afterward; `chmod` measured returning `EPERM` on `/mnt/c` directly; the plugin cache verified at `gitCommitSha == HEAD` before the run and the installed `rebind.py` exercised from it. 445 tests + five meta-gates green. → `11` (Phase 7a DRIVEN; Phase 6's last step discharged; 7b gains the environment probe), `07` (the environment class opens; two Phase-6 residuals stand), `product/hooks/guard.sh`, `product/scripts/update_reconcile.py`, `product/commands/rebind.md`, `product/shared/schemas.md`, `product/templates/orchestrator-CLAUDE.md`.

## D144 — Phase 7b BUILT: parking gains a code writer and the handoff mirror becomes a **projection**, the bindability probe lands at the machine transition (not on a timer), the pre-commit backstop is re-asserted non-clobbering, and secrets get a declared set — plus three calls only the code could make **[BUILT 2026-07-30 — the durability trio + the environment probe D143 added; the probe's placement question DECIDED by the maintainer; 507 tests + five meta-gates green; not yet driven on a real install]**
7b was deliberately held back so it would be designed from the D143 drive's real evidence rather than a hypothesis. All four items are landed, unit-tested, and swept. **Nothing here has been driven** — that is the phase's remaining exit test.

**`bus.py park`/`unpark` — parking finally has a writer, and the mirror is a PROJECTION.** The record lands at the runtime root through `Paths` (retiring `checkpoint/SKILL.md`'s "resolve the runtime root yourself, never assume `.workflow/parked/`" — a second owner of a rule `Paths` already owns), gets `deadline` + `opened_at` stamped, is written `0600` with the achieved mode verified, and projects a fenced `<!-- parked:begin/end -->` block onto `handoff.md`. The machine-block machinery is now generated from **one** `block_markers()` so a third block cannot invent a third spelling of `drain.py`'s idiom, with the `drain:` literals reproduced byte-for-byte because a handoff.md in the field already carries them. The mirror holds **ids + kind + summary + opened-at only** — a test asserts a `setup` body's credential and the correlation token never reach the committed file.
**Three calls the design could only make with the code in front of it:**
- **`park` takes the full record on STDIN, not the four flags D141 named.** A four-field record cannot be schema-valid: it drops `token` (the anchor the drain matches a verdict on) and `request` (what the console renders), so the writer would have produced a *degraded* record. Stdin also keeps a nested, judgment-rich `request` out of a process listing, and the skill pipes it through a **quoted heredoc** (`<<'JSON'`) so a body carrying quotes/`$`/backticks arrives byte-exact instead of being mangled by the shell. The D127/D139 split is unchanged — the orchestrator composes judgment, the runner validates and **refuses** a record that cannot do its job (no id, no token, unknown kind, empty request) and writes nothing on refusal.
- **`unpark` is not optional, and D141 missed it.** Prose `handoff.parked[]` was *accidentally* self-correcting — the orchestrator rewrote the whole file at each handoff, so a resolved checkpoint simply stopped being written. A **persisted** machine block is not, so `park` alone would ship a block that only ever GROWS, reporting answered checkpoints as open forever in the one file a cold start trusts — strictly worse than the prose it replaced, because a machine block reads as authoritative. So the block is re-derived from `parked/` on every mutation, and `unpark` (idempotent) is wired into the verdict arm of `orchestrator-CLAUDE.md` + `loop.md`. It also makes the "already-closed token" anchor *real*: closed means the record is gone, and until now nothing removed it.
- **The deadline is stamped at MICROSECOND precision.** `alert_key` is `(ticket_id + deadline)` and its docstring **accepted** a same-second collision, reasoning "a re-park almost always yields a later deadline" — sound while a model hand-stamped it at human speed, and false the moment a script derives it. Two re-parks of one ticket inside a second (a retried `/rebind` re-opening the same checkpoint is the real path) would collide into "already alerted" — i.e. **silence**, the failure class this project treats as unacceptable. Closed; the residual is now narrower and the caller's own doing (a park that *supplies* a duplicate deadline).
*Rejected — committing `parked/`* (unchanged from D141): a `setup` checkpoint's body is exactly where a credential appears, and the tree is runtime for `rename`/`0600` reasons committing does not satisfy. The record does not *move* to the committed half, it **projects** onto it.

**The bindability probe reports from `rebind.py apply` — not `check`, and not a standing `SessionStart` probe.** D143 decided the mechanism (run `checks.sh --check` exactly as the pre-commit hook runs it — same command, cwd and shell, asserted by a test — and report whether it exits clean, never a toolchain-detection heuristic). **The open half was *where*, and it is the maintainer's call: `apply`.** *Rejected — a standing `SessionStart` probe:* it runs the project's whole test suite before a session can begin, which is this repo's master rule (**never sit in Claude's request path**) inverted; the harness timeout kills a slow suite and a killed probe is indistinguishable from a failing one; it is invisible to `claude -p`; and making it cheap needs a cache-invalidation rule (which lockfile? which mtimes?) that is a toolchain heuristic wearing a different hat — the very thing D143 rejected. *Not `check`:* that dry run's contract is **"writes nothing"** (VERIFIED in D142) and running a project's `TEST` command writes caches and build artifacts. `check` reports `NOT PROBED` and says why. Skipped on `BIND` (at `/start` step 3 the stack is not wired, so the gate answers a question nobody asked) and on `HEALTHY` (`apply` is a fixed point there, and a full test suite is not a no-op). `--no-probe` opts out; a hung gate times out rather than hanging the repair.
**Two calls inside it.** The probe **reports an observable and does not diagnose** — a non-zero exit means "you cannot commit right now", and whether that is a missing toolchain or a genuinely red test is for the reader; inventing that distinction is the rejected heuristic. And **the gate's output tail goes to stdout ONLY, never into the filed loss**: `backlog.md` is committed, the tail is arbitrary subprocess text, and the one control that would catch a secret in it is the staged-diff scan in the very gate that just failed to run. The diagnosis belongs on the screen of the human deciding what to do, not in a committed file forever.
**The standing half is one clause, not a mechanism.** The pre-commit hook already runs the gate on every commit; it just never named the other possible cause. It now routes a failure to `/rebind` in its block message — the right moment, zero recurring cost, no cache, and **visible to `claude -p`**, which is exactly where the SessionStart residual bites.

**The pre-commit re-assert, and the case that most needs it is a CLONE.** `session_start.py` gains the idempotent three-way (absent ⇒ install + one line · byte-identical ⇒ silent · different ⇒ **never clobber**, warn once), and the `SessionStart` matcher is broadened to `startup`/`resume` — the **rehydrate stays `clear`-only**, because injecting the whole handoff on every startup is a different and noisier feature. Broadening is *required* by the design's own motivating case: `.git/hooks/` is not part of the repository, so every clone of a bootstrapped project arrives with the gate silently absent, and a clone runs neither `/start` (already bootstrapped) nor `/rebind` (already bound). **"Warn once" is keyed by the sha256 of the FOREIGN hook**, stored in `.git/hooks/.disciplined-builder-assert` — machine-local by construction (a clone warns on its own), never committed, no gitignore entry and no runtime-tree dependency; a *different* foreign hook is new information and warns again, and installing after a warning clears the marker. `/rebind`'s arm calls `session_start.py --assert-hook`, the same tested code path, rather than re-describing the three-way in prose — a rule with two owners is a rule that drifts, which is the lesson of this whole slice. The chmod is best-effort for the D143 reason (a mount that will not honour a mode already reports every file executable, so git runs the hook regardless; aborting over an unenforceable permission bit is strictly worse than proceeding). *Residual, stated not papered over:* the warning rides `additionalContext`, so a headless `claude -p` clone stays quietly uncovered.

**`config.json` `secrets_required[]` — key names only, and it runs in the dry run.** Written by the `setup` checkpoint at elicitation (idempotent on the name); `rebind.py` diffs it against the store and files `required − present` as an itemized typed issue. It exists because absence is **undetectable by inspection** — an empty `secrets/` is indistinguishable from a project needing none — so without it a machine move could only ever report "the store is gone, work out what was in it". Two things the code forced: store entries are named by `message_id`, not by the credential, so "present" is derived by walking the payloads for key **names** (values read into memory, never returned, printed, or filed) — and that match is deliberately **generous**, because a missed match reports a live secret as lost (noise a human corrects) while a false match reports a lost one as present (**silence**). And because it is pure reads, unlike the bindability probe it runs in `check` too. An absent declaration is *"we cannot tell"*, not *"nothing is missing"* — the generic store-lost entry still covers the move, and `/rebind` now tells the human to backfill the names as they re-elicit. **Point-of-use fail-closed stays the floor**, restated in both `schemas.md` and the skill: a manifest can only say what *should* be there.

**The leak gate earned its keep on a real leak.** `check-no-spec-refs.sh` blocked the commit over a `D140` reference written into `rebind.py`'s new docstring — the construction record citing itself inside the shipped package. Caught mechanically, not by reading.

*Evidence:* 507 tests (445 at `e551837`, +62 here: 28 parking, 12 bindability, 11 declared-secrets, 11 pre-commit assert) + five meta-gates green; the drain's durability path re-run green across the block-machinery refactor before any new code was written; the release boundary unchanged at 54 shipped files / 18 install entries. → `11` (7b tags; Phase 7's remaining exit test is the drive), `07` (the environment class's *where* question closes; the host-limits question closes as **detect and route**), `product/scripts/{bus.py,rebind.py}`, `product/hooks/{session_start.py,pre-commit.sh}`, `product/skills/{checkpoint,planner}/SKILL.md`, `product/commands/{rebind.md,dispatch.md,start.md}`, `product/templates/{settings.json,loop.md,orchestrator-CLAUDE.md}`, `product/shared/schemas.md`.

## D145 — D144's parked mirror shipped with a migration hole, and it was the exact failure the mirror exists to end: a project that parked BEFORE the writer would publish a resume anchor naming no open checkpoint while one was open **[FIXED 2026-07-30 — found by sweeping D144's own blast radius minutes after `079e6da`; `bus.py mirror` + the `/dispatch` call; 513 tests + five meta-gates green]**
D144 gave `handoff.md` a machine-owned parked block written by `park`/`unpark`, and simultaneously told `/dispatch`
to **stop hand-writing the prose `parked[]`** on the grounds that the block covers it. Both halves are right. Their
**intersection** was not: the block is written only at a *mutation*, so an install whose checkpoint was parked
before the writer existed has a live `parked/<id>.json` and **no block at all** — and a `/dispatch` there would then
publish an anchor carrying neither. A cold start reads "nothing is parked" while a human is genuinely being waited
on. Silent, and precisely the class the mirror was built to end. `idea testing` is such an install (its setup
checkpoint was re-opened by hand during the D143 rebind, so its record predates the writer).

**Call: expose the projection as its own verb, `bus.py mirror`, and have `/dispatch` run it before writing the
anchor.** The block becomes self-healing on any install that predates it: the projection already reads a legacy
hand-written record correctly (id from the record or the filename, `summary` **derived** from
`checkpoint.request.what` when unstored, `opened_at` honestly `null`), so nothing needed migrating — only
*projecting*. Idempotent, mutates nothing in `parked/`, and leaves the prose and the drain block untouched.
**An EMPTY block is a positive statement ("nothing is parked"); an ABSENT one only means nothing has projected
yet** — which is exactly why `/dispatch` projects rather than assuming, and why `mirror` writes an empty block
rather than skipping.
**And the failure path routes rather than papering over.** If `mirror` fails, the runtime half is unreachable (that
is what `parked/` lives on), so `/dispatch` is told to say so plainly, name the open work it can still see, and send
the human to `/rebind` — *not* to hand-write a `parked[]` it cannot verify. Detectors route; none heals.

*Rejected — leaving it to the next `park`/`unpark`:* the hole is open for exactly as long as no checkpoint changes
state, which on a project blocked ON a checkpoint is unbounded — the worst possible correlation. *Rejected —
having `/dispatch` fall back to hand-writing the prose when no block exists:* that restores the second copy D144
deleted and re-opens the drift, and it asks a model to decide which of two sources is authoritative at the one
moment it has least context.

**The process note is the point.** This was caught by running D144's own blast-radius sweep *after* the commit, not
by the tests — every unit test passed, because each half is individually correct and nothing exercised a legacy
record against the new `/dispatch` prose. It is the same shape as the failures this phase keeps finding: **a
documented flow whose mechanism is not present reads exactly like a working one.** The mirror's own reason for
existing, turned on the mirror.

*Evidence:* `publish_parked_mirror` confirmed to have exactly two callers before this change (`write_park`,
`remove_park`) and none on a read path; the legacy-record projection driven in five new tests (backfill, empty
block, idempotence, prose/drain-block untouched, `parked/` unmutated) plus a CLI case; 513 tests + five meta-gates
green. → `11` (the 7b park tag records the amendment), `product/scripts/{bus.py,test_bus.py}`,
`product/commands/dispatch.md`, `product/shared/schemas.md`.

## D146 — Phase 7b DRIVEN: the matcher fires and the probe reports exactly as designed, but the machine blocks could be **terminated by their own payload** — and D144's stated `claude -p` residual turned out never to have been real **[DRIVEN 2026-07-30/31 — all four 7b items exercised on a real clone of `idea testing` + the live harness; one high-severity fix (`_render_fenced`), one false residual retracted, one finding left open for a design call; 515 tests + five meta-gates green]**
7b was built (D144/D145) and had never run. The drive was ordered cheapest-first on purpose: if the broadened
`SessionStart` matcher was wrong, item 3 never runs and **every test still passes** — the precise failure this phase
exists to eliminate, sitting inside the phase.

**1. The matcher fires, and the proof is a file rather than a context window.** D144 broadened `SessionStart` to
`startup`/`resume` against no evidence but the corroborating spellings of the existing `clear` and `PreCompact`
matchers. Driven on a scratch bootstrapped repo with `.git/hooks/pre-commit` deliberately absent: after one trivial
`claude -p`, the hook exists and is **sha256-identical** to `.claude/hooks/pre-commit.sh` (`b039658a…`); after
`claude -c -p`, likewise. The foreign arm was left byte-for-byte untouched, with the warn-once marker written keyed
to the foreign hash. Both broadened strings are real against harness 2.1.220. `--assert-hook` was driven standalone
for the first time and installs correctly.

**2. The bindability probe reported the exact D143 symptom it was built for.** On a fresh clone under `/mnt/c`
(arriving with no `runtime.json`, no runtime tree, no `node_modules`, no git hook): `RE-CREATE`, then
`bindable: NO — bash .workflow/checks.sh --check exited 1`, tail showing `tsc: not found`. The three controls all
held: the loss filed as a typed backlog issue, the **output tail on stdout and provably absent from the committed
`backlog.md`**, and idempotence-on-title real — the three pre-existing D143 loss entries were not re-filed.
`check` reports `NOT PROBED`; `--no-probe` skips the gate in 0.15s.

**3. The park→verdict→unpark seam works, and the skill's literal instructions produce a record `park` accepts.**
Driven end-to-end: a `setup` record composed per `checkpoint/SKILL.md`, piped through the quoted heredoc with a
deliberately shell-hostile body (`$`, backticks, quotes, `$(…)`) that arrived **byte-exact**; record at `0600` with
a microsecond deadline; daemon; `POST /api/verdict` → `202`; `drain.py list` **redacting** the sensitive value and
routing it to `drain.py secret`; store at `0600` with the inbox carrier unlinked; `unpark` emptying the block and
no-opping on the second call. All six refusal paths fail closed and write nothing; a dead runtime root fails closed
on both `park` and `mirror`. D145's `bus.py mirror` backfilled a block where none existed from the real legacy
record — `summary` derived, `opened_at` honestly `null`, `parked/` unmutated.

**THE FIX — a machine block could be terminated by its own payload, and the drain half is reachable from the
console.** `_block_re` matches `begin` → the **first** `end`, and `_render_fenced` emitted payload text verbatim. So
any string containing `-->` closes a comment it does not own: the *next* publish matches begin → the forged marker,
replaces that span, and strands the real block's tail as prose. The block still **looks** well-formed. Driven on
both blocks. On the parked mirror it corrupts the committed anchor with orphaned fragments that read like a live
entry. On the **drain block it is worse**: one publish took `consumed_through` from a live watermark to `null` and
destroyed the dead-letter record — every already-consumed inbox message becomes pending again, which is the
re-promoted intake / re-fired control op the consumed-set exists to prevent. **Not theoretical:** a dead-letter
`reason` is written when a verdict quotes an unknown/closed token, and **that token comes from the console**.
**Call: escape at `_render_fenced`, not per field.** `park_summary` already neutralized backticks for the sibling
hazard (breaking the ```` ```json ```` fence) — but a per-field sanitizer only ever covers the fields someone
remembered, and `dead_letters[].reason` was never one of them. The escape goes at the one place both blocks
serialize, the same **one owner** `block_markers()` gave the marker literals. `-->` becomes JSON's own `--\u003e` escape:
the decoded value is byte-identical, so nothing is hidden from a reader and nothing is lost from the record — the
payload is merely denied a literal comment terminator. *Reachable by reading?* **Yes** — `_block_re`'s `.*?` sits
three lines below `block_markers()`, and `park_summary`'s docstring enumerates one hazard and stops. It was
*found* by driving a hostile body through, and the high-stakes half only by following a free-text field.

**D144's `claude -p` residual was never real, and a false residual is the expensive kind of wrong.** D144 and D143
both state that the foreign-hook warning "rides `additionalContext`, so a headless `claude -p` clone stays quietly
uncovered". Driven, with three-state discrimination: foreign hook + no marker → the session **quotes the warning
verbatim in its rendered form** (paths substituted — a form that exists only at runtime, so it cannot have come
from reading the source); marker present → silent; a *different* foreign hook → warns again, marker re-keyed.
`additionalContext` reaches `-p` sessions. The retraction is in `session_start.py` itself, because a stated-but-false
residual invites someone to build a second mechanism for a hole that is already shut. This also drove the
warn-once-keyed-by-foreign-sha machinery end-to-end, which D144 shipped untested against a live harness.
**The standing half of the probe's coverage is confirmed too.** `apply` skips the probe on `HEALTHY` by design, so a
bound-but-unbuildable project gets nothing from `/rebind` — driven, and it is genuinely silent. What covers it is
the pre-commit block message, driven on the unbuildable clone: the commit is refused (exit 1, nothing lands) and the
message names the did-not-travel toolchain and routes to `/rebind`. It rides **git's own output stream**, which is
what actually makes it headless-visible — the claim D144 made and never measured.

**FOUND, NOT FIXED — the declared-secret diff silently depends on an undefined payload shape, and is inert in the
shape the code actually produces.** `present_secrets` derives "present" by collecting dict **keys** anywhere in a
store payload. But `drain.py secret` stores `returns` verbatim from the console verdict, and in its natural shape
(`[{id, sensitive, value}]`) the `id` is the **task** id (`runpod-credentials`), never the credential name
(`IVRIT_RUNPOD_API_KEY`) — which the skill writes into `secrets_required[]`. Driven both ways: with the shape
`drain.py secret` actually writes, **nothing ever matches** and every declared secret is reported lost on every
rebind of a machine that lost nothing; with `returns` as a dict keyed by credential name, it matches exactly.
Nothing in `schemas.md`, `checkpoint/SKILL.md`, or the console defines which shape `returns` is, so whether this
feature works is currently **luck**. D144's generosity argument still holds directionally (a missed match is noise,
a false match is silence) — but this is not a tuning miss, it is a total one, and permanent false "lost" noise
trains the human to ignore the one entry meant to be an early warning. **Left open deliberately:** the fix is to
*define* `returns`' shape, which touches `schemas.md`, the checkpoint skill and the console, and that is a design
call, not a drive fix. → `07`.

*Evidence:* three checks driven on a real clone of `idea testing` under the real `/mnt/c` mount plus the live
harness (2.1.220); the hook proven by sha256 file identity, never by a context window; the forged-marker bug
reproduced on both blocks, fixed, and **re-driven on the same clone** (one marker each, both blocks parse, watermark
intact, hostile string round-tripping byte-identical); 515 tests (513 at `f834901`, +2: one per block) + five
meta-gates green; release boundary unchanged at 54 shipped files / 18 install entries; the real `idea testing`
working tree and runtime tree verified untouched throughout. → `11` (7b tags → DRIVEN; Phase 7's exit test is
discharged), `07` (the `returns`-shape question opens), `product/scripts/{bus.py,test_bus.py,test_drain.py}`,
`product/hooks/session_start.py`.

## D147 — `returns` gets a declared shape (a **name-keyed map**), and the drive's question turned out to sit downstream of a bigger one: it had **no producer** — the console never had a setup form, so the whole credential path served a payload nothing could emit **[BUILT 2026-07-31 — the shape + the form + the exact matcher; 539 tests (515 at `7f99fd3`, +24) + five meta-gates green; the form's LOGIC is driven through node against the real validator, its RENDERING has still never been in a browser]**
D146 left one question: what shape is a `setup` verdict's `returns`? Answering it meant asking who writes one — and
**nothing did.** The console's verdict form posted `{outcome, notes}` and nothing else (no `returns`, no `tasks[]`,
no per-task outcome); `bus.py`'s verbs are `ensure|serve|stop|status|park|unpark|mirror`; `drain.py`'s three are all
consumers; and `curl`/`/api/verdict` appear in **zero** of `checkpoint/SKILL.md`, `schemas.md`,
`orchestrator-CLAUDE.md`, `commands/`. The only `returns` that has ever existed was hand-POSTed by the 7b drive,
which is precisely why it had to invent `[{id, sensitive, value}]` — **the shape was re-invented per invocation by
whoever wrote the request.** That, not matcher tolerance, is where "whether the feature works is luck" came from.

**And it was an unfulfilled promise, not an omission.** D99 specified the form as carrying `{outcome, notes,
returns?}` / plural `tasks[]` **and** rendering D98's steps + verified deep-links + breadcrumbs for `setup`. What
shipped carries none of the five; `cp.request` was `JSON.stringify`'d into a `<p>`. Increment 3 was tagged BUILT
with "the console's forms", the component **COMPLETE**, and the one stated residual was *legibility* ("nobody has
rendered the page in a browser") — so a **capability** gap read as polish. The sharpest consequence: D122 built a
second socket, a persisted second-factor token, and the structural `remote_carries_payload` boundary specifically so
credential-bearing setup verdicts could arrive from a phone over Tailscale — **guarding a payload no client could
produce.** An away human, the entire premise of the away channel, could not answer a setup checkpoint at all. Same
shape as every other finding this phase: *a documented flow whose mechanism is absent reads exactly like a working one.*

**Call 1 — the shape is a NAME-KEYED MAP: `returns: { "<KEY_NAME>": { value, sensitive?: true } }`,** at
`verdict.returns` and `verdict.tasks[].returns`. **Rejected — the candidate `name` field** on a
`[{id, sensitive, value}]` entry: task identity already lives at `tasks[].id`, so the driven shape was the wrong
*slot*, not a mis-keyed field, and bolting `name` beside `id` ratifies the collapse — two same-typed identifiers on
one entry that a composer has even odds of swapping, silent either way, which is the failure class D146 had just
fixed twice. The map has **one identifier per level**, makes multiple credentials from one task fall out as more
keys, expresses a non-credential artifact as the same entry minus the marker, and needed **zero** matcher change —
it is the shape D146 drove and found "matches exactly". *Also rejected — the orchestrator eliciting at the terminal
and writing the store directly:* it puts a live key through a context window, which `cmd_secret`'s own contract
forbids, and kills the away path outright.

**Call 2 — build the form (console increment 3b), because the alternative strands a built increment.** Per-task
rows (own outcome, so a mixed reply still routes each item on its own) with one **labelled** input per credential,
named from the request's new `tasks[].secrets[]` — never free text, so the human never hand-composes a payload and
the key can never be something they typed. Plus D99's promised `how` steps, now `[{step, url?, breadcrumb?, query?}]`,
rendered as a numbered list with live links. *Rejected — documenting the POST instead:* cheaper and honest, but it
leaves D122's credential arm permanently unreachable, and this project's standard is that a documented-but-absent
mechanism is worse than an absent one.

**Call 3 — declaring the shape FLIPS the matcher, and generosity becomes the bug.** D144's "generous because a
missed match is noise, a false match is silence" was correct *while the shape was undeclared*. `present_secrets` now
reads **`returns` nodes only** (descending, so it finds `tasks[].returns` too, rather than pinning two paths that go
blind when the envelope gains a level). Collecting every key — the old behaviour — swept in `token`/`value`/`id`/
`stored_at`, so a project declaring a credential called `token` would have **matched falsely**: a lost key reported
present, i.e. silence. The other direction is covered by the boundary instead of by tolerance — **the bus `400`s a
non-conforming `returns`**, so it never reaches the store. And **non-conformance is a separate observable, never
folded into the loss**: a store predating the declaration holds real credentials this cannot name, and reporting
those as "lost" would send a human to re-elicit keys they still have — the false-alarm habit that trains someone to
ignore the one entry meant to be an early warning. "I cannot read this" and "this is gone" are different facts.

**Three things only the code could have said.**
- **No validation error may echo a key or a value.** The commonest malformation is the *value* pasted into the key
  position — where `sk_live_abc123` sails past any credential-name regex — and the `400` body crosses the very
  plaintext edge `remote_carries_payload` exists to protect, into whatever proxy log sits between. Messages carry an
  **ordinal** (`verdict.returns entry 2`) and nothing else; a test asserts a canary never appears in any of them.
- **The poll would have wiped a half-typed credential.** `renderCheckpoints` repaints the list wholesale on every
  tick, and pasting an API key takes longer than one poll interval. **Editing wins:** the repaint is skipped while
  the list holds focus or an unsent value. This was also a pre-existing latent bug on the `notes` field that nobody
  had hit because nobody has used the page.
- **The page needed a third fact, `bus-credentials`.** The mode is binary (`loopback|remote`), but a Tailscale
  socket *may* carry a credential and reads as `remote` — so mode alone would have hidden the inputs on exactly the
  socket D122 built for. It gates only what the form **asks for**; the `403` stays the enforcement, because a served
  page must never be the thing that decides its own limits. When the socket cannot carry one, the form says so
  rather than silently omitting the inputs. (Relatedly: only `http(s)` `how` links become anchors — a
  `javascript:`/`data:` href from a loop-authored guide would run in the console's own origin, where the token lives.)

*Evidence:* the missing producer established by exhaustion (console POST body, the CLI verb list, and a zero-hit grep
for `curl`/`/api/verdict` across skills, schemas, template and commands) rather than by inference; 539 tests
(+24: 9 shape-validation, 9 console-form, 2 socket-credential meta, 3 exact-matcher, 1 full-chain) + five meta-gates
green; release boundary unchanged at 54 shipped files / 18 install entries. **The seam that broke is now tested as a
seam** — the shipped `collectVerdict` is sliced out of `APP_JS`, run through node over a DOM shim, and its output fed
to the real `bus.validate`, so producer and schema cannot silently diverge again; and a second test drives
console→`drain.py secret`→store→`present_secrets` end to end, which is the only place D146's failure was ever
visible (every link passed its own unit test while the chain was broken). `node --check` now guards `APP_JS`, since a
syntax error there ships a console that renders nothing and says nothing. **Residual, stated precisely: the SETUP
FORM has never been rendered in a browser.** The cockpit itself was (D120, headless Chrome, closing the
twice-carried residual) — but that render predates this form by six increments, and an interactive credential form
fails in ways a read-only card does not. *The sweep also caught `11` still carrying the browser-render residual on
increments 2 and 3, stale against D120's closure since it was written; repointed.* → `07` (the `returns`-shape question
closes), `11` (console increment 3b; the declared-secrets item's DRIVEN caveat discharges),
`product/shared/schemas.md`, `product/skills/checkpoint/SKILL.md`, `product/agents/setup-guide.md`,
`product/commands/rebind.md`, `product/scripts/{bus.py,rebind.py,test_bus.py,test_drain.py,test_rebind.py}`.

## D148 — increment 3b DRIVEN: the credential path held everywhere, and the **interaction shell** around it failed twice — `type="password"` handed the key to Chrome's password manager, and a sent verdict left no evidence it had been sent **[DRIVEN 2026-08-02 — every mechanical phase green in a real browser; two human-only defects found and fixed; 551 tests + five meta-gates green]**
D147 shipped the setup form and stated its residual precisely: *the form has never been rendered in a browser.* The
cockpit had been (D120), but that render predated this form by six increments, and **an interactive credential form
fails in ways a read-only card does not.** This is that drive.

**The probe that sized it.** There is no Chrome in WSL, but Windows `chrome.exe --headless --screenshot` reaches a
WSL-bound loopback port and writes a PNG that is directly readable. That carried the whole legibility half except
genuine typing — so the bed, the records, the byte-trail and every negative path were driven mechanically, and only
interaction went to a human. *Rejected — building a CDP driver:* Chrome binds its debug port to the Windows
loopback, which WSL cannot reach, and it would buy assertions the suite already makes.

**The bed, per D146's precedent:** a `git clone` of the real project to the native filesystem, the new package
installed into it, `/rebind` → RE-CREATE. Never the real install — answering the live parked checkpoint would consume
its token and unpark it for real. Verified untouched at the end: tree clean, original token, `outcome`s still null.

**What held — the entire credential path, first time, no fixes.** The render is clean (no page errors, no CSP
violations). Both graceful-degradation paths fall out of the *real* legacy record: no `tasks[].secrets[]` → no inputs,
a single-line string `how` → a paragraph rather than a numbered list. The structured `how` renders with live links
and breadcrumbs; a step with no URL degrades to its breadcrumb; **a `javascript:` URL never becomes an anchor.** The
byte-trail is sound end to end — `202` + `Location` ticket → `0600` inbox → `drain.py list` redacts the whole
`returns` node → `drain.py secret` → `0600` store + inbox unlinked — with the canary in **exactly one file in the
entire bed** and nothing staged, in `HEAD`, or in history. **D146's symptom inverted, all three ways:** all keys
present → HEALTHY and silent; drop exactly one → that one key named; a pre-declaration store → every key reported
missing **plus** the unreadable caveat stated separately. And the false-match trap D147 built the matcher flip for —
declaring `secrets_required = [token, value, stored_at, message_id, id]`, all real envelope keys — correctly reports
**all five missing** rather than matching falsely into silence. Every negative path held: the non-Tailscale socket
renders the refusal note *instead of* the inputs, a forced conforming POST there still `403`s with no canary in the
body, and malformed `returns` `400`s with ordinals only.

**What broke — both in the interaction shell, both found only by a human, neither findable headlessly.**

**Call 1 — the credential input becomes `type="text"`. D147's masking was wrong twice over.** Chrome **offered to
save the key to its password manager**, and `autocomplete="off"` cannot stop it: Chrome ignores that attribute on
password fields by design, so the prompt is unsuppressable while the field stays `type=password`. That copies a live
credential into browser-synced storage nobody asked for — the precise class of unrequested persistence the
`remote_carries_payload` boundary exists to prevent, arriving through the front door instead. The second failure is
plainer: **a human cannot tell whether a paste landed whole**, so a truncated key becomes a credential that fails at
point of use, hours later, with no clue why. *Rejected — a reveal toggle:* it fixes verification and leaves the
manager prompt exactly where it was, because the field is still a password field. Masking was defending a loopback
(or WireGuard) socket against a shoulder, while costing correctness and duplicating the key.

**Call 2 — "answered" becomes a fact the SERVER publishes (`answered_at` on the parked record).** After sending,
the console gave **no evidence at all** that the verdict had been sent. The mechanism is exact: `btn.disabled = true`
fires first, **a disabled element cannot hold focus**, the handler then clears the inputs — so both arms of
`renderCheckpoints`' repaint guard go false and the 2.5s poll rebuilds the card from its template, destroying the
"sent" flash well inside its own 6s timeout and re-arming a form that looks untouched. The card is still *listed* for
a correct reason (only the orchestrator's drain unparks it), but for a setup checkpoint "looks unanswered" invites
**re-typing a live credential onto the wire for nothing.** *Rejected — localStorage:* a verdict answered from a paired
phone would still read as open on the laptop, and it makes the page the thing that decides what it already did —
the same error `bus-credentials` was built to avoid. The parked record is the natural home: it already exists, it is
already daemon-owned, it is gitignored, and `unpark` deletes it, so the flag cannot outlive its question. **Only a
timestamp is ever written** — a stamp carrying the reply would put a live key in a second file, which is the whole
point of the parked/secret split — and it runs *after* the message is durable, so a display hint can never cost an
answer.

**Four things the drive found that are NOT fixed here, recorded so they are not re-discovered.**
- **`drain.py list` prints an unmarked `returns` value verbatim** — key *and* value — into the surface the
  orchestrator reads. The `sensitive` marker is **composer-supplied** and is the sole trigger for all three
  protections at once: redaction, the shred, and store-routing (`drain.py secret` refuses the record, so it stays on
  the durable inbox). `check_returns` accepts an unmarked entry as fully conforming *by design* — D147 made it the
  way to express a non-credential artifact — so the credential/artifact boundary now rests entirely on the composer's
  assertion. **Unreachable from the shipped form** (`collectVerdict` always sets `sensitive: true`); reachable from
  any hand-composed POST, which is exactly what the 7b drive was. → `07`.
- **`check_returns`' own docstring contradicts its contract**, promising the error "names the offending key" six
  lines above the comment explaining why it must never do that. A future editor "fixing" the terse ordinals to match
  the prose re-opens the plaintext echo the ordinals exist to prevent.
- **The request side is entirely unvalidated** — `park` accepted a request task carrying `outcome: null`, a
  reply-side `returns` map, and an invented field, while the reply side `400`s on a single unknown entry key.
  Contained three ways (`parked/` is gitignored, the mirror projects four fields, the console ignores unknowns), so
  it is hygiene rather than a credential-in-git path. → `07`.
- **`outcome` on a *request* task is noise and should stop being written.** `schemas.md` declares the request entry
  `{id, what, secrets?[]}` and the *reply* entry `{id, outcome, returns?}`; nothing in the package emits it, and the
  live record's came from the `/rebind` hand-reconstruction copying the reply shape. It is the unvalidated request
  side caught in the wild.

*Also confirmed, and worth stating because it bounds a D146 worry:* the parked mirror projects only
`{ticket_id, kind, summary, opened_at}`, so **D147's new fields never reach `_render_fenced` at all** — the escape is
not newly exposed. The escape itself was driven directly instead, with a hostile *summary* carrying ` ``` `, `-->`
and a literal `<!-- parked:end -->`: it came out as `-->` / `'''` with exactly one terminator surviving.

*Evidence:* the five phases driven cheapest-first against a cloned bed on the native filesystem; the real install
verified untouched (tree clean, token unconsumed, `parked`/`inbox`/`secrets` unchanged); 551 tests
(539 at `54e9766`, **+12** — eight `answered_at` unit tests plus two end-to-end over the real socket, which run in
both socket fixtures; and the masking test **inverted** to assert `type="text"` *and* the absence of
`type="password"`, so a well-meaning revert fails loudly). One of the eight came out of the build rather than the
drive: a ticket that parks, resolves and re-parks must re-open as **unanswered**, or the fix would produce the same
silence pointing the other way — `write_park` rewrites the record wholesale, so it does, and that is now pinned.
Five meta-gates green, release boundary unchanged at 54 shipped files / 18 install entries. *One method correction worth recording:*
the first whole-tree canary sweep used a `grep` that honours `.gitignore` and silently skipped `.workflow/` — the
`find`-based re-run is the sound evidence, and a sweep that cannot see the directory it is auditing proves nothing.
~~**Residual: the two fixes have not themselves been re-driven in a browser by a human**~~ — **CLOSED by D149**
(2026-08-02, at the keyboard: *"no chrome didnt offer to save the password"*). The render, the disabled form and the
stamp were verified here (screenshot + DOM + tests), but *that Chrome no longer offers to save the key* was a
negative only a human could confirm, and it now is. **That same re-drive found the answered card was still not
legible and that `hidden` was not hiding — see D149.** **Deadline/timestamp rendering stays raw ISO with microseconds** (`OVERDUE —
2026-08-01T19:09:35.930246+00:00`), which a human flagged unprompted as machine-facing; left open deliberately rather
than bundled. → `11` (increment 3b DRIVEN; the browser residual discharges), `07` (two new open questions),
`product/scripts/{bus.py,test_bus.py}`.

## D149 — the re-drive of D148's own fixes: the unmask is confirmed at the keyboard, and two more defects only a human saw — an answered card that was inert but not *legible*, and `hidden` that did not hide **[BUILT 2026-08-02 — D148's residual closes; +3 fixes incl. an "override" that had to be made REAL before it could be offered; 560 tests + five meta-gates green]**
D148 closed with one thing only a human could settle — *does Chrome still offer to save the key?* — and two
predictions I had no way to test. The answer came back **no prompt**, which closes the residual and confirms the
`type="text"` call. The same session found three more things, and the pattern is now unmistakable: **every defect
this increment has produced lives in the interaction shell, and every one of them needed hands.**

**Call 1 — "answer again" REPLACES the pending answer; the bus supersedes it.** The maintainer asked for a refill
button warning that it "will override the previous values". **It would have been a lie in the most dangerous place.**
Driven first: a second verdict for the same token returns `202` and leaves **two** pending records on the inbox —
nothing overrides. `schemas.md` is explicit that a re-applied verdict finds the token closed and dead-letters, so the
**first** answer is the one that wins. A human correcting a mistyped credential would have retyped it, believed it
fixed, and left the **typo** live all the way to the store. So the mechanism was built to match the promise rather
than the promise softened: a verdict now **unlinks an undrained earlier verdict for the same token**, and that unlink
**is its shred** (the superseded record may hold the live key the human just replaced). Bounded by the only window
in which replacement can be honest — once the orchestrator drains it the answer is applied, so the page stops
offering it. *Rejected — an additive refill that warns "the loop applies whichever it drains first":* cheap, and it
exposes a race to a human instead of resolving it. *Rejected — no refill at all (correction via a fresh checkpoint
when the key fails at point of use):* no new mechanism, but it strands a human who KNOWS the answer is wrong with no
way to say so. Ordering is deliberate: the new record is durable **before** the old is removed, so a failure mid-way
leaves two answers, never none.

**Call 2 — "still replaceable" is an EXISTENCE CHECK on a stamped id, not an inbox scan.** The first cut answered
"can this be replaced?" by scanning the inbox and comparing tokens — which parses **credential-bearing bodies every
2.5 seconds** to answer what is really "is that one file still there". The POST now stamps `answer_message_id` on the
parked record and the poll does `os.path.exists`. The thorough token scan stays on the **write** path, which runs
once per answer. *The split is the point:* cheap and body-free on the hot read path, exhaustive where cost does not
matter. The id is stamped even when the timestamp does not move, because the console's check reads the id.

**Call 3 — an answered card must be legible before it is touched, not merely inert.** Reported in exactly those
terms: *"it looks exactly the same… i cant do anything on the card"*. Disabling the controls made the card **behave**
answered while **looking** live, so the state read as a broken page rather than a settled question. The answered card
now dims its body, keeps a green border, and leaves the banner — and the one control still available — at full
strength. *The dimming had to exempt the re-answer control:* `pointer-events:none` on the whole card would have made
the only remaining action unclickable, which is the same "looks broken" failure pointing the other way.

**The one that would have gone on hiding: `hidden` was not hiding.** `.verdict` is `display:flex`, and **any** class
rule setting `display` outranks the `hidden` attribute's UA `display:none` — so the answered card went on showing its
notes field and Send button with the attribute correctly set. **My own DOM check had asserted `hidden` was present
and passed**, which is precisely the trap: the attribute *was* there, and the page ignored it. Only the render
showed it. Fixed once and globally (`[hidden] { display:none !important; }`) rather than per-selector, because every
`hidden` toggle on the page rode on the same assumption — the pairing section, the demo wrapper, the task block, the
steps list.

*Evidence:* the supersede driven end to end against the bed — first answer `TYPO`, replacement `RIGHT`, and after it
the inbox holds **one** record, the corrected value is what survives, `answered_at` and `answer_message_id` both move
to the new reply, and the typo'd key is on disk in **zero** files; then a simulated drain flips `answer_pending` to
false and the button withdraws. 560 tests (551 at `4ca6170`, **+9**), five meta-gates green, release boundary
unchanged at 54 shipped files / 18 install entries. *A method note worth keeping:* two of the four defects in this
entry and D148 were invisible to a DOM assertion that passed — **"the attribute is set" and "the page obeys it" are
different facts**, the same shape as this project's standing lesson that a documented mechanism is not a working one.
**Residual: the re-answer button itself has not been clicked by a human** — the supersede beneath it is driven over
the real socket and the gating is unit-tested, but the click path (re-enable → retype → send) is once again the part
only hands can close. → `08` (D148's residual marked closed), `11` (increment 3b), `product/shared/schemas.md`,
`product/scripts/{bus.py,test_bus.py}`.

## D150 — Phase 4 DRIVEN: the demo had never rendered because it structurally *could not* — an opaque origin makes every subresource read as cross-site, and the CSRF gate refused them **[DRIVEN 2026-08-02 — the first runtime validation of the demo since D124 built it; one high-severity fix; the `kind:demo` card's first browser render ever]**
Phase 4 was tagged **BUILD-COMPLETE (not yet runtime-validated)** and that was literally true: the demo had been
built (D102–D104 + D124) and never once exercised. Driving it end to end on a clean bed found the reason.

**The defect — every demo bundle with a sibling file rendered SILENTLY BLANK.** `DEMO_CSP`'s `sandbox` directive
forces an **opaque origin** (that is the whole point of D102 — isolation even at top-level, the deep-link case an
iframe `sandbox` attribute alone misses). An opaque origin is, by definition, **not same-site with anything**, so a
real browser labels every **subresource** of that document `Sec-Fetch-Site: cross-site` — which is exactly the value
`_cross_site()` fails closed on. The document navigation passed (`Sec-Fetch-Site: none`) and then `style.css` and
`app.js` both 404'd. **MEASURED, not inferred:** a header-logging server driven by the real Chrome showed the
navigation arriving `none` and both subresources arriving `cross-site`/`no-cors`.

**Call — the demo route drops the site gate (`_guard(need_token=False, site_gated=False)`), and keeps everything
else.** The gate is a **CSRF** control; CSRF is a **state-change** concern. The demo class is read-only `GET`,
token-free by construction (a browser cannot header a document navigation), and carries a throwaway low-fi sandbox
with no credential in it. Crucially the gate is not merely strict here, it is **structurally unsatisfiable**: under
an opaque origin it can never pass for a legitimate asset, so keeping it means the class is broken rather than
guarded. The **host gate** and the **realpath guard** — the two that do real work on this path — are untouched, and
the exemption is scoped to `/demo/*` (tested: `/`, `/api/state`, `/health` still refuse `cross-site`).
*Rejected — drop `sandbox` from the CSP and rely on the iframe attribute:* defeats D102's entire top-level case.
*Rejected — require demos to be a single inline `index.html`:* dodges the failure instead of removing it, and a model
authoring a demo will reach for a sibling file and get a blank page again; `create-demo`'s own format section
explicitly permits sibling assets.

**Why the test suite missed it, and why that matters more than the bug.** Every pre-existing demo test sent **no
`Sec-Fetch-Site` header at all**, so the whole class passed while a real browser showed a blank page. This is the
third instance of the standing lesson from D148/D149 — **a mechanical assertion passing is not the page behaving.**
The regression test now sends the header a browser actually sends.

*Evidence:* the full lifecycle driven on a fresh clone of `idea testing` at `~/drive-demo` (installed from
`MANIFEST.json`, `rebind apply --no-probe` → RE-CREATE). `create-demo` bundle → lint clean → park → the **`kind:demo`
card rendered in a browser for the first time** (iframe, "open full-screen", verdict form; every prior drive — D120,
D148, D149 — used setup or read-only cards, so `renderCheckpoints`' entire `cp.kind === "demo"` branch was
unexercised). Isolation **re-verified after the fix rather than assumed**, top-level in Chrome:
`window.origin=null`, `localStorage` and `document.cookie` both throw `SecurityError`, scripts running, bundle fully
styled. Routing held: `changes` → non-terminal, bundle survives, checkpoint stays open; `approve` → unpark → mirror
empties → bundle pruned (backstop `prune_demos` correctly skipped it while parked). Real working tree and real
runtime root verified untouched. → `11` (Phase 4), `product/scripts/{bus.py,test_bus.py}`.

## D151 — Phase 6's last residual DISCHARGED: the governor cycle fired, and the thing it exists to save is the state that lives *only* in the conversation **[DRIVEN 2026-08-02 — no code change needed; the plugin-staleness finding is the entry's real payload]**
The D136 governor shipped BUILT but its **cycle** had never run — the banner never fired in the D138 re-drive
because the bootstrap context law kept the window too lean to trip it. Forced and driven whole.

**It works, and the interesting half is what survived.** The banner fires at `config.context.warn_pct` and is silent
below it (driven at 40 / 74.9 / 75 / 88 through real statusline stdin). `/dispatch`, driven with a **real `claude -p`
session** in the bed, rewrote the prose whole (10677 → 5232 chars), wrote `base_sha`/`current_item`/`loop_position`,
and **preserved both machine blocks byte for byte** — D145's rule holding under a real model rather than under a
test. `SessionStart(clear)` re-injected 5810 chars of anchor and **both** of its jobs fired, the D144 pre-commit
assert installing the hook a fresh clone never gets. Then the part that matters: a session given **only that anchor**
correctly named the in-flight item, its loop node, what blocked it, the next action, the must-nots, **and a deferred
per-chunk-vs-per-N-chunks decision that had existed nowhere but the pre-clear conversation.** Carrying that across a
`/clear` is the entire point of the mechanism, and it did.

**The finding — the version-pinned no-op was ALREADY KNOWN, and that is the point.** Phase 6's own sequence line in
`11` says it outright: *"forced-reinstall the plugin to HEAD (a version-pinned `update` is a no-op — verify
`gitCommitSha` == HEAD)"*. So nothing about the mechanism is new. What this drive found is that **a known-manual
step is not a control**: the install silently drifted back to **12 commits and 17 shipped files** behind HEAD
(pinned at `b48fdc09`) with nobody noticing — a `session_start.py` with no pre-commit assert, a `dispatch.md` still
instructing the model to hand-write `parked[]`, a `bus.py` with no setup form and no supersede. `claude plugin
marketplace update` succeeded; `claude plugin update` then reported **"already at the latest version (0.1.0)"** and
changed nothing. Force-reinstall (`uninstall --keep-data` + `install`) moved it to HEAD, verified by `gitCommitSha`
and a zero-file diff. **The consequence generalizes past the maintainer's machine:** any user who installs `0.1.0`
and later receives fixes without a version bump is *told they are current while they are not*. Same shape as D143's
install missing five package files — silent staleness, here with an actively misleading message on the update path,
and the same lesson as D129: a documented manual step is not a mechanism.
**Two levers, left OPEN for a deliberate call** (`07`): bump `version` on every release that changes shipped files —
which D135 already made meaningful, since that version becomes `config.json`'s `workflow_version` and `/update` keys
on it — and/or a sixth meta-gate that refuses a release whose shipped files moved without a bump.

*Also noted, minor:* the statusline prints `ctx 75%` at 74.9% with **no** banner and `ctx 75%` at 75.0% **with** one
— the same displayed number, two behaviours. Cosmetic, but it reads as a bug to a human. *Method note:* `/dispatch`
also hit a genuinely blocked `bus.py mirror` (the bed workspace was untrusted, so `permissions.allow` was ignored)
and **degraded exactly as D145 prescribes** — said so plainly in the prose and refused to hand-write a `parked[]` it
could not verify. A rule holding under a failure it was never tested against. → `11` (Phase 6 residual), `07`.

## D152 — `returns` MEANS credential: the `sensitive` marker is deleted, not defaulted — and the request side stops accepting the reply's fields **[BUILT 2026-08-02 — both D148 open questions CLOSED by the maintainer; the leak reproduced with a canary before anything was changed]**
D148 left two questions open. Both are answered, and the first is the one with teeth.

**Call 1 — split the field (option C).** One composer-supplied `sensitive` boolean was the **sole trigger for three
protections at once**: redaction out of the surface the orchestrator reads, eligibility for `drain.py secret` (which
shreds and stores), and therefore whether the value was ever removed from the inbox. A **fully conforming** entry
that merely omitted it was printed **verbatim, key and value** — reproduced with a canary before any change, and
confirmed refused by `secret` and therefore never shredded. One nuance the original write-up did not have:
redaction is **all-or-nothing per message**, so an unmarked entry riding beside a marked one was protected by
accident; the exposure is exactly a message where *nothing* is marked. `returns` now **means credential** and the
marker is **gone**: `_is_sensitive` is structural (a non-empty `returns` is a credential), so no producer can forget
to protect a value. `artifacts` is the declared non-credential half — same name-keyed shape, validated just as
strictly, never redacted, never stored. **It has no shipped producer and `schemas.md` says so plainly**, because a
field specified as if it works while nothing can emit it is the exact defect that made the old shape a coin toss
(D147). A composer still sending `sensitive` gets a `400` naming the field and pointing at `artifacts` — that names
a **schema** key, never a credential name or value, so the no-echo discipline the ordinals exist for still holds.
*Rejected — invert the default (sensitive unless marked `false`):* strictly better failure direction and two lines,
but it keeps one composer boolean as the sole gate, which is the thing being questioned, and it forces the
annotation onto the common benign case. *Rejected — redact everything and let the marker drive only routing:* the
orchestrator legitimately needs benign values to act on, so it would need a verb that prints them — the same
exposure under another name. **The governing reason is this project's own most-repeated lesson (D129, and again in
D142/D144/D145/D147 and D150 today): derive the protection from the artifact's shape, never from a signal somebody
had to remember to send.** A composer-supplied boolean *is* the missing signal restored.

**Call 2 — the request side refuses the reply's fields, and nothing more (option B).** `bus.py park` accepted
`outcome: null`, a reply-side `returns` **carrying a value**, an invented task field and an invented top-level key,
all persisted — while `check_returns` `400`s the reply on one unknown entry key. `park` now refuses **`outcome` and
`returns` on a request task** and stays permissive about everything else. `outcome` was decided in D148 and never
built; the live record's came from a `/rebind` hand-reconstruction copying the reply half, and it reads to a later
human as though the question were already answered. **`returns` is the sharper of the two:** it carries a VALUE, the
whole `request` is handed to the console on every poll, and nothing on the request path ever runs it through
`check_returns` — so a credential pasted onto a request would reach the browser having passed no boundary at all.
*Rejected — full symmetry (declare `request`, reject every unknown):* tidiest and defensible, but **a park that
hard-fails is a checkpoint that never opens** — the machine's own way of asking for help — which is a worse failure
than an extra field. The asymmetry is principled, not lazy: the reply crosses a trust boundary from a human or a
browser; the request is composed by the loop itself. That trust simply does not extend to fields belonging to the
other side of the exchange.
**Residual — `artifacts` has no shipped producer**, stated in `schemas.md` rather than left to be discovered.
Deferred deliberately: closing it touches the setup form, the surface that broke twice in D148/D149, so it wants a
browser drive and not a mechanical pass. Queued in `11` (Space 4) to bundle with the next `align` findings.
→ `07` (both entries closed), `11`, `product/shared/schemas.md`,
`product/scripts/{bus.py,drain.py,test_bus.py,test_drain.py}`.

## D153 — the console's last two human-facing defects: an override that was offered but never wired, and machine timestamps aimed at a human **[BUILT 2026-08-02 — D149's residual CLOSED by the maintainer's own click; the regression test was checked against the unfixed source before being trusted]**
**The defect — "answer again" led nowhere, and only a human could find it.** `renderCheckpoints` attached the
send-button click handler **after** the `if (cp.answered_at)` branch, and that branch ends in `return`. So an
answered card **never got one**: "answer again" dutifully un-hid the form and re-enabled every control, then handed
back a button bound to nothing. Clicking it did nothing, forever; a reload re-read the still-answered server state
and closed the form again, which reads as *"my answer will not send"*. D149 made the override **real** on the server
and gated it correctly in the page — the one missing piece was the wire between the button and the POST. The handler
now attaches before the answered branch, which is safe precisely because that branch immediately **disables** the
button, so it cannot fire until re-answering is deliberately chosen.

**This is the fourth defect in a row that a passing assertion hid.** D149's tests asserted `disabled === false` after
the re-answer click and **passed** — because *"the button is enabled"* and *"the button does anything"* are different
facts, exactly as *"the attribute is set"* and *"the page obeys it"* were. The new test drives the **real shipped
`renderCheckpoints`** through node over a DOM shim and asks the second question, and it was **verified against
HEAD's unfixed source, where it reports `sendListeners: 0`** — a regression test that has never failed on the bug it
names is not evidence.

**Call — deadlines and answer stamps render as a DURATION, with the instant on `title`.** `OVERDUE —
2026-08-01T19:09:35.930246+00:00` made a human subtract two timestamps in their head to learn the only thing they
wanted, which is *how late*. Now `overdue by 18h` / `due in 24h` / `answered 6m ago`, with the exact microsecond ISO
one hover away (verified present in the rendered DOM, not merely set in code). **Computed client-side deliberately:**
a server-rendered relative string would either change every second and destroy the snapshot's `ETag`/304, or go
stale between polls. The server keeps ownership of the `overdue` **decision** — only the wording is derived — and a
skewed client loses to the flag rather than printing a number contradicting the badge beside it.

*Evidence:* the supersede proven by the maintainer's own hands, which is what D149's residual required — click →
retype → send, then a whole-tree audit (`find -exec grep`, because this shell's `grep` honours `.gitignore` and
would silently skip `.workflow/`): **exactly one** file in the entire bed carries the new canary, the first canary
appears in **zero**, the message id moved, and the surviving entry's fields are `['value']` — the D152 shape,
emitted by the fixed form. → `11`, `product/scripts/{bus.py,test_bus.py}`.

## D154 — "edit the spec, then regenerate" gets a floor: a refine round must MOVE THE SPEC, because approve deletes the only other copy **[BUILT 2026-08-02 — found by driving a real refine round; closes the refine cap's missing enforcement in the same place]**
Driving a real `changes` → refine → `approve` cycle with a live orchestrator exposed a rule that was prose with
nothing behind it. `create-demo` says a `changes` verdict **edits the spec first and regenerates the bundle from
it**. The drive regenerated the bundle and never touched the spec — and the orchestrator itself flagged the gap.

**Why this is severe rather than untidy: the terminal `approve` DELETES the bundle.** A decision that reached only
the demo bytes is therefore destroyed **at the exact moment it is approved**, leaving a locked spec that never
learned it. The human said yes to something that no longer exists anywhere, and the durable artifact is confidently
wrong. Silent, permanent, and precisely the decision the checkpoint existed to capture. (Concretely: the maintainer
asked for "a unique icon beside every speaker name", approved it, and the spec would have locked with no mention of
icons.)

**Call — the refine ledger records the spec each round was generated FROM, and `check_demo_bundle.py` enforces it.**
`.refine.json` grows from `{round: N}` to `{ round, rounds: [{ round, spec_ref: { path, sha256 }, note? }] }`, and
the lint — which already runs before every park — refuses a round whose `spec_ref` is missing, whose **latest** hash
does not match the spec on disk, or **whose hash is unchanged from the previous round**. That last one is the actual
rule: a regeneration that did not move the spec is refused. The hash is chosen precisely because it is **the one
thing a producer cannot satisfy by remembering to set a flag** — the same reasoning that retired the `sensitive`
marker in D152. Only the latest round is pinned to current bytes; earlier rounds legitimately describe superseded
revisions, and requiring all of them to match would make every later edit retroactively invalidate the history.
`spec_ref.path` is repo-relative because **a brownfield project's adopted spec is not `docs/spec.md`** (the drive bed
carries `docs/product_specs.md`, per D39/D50/D130's never-clobber rule).
*Rejected — strengthen the prose:* prose is exactly what failed. *Rejected — a self-reported `spec_updated: true`
flag:* a boolean the composer sets is the D152 marker wearing a different hat.

**The same change closes a finding surfaced during the D150 drive:** `config.demo.max_refine_rounds` lived in
`schemas.md` and `create-demo/SKILL.md` and **no code read it**, so the circuit-breaker depended on a model
remembering to increment a counter and compare it. The lint now refuses a `round` over the cap and names the
escalation (`discuss`), and an unreadable or malformed ledger **blocks** rather than passing quietly.
`.refine.json` also gains a `schemas.md` owner — it was a live on-disk artifact with no declared shape, which is the
same class of gap D147 was about.

*Evidence:* 11 new lint tests including the exact defect (a round that did not move the spec), the superseded-revision
case, the cap with a configured and a defaulted value, and junk config falling back rather than crashing. The
approved icon decision was folded into the drive bed's real adopted spec before the lock, which is what the recovery
looks like when this fires.
**Residual — the floor is forward-only.** Nothing checks specs locked *before* it existed, and nothing can: the
terminal `approve` already deleted the bundle, so there is no artifact left to diff a locked spec against. That
makes detection a judgment pass over the spec and the item's history rather than a gate — which is what `align`
already is. Queued in `11` (Space 4) to bundle with the next `align` findings, deliberately **not** as a new gate.
→ `04`, `11`, `product/shared/schemas.md`,
`product/skills/{create-demo,checkpoint}/SKILL.md`, `product/scripts/{check_demo_bundle.py,test_check_demo_bundle.py}`.

## D155 — The post-Phase-7 cold audit's four judgment calls: `align` gains the lens it was already credited with, the spec is ONE file, a mis-routed residual is re-queued, and Phase 8 is release discipline **[DECIDED 2026-08-03 — the audit is the evidence; only the `align` lens is a package change, the rest are ownership + sequencing]**
The **D89 tier-3 phase-boundary cold audit** ran over the 46 commits (**D114→D154**) since the pre-Phase-3 pass —
the whole console/bus build, the demo + release surface, and Phases 5/6/7, none of it previously cold-audited.
Thirteen doc↔artifact drifts were auto-fixed under the audit's autonomy contract; **four judgment findings were
logged, not resolved** (`reviews/post-phase7/`). This entry resolves all four.

**The audit's own headline, because it is the reason three of these four exist:** ten of the thirteen auto-fixes
were **one shape repeating** — a decision retired a mechanism and the D80 blast-radius sweep reached the primary
surface but not the terse ones. Two were in the **shipped** package and worse than cosmetic: `schemas.md`
contradicted **itself** about the `sensitive` marker D152 deleted (four sites still told a producer to set one,
which `bus.py` `400`s — a doc that *induces* a defect), and `05`'s layout tree, which **D114 made the owner** of
every `.workflow/` path's commit-class/`bus:`/`pin`, was missing two paths that landed after it
(`install-set.json` D139, `statusline.delegate` D136) — because `check_enum_coherence.py` holds *listed* rows to
their consumers and **cannot see an absent row**. D114's own failure mode, one layer up. The tier-2/tier-3 split
held exactly as D89 predicted: all five gates were green before and after, because every finding lived in prose.

- **JF1 — `align` was NAMED the detector and never GIVEN the lens.** D154's residual is forward-only (a terminal
  `approve` deletes the bundle, so nothing can diff a spec locked before the refine ledger existed) and `11`
  queued it here with "`align` is the natural detector, not a new gate". But `align`'s standing checks were
  exactly two, so **running the pass as shipped did not perform the detection `11` says it performs.** That is
  D117's lesson recurring verbatim: *a rule that lives only in this repo's log is not a rule the consumer
  follows.* **Call — a third standing lens in `align` step 3, the "approved-demo" lens:** for an item whose
  history shows a terminal demo approval with an absent ledger, read its `spec` slice against its own checkpoint
  request, verdict `notes` and commit history, and flag an agreed change the spec does not carry. **A read, not a
  gate** — there is nothing left to diff, so it can only ever be judgment; a hit leaves as an ordinary ticket at
  the element's `commitment`. It is **bounded by construction**: the set is finite and historical (new rounds are
  lint-gated), and the existing findings-register dedup stops a cleared item being re-flagged every scan — reuse,
  not a new piece of state. *Rejected:* a new gate (there is no artifact to gate on); a per-project "backfill
  done" flag in `anchor.json` (accretes state the register's dedup already provides).
- **JF2 — `artifacts` has no producer, and was queued to a process that CANNOT close it.** Verified still true
  and still honestly disclosed in `schemas.md`, which is the property D147 established. The real defect was the
  **tag**: `[fix-later — bundle with the `align` pass]`. This pass proved a coherence sweep can only confirm the
  disclosure is honest — closing it is a build touching the setup form, the surface that broke twice at human
  hands (D148/D149), so it wants a browser drive. **Call — retag `[stageable — a BUILD needing a browser
  drive]`** and take it off the align queue. *A queue entry routed to a process that cannot discharge it is
  exactly how the D136 governor residual sat stale for six decisions* (`11`'s own lesson). **The field stays
  declared despite the gap** — it is what lets `returns` *mean* credential, so deleting it re-opens the D152 hole
  (a composer with a non-credential value and nowhere to put it puts it in `returns`, and it is shredded into the
  secret store). *Rejected:* removing `artifacts` until something emits it; building it blind here (tagging BUILT
  against an undriven surface is the D147 defect itself).
- **JF3 — `docs/spec/` (dir) vs `docs/spec.md` (file): genuinely two owners, now one.** `schemas.md` (the owner of
  artifact shapes) said the file; `05`'s tree, `memory-model.md`, `start.md` ×2 and `11` said the directory.
  **Call — `docs/spec.md`, ONE file, is canonical**; the five directory sites are repointed. The decisive argument
  is mechanical rather than aesthetic: **D154's `refine-ledger` hashes exactly one file** (`spec_ref: {path,
  sha256}`), so a directory spec would silently weaken the newest floor — there would be no defined thing to hash.
  Corroborating: the one real brownfield drive (D130) produced `docs/spec.md`, two shipped tests assume it, and
  D154's own prose already reasons about "`docs/spec.md`" as the greenfield name. The brownfield case is
  **unaffected and stays first-class**: an adopted spec keeps its own name (D39/D50/D130 never-clobber), which is
  precisely why every reference is a *recorded* path and `spec_ref.path` is free-form. *Rejected:* a `docs/spec/`
  directory with `spec.md` as its entry (buys nothing today and needs a tree-hash rule to keep D154 coherent).
- **JF4 — Phase 8 = release discipline FIRST, then the interaction-model rework.** `11` is the declared owner of
  "what's left" and, after Phase 7 closed, **named no successor** — its next-slice pointer had named the completed
  Phase 5 for three phases (auto-fixed as A13). **Call — open Phase 8 with D151 (8a) ahead of async chat (8b).**
  The argument is that 8a is the only open item that **harms a real installed user today**, and it was *measured*:
  the install had drifted 12 commits / 17 shipped files behind — including the `SessionStart(clear)` rehydrate, so
  a `/clear` dropped into an empty session — while `claude plugin update` said *"already at the latest version
  (0.1.0)"*. `11` already prescribed a manual force-reinstall, and **the drive is the proof the manual step did not
  hold**; a control nobody runs is not a control. Both D151 options are taken, because the second makes the first
  un-forgettable: **bump `version` on every shipped-file release** (the same lever twice — D135 makes that value
  `config.json`'s `workflow_version` and `/update` keys its migration on it) **and a sixth meta-gate in
  `build-release.py`** refusing a release whose shipped set moved without a bump — `check-status-coherence` applied
  to the ship boundary, the `install-set.json` pattern one level up. Async chat's blocker *has* cleared (D132
  parked it behind a re-drive; D138 ran one), so sequencing it second is a deliberate scheduling call, not a
  dependency: **shipping a large new surface onto a fleet that cannot learn it is stale multiplies the very problem
  8a exists to fix.** *Rejected:* declaring the sequence closed and running purely `[stageable]`-driven (leaves the
  status owner unable to answer its one question); leading with async chat (the biggest feature is not the most
  urgent); a self-hosting/dogfooding slice first (wants the project-state view, still `[stageable]`).

*Rejected across all four:* resolving any of them **inside** the audit commit — the D89 contract exists so a
detection pass cannot quietly become an authority, and it held (the audit shipped 13 mechanical fixes and zero
judgment calls; these four arrived only when the maintainer asked for them).
*Evidence:* `reviews/post-phase7/doc-review-register.md` (the full pass — base `3fb93dd`, HEAD `9d13b3c`, 46
commits / 105 files, method + every finding re-verified against its artifact); five meta-gates green before and
after; 584 tests green across both commits (prose-only edits, which is what proves they changed no behaviour).
Reuses **D89** (the tier-3 ritual + the three-tier split), **D80/D114** (one owner per fact; the tree's ownership),
**D152/D154** (the retired marker; the refine ledger), **D147** (a field that cannot be emitted), **D151** (the
staleness measurement), **D117** (a rule the consumer never receives). → `05`, `07`, `11`, `reviews/post-phase7/`,
`product/skills/align/SKILL.md`, `product/shared/memory-model.md`, `product/commands/start.md`.

## D156 — `artifacts` gets its producer: the request declares `provides[]`, and the two halves of the exchange share no key name **[BUILT 2026-08-03 — D152's residual CLOSED; the tests were proven against the unfixed source, but the form itself is NOT yet browser-driven]**
D152 split the setup reply in two — `returns` **means** credential, `artifacts` is the non-credential half — and
shipped the second half **declared, validated, and unproducible**: the console's setup form renders one input per
declared `request.tasks[].secrets[]` name, and `secrets[]` means credential, so the form could only ever emit
`returns`. It was disclosed in place rather than left to be discovered, which is the property D147 established, but
a disclosure is not a producer. D155 (JF2) retagged it off the `align` queue as a build; this is that build.

**Call — a request-side `tasks[].provides[]`, the exact mirror of `secrets[]`.** Same labelled row, a different
input class (`.avalue`), a different reply field (`artifacts`). Two declared lists, never one list with a flag:
**which list a name was declared in is what decides the value's protection**, and that is a property no composer can
forget to set. *Rejected — typing the existing declaration (`secrets[]` becoming `[{name, kind}]`):* one array, no
new field, and disqualifying — a composer-supplied `kind` deciding whether a value is shredded is the deleted
`sensitive` marker wearing a different hat, and it breaks the load-bearing sentence "`secrets[]` *means*
credential". *Rejected — leaving it declared-and-disclosed with a test pinning the disclosure:* zero cost, but it
buys no capability and guards prose.

**The name is the sharp part, and the roadmap's own phrasing had it wrong.** `11` proposed a request-side
`artifacts[]`. But request and reply deliberately share **no** key name — the request declares NAMES to ask for
(`secrets[]`), the reply carries VALUES (`returns`) — and that non-overlap is the *only* reason `check_request_tasks`
can refuse a reply-side field on a request at all (D152 call 2). Reusing `artifacts` on both sides would make one key
mean "a list of names" outbound and "a map of values" inbound, and would forfeit that refusal permanently. Hence
`provides[]`.

**A capability, not just a gap closed.** The `provides[]` inputs are **not** gated on the credential-socket check.
That gate exists to keep secrets off a socket that may not carry one; a webhook URL is not a secret. Until now a
paired **remote** console could answer a setup task with an outcome and *nothing else* — the first thing it can hand
back is this.

**Two traps the surface had waiting**, both of the class that broke it under human hands twice before: the repaint
guard latches on any non-empty input, so `.avalue` had to join it (and had to be cleared on send, or a left-behind
artifact freezes the whole list at its last painted snapshot); and the answered/re-answer disable sweeps needed it
too, or a re-answered card hands back a live input beside dead ones. *Evidence:* six tests drive the **real shipped**
`renderTasks`/`collectVerdict` through node and feed the output to the real validator — the artifacts-only reply is
asserted **not** sensitive (it must not be shredded), a credential and a provided value in one task are asserted to
land in different fields, and `renderTasks` is driven with the credential socket **refused** to prove the
non-credential input still renders. **Five of the six were run against HEAD's unfixed source and fail there**; the
sixth is a negative case that passes trivially, and is kept as a guard rather than as evidence.
**Residual — not browser-driven.** Everything here is a node-over-DOM-shim drive plus the validator. The surface's
own history (D148/D149/D153) says a shim answers "does the code do X", never "does the page do X" — so this lands
**BUILT, not DRIVEN**, and `11` carries it as needing one browser pass on both sockets.
→ `11`, `product/shared/schemas.md`, `product/skills/checkpoint/SKILL.md`,
`product/scripts/{bus.py,test_bus.py}`.

## D157 — the refine ledger survives the delete: `--promote` writes a committed approvals file, and `align`'s approved-demo lens gets the discriminator and the scope it was missing **[BUILT 2026-08-03 — closes D154's residual for real; corrects D155's JF1, which shipped a lens that could not fire]**
D155 gave `align` the approved-demo lens D154's residual had been queued to. Reading the shipped lens against the
shipped mechanics **before relying on it** found it could not perform the detection it was credited with — the same
failure JF1 itself named, one level in.

**Defect 1 — the entry condition is a tautology.** The lens fires on "a terminal demo approval with an **absent
ledger**". But `.refine.json` lives *inside* `demos/<item-id>/`, and the terminal `approve` **deletes that
directory**. After any approval the ledger is always absent, so the condition is true of **every approved demo item,
forever** — it cannot separate a pre-floor item from a post-floor one, and the set is unbounded rather than "finite
and historical" as D155 claimed.
**Defect 2 — a standing check inside a scoped pass.** Step 3 runs only over the work-list step 1 builds from the
diff since the anchor. A historical item has no diff, so it never enters the work-list: the lens was scoped out of
ever seeing precisely the items it exists for.
**Defect 3 — nothing clears a clean item.** D155 leaned on the findings register's dedup, but the register dedups
**findings**, and a clean read produces none. Every passing item would be re-read on every scan forever — a budget
leak in the one pass that is budget-bounded.

**Call 1 — promote the ledger instead of destroying it.** `check_demo_bundle.py --promote <bundle>` folds
`{item_id, approved_at, rounds, spec_ref}` into a committed **`.workflow/demo-approvals.json`**, and `checkpoint`'s
demo route runs it **immediately before** the delete. Ids, a count and a hash — no bytes, no values. An item **with**
an entry is settled mechanically (the lint already refused any round that did not move the spec); an item **without**
one was approved before the floor existed, and that set is finite and shrinks to nothing. Idempotent on `item_id`,
because applying a verdict is itself re-appliable after a crash and two entries would later read as two approvals.
This also repairs something already true: the approve path *already* read the ledger before deleting it and left no
evidence it had — a load-bearing check that records nothing is indistinguishable from one that never ran.
*Rejected — dating items against the package version that processed them:* no per-item version stamp exists, and
inventing one to answer a question a three-line ledger answers is the wrong direction. *Rejected — accepting the
gap and retiring the lens:* defensible today (nothing has been released, so the pre-floor set is plausibly empty
everywhere but the maintainer's own bed) and rejected anyway — it is the disclosure-instead-of-mechanism move this
project keeps punishing, and it would forfeit the forward half, where a *missing* promoted entry now also catches a
round that bypassed the lint.
**Call 2 — scope admits the backlog where scope is decided.** Step 1 now also admits every item with a terminal demo
approval, no promoted entry, and no place in the anchor's `cleared_demo_items[]`. Putting the exception in the
scoping step rather than letting a lens quietly read outside its own work-list is what keeps "the work-list is the
only thing the semantic pass looks at" true.
**Call 3 — a clean read is recorded.** `anchor.json` gains `cleared_demo_items[]`. Only a *clean* read clears an
item; one that produced a finding stays in the backlog until the ticket closes it, because the ticket, not the scan,
is what resolves a finding. *This is the state D155 explicitly rejected adding* ("accretes state the register's dedup
already provides") — the rejection was wrong on a fact: the register cannot dedup an absence.

*Evidence:* seven tests over the real promote — the last round's `spec_ref` outliving an `rmtree` of the bundle, a
round-0 approval recording an honest `null`, promote-twice replacing rather than duplicating, a torn approvals file
being replaced rather than propagated or wedging every future promote, and no temp file left behind.
*The pattern worth naming:* this is the second residual in two decisions routed to a process that could not
discharge it (D155/JF2 was the first). "Queued to `align`" reads as *filed* when it is often *parked*.
→ `11`, `product/shared/schemas.md`, `product/commands/start.md`,
`product/skills/{checkpoint,align}/SKILL.md`, `product/scripts/{check_demo_bundle.py,test_check_demo_bundle.py}`.

## D158 — the plugin version tracks RELEASES, not pushes; the maintainer's stale-install problem gets its own mechanism **[DECIDED 2026-08-03 — settles the cadence half of Phase 8a before it is built; one meta-script shipped nowhere]**
A question about what "being on the plugin marketplace" means surfaced a conflation worth settling in writing,
because two different staleness problems were being treated as one.

**What the marketplace actually is, stated once so it stops being re-asked:** there is no central Anthropic
directory and this package is not listed in one. A "marketplace" is *a repo containing
`.claude-plugin/marketplace.json`* — so "being on the marketplace" means only that **this repo is addressable as a
plugin source** by someone who already knows its name. Nothing is published, reviewed, or discoverable, and nothing
on any server can go stale. The only thing that goes stale is **the copy in an install's cache**. There is therefore
nothing to withdraw or gate on stability, and removing the manifest would break only the maintainer's own install
path.

**Call — the `version` in `plugin.json` moves once per RELEASE that changes a shipped file, never per push.**
*Rejected — a pre-push hook that bumps whenever a manifest file moved:* it would keep every cache fresh and it
destroys what the version is *for* — D135 makes that value `config.json`'s `workflow_version` and `/update` diffs
its whole migration against it. A version that moves five times a day is not a migration key, it is a commit
counter. Phase 8a's per-release bump plus the sixth meta-gate stands unchanged.

**Call — the maintainer's loop gets a mechanism instead: `scripts/dev-reinstall.sh` (meta-only, never ships).**
Uninstall-then-install from the working tree, printing the roster and the source sha it just installed. `11` already
prescribed a manual force-reinstall before a drive, and **D151 is the proof the manual step did not hold** — the
install sat 12 commits and 17 shipped files behind while `claude plugin update` reported the latest version. The
same rule the product applies to itself: a documented step nobody runs is not a control. The two halves are
deliberately different in kind, and that is the whole point — a **released user** has no working tree to reinstall
from, so their fix must be the version bump and the gate that refuses an un-bumped release; the **maintainer's** fix
must be that the version is irrelevant.

*Worth stating because it changes the priority argument for 8a:* the user harmed by a stale install today is the
maintainer, on the machine the package is tested on. So 8a's payoff is not mainly "future users get updates" — it is
that a test drive stops silently running commits-old code and attributing the result to HEAD. That is a correctness
argument about the project's own evidence, and it is stronger than the user-facing one D155 promoted it on.

## D159 — The chain-forecast: a pre-execution routing forecast over the EXISTING loop, surfaced as a new judgment checkpoint kind **[DESIGNED 2026-08-03 — Phase 9a; unbuilt. Answers the maintainer's "show me the chain of events before you walk it"]**
The maintainer wanted, before a large change, to *see the chain of events the loop proposes* — "orchestrator launches
research → figures out the current implementation → proposes a plan → executes → human QA here → testing…" — with each
event's probable outcome and its fallback, so he can view / question / modify it, front-load the human gates he can
answer up front (e.g. hand over a credential now instead of at the blocking step), and afterwards watch reality unfold
against it. Nothing today produces this: `planner` decompose gives a roadmap of **work units**, plan-one gives **code
steps** — neither forecasts the loop's own **routing**.

**Call — a forecast of the loop's routing, generated cheap and read as conditional, surfaced as a checkpoint.**
- **A `/create-forecast` command** (the explicit human trigger on big work, the exact sibling of `/create-demo`) **+ an
  orchestrator self-invoke gated on the D69 proportional-rigor triage** (high blast-radius × hard-to-reverse →
  auto-forecast; not a vibe). The forecast reads the **indices** — `graph.json` + the spec + `loop.md` — and applies
  the loop's *own* trigger rules **without firing them** (planner declares a `human-qa` criterion → a qa checkpoint is
  predicted; `spec.integrations[]` or an execute-discovered step → setup; the sandbox gate → demo; a decision with no
  recorded answer → `decision-engineer`→`research`). That is what makes it **smart yet cheap** — it predicts the
  trigger, it does not resolve it; it forecasts the territory from the map, it never does the work.
- **Every event NAMES a real `loop.md` node** — the forecast is a *prediction over the existing graph*, not a second
  graph, so `check_contracts.py` can lint that every event resolves (D80: one routing owner).
- **Branch points are explicit but bounded.** A branch earns a node only where the *human would do something different*
  (pre-supply a credential, pick a 4a/4b integration path, decide a qa is worth their time). `verify → succeeds: X |
  fails: debug` is shown once as "this step self-corrects"; it is **not** recursively unrolled into every
  verify→debug→refine cycle, which would redraw `loop.md` per-item and drown the signal.
- **Surfaced as a judgment checkpoint** (D96 taxonomy) — `{outcome: approve|changes|reject, notes}` parked on the bus
  like a demo. `changes` re-forecasts with the edits; `approve` **freezes** it. Reuses the token/deadline/away-alert/
  drain/"my requests" machinery whole — no new inbox kind. **The framing: `create-demo` de-risks the PRODUCT question
  ("did we agree *what* to build?"); the forecast de-risks the PROCESS question ("did we agree *how* the machine will
  proceed?") — the same pre-plan intake primitive on an orthogonal axis** (D21/D22 set the precedent of a checkpoint
  that fires pre-plan at intake).
- **The front-loading superset over D97** — D97 bundles foreseeable setups *within-plan at first-contact*, deliberately
  not front-loaded, to avoid pestering. The forecast **front-loads the ELICITATION, never the VERIFICATION**: a
  predicted setup surfaces as an optional pre-fill ("this chain needs `IVRIT_API_KEY` at event 5 — hand it over now, or
  be asked then"); if provided, event 5 finds it in the secret store and skips the *asking* but **still runs D97's
  machine-verify probe** (a key handed over 40 minutes early can still be wrong). A strict superset of D97, not a
  reversal — which is why D97's within-plan bundling stands unchanged for everything not pre-supplied.
- **Reality is DERIVED, and a structural divergence re-forecasts.** The frozen forecast renders beside a reality column
  computed from `state.json` + `git log` + the item `changelog` (never a rewrite; the "my requests" pattern of
  resolving off per-effect anchors — D108/D119). An event that unfolds as predicted just fills in; a **structural
  divergence** — an event that was never forecast (D37's structural tier) — does not silently continue: it re-forecasts
  the tail and re-shows. The forecast also **marks its own blind spots** ("beyond event 6, unforeseeable — do not read
  this as unattended"), because execute-discovered needs are unforecastable by definition (`align`'s honest-truncation
  rule: a silent cap reads as "all clear").
- **Loopback-only (Socket B).** A forecast is *more* authoritative than a verdict — it is a whole execution plan, and
  D90 makes an approved one drive the agent — so it never rides the reduced remote surface (D112).

*Rejected:* a **new routing graph** the orchestrator follows *instead of* `loop.md` (two routing owners = the drift
D80 exists to kill; the forecast names existing nodes); a **new inbox `kind`** (it is a checkpoint verdict — reusing
the kind buys the whole park/resume/away stack free); **unrolling every mechanical edge** (rebuilds `loop.md` as a
per-item state machine — branch only at decision-meaningful points); reversing **D97** to front-load verification (the
elicit-early/verify-at-the-gate superset gets the away-run benefit without dropping the probe that catches a wrong
key); riding the **remote** surface (an approved forecast is agent control — D112). *What is binding about an approved
forecast is NOT the sequence* — it is the corrections made reviewing it (which land as ordinary spec edits / decision
records) and the human gates it front-loads; deviation is a divergence event, which `execute` already has the
vocabulary for (D37), not a failure.
*Reuse:* D96/D97 (checkpoint taxonomy + verb-enum verdict + the setup probe), D69 (the self-trigger's principled gate),
D21/D22 (`create-demo` — the pre-plan intake-checkpoint precedent + the de-risking framing), D37 (divergence tiers),
D108/D119 (derived "my requests" anchors), D112 (loopback = authoritative), D80 (single routing owner + `check_contracts`).
→ `04`, `09`, `11`, `07`.

## D160 — The context-budget law: a mechanical doc-size gate extends the retention/read law over PROSE **[DESIGNED 2026-08-03 — Phase 9b; unbuilt. The enforcement the "bounded by construction" claim never had]**
The maintainer asked what currently ensures no context-loaded file exceeds a sane size and periodically flags one that
does. The answer is **nothing**: `memory-model.md` *asserts* "always-read files are bounded by construction," and there
is **no mechanical check anywhere** that holds it true; `retention.py` (D71) caps the append-only tier (`# Sessions`)
and nothing else. The claim is enforced by hope — and this repo is the counter-evidence: `11-roadmap.md` (767 lines)
**paged at the 25 000-token Read-tool ceiling** during this very session, in the file whose product is meant to prevent
exactly that.

**Call — a role-tiered, token-measured, mechanically-enforced budget, built ON the retention law, not beside it.**
- **A mechanical check `check_doc_budget.py`** token-counts every workflow-owned doc against its **role budget** and
  runs (a) in `checks.sh` (cheap, decidable, always-whole) and (b) as a **third maintenance item `prioritize` injects
  on a threshold — decoupled** from retention (memory pressure) and `align` (drift risk), the same shape those two
  already use. This *is* the maintainer's "the orchestrator flags it by itself periodically."
- **Budget by ROLE, in TOKENS, not lines** (model-window-agnostic, the same reason `warn_pct` is a percentage — D136):
  - **always-loaded** (`CLAUDE.md` brief, `loop.md`) → aggressive: the community ~200-line / sub-1k-token target, because
    every token is rent paid *every turn, every session, before a word is typed*;
  - **on-demand context** (a spec doc, a `rules/*.md`, a knowledge node) → **the 25 000-token Read ceiling is the HARD
    wall** (a file over it *mechanically cannot be loaded in one call* — enforcement that is a failure, not advice), with
    a softer advisory flag below it (schedule a trim before it becomes a wall).
- **Over-budget → a TICKET** (trim / split / distill), never auto-mangle. The **prose arm** is the one genuinely new
  mechanism: you cannot drop half a spec doc to git like a `# Sessions` entry — splitting prose coherently needs
  judgment — so an over-budget prose file routes to a **split-and-pointer** (lean current-state file + archived-detail
  file + a head marker), mirroring retention's existing Sessions marker. This repo already does it by hand (roadmap =
  status, git = history); the product just never made it a rule.
- **It does NOT re-check truth.** `align` owns "is this doc *wrong*"; the budget gate owns "is this doc *too big*" — two
  owners, no overlap (D80). Building a second truth-checker was the trap.
- **Un-defer Sessions distillation** (deferred at D61; D88 already holds "distill a postmortem to a one-line lesson
  *before* drop"). The best-practice finding that **compression beats raw retention** is the evidence to build it now —
  it is the prose/log arm's real answer, better than tuning "keep last N."

*Numbers (researched, tiered — there is no single constant):* **25 000 tokens** = the Read-tool hard ceiling (the
enforcement point); **~40 KB** = Claude Code's own `CLAUDE.md` performance warning; **~200 lines / <1k tokens** = the
community target for an always-loaded brief. Derive the shipped defaults by measuring the repo's own files, not by
citing a number.
*Rejected:* an **"every X turns" trigger** (turns are not durable — a `/clear` resets them and the away-runner spawns a
fresh `claude -p` per ticket with no turn history; use item/commit boundaries like retention/`align`); a **second
truth-checker** (D80 violation — `align` already classifies + routes); a **single best-practice max size** (none
exists; budget by role in tokens); **auto-trimming prose** (needs judgment → ticket + split-pointer). *Corrections
folded from the discussion:* trigger on boundaries not turns; do not duplicate `align`.
*Reuse:* D59–D61/D71 (the retention/read law + `retention.py` + the maintenance-item injection pattern), D80 (single
owner), D88 (distill-to-lesson-before-drop), D136 (`warn_pct` = percentage-not-token precedent). Research: Claude
Code #4002 (25k read ceiling), #2766 (40KB `CLAUDE.md` warning), context-rot / compression-beats-retention (2026).
→ `05`, `06`, `product/shared/memory-model.md`, `11`, `07`.

## D161 — Org mode: the third `/start` mode — a private-tree brain over a read-only company checkout, ZERO footprint, human-only git **[DESIGNED 2026-08-03 — Phase 9c. ⚠ PARTLY SUPERSEDED BY D174 (BUILT + DRIVEN 2026-08-05): the goal, the deltas and the drive protocol below all held, but the TOPOLOGY did not — `project_root` is **`.`** (the brain IS the private clone), not "an absolute path to the checkout", and there is no third `project_root` value. **Ground on D174 before building on this entry.** Reframes the maintainer's "project repo vs docs repo"]**
The maintainer wants to run the workflow against a **company product he does not own** — where the docs/rules/knowledge/
machinery the workflow generates "cannot by any means be included in the org's repo, not in a sandbox, not in testing,
definitely not in prod," where **coworkers change the product independently** so the workflow must be able to re-align
on demand or on every push, and where the whole thing is **optional** (a solo dev pays its cost for no benefit). His
first framing — a "project repo" vs a "docs repo" — is the wrong cut and he set it aside.

**Call — two working trees + a private brain; `config.org` (absent ⇒ inert, like `config.remote`/`config.runner`); a
third `/start` mode beside greenfield/brownfield.**
- **The user's checkout** — the normal company clone. **The workflow touches it never** (reads nothing, writes nothing,
  adds no `.claude/`, no `.workflow/`, no `docs/`, not even a `.gitignore` line). **Zero footprint IS the leak
  guarantee** — there is nothing in the checkout to leak, so no gitignore mistake can expose anything. Stronger *and*
  simpler than the rejected orphan branch.
- **The workflow's private tree** (on the workstation) holds the entire brain: the `CLAUDE.md` brief, `.claude`
  scripts/hooks, `.workflow/`, and `docs/` (spec + decisions + knowledge + graph). **`claude` runs from here**, and
  **`project_root` = an absolute path to the checkout** — the third `project_root` value (greenfield `./project`,
  brownfield `.`, org = an external absolute path). The relocation precedent already exists (D114/D115/`rebind`).
- **A private clone of the product code inside the brain, with no write-remote to the company** ("Reading A", the
  maintainer's choice): the loop commits **freely** there as its resume ledger (D48 intact), and those commits
  **physically cannot reach the company** (no remote to push to). Its output is a **reviewable branch/diff** the human
  pulls into *their* checkout, reviews, and commits + pushes **themselves**. "User and user only" is enforced
  structurally, not by discipline.
- **Sync (the maintainer's "align on every push"):** the private clone `git fetch`es company `HEAD` **read-only**;
  `align` reads drift off `FETCH_HEAD` vs a **`describes_sha`** stamp (every knowledge snapshot records the company
  `HEAD` it describes) — so **org-align is existing `align` with a different anchor + diff-base, not new machinery**. A
  coworker's push is the ordinary drift case with a bigger diff (already budget-capped + honestly-truncated). A
  **non-trivial upstream conflict is the human's to resolve** (a checkpoint), never an autonomous merge — detection is
  not resolution, and the human applies the bundle anyway.
- **The absolute outward boundary:** in org mode the loop writes **no company-visible surface** — not `main`
  (`guard.sh` push floor → absolute deny, D110), not the tracker, not the repo's hooks. `guard.sh` is where the push
  half already lives; the issue-create half belongs beside it.

**Org-brownfield is mostly brownfield-minus-footprint** (it reuses `ingest`/codemap/reconcile wholesale — D68/D130 —
which de-risks the build). The deltas, all gated on `config.org`:
- *Does less (footprint-avoidance):* no install into the checkout · **never edit the company `CLAUDE.md`** (read-only
  as the ingest intent-seed, never inject the managed block) · **no git hooks in the checkout** (they would fire on the
  user's & coworkers' own commits) · **`create-issue`/`close-issue` go LOCAL-ONLY** (never `gh issue` the company
  tracker — the roster's from-anywhere side-door is the sharpest leak; `prioritize`'s GC on a no-`github_ref` issue,
  D142, already supports it) · no `.gitignore` edit · **do not adopt the company's existing secrets** · **ingest gates
  run read-only** (never the company's full test suite — a real deferred brownfield hazard, D130).
- *Does more:* the read-only upstream sync; the remote-less private clone; **the review-bundle producer** — the one
  net-new capability (the roster has no PR/patch producer today), its exact form (branch / `format-patch` / squashed
  diff) **deferred to build**.

**Governance caveat (stated, not solved — the honest limit):** the private tree concentrates *derived company IP*
(knowledge nodes describing proprietary code, decision records about their architecture) on personal infra. "Zero
footprint on the company repo" is **not** "compliant with the company's data policy." So the private tree's
archive-to-git default is **local-only, no remote**; a backup remote is a deliberate act the maintainer takes against
his own policy.

**BUILD LAST, behind its own drive** — there is **zero prior multi-repo / multi-committer evidence** (every drive to
date was solo, single-orchestrator, one repo), and an optional rarely-run mode is exactly where the F2/F3-class silent
breakage hides. Drive protocol: clone a **real public repo** at a **pinned historical SHA**, run org mode, then
**replay the repo's own later real commits onto `FETCH_HEAD`** as free, realistic coworker drift, and assert the four
properties that DEFINE org mode — **(a)** the checkout stayed byte-pristine, **(b)** the loop never pushed/committed to
the company, **(c)** `align` detected the replayed drift via `describes_sha`, **(d)** no artifact leaked across the
boundary.

*Rejected:* the **project-repo-vs-docs-repo two-repo split** (converts every same-item STABLE guarantee into a
distributed transaction — there is no single staged diff across two repos, so `verify_check.py`/the commit hook/
`align`'s single anchor all break; the private-brain model has no second *synced* repo to tear); an **orphan branch**
in the company repo (the maintainer wants the artifacts *nowhere the company can see*, not on a side branch); **Reading
B / zero-commit patch-only** (breaks resume-from-git D48 for no gain — a remote-less local commit is invisible to the
org either way, so it is stricter than the actual goal and fights the architecture); a **config tab to toggle it**
(switching a live project's git topology is a *migration*, not a setting → chosen at `/start`. **The config tab is
dropped entirely**, and with it its D112-violating "change credentials over Cloudflare" arm — Cloudflare terminates
TLS, so a key would transit a third party; the credential-away case is Tailscale-only, D112).
*Reuse:* D28/D29 (start modes), D68/D130 (brownfield ingest — org mode ≈ this minus footprint), D114/D115/`rebind`
(runtime relocation → `project_root`/private-tree), D81 (`align` — `describes_sha` rides its existing diff-scope), D110
(the `guard.sh` push floor → absolute in org mode), D142 (`prioritize` GC on a no-`github_ref` issue — local-only
issues already supported), D109 (operator-responsibility), D93 (single-writer — the checkout's sole writer stays the
human).
→ `05`, `09`, `11`, `07`.
→ `07`, `11`, `README.md`, `scripts/dev-reinstall.sh`.

## D162 — Phase 9a's deferred mechanics: the forecast is a COMMITTED artifact that outlives its own checkpoint, gated by a skill-owned gate, and its verdict may carry an optional action payload **[DECIDED 2026-08-03 — the four calls D159 deferred, taken while writing the build plan; 9a still UNBUILT. One live shipped bug found while grounding: `align`'s mechanical layer crashes in every product repo]**
D159 designed the chain-forecast and deferred its mechanics "to build". Writing that build plan showed four of them
are not schedule items — they **change the artifact list**, and three of them are load-bearing enough that a plan
written without them would have been a plan to build the wrong thing.

- **The forecast is a COMMITTED artifact with the item-dir lifecycle** — `.workflow/forecasts/<id>.json`, the parked
  record carrying only `checkpoint.forecast_id` (the `demo_id` passthrough pattern). **It cannot live in the parked
  record**: `bus.py unpark` *removes* `parked/<id>.json` and the `handoff.md` mirror deliberately carries ids + kind +
  summary + opened-at and never a `request` body — so the thing D159 says `approve` **freezes** would be destroyed at
  the exact moment it is approved. That is **D154's defect one layer up** (approve deletes the only other copy),
  and D157's fix (promote before the delete) is the precedent. Committed rather than runtime because the frozen
  forecast is the anchor reality is compared against for the *life of the change* — across sessions, cold starts,
  and a `/rebind` to a machine where the runtime tree explicitly may not survive. It is safe to commit because it
  carries credential **key names only, never values** (the same class as `config.json`'s `secrets_required[]`), and
  that becomes a **linted invariant**, not a promise. Lifecycle copies `.workflow/items/<id>/` exactly: committed
  while the change is open, pruned by the audit pass when it closes, **history in git** — the project's own memory
  law (D38/D51/D61), not a new retention policy.
- **The trigger is a skill-owned FORECAST GATE, not D69.** D159 gated the orchestrator self-invoke on "the D69
  proportional-rigor triage". That triage **does not ship** — `grep -rn 'proportional\|rigor' product/` is empty, and
  `planner` carries `risk_class` + the three coverage gates but no tier-0/1/2 grading. Worse, D69 hosts it on
  **`planner` output** — *after* planning — while the forecast is a pre-plan intake checkpoint whose first predicted
  event **is** planning: the gate sits downstream of the moment it is useful. So 9a ships a **forecast gate** stated
  in `create-forecast/SKILL.md`, on D69's own axes (reversibility × blast-radius × ambiguity), evaluated by whoever
  routes past it — **exactly what the sandbox gate is to `create-demo`**. When D69's universal planner triage is
  later built it **subsumes** this gate rather than forking from it; this entry is that amendment, recorded rather
  than smuggled.
- **The front-loaded elicitation rides the forecast card, and a BLANK input is the vocabulary.** D159's pre-fill is
  explicitly optional ("hand it over now, **or be asked then**") — but `VERDICT_OUTCOMES` is `approve|changes|reject`,
  a per-task `reject` means "replan or escalate", a timeout "never auto-proceeds", and `request.blocking` is literally
  `true`: **the stack has no vocabulary for a skippable ask**. Filled → the secret store; blank → simply not
  front-loaded, and D97's within-plan ask stands unchanged. No new outcome enum, no new state.
- **A judgment verdict MAY carry an optional action payload — a refinement of the D96 taxonomy, written into `04`.**
  The two types classify *what the verdict means*: a forecast verdict still means "this is my opinion of the
  process", and the credential is not the verdict but a payload the human volunteered early. **The action boundary
  is still crossed at the gate**, where D97's machine-verify probe runs unchanged. Stated in `04` as designed, so it
  never reads as a leak. It also enforces one arm of D159's loopback-only for free: `remote_carries_payload()`
  already `403`s any `returns`/`tasks`-bearing verdict on Socket A.
- **Two sub-calls that fell out.** *Forecast runs BEFORE demo at intake* — a forecast placed after the demo cannot
  predict the demo checkpoint, which is one of the very gates it exists to front-load, and the forecast is cheap
  while the demo is expensive. *Re-forecast fires at the SCHEDULER BOUNDARY only, never mid-item* — which is what
  keeps `prioritize`'s non-preemption (D91) and D35 never-stall intact, and is why the divergence check belongs in
  `loop.md`'s **§ Scheduler boundary** (explicitly "plain control-flow, not a node") rather than as a routing edge.
- **Reality derives from a per-effect ANCHOR TABLE, not `state.json`.** D159 named `state.json` first; it is volatile
  and holds only the **current** node, never a history, so "which events have happened" is not readable from it. The
  table (`plan.md` ⇒ planner ran · `changelog` ⇒ execute · `verify-verdict.md` ⇒ verify · a parked record's
  `answered_at` ⇒ that checkpoint happened · `git log` ⇒ commit) is the **actual deliverable of the reality half**,
  lives in `schemas.md`, and needs no writer — the D108/D119 resolve-off-anchors pattern D159 itself cites.
- **Lint ownership splits by fact-domain (D80).** *Graph facts* — "does this event name a real node" — go to
  `check_contracts.py` as a new `--forecast <path>` mode, because it already owns `loop.md` parsing. *Forecast
  lifecycle* — freeze / reality / divergence / the names-only invariant — goes to a new `scripts/forecast.py`,
  imported by `bus.py` **with a guarded fallback** so a partial install renders the panel "unavailable" instead of
  taking the console daemon down.
- **Found while grounding, folded into 9a rather than filed: `align`'s mechanical layer is dead in every product
  repo.** `align` invokes `.claude/scripts/check_contracts.py` with **no arguments**, but the script's defaults
  resolve relative to its own parent-of-parent — `.claude/templates/loop.md`, `.claude/skills`,
  `.claude/shared/schemas.md` — none of which exist in an installed target (`/start` copies loop.md to
  **`.workflow/loop.md`**; skills and `shared/` live under `${CLAUDE_PLUGIN_ROOT}`). Reproduced in a simulated
  install layout: a `FileNotFoundError` traceback, exit 1. It is folded into 9a because 9a adds a mode to that same
  script, and **shipping a new mode onto a script that crashes in situ is building on sand**.

*Rejected:* keeping the forecast **in the parked record** (destroyed by `unpark` at the instant of approval — D154);
a **runtime/gitignored** forecast (dies on the machine move the artifact most needs to survive); **claiming D69's
triage** (it does not ship, and its host fires after the forecast is useful); **spawning a real `setup` checkpoint**
for the pre-fill (it needs its own ticket or it deadlocks the change on an optional ask — and an unanswered optional
ticket then re-alerts every `reminder_hours` and escalates as overdue *forever*, pestering by construction, which is
the exact thing D97 refused front-loading to avoid); a fourth **`defer` outcome** (an enum change rippling through
bus validation + `04` + `schemas.md` to express what blankness already expresses); **`state.json` as the reality
source** (no history); a **single lint script** (one owner per fact-domain, D80); **filing the `check_contracts`
bug as fix-later** (a queue entry routed past the build that is already touching the file is how the D136 governor
residual sat stale for six decisions — `11`'s own lesson).
*Reuse:* D154/D157 (approve deletes the only other copy → freeze/promote first), D96/D97 (taxonomy + the verb-enum
verdict + the setup probe that still runs at the gate), D22 (the sandbox gate — the per-capability-gate precedent),
D108/D119 (derived per-effect anchors), D91/D35 (non-preemption + never-stall → boundary-only re-forecast), D80
(one owner per fact-domain), D38/D51/D61 (lean files, history in git → the prune-at-close lifecycle), D112
(loopback = authoritative).
→ `04`, `07`, `11`.

## D163 — Phase 9a BUILT: the chain-forecast ships, and the seven calls the build had to make that D162 did not settle — plus two live shipped bugs found on the way **[BUILT 2026-08-03 — 9a-1 + 9a-2 by hand at `5a77aba`; 690 tests + all six meta-gates green; both halves driven end-to-end in a simulated install. NOT browser-rendered, and no real project has forecast a real change yet]**
D159 designed the chain-forecast, D162 settled the four mechanics that changed its artifact list. Building it
surfaced **seven more calls neither entry had taken** — each one a place where the design was underdetermined and
the code could not be written without choosing. They are captured here rather than absorbed silently, because five
of the seven *contradict or correct* something a prior entry states, and a build that quietly overrides its own
design record is how a spec stops being the source of truth.

**What shipped** (the commit message at `5a77aba` is the build record and is not restated here): `skills/create-forecast`
with the skill-owned forecast gate placed BEFORE the sandbox gate at intake · `scripts/forecast.py` as the lifecycle
owner (required horizon, linted names-only invariant, freeze + chain digest, reality, divergence) ·
`check_contracts.py --forecast` as the graph half · committed `.workflow/forecasts/<id>.json` · the `forecast`
checkpoint kind through schemas + bus + checkpoint + roster · the anchor table in `schemas.md` · a `#fc-list`
console panel with a shared chain renderer, state badges and a divergence banner.

**The seven calls:**
- **1. The prune lives in `retention.py`, not `forecast.py` — correcting D162's "lifecycle → `forecast.py`."** D162
  split lint ownership by fact-domain and assigned the whole forecast *lifecycle* to the new script. But **every
  other prune in the system is in the audit pass**, and a second pruner is a second owner of "what gets deleted when"
  — the exact D80 failure the split was meant to avoid, reintroduced one level down. So `forecast.py` owns the
  forecast's *semantics* (freeze, reality, divergence, lint) and `retention.py` owns its *deletion*, keyed off the
  **same `promoted.json` marker** that closes the item dir. It runs **BEFORE** the item prune, because the reverse
  order has a crash window that orphans a forecast whose anchors are already gone. **Closure is read positively,
  never from absence** — a forecast is born *before* any item dir exists, so "no item dir" is the normal state of a
  brand-new forecast, and a pruner that read absence as closure would delete every forecast at the moment it was
  created.
- **2. No `/create-forecast` command file.** D159 says "a `/create-forecast` command … the exact sibling of
  `/create-demo`". Plugin skills **already** expose a slash command by name — `create-demo` ships no command file
  either. Writing one would create a **second entry point** to the same capability, which is the drift D80 exists to
  kill; the sibling framing is honoured by *being* the same shape, not by adding a file.
- **3. The per-item artifact filenames are PINNED.** `changelog.md` · `debug-report.md` · `plan-delta.md` were named
  **nowhere** in the repo — the anchor table cannot anchor `execute` without them, and an artifact written under a
  different name is an event that silently reads as never having happened. `schemas.md` now states the fixed set and
  says why (two mechanisms read them by name and neither can guess: the coverage gates key off `promises.json`, the
  anchor table keys off the rest).
- **4. A FOURTH reality state, `unknown` — an addition to D159's model.** D159 implied a binary (an event either
  unfolds as predicted or is a divergence). Some nodes have **no derivable anchor at all**: `decision-engineer`'s
  output is a *global* decision record that cannot be tied to one item. Rendering "I can't tell" as `pending` would
  make the column **lie** — a reader would see "did not happen" for something that may well have. So: `done` · `open`
  · `pending` · `unknown`, and `unknown` renders as unknown. This is `align`'s honest-truncation rule (a silent cap
  reads as "all clear") applied to a column instead of a list.
- **5. Divergence exempts the item-complete tail** (`commit` · `document` · `close-issue` · `prioritize`). These run
  for **every** item, so their absence from a forecast chain is the horizon talking, not a surprise — and **a signal
  that fires on every finished item is not a signal**. They stay in the *reality column* (which is information); they
  are out of *divergence detection* (which is an alarm). D159 defined structural divergence but never bounded it, and
  unbounded it would have re-forecast at the end of every single item.
- **6. Re-forecast is a SUPERSEDE, never an in-place edit.** D159 says `changes` "re-forecasts with the edits" without
  saying what happens to the frozen record. Editing a frozen chain in place destroys the thing approval exists to
  create — the anchor reality is measured against — and would make the chain digest meaningless. So a re-forecast
  writes a **new version over the same `<id>.json` with `status` back to `draft`**, and the superseded version lives
  in **git**. Same file, same id, one live chain; history where this project always keeps it (D38/D51/D61).
- **7. The loopback-only gate is keyed on KIND, not payload — correcting D162.** D162 claimed D159's loopback-only
  rule was enforced "for free" because `remote_carries_payload()` already `403`s a `returns`/`tasks`-bearing verdict
  on Socket A. That covers **only the pre-fill arm**. A **bare `forecast` approve** — no payload at all — carries no
  `returns`, passed the payload check, and **was riding the remote socket**. But an approved forecast is *a whole
  execution plan the agent follows* (D90 makes an approved verdict authoritative), which is precisely why D159 put it
  on loopback. The gate is now on the checkpoint **kind**: a `forecast` verdict is refused on Socket A whether or not
  it carries anything.

**Two live shipped bugs, both fixed in the same commit, both proved failing first:**
- **`check_contracts.py` crashed in every product repo** — `align` invokes it with no arguments and the defaults
  resolved to `.claude/templates/loop.md` + `.claude/skills`, which no install has. `FileNotFoundError`, exit 1:
  **`align`'s entire mechanical layer was dead in situ**, in every installed project, silently. Found while grounding
  D162 and folded into 9a rather than filed, because 9a adds a mode to that same script. Defaults are now
  layout-aware, a missing package input degrades **loudly** instead of crashing, and `align` passes the plugin root
  explicitly. 7 regression tests, 6 of which fail against the unfixed source.
- **`bus.py`'s `PARK_KINDS` was an unguarded second copy of the schema kind enum** — a kind the schema declares and
  the tuple omits is a checkpoint that **can never open**, and no prose consumer could see the drift. It is now
  parsed by `check_enum_coherence.py` like the other code consumers. This is the same class of defect as the bug
  above: a second source of truth that no gate was watching.

**One row of the anchor table is RETRACTED.** `schemas.md` declared `commit` → "a `git log` subject naming the item
id", and `forecast.py`'s `ANCHOR_TABLE` never implemented it. The row is **dropped**, not implemented, and this is
the call rather than the deferral: (a) it is **misspecified as written** — `commit/SKILL.md` pins `Refs: item
#<backlog-id>` as a **trailer**, and the subject is `type(scope): summary`, so the declared probe looks in the wrong
place; (b) `commit` is **divergence-exempt** (call 5), so the anchor buys a single column cell and never a signal;
(c) `document` (`promoted.json`) already anchors the item-complete tail and runs *before* `commit`, so the adjacent
cell already tells the human the item reached its tail; (d) every other anchor is a pure `path.exists()`, and
`forecast.py` is imported by the console daemon — adding a subprocess with a timeout, a cache and a bounded window
to a module whose whole virtue is that it cannot fail is a poor trade for (b). If it is ever wanted, the exact
anchor exists and is not a fuzzy subject grep: `git log --grep='^Refs: item #<id>$'`. Better to ship a table where
every row is true.

*Rejected:* a **second pruner** in `forecast.py` (two owners of deletion — D80); reading closure from the **absence**
of an item dir (deletes every newborn forecast); a **`/create-forecast` command file** (a second entry point to one
capability); a **binary reality model** (renders "I can't tell" as "did not happen" — a column that lies); **unbounded
structural divergence** (fires on every finished item, so it is noise, not signal); an **in-place edit of a frozen
chain** (destroys the anchor approval exists to create, and voids the digest); the **payload-keyed** loopback gate
(passes a bare approve, which is the *most* authoritative verdict there is); **implementing the `commit` anchor**
(misspecified, signal-free, redundant with `document`, and a subprocess in the daemon's import path).
*Reuse:* D80 (one owner per fact-domain — twice: the pruner and the command file), D38/D51/D61 (history in git → the
supersede), D90/D112 (an approved verdict is agent control → loopback by kind), D37 (divergence vocabulary), the
`align` honest-truncation rule (→ `unknown`), D22 (the sandbox gate, the per-capability-gate precedent the forecast
gate copies), D154/D157 (approve deletes the only other copy → freeze before unpark).
*Evidence:* `5a77aba` (the build, with the two bugs each proved failing against the unfixed source); 690 tests + all
six meta-gates green; both halves driven end-to-end in a simulated install layout.
*Residuals — deliberately NOT built:* (1) a **per-ITEM forecast** on the `planner:plan-one` path — 9a is intake-only,
the gate is stated for a "change", and `/create-forecast` is available by hand anywhere; (2) `discuss`, `prioritize`,
`align`, `close-issue` and `ingest` have **no anchor-table entry**, so they render `unknown` — honest, but thin, and
worth revisiting if the column reads as mostly-unknown in practice; (3) the `#fc-list` panel has **never been
rendered in a browser** (the D147/D156 pattern: mechanically driven, visually unproven).
→ `04`, `05`, `07`, `09`, `10`, `11`, `shared/schemas.md`.

## D164 — Phase 8a RE-DESIGNED against the platform: the plugin `version` is DELETED, not disciplined — delivery becomes the commit SHA, and the staleness PREVENTER becomes a two-hop DETECTOR **[DECIDED 2026-08-03 — supersedes 8a's build plan (D151/D155/D158); the sixth meta-gate is deleted from the plan, not deferred; unbuilt. Also fixes the Phase-8/Phase-9 sequencing D163 left open]**
8a was designed to build machinery enforcing a human ritual. Re-checked against the live platform docs before
building it — the D136 precedent — the ritual turns out to be **something the platform performs for free**, and the
one argument for keeping the ritual **does not survive reading our own code**.

**The platform fact (verbatim, `code.claude.com/docs/en/plugins-reference#version-management`, re-read 2026-08-03).**
`version` is optional, and the cache key resolves from the first of: (1) `plugin.json`'s `version`; (2) the
**marketplace entry's** `version`; (3) **the git commit SHA** for `github`/`url`/`git-subdir`/relative-path sources
in a git-hosted marketplace; (4) `unknown` for npm or a local directory not inside a git repo. The docs' own
Warning: *"If you're iterating quickly, leave `version` unset so the git commit SHA is used instead."* Note rule (2):
putting a semver in `marketplace.json` **re-pins** — so "semver in the marketplace, omit in the plugin" decouples
nothing.

**Call 1 — DELETE `version` from `plugin.json` (and never add one to the marketplace entry).** Delivery then keys on
the commit SHA, so staleness becomes **structurally impossible to forget** rather than ritually prevented — this
project's most-repeated lesson (D129, and again D142/D144/D145/D147/D150/D152): derive the protection from the
artifact's shape, never from a signal somebody had to remember to send. **The sixth meta-gate in `build-release.py`
is therefore deleted from the plan, not deferred** — there is no longer a ritual for it to guard. *(Caught by the
blast-radius sweep: "the sixth meta-gate" was already a stale name — D163 records **six** gates green, so D155's
proposed one would in fact have been a seventh. It is named here as D155/D158 named it, and dropped.)*

**Call 2 — `config.json`'s `workflow_version` becomes that SHA.** *This retires the objection that killed the idea
on first look.* The fear was that D135 couples the plugin version to the migration key, and a SHA is not ORDERED, so
"is this install older than migration X?" becomes unanswerable. **Reading `update_reconcile.py` rather than its
description: `/update` never asks that question.** `workflow_version` is used in exactly three ways — an **equality**
test (`noop = old == new`), a **display** string (`STAMP old -> new`), and **absent ⇒ unknown-old ⇒ removals
disabled**. There is no ordered comparison anywhere; every migration decision is **content-hash** driven through
`install-set.json` (`ADD`/`SAME`/`REFRESH`/`LOCAL-EDIT`/`REFRESH?` all come from `_sha`). D137/D139 built the hash
ledger *precisely* so the version would not have to carry ordering. Under a SHA the equality test gets strictly
**more** correct: `noop` becomes true only when the content genuinely did not move, where under the pin `noop=True`
**is** the D151 lie. `update.md` already conceded it in prose — *"a dev install can move without the version
moving."* **If `/update` ever needs true ordering ("installs before N need step Z"), the escape hatch is a
product-owned `schema_version` in a shipped file — a different field from the delivery cache key.** Not built now:
adopting a second version source before anything asks for it is accretion, which D80 forbids.

**Call 3 — the PREVENTER becomes a DETECTOR, covering BOTH hops, local-only, everywhere, once per distinct SHA.**
There are **three** layers and therefore **two** copy hops, and 8a had only ever reasoned about one: the **source**
(`product/` in this repo) → the **install** (`claude plugin install` *copies* it to
`~/.claude/plugins/cache/<mkt>/<plugin>/<version>/`, one per machine — this is what `CLAUDE_PLUGIN_ROOT` points at,
so *this* is what runs) → the **project scaffold** (`/start` copies the `MANIFEST` `install[]` set into the project's
own git, because `.claude/settings.json` references those files by project-relative path and the cache path is
machine-specific and uncommittable). **The hop nobody had written down is that `/update` is BOUNDED BY THE
INSTALL** — it runs `${CLAUDE_PLUGIN_ROOT}/scripts/update_reconcile.py --plugin-root ${CLAUDE_PLUGIN_ROOT}` and never
reaches back to the source. So a stale install does not merely run old code: it **propagates** old code into every
project that runs `/update`, reporting success. That is why the two axes are not redundant. The detector rides
`hooks/session_start.py`, which is **already wired at matcher `startup` and whose re-assert block already runs on
every source** — no new hook surface: **hop A** compares the installed SHA against the on-disk marketplace anchor
(`.gcs-sha` for a github source; `git rev-parse HEAD` for a directory source) → *reinstall*; **hop B** compares
`config.workflow_version` against `basename(CLAUDE_PLUGIN_ROOT)` → *run `/update`*. Warn-once state keyed on the SHA,
always fails open. **The governing reason a detector replaces a preventer: delivery is not ours to fix** — issue
#17361's Failures 1 and 3 are CLI-side, so **no author-side choice makes delivery automatic**; what an author can
control is that the *manual* path stops lying, and that the install can *say* it is stale.

**Call 4 — the cache prune is meta-only, keep-2, in `scripts/dev-reinstall.sh`.** SHA versioning means every update
writes a **new** dir and abandons the old one; Claude Code has **no retention policy at all** and `uninstall` does
not reclaim them either (both measured). At ~2.4MB per update this is negligible for a released user and fastest for
the maintainer, who is therefore the one who gets the prune. Keep-**2**, not keep-1: the CLI prints *"Restart to
apply changes"*, so a session that began before an update is still executing from the older dir.

**Call 5 — the sequencing D163 left open: `8a → drive 9a → 9b`.** Not on 8a's user-facing payoff, but because **a
stale install corrupts the evidence of every drive that follows it** — D151's actual lesson. Do 8a first and every
later drive is trustworthy by construction; then **the 9a browser drive doubles as 8a's exit test**, proving the
delivery path end-to-end while closing 9a's never-rendered `#fc-list` residual in one pass. 9b is the largest of the
three and unblocks neither, so it follows.

*Rejected — **8a as designed** (bump-per-release + the sixth meta-gate):* the most work for the least benefit; it
enforces a ritual the platform performs for free, and issue #17361's Failure 3 means even a correct bump does not
reach clients automatically — so it buys only the manual path that deleting the field also buys, while preserving
the misleading message on every skipped bump. *Rejected — **auto-bumping semver from a hook**:* D158 rejected this
because "a version that moves five times a day is not a migration key" — **that reason is now void** (nothing orders
it), but it loses anyway as local machinery reimplementing a native platform behaviour. *Rejected — **a version in
the marketplace entry**:* resolution rule (2) re-pins. *Rejected — **`git ls-remote` in the detector**:* it would
also catch Failure 1, but a network call at session start needs a timeout, an offline path and a cache rule — most
of the detector's total complexity, for the one failure a directory-source install cannot exhibit. *Rejected — **a
GC shipped into the product**:* a plugin deleting siblings of itself inside the CLI's own cache is outside our ship
boundary and can yank a directory from under a live session. *Rejected — **a runner-only warning**:* it would skip
interactive sessions, which is where **both** drift data points actually happened. *Rejected — **a hop-B-only
detector**:* that is the axis that can lie, since a stale install makes `/update` report success over stale files.

*Corrections this forces to prior entries:* **D158's stated reason for rejecting an auto-bump is void** (it assumed
the version carried ordering; it does not), and **D158's "the two halves are deliberately different in kind" is
partly superseded** — one detector serves both audiences with **different anchors** (released user → marketplace
clone; maintainer → the repo), which is D161's "org-align is existing `align` with a different anchor" pattern.
D158's *call* — that the maintainer's fix must not depend on a version — still stands and is what the prune rides.

*Evidence (measured, CLI **2.1.220**, in a throwaway `CLAUDE_CONFIG_DIR` — the real install was verified untouched
afterwards):* a version-less plugin in our exact shape (`source: directory` at a path that *is* a git repo; plugin
`source: "./product"`) resolved to the **short commit SHA** (`5f8148115e14`), **not** `unknown` — settling the rule
(3)/(4) seam that would have made omission *strictly worse* than the pin; a new commit was then delivered by
`claude plugin update` **without even a preceding `marketplace update`** (a directory source reads live), content
verified in the cache. **The pinned control reproduced D151 in 60 seconds:** content changed without a bump →
`✔ already at the latest version (0.1.0)` → the change never reached the cache. `gitCommitSha` correctly stayed at
the **install-time** commit, so `11`'s prescribed `gitCommitSha == HEAD` check is **sound** and is the detector's
primitive. Four updates → **four** cache dirs, and `uninstall` reclaimed none. `claude plugin validate` on a
version-less `product/` **passes** (advisory warning `No version specified`; note `--strict` would treat it as an
error, which matters only if this is ever submitted to `claude-community`). *Corroboration:* Anthropic's own
`claude-plugins-official` marketplace carries **`version: None` for every plugin**, pinned by SHA — the reference
implementation already does this. *Issue state as of 2026-08-03:* #49410 and #52218 **closed**; #72616 (our exact
directory shape) closed by a **bot as an auto-duplicate**, not fixed; **#17361 OPEN**, with reproductions on 2.1.220
through 2026-07-31 separating three failures — **F1** autoUpdate never pulls the clone, **F2** the cache is keyed on
the version string so content changes never re-extract (*this is D151, and this is the control above*), **F3**
session start never performs the update even when the catalog is current and the version genuinely differs
(`0.4.0`→`0.5.1` unapplied through a 30-minute idle session). F3 was **not** independently reproduced here — it needs
a 30-minute idle session — so it rests on three independent reports at our exact CLI version. *Blast radius of the
change itself is small:* one function (`plugin_version()`, 2 call sites) plus a `--plugin-dir` edge where
`basename` is `product` rather than a SHA, one test fixture asserting `"0.2.0"`, and prose in `start.md` step 7,
`shared/schemas.md`'s `config.json` owner line and `update.md`'s `STAMP` paragraph; `build-release.py` only copies
the manifest and never reads the version. *Second data point for D151, from this session:* the install was **six
commits stale** and was only fixed because the maintainer was explicitly told to reinstall — `dev-reinstall.sh` had
shipped the day before (D158) and did not run. Two data points now say a manual script is not a control, which is
what Call 3 answers.
→ `07` (the Phase-8a OPEN block closes), `11` (Phase 8 rewritten; the Phase-9-vs-8 sequencing call resolved). At
build: `product/.claude-plugin/plugin.json`, `product/scripts/update_reconcile.py`, `product/hooks/session_start.py`,
`product/commands/{start,update}.md`, `product/shared/schemas.md`, `scripts/dev-reinstall.sh`.

## D165 — Phase 8a BUILT, and two mechanisms changed under measurement: the SessionStart hook gets no `CLAUDE_PLUGIN_ROOT`, and the warn-once state belongs in `.git/hooks/` **[BUILT 2026-08-03 — `540d0e0`; realizes D164's four calls; both of `07`'s Phase-8a open items close]**
D164's four calls were built as specified. Two things only a build could find changed *how*, not *what* — and one
of them would have made the detector silently inert.

**The hook receives no `CLAUDE_PLUGIN_ROOT`.** D164's hop B was written as "`config.workflow_version` vs
`basename(CLAUDE_PLUGIN_ROOT)`". Measured on 2.1.220 with a real probe session: a project-settings hook is handed
`CLAUDE_PROJECT_DIR` and **not** `CLAUDE_PLUGIN_ROOT`. That is not an accident of configuration — the package
*installs itself into the project* (`.claude/settings.json` names hooks by project-relative path, which is the
third layer D164 itself identified), so the hook that runs is the **project's copy**, wired from the project's
settings, and there is no single plugin context for the harness to point at. The docs read ambiguously here; the
probe settled it. Hop B therefore reads the resolved cache key from **`installed_plugins.json`** — the file the
detector must open anyway for hop A's `gitCommitSha`, so no new source is adopted — and still prefers the env var
when set, so a future harness that exports it is an improvement rather than a break. Same comparison, working
anchor. **The lesson generalizes past this hook:** anything the package installs into a project cannot assume
plugin-scoped environment, and three other shipped scripts take `--plugin-root` as an argument precisely because
they are invoked from command prose that expands it — the hook has no such caller.

**The warn-once state went to `.git/hooks/.disciplined-builder-stale`, not under `.workflow/`.** `07` framed this
as "which `.workflow/` key owns it". All three of the requirements point elsewhere. The facts recorded are about
**this machine** (which SHA is installed), so committing them would let one machine's install silence the warning
on every other; `.git/` is untrackable **by construction**, needing no `.gitignore` entry — which is load-bearing
rather than tidy, because the installs this must reach are precisely the ones too stale to have a new ignore line;
and it must survive a `/rebind` and be readable before a project is bootstrapped. It is also **bounded at one
small file rewritten in place, so nothing prunes it** — `retention.py`'s remit is `.workflow/` artifacts and
extending it here would buy nothing. This adopts the convention the *same file* already used for the foreign-hook
marker, and gives **both** markers a `shared/schemas.md` owner, which the older one never had.

**The `--plugin-dir` edge (`07`'s second item) closed as a four-rung chain**, and the rung ORDER is the decision:
a `plugin.json` pin → the resolved cache-dir basename → the source repo's `HEAD` → `unknown`. Basename comes
*before* git deliberately — the cache lives under the CLI config dir, and a user who versions their dotfiles would
otherwise have us report their **dotfiles'** HEAD as the package version. A `version` subcommand was added because
`plugin.json` no longer has a field to read, and without it `start.md` would have had to re-describe the chain in
prose — a second owner of the rule, which is the drift D80 exists to stop. `unknown` is now excluded from the
no-op test: two installs that both failed to resolve a version are not the same install.

*Rejected:* **a `.workflow/staleness.json` + a new `.gitignore` line** — the line arrives via `/update`, i.e.
exactly the mechanism a stale install has not run, so the state file would sit untracked and be committable on the
projects that need the warning most; **duplicating the resolution chain into the hook** — one rule, two spellings;
**a `retention.py` arm for the marker** — a bounded single file needs no collector.

*Evidence (measured, CLI 2.1.220):* a probe session dumped the SessionStart hook's environment — `CLAUDE_PROJECT_DIR`
present, `CLAUDE_PLUGIN_ROOT` **absent**; the version chain resolved `ab1d951b06c8` under `--plugin-dir ./product`
(rung 3, the `07` edge) and `0.1.0` against the still-pinned live cache dir (rung 1); `claude plugin validate` passes
on the version-less package with the advisory `No version specified`; **the delivery call proved end-to-end** — before
the reinstall hop A fired against the real registry (*"installed at 21dda6c43208, the source on this disk is at
540d0e0ee9b4 — the source is 2 commits ahead"*), after it hop A went silent **with no state cleared** (the condition
simply stopped holding) and hop B correctly asked for `/update`; `installed_plugins.json` `version` is now the SHA
`540d0e0ee9b4`, and the cache held exactly two dirs so keep-2 reclaimed nothing. 712 tests (690 + 22), all meta-gates
green. *Not built, deliberately:* the release gate D164 deleted — a pytest invariant asserts instead that no `version`
reappears in `plugin.json` **or** the marketplace entry (resolution rule (2) re-pins from there), which guards the new
shape rather than the old ritual.
→ `07` (both Phase-8a items close), `11` (8a → BUILT). Files: `product/.claude-plugin/plugin.json`,
`product/scripts/update_reconcile.py`, `product/hooks/session_start.py`, `product/commands/{start,update}.md`,
`product/shared/schemas.md`, `scripts/dev-reinstall.sh`, `product/scripts/test_{update_reconcile,session_start}.py`.

## D166 — The first browser render of the chain-forecast found two defects, and both were in the interaction shell — including one that would have re-forecast chains for someone else's checkpoint **[BUILT 2026-08-03 — `613d230`; closes 9a's never-rendered residual (`07`)]**
9a shipped mechanically driven and never rendered. Rendered in real headless Chrome against a live bus daemon with
three forecasts (frozen · frozen-and-diverged · draft) and two open forecast checkpoints. **The D147/D156 shape held
a ninth time:** the logic was fine and both defects were in the shell, where every previous drive found its defects.

**Defect 1 — every event was numbered twice.** The chain is an `<ol class="chain">` whose list marker was never
suppressed while each `<li>` also renders the record's own `n`, so every row of every chain read "1. 1", "2. 2" — on
the checkpoint card *and* the panel, since D163's one-shared-renderer decision means one fix covers both. **No
assertion could have caught it:** each number is individually correct and `textContent` sees only one of them. The
same stylesheet already sets `list-style:none` on `ol#log`, which is what marks this an oversight rather than a
choice. Fixed by suppressing the marker, **not** by dropping `.ev-n` — `n` is a record field, and a browser marker
always counts 1..N from the top, so the two would disagree the moment a chain were rendered partially or an event
filtered.

**Defect 2 — the reality probe's `parked` arm was not item-scoped, and it is the expensive one.** `_probe` computed
`item` and then never applied it to parked records, so it answered from **any** open checkpoint in the project. Two
consequences, both reproduced live before fixing: a `qa` checkpoint parked for an unrelated change made this chain's
`checkpoint:qa` read `open` — whose entire meaning is *"the machine is waiting on YOU, here"* — when nothing about
this change was waiting; and a chain predicting **no** checkpoint collected a structural **divergence** from somebody
else's checkpoint. That second one is not cosmetic: **a structural divergence re-forecasts the tail** (D159), and
since `prioritize` emits parallel items, an open checkpoint somewhere is the *normal* state — so the false positive
would have fired most of the time and paid for a re-forecast each time. Fixed by testing `ticket_id` against the
forecast's own id, which is what every other probe in the same function already did.

*Checked and NOT defects:* the gate's secret-prefill inputs render correctly — the missing inputs on the first
attempt were the fixture's fault, because projecting event gates into `request.tasks[]` is `create-forecast`'s own
job (its step 6), not the console's; and both linters correctly refused a frozen record with no digest and a
`branch[].then` naming no real node.

*Rejected:* **dropping `.ev-n` and letting the `<ol>` marker number the chain** — the marker renumbers from 1
regardless of the record, so a partial render would show two different numbers for one event; **inferring the
checkpoint's owner from `state.json`** — volatile, holds only the current node, and the anchor table's whole premise
is that reality is derived from durable artifacts.

*Evidence:* real headless-Chrome renders before and after (numbering doubled → single; divergence banner
`"the loop reached checkpoint, debug"` → `"the loop reached debug"`); the cross-item leak reproduced in both
directions and then re-verified fixed; +5 tests (both directions of the scoping leak, the real signal still firing,
and a stylesheet guard — the defect *was* a missing rule, so the guard asserts the rule's presence). 717 tests, all
meta-gates green. *Left for judgment, not fixed:* the panel prints a raw ISO `frozen <stamp>` while the card
humanizes ("due in 24h") though the page's own `humanGap` helper exists and its comment argues against exactly this;
the prefill hint "Optional — …" renders *after* the credential inputs; and while a forecast checkpoint is open the
card and panel render the same chain twice on one page.
→ `07` (9a's browser residual closes; three shell observations open), `11` (9a residual cleared).
Files: `product/scripts/bus.py`, `product/scripts/forecast.py`, `product/scripts/test_{bus,forecast}.py`.

## D167 — Phase 9b BUILT: the context-budget law is two-tier per role, and its estimator is calibrated on this repo's own measured paging failure **[BUILT 2026-08-03 — realizes D160; the "bounded by construction" claim finally has a mechanism]**
D160 designed the law and deliberately left the numbers to measurement (*"there is no single constant"*). Measuring
produced one hard number, one dead heuristic, and one conflict D160 had not foreseen.

**The estimator is calibrated, and the obvious choice was wrong.** There is no tokenizer in the standard library and
this package ships stdlib-only Python, so the count must be estimated from length. The divisor is not folklore: this
repo's own `11-roadmap.md` was **85 083 characters** at `9d13b3c` when it *paged at the 25 000-token ceiling*, which
puts the real ratio at **≤ 3.40 chars/token** for markdown prose. That measurement **kills `chars/4`** — the usual
rule of thumb scores that exact file at 21 271 tokens, comfortably "under" a wall it demonstrably could not fit. 3.2
ships, for margin, and the estimate rounds **up**: under-reporting is the one failure this cannot have, because it
lets an unreadable file pass. It is a config knob, because a doc dense in fenced code tokenizes worse than prose.

**Call — TWO TIERS PER ROLE (hard fails `checks.sh`, advisory schedules a trim).** D160 prescribed a hard wall plus
a softer advisory for the *on-demand* role; measuring forced the same shape onto the *always-loaded* role, for a
reason D160 could not have known: **the package's own always-loaded templates measure ~3.3k and ~3.4k tokens**, i.e.
**3.3–3.4× the sub-1k community target D160 cites**. Shipping the aggressive number alone would have made the gate
**red on every clean install** — and a gate that fires on a fresh bootstrap is one a human learns to skip, which is
the same failure D164's warn-once-per-SHA rule exists to avoid, one phase earlier. So: `always_hard` 4000 /
`always_advisory` 1200, `ondemand_hard` **25000** (the Read ceiling — not a preference) / `ondemand_advisory` 15000.
Green on install, with the aspiration tracked as **work** rather than as a broken build.

**The trigger is the finding, so there is no second number to tune.** `prioritize` gains a **third** decoupled
maintenance item — `doc-budget`, beside `document:audit` (memory pressure) and `align` (drift risk) — injected every
`every_p_items` items *when the report actually carries an advisory*, at most one open at a time (an over-size doc
stays over-size, and re-filing it every P items is sediment, not a signal). Only advisories reach the scheduler: the
hard tier already failed the commit gate, so by then the unreadable-file case is impossible.

**Sessions distillation is un-deferred, and its placement rule is a real trap.** Compression beats raw retention, so
the `audit` item distils each entry about to fall past *K* into a one-line lesson **before** `retention.py` caps —
the script is deterministic and cannot distil, so distilling afterwards would be distilling from git. The lessons
live in a **top-level `# Lessons` section placed BEFORE `# Sessions`**, never nested under it: `# Sessions` is
terminal and its region deliberately runs to EOF once entries begin (so a markdown H1 inside a postmortem body
cannot truncate the region), which means a `## Lessons` under it would be parsed as a session **entry** and dropped
by the very cap it was written to survive. Verified against the real script, both placements.

*Rejected:* **`chars/4`** (measured unsafe, above); **a pip tokenizer** (`tiktoken`/the SDK) — the package is
stdlib-only by construction and a size gate does not justify the first dependency; **budgets in lines** (a unit the
model does not read, and window-dependent); **one budget for all roles** (there is no best-practice max size — that
is *why* it is per role); **auto-trimming prose** (needs judgment → ticket + split-and-pointer); **a second
truth-checker** (`align` owns "wrong", this owns "too big" — D80); **folding doc-budget into `document:audit`** (it
would tie doc size to memory pressure, the coupling the decoupled thresholds exist to prevent); **budgeting the
VOLATILE tier** — `handoff.md` is already capped mechanically at injection time by the `SessionStart` hook, and one
bound with two owners is a bound that drifts.

*Evidence (measured, not cited):* the calibration above, recovered from git (`9d13b3c`, 767 lines / 85 083 chars);
the shipped always-loaded pair at 3309 and 3395 tokens; **`product/shared/schemas.md` measured at 28 519 tokens —
already past the hard wall, in a shipped file the whole package names as its schema owner** (recorded as tracked debt
in `07`, and the prose arm's first real customer); the gate dry-run green-with-one-advisory on a real bootstrapped
project and blocking on a hard breach; `# Lessons` proven to survive a real `retention.py` cap while a `## Lessons`
under `# Sessions` is proven to be capped away. +24 tests (17 gate, 5 lessons-placement, 2 wiring); **741** tests total,
all meta-gates green. *Found while wiring, not fixed:* `retention.py`'s `--project-root` means the **product** root
while `update_reconcile.py`'s means the **repo** root — one flag name, two meanings (`07`).
→ `05`, `06`, `product/shared/{memory-model,schemas}.md`, `11`, `07`. Files: `product/scripts/check_doc_budget.py`
(new), `product/templates/{checks.sh,loop.md}`, `product/skills/{prioritize,document}/SKILL.md`,
`product/MANIFEST.json`, `product/scripts/test_{check_doc_budget,retention_lessons,checks_runner}.py`.

## D168 — `schemas.md` SPLIT: the split-and-pointer arm's first real customer forces a second marker form, a machine-followable pointer, and a budget on the detail file the remedy produces **[BUILT 2026-08-04 (`b4e2c25`) — exercises D167's convention; not a new law, the first *execution* of one]**
D167 shipped the split-and-pointer remedy as prose and a marker string that nothing parsed. `07` then recorded the
first customer, and it was ours: **`product/shared/schemas.md` measured 28 520 tokens** — past the 25 000-token Read
ceiling, in a *shipped* file the whole package names as the owner of every schema. The failure it causes is not
hypothetical: D130 measured `ingest` burning its turn budget hunting formats across five files and **running out
before parking its blocking checkpoint**, which is precisely why `schemas.md` was made the single owner. The owner
then grew past the wall, so the same failure was recurring one layer up.

**Call — split at the loop-artifacts / runtime-substrate line.** The survivor keeps what a *skill* produces and
consumes (spec, plan, changelog, verdict, checkpoint, parked-ticket, inbox-message, forecast, outbox, handoff,
state — **18 670 tokens**); the new **`product/shared/schemas-runtime.md`** takes the records the package's own
*processes* own, written and read by `/start`, `/update`, `rebind.py`, the bus daemon and the `SessionStart` hook and
never authored by a skill as work (`config.json`, `runtime.json`, `.workflow-runtime`, `install-set.json`, the
orchestrator-brief managed block, `statusline.delegate`, `bus.lock`, `orchestrator.lock`, `bus.json`, `remote_token`,
`alerts.json`, the session-start warn-once markers — **10 832 tokens**). All 33 sections preserved, verified
section-by-section against `HEAD`, not by eye. `shared/` never installs into a target, so the sibling ships with the
plugin exactly as the survivor does.

**A SECOND MARKER FORM, because the convention assumed the detail was dead.** D167's marker mirrored retention's
Sessions marker and carried `@ <sha>` — right for content **frozen in git**. The first real customer splits into a
**LIVE SIBLING** still being edited, where a sha is stale at the next edit and sends a reader to git for a file
sitting beside them. So the convention now has two forms, and the difference is semantic, not cosmetic: an archived
target is *expected* to be absent from disk, a live-sibling target that is absent is a fault worth reporting.

**The pointer must be MACHINE-followable, and choosing the split line could not avoid it.** Two shipped consumers
parse `schemas.md` whole, and the attempt to dodge them by picking a different line fails on inspection: the
runtime-substrate half is exactly where the `kept on a native filesystem` headers live. Both readers were **measured
against the real split rather than reasoned about**, and both break **loudly, in opposite directions** — the
meta-gate's native-FS rule (R2) hard-fails with **five** false "the layout pins a path no schema header claims"
errors, while the contract linter's `kind:` union silently loses `generic` and `slack` and then reports legitimate
uses as *novel* kinds. **Neither goes quiet, so this is NOT the silent-gate-defeat class (D129)** — a first draft of
this entry and of the code comments claimed it was, and the measurement refuted it. The honest finding is smaller and
still decisive: the split was **not viable** without teaching the parsers. `read_with_splits` lives in
`check_doc_budget.py`, which already owns the marker string, for the reason that file states — a marker with two
spellings is a marker nothing can find.

**The remedy was producing a file the gate then stopped watching.** `check_doc_budget.py`'s scan is a fixed glob
(`docs/spec.md`, `rules/**`, `docs/knowledge/**`, …). A `docs/spec-detail.md` produced by the split it prescribes
falls **outside** that glob, so the detail half could grow straight back through the wall unseen and the second split
would have nowhere to land. Detail files are now scanned as their **own row**, always **on-demand** whatever the
referrer was — detail broken out of an always-loaded file is by definition no longer read every turn, which is the
point of that remedy. **The sizer still does not follow the pointer**: the survivor is under the wall *because* the
detail moved out, and a sizer that re-added the bytes would report the split as having achieved nothing. Two readers
of one file, two correct answers.

**The resolver DEGRADES, it does not crash.** `check_contracts.py` imports a sibling script, and that suite exists
because this script once **died in every product repo** (D163). A partial copy now reads the survivor and *says* the
split went unfollowed, and stays silent when nothing is split.

*Rejected:* **hand-tuning the split line to keep every parser input in the survivor** (measured impossible — the
native-FS headers are the moved half, and it would leave only ~4k tokens movable, not enough for headroom);
**copying the marker regex into the meta-gate** (a second spelling of a compatibility contract — the exact defect
that gate exists to catch, so it borrows the parser instead); **a hard import** (reintroduces the D163 crash class);
**making the sizer follow the pointer** (would report every split as achieving nothing); **rewriting the 37
`schemas.md §` references across 22 files** (the reference form resolves across both halves by design — the section
name is the anchor; rewriting them is churn that buys nothing); **stamping `@ <sha>` on the live sibling** (a lie at
the next edit).

*Evidence:* measured, not reasoned — original 28 520 tok → 18 670 + 10 832; a section-set diff against `HEAD` showing
33 sections in, 33 out, zero bodies changed; the R2 counterfactual run both ways (**5 errors survivor-only → 0
following**); the enum-union counterfactual (`generic`, `slack` lost survivor-only) reproduced end-to-end as a
subprocess, with and without the resolver beside the script; the leak gate catching a `D129` reference this entry's
own drafting had leaked into a shipped file. **756 pytest (+15)**, all five meta-gates green (no-spec-refs `8 shipped
paths`, status-coherence, enum-coherence, contract linter `0 advisory`, release boundary **58 shipped files / 20
install entries**). Reuses/relates **D167** (the convention + the gate), **D160** (the law), **D80** (one owner per
fact), **D129** (derive from the artifact), **D163** (the crash class + the one-owner-for-a-marker rule), **D130**
(the format-hunt this prevents), **D125** (the ship boundary).
→ `05`, `07`, `11`, `product/shared/memory-model.md`. Files: `product/shared/schemas-runtime.md` (new),
`product/shared/{schemas.md,memory-model.md}`, `product/scripts/{check_doc_budget.py,check_contracts.py}`,
`scripts/check_enum_coherence.py`, `product/scripts/test_{check_doc_budget,check_contracts}.py`,
`scripts/test_check_enum_coherence.py`.

## D169 — Phase 8b BUILT: the console stops being write-only. A question becomes a typed kind, answering becomes a skill, and the premise that sized the slice was inverted **[DECIDED + BUILT 2026-08-04 (`ad9d910`) — closes the three calls `07` left open; Phase 8 COMPLETE; browser-driven, and the drive found two defects a green suite missed]**
The interaction-model rework D132 deferred and D138 unblocked. The three researched constraints held and none was
re-derived; the three open calls were settled **in design, before code**, as `07` demanded.
- **The finding that sized the whole slice — the premise was backwards.** `07` framed it as "a question wants the
  knowledge base; a request is already served by intake", implying the question arm was cheap. Checked against the
  shipped roster: **all 18 skills either write the KB or read it as input to work, and nothing answered a human's
  question.** So the *request* arm was the one already complete end-to-end (D99 intake form → `202` + ticket →
  D108 drain → "my requests"), and the **question arm was the entire net-new substance of 8b**. That makes the
  slice both smaller than "chat" and concentrated: one capability, `answer`, carries all of the risk. Pressure-
  testing surfaced a **third bucket** the two-way split hid — *status* ("is the deploy done?") — which the cockpit
  already answers with no spawn at all, and which was therefore deliberately given **no new affordance**.
- **Call 1 — the thread is RUNTIME, not committed.** Two precedents pulled opposite ways (`inbox/` RUNTIME vs
  `forecasts/` COMMITTED), and D162's committed-forecast reasoning looked like it transferred. It does not, twice
  over. **(a)** A forecast is machine-generated and its safety is a *linted invariant*; a thread is arbitrary human
  prose, and free text cannot be linted for secrets — committing it is a new leak surface in a repo with a leak
  gate. **(b)** The decisive one: the conversation Claude actually resumes lives in **its own session file**,
  machine-local and cwd-keyed, so committing the thread buys a **readable log and not a resumable conversation** —
  a machine move ends the conversation either way. And a committed transcript is **by construction a second copy of
  every decision it contains**, which is a straight **D80** violation: the spec, backlog and decision record already
  own those facts. So: RUNTIME + pinned (it crosses the process boundary exactly as `outbox/` does), durable
  outcomes land with their existing owner.
- **Retention here governs SPEND, not bytes — the one arm in this package that does.** `--resume` re-sends the
  accumulated history, so thread length is priced *per question*, unlike `demos/`/`forecasts/`/`items/`, which
  bound disk. So the knob is a **rotation**, not a cap: at `config.thread.rotate_at_tokens` (200 000, the owner's
  number) the thread writes its own handoff, drops `session_id` and starts fresh — **D92's disposable-conversation
  law applied to the thread**. Its handoff is a **separate file** by necessity: `handoff.md` already has two authors
  (the orchestrator's prose, `drain.py`'s machine block) and a third writer would break exactly the split that makes
  it work.
- **Call 2 — the HUMAN classifies, at the console.** Two affordances, no model in the routing path. The split is
  structural, not taxonomic: **who is blocked differs.** A request queues and the human walks away; a question is
  worthless unless an answer arrives. Rejected: classify-at-drain (classification would only happen when a loop is
  live, so a 2am question pays a cold start merely to be *routed*, and a misfiled request comes back as chat rather
  than a ticket) and a daemon-side classifier (the master-rule objection no longer bites, but it buys a model call
  to rediscover what the human already knew). Making the human choose also makes **cost honest** — an Ask spawns
  Claude, a Request is free until the loop picks it up.
- **Call 3 — loopback-only, and declining cost no code.** `REMOTE_KINDS` is a **positive** allowlist, so a new kind
  is loopback-only unless someone writes it in. A question is run into `claude -p` verbatim, so it clears **D112**'s
  authoritative-prompt bar *more easily than a forged verdict*: `notes` is free text bolted to a bounded decision, a
  question **is** the whole prompt. The conversation is **readable** remotely (a read is precisely what Socket A
  serves) and the **composer** is not — the panel says why instead of offering a control that would 404. Any future
  remote path rides the **Tailscale-only** carve-out, never a TLS-terminating proxy. Pinned by a test so a future
  kind cannot be waved through by forgetting the line exists.
- **Who spawns the answerer — the daemon, and D132's wording was already false.** "The daemon never calls Claude"
  has not described the shipped system since the D123 runner, which spawns `flock -n orchestrator.lock claude -p`
  on the user's own auth. So the runner's trigger set simply gains `question`; the architecture does not change.
  What *is* new is a **separate `RUNNER_ANSWER_PROMPT`** — kept distinct rather than folded into the resume prompt
  behind a conditional, because the failure mode of getting it wrong is **a session that starts building unattended
  because somebody asked it a question**. A batch containing one drivable message keeps the resume prompt (the loop
  drains every kind at its boundary, answering on the way past); questions-only gets answer-and-stop. Asserted
  against the **argv actually exec'd**, not the branch that chose it.
- **`question` sorts LAST at the boundary, and `answer` is a side-door.** It is the only kind that changes no build
  state, so answering must never sit in front of resuming a parked ticket. `answer` has no `loop.md` node because it
  has no edge — declared a side-door, which took the contract linter's advisory to zero.
- **The browser drive earned its keep for a TENTH time — the D147/D156 shape held again: the logic was fine and both
  defects were in the interaction shell.** **(1)** A posted question was **invisible until answered** — the POST
  returned `202`, the box cleared, and the panel showed nothing; on a cold start that is minutes of a human
  wondering whether anything received them. Every mechanical test passed straight through it. Fix: the read-model
  **joins unanswered inbox questions into the view** as pending turns marked *waiting for an answer* — display only,
  reading two files it already reads, so `answer` remains the thread's single writer. **(2)** Writing the test for
  that fix exposed a second: the **absent-thread early return skipped the merge**, so the *first question a project
  is ever asked* — the one case that matters most — would also have rendered as nothing. The panel also reuses the
  page's own `humanGap` rather than printing a raw ISO (the 9a residual) and puts each hint **before** its input
  (the other one).
- **Rejected / not built:** a per-thread list with switching (no stated need, and thread-switching UI is cost
  without a user); a "answering…" progress state (nothing streams, and the answer may wait on a boundary or a
  relaunch, so *"waiting for an answer"* is what is actually true); a status affordance (the cockpit has it).
*Why it matters:* every human message to this system was previously a **command with no reply channel** — a result
surfaced as state, by ticket. The master rule forbids a hosted program in Claude's request path; it never forbade
the project answering a question locally, and the distinction is what makes "talk to the project through the
website" buildable without overturning D3.
**Verification:** 778 tests (from 721) + 5 gates green; end-to-end against a live daemon on the 9a drive target
(`POST /api/question` → `202` → durable inbox record → `drain.py list` classifies and sorts it last); rendered in
real headless Chrome in **both light and dark** mode. **Left unproven and logged in `07`:** the 200k **rotation**
executes inside `answer` at drain time and no test crosses the threshold, and **answer quality** is unmeasured —
no real project has been asked a real question.
**Supersedes / corrects:** **D132**'s "the daemon never calls Claude" (already false in the shipped system, now
stated); `07`'s "a question wants the knowledge base" premise (inverted — there was no KB query capability); and
`07`'s "one-line WSL opt-in" **as it applies to this machine** (no `.wslconfig`, and `pid1` is `init(Ubuntu)` with
no systemd, so the `enable-linger` arm needs systemd enabled first — the `vmIdleTimeout` arm is still one line, and
neither is taken).
**Builds on:** **D93/D108** (the typed inbox + consumed-set, reused unchanged), **D123** (the runner), **D112**
(the remote boundary), **D99** (the console + "my requests"), **D92** (disposable conversation → the rotation),
**D80** (why a committed transcript is a second owner), **D166** (the browser-drive discipline).
→ `05`, `07`, `10`, `11`. Files: `product/skills/answer/SKILL.md` (new), `product/scripts/{bus.py,drain.py}`,
`product/shared/{schemas.md,schemas-runtime.md}`, `product/templates/{loop.md,orchestrator-CLAUDE.md}`,
`product/commands/start.md`, `product/scripts/{test_bus.py,test_drain.py}`.

## D170 — Phase 8b DRIVEN: answer quality is measured and good, the 200k rotation finally executed, and driving it found three defects — one of them a correctness bug in the skill's own prescribed step order **[DRIVEN 2026-08-04 — closes BOTH residuals `07` logged against D169; no product change in this entry, the three defects are logged OPEN in `07`]**
D169 shipped 8b and logged two things it could not prove: the **rotation had never executed**, and **answer quality was
unmeasured**. Both are now closed by a real drive, and the drive earned its keep for an **eleventh** time.

- **The method is the load-bearing part: the grading session must not be the answering session.** An answer about
  *this* project, graded by a context that already read the record, measures nothing — the grader cannot tell a
  recalled fact from a retrieved one. So the drive ran the **shipped argv verbatim**
  (`flock -n orchestrator.lock claude -p "$RUNNER_ANSWER_PROMPT"`, the prompt string read out of `bus.py` rather than
  paraphrased), which buys a genuinely cold context **for free** and exercises the real away-path at the same time.
  Four independent runs. Questions were posted through the real console (`POST /api/question` → `202`), never
  hand-written into `inbox/`.
- **Quality: good, and specifically good at the thing that needed proving.** Two traps were designed against
  *certain* ground truth in the fixture. **(a)** "What root cause did CHG-2's debug report find?" — the file
  **exists** and contains only the placeholder string `root cause`. That is the hard version of the trap: a file at
  the expected path is an invitation to confabulate. Every run answered **"the record does not say"**, and the best
  of them enumerated *where it had looked* (git history, `docs/decisions/`, `docs/`, `backlog.md`) before concluding —
  negative evidence, not a shrug — and refused to guess between "debug never ran" and "ran but was never written
  down". **(b)** "Do shared links expire, what TTL?" — recorded only as an unresolved **branch** in CHG-1's forecast;
  answered **"undecided, deliberately"**, citing the branch. The control question (what must the human supply for
  CHG-1) came back exact — `SHARE_BASE_URL` + `SHARE_LINK_SIGNING_KEY` at the event-5 setup checkpoint — with the
  no-credential-in-the-thread rule applied **unprompted**.
- **It detected a fabrication it did not author.** The fixture's pre-existing thread turn cites
  `docs/decisions/0004-ledger-store.md`; there is no `docs/` in that repo at all. Two runs independently flagged the
  prior answer as invented rather than inheriting it. That is the D169 failure mode — *an invented answer about your
  own project is indistinguishable from a real one* — caught in **existing history**, which is the case no test
  reaches. It also found two record inconsistencies **nobody planted** (`state.json` says `execute`/`current_item:
  CHG-1` while CHG-1's park says `create-forecast` with its token open; a third forecast `CHG-2.json` exists
  `frozen` but unparked), reported both, and repaired neither — the read discipline held under temptation.
- **`07`'s proposed cheap partial was based on a false premise, and checking it changed the plan.** `07` offered "a
  unit test over the estimate-and-decide half, leaving only the write unproven". **There is no such half.**
  `rotate_at_tokens` appears **only** in `answer/SKILL.md` prose and the two schema docs; `bus.py` merely *displays*
  `rotations`. Estimate, decide, distil, clear and increment are **all** model behaviour with **no seam** — a unit
  test cannot reach any of it. The option neither `07` nor the maintainer had listed **dominates both**: shrink
  `config.thread.rotate_at_tokens` in a fixture and drive it, which proves the **whole** path including the write,
  needs no product change, and costs one run. Same shape as D169's inverted premise: the recorded framing, not the
  work, was the expensive part.
- **DEFECT 1 (correctness, shipped) — `answer`'s prescribed step order can double-answer.** `SKILL.md` runs
  **4 append → 5 rotate → 6 `drain.py record`**. But rotation **clears `turns`**, and `turns` carry the idempotency
  anchor step 2 depends on ("skip anything already answered"). A crash in that window leaves the message
  **unrecorded** *and* the anchor **destroyed** — so the retry answers it a second time, which is the one outcome the
  anchor exists to prevent. The drive's answerer **noticed unprompted, inverted the order, and said why**. Fix is a
  swap of 5 and 6; logged OPEN in `07` rather than patched here, because capture is not build.
- **DEFECT 2 (design, not a typo) — rotation LAUNDERS a fabrication into durable memory.** The handoff restates the
  fabricated Postgres/SQLite rationale as **sourced fact** ("Answered from `docs/decisions/0004-ledger-store.md`…
  6x-slower query planner") with **no trace of the caveat** two earlier runs had raised. Rotation is lossy
  compression; it dropped precisely the caveat that mattered, and it cleared the turns holding the evidence. The next
  session starts **primed with the invention as established**. This is worse than the original failure mode because
  there is now a *mechanism that promotes it*: a distillation inherits the authority of the record while shedding the
  doubt attached to its claims. It is a question about what a distillation **owes to claims it can no longer verify**,
  not a bug with an obvious patch — so it is logged as a design question, not a fix.
- **DEFECT 3 (surface, found only by rendering) — a rotated thread renders as a cold start.** After rotation the
  Conversation panel shows **"nothing asked yet"**, byte-identical to a project that has never been asked anything.
  Six exchanges appear **erased**, with no sign a handoff exists. It is not a data problem: `/api/state` serves
  `{"active": false, "rotations": 1, "turns": []}`, so the page already has everything needed and renders the wrong
  string anyway. Render-layer only. Unreachable before this drive **because it only exists after a rotation**.
- **The trust precondition re-verified on CLI 2.1.220, and REFINED.** `/start` records that a `claude -p` in an
  untrusted workspace has no grant path. Measured here: it does **not stall** — it proceeds **READ-ONLY**, composes a
  complete correct answer, and **silently fails to persist it**, printing `Ignoring 10 permissions.allow entries from
  .claude/settings.json: this workspace has not been trusted`. That is worse than stalling in the away path: the
  runner sends stdout to `DEVNULL`, scores no-progress, backs off, **re-spawns and burns another full answer**, and
  hard-stops with an alert the human cannot act on. **The answer is computed before the write is attempted and there
  is no writability precondition** — logged OPEN in `07`; a cheap probe before the expensive work turns a silent loss
  into a specific, actionable alert.
*Rejected:* **building a second rich-record target** — `~/drive-demo` is a real brownfield project with a genuine
knowledge base, but it is on an **older, different workflow kit** (its `drain.py` has no `question` kind, no `answer`
skill, no `thread/`) *and* it is the maintainer's own product repo, so driving 8b there needs a real `/update` on live
work; the fixture's own record turned out rich enough to design certain-ground-truth traps against. **Forcing the
writes with `--permission-mode acceptEdits` / `--dangerously-skip-permissions`** — it changes the plumbing under
measurement and bypasses the `ask` floor the runner deliberately does **not** bypass; the honest fix was the one-time
trust the platform itself names.
*Why it matters:* `answer` is the one capability whose failure is **invisible by construction** — a confident wrong
answer about your own project looks exactly like a right one, which is why D169 could not close it with tests and why
it needed a human-graded drive. It passes. The residual risk moved somewhere unexpected: not to the answering, but to
the **rotation that summarises it**.
**Verification:** four runs on the shipped argv; thread **2 → 10 turns**; watermark advanced and `drain.py list`
`pending_count: 0`; rotation asserted mechanically — `session_id` `None`, `rotations: 1`, `turns: 0`,
`thread/handoff.md` 3 912 B; console rendered in real headless Chrome at **three** states (all-pending, answered,
post-rotation). Fixture `config.json` restored afterwards; the rotation evidence deliberately left in place.
**Supersedes / corrects:** `07`'s "a cheap partial: a unit test over the estimate-and-decide half" (**no such half
exists in code**); `07`'s two Phase-8b residuals (both CLOSED); `/start`'s untrusted-workspace wording (**read-only,
not stalled**).
**Builds on:** **D169** (8b), **D123** (the runner + its argv), **D108/D93** (drain + watermark), **D166** (the
browser-drive discipline, eleventh payoff), **D92** (disposable conversation → the rotation).
→ `07`, `11`. Files: none — capture only; the three defects are OPEN in `07`.

## D171 — Phase 9c org mode: the review bundle is a PER-ITEM SQUASHED DIFF, and the "read-only ingest gates" question was anchored to the wrong node — the hazard is the COMMIT gate, which needs a third `checks.sh` state **[DECIDED 2026-08-04 — settles `07`'s org-mode questions (1) and (3) and RE-ANCHORS (2). BUILT by D174 (2026-08-05); all three calls shipped as decided. ⚠ ONE PREMISE RE-GROUNDED: "an empty `checks.env` deadlocks org mode at its first commit" is TOPOLOGY-DEPENDENT — true under D174's `project_root: "."`, but inverted under D161's literal external path, where the backstop cannot fire at all and is silently disarmed instead. The third state ships either way, for the stronger reason]**
Two of D161's three deferred calls are now taken, and grounding the third against the shipped code moved it to a
different part of the system than `07` recorded.

- **(1) The review-bundle format — a PER-ITEM SQUASHED DIFF, plus a metadata sidecar kept OUTSIDE the diff.** The
  bundle crosses a **governance** boundary, not a history one. The loop's git history exists to serve **D48 resume**,
  and that is served **entirely inside the private clone** — nothing about resume requires the company repo to ever
  see a loop commit. A squashed diff makes the **human the author by construction**, which is what D161's "user and
  user only, enforced **structurally**, not by discipline" actually asks for, and it carries **no loop commit
  messages** across (those quote ticket ids and knowledge prose *about the company's own code* — derived IP flowing
  back in, and noise their reviewer cannot interpret). It also yields a clean invariant that matches the loop's
  existing one-commit-per-item discipline: **one item → one bundle → one human commit.** The sidecar carries item id,
  the base `describes_sha` the work was done against, and the plan/changelog summary — deliberately **not** in the
  diff, so it can never land in company history.
  *Rejected:* a **branch** in the private clone fetched by the checkout — best tooling, but the path of least
  resistance (`git push`) is **exactly the wrong act**, landing machine-authored commits upstream, and it wires a
  remote from the company checkout to the private brain; **`format-patch`** — preserves granularity and needs no
  remote, but carries loop authorship and a whole series is easy to `git am` unreviewed. Kept as a possible **opt-in**
  for unusually large multi-commit work, never the default.
- **(2) RE-ANCHORED: `ingest` is not where the hazard lives.** `ingest` **runs no gates at all today** — there is no
  test/build step in the skill — so "confirm ingest gates run read-only" was very nearly a no-op as written. The real
  exposure is the **commit gate, which fires far more often**: `/start` brownfield **ADOPTS** the project's existing
  formatter/linter/typechecker/test into `.workflow/checks.env`, and `checks.sh --check` runs them **repo-wide**,
  invoked by the `commit` skill *and* registered as git's `pre-commit` hook. In org mode that means **every loop
  commit in the private clone runs the company's full suite and linters on personal infra**. Sharper still:
  `checks.env` is **`source`d** and the fixers run through **`eval`**, so adopted values execute as written — a
  `TEST="npm test"` on an unknown company repo is **arbitrary code execution** on the maintainer's machine via
  lifecycle scripts, plausibly against real services with whatever credentials are in the environment. The rule org
  mode needs is therefore stronger than "do not run their suite": **never execute anything out of the checkout** —
  no install, no build, no test, no hook.
- **…and the obvious fix does not work, which is why this is a build item and not a note.** An empty `checks.env`
  **deadlocks org mode at its first commit**: `checks.sh` deliberately **fails the commit closed** the instant source
  exists under `project_root` with no stack gate wired, precisely so a missed re-wire cannot silently disarm the gate.
  So org mode needs a **third declared state** — *deliberately unwired because we must not execute their code* —
  distinct from *not yet wired*, still running the three **stack-agnostic** coverage gates (which read only
  `.workflow/` and are safe by construction). **Consequence to carry into the build:** org-mode `verify` degrades to
  **artifact conformance** (plan vs changelog vs spec), and all runtime checking moves to a human `qa` checkpoint in
  the user's **own** checkout.
  *Verified, not assumed:* `codemap.py` is **static** — `ast` + `re` only, no `subprocess`/`exec`/dynamic import (its
  single `__import__` hit is a comment listing known gaps) — so the code map is safe to build over company code, and
  the read-only story survives its most obvious counter-example.
- **(3) Archive-to-git stays local-only by default — and becomes VISIBLE rather than merely stated.** D161 records
  "a backup remote is a deliberate act the maintainer takes against his own policy", which is exactly the kind of
  sentence that silently stops being true. So: **no remote by default**; adding one requires an explicit
  acknowledgement key in `config.org`; and the console shows a **badge whenever the private tree has a remote**. That
  converts a governance caveat into a **recorded, visible fact** — the same move D80 makes for status.
*Why it matters:* org mode's whole promise is a boundary that holds when nobody is watching. Two of the three calls
here are about making a guarantee **structural** (the human authors the commit; the executable gate is off by
declaration) rather than **remembered**, which is the only form that survives a rarely-run optional mode.
**Verification:** grounded against shipped code, not reasoned — `skills/ingest/SKILL.md` (no gate step),
`commands/start.md` (brownfield *adopt*; fail-closed backstop), `templates/checks.sh` (`source`d `checks.env`,
`eval`'d fixers, repo-wide `--check`), `scripts/codemap/codemap.py` (static). No code written; 9c remains unbuilt.
**Supersedes / corrects:** `07`'s org-mode item (2) — the hazard is the **commit gate**, not `ingest`; D161's
"its exact form (branch / `format-patch` / squashed diff) deferred to build" — now decided.
**Builds on:** **D161** (org mode), **D48** (resume-from-git — why history stays in the private clone), **D110**
(the `guard.sh` push floor), **D130** (the deferred adopted-code-gates hazard this sharpens), **D80** (make the fact
visible and owned).
→ `07`, `11`. Files: none — design only.

## D172 — the three Phase-8b-drive defects are fixed, and the laundering one is answered STRUCTURALLY: a distillation may drop, point and quote, but never restate **[BUILT 2026-08-04 — closes all three defects `07` logged against D170; the away-path item stays OPEN with its recorded remedy CORRECTED]**
D170 found three defects by driving what a green suite had passed and captured them rather than patching them. All
three are now fixed. The middle one was the only genuinely undecided call, and it moved the design.

- **DEFECT 1 (correctness) — the step order is swapped: append → record → rotate.** Rotation clears `turns`, and
  `turns` carry the idempotency anchor, so the shipped order left a window where a crash destroyed the anchor *and*
  left the message unrecorded — and the retry answered twice. **Two things were checked rather than assumed.**
  (a) The swap leaves the **append→record window unchanged** — nothing sits between them, so the anchor still covers
  exactly the case it was written for; that is now an assertion (`record == append + 1`), not a belief.
  (b) The half nobody had written down: **post-rotation the anchor is unreachable** (there are no turns) and
  idempotency rests on the **drain watermark alone**. That is correct *because* the record now precedes the
  rotation — a rotated message is already consumed and can never come back pending — but unsaid it is exactly the
  reasoning a future editor re-breaks, so it is in the skill.
- **…and the mechanical guard is real, with a ceiling stated out loud.** `test_answer_skill.py` parses the numbered
  steps out of the **real shipped `SKILL.md`** and refuses an order that puts a `turns`-clearing step ahead of the
  record. **Mutation-tested**: the pre-fix order was re-injected and both ordering assertions fired. Its honest
  ceiling, recorded so nobody mistakes it for more: **it proves the SPEC still says the right thing; it cannot
  prove the model FOLLOWS it** — there is no seam between the prose and the behaviour, which is the same no-seam
  finding D170 hit with rotation. Behaviour is proven by driving, not by this file. One measured correction along
  the way: matching the step *body* is wrong — step 2 legitimately mentions `drain.py record` while explaining the
  anchor — so a step is identified by its **bold directive**, not by a substring.
- **DEFECT 2 (design) — the laundering is answered by REMOVING the payload, not by policing it.** The handoff now
  keeps only what is **not re-derivable**: the human's turns **verbatim**, open threads, outcomes that landed with a
  real owner **as pointers**, contradictions **as the two pointers that contradict**, and the rotation count. It
  carries **no project prose answer at all**. The argument is not taste: `answer` answers from the project's own
  record **by construction**, so every answer is re-derivable from it — and **an answer that is *not* re-derivable
  is precisely an invented one**. Dropping the prose therefore discards exactly the hazard and nothing else, and it
  makes laundering **impossible rather than policed** — the same move D161 makes for the org-mode git boundary.
  It also *shrinks* the handoff, which is what rotation exists to do.
- **The evidence killed the obvious alternative.** The real artifact was read, not imagined: the fabricated answer
  was restated as *"Answered from `docs/decisions/0004-ledger-store.md`…"* — **it already carried a citation** — while
  the **same file, three paragraphs later**, said `docs/decisions/` was empty. So **carrying provenance forward
  forwards the FABRICATED provenance** and makes the invention look better-sourced, and **refusing unsourced claims**
  cannot fire because the claim *appeared* sourced. Only **re-verification** catches it, and it re-reads the record
  at the exact moment rotation exists to cut per-question cost, with the same model grading itself. The handoff also
  hand-wrote a "Live state" section that was a **second copy of `parked/`** — the D80 violation `/dispatch` already
  avoids by *mirroring* — and the carry-list drops that too.
- **The rule is general and is stated ONCE.** `memory-model.md § the distillation law`: **a distillation may DROP,
  POINT and QUOTE — it may never RESTATE.** Restating is the move that converts a claim into a fact.
  **The other summarising surfaces were checked before generalising, and the shape is graded, not uniform** —
  `# Lessons` distils but drops its source **to git**; `/dispatch`'s `handoff.md` is largely already compliant
  (it **mirrors** `parked[]` rather than restating it, `base_sha` is a pointer, the drain block is machine-owned)
  and sits on an intact git/backlog/`parked/`; **`precompact` is not a distillation at all** — it copies
  `handoff.md` verbatim with a named truncation notice. The thread rotation is **the only place in the package
  where the distillation becomes the sole surviving copy**, which is why the law is binding there and guidance
  elsewhere. Deliberately **not** copied into `document`/`dispatch`/`research`: one owner, and they inherit it.
- **DEFECT 3 (surface) — a rotated thread is a handoff, not a cold start; and a dead-lettered question stops
  promising an answer.** The panel now reads *"conversation handed off (rotation N) — the earlier turns are
  distilled into thread/handoff.md, and the next question starts fresh from it"*, and a dead-lettered question
  renders *"dead-lettered — no answer is coming"*, dimmed and dotted. Both were render-layer only: `rotations` was
  already on the wire, and the dead-letter flag is computed from the **same drain-block read `requests()` already
  does** — no new source. The dead-letter **reason** is deliberately left out of the panel: the "my requests"
  surface owns it. Newly testable, and tested: the real shipped `renderThread` runs under node with a small DOM
  shim, in **both** directions — a project nobody has asked still says "nothing asked yet".
- **The away-path item's recorded remedy is WRONG, and checking it is the only reason that is known.** `07` proposed
  "a cheap **writability probe** before answering". The daemon is plain Python with **no permission layer**, so it
  writes `.workflow/` fine in an untrusted workspace — the probe passes every time and **never fires**. The
  detectable precondition is a **trust-record read** (`~/.claude.json` → `projects["<abs path>"]
  .hasTrustDialogAccepted`, verified present on 2.1.220; **12 of 26** tracked projects on this machine are `false`).
  That is a different item: it reads an **undocumented platform-internal file**, so it must **fail OPEN** or a
  format change stops the runner answering questions entirely. Deferred to its own slice — it changes the runner's
  spawn decision and needs a drive against a genuinely untrusted workspace. **Third time in three phases** that a
  recorded framing, not the work, was the expensive part (D169's inverted premise, D170's non-existent code seam).
*Rejected:* **carrying provenance + a confidence flag** and **refusing to distil an unsourced claim** — both defeated
by the fabricated citation above; **re-verifying on rotation** — the only one that would catch it, at the cost of
re-reading the record precisely when rotation is trying to save that cost, and with the same model grading itself;
**a thread-local fix with no general rule** — the shape recurs at every summarising step, and the next one built
would have rediscovered it; **tightening `/dispatch`'s in-flight-decision clause in this slice** — its source
survives, so it is guidance not a defect, and the law now covers it without touching the path every session uses.
*Why it matters:* the residual risk after D170 was not the answering but **the rotation that summarises it**, and
the fix that survives is the one that leaves nothing to police. Defect 3 also re-earns the render discipline for a
**twelfth** time, and sharpens it: it was **unreachable until the rotation had run**, which is the argument for
rendering the state you just *created*, not the state you started from.
**Verification:** **758 tests** green (743 → 758: +5 skill-order, +4 thread read-model, +6 real-`renderThread`
under node), 5 meta-gates green. The ordering guard **mutation-tested** by re-injecting the shipped bug. Both render
states shot in **real headless Chrome** against a *copy* of the rotated fixture (the maintainer's `~/drive-9a` left
byte-untouched), questions posted through the real `POST /api/question` and dead-lettered through the real
`drain.py record --dead-letter`. `schemas.md` measured by hand at **~20.6k** of the 25 000 ceiling.
**Supersedes / corrects:** `07`'s away-path remedy (**a writability probe cannot detect an untrusted workspace**);
`07`'s three D170 defects (all CLOSED); `schemas.md`'s rotation bullet (it now states the order and the carry-list);
`05`'s `thread/` layout note (it named the file but not what may go in it).
**Builds on:** **D170** (the drive that found all three), **D169** (8b), **D93/D108** (drain + watermark — what
idempotency falls back to), **D80** (one owner; the law is stated once and pointed at), **D38/D61** (the memory
model this law joins), **D166** (the browser-drive discipline, twelfth payoff), **D161** (structural over policed).
→ `05`, `07`, `10`, `11`. Files: `product/skills/answer/SKILL.md`, `product/shared/memory-model.md`,
`product/shared/schemas.md`, `product/scripts/bus.py`, `product/scripts/test_answer_skill.py` (new),
`product/scripts/test_bus.py`.

## D173 — the away path refuses to spawn into a workspace it cannot save its work in, and the trust read that decides it is exact-path, absence-aware, and fails open **[BUILT 2026-08-04 — closes `07`'s away-path item; REVERSES the D123 residual that declined this gate]**
**The call:** the runner **blocks the spawn** when the workspace reads untrusted, and fires **one** away alert naming
the exact fix the platform itself prints — including the manual flag, because the trust dialog does not render in
some WSL terminals. It is a live read, not a latch: granting trust re-arms the runner with no restart.
**Why this reverses D123's residual (b).** That call — "a *warning* in `status`, not a spawn-block … the
stall-timeout is the real backstop" — was sound reasoning on a **false premise**, and the premise was checked before
building rather than after. **MEASURED on CLI 2.1.220:** an untrusted `claude -p` does **not** hang. It discards the
allowlist (`Ignoring N permissions.allow entries … has not been trusted`), proceeds **read-only**, composes a
complete correct answer, fails to persist a byte, and **exits 0 in seconds**. `RUNNER_STALL_TIMEOUT` only reaps a
launch still *running*, so it is never reached: the launch scores no-progress and the away path burns
`RUNNER_MAX_ATTEMPTS` **full answers** before an unactionable hard-stop. **Blocking cannot lose work that survives
today — that path already ends stopped.** It only stops sooner, for free, and says something the human can act on.
**Two recorded framings were wrong, and measurement caught both before any code.**
- **D172 said the signal was `hasTrustDialogAccepted: false` ("12 of 26 tracked projects").** The count was real but
  it is **not the signal**. `claude -p` does **not create** a project record (measured: two untrusted runs, both
  directories still absent afterwards), so the *ordinary* untrusted case — never opened interactively — has **no
  entry at all**. The predicate is **not `True`**. This also means the `status` and `/start` warnings that already
  shipped, both keyed on `is False`, **could not fire on the common instance of the bug they warned about**.
- **`07` feared trust might inherit from a trusted parent** (a false negative would silently stop answering). It
  does not: a fresh directory under a `true`-recorded parent is **still untrusted** (measured), so trust is
  **exact-path** and there is no ancestor chain to walk. `realpath` is consulted only for a *trusting* answer,
  because erring toward trusted is the fail-open direction.
**Fail-open lives on the READ, not in the absence of a gate.** This parses an **undocumented platform-internal
file**, so absence may be read as untrusted only while a **schema-health probe** proves the file still speaks the
format (it parsed, `projects` is a dict, some entry still carries the flag). Unreadable, renamed or reshaped ⇒
**unknown** ⇒ spawn exactly as before. A format change must never be why a human's questions stop being answered.
*Rejected:* **keeping it warning-only** — the warning could not fire on the common case, and the burn continues;
**spawn-once-then-stop** — still pays a full answer to learn something a file read already knows, and the cost it
saves is the fifth burn, not the first; **`is False` only** — the narrowest predicate, and measurably blind to the
ordinary case; **inheriting trust from a trusted ancestor** — measured not to be how the platform behaves, and it
would have silently un-gated the very case this exists for; **hard-stopping** rather than declining — a hard-stop
would need a restart after the human does what the alert asked, and the whole point is that it self-heals.
*Why it matters:* `/start` already writes the trust flag, so a properly-started project is trusted long before the
runner could fire — this gate is for the projects that *aren't* (started before that step, a failed write, a moved
repo path), and those are exactly the ones nobody is watching. It also makes an **untrusted daemon go idle** rather
than pin itself open on a condition no amount of waiting resolves. **Fourth phase running** in which a recorded
framing, not the work, was the expensive part (D169's inverted premise, D170's non-existent code seam, D172's
writability probe that cannot fire — and now D172's own corrected remedy, half right).
**Verification:** **801 tests** green (793 → 801: +8 covering no-spawn/alert-once, the actionable alert text, absence
as untrusted, exact-path-no-inheritance, both fail-open arms, re-arm-on-trust, and the idle vote), 5 meta-gates
green. The gate is **mutation-tested** three ways — disabling it, restoring the old absent⇒unknown predicate, and
deleting the schema-health probe each fail exactly the tests that own them. **DRIVEN** against a genuinely untrusted
workspace with the **real** `claude` on `PATH` (no stub — a failed gate would have burned a real answer) and the
**real** `~/.claude.json`: no `flock -n claude` process spawned, exactly one away alert off a real loopback webhook,
the question still queued. The drive also caught a **render defect the unit tests could not** — `status` printed the
placeholder `projects["<this repo>"]`, unactionable precisely where a human reads it; the repo path now rides in
`readiness()` so the surface names the exact key. (A first drive at 12s proved nothing and was fixed, not believed:
the janitor ticks at 30s, so the runner had not run.)
**Supersedes / corrects:** **D123 residual (b)** (the gate is now built, and its stated backstop was inert);
**D172's remedy** (right file, wrong predicate — `not True`, not `is False`); `01`, `11` and `schemas-runtime.md`
(all three said an untrusted `claude` *stalls*; it exits 0); `07`'s parent-inheritance worry (measured unfounded).
**Builds on:** **D172** (which named the file to read), **D123** (the runner this gates), **D94** (the daemon
hosting it), **D101** (the away-alert taxonomy this reuses), **D80** (one owner — the trust read and the alert
share `claude_config_path()`), **D166** (the render discipline, thirteenth payoff — and again it was the state we
*created*, an untrusted workspace, that showed the defect).
→ `01`, `07`, `11`. Files: `product/scripts/bus.py`, `product/scripts/test_bus.py`,
`product/shared/schemas-runtime.md`.

## D174 — Phase 9c org mode BUILT and DRIVEN: the brain IS the clone, the derived tree is namespaced, and the boundary is verified rather than applied **[BUILT + DRIVEN 2026-08-05 — six increments, `3816b62`→`1ad7707`; 835 tests (801→835), 5 meta-gates green, exit-gate drive 27/27. CLOSES Phase 9, and with it the last phase on the roadmap. CORRECTS D161's `project_root` and re-grounds D171's deadlock premise. ⚠ THE "LAST PHASE" CLAUSE IS SUPERSEDED BY D175 (2026-08-05, same day): it was accurate as a description of the plan then, and D175 **decided** to sequence the remainder as **Phase 10** — a scope reversal, not a correction of this entry. Everything else here stands]**
Org mode was the last unbuilt slice and the one with **zero prior multi-repo / multi-committer evidence**. Two of the
three things that cost time were, again, **recorded framings rather than the work** — which is now five phases running
(D169's inverted premise, D170's non-existent seam, D172's probe that could not fire, D173's predicate, and these).

- **(1) THE TOPOLOGY WAS INCOHERENT AS RECORDED, and it is upstream of everything else.** D161 says `project_root` is
  "an absolute path to the checkout". That cannot hold against three shipped invariants: `/start` writes `rules/`,
  `docs/` and `llms.txt` **under** `project_root` (so it would install into the very checkout that must stay
  pristine); `verify_check.py` binds the item to the **staged diff of one repo** (D161's own argument against the
  two-repo split); and `checks.sh`'s backstop resolves `git ls-files -- "$proot"`, which on an external absolute path
  exits **128 with empty stdout** — the `2>/dev/null` eats the fatal, `grep -q` finds nothing, and the fail-closed
  gate **silently no-ops**. **Call: the brain IS the private clone, `project_root: "."`** — org mode is brownfield
  cloned rather than in-place, with zero footprint on the operator's own checkout. Every single-repo guarantee then
  holds unchanged, which is exactly why D161 rejected the two-repo split in the first place. **The "third
  `project_root` value" dissolves.**
- **(2) That topology has a consequence the design had not reached, and it is the LEAK BOUNDARY.** A real company repo
  very likely already has `docs/`, so the brain's derived IP would interleave with — and clobber — the owner's files,
  and the bundle's exclusion would degrade from **two directories to a per-file list that must stay correct forever**.
  So **`docs_root` is ADOPTED as its own key with its own owner** (absent → `project_root`, so the split is invisible
  in every other mode). Org mode sets `.workflow`, the brain then owns exactly **`.workflow/` + `.claude/`**, and the
  exclusion list is two entries. The brief moves to **`.claude/CLAUDE.md`** — *verified against the live platform
  docs, not assumed*: it is a first-class project-instructions location loaded at project scope, and discovered files
  **concatenate rather than override**, so the brief loads every session while the owner's root `CLAUDE.md` stays
  byte-untouched and still serves as the ingest intent-seed (which is what D161 asked for and had no mechanism for).
- **(3) The third `checks.sh` state, and D171's premise re-grounded.** D171 called the empty-`checks.env` deadlock the
  reason for a third state. That premise is **topology-dependent**: it holds under the settled `project_root: "."`
  and is **inverted** under D161's literal wording, where the backstop cannot fire at all. Either way the state is
  needed, so it ships — `STACK_GATE_NONE="<reason>"`, which short-circuits the backstop *and* refuses to execute
  **anything** from `checks.env` in either mode, prints the reason every run, and **reports rather than obeys** a
  command set alongside it. That last part is the structural half: a re-run of `/start`'s brownfield stack adoption
  cannot silently re-arm `eval` on foreign code.
- **(4) The review bundle — the one net-new capability — verifies its own output.** `git diff` excludes the brain by
  pathspec, and then the producer **parses the paths back out of the bytes it just produced** and refuses to write a
  bundle that still names one. An exclusion only ever *applied* is a policy; one *checked afterwards* is a gate. It
  also refuses added lines referencing `.workflow/` inside the owner's own files — the path is theirs, the content is
  ours, and path exclusion cannot see it.
- **(5) org-align is align with a SECOND ANCHOR, exactly as D161 required — no new machinery.** `describes_sha` beside
  `base_sha`; fetch read-only; scope the union of both diffs; **stamp last and only on a completed scan**, because
  stamping early marks unread upstream commits as read, which is the one error the anchor exists to prevent. A
  non-trivial upstream conflict raises a checkpoint, never an autonomous merge.
- **(6) The governance caveat becomes a rendered fact.** `guard.sh` blocks `git remote add/set-url/rename` in org mode
  unless `org.archive_remote_ack` records a reason (failing **open** outside org mode — an ordinary project must never
  be blocked from managing its own remotes), and the console badges the **state** for as long as a push path exists,
  so a remote added out of band still shows. Read from `git remote`, never from config: the hazard is the remote that
  is actually there. The fetch-only `origin` (push url `no_push`) is correctly not one.

*Rejected:* keeping D161's literal external `project_root` (breaks the three invariants above); a **second private
clone** at an external path (the two-repo split D161 rejected by name); keeping `docs/` at the root and **gap-filling**
(turns a structural boundary into a policed per-file one — the failure mode zero-footprint exists to avoid);
**refusing** to bootstrap org mode when the repo already has `docs/` (converts a design problem into an availability
problem on a large share of real repos); deriving the third `checks.sh` state from `config.org` presence (conflates
"is org mode" with "the gate is deliberately off", and leaves a non-org project that must not run its own code with no
path); a `config.org.enabled` toggle (a live topology switch is a **migration, not a setting** — presence *is* the
mode, chosen once at `/start`).
*Verified, not assumed:* `git remote set-url --push origin no_push` kills bare/explicit/`--all` pushes with a fatal
while `fetch`/`FETCH_HEAD` keep working; `.claude/CLAUDE.md` is a project-scope instructions location that concatenates
with the root file; `git ls-files` on an external absolute path exits 128 with empty stdout; `git -C <bad path> remote`
returns **non-zero**, it does not raise.
**Six defects found, five of them by rendering or driving the state we CREATED rather than by reading code** — the
D166 discipline's fourteenth payoff: the org brain budgeted the **owner's** root `CLAUDE.md` (always-loaded, 4000-token
hard wall, fails the commit, remedy forbidden — a large company brief would have deadlocked *every* commit behind a
gate nobody there may satisfy); the bundle hand-off quoted a **brain-local sha** the owner's repo cannot resolve;
the badge's "cannot read git" branch guarded only an exception, so a failed read reported "no remotes" — the one
wrong-direction answer; two shipped files claimed `checks.env` "is gitignored and does not travel" while `/start` and
`/update` ship it **committed** (load-bearing here, since a safety declaration that did not travel would lapse); and
the **drive's own first run was falsely green** — `git init --bare` defaulted HEAD to `master` while the push created
`main`, so both clones came up empty and four assertions passed for the wrong reason (the push refused as "src refspec
does not match any", not by `no_push`; the pristine check compared two empty trees). A harness that cannot fail is not
evidence, which is why the drive is committed rather than run once and described.
**Verification / the exit gate:** `scripts/drive-org-mode.sh` — **pallets/click at a pinned historical SHA
(`94c191c`)**, with **42 of the repo's own later real commits replayed** onto the origin as coworker drift (which
produced a genuine same-file overlap, so the conflict case is present rather than hypothetical). **27/27** on the four
properties that define the mode: **(a) pristine** — the operator's checkout is byte-identical before and after
(content hash over every file, plus HEAD and porcelain), with no `.workflow/`, `.claude/` or git hook appearing, and
work reaching it only when the human applies the bundle (author: the human); **(b) no push** — all three push forms
die on `fatal: 'no_push' does not appear to be a git repository`, origin still byte-identical to the pinned SHA;
**(c) drift** — 42 commits over 51 files detected against `describes_sha`, which the fetch did not auto-advance;
**(d) no leak** — the bundle carries exactly one file, no `Refs:` trailer, no derived knowledge, no intermediate
state. Plus the standing rule: no stack command was ever wired and nothing out of their tree ran.
**Supersedes / corrects:** **D161** — `project_root` is **`.`**, not an external absolute path, and there is no third
`project_root` value; its "never inject the managed block" now has a mechanism (`.claude/CLAUDE.md`) rather than only
a prohibition. **D171** — the deadlock premise is **topology-dependent** and inverted under D161's literal wording;
the third state ships regardless, for the stronger reason. Also corrects `pre-commit.sh` and `rebind.md` on
`checks.env`'s travel.
**Builds on:** **D161** (org mode), **D171** (the three settled calls — bundle form, commit-gate anchoring, local-only
archive), **D48** (resume — why history stays in the private clone), **D110** (the `guard.sh` floor this extends),
**D130** (the adopted-code-gates hazard), **D80** (`docs_root` adopted with a declared owner; the badge makes a
caveat a visible fact), **D166** (render the state you created), **D68** (brownfield ingest, reused wholesale).
→ `07`, `09`, `11`. Files: `product/templates/checks.sh`, `product/templates/loop.md`, `product/commands/start.md`,
`product/commands/rebind.md`, `product/hooks/{guard.sh,pre-commit.sh}`, `product/skills/{commit,align}/SKILL.md`,
`product/shared/schemas-runtime.md`, `product/scripts/{review_bundle.py,check_doc_budget.py,bus.py}`,
`product/MANIFEST.json`, `scripts/drive-org-mode.sh`, + tests.

## D175 — Self-hosting is DROPPED, and Phase 10 opens over the remainder with a spine the premise-check found rather than one imposed: truth-in-shipping **[DECIDED 2026-08-05 — two deliberate REVERSALS of what `11` asserted the same day, plus a scope decision. Re-checks all ten by-space candidates against the shipped tree: SIX are stale. Closes `07`'s dogfooding call and its project-state-view framing; settles the observed layer's two-tier conflict inside `11`]**
Phase 9 closed as the last phase, and `11` said so in three places: *no live phase pointer*, *this was the LAST
phase*, *a menu, not a sequence*. Those were **true as a description of the plan**, and this entry does not correct
them as errors — it **supersedes them by decision**. Two reversals, and the first forces the second.

- **(1) SELF-HOSTING IS DROPPED — "not the right thing for this repo."** Not deferred, not "a later experiment on a
  clone" (which is how D162/D163 parked it and `11`'s Phase 9 header still promised); **cancelled.** Driving this
  project's own implementation with the product is out. **The distinction this repo has always drawn is load-bearing
  and only ONE side moves: *self-hosting* (drive THIS project with the product) is dropped; *dogfood-validation*
  (drive the product against throwaway or foreign repos as EVIDENCE — D52, D125, `drive-org-mode.sh` vs
  pallets/click) is UNTOUCHED and is the entire evidence discipline of this repo.** The maintainer confirmed he
  intends to keep dogfooding whenever needed. Every sweep of the first word had to stop at the second, and four
  sites that name the second (`10-roster` D52, `11`'s Space-1 line, `00-vision`'s D125 note, `03-website`'s console
  MVP) were checked and **left byte-untouched**.
- **(2) PHASE 10 OPENS — because dropping self-hosting removed the only spine the menu had.** With it gone the theme
  could not be assumed, so it was **found by checking premises**, and the finding *is* the theme: **six of the ten
  candidates were stale in the same direction — the tree asserts things nothing produces or checks.** Hence
  **truth-in-shipping: close the gap between what the tree CLAIMS and what it DOES.** Its unusual shape follows
  honestly from that — **more of Phase 10 is correction than construction**, and it corrects the *record* as well as
  the product. **10a** the over-claims · **10b** the portability claim (D89 native-Windows + the D58 trust-UX doc,
  admitted as the weakest fit) · **10c** the project-state view.
- **(3) THE OBSERVED LAYER'S TWO-TIER CONFLICT IS SETTLED — and it was hiding a real defect.** `11` tagged it
  `**[core — build next (D78)]**` in one place and listed it `[stageable]`/`[later]` in two others — **same item,
  two tiers, in the doc that OWNS tier (D80)**; the coherence gate misses it because it checks tag *location*, not
  tag *agreement*. Settled against the shipped tree: `graph.observed.json` occurs in `06`, `11`, `08` and **nowhere
  in `product/`** — no producer, no schema, no consumer — and "build next" had been stale since Phase 2/3 closed.
  **Tier: `[stageable]`**, D83's charter revisit parked with it. But the check surfaced a **separable, live defect
  that exists whether or not the layer is ever built: two SHIPPED files assert it as real.** `codemap.py` rests its
  standing precision-over-recall rule on the layer accreting the missed recall, and `verify/SKILL.md` licenses
  `verify` to drive flows as a pure observer *for* it. **Retract both claims (10a); do not build the layer.** The
  precision bias is right on its own terms — a fabricated edge is sticky and unretractable — and needs no
  nonexistent layer to justify it.
- **(4) THE PROJECT-STATE VIEW SURVIVES, on a different argument, and is RE-AIMED.** `11` called it "the
  self-hosting prerequisite" since 2026-06-30, and that justification evaporated with (1). It was NOT rescheduled on
  inertia: `07`'s original entry carries an **independent** reason — the gap is felt reading a project and "bites
  harder on code projects" — which survives untouched. **Consequence, and it is the substantive half: it is built
  for a TARGET project**, not to read this repo's own `docs/design/`. That is forced twice over — by D125's product
  boundary, and because a meta-only tool cannot be dogfooded and so would get no evidence discipline at all.
- **(5) FOUR CANDIDATES RETIRED as line items — their premises did not rot, they were never real, or the work
  shipped.** ~~*Engineering-feasibility pass*~~ — a **duplicate**: the D69 entry says in its own words that it
  "Formalizes the engineering-feasibility pass". ~~*Arbiter input contract*~~ — `grep -rn 'arbiter'` over
  `product/` and `10-roster.md` is **empty**; the name died into `adjudicate`/`decision-engineer`, and the substance
  is `prioritize`'s. ~~*`@import`-survives-`/compact`*~~ — `grep -rn '@import' product/` is **empty**;
  `orchestrator-CLAUDE.md` reaches its files by explicit *Read* instructions. ~~*Remote control*~~ — **BUILT**, and
  the roadmap had gone stale: D122 shipped the two-socket split in Phase-3 increment 5 (fixed remote port, "Pair a
  phone", stable remote credential, A's verdict-only POST allowlist). The *project-map tab* is what actually
  remains, and its cost was understated — the console is a flat `<section>` list with **no tab machinery at all**.
- **(6) COMMITMENT STORAGE: the question was already answered, so it is RE-ASKED as the D80 one.** "Spec **vs** node
  frontmatter" read as an open fork for two months; the tree shipped **both** (`schemas.md` tags it per spec element
  *and* carries it in node frontmatter). Live question: is the node copy **derived** (one owner, a projection) or
  independently authored (**two owners for one fact**)? It matters because `align` classifies drift *by* commitment
  and `document` reads it — a silent divergence mis-routes drift instead of failing loudly. → `07`, 10a.
- **(7) THE BIGGEST CANDIDATE IS DEFERRED, WITH A TRIGGER — a phase that swallows the backlog is a backlog with a
  new name.** The D69 proportional-rigor triage stays out: D162 already shipped the narrower skill-owned **forecast
  gate** (`grep -rn 'proportional\|rigor' product/` returns exactly **one** hit) covering the case that fires today,
  and a universal triage over every `planner` output is phase-sized. **Trigger: promote on a SECOND narrow gate
  wanting the same triage** — then the duplication is real rather than hypothetical, and the triage has two callers
  to be designed against instead of one. Same discipline applied to the project-map tab, model/effort routing,
  symbol-level paths and the device/QA platform: **each deferral carries a stated reason and what would promote it.**

*Rejected:* keeping "no Phase 10" and picking items off a menu (leaves the remainder unsequenced and unargued — the
condition that let six items rot in the first place); **"credible on someone else's machine"** as the spine (the
tempting theme, and it got *weaker* not sharper — D112, its third leg, turned out already BUILT as D122, leaving
D89 + the D58 doc, and the observed-layer and `verify` defects unhomed); **inventing a feature theme** to make the
phase look tidy; opening Phase 10 as an unthemed cleanup (available and honest, but the premise-check had already
produced a real spine, so settling for none would have thrown it away); building the observed layer to make the two
shipped claims true (the layer is `[stageable]` on its own merits and the claims are the defect — making a false
claim true is the expensive way to stop it being false); dropping the project-state view with self-hosting (its
independent justification survives, and was never withdrawn); scheduling it to read *this* repo's docs (breaks D125
and cannot be dogfooded); folding the D69 triage in (would dominate the phase).
*Verified, not assumed — every scheduling call was grepped against the shipped tree first:* `graph.observed.json`
absent from `product/`; `arbiter` absent from `product/` and the roster; `@import` absent from `product/`; `model:`
frontmatter absent from every shipped agent and skill (so model/effort routing is genuinely unbuilt); `bus.py`
carries the pairing surface and remote socket (so remote control is genuinely built); `hooks/verify_check.py`
already runs `git diff --cached` while `skills/verify/SKILL.md` reads only plan↔changelog (so #8 is real *and*
cheap); `schemas.md` carries `commitment` in both places; `## Key symbols` is an optional extractive aid, so the
symbol-level seam is real. State at capture: `5887279`, **835 tests**, 5 meta-gates green.
**The standing lesson did not weaken — this is the seventh consecutive slice where the recorded FRAMING, not the
work, was the expensive part** (D169's inverted premise · D170's non-existent seam · D172's probe that could not
fire · D173's predicate that could never fire · D174's incoherent topology *and* inverted gate reason · and now
**six of ten candidates stale at once**). Two of the six had rotted so far that the thing they named does not exist.
The operational rule this hardens: **an item whose premise has rotted gets re-designed or dropped, never scheduled
on its original wording** — and the check is a grep of the shipped tree, not a re-reading of the doc.
**Supersedes / corrects:** **D162/D163** (the "separate later experiment on a clone" is cancelled, not pending);
**D78/D83** (tier settled `[stageable]`; the charter revisit parked with it); **D69** (deferred with a trigger; its
"formalizes the engineering-feasibility pass" clause retires that duplicate line item). Historical entries that cite
self-hosting as a *motivation* (**D63**, **D70**, **D121**, **D155**) are left unedited — they record what was true
when made; this entry is the correction.
**Builds on:** **D80** (one owner per fact — the tier conflict, the commitment question, and the sweep itself),
**D125** (the product boundary that aims 10c at a target project), **D52** (dogfood-validation, explicitly kept),
**D166** (render the state you created — binding on 10c), **D122** (already-built remote control), **D162**
(the forecast gate the deferred triage would subsume).
→ `07`, `11`. Files: `docs/design/11-roadmap.md`, `docs/design/07-open-questions.md`.

## D176 — Phase 10 BUILT: three shipped claims retracted or made true, the portability claim measured rather than assumed, and "where is this project" answered by a generated view **[BUILT 2026-08-05 — three increments, `1d52783`→`5b0d09b`+; 853 tests (835→853), 5 meta-gates green, release boundary clean. CLOSES Phase 10 and `07`'s commitment question. ONE RESIDUAL STATED, NOT HIDDEN: native-Windows execution under Git-Bash is unverified]**
D175 opened Phase 10 on the thesis that **the tree asserts things nothing produces or checks**. Building it
found the thesis was, if anything, understated: the commitment question re-asked as a two-owner problem turned
out to have **no owners at all**, which is a *fourth* instance of the same defect in one phase.

- **(1) 10a — the observed layer, retracted in both shipped files.** `codemap.py` rested its standing
  precision-over-recall rule on a durable observed layer accreting the missed recall; `verify/SKILL.md` licensed
  `verify` to **drive the affected flow** as a pure observer to feed it. Neither can be honoured — no producer,
  no schema, no consumer. The precision rule is restated on its own terms (**the two error directions are not
  symmetric**: a fabricated edge is sticky and unretractable, a missed one is merely absent and returns when the
  arm improves), which is where it was always load-bearing. Removing `verify`'s licence also resolved a **latent
  contradiction** the retraction exposed rather than created: the licence let a skill whose first rule is
  *artifact-only* take a runtime action.
- **(2) 10a — `verify` reads the real diff.** The changelog is written by the step that made the change, so
  alone it cannot catch an omission; `verify` now gathers a third view and is genuinely `adjudicate`-shaped —
  **asked** (plan) vs **claimed** (changelog) vs **actual** (diff) — with under-report / over-report / off-plan
  each a hard fail, because each names a file and is therefore demonstrable rather than suspected. **Two git
  reads are required and both were verified by measurement, not reasoning:** `git diff HEAD` is **blind to a
  newly created file** (untracked until staged — and a new file is the likeliest thing for a changelog to
  under-report), and it is **fatal on a repo with no commits**. A check running only the first command would
  have passed for the wrong reason.
- **(3) 10a — `commitment` on nodes was a field a DECISION HAD ALREADY REFUSED, and the sweep is what found it.**
  D175 re-asked this as a D80 two-owner question. The build first found it was a **phantom field** — `graph.json`
  is structural and has no commitment to supply, the seeder emits `path`/`type`/`lang`/`tier`/both signals and
  never one, and **nothing anywhere reads a commitment off a node**. Then the blast-radius sweep found the sharper
  fact: **D106 settled this in Phase 2**, in terms that name this exact thing — *"the spec is the sole owner …
  **nodes never store a commitment value**"*, with node frontmatter listed under its **Rejected** line as "a
  second copy — D80 violation; regen-clobber; N-way fan-out of one fact". So `shared/schemas.md` shipped a field
  its own decision had refused, and cited that schema as *evidence* for the opposite call. Deleted, and the
  deletion is now justified by D106 rather than merely by the field's uselessness.
  **The record carried the same contradiction: `11` recorded D106's closure ("E1 … spec-inline, never node
  frontmatter") AND listed "Commitment-status storage — spec vs node frontmatter" as `[stageable]`/open.** Same
  fact, two states, in the doc that owns it — **structurally identical to the observed-layer two-tier conflict
  D175 settled**, and the third such conflict found in this phase. This is why the sweep is not optional: the
  build alone would have deleted the field for a true but weaker reason and left both stale entries standing.
- **(4) 10b — the portability claim MEASURED, and the fail-closed design survived a state it never anticipated.**
  On the stock Windows PATH, `python3` is the **Microsoft Store stub** — a 2-byte execution alias, empty stdout,
  advert on stderr, **exit 49** — which is neither "python3 present" nor the "python3 absent" the hooks were
  written against. It holds anyway, for two independent reasons: empty stdout trips `guard.sh`'s raw-payload
  fallback, and the non-zero status trips verify-before-commit in both hooks. **The first measurement said exit
  0**, which would have been a *silent bypass of verify-before-commit*; that reading came from `%errorlevel%`
  expanding at cmd.exe **parse** time, before python ran. Re-measured from bash: 49. Also measured: `bash` on the
  stock PATH is the **WSL launcher** (`uname -s` = Linux), so "bash on Windows" silently means a different
  filesystem view.
- **(5) 10b — the one real defect: `loop.sh` misdiagnosed a MISSING `flock` as lock CONTENTION.** Git for Windows
  ships no `flock`, so it exits 127 and `if ! flock -n 9` inverted that straight into the "an orchestrator
  already holds the lock" branch — sending the operator to hunt a session that does not exist, on a machine where
  the launcher can never work. `flock` is now probed separately. **The safety posture is deliberately unchanged**
  — still refuses to start, because two orchestrators clobbering one `.workflow/` is the hazard the file exists
  to prevent; only the diagnosis changed. **The first test harness was falsely green** (its stub PATH still
  resolved `/usr/bin/flock`, so it proved nothing), so the suite carries a guard asserting the harness can
  actually hide `flock`, and was mutation-tested against the pre-fix script to confirm it fails.
- **(6) 10b — D58's trust-UX residual closed.** `shared/trust-model.md`: broad-local vs ask-on-outward and why
  broad-allow is deliberate (an enumerated safelist is defeated by `cd x && cmd` chaining, so it invites trust it
  has not earned), precedence, workspace trust and why `/start` records it, the hook floor that survives bypass,
  and honest limits. The **README carried no permissions content at all**, which for a package asking for broad
  local allow is a transparency gap; it now points at the doc.
- **(7) 10c — the project-state view, as a GENERATED read.** A `status` **skill** over `scripts/project_state.py`.
  **Chosen over a console screen** because D99 scoped the console as a supervision cockpit *and not a project
  explorer*, and `bus.py` knows nothing of `docs/`, `spec.md` or `graph.json` — teaching it would push explorer
  concerns into the cockpit. Split deliberately: the **script settles only what a machine can settle exactly**
  (counts, frontmatter, path resolution, centrality ranking) and the **skill narrates**, which is what makes the
  narration checkable — every number has a file behind it. It **writes nothing**: a stored status doc is stale at
  the next commit and is then believed, which is worse than none. Two properties are load-bearing and tested:
  **`missing` and `zero` render differently** (a brownfield repo before `ingest` legitimately has no spec, and
  reporting "0 features" there is a lie dressed as data), and the **`docs_root` split is honoured**, without
  which `status` would read the OWNER's spec in org mode — the one boundary org mode exists to hold.

*Rejected:* building the observed layer to make its two claims true (making a false claim true is the expensive
way to stop it being false; the layer is `[stageable]` on its own merits); leaving `verify`'s observer licence
dormant "in case" (a dormant licence with no consumer is the same defect, deferred); keeping `commitment` on
nodes as a derived projection (there is nothing to derive it *from*); a console screen for 10c (D99's boundary,
plus `bus.py` would have to learn the docs tree); a `status` skill that WRITES a status file (D38 — the rot this
capability exists to replace); changing `loop.sh` to proceed without a lock when `flock` is missing (trades the
duplicate-orchestrator hazard for convenience); installing Git for Windows to close 10b (a system change on the
maintainer's machine, not mine to make).
*Verified, not assumed:* `git diff HEAD` misses untracked files and is fatal with no HEAD (both driven);
Store-stub `python3` exits **49** with empty stdout (re-measured after a cmd.exe parse-time artefact gave a
wrong 0); stock-PATH `bash` reports `uname -s` = Linux; the pre-fix `loop.sh` really does print "already holds"
when `flock` is absent (mutation-tested); the `status` render was exercised against a populated fixture **and**
against its degraded paths (no spec / no map / no git / no state / malformed JSON) before being called done.
**Fourteen defects across seven phases have now been found by rendering or driving the state we CREATED rather
than by reading code** — this phase adds the falsely-green flock harness and the falsely-green exit code.
**Residual, deliberately not papered over:** 10b is **not closed for native Windows**. Git for Windows is not
installed here, so execution under its bash — the interpreter that actually runs a git hook on a Windows dev box
— is unverified. Worse than unverified in one place: `loop.sh` now *correctly* refuses under Git-Bash, which
means **the launcher cannot start a loop there at all**, and a good error message may not be the right answer.
Logged in `07` with what would close it.
**Supersedes / corrects:** **D78/D83** (the observed layer's two shipped claims retracted; the layer and the
charter revisit stay parked); **D58** (its trust-UX residual is closed); **D89** (its native-Windows gap is
*narrowed by measurement*, not closed). **Builds on:** **D175** (the scope this executes), **D80** (one owner —
`commitment`), **D99** (the cockpit/explorer boundary that chose 10c's form), **D38** (generated, never stored),
**D166** (render the state you created), **D174** (`docs_root`, which 10c must honour).
→ `07`, `10`, `11`. Files: `product/scripts/{codemap/codemap.py,loop.sh,project_state.py}`,
`product/skills/{verify,status}/SKILL.md`, `product/shared/{schemas.md,trust-model.md}`,
`product/templates/loop.md`, `product/commands/start.md`, `product/MANIFEST.json`, `README.md`, + tests.

## D177 — the context governor's shipped default drops 75 → 30, because the default IS the setting everywhere **[DECIDED + BUILT 2026-08-06 — maintainer-set from the first long interactive drive of a real project (`agentic cyber`). Supersedes D136's `75`, which stands as the record of what was built then]**
D136 shipped the interactive context governor with `config.context.warn_pct` defaulting to **75** — a percentage,
never a token count, so it is model-window-agnostic. Driving a real project through a long design phase, the
maintainer's call is that 75 arrives **too late to be a governor**: the banner fires with a quarter of the window
left, by which point three quarters has been spent on context a handoff would have carried for free. The reset is
cheap (a `/dispatch` write plus a `SessionStart` rehydrate) and the thing it prevents is not.

- **The call:** `WARN_PCT_DEFAULT` **30**. The knob is unchanged — a project that wants a different threshold
  still writes `config.context.warn_pct`, and an explicit value still wins.
- **Why the DEFAULT and not a per-project edit:** measured on this machine, **every** other workflow-driven
  project has `warn_pct` **absent** (`dogfood-orchestrator`, `dogfood-start`, `idea testing`, `p5-test`,
  `drive-3b`, `drive-9a`, `drive-demo`) and therefore runs on the shipped constant. Only `agentic cyber` carried
  an explicit stamp. So the default is not a fallback here — it **is** the live setting in 7 of 8 projects, and
  editing one `config.json` would have reached exactly one of them.
- **Rejected — 65**, first proposed as a compromise that keeps a runway to finish the current item before
  clearing. The maintainer's counter is the one that decides it: the governor exists to stop unbounded
  accumulation, and a threshold chosen to avoid interrupting an item is a threshold chosen by the thing being
  governed. **Rejected — leave 75 and document the knob**: a default nobody changes is the behaviour, and this
  one was found late by the only person driving it.
- **The blast-radius sweep earned its keep on a case grep could not reach.** Searching `75` finds the constant,
  the `schemas-runtime.md` owner line and D136's history. It does **not** find
  `test_banner_absent_below_threshold`, which asserted "no banner" at **`pct=40`** — true under 75, false under
  30. The test encoded the old default in a value that never mentions it, and would have failed on the next run
  with no obvious cause. Retargeted to `pct=20`; the boundary test moved 74/75 → 29/30. 11 statusline tests green.
- **D136's `default 75` is NOT edited.** It records what was built on 2026-07-26 and remains true of that build;
  this entry supersedes the value, git holds the change. Same law the project applies to every other status fact.

*Evidence:* the live `agentic cyber` drive (a human at 33% context with no banner, asking where it should have
fired); the 8-project `warn_pct` census above; the statusline reads `config.json` per render, so the change lands
with no restart and reaches existing projects on their next `/update`.
**Supersedes:** **D136** (the `75` value only — its percentage-not-token-count reasoning is untouched and is why
this change is a single constant).
**Builds on:** **D136** (the governor), **D80** (one owner — `schemas-runtime.md` states the default, nothing else
restates it).
→ Files: `product/scripts/statusline.py`, `product/scripts/test_statusline.py`,
`product/shared/schemas-runtime.md`.

---

## D178 — The shipped skills never reach the workers: every loop node dispatches to `general-purpose` carrying a hand-written paraphrase **[DECIDED — fix scoped as `### Phase 11`; unblocks D84's deferral and overrules its `document` call; MEASURED across 51 subagent transcripts of a real drive, not reasoned]**
Origin: a design conversation on whether the loop's **one-execute-agent-and-wait** shape is right *practice* (not
right per this repo's definition). External evidence says it is: Cognition's 2026 revision keeps **single writer**
(writes stay single-threaded; extra agents contribute intelligence, not actions), Anthropic's multi-agent post
states coding is less parallelizable than research, and the one benchmark of aggressive parallel coding agents in
our own harness family scored **16.3% pass vs 20.1% for plain sequential** — fastest, and worse than serial. So the
question closed *yes*. But sizing the writer required measuring a real drive, and the measurement found something
larger than the question asked.

**The finding.** Across the maintainer's `agentic-cyber` drive: **50 `Agent` dispatches — 33 to `general-purpose`,
17 to `dev-autonomous-workflow:research` — and of 51 subagent transcripts, ZERO invoked the `Skill` tool.**
`Execute`/`Document`/`Verify`/`Plan` each went to `general-purpose` carrying a **2.8k–8.8k-character prompt the
orchestrator composed itself**. `execute/SKILL.md`, `verify/SKILL.md`, `document/SKILL.md`, `planner/SKILL.md` never
entered a worker's context. **`research` is the only node working as designed — because it is the only one of them
that is a declared agent**, and it resolved namespaced 17/17 (D128's rule holds).

**The sharper version:** the main window invoked skills 10 times (`planner`×2, `execute`, `verify`, `document`,
`commit`, `prioritize`, `dispatch`, `discuss`×2). So on some items the orchestrator **read the skill into its own
context and then re-typed a lossy summary into the dispatch prompt** — paying the full context cost D84 exists to
avoid *and* still handing the worker a paraphrase. A telephone game with a token bill.

**What the paraphrase drops is the load-bearing detail**, which is the whole reason this is not cosmetic:
`verify`'s **two required git reads** (`git diff HEAD` is blind to a new untracked file — "checking only the first
command yields a check that passes for the wrong reason", D176), its exact `pass: true` first line (machine-read by
`guard.sh`/`pre-commit.sh`), and `execute`'s **backup guard** on a destructive `risk_class`. Two further violations
are visible in the same data: **one subagent spawned its own `Agent`** (leaves must not spawn — D84 — but
`general-purpose` carries the tool), and subagents ran **134 `WebSearch` + 61 `WebFetch`** (legitimate for
`research`; an executor that can browse is an executor that can improvise).

**Cause, and it is one line we shipped:** `templates/orchestrator-CLAUDE.md:17` — *"Never do inline what a skill or
agent should do. When in doubt, dispatch."* With no agent type declared for those nodes, the only way to obey it is
`general-purpose` plus improvisation. D84 classified the nodes and never turned the classification into a
**dispatch** rule, so the brief and the roster disagreed and the model resolved it the only way it could.

**Calls (the fix, to be built as `### Phase 11`):**
1. **Declare the leaf agents.** `execute` · `document` · `create-demo` move `skills/` → `agents/` in `research.md`'s
   format, `Route` stripped (an agent returns a result; the hub follows the edge). **`tools:` is the point** — no
   `Task`/`Agent` (leaves don't spawn) and no `WebSearch`/`WebFetch` on `execute`. This converts two prose
   invariants into harness-enforced ones.
2. **`document` becomes an agent — overruling D84**, which left it a skill as "borderline weight". Measured at
   **40.0k tokens / 13s per dispatch**. It is not borderline. The call is amended on evidence, not re-argued.
3. **State the dispatch rule in the brief.** Replace `:17` with D84's two axes as a *dispatch* rule: leaf+heavy →
   `Agent(dev-autonomous-workflow:<name>)`; fan-out controller / human-interactive / thin bookkeeping →
   `Skill(dev-autonomous-workflow:<name>)` **inline**; never dispatch a loop node to `general-purpose`.
4. **A mechanical gate for the class** — a `PreToolUse` matcher on `Agent` that **blocks** `general-purpose` when
   the dispatch targets a loop node. Without it (3) is advisory prose, and advisory prose is precisely what failed
   here. Blocking, not warn-only: D117's lesson is that *a rule that lives only in this repo's decision log is not
   a rule the consumer follows*. It ships in the package, so an in-flight project is untouched until `/update`.
5. **Make the measurement repeatable** — the transcript query lands in `scripts/` (meta-only, never ships):
   dispatches by `subagent_type`, skill-load rate inside subagents, per-node token distribution. **This defect was
   invisible to reading and obvious to measurement**; it should stay measurable.
6. **Drive it** (D127/D128 practice): one full item on a real project showing namespaced dispatch, roles arriving,
   and **zero** `general-purpose` loop dispatches. **Only then** re-measure the writer's scope — a scoped `execute`
   with no web tools may burn materially less, and the plan-size question must be answered against the fixed
   system, not the broken one.

**`verify` stays an inline skill** (D84: fan-out need beats heaviness — a leaf cannot spawn). The tension that
creates — an inline `verify` reads the diff in the orchestrator's own window, and against a 191k–300k `execute`
that diff is large — is **logged as open in `07` rather than declared settled**. D84's answer ("authoring-thinness:
push heavy reads into spawned workers") is the intended one; it has not been measured.

**Interim exposure, stated rather than implied:** the **deterministic layer is untouched** — `guard.sh`,
`pre-commit.sh`, `check_promise_coverage.py`, `check_decision_coverage.py` and `checks.sh` are hooks and scripts,
not skills, and the `pass: true` contract **fails closed** (a garbled token blocks a commit rather than passing a
bad one). What is degraded is judgment inside the workers. Two exceptions carry real risk until Phase 11 lands:
a **destructive `risk_class`** (the backup guard exists only in the skill text that is not arriving — nothing
mechanical enforces it) and **`verify`'s new-file blindness** (the one silent-wrong-pass in the set).

*Rejected:* **parallel execution agents / within-item fan-out** — the shape the conversation opened with. Rejected
on external measurement (above) plus **4–220× token consumption** for multi-agent vs single-agent, which on a
product that runs on the *user's own subscription* is a product defect, not a trade-off. **Re-open trigger, stated
so this is a decision and not a nailed door:** the arXiv cohesion-aware result (+11.3%/+14.0% pass, −45/−52%
latency, −28/−35% cost) came from partitioning on a **dependency graph** — which is our D91 predicate. If within-item
parallelism is ever reconsidered, the entry condition is that predicate applied to plan *steps*, restricted to
independent leaf files, never naive splitting. Also rejected: **warn-only** for call 4 (the failure mode being
guarded is "advisory rule ignored"); **fixing the writer's scope first** (it would have measured a paraphrase).

*Evidence:* `~/.claude/projects/-mnt-c-…-agentic-cyber` transcripts, 2026-08-07 — 50 `Agent` dispatches
(33 `general-purpose` / 17 `dev-autonomous-workflow:research`); 51 subagent transcripts, **0** `Skill` invocations;
10 main-window `Skill` loads; dispatch prompts 2.8k–8.8k chars; 1 nested `Agent` inside a subagent; 134 `WebSearch`
+ 61 `WebFetch` inside subagents; `Execute S2a-evidence-store` 11m16s / 191.3k tokens (maintainer reports ~300k
routinely), `Document S2a-evidence-store` 13s / 40.0k. External: Cognition *Don't Build Multi-Agents* (2025) +
*Multi-Agents: What's Actually Working* (2026-04-22); Anthropic's multi-agent research system; arXiv 2606.00953
*When Parallelism Pays Off*. **Unblocks D84** (whose deferral rested on "the context saving can't be measured until
the loop runs" — it ran, and the number is 191.3k per dispatch) and **widens its blast radius** from a file move to
a dispatch-mechanism defect. Reuses **D128** (namespaced resolution), **D117** (deterministic > logged prose),
**D91** (the collision predicate), **D127/D128** (drive-to-verify). → `11` (`### Phase 11` opened), `10` (D84
annotation amended), `07` (the inline-`verify` tension), `01` (the dispatch rule).

## D179 — Phase 11 BUILT + DRIVEN: the roles now reach the workers, and the gate that keeps them there **[DECIDED — 11a–11e BUILT and DRIVEN 2026-08-07; the exit test is green on a real model. 11f NOT started. Two defects were found *by the drive*, both in this slice's own changes]**
D178 measured the defect and scoped the fix; this is the fix, built and driven. Nothing here re-argues D178 —
single-writer stands, `document` is an agent, `verify` stays inline — what is new is what the build cost, what
the drive found, and the numbers the exit test produced.

**What shipped.**
1. **`execute` · `document` · `create-demo` are `agents/`** in `research.md`'s format, `Route` stripped (the hub
   follows the edge). **The `tools:` line is the substance:** `Read, Write, Edit, Grep, Glob, Bash` and nothing
   else — no `Task`/`Agent`, so "leaves don't spawn" is now enforced by the harness rather than promised in
   prose, and no `WebSearch`/`WebFetch`, so an executor cannot improvise from the web.
2. **The dispatch rule replaced the brief's `:17`.** Two axes stated as a *mechanism* rule — leaf+heavy →
   dispatch `dev-autonomous-workflow:<name>`; everything else → run the skill inline by name; never a loop node
   to `general-purpose`; **pass inputs, not instructions**.
3. **`hooks/dispatch_guard.py`** — a blocking `PreToolUse(Agent|Task)` gate. It **reads the node names from the
   project's own `.workflow/loop.md`** and keeps no roster of its own (a second list is the drift D80 exists to
   stop). Two independent signals, either sufficient: the dispatch *title* leads with a node name, or the prompt
   reaches into the loop's runtime (`.workflow/items/…`, a plan/changelog/verdict). Deliberate failure modes: no
   `loop.md` → allow (there is no loop to protect); `loop.md` present but yielding no nodes → **block** and say
   why (an empty node set would pass every dispatch vacuously); a namespaced dispatch → always allowed, even
   with a broken graph, so the gate can never stall the loop's own work. **Stated cost, not discovered later:**
   signal 2 also blocks a general-purpose dispatch that merely mentions those paths. That is the trade — the
   block prints the correct call, and re-dispatching by name is one turn.
4. **`scripts/measure-dispatch.py`** (meta-only): dispatches by `subagent_type`, role-arrival rate, per-node
   cost, and the two invariant violations. It **refuses to report a single per-dispatch token figure** — the
   number the CLI shows is not in the transcript, so it reports the parts instead (`new` / `fed in` / `written`
   / `peak context`). An empty scan prints "nothing measured", never a clean bill.
5. **Collateral the move required:** the contract linter now scans `agents/` as well as `skills/` — moving
   `document` out of `skills/` had silently taken `document:audit` out of the unrouted-mode-ref check, a gate
   going quiet with no message; the sandbox gate moved out of `create-demo` (a dispatched agent's file is the
   *worker's* context, and the router never reads it, so a gate living there could not be evaluated); MANIFEST
   gained the hook, `/start` and the trust model name it, and the roster table reads the on-disk truth.

**The two defects the drive found, both ours.**
- **The fix blew the shipped doc budget.** The new dispatch rule and the relocated sandbox gate pushed *both*
  always-loaded templates over the 4000-token HARD budget (`loop.md` 3896→4251, the brief 3506→4064), so every
  new install would have started with `checks.sh --check` red. Found only because the drive ran the real gate on
  a real install. Fixed by the budget's own prescribed remedy — the gate's conditions now live once in
  `create-demo`'s file with a one-line pointer from `loop.md` (read on demand; that file is not read every
  turn), and the brief's new section was compressed to the operative sentences. Both now pass (3984 / 3926).
  **`loop.md` has ~16 tokens of headroom left: it cannot take another addition without a matching subtraction.**
- **`dev-reinstall.sh` was silently shipping stale bytes.** With the cache keyed on the commit SHA (D164), a
  *second* reinstall at the same HEAD reused the already-extracted directory, so the drive kept exercising the
  first run's package while the working tree had moved on. This is **D151's staleness failure returning through
  D164's key**, and it attacks the one mechanism the exit test depends on. Fixed: the SHA's cache dir is dropped
  before install, every time — a dirty tree has no SHA of its own, which is this script's whole premise.

**The exit test (11e), on a real model.** A real project (the packaged `slugify` library from the Phase-5
fixture), migrated onto the new package **through the product's own `/update` runner** — which is also the proof
of D178's claim that an in-flight project is untouched until `/update`. One full item driven end to end
(`planner:plan-one → execute → verify → document → commit`), plus a maintenance `document:audit` pass:
- **4/4 dispatches namespaced, 0 loop nodes on a general worker** (was 33 of 50). The inline half behaved too —
  `planner`, `verify`, `commit`, `discuss`, `decision-engineer` ran as skills in the orchestrator's own window.
- **The paraphrase disappeared, measurably: dispatch prompts fell from 2794–9663 chars to 289–1188.** That is
  the telephone game ending — the prompt now carries inputs, and the role arrives as the worker's own file.
- **0 nested spawns** (was 1) and **0 web calls in a worker whose job is not to gather** — both now structural,
  from `tools:`, not from a rule anyone has to remember.
- **The gate was verified firing in a live session**, not just in tests: a deliberate `general-purpose` dispatch
  at `execute` came back `BLOCKED … Run it by name instead`, and the model did not work around it.
- **Replayed against history:** all 51 dispatches of the original `agentic-cyber` drive were fed to the shipped
  hook — **34/34 non-namespaced blocked, 17/17 namespaced allowed, zero false negatives** on real data.

**What the measurement now says about 11f (recorded, not acted on).** Every node is **read-dominated**:
`execute` at 335.6k fed in against 24.1k written, `document` 175.0k vs 15.7k, `research` 151.7k vs 13.7k, with
peak contexts of 60.5k / 52.5k / 47.0k. Of D178's two rival diagnoses this is the *first* one — the writer is
being fed, not writing too much — which points at `planner` under-supplying context (D134's resolution) rather
than at a plan-size budget. **One item is not a sample**; 11f takes this properly.

*Rejected:* **warn-only** for the gate (re-affirmed under the false-positive cost, which is real: the failure
being guarded is "the advisory was ignored", and an advisory version fails at exactly the moment it matters);
a **hardcoded node list** in the hook (a second roster, drifting the day a node is added); **matching on the
whole prompt body** rather than title-position + runtime-path (every node name is also a common English word —
`document`, `execute`, `verify` — and body matching would block ordinary work); **hand-seeding the drive
fixture** instead of migrating it with `update_reconcile.py` (it would have tested a fixture, not the product's
own upgrade path); and **splitting `execute`'s plan** in response to its cost (the number says read-dominated,
so splitting would make it worse — this is exactly the reasoning-ahead-of-measurement 11f exists to prevent).

*Evidence:* the drive at `~/drive-11e` — item `ROADMAP-3` committed `03d6c0f`, its prerequisite-repair riding
its own commit `5f52739` (the two-commit carve-out working unprompted); `scripts/measure-dispatch.py
~/drive-11e --since 2026-08-07` → 4/4 declared, 0 general-purpose, 0 violations; the historical replay against
`~/.claude/projects/-mnt-c-…-agentic-cyber`; the live block message quoted verbatim above. 885 tests pass
(824→885, +61: 15 for the gate, 11 for the measurement, 6 for the linter's agent half, the rest existing), all
five meta-gates green. **Discharges D178's calls 1–6** and leaves **11f** — the writer's scope — open with its
first real numbers attached. → `11` (Phase 11 status), `10` (roster + the D84 amendment), `07` (the open
tensions, now measurable), `01` (the dispatch rule as shipped).

## D180 — Phase 11f MEASURED: the writer is right-sized, the ROUTER is the constrained window — and the instrument that said otherwise was wrong **[DECIDED — 11f MEASURED 2026-08-08 on four items driven end to end; Phase 11 CLOSED. Neither of D178's two fixes is adopted, and the reason is data, not preference. Three shipped defects were found by driving and fixed]**
11f existed to take one attribution against the fixed system — discovery-read cost vs production-write cost,
re-read ratio, off-`files_touched` reads — and then choose between two opposite fixes. The attribution was taken.
It chose neither, and the first thing it found was that **the measurement itself was wrong**.

**The instrument was over-counting, twice.** Both defects inflate exactly the number D178/D179 reasoned from.
1. **One API response is written as SEVERAL transcript records** — one per content block — each repeating the whole
   response's `usage`. Summing over records multiplies `cache_creation` by the block count. `execute` on the 11e
   drive was never 335.6k fed in: it is **119.1k**. `document` 175.0k → **45.6k**; `research` 151.7k → **48.6k**.
   `written` was barely affected (partial records carry partial counts, only the last carries the total — which is
   why the aggregation is MAX within a response, not first-wins). Grouped on `message.id`, falling back to
   `requestId` then the record `uuid`, so an unknown shape degrades to the old over-count rather than silently
   dropping turns.
2. **`cache_creation` double-counts a stall.** That same `execute` had one **659-second gap**, and the next call
   wrote **55,518 tokens** — its whole prefix again, past the prompt cache's 5-minute TTL. That single stall is
   **47% of its "fed in"**. The other three drives never stalled and their `fed in` ≈ their peak context. So
   `cache_creation` is a *billing* proxy, not a "how much material was this worker given" proxy; the material
   measures are peak context and the tool-level split. The instrument now names stalls under the cost table.

So the number that opened this phase describes a worker whose context actually peaked at **60.5k**, ~13k of it
material it read.

**The attribution, four items, 3→11 declared files, all driven to commit on the fixed package.**

| item (plan files) | fed in | peak | boot | written | produced | discovery | disc:prod | reads | off-plan | re-read |
|---|---|---|---|---|---|---|---|---|---|---|
| ROADMAP-4 `__version__` (3) | 39.8k | 39.7k | 9.5k | 11.5k | 2.8k | 7.7k | 2.8x | 7 | 1 | 0% |
| ROADMAP-5 CLI (4) | 49.4k | 51.5k | 7.2k | 15.7k | 4.9k | 9.2k | 1.9x | 7 | 1 | 0% |
| ROADMAP-3 `max_length` | 119.1k† | 60.5k | 10.0k | 24.0k | 5.5k | 10.4k | 1.9x | 8 | — | 12% |
| ROADMAP-6 package split (11) | 57.6k | 59.9k | 7.0k | 29.0k | 7.0k | 9.5k | 1.4x | 7 | 0 | 0% |

† 55.5k of it is the stall re-write. **`off-plan` counts PRODUCT reads only** — the loop's own `plan.md` /
`promises.json` / `checks.env` are excluded, and that exclusion is load-bearing: scored in, they made `execute`
read 43–57% off-plan, which looks exactly like a writer hunting for context nobody gave it. Every one of those
reads was a file the worker is *told* to read and which a plan never lists in its own `Files touched` table.

***Rejected — read-dominated ⇒ `planner` under-supplies context (D134's resolution).*** Discovery is **flat**:
7.7k–10.4k, seven or eight reads, across a 3.7x spread in item scope. Re-reads are **0% in three of four**.
Off-plan product hunting is **one read** in each of the two items that had any (both a test file the plan forgot
to name) and **zero** on the largest item. The writer is not casting about, so there is nothing for a
better-supplied plan to fix — and the supply would be paid for in the wrong window (below).

***Rejected — write-dominated ⇒ a plan-size budget splitting on the D91 predicate, serially.*** Production **is**
the half that scales (2.8k → 7.0k produced; 11.5k → 29.0k written), but **sub-linearly** — 3.7x the scope buys
2.5x the output — and it lands nowhere near a ceiling: the largest writer peaked at **59.9k**. Against that,
splitting pays **7–10k of `boot` per extra dispatch** (the fixed cost of a worker existing, measured on every
dispatch here) plus extra turns in the window that *is* near its ceiling. The D178 re-open trigger for within-item
parallelism is untouched and still stands; this rejects *serial* splitting too, on cost.

**What the data says instead — the constraint is the ROUTER, not the writer.** One item consumes **98k–179k of
the orchestrator's own window**, and the router is **43–53% of every drive's fed-in tokens**. Put on one axis for
the first time: an **inline** node costs the router 9–29k, a **dispatched** one costs it 0.3–2.6k. That is the
dispatch rule's claim, measured — and the exception is honest: `research` costs the router +22.5k, because its
findings are read there by design. The most expensive inline node is **`planner` itself** (+26.6k, +16.0k,
+49.2k, +38.1k across the four drives), consistently **above `verify`** (+10.6k, +20.6k, +20.6k). So the first
diagnosis' remedy would have loaded the constrained window to relieve the unconstrained one.

**This does not become a fix in this slice, deliberately.** `planner` and `verify` are inline *because they fan
out*, and a leaf cannot spawn (D84) — so "move them out" is not an edit, it is D27's two-level-agent topology
reopened. What changes is that `07`'s inline-`verify` tension is no longer unmeasured, and it is no longer only
about `verify`. **Phase 11 closes here**; the successor candidates are that tension and the cold-context reviewer,
which `11e` unblocked.

**Three shipped defects, found by driving, fixed and re-proven (not one of them reachable by reading).**
- **`/update` renamed the project it was updating.** `render_brief` filled `<project>` from the checkout
  directory's basename while `/start` had filled it with the project's real name. Every update on such a project
  reported the brief as a `LOCAL-EDIT` — "local edit would be LOST", demanding `--confirm-overwrite` — over a
  difference the package invented itself, and an apply would have renamed the project. A false alarm on the exact
  flag that protects real local edits is worse than no alarm: it teaches the operator to pass it. `config.project`
  is now the source (basename the fallback), with `schemas-runtime.md` as its owner and `/start` told to write it.
- **`checks.sh --fix` handed the loop's own manifests to the stack formatter.** The `commit` skill scopes `--fix`
  to the item's *staged* files, which include `.workflow/items/<id>/promises.json`; `ruff format` force-parses an
  explicitly-named file as Python whatever its extension and wrote a **magic trailing comma** into it — invalid
  JSON, and that manifest is what `check_promise_coverage.py`/`check_criterion_discharge.py` parse. Reproduced
  independently on a real manifest rather than taken on the drive's word: both gates then exit 2 with "cannot
  parse manifest", so the fail-closed contract **held** and the damage is a self-inflicted commit stall, not a
  silent gate defeat. Fixed in the shipped runner (a formatter has no business in `.workflow/`/`.claude/` for any
  stack, so the filter is stack-agnostic and mechanical rather than a rule `commit` must remember — D117);
  withheld paths are named on stderr.
- **The instrument's own two over-counts**, above.

*Rejected:* **acting on the D179 numbers** (they were 2.8–3.5x high — the whole reason 11f re-measures rather than
reasons); **folding test/gate output into "discovery"** (it is feedback on work done, not context for work not
done, and folding it in blames the planner for a test suite's verbosity); **scoring `.workflow/` reads against the
plan** (see above); **counting only `Read` as a read** (a worker can `cat` its way through a repo, so read-shaped
Bash counts as discovery); **fixing `checks.sh` in the `commit` skill's prose** instead of the runner; and
**building the router fix here** — the measurement says where the constraint is, it does not say the topology
question is answered.

*Evidence:* three fresh fixtures forked from the migrated 11e drive — `~/drive-11f-s` (`ROADMAP-4`, committed
`1c19688`), `~/drive-11f-m` (`ROADMAP-5`, `e01e55b`), `~/drive-11f-l` (`ROADMAP-6`, `fab043d`) — each seeded with
one item and driven headless to its commit, plus the re-measured 11e drive. Fidelity held throughout: **8/8
dispatches namespaced, 0 loop nodes on a general worker, 0 nested spawns**, all three trees clean and green
(799 / 877 / 1012 tests in the fixtures). Two of the three drives were cut mid-item by an account session limit
and resumed in a second session, so their router *totals* sum two windows; the comparable figure is the
per-session peak (106.3k / 98.4k). **Scope caveat, stated rather than implied:** one small fixture project (a
79-line library) — what generalizes is the *shape* (flat discovery, own-output dominance, a fixed ~8k boot, the
router's share), not the absolutes; on the large `agentic-cyber` tree the same node peaked at 220.3k. `901` tests
pass (`899`→`901`, +16 across the slice), all five meta-gates green. **Closes Phase 11.** → `11` (11f + phase
status), `07` (both tensions re-stated against real numbers), `10` (the D84 annotation).

---

## D181 — the marketplace binding is a single mutable pointer to an absolute path, and a throwaway worktree can silently take it **[DECIDED + BUILT 2026-08-08 — from a real failure on this machine, where the plugin disappeared from every project at once. Two mechanisms: one meta-only guard at the cause, one shipped detector at the symptom. Extends the hop-A design with the third state it never had]**
On 2026-08-06 `scripts/dev-reinstall.sh` was run from inside the build worktree
`.claude/worktrees/phase9-capture`. It resolves its own directory and hands that to `claude plugin marketplace
add` — so the marketplace was bound to the worktree's absolute path. The worktree was then merged and deleted,
and **the plugin vanished from `/plugin`, from skills, agents and commands, on every project on the machine.**

Two facts make that a silent single-point failure rather than an obvious mistake:

- **The marketplace name is identical in every checkout of this repo** (it comes from `.claude-plugin/marketplace.json`).
  So adding from a worktree does not create a *second* marketplace beside the real one — it **rebinds the only
  one**, with no prompt and no warning. The script's own comment blessed exactly this ("`add` is what picks up a
  moved/renamed checkout"), which is right for a moved checkout and wrong for a disposable one.
- **A `source: directory` marketplace stores an absolute path with no liveness contract.** Nothing re-checks it,
  nothing warns when it dies. The installed bytes survive — the install is a *copy* under the CLI cache, which is
  why nothing appeared to break at install time — but every route to a newer copy is severed.

- **Call 1 — `dev-reinstall.sh` refuses to install from a linked worktree** (`--git-common-dir` ≠ `--git-dir`),
  naming the main working tree to use instead. `--allow-worktree` keeps the deliberate case open with the
  consequence printed. It also now prints **what the marketplace is actually bound to** at the tail, beside the
  roster line, on the same principle: a wrong binding should be visible, not inferred.
- **Call 2 — hop A gains a third state: registered-but-GONE.** `_marketplace_anchor` returned `(None, None)` both
  when there was no anchor to read *and* when the anchor's whole location had disappeared, and the caller reads a
  `None` anchor as "nothing to compare" and stays quiet. So the one condition that is **unrecoverable without
  human action** was the one condition the detector was silent about, and an install whose source is gone reads as
  current forever. It now returns `(None, location)` for that case and says so, naming the dead path, warn-once
  keyed on it so re-pointing silences it by itself.
- **Rejected — silently redirecting the install to the main tree** when run from a worktree. Installing main's
  bytes when the caller asked for this worktree's is a *different* lie, of exactly the kind this script exists to
  defeat (D151). Refusing states the problem; redirecting hides it.
- **Rejected — shipping a "your marketplace is a worktree" detector in the product.** The root cause is a
  maintainer script, not user behaviour, and the dangling-path warning already covers the released user who moves
  or deletes a checkout. Ship the symptom detector, keep the cause guard meta-only.
- **A corollary worth stating, because it raised a false alarm.** The install pins a **commit SHA**, and the SHA it
  pinned (`15af534`) was **orphaned by a rebase 18 minutes later** — the worktree branched at `9e4dcb6`, `main`
  moved two commits, so the ff-only merge was impossible and the commit was rebased to `f8d4f7f` before landing.
  `merge-base --is-ancestor` therefore says "not an ancestor" and reads as a regression risk. It is not one: the
  rebased commit is a strict **superset** (194 vs 186 lines into the register, 10 vs 8 into `07`), and every line
  that later disappeared is a supersession, not a loss. **The right test after a rebase is content-containment,
  not ancestry** — and the second-order lesson is that a reinstall must follow any rebase, because the pin can
  outlive the commit.

*Evidence — reproduced, not reasoned:* the failure was reproduced **twice live** while fixing it. The second time
was accidental and is the better evidence: running the *worktree's own* copy of `dev-reinstall.sh` (still at
`15af534`, before the guard) silently rebound all three registries — `known_marketplaces.json`, `settings.json`'s
`extraKnownMarketplaces`, and the install's `gitCommitSha` — back to the worktree, from a command that looked like
an ordinary reinstall. **The failure needs no unusual conditions; it needs one `cd`.** The guard was then proven on
a throwaway repo with a real linked worktree: refuses from the worktree naming the main tree, proceeds from the
main tree, proceeds under `--allow-worktree`. Three tests cover hop A's new state (fires and names the dead path ·
warn-once holds · a location that exists but yields no SHA stays as silent as before). `904` tests pass
(`901`→`904`), all five meta-gates green. The orphaned worktree is removed and the binding is repaired to the
repo root — which the new tail line now states rather than leaving to be assumed.
**Builds on:** **D164/D165** (the two-hop detector and its warn-once marker — this adds a state to hop A, it does
not change the design), **D151** (the staleness class, and the "no-op that reports success" failure mode this
inherits its refusal principle from), **D125** (the repo as its own marketplace, which is *why* the name collides
across checkouts).
→ Files: `product/hooks/session_start.py`, `product/scripts/test_session_start.py`, `scripts/dev-reinstall.sh`.

## D182 — a maintenance item had no legal commit: the gate could not tell "verify-free by design" from "verify was skipped", so the pass now says which, in the commit itself **[DECIDED + BUILT 2026-08-09 — from a real drive, where landing the first `align` scan needed a hand-written verdict to get past the gate. Two defects, one root cause. The escape is a committed receipt, deliberately not a `state.json` field]**

`loop.md` § Maintenance items gives `document:audit` / `align` / `doc-budget` a **straight-to-commit** path — no
`planner`/`execute`/`verify`, because there is no product-code change to plan and no runtime behaviour to verify.
`verify_check.py` was never told. Under `status: building` it demands an identifiable item and a `pass: true`
verdict for it, with `phase: bootstrap` the only escape — so a maintenance commit **blocked both ways**: with
`current_item` set, *"no verify-verdict.md"*; with it null, *"no item is identifiable … fails closed"*. There was
no value of `current_item` that let the commit through.

**Same root, second defect:** `staged_item_ids()` derived items from `git diff --cached --name-only`, which lists
**deletions**. `document:audit`'s retention prune deletes closed `.workflow/items/<id>/` dirs — so the prune
re-derived every dir it had just deleted as an item under commit, went looking for the verdict inside it, and
blocked on the file the same commit was deleting. Both defects are the gate reading a **non-build change as an
unverified build item**.

**The call.** A maintenance pass **stages a receipt in its own commit** — `.workflow/maintenance/<item-id>.json`
`{ item, kind, summary }`, `kind` ∈ the three maintenance nodes — and the gate accepts that in place of a verdict.
It is validated (parses · `item` equals the filename stem · known `kind`) and must be **staged in the commit under
review**; a rejected receipt blocks with the reason named. Deletions are dropped from the staged derivation
(`--diff-filter=d`). The pass deletes any earlier receipt as it writes its own, so the directory holds exactly one
file and the history of past maintenance is that directory's git log.

- **Rejected — a `state.json` marker (`phase: maintenance`), the obvious mirror of the bootstrap escape.** The
  bootstrap escape is safe *because it fires once and then disappears forever*; maintenance **recurs for the life of
  the project**. A volatile marker for a recurring motion re-arms on every threshold hit and, left stale by a
  crashed pass or a resumed session, disarms verify-before-commit for the next **product-code** commit — the same
  fail-open shape as the two drift vectors D129 exists to defeat. A marker carried in the commit cannot go stale,
  and a human reviewing the diff can see it. (The proposal also assumed a `phase: normal-ops`; `phase` is
  bootstrap-only and absent once the loop drives.)
- **Rejected — a trivial `pass: true` verdict from the maintenance skills** (the workaround used to land the scan).
  `project_state.py` derives an item's `verified` from that first line, so a courtesy verdict makes the console
  report an item as **verified that never ran verify**. The anchors are evidence; an anchor that lies is worse than
  an absent one. This is also why the receipt is a distinct artifact rather than a verdict variant.
- **Rejected — the receipt under `.workflow/items/<id>/maintenance.md`** (the first sketch). That directory's
  filenames are declared FIXED *because they are anchors*, and it entangles a verify-free item with `promoted.json`
  prune semantics it can never satisfy — leaving maintenance dirs as permanent sediment, or inviting a second lying
  marker to clear them. A separate namespace also makes the rule honest: a maintenance item is not an item with an
  exemption, it is a different kind of thing under commit. Nothing exempts a **staged item dir** — `planner` mkdirs
  that dir, so something was built under it, and a built item is verified rather than exempted.
- **Rejected — making the receipt a forecast anchor.** An anchor firing for a node no chain named is read as a
  **structural divergence**, and maintenance items are *injected* by `prioritize`, never forecast — so every routine
  maintenance pass would re-forecast the tail.
- **Rejected — a retention rule for the new tier.** Self-collection (each pass deletes the previous receipt) bounds
  the directory at one file by construction, with no new `config.retention` key and no `retention.py` change. An
  append-only tier with no collector would have been sediment by this project's own memory law.
- **The `kind` set is registered as a real enum invariant** (`maintenance.kind`, the fifth), because
  `verify_check.py`'s `MAINT_KINDS` is its **decider** and not a restatement — the `checkpoint.kind`/`PARK_KINDS`
  shape exactly (D-gate). A node the schema declares and the tuple omits is an item whose receipt is rejected, so it
  can **never commit**, while `loop.md` goes on routing it straight to `commit`; the drift is invisible from the
  schema side. `declared_values()` had to admit `:` to parse a node **mode** (`document:audit`) — without it the
  gate silently drops that member and reports a mismatch the code does not have.

*Evidence — reproduced against the shipped gate, not reasoned:* restoring the pre-fix `verify_check.py` fails
**6 of the 9 new tests**, including both reported repros (the `align` commit, and the prune commit blocking on the
verdict it deletes). The other 3 pass on **both** versions and are the tightness tests that must never regress — a
maintenance item **without** a receipt still blocks, an **unstaged** receipt exempts nothing, and a receipt does not
excuse a staged item dir carrying a failing verdict. The defect was found by driving, not by reading: the first
`align` scan on a real run could only be landed by hand-writing a verdict. `916` tests pass (`904`→`916`; 9 gate
tests + 3 enum-drift tests), all five meta-gates green.

**Builds on:** **D129** (the fail-closed verify-before-commit gate and its two drift vectors), **D139** (the
bootstrap carve-out — this is the second escape, and it is deliberately shaped *unlike* it), **D133** (bootstrap
state-publishing), and `loop.md` § Maintenance items, which promised the straight-to-commit path this makes legal.
→ Files: `product/hooks/verify_check.py`, `product/scripts/test_verify_check.py`, `product/templates/loop.md`,
`product/shared/schemas.md`, `product/skills/align/SKILL.md`, `product/agents/document.md`,
`product/skills/prioritize/SKILL.md`, `product/commands/start.md`, `scripts/check_enum_coherence.py`,
`scripts/test_check_enum_coherence.py`.
