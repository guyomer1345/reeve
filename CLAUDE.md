# dev-autonomous-workflow — working brief

This repo is the **spec for "the disciplined builder"**: an autonomous-but-disciplined dev workflow shipped as
a pure Claude-Code-native config package (skills + subagents + hooks + slash commands + CLAUDE.md) that a user
runs locally on their own subscription. Master rule: **never sit in Claude's request path.** Six design
spaces — orchestrator · agents · website · checkpoints · shared-state · knowledge.

> This file is working-guidance for editing **this spec repo**. It is *not* the `orchestrator-CLAUDE.md` the
> package ships into target projects (that lives in `product/templates/orchestrator-CLAUDE.md`).

## Repo layout (D125)
- **`product/`** — the installable plugin (everything that ships). Its **`product/MANIFEST.json`** is the single
  source of truth for *what ships*; the leak gate, `/start`'s install step, and the release build all derive from it.
- **`docs/design/`** — this construction record: the numbered design docs `00`–`11` + the `08` decision log +
  `reviews/`. Dense and internal by design; a consumer never needs it.
- **`scripts/`** — meta-only tooling that never ships (`check-no-spec-refs.sh`, `check-status-coherence.sh`,
  `check_enum_coherence.py`, `build-release.py`), plus their tests.

## Ground yourself first (read before proposing anything)
- **`docs/design/11-roadmap.md`** — the complete by-space map of what's left + the phased build sequence (canonical status).
- **`docs/design/08-decision-log.md`** — every decision: the call, why, what was rejected, the evidence.
- Then the numbered spec docs `docs/design/00`–`11` + `product/shared/` as the topic needs.

The **`docs/design/` spec folder is the source of truth.** Don't duplicate what it already records.

## How we work — design-first
- **Discuss and critique before capturing.** The maintainer writes his own thinking first and wants a *peer*
  who pushes back — **hard critique: find the gaps, say what's missing, no premature agreement.** Prefer crisp
  operational rules over vague wording.
- Keep decisions **in the conversation while in flux.** Only when the maintainer says a slice is closed,
  **capture it**: edit the numbered spec docs **and** add a matching `docs/design/08-decision-log.md` entry (call · why ·
  rejected · evidence). **Never capture unprompted.**
- The project's own memory law applies to its docs: lean files, pointers not duplication, history in git
  (`product/shared/memory-model.md`; D38 / D51 / D61).
- **Status is derived — one OWNER per fact, never a second copy (D80).** Owners: roster count → `docs/design/10-roster.md`'s
  table · phase / what's-left → `docs/design/11-roadmap.md` · decisions → `docs/design/08-decision-log.md` · open design-questions →
  `docs/design/07-open-questions.md` · structure → `graph.json`. Every other doc *points* to the owner or is *generated* from it; a new source is **adopted**
  deliberately (declare its owner), never accreted. **On capture, run the blast-radius sweep:** grep every guiding
  doc for the fact you just changed, update its owner, repoint the rest — then `scripts/check-status-coherence.sh`
  is the mechanical backstop (roster counts, `D1–DN` ranges, and roadmap `**[…]**` tags stay in their owner;
  auto-runs at commit via `.git/hooks/pre-commit`). Same logic applies to any single-source-of-truth claim.

## Where we are
**Status is single-source — read the current phase + what's left from `docs/design/11-roadmap.md` (its _Recommended
sequence_).** This section carries **no copy of the phase list and no phase count** — an earlier version restated
a four-phase order while the roadmap had grown to seven, which is the drift D80 exists to stop. *Where* we are, and
*how many* phases there are, live in `docs/design/11-roadmap.md` alone.
