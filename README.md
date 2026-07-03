# Dev-Workflow Spec — working draft

**What this is:** the full specification for an autonomous, disciplined Claude-Code-native dev
workflow ("the disciplined builder"). The repo is **both the spec and the package being built** — the numbered
docs design it; `skills/ agents/ rules/ hooks/ commands/ templates/ scripts/` implement it.

**Status:** see `11-roadmap.md` — the canonical map of what's done, what's left, and the current phase. This
folder is the source of truth; the spec lives and is edited here directly. (This README stays status-free by
design — status is single-source.)

> **Home:** `/mnt/c/Users/Guy Omer/Documents/dev-autonomous-workflow/` (permanent working directory).

## How it's organized
- `00-vision.md` — product thesis, goals, the master rule, MVP scope.
- `01-orchestrator.md` — Space 1: the spine (macro-loop, router role, memory model, session lifecycle).
- `02-agents.md` — Space 2: the persistent agent roster + I/O contracts.
- `03-website.md` — Space 3: local console (visualization + your channel to the orchestrator).
- `04-checkpoints.md` — Space 4: the manual human-test gate.
- `05-shared-state.md` — Space 5: the on-disk state + the local comms bus.
- `06-knowledge.md` — Space 6: the project knowledge base (code graph + per-file memory).
- `07-open-questions.md` — everything deliberately deferred.
- `08-decision-log.md` — every decision, why, what was rejected, and the evidence.
- `09-intake.md` — the intake stage of the spine: task types + contracts, the demo skill + sandbox gate,
  the commitment model. (Extends `01`.)
- `10-roster.md` — Space 2 v1: the full capability roster (skills + agents), loop order, call-graph;
  per-capability contracts live in the package files below.
- `11-roadmap.md` — **canonical status:** what's built, what's left, the phased build sequence.

Package source (Claude-Code-native, D25): `skills/<name>/SKILL.md`, `agents/<name>.md`,
`shared/schemas.md`. The repo is both the spec and the package being built.

## Status legend
- **[DECIDED]** — closed; rationale in the decision log.
- **[OPEN]** — needs to be closed before build.
- **[DEFERRED]** — known, intentionally not specced now (post-MVP or later).

## What's left
See `11-roadmap.md` — the canonical, living map of remaining work by design-space and the phased build
sequence. Kept there, not here, so status lives in exactly one place.

## Home
Permanent home: `/mnt/c/Users/Guy Omer/Documents/dev-autonomous-workflow/` — the project's working
directory and source of truth. Specs are edited here directly.
