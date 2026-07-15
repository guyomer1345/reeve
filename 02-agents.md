# 02 — Agents (Space 2: persistent specialists)

> **Roster v1 CLOSED (2026-06-29) → `10-roster.md`.** The full skill + agent roster, I/O contracts in
> the package files (`skills/`, `agents/`, `shared/schemas.md`), loop order + call-graph pinned. The notes
> below are the original sketch, kept for provenance. The **collision-model independence test** is now
> **DECIDED (D91)** — the eligibility predicate lives in `01`/`10`; the `prioritize` **interrupt model** is
> closed too (pure queue, D26).

## Key fact **[DECIDED]**
Agents PERSIST — they hold their own context and can be continued via SendMessage. They are NOT
one-shot/stateless. The orchestrator spawns them and routes between them. (See D4.)

## Known roles (sketch — NOT the final roster) **[SUPERSEDED → `10-roster.md`]**
Mentioned so far: planning, investigation/research, execution, debug, **Arbiter** (decision-maker —
renamed from the placeholder "sequential decision maker"). The full roster is explicitly bigger and
undecided.

## To close **[CLOSED → `10-roster.md`]**
- The v1 roster: names + responsibilities.
- Each role's I/O contract (what it's seeded with on spawn, what it returns).
- Which agents are long-lived vs short-lived.
- Topology: does only the orchestrator spawn agents (strict hub-and-spoke), or can agents spawn
  sub-agents (nested)?
- How each maps to a Claude Code primitive (subagent / agent-type definition).

## Collision model **[DECIDED — D91; see `01`]**
How the orchestrator decides two agents' tasks are independent enough to run in parallel (file/module/
area overlap). Resolved: the eligibility predicate is **dependency-ready ∧ file-disjoint ∧ ¬1-hop code-map
neighbor** (`01` Concurrency; D91).
