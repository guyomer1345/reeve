# reeve

**The disciplined builder**, an autonomous *but disciplined* dev workflow for Claude Code.

This harness is built to wrap around your existing project, or to create a new one, and act as a hardening
layer for **context management, project state, project knowledge, and the development loop**. It runs on top
of Claude Code. It does not replace it, and it never sits in Claude's request path. Everything is local, on
your own subscription, with nothing to sign up for.

It does that with four things, and a set of agents and skills at its call:

- **A fixed routing graph** decides what happens next: prioritize, plan, execute, verify, document, commit.
  The next step is never improvised, and a failure routes to `debug` then `refine` instead of to a guess.
- **Durable state on disk** (`.workflow/`) means nothing load-bearing lives only in the context window. The
  spec, the backlog, the plan, the changelog and every parked checkpoint survive a `/clear`, a closed
  terminal, and a new machine.
- **A project knowledge base** that the loop keeps fresh itself: a typed code map of how your files actually
  connect, plus a per-file history of what was learned working on them. Decisions get made against how your
  codebase really is, not against a summary of it.
- **Mechanical gates** hold the work to the spec rather than hoping it does: pre-commit checks, a
  plan-coverage and acceptance-criteria discharge check, a secret scan, a protected-branch push floor, and a
  periodic drift scan that files whatever has diverged as ordinary tickets.

---

## Recommended usage

The harness attaches itself to your existing project, or helps you initialise a new one.

**When creating a new project**, I extremely recommend that the purpose and scope, the design, the tech
stack, the architecture, the third-party integrations, and the core aspects of it are discussed and enforced
**by the operator**, and only after that, allow a continuous autonomous development cycle. Be as clear about
what the project is *not* as about what it is; scope is the thing an autonomous loop inflates first. The
harness is deliberately unwilling to guess here. Where you genuinely have no preference, `decision-engineer`
will research the options and market practice and come back with a confidence-scored recommendation rather
than quietly picking one.

**When using the harness on an existing project**, allow it to ingest and get to know the project. Then have
a discussion with it after the ingestion has finished, to make sure the goals, the purpose, the tech stack,
the constraints and the core aspects of the product are maintained **as you set them**, not as they were
reconstructed from the code. Pay attention to one thing in particular: tell it what in there is *deliberate*
and what is legacy accident. Reading an implementation cannot separate the two, and a bug that gets
reconstructed as a requirement will be defended by every gate downstream.

**In terms of the development cycle**, discuss and plan the foreseeable roadmap, or the feature you want to
implement, and use tools like **demo** and **forecast** (see below) to allow for precise and clean results.

**After closing in on the goals**, run **`/dispatch`**, clear the context, and tell Claude to simply continue.
That is what keeps the development cycle smooth. You will notice that on reaching around **300k of context**
there will be a warning recommending you dispatch and clear again before continuing. Do it. That is what
allows your usage to persist, and ensures optimal results from Claude.

---

## Install

