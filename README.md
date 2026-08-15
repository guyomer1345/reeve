# reeve

**The disciplined builder** — an autonomous *but disciplined* dev workflow for Claude Code.

> A *reeve* was the officer who ran the manor day to day while the lord was away, and rendered a full account
> of it when he returned. That is the deal here: it works on its own, and it answers for what it did.

It is a pure Claude-Code-native package — skills, subagents, hooks, slash commands, and a `CLAUDE.md`
driver — that you install into your **own** Claude Code and run locally on your **own** subscription. It
drives a project the way a professional engineer does: a self-directing loop (prioritize → plan → build →
verify → document → commit) that runs on its own and pauses only for human checkpoints and steering, backed
by a live supervision console and a project knowledge base.

**Master rule:** it never sits in Claude's request path. Everything runs locally on your machine; the
components talk over a local bus and files, never by routing Claude on your behalf. There is no server, no
hosted router, and nothing to sign up for.

## What you get

- **A self-driving engineer loop** — not vibe-coding. It plans work, writes it, verifies it, and documents it,
  committing as it goes, and asks for you only when a real decision or a manual QA gate needs a human.
- **A manual human-test gate** — the loop parks at defined points, shows you what to check, and resumes on
  your verdict — which you can deliver from the console, including from your phone over a transport you declare.
- **A live supervision console** — a local web page (a detached, zero-build daemon) that shows where the
  project is, lets you send a verdict or a new task, and alerts you when the loop needs you or hard-stops.
- **A project knowledge base** — a typed code-map graph plus per-file experiential memory, kept fresh by the
  loop itself, so the engine's decisions are grounded in how *your* codebase actually connects.

---

## Install

