---
description: Bootstrap the disciplined-builder workflow in this project and become the orchestrator. Auto-detects greenfield (empty) vs brownfield (existing code), scaffolds workflow state, and hands off to inception or ingest.
argument-hint: "[greenfield|brownfield]  (optional — auto-detected if omitted)"
---

# /start — bootstrap the workflow (the `init` capability)

Run once to turn the current directory into a workflow-driven project and initialise this session as the
**orchestrator**. Conceptually this is `init`; it is exposed as `/start` because `/init` is a
built-in Claude Code command.

## 0. Detect mode & guard
- If `.workflow/` already exists → the project is already initialised. Do **not** clobber: report current
  state and offer to resume from `.workflow/handoff.md` instead. Stop.
- Else pick the mode: `$ARGUMENTS` if given, otherwise **detect** — existing source files present →
  **brownfield**; empty (or package only) → **greenfield**. **Confirm the detected mode with the user**
  before proceeding (mis-classifying is costly).

## 1. Shared steps (both modes)
1. **repo-setup:** ensure git is initialised (`git init -b main`), a git identity is set, and a
   `.gitignore` exists. If a remote is wanted and `gh` is unauthenticated → raise `checkpoint`(kind=setup)
   → `setup-guide` for `gh auth login`. If already authenticated, create/push directly.
2. **Scaffold the workflow layout** (provisional — EXPAND):
   ```
   .workflow/
     config.json       # project_root + run config      (committed)
     loop.md           # routing graph + diagram        (committed)
     checks.sh         # mechanical-gate runner (generated per-stack; --fix / --check) (committed)
     codemap.sh        # code-map generator (generated per-stack; writes docs/knowledge/graph.json) (committed)
     state.json        # live position — RUNTIME, add to .gitignore
     handoff.md        # durable resume anchor          (committed)
     backlog.md        # live OPEN queue (issues + roadmap; closed leave) (committed)
     outbox/           # RUNTIME — pending outward-action queue (push/issue awaiting a console release); add to .gitignore
   <project_root>/     # the product (greenfield: project/ ; brownfield: repo root)
     llms.txt          # thin agent entry point → docs/knowledge/  (committed)
     rules/            # engineering rules — specialized baseline, subtree-overridable (committed)
     docs/             # docs-root — durable product knowledge
       spec/           # product spec (discuss fills this)   (committed)
       architecture.md # inline Mermaid-C4 (document-owned)  (committed)
       knowledge/      # code map                            (committed)
       decisions/      # decision-records = ADRs (append-only) (committed)
   ```
   `.workflow/items/<id>/` and `.workflow/align/` are **not** scaffolded here — `planner` `mkdir`s each item
   dir on demand, and `align` `mkdir`s `.workflow/align/` on its first run (writing `anchor.json`).
   Add the **runtime** paths to the target's `.gitignore` — `state.json`, `runtime.json`, `bus.json`, `bus.lock`,
   `alerts.json`, `outbox/`, `parked/`, `inbox/`, **`secrets/`**, `remote_token`, `demos/`, and the per-ticket worktrees (created at runtime by the
   bus/orchestrator, not scaffolded here); the durable artifacts (`config.json`, `loop.md`, `checks.sh`,
   `codemap.sh`, `handoff.md`, `backlog.md`, `items/`, and `docs/`) are committed. **`secrets/` holds live
   credentials** a human hands over at a setup checkpoint — it must be gitignored *and* live on a filesystem that
   honours `0600`; it is never swept by the retention pass.