Requirements: [Claude Code](https://code.claude.com) (v2.1+), plus `python3`, `git`, and `bash` on your PATH.
The shipped helpers are stdlib-Python and bash, with zero third-party dependencies.

Install it as a marketplace plugin:

```bash
claude plugin marketplace add guyomer1345/reeve
claude plugin install reeve
```

Then open the project you want it to drive and run `/start`.

Installing **copies** the package. It is a snapshot, not a live link. The package ships no `version` field,
so Claude Code keys the install on the **git commit SHA**; when the repo moves, `claude plugin update` picks
it up. After upgrading the plugin, run **`/update`** inside each project so its installed half is refreshed
to match.

### Permissions, worth two minutes before the first run

An autonomous loop that prompts on every file write is not autonomous, so `/start` installs settings that
**allow local work broadly** (edit, read, run tests) while **always asking before anything leaves the
machine** (`git push`, `gh`, deploys, `ssh`, `curl`). That is a real ask, and
**[`shared/trust-model.md`](product/shared/trust-model.md)** states exactly what is granted, what stays
gated, and what is enforced even if you disable the gates.

Three things worth knowing up front:

- **You do not need `--dangerously-skip-permissions`.** It would auto-approve the outward actions, which is
  the one gate that actually matters.
- **`/start` records workspace trust** for the project root. Without it, Claude Code treats the shipped
  allowlist as inert and prompts for everything anyway.
- **`/start` is interactive-only.** It writes into `.claude/`, which Claude Code guards above the settings
  allowlist, so a `claude -p` session has no way to accept those prompts. Run it in a normal session.

---

## Terminology

| term | what it means here |
|---|---|
| **greenfield** | An empty directory, where the thing does not exist yet. `/start` routes you into `discuss` and you design it before anything is built. Your code lands under `project/`. |
| **brownfield** | A repository that already has code. `/start` routes you into `ingest`, and your layout is left exactly as it is. |
| **ingest** | The brownfield bootstrap. Builds the code map and reconstructs a spec from your existing `CLAUDE.md` and docs (never guessed from the code alone), then stops at a blocking checkpoint for you to confirm it. |
| **spec** | The written, testable statement of what the project is for. Everything downstream is held against it. |
| **backlog / item** | The queue of work, and one unit of it. An item is planned, executed, verified, documented and committed as a single pass. |
| **checkpoint** | A durable pause for a human verdict. Not a blocked process: the loop records where it stopped and resumes when your answer lands, even after the terminal closes. |
| **demo** | A throwaway, low-fidelity sandbox of a user-facing change, shown to you *before* it is really built, so you approve the look and behaviour first. |
| **forecast** | The chain of events the loop proposes to walk for a change, shown *before* it walks it, so you can correct the route and answer its human gates up front. |
| **dispatch** | Writing a complete `handoff.md` so a `/clear` is safe. The context-reset ritual: `/dispatch`, then `/clear`, then tell it to continue. |
| **code map** | A typed graph of how your files actually connect, kept fresh by the loop and used for blast-radius before a change. |
| **align** | The periodic drift scan. Reconciles spec, decisions and promises against the code that actually exists, and files whatever diverged as tickets. |

---

## Commands

`/start`, `/update`, `/dispatch` and `/rebind` are the four you type as slash commands. The rest are
capabilities you can call by name when you want them; the loop also reaches for them on its own.

### The four you type

| command | when | what it does |
|---|---|---|
| **`/start`** | once, per project | Bootstraps the project. Detects greenfield vs brownfield and confirms it with you, scaffolds `.workflow/`, installs the scripts and git hooks into `.claude/`, starts the console daemon, and hands off to `discuss` or `ingest`. Safe to re-run: it resumes a half-finished init rather than clobbering a live one. |
| **`/update`** | after upgrading the plugin | Migrates an already-initialised project onto the currently-installed version. Refreshes the package-owned files, regenerates the code map, and **never touches what the project owns**. |
| **`/dispatch`** | when the statusline warns | Writes a complete, current `handoff.md` so a `/clear` is safe. Run it, then `/clear`, then say "continue". The next session rehydrates from the handoff on its own. |
| **`/rebind`** | after a machine move | Re-binds the machine-local runtime half to *this* machine. The symptom is a tool refusing to start because the runtime root does not exist, because you moved the repo or rebuilt the machine. It repairs the pointer, recovers what survived, and itemizes what did not. |

### The ones worth calling by name

| capability | what it does |
|---|---|
| **`discuss`** | The requirements conversation. **The first step of any new intake**, whether a new project or a new feature on an existing one, and it produces the spec. This is where you do the design work, and it is the single most valuable place to spend your attention. |
| **`create-forecast`** | Lays out the chain of events it proposes to walk, before it walks it. Use it on anything big. |
| **`create-demo`** | Builds the throwaway sandbox of a user-facing change for you to approve before it is really built. |
| **`status`** | Where is this project: what is done, how the pieces connect, what is left, what is blocked on you. Synthesized fresh every time, never a stored document. Good for coming back after time away. |
| **`create-issue`** | File a bug or a "do this later" without addressing it now. Opens a real GitHub issue, which `planner` later picks up and `close-issue` closes. |
| **`align`** | Run the drift scan on demand, rather than waiting for its commit threshold. Worth doing after a merge or at a phase boundary. |
| **`answer`** | Ask a question about the project and get it answered from its own knowledge base, spec and decision record. |

---

## Skills and agents

The package ships **17 skills** and **5 agents**, and the split between them is deliberate rather than
cosmetic.

A **skill** runs *inline*, in the session you are already in. It sees your conversation and can talk back to
you, which is what a decision, a fan-out or a piece of bookkeeping needs. A skill cannot spawn other workers.

An **agent** runs in its **own context window**, as a subagent. It gets sent inputs, does one heavy job, and
returns a result. Nothing it reads pollutes the orchestrator's context, which is exactly the point: the
orchestrator stays thin because the expensive work happens somewhere else. An agent is a leaf, so it never
fans out further.

The rule is: **heavy leaf work goes to an agent, everything else stays a skill.**

### The five agents

| agent | what it does |
|---|---|
| **`execute`** | The loop's writer. Runs an approved plan file step by step and records exactly what was done. It makes **zero decisions of its own**: an undecided option, missing information, or a plan assumption that turns out to be untrue stops it and comes back as a blocker rather than a judgement call. This is the discipline the whole design rests on. |
| **`document`** | Folds completed changes, and the decisions behind them, into the project knowledge base: the knowledge nodes, the typed edges, the per-file history log and the architecture doc. It reads the changelog and the decision stream, not just the diff. Also runs the retention and prune audit when the loop schedules one. |
| **`create-demo`** | Builds the throwaway, low-fidelity sandbox of a user-facing change so you can approve the look and behaviour before it is really built. On a change request it edits the spec first, then regenerates from it, so the sandbox and the spec never drift apart. |
| **`research`** | Gathers external or internal information on demand: tech-stack options, whether something is a known bug, third-party API and setup details, market practice. Dispatched by `decision-engineer` and `debug`, and callable directly whenever something lacks information it needs. |
| **`setup-guide`** | Produces precise, current, click-by-click instructions for a manual external task the system cannot do itself, like configuring auth or setting up webhooks. It researches the service's real UI directly and emits exact steps, each with a verified deep-link and a breadcrumb path, for a setup checkpoint. |

### The skills

Beyond the ones listed above under *worth calling by name*, the loop's internal vocabulary is: `planner`,
`prioritize`, `verify`, `debug`, `refine`, `commit`, `close-issue`, `decision-engineer`, `checkpoint`,
`ingest` and `adjudicate` (the shared "gather competing views, then judge" procedure that `verify`, `debug`
and `decision-engineer` all specialize). You can name any of them, but normally you just talk to the
orchestrator and it routes.

---

## Tuning

The harness reads its knobs from **`.workflow/config.json`**. **Every one of them ships with a working
default, and leaving the file alone is a completely reasonable choice.** Nothing below is required to run.
But a few are worth a minute of your own judgement, because the right value depends on how *your* project
moves, and a default is a compromise across all of them.

**The two most worth setting yourself:**

| key | default | what it controls |
|---|---|---|
| `align.every_n_commits` | `20` | How many commits pass before the drift scan runs. **Lower it** (8 to 10) on a fast-moving project, or one where the spec is load-bearing and you want drift caught early. **Raise it** on a slow, stable codebase where the scan is mostly cost. |
| `doc_budget.every_p_items` | `15` | How many completed items pass before the documentation-size check runs, the pass that catches docs growing past what fits in context and trims or splits them. **Lower it** if your project generates a lot of documentation and you would rather pay small frequent trims than one big one. |

These two are deliberately **decoupled** from each other and from retention: doc size is not drift risk, and
neither one is memory pressure. They get separate thresholds on purpose.

**The rest, for when you want them:**

| key | default | what it controls |
|---|---|---|
| `context.warn_pct` | `30` | The percentage of the context window past which the statusline starts recommending `/dispatch` then `/clear`. A percentage rather than a token count, so it is model-window-agnostic. On a 1M-context model that is the ~300k warning. |
| `align.max_agents` | `6` | Hard cap on the drift scan's fan-out, so it can never halt production. Whatever it defers rides the next scan. |
| `doc_budget.ondemand_hard` | `25000` | Not a preference. It is the Read tool's own token ceiling, past which a file cannot be loaded in one call at all. Exceeding it **fails** the checks. |
| `doc_budget.chars_per_token` | `3.2` | The estimator's divisor. There is no tokenizer in the stdlib, so counts are estimated and err high on purpose. Lower it for docs dense in fenced code. |
| `retention.sessions_k` | `10` | How many per-file session entries the knowledge base keeps before the audit pass prunes. |
| `retention.every_p_items` | `15` | How often the retention and audit pass is scheduled. |
| `checkpoint.deadline_hours` | `24` | How long a parked checkpoint may sit before the daemon escalates. **A deadline never auto-proceeds**, it only raises the alarm. |
| `checkpoint.reminder_hours` | `4` | How often the daemon re-alerts while a checkpoint is open and not yet overdue. |
| `demo.max_refine_rounds` | `3` | How many times a demo sandbox may be regenerated before the loop stops auto-proceeding and escalates to a live `discuss`. |
| `thread.rotate_at_tokens` | `200000` | When the question and answer thread rotates into a fresh session. This one bounds *spend*, not disk, because a resumed thread re-sends its whole history on every message. |
| `notify.webhook` / `notify.desktop` | unset / off | The away channel. **The webhook is the real one**: it reaches a phone and works from a detached daemon, while a desktop toast is best-effort and needs a notification daemon present. Worth setting if you intend to run the loop while away. |

Absent keys fall back to the shipped defaults, so you only write the ones you want to change.

---

## How the flow actually works

### The spine

The orchestrator is a **thin router**. It reads a fixed routing graph (`.workflow/loop.md`) plus the live
position (`.workflow/state.json`), dispatches the next step to a skill or an agent, and advances, keeping its
own context deliberately thin by pushing the real work down into agents.

```
                    greenfield                    brownfield
                        │                             │
                    discuss                        ingest
                  (spec written)            (code map + reconstructed spec)
                        │                             │
                 forecast? demo?              checkpoint:reconcile ◄── you confirm
                        │                             │
                 planner:decompose  ─────────────────►│
                        │                             │
                        └──────────► prioritize ◄─────┘
                                          │
                                   planner:plan-one ──► decision-engineer ──► research
                                          │
                                       execute
                                          │
                                        verify ──fail──► debug ──► refine ──┐
                                          │ pass                            │
                                    checkpoint:qa ◄── you test the live app │
                                          │ pass                            │
                                       document                             │
                                          │                                 │
                                        commit ──► close-issue ──► prioritize ◄┘
```

Read as prose: **`prioritize`** picks the next independent work items off the backlog. **`planner`** turns
one into a step-by-step plan file, and if it hits a real open decision it refuses to guess and calls
**`decision-engineer`**, which can call **`research`** for outside evidence. **`execute`** runs the plan and
records exactly what it did, making no decisions of its own.

**`verify`** then checks the plan against the changelog against the tree's real diff, and against the spec
intent and the plan's acceptance criteria. On failure it goes to **`debug`**, which diagnoses with a
confidence score and loops for more information when unsure, and then to **`refine`**, which never edits code
itself. It routes the correction back through plan and execute, so the zero-decision discipline holds even on
the repair path.

Once it passes, **`document`** folds the change and the decisions behind it into the knowledge base,
**`commit`** snapshots it as a Conventional Commit linked to its work item, and **`close-issue`** closes the
GitHub issue it resolved. Then back to `prioritize`.

**Side doors** are callable from anywhere: `create-issue`, `research`, `answer` and `status`.

### Checkpoints, where you come in

Checkpoints are **durable parks, not blocked processes**. The loop records where it stopped, yields, and
resumes later, even after the terminal closes, once your verdict lands. Five kinds:

- **`reconcile`**: confirm the spec `ingest` reconstructed from your existing code. *(brownfield bootstrap)*
- **`forecast`**: approve the chain of events the loop proposes to walk, before it walks it.
- **`demo`**: approve a sandbox of a user-facing change. Verdicts are **approve** (lock the spec, prune the
  sandbox), **changes** (regenerate it), or **reject** (back to `discuss`).
- **`qa`**: test the built feature in the live app and pass or fail it. The manual human-test gate.
- **`setup`**: perform a manual external action the machine cannot do itself, like configuring auth or
  setting up webhooks. It hands you verified deep-links and click-by-click steps researched against the
  service's actual current UI, and takes any credential straight into the gitignored secret store.

You answer from the console, from your phone, or just in the session.