Requirements: [Claude Code](https://code.claude.com) (v2.1+), plus `python3`, `git`, and `bash` on your PATH
(the shipped helpers are stdlib-Python and bash, zero third-party dependencies).

```bash
# add this repo as a plugin marketplace, then install the plugin
claude plugin marketplace add guyomer1345/reeve
claude plugin install reeve
```

To hack on the package locally instead, clone it and add the working copy as the marketplace:

```bash
git clone https://github.com/guyomer1345/reeve
claude plugin marketplace add ./reeve
claude plugin install reeve
```

Installing **copies** the package — it is a snapshot, not a live link to the checkout. The package ships **no
`version` field**, so Claude Code keys the install on the **git commit SHA**; content that moves gets a new key,
and `claude plugin update` is no longer a no-op over changed content. What it still cannot see is an **uncommitted**
edit in your working tree, since the SHA has not moved yet. So while you are editing the package, re-install rather
than update: `scripts/dev-reinstall.sh` does it from the working tree and prints what the install now carries.

### Permissions — worth two minutes before the first run

An autonomous loop that prompts on every file write is not autonomous, so `/start` installs settings that
**allow local work broadly** (edit, read, run tests) while **always asking before anything leaves the machine**
(`git push`, `gh`, deploys, `ssh`, `curl`). That is a real ask, and **[`shared/trust-model.md`](product/shared/trust-model.md)**
states exactly what is granted, what stays gated, and what is enforced even if you disable the gates.

Two things worth knowing up front: **you do not need `--dangerously-skip-permissions`** (it would auto-approve
the outward actions, which is the one gate that matters), and `/start` records **workspace trust** for the
project root — without it Claude Code treats the shipped allowlist as inert and prompts for everything.

`/start` is **interactive-only** — it writes into `.claude/`, which Claude Code guards above the settings
allowlist. Run it in a normal interactive session, not `claude -p`.

---

## Getting started: greenfield or brownfield

Open the directory you want the workflow to drive in Claude Code and run:

```
/start
```

`/start` detects which mode you are in — **greenfield** (empty directory) or **brownfield** (existing code) —
**confirms the detection with you**, then scaffolds `.workflow/`, installs the shipped scripts and git hooks
into `.claude/`, prints a **console URL**, and hands off to the right entry point. The two modes are genuinely
different experiences, and picking the right one matters more than any other choice you make here.

### Greenfield — you are building something new

Use this when the directory is empty (or holds nothing but a package manifest) and the thing does not exist yet.

`/start` routes into a **`discuss` conversation**, and this is the part to take seriously. Greenfield mode
assumes **you, the operator, drive the design completely** — the purpose, the product surface, the
architecture, and the tech stack are all discussed, decided, and *reviewed by you* before a line is written.
The loop is deliberately unwilling to guess here. Expect to work through:

- **what the thing is for** — the actual goal, the user, the shape of the product;
- **the screens / surfaces** and the core features, in enough detail to be testable;
- **the tech stack and architecture** — and where you genuinely have no preference, `decision-engineer`
  researches the options and market practice and comes back with a confidence-scored recommendation rather
  than quietly picking one;
- **the integrations** you will need (auth, billing, storage), which become **setup checkpoints** later.

That conversation produces a written, testable **spec**. Only then does `planner` decompose it into a phased
roadmap and the loop starts building. This front-loading is the whole point: the disciplined half of
"autonomous but disciplined" is that the machine is executing *your* design, not inventing one and asking
forgiveness at review time.

Greenfield puts your code under a **`project/` subdirectory** (`config.project_root` = `./project`), keeping
the workflow's own state and docs cleanly beside it rather than tangled into your source tree.

**Greenfield is the right call when:** it is a new product or a new service; you care about the architecture;
you want the spec to exist as a durable artifact the loop is later held against.

### Brownfield — you are working on code that already exists

Use this when there is a real codebase already — yours, or one you have inherited.

`/start` routes into **`ingest`**, which does two things before anything is allowed to change:

1. **Builds the knowledge base** — a structural **code map** of the real repository (a typed graph of how the
   files actually connect), plus the per-file history log the loop keeps updating from then on.
2. **Reconstructs a spec** — what this codebase appears to be *for*. Crucially it seeds the core intended
   behaviour from your existing `CLAUDE.md` and docs, **never guessed from the code alone**, because guessing
   intent from an implementation is how you end up encoding a bug as a requirement.

Then it stops. `ingest` hands its reconstruction to a **blocking `reconcile` checkpoint**: you read back what
it believes the project is and either confirm it, correct it, or send it to re-ingest. Nothing autonomous runs
until you have signed off on that understanding. Budget real attention for this gate — every decision the loop
makes downstream is made against the spec you approve here.

Brownfield leaves your repository layout exactly as it is (`config.project_root` = `.`).

**Brownfield is the right call when:** adding features to a live codebase; paying down a backlog of bugs;
refactoring; onboarding yourself to something unfamiliar (the ingest pass alone is worth it); or handing an
existing project a disciplined loop it never had.

**Brownfield is *not* a shortcut around design.** For a substantial new feature inside an existing codebase,
you still go through `discuss` — brownfield only changes how the project is *bootstrapped*, not whether new
work gets specified.

### Which am I?

| | greenfield | brownfield |
|---|---|---|
| Starting point | empty directory | existing repository |
| Entry point | `discuss` — the design conversation | `ingest` — code map + reconstructed spec |
| First human gate | you drive the whole design | `reconcile` — confirm what it understood |
| Your code lives in | `project/` | the repo root, untouched |
| Spec comes from | you, up front | reconstruction + your confirmation |

---

## The commands

Four slash commands are all you type. Everything else is the loop's own vocabulary, dispatched internally.

| command | when | what it does |
|---|---|---|
| **`/start`** | once, per project | Bootstraps the project: detects greenfield vs brownfield, scaffolds `.workflow/`, installs scripts + git hooks into `.claude/`, starts the console daemon, and hands off to `discuss` or `ingest`. Safe to re-run — it resumes a half-finished init rather than clobbering a live one. |
| **`/update`** | after upgrading the package | Migrates an already-initialised project onto the currently-installed version: refreshes the package-owned files, regenerates the code map, and **never touches what the project owns**. The sibling of `/start`. |
| **`/dispatch`** | when the statusline warns | Writes a complete, current `handoff.md` so a `/clear` is safe. Run it, then `/clear` — the next session rehydrates from the handoff automatically. This is the context-reset ritual. |
| **`/rebind`** | after a machine move | Re-binds the project's machine-local runtime half to *this* machine. The symptom is a tool refusing to start because the runtime root does not exist — you moved the repo to another machine, or rebuilt the one it was on. It repairs the pointer, recovers whatever survived, and itemizes what did not. |

Beyond those, you mostly just **talk to the orchestrator**: ask it for status, hand it a new feature, tell it
to fix something, answer a checkpoint. It routes.

---

## How the flow actually works

### The spine

The orchestrator is a **thin router**. It reads a fixed routing graph (`.workflow/loop.md`) plus the live
position (`.workflow/state.json`), dispatches the next step to a skill or a subagent, and advances — keeping
its own context deliberately thin by pushing real work down into subagents. The main line:

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

Reading that as prose: **`prioritize`** picks the next independent work items from the backlog.
**`planner`** turns one into a step-by-step plan file — and if it hits a real open decision, it refuses to
guess and calls **`decision-engineer`** (which can call **`research`** for outside evidence).
**`execute`** runs the plan and records exactly what it did; it makes **zero decisions of its own** — an
undecided option or a false plan assumption stops it and comes back as a blocker.
**`verify`** checks the plan against the changelog against the tree's real diff, and against the spec intent
and acceptance criteria. On failure it goes to **`debug`** (diagnose, with a confidence score) and then
**`refine`**, which never edits code itself — it routes the correction back through plan → execute, so the
zero-decision discipline holds even on the repair path.
Once it passes, **`document`** folds the change into the knowledge base, **`commit`** snapshots it as a
Conventional Commit linked to its work item, and **`close-issue`** closes the GitHub issue it resolved.
Then back to `prioritize`.

**Side doors** are callable from anywhere: `create-issue` (file a bug or deferred work without doing it now),
`research`, `answer` (a question about the project, answered from its own knowledge base), and `status`
(where is this project — synthesized fresh, never a stored document).

### Checkpoints — where you come in

Checkpoints are **durable parks, not blocked processes**. The loop records where it stopped, yields, and can
resume later — even after the terminal closes — once your verdict lands. Five kinds:

- **`reconcile`** — confirm the spec `ingest` reconstructed from your existing code. *(brownfield bootstrap)*
- **`forecast`** — approve the chain of events the loop proposes to walk *before* it walks it, so you can
  question and correct the plan and answer its human gates up front. Fires on big changes.
- **`demo`** — approve a throwaway, low-fidelity sandbox of a user-facing change before it is really built.
  Verdicts are **approve** (lock the spec, prune the sandbox), **changes** (regenerate it), or **reject**
  (back to `discuss`).
- **`qa`** — test the built feature in the live app and pass or fail it. This is the manual human-test gate.
- **`setup`** — perform a manual external action the machine cannot do (configure Clerk auth, set up Polar
  webhooks). It hands you verified deep-links and click-by-click steps researched against the service's
  actual current UI, and collects any credential straight into the gitignored secret store.

You answer from the console (including from your phone), or just in the session.

### The console

`/start` prints a URL. Behind it is one local daemon that serves the read-only cockpit **and** accepts your
input — verdicts, new tasks, questions, and releases for outward actions like a push. The loop drains that
inbox between work items, so an approval you give while away actually moves the project forward: a
relaunch-runner can wake a sleeping loop to consume it. The daemon also raises the alarm when a checkpoint
goes unanswered past its deadline, and can reach you off-machine through a webhook you configure.

### Discipline is enforced, not hoped for

Engineering rules with concrete per-stack enforcers; mechanical pre-commit gates (secret scan, a
protected-branch push floor, plan-coverage and criterion-discharge checks); and a periodic **`align`** scan
that reconciles the spec, the decisions, and the promises against the code that actually exists — filing what
drifted as ordinary tickets rather than silently letting the spec become fiction.

---

## Tuning

The workflow reads its knobs from **`.workflow/config.json`**. **Every one of them ships with a working
default, and leaving the file alone is a completely reasonable choice** — nothing below is required to run.
But a few are genuinely worth a minute of your own judgement, because the right value depends on how *your*
project moves, and the default is a compromise across all projects.

**The two most worth setting yourself:**

| key | default | what it controls |
|---|---|---|
| `align.every_n_commits` | `20` | How many commits pass before the drift scan runs — reconciling spec, decisions, and promises against the real code. **Lower it** (say 8–10) on a fast-moving project, or one where the spec is load-bearing and you want drift caught early. **Raise it** on a slow, stable codebase where the scan is mostly cost. |
| `doc_budget.every_p_items` | `15` | How many completed items pass before the documentation-size check runs — the pass that catches docs growing past what fits in context and trims or splits them. **Lower it** if your project generates a lot of documentation and you would rather pay small, frequent trims than one big one. |

Both are deliberately **decoupled** from each other and from retention: doc size is not drift risk, and
neither is memory pressure. They get separate thresholds on purpose.

**The rest, for when you want them:**

| key | default | what it controls |
|---|---|---|
| `align.max_agents` | `6` | Hard cap on the drift scan's fan-out, so it can never halt production. Deferred surface rides the next scan. |
| `doc_budget.ondemand_hard` | `25000` | Not a preference — the Read tool's own token ceiling, past which a file cannot be loaded in one call at all. Exceeding it **fails** the checks. |
| `doc_budget.chars_per_token` | `3.2` | The estimator's divisor (there is no tokenizer in the stdlib, so counts are estimated and err high on purpose). Lower it for docs dense in fenced code. |
| `retention.sessions_k` | `10` | How many per-file session entries the knowledge base keeps before the audit pass prunes. |
| `retention.every_p_items` | `15` | How often the retention/audit pass is scheduled. |
| `context.warn_pct` | `30` | The context-usage percentage past which the statusline nags you to run `/dispatch` then `/clear`. A percentage, not a token count, so it is model-window-agnostic. |
| `checkpoint.deadline_hours` | `24` | How long a parked checkpoint may sit before the daemon escalates. **A deadline never auto-proceeds** — it only raises the alarm. |
| `checkpoint.reminder_hours` | `4` | How often the daemon re-alerts while a checkpoint is open and not yet overdue. |
| `demo.max_refine_rounds` | `3` | How many times a demo sandbox may be regenerated before the loop stops auto-proceeding and escalates to a live `discuss`. |
| `thread.rotate_at_tokens` | `200000` | When the question/answer conversation thread rotates into a fresh session. This one bounds *spend*, not disk — a resumed thread re-sends its whole history per message. |
| `notify.webhook` / `notify.desktop` | unset / off | The away channel. **The webhook is the real one** — it reaches a phone and works from a detached daemon; a desktop toast is best-effort and needs a notification daemon present. Worth setting if you intend to run the loop while away. |

Absent keys fall back to the shipped defaults, so you only ever write the ones you want to change.

---

## How it was built

This repo shows its work. The `product/` directory is the installable plugin — its
[`MANIFEST.json`](product/MANIFEST.json) is the single source of truth for exactly what ships. Everything
outside `product/` is the **construction record**: the full design spec, the reasoning behind every call, and
the maintenance tooling live under [`docs/design/`](docs/design/) — the numbered design documents and an
append-only decision log. It is dense and internal by design; you do not need any of it to *use* the workflow,
but it is all there if you want to see why the thing is shaped the way it is.

**Project status** (what's built, what's left, the phased plan) has exactly one home:
[`docs/design/11-roadmap.md`](docs/design/11-roadmap.md).
