# Skill & Agent Authoring Format

One canonical shape for every package file, so the roster reads as a graph of typed nodes
(`Inputs → … → Output → Route`). A **menu, not a mandatory skeleton**: the spine is required; the rest are
included only when they earn their tokens (Anthropic: *"concise is key"*). Definitions live in the contract
sections — name `shared/schemas.md` artifacts; don't re-explain them in prose.

## Skills (`skills/<name>/SKILL.md`)

**Frontmatter** (required)
- `name` — lowercase-hyphen; the workflow-node verb (`verify`, `commit`). Kept **imperative on purpose** —
  gerund is Anthropic's default, but these names double as routing-graph labels.
- `description` — third person, ≤1024 chars: *what it does · when to use it · where it routes on failure*.
  This is what the orchestrator matches on; make it specific.
- `allowed-tools` — optional; only to **constrain** (e.g. a read-only skill that must not Write).

**Body**
- `# <Name> — <one-line role>` — required.
- **Core principle** — optional, ≤2 lines; only when a framing invariant isn't obvious (good place to
  define jargon once, e.g. what `adjudicate` means).
- **## When** — optional. Trigger conditions, when the operational detail goes beyond the description.
- **## Inputs** — required. The artifacts it consumes, each named from `schemas.md`. The contract is
  *defined* here, not described.
- **## Workflow** — optional. Numbered steps only when genuinely multi-step; omit for lean skills.
- **## Rules** — optional. Boundaries / negative instructions — what it must NOT do (e.g. "`execute` never
  edits `docs/knowledge/`; that's `document`"). Use to stop drift.
- **## Output** — required. The artifact it emits (named from `schemas.md`).
- **## Route** — required. `pass → … · fail → …` — the directed edges of the loop.
- **## Calls** — optional. Sub-skills / agents it dispatches (a route is not a call).
- **## References** — optional. Links to bundled files, one level deep; never an inline "misc" dump.

## Agents (`agents/<name>.md`)

**Frontmatter**: `name`, `description` (third person, explicit *when-to-delegate* triggers), optional
`tools` (restrict to the minimum the role needs), optional `model`.

**Body** (system prompt) — same spine, agent-shaped:
- **Role & scope** — what it is and is *not* responsible for.
- **Inputs / when invoked**
- **Process**
- **Constraints** — what to ignore / never do.
- **Output** — the artifact or shape it returns.

## Rules files (`rules/<topic>.md`)

The thin baseline engineering principles — the agent-readable contract, machine-enforced where a tool can
check it. One file per topic (`code-style`, `testing`, `security`, `ops`), principles only, not a manual.

- **Shape**: `# <topic> — baseline`, a one-line precedence note, then a flat list of one-line imperative
  principles. No Workflow/Route scaffolding — a rules file is a list, not a node.
- **Enforcement tags**: append `— enforced by: <mechanism>` to any principle a tool can check (formatter,
  linter, typechecker, test runner, secret-scan, CI gate). These tags are the wiring manifest `/start` reads
  to install the enforcement layer; leave a purely behavioural principle untagged (the agent still honours it).
- **Precedence**: nearest-file-wins — the package baseline is the floor, a project-root `rules/` overrides it,
  and a `rules/` inside a subtree overrides the root for files under it. State this in the file's header line.
- **Scope**: engineering principles only. Loop/orchestration behaviour belongs in the orchestrator brief, not
  here; anything neither enforceable nor a durable engineering principle doesn't belong in the package at all.
- Same **no-spec-refs / plain-language** law as every package file (below).

## Rules of thumb
- Concise over complete: drop any section that only restates what Claude can already infer.
- Define contracts, don't pad prose. Jargon gets one defining line or a `schemas.md` link.
- One term per concept, used consistently across the roster.
- **No spec-internal references.** State behaviour in plain language across the *entire* shipped package —
  `skills/`, `agents/`, `shared/`, `commands/`, `templates/`, `hooks/`. Decision IDs (`Dxx`), design-doc
  numbers, and `Space N` labels live only in the design docs + decision log, which point *down* to the file —
  never the reverse. A commit-time grep gate (`scripts/check-no-spec-refs.sh`) enforces this so it can't
  silently regress.
- This format is **v1** — validated as we apply it skill-by-skill; if a skill fights it, that's signal
  about the format, not the skill.

## Source
Derived from Anthropic's [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
— "concise is key", description-as-trigger, progressive disclosure, gerund naming, cohesive library —
adapted for an orchestrated roster of small typed-node skills (where uniform Inputs→Output→Route and
imperative routing-labels matter more than the generic large-skill guidance).
