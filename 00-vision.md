# 00 — Vision, Goals, Guardrails

## The product
An autonomous but **disciplined** dev workflow that builds like a professional engineer, delivered as
a **pure Claude-Code-native config package** (skills + subagents + hooks + slash commands + MCP +
CLAUDE.md) the developer installs into their OWN Claude Code and runs locally on their OWN
subscription. **[DECIDED]**

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
  checkpoints WITH help (doc links, screenshots of where settings live, screen-share + live Claude
  feedback); the knowledge base; graceful session handoff.
- **Out (designed-for, not built):** automated testing; "test-from-anywhere" (run-while-away → spin
  test env → Cloudflare tunnel → ping phone); the paid device/QA platform.

## Operating scope **[DECIDED]**
Single local project, single user, single machine; the workflow runs inside the repo it's building.

## Repo = spec + package
This folder is the project's permanent home and source of truth; the spec is edited here directly, and the
package it specifies (`skills/ agents/ rules/ hooks/ …`) is built here alongside it. For what's built vs still
open, see `11-roadmap.md` (canonical status).
