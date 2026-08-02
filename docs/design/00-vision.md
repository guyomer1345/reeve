# 00 — Vision, Goals, Guardrails

## The product
An autonomous but **disciplined** dev workflow that builds like a professional engineer, delivered as
a **pure Claude-Code-native config package** (skills + subagents + hooks + slash commands + scripts +
CLAUDE.md) the developer installs into their OWN Claude Code and runs locally on their OWN
subscription. **[DECIDED]** *(No MCP component: the in-session blocking MCP tool was rejected as the
runtime foundation — D90 — and nothing MCP ships; the local channel is the bus daemon.)*

It is NOT a program/website/SDK that drives Claude. It is content the user runs in their own Claude Code.

## Core loop (the spine — fully specced in `01`)
roadmap → execute → test → document → audit → next — running autonomously, pausing only for human
checkpoints and direction. (Known to be incomplete: research, debug, and more phases exist.)

## What makes it different
- An auto-driving disciplined-engineer macro-workflow (not vibe-coding).
- A **manual human-test gate** — pauses for a human to QA the live app, then resumes.
- A **project knowledge base** (typed code graph + per-file experiential memory) that powers autonomy.

## The master rule (non-negotiable) **[DECIDED]**
**Never sit in Claude's request path.** Config the user runs locally = clean. A hosted program that
injects into / routes the Claude session on behalf of users = prohibited. Everything runs locally on
the user's machine; components talk via the local bus + files, never by routing Claude.

## Human-in-the-loop model **[DECIDED]**
The human is active in two modes, plus in-flight checkpoints:
- **Inception (heavy):** define tech stack, MVP goals, product screens, core features, integrations
  (billing/auth).
- **Steering (ongoing):** request screen/design/feature changes → become todos for the orchestrator.
- **Checkpoints:** the machine pauses for manual QA at defined points.

Between these, the machine runs autonomously. Design tenet: *if it pings the human more than they'd
act by hand, it failed.*

## MVP scope **[DECIDED]**
- **In:** the full loop; persistent agents; the local website (visualization + control); manual
  checkpoints WITH help (contextual steps + verified deep-links + breadcrumb paths — D98); the knowledge
  base; graceful session handoff.
- **Out (designed-for, not built):** richer checkpoint help (screenshots of where settings live, screen-share
  + live Claude feedback — D98); automated testing; "test-from-anywhere" (run-while-away → spin test env → reach it
  remotely → ping phone — the *remote* half now rides the console's identity-gated remote surface, D112, not the
  retired unauthed tunnel); the paid device/QA platform.

## Operating scope **[DECIDED]**
Single local project, single user, single machine; the workflow runs inside the repo it's building.

## Repo = spec + package **[published shape DECIDED — D125]**
This repo is **one transparent monorepo** that is both the spec and the package. The installable plugin lives
under **`product/`** (the plugin root; its `product/MANIFEST.json` is the single source of truth for what ships);
the **construction record** — the numbered design docs + the decision log — lives under **`docs/design/`**, and
the meta-only tooling outside both. A consumer installs `product/` and follows the front-door `README.md`; a
contributor reads `docs/design/`. For what's built vs still open, see `11-roadmap.md` (canonical status).
*One repo, not a distilled twin (D125): the reasoning trail is the workflow's own dogfooded output, and a
hand-maintained twin is the drift this project exists to kill.*
