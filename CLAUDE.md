# reeve — working brief

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
  `check_owner_sweep.py`,
  `check_enum_coherence.py`, `check-template-budgets.py`, `check_install_closure.py`, `build-release.py`, `dev-reinstall.sh`,
  `exit_test_wave_coherence.py`, `smoke_drive.py`), plus their
  tests. **`smoke_drive.py` is the one that runs the package as an INSTALLED WHOLE** — throwaway repo,
  manifest install, real `/start`, one real item, then seam assertions; both bootstrap modes. It spends real
  model calls and **must never join the routine suite**; its `--self-test` (the negative controls) does, and
  `build-release.py --out` refuses to emit without a current receipt, so it is a control rather than a
  documented step. `check-template-budgets.py` is the one that binds *this* repo to the package's own context budget:
  the shipped gate walks an installed project, so `product/templates/*` is invisible to it — that one measures
  them **at source**, through the shipped gate's own estimator and role rule (D184).

## Ground yourself first (read before proposing anything)
- **`docs/design/11-roadmap.md`** — the complete by-space map of what's left + the phased build sequence
  (canonical status). Its **`### The ordered build sequence`** is the live work order — read that first; it is
  the single owner of *what to build next, and why in that order*. It is marked **▶ START HERE**, and the
  next thing to build is the subsection marked **`▶ NEXT`** — its parent heading names that subsection's title
  too, so the two must agree. **It is NOT the first subsection**, and saying so here was wrong for nine closed
  entries: the sequence runs in BUILD order, so closed work sits above the live entry, not below it. A session
  that trusted the old wording landed on a slice closed days earlier. Everything that is not `▶ NEXT` or
  `Then —` is closed work kept for its reasoning. **Read the `ACCEPTANCE LEDGER` sections immediately above it first** (one per request — Phase 12's, then
  Phase 13's; ask numbers are GLOBAL across them, because the asks are the maintainer's, not a phase's): they own
  what the maintainer actually ASKED FOR, and every queue entry cites an ask number. It exists because five of ten
  asks were delivered as closed while unmet — a request with no durable owner goes missing silently (D214).
  **An ask with no item against it is work that has been lost.**
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
  doc for the fact you just changed, update its owner, repoint the rest — then **two** mechanical backstops, both
  auto-running at commit via `.git/hooks/pre-commit`. `scripts/check-status-coherence.sh` keeps roster counts,
  `D1–DN` ranges and roadmap `**[…]**` tags in their owner. `scripts/check_owner_sweep.py` catches the sweep you
  did not do, in three decidable shapes: a decision that says it settled an `07` question while `07` still reads
  as open; an `[ask #N]` carrying both a CLOSED queue entry and an open one (a ghost that gets built twice); and
  an ACCEPTANCE LEDGER row with **nothing against it** — no tagged entry and no discharger named, which is
  `D214`'s own defect mechanized (`D223`). **Its stated blind spot is a
  section HEADER that contradicts the items under it** — prose agreeing with prose is not decidable, so that half
  is still yours. Same logic applies to any single-source-of-truth claim.

## Where we are
**Status is single-source — read the current phase + what's left from `docs/design/11-roadmap.md` (its _Recommended
sequence_).** This section carries **no copy of the phase list and no phase count** — an earlier version restated
a four-phase order while the roadmap had grown to seven, which is the drift D80 exists to stop. *Where* we are, and
*how many* phases there are, live in `docs/design/11-roadmap.md` alone.

**A session resuming after 2026-09-19 has STANDING ORDERS, and they live in the work order, not here** —
`11`'s `### The ordered build sequence` § `▶ NEXT`, in the blockquote at the top of that entry. They are the
maintainer's, dated, and scoped to that queue: drive it end to end, do not stop to ask between items, capture
as each one closes. **They expire when the queue does** — and this pointer goes with them, because a standing
order left in `CLAUDE.md` after its stretch is over is an instruction with no owner. Read them before starting;
they suspend the "never capture unprompted" rule above for that queue and nothing else. **The queue they govern
now is the unattended-drive bundle, and its item 0 is BLOCKING: an overnight run's artifacts are read before
anything is built, because they may reorder the rest.**