3. **Place the runtime tree on a filesystem that can hold it.** Check the mount under the launch root. The
   atomicity- and mode-sensitive runtime paths (`state.json`, `bus.json`, `bus.lock`, `alerts.json`, `parked/`,
   `inbox/`, `outbox/`, `secrets/`, `remote_token`) need a **local** filesystem: on a network-style or Windows-interop mount, `rename` is not
   reliably atomic and — the one that bites silently — **a file created `0600` can come back world-readable with no
   error at all**, which would leave the console's capability token and any stored credential readable by other
   users on the machine.
   - **Local mount (the common case):** nothing to do. `.workflow/` is the runtime root; write no pointer.
   - **Network-style / interop mount** (e.g. a repo under a mounted Windows drive): create a runtime tree on a local
     filesystem (under the user's home), and write **`.workflow/runtime.json`** = `{"runtime_root": "<abs path>"}`.
     That pointer is how every other process finds the relocated tree, so it stays on the repo mount and is
     **gitignored** (the path is machine-specific — committing it would hand a clone a wrong root). Tell the user
     plainly that `.workflow/` now spans two filesystems, and why.
   - Committed artifacts (`handoff.md`, `backlog.md`, `config.json`, `docs/`) **never** relocate — they live with the
     repo by definition. Only the runtime half moves.
4. **Install the orchestrator brief** (the driver), from the package `templates/`:
   - **greenfield:** copy `templates/orchestrator-CLAUDE.md` → the launch-root **`CLAUDE.md`** (fill
     `<project>`/`<project_root>`) and put the product under **`project/`** (its own `CLAUDE.md` left to the
     product); set `project_root: ./project`.
   - **brownfield:** the product stays at the repo root; wrap `templates/orchestrator-CLAUDE.md` in the
     **sentinel markers** and **append** it to the *existing* root `CLAUDE.md` (never clobber — idempotent via
     the markers); read that existing `CLAUDE.md` as a **primary ingest source**; set `project_root: .`.
   - Copy `templates/loop.md` → **`.workflow/loop.md`** and write **`.workflow/config.json`** (`project_root` +
     run config).
   - Copy `templates/settings.json` → **`.claude/settings.json`** (loop permission rules: `allow` local actions;
     the outbox-covered outward classes — `git push`, `gh issue` — are deliberately **not** `ask`ed, because they
     are approved through the outbox + a console `release` and fired later at a boundary, when a terminal prompt
     would reach nobody; every other outward command — deploy / publish / cloud / network — stays `ask`) and
     `hooks/{guard.sh,pre-commit.sh}` → **`.claude/hooks/`** (guard = secret-scan + verify-before-commit + the
     **push floor** (never move a protected branch, never push a secret) hard gates; pre-commit = the
     mechanical-gate backstop, registered in step 4). `build-once-per-wave` is deferred.
   - Copy the shipped **code-map extractor** (`scripts/codemap/`) → **`.claude/scripts/codemap/`** — the
     per-language tool `.workflow/codemap.sh` invokes to build the knowledge graph (wired in step 4).
   - Copy the shipped **retention script** (`scripts/retention.py`) → **`.claude/scripts/`** — the deterministic
     `audit`-item enforcer `document` (audit mode) invokes to bound the append-only tier. Stack-agnostic (it edits
     only the workflow's own `.workflow/`+`docs/` layout), so it ships fixed — not generated per-stack.
   - Copy the shipped **coverage gates** (`scripts/check_promise_coverage.py` + `scripts/check_criterion_discharge.py`
     + `scripts/check_decision_coverage.py`) → **`.claude/scripts/`** — the deterministic gates `checks.sh --check`
     invokes so a load-bearing promise can't ship with no resolvable / boundary test, no `artifact`
     acceptance-criterion ships without a mechanical `discharge`, and no governing decision ships mapped to no plan
     step. Stack-agnostic (all read the workflow's own `promises.json`), so they ship fixed — not per-stack.
   - Copy the shipped **console daemon** (`scripts/bus.py`) → **`.claude/scripts/`** — the detached local HTTP
     daemon that serves the supervision console and is the channel a human uses to reach the loop while it is busy,
     parked, or dead. A per-project copy (like every other shipped script), which is also what keys it per project:
     its lock, its discovery record, and its port all derive from that project's runtime root, so two projects
     cannot collide. Stack-agnostic (it reads only the workflow's own layout), so it ships fixed — not per-stack.
   - Copy the shipped **drain bookkeeper** (`scripts/drain.py`) → **`.claude/scripts/`** — the deterministic half
     of the boundary inbox drain the orchestrator invokes each turn (`list` → apply → `record`): which messages are
     new, in what order they apply, what the watermark is, and what may be pruned. It sits beside `bus.py` and
     imports its path resolution, so the two must land in the same directory. Stack-agnostic (it reads only the
     workflow's own layout), so it ships fixed — not per-stack.
   - Copy the shipped **contract linter** (`scripts/check_contracts.py`) → **`.claude/scripts/`** — the decidable
     routing-graph check `align`'s mechanical layer invokes over `.workflow/loop.md` + the installed skills (via
     `--loop`/`--skills-dir`/`--schemas`): every routing target resolves, every invoked `node:mode` is routed,
     every skill is a node or side-door. Stack-agnostic (lints the workflow's own wiring), so it ships fixed.
   - **Surface the one-time permission message** to the human: *"This is an autonomous loop. Accept the
     workspace-trust dialog so the package can pre-approve the loop's local actions. Pushes and issue
     create/close are **not** approved by a terminal prompt — they queue to `.workflow/outbox/` and wait for you
     to release them from the console, so the loop keeps working while you are away; deploys and other outward
     commands still ask. Two things are hard blocks, not prompts, and nothing can waive them: the loop never
     moves `main`/`master`, and it never pushes a secret. You don't need `--dangerously-skip-permissions`."*
5. **Specialize rules + wire enforcement** (the disciplined layer — auto-write greenfield, adopt-and-gap-fill
   brownfield):
   - **Seed the rules.** Copy the package baseline `rules/*.md` → **`<project_root>/rules/`**. Detect the
     stack (languages, frameworks, package manager) and rewrite each `— enforced by: <mechanism>` tag with the
     project's *concrete* tool (e.g. `formatter` → `prettier`/`black`/`gofmt`), so the agent reads real commands.
     Nearest-file-wins: this project copy is the floor a subtree `rules/` can override.
   - **Wire the enforcers named by the tags.** For each enforceable principle, install the concrete gate from
     the detected stack: `.editorconfig`, formatter, linter, typechecker (where the language has one), the
     test-runner script, a dependency-audit step, and a **CI workflow** that runs format-check + lint +
     typecheck + test on push/PR. **Greenfield:** write these from the detected stack. **Brownfield:** *adopt*
     what already exists — never clobber a config the project ships; record the existing tool as the enforcer
     in the specialized `rules/`, and only **gap-fill** the missing ones.
   - **Generate `.workflow/checks.sh`** — the one mechanical-gate runner both callers share: a
     `--fix` mode (format + lint-fix + strip a stale reference, for the `commit` skill to run in-loop) and a
     `--check` mode (fail non-zero on residual drift, for the git hook). It wraps the concrete tools just wired,
     **plus the stack-agnostic `check_promise_coverage.py`, `check_criterion_discharge.py`, and
     `check_decision_coverage.py`** over each open item's `.workflow/items/<id>/promises.json` — a load-bearing
     promise with no resolvable / boundary test, an `artifact` criterion with no `discharge`, or a governing
     decision mapped to no step, fails the commit (the mechanical plan-coverage gates; teeth, not advice).
   - **Register the git backstop.** Install the shipped `pre-commit.sh` as git's `.git/hooks/pre-commit` (copy
     or symlink — git requires the exact name `pre-commit`) so a commit made *outside* the loop still hits
     `checks.sh --check`.
   - **Generate `.workflow/codemap.sh`** — the code-map runner: a single call to the shipped engine
     (`.claude/scripts/codemap/codemap.py <project_root>`), which auto-dispatches each file to its language arm
     and writes `docs/knowledge/graph.json` (a typed import graph plus the *impact* and *orchestration* centrality
     signals per file, and a per-language coverage summary tagging each language's arm tier). **Python** (stdlib
     `ast`), **JS/TS** (`tsconfig`/`jsconfig` `paths`+`baseUrl` aliases + extension/index resolution), **Go**,
     **Java**, and **C#** have precise resolver arms; every other recognized source language falls to the **tier-0
     generic floor** (directory-cluster nodes + shallow-regex imports, precision-first resolution, same `graph.json`
     contract) so a repo in any recognized language gets at least nodes + clusters + both lenses — never nothing.
     (Further precise arms are zero-dep resolvers that plug into the same engine as they land — C++ needs a
     compile-DB, so it stays on the floor for now; tree-sitter is reserved for parse-hard languages, shipped as an
     optional upgrade.) Regenerable — the loop re-runs it and never hand-edits the graph.
   - **Externals → checkpoint.** Anything needing an account or a provider choice (CI host, deploy creds) is an
     outward/setup step → raise `checkpoint`(kind=setup) → `setup-guide`, don't guess.
6. **Ensure the console daemon is running.** Run `python3 .claude/scripts/bus.py ensure --workflow-dir .workflow`.
   This is **adopt-or-spawn and idempotent**: it adopts a daemon that is already up and only spawns one if none is,
   because spawning fresh would drop messages already sitting in the inbox. It prints the console URL — surface that
   to the user, and mention they can reach it from a browser on the host machine.
   - The daemon is **detached into its own session**, so it outlives this session, a `/clear`, a `--resume`, and the
     terminal closing. That is the point: a verdict must be deliverable while the loop is busy, parked, or dead.
   - If it reports a **warning about file mode**, relay it rather than swallowing it: it means this filesystem
     ignored the `0600` on the token file, so the console's capability token is readable by other users on the
     machine. The fix is to place the runtime tree on a local filesystem (step 3).
   - On WSL the daemon dies a few seconds after the last terminal closes (a detached process cannot hold the distro
     alive); it comes back on the next `/start`, and nothing already written to the inbox is lost.
7. **Commit** the initialised scaffold.

## 2. Greenfield (new project)  — fully supported
- Scaffold an empty `<project_root>/docs/` (spec, architecture, knowledge, decisions); it grows as the project
  is built.
- Hand off to **`discuss`** (inception) to build the spec from zero → then the normal loop
  (`prioritize → planner → …`).

## 3. Brownfield (integrate existing codebase)  — flow specified; unexercised
- **Rules + enforcement are already adopted** by shared step 5 (adopt existing configs, gap-fill the missing
  enforcers, layer our `rules/` on top). That is the *habits* half of integration. The **docs → knowledge** half
  below is **specified** too (the `ingest` skill body) — so this section is no longer a spec stub. The residual is
  **runtime, not spec**: it is unexercised until a real brownfield bootstrap.
- **Run `ingest`.** The skill runs `.workflow/codemap.sh` to build the structural graph, seeds
  `docs/knowledge/` nodes, and reconstructs `docs/spec/` from the existing `CLAUDE.md`/docs + code (tagged
  `unspecified`). **Adopt an existing `docs/`** if present — write to known subpaths, never clobber; namespace
  ours on a name collision. The durable per-file `why`/Sessions stay empty until `document` authors them on
  first touch.
- **Reconciliation checkpoint** — `ingest` surfaces the reconstructed understanding ("here's what I think the
  app does, its core flows, its stack") via a blocking `checkpoint` for the user to confirm/correct; confirmed
  invariants flip `unspecified → locked` before the loop drives.
- Then hand to the normal loop.

## Expand later
- Additional **code-map language arms** — Python (`ast`), **JS/TS** (tsconfig resolver), **Go**, **Java**, and
  **C#** precise arms plus the **tier-0 generic floor** (all other recognized languages) ship today; the next
  prevalence-ranked precise arms (C++ — needs a compile-DB — then Rust · PHP) are **zero-dep resolver arms** on the
  same engine + `graph.json` contract, each upgrading its language from the floor's best-effort edges to precise
  resolution. tree-sitter is reserved for parse-hard languages (optional upgrade — absent → the floor).
- The console's **write** path — delivering a verdict, filing an intake, releasing a queued outward action. The
  daemon serves the read-only cockpit today; the forms land next.
- The full **disk layout** — the tree above is a provisional first cut.
