# 05 — Shared State + Comms Bus (Space 5)

## Why it's its own space **[DECIDED]**
Because agents are persistent but the orchestrator stays lean, and the website is local-only, every
connection between spaces runs through **disk artifacts + a local bus**. Designed deliberately so it
doesn't grow ad hoc.

## The comms bus **[DECIDED — A3 research]**
A **local HTTP loopback service** (the website's backend) is the message channel.
- website → orchestrator: POST to localhost (verdicts, instructions); orchestrator reads via curl / a
  local MCP tool.
- orchestrator → website: orchestrator writes `state.json`; website reads it (inotify / poll).
- File-watching is **rejected for control-flow** (fragile, polling, races); fine only for one-way
  state display.
- **Verdict delivery — durable inbox + token correlation (D90/D91):** a checkpoint mints a **token**
  (`{ticket}:{step}:{uuid}`); the bus appends each incoming verdict to an **append-only file inbox**
  (`.workflow/inbox/`, atomic write+rename = durable, at-least-once). The orchestrator matches verdicts to parked
  tickets **at boundaries, idempotently, single-shot**; a token for an unknown/closed ticket → **dead-letter +
  surface** (never a silent resume); a stale deadline → **escalate**. The verdict resumes its ticket via
  `claude --resume <id> -p "<verdict>"` (D90). This is the correlation half of continue-while-parked interleaving.
- **Reserved action — `node/subgraph → ticket` (D70):** the project-map screen emits a scoped **backlog
  item** (payload: node ID(s) + the ask) — an ordinary D69-triaged intake item, never a privileged fast-path;
  UX deferred. Node IDs are the code-map's stable addressable keys (today relpath/module; symbol-level later).

## Disk layout **[layout DECIDED — D53/D62; read/write protocols EXPAND]**
`init` (`commands/start.md`) scaffolds this layout in a target project:
```
<launch root>      # where Claude runs = orchestrator home (process / machinery)
  CLAUDE.md         # orchestrator brief (greenfield: here; brownfield: a marked block in the existing one)
  .workflow/
    config.json     # project_root (./project | .) + run config    (committed)
    loop.md         # routing graph + diagram (fixed topology)      (committed)
    state.json      # live position (item/phase/wave) — RUNTIME, gitignored
    handoff.md      # durable resume anchor                         (committed)
    backlog.md      # live OPEN queue: issues + roadmap (closed leave) (committed)
    checkpoints/    # RESERVED — demoted (D60); no writer yet
    parked/<id>.json # RUNTIME — a parked ticket's resume record (token, state, predicted_outcome, deadline) — D91, gitignored
    inbox/          # RUNTIME — append-only verdict queue the bus writes; matched at boundaries — D90/D91, gitignored
    items/<id>/     # per-item artifacts (mkdir on demand; pruned once closed — D61)  (committed)
  <worktrees>/      # RUNTIME — one git worktree per in-flight ticket (D91); raw `git worktree`, gitignored
  <project_root>/   # the product (greenfield: project/ ; brownfield: the repo root)
    CLAUDE.md       # the product's own brief
    llms.txt        # thin agent entry point → points into docs/knowledge/  (committed)
    docs/           # ← the DOCS-ROOT — durable product knowledge (D62)
      spec/         # the product spec (discuss fills it)           (committed)
      architecture.md  # inline Mermaid-C4 L1/L2 (document-owned)   (committed)
      knowledge/    # code map — Space 6 (index.md, graph.json, nodes/)  (committed)
      decisions/    # decision-records = ADRs (append-only, global) (committed)
    <product code>
```
**Commit policy:** everything durable is committed; the **runtime** view (`state.json`, `parked/`, `inbox/`, the
per-ticket worktrees) is gitignored.

**Continue-while-parked isolation (D91):** each in-flight ticket develops in its own **git worktree** on its own
branch; a checkpoint parks it with a `WIP:` commit + a `parked/<id>` record, and the loop interleaves to the next
independent ticket (≤3 concurrent, prefer-serial). `handoff.parked[]` lists every parked ticket so a cold start
rebuilds them all from `parked/` + `inbox/`. Resume = un-WIP → `rebase` onto trunk (`rerere`) → `verify` → final
commit → merge → `worktree remove`.

**Memory tiers (D38 — `shared/memory-model.md`):** every durable file is **volatile** (rewrite freely:
`state.json`, `handoff.md`, and `backlog.md` — a live *open* queue, closed items leave, D59), **stable**
(change only with the code that changes it, CI-gated: `docs/spec/`, the inline Mermaid-C4 `docs/architecture.md`
— D41, *not* a separate `diagrams/`), or **append-only** (supersede, never edit: `docs/decisions/`, the
per-file `# Sessions` sections). Skills key off location + filename to know their rights.

**Resume model (D48).** `state.json` is the volatile live pointer (rewritten in place); `handoff.md` is the
durable resume anchor (program counter — current item + loop position + parked work); **git history is the
append-only completed-step log** (each item ends in a `commit`). Mid-run the orchestrator reads `state.json`;
a cold start reads `handoff.md` + `git log` and rebuilds. **Bounded by construction (D51):** every
always-read file (`CLAUDE.md`, `state.json`, `handoff.md`, `loop.md`) holds current state only — never history.

Still to close: read/write ownership per file + the request/response protocol; symbol-level knowledge paths.
*(Retention/read law closed — D61; docs-root unified under `<project_root>/docs/` — D62.)*
