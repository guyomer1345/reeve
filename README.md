# dev-autonomous-workflow

**The disciplined builder** — an autonomous *but disciplined* dev workflow for Claude Code.

It is a pure Claude-Code-native package — skills, subagents, hooks, slash commands, and a `CLAUDE.md`
driver — that you install into your **own** Claude Code and run locally on your **own** subscription. It
drives a project the way a professional engineer does: a self-directing loop (prioritize → plan → build →
test → document) that runs on its own and pauses only for human checkpoints and steering, backed by a live
supervision console and a project knowledge base.

**Master rule:** it never sits in Claude's request path. Everything runs locally on your machine; the
components talk over a local bus and files, never by routing Claude on your behalf. There is no server, no
hosted router, and nothing to sign up for.

## What you get

- **A self-driving engineer loop** — not vibe-coding. It plans work, writes it, tests it, and documents it,
  committing as it goes, and asks for you only when a real decision or a manual QA gate needs a human.
- **A manual human-test gate** — the loop parks at defined points, shows you what to check, and resumes on
  your verdict — which you can deliver from the console, including from your phone over a transport you declare.
- **A live supervision console** — a local web page (a detached, zero-build daemon) that shows where the
  project is, lets you send a verdict or a new task, and alerts you when the loop needs you or hard-stops.
- **A project knowledge base** — a typed code-map graph plus per-file experiential memory, kept fresh by the
  loop itself, so the engine's decisions are grounded in how *your* codebase actually connects.

## Install

Requirements: [Claude Code](https://code.claude.com) (v2.1+), plus `python3`, `git`, and `bash` on your PATH
(the shipped helpers are stdlib-Python and bash, zero third-party dependencies).

```bash
# add this repo as a plugin marketplace, then install the plugin
claude plugin marketplace add guyomer1345/dev-autonomous-workflow
claude plugin install dev-autonomous-workflow
```

To hack on the package locally instead, clone it and add the working copy as the marketplace:

```bash
git clone https://github.com/guyomer1345/dev-autonomous-workflow
claude plugin marketplace add ./dev-autonomous-workflow
claude plugin install dev-autonomous-workflow
```

Installing **copies** the package — it is a snapshot, not a live link to the checkout, and `claude plugin update`
compares *versions*, which move once per release rather than once per commit. So while you are editing the package,
re-install rather than update: `scripts/dev-reinstall.sh` does it from the working tree and prints what the install
now carries.

## Getting started

Open the project you want the workflow to build (or an empty directory for a new one) in Claude Code and run:

```
/start
```

`/start` detects whether the project is **greenfield** (empty) or **brownfield** (existing code), scaffolds
the workflow state under `.workflow/`, installs the shipped scripts and git hooks into `.claude/`, and hands
off — to a spec-building conversation for a new project, or to an ingest + reconciliation pass for an existing
one. It prints a **console URL**; open it to watch the run and to reach the loop while it works.

From there the loop runs on its own. You step in at checkpoints (approve / request changes / reject), steer it
with new requests, and authorize outward actions (pushes, issues) from the console when you choose to.

## How it works

- **The orchestrator** is a thin router driven by `CLAUDE.md` and a `.workflow/loop.md` state graph. It reads
  the current position, dispatches the next step to a skill or subagent, and advances — keeping its own context
  thin by pushing real work into subagents.
- **Checkpoints** are durable parks, not blocked processes: the loop records where it stopped and can be
  resumed later (even after the terminal closes) once your verdict lands.
- **The console + bus** is one local daemon that serves the read-only cockpit *and* accepts your verdicts,
  new tasks, and outward-action releases — then a relaunch-runner can wake the loop and drain them, so an
  approval you give while away actually moves the project forward.
- **Discipline** is enforced, not hoped for: engineering rules with concrete per-stack enforcers, mechanical
  pre-commit gates (secret-scan, a protected-branch push floor, plan-coverage checks), and an
  alignment scan that keeps the built code honest against the spec.

## How it was built

This repo shows its work. The `product/` directory is the installable plugin — its
[`MANIFEST.json`](product/MANIFEST.json) is the single source of truth for exactly what ships. Everything
outside `product/` is the **construction record**: the full design spec, the reasoning behind every call, and
the maintenance tooling live under [`docs/design/`](docs/design/) — the numbered design documents and an
append-only decision log. It is dense and internal by design; you do not need any of it to *use* the workflow,
but it is all there if you want to see why the thing is shaped the way it is.

**Project status** (what's built, what's left, the phased plan) has exactly one home:
[`docs/design/11-roadmap.md`](docs/design/11-roadmap.md).
