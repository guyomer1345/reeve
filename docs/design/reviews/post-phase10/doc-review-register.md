# Post-Phase-10 Doc-Review Register (coherence cold-audit)

**The D89 tier-3 phase-boundary `align` cold-audit** — the full-surface read-only sweep the `align` skill reserves
as an explicit one-off (`skills/align/SKILL.md:113`), run because diff-scoped `align` is anchor-blind and the
surface has moved **29 commits / D155 → D176** since the last one.
COHERENCE, not substance: does the whole surface agree with itself and with the built artifacts? Where a
doc↔artifact drift was a *mechanical* D80 repair (stale ref / retired mechanism still named / a decided fact a
second copy never learned / a doc contradicting its own owner) it was **auto-fixed** in this commit; where it needs
**judgment** (a design call, a shipped default, a build task) it is **logged below**, not resolved.

- **Base commit:** `c0b3272` (the post-Phase-7 register, 2026-08-02). Branch `worktree-phase9-capture` at
  `9e4dcb6`, identical to `main`/`origin/main`. **HEAD:** `9e4dcb6`.
- **Scope:** 29 commits, 72 files, +10,776/−582 lines — **D155 → D176**: Phase 8 (release discipline, the `version`
  deletion, the console's read side + `answer`), Phase 9 (chain-forecast, context-budget law, org mode), and
  Phase 10 (truth-in-shipping). Nothing in that range had ever been cold-audited.
- **Method:** five meta-gates run green first → the **entire** doc surface (`00`–`11`, the prior registers,
  `CLAUDE.md`, `README.md`) and the shipped surface (20 skills · 2 agents · 4 commands · `shared/` · `templates/` ·
  `rules/` · `MANIFEST.json`, plus `check_doc_budget.py`/`check_contracts.py`/`drain.py`/`codemap.py` where a doc
  claim had to be checked against real behaviour) read **in one context** rather than fanned out — coherence is a
  cross-document property, and a fan-out fragments exactly the comparison being made. Every finding was
  **re-verified against the actual artifact** before acting.
- **Autonomy contract honoured:** no `08-decision-log.md` edits; no D-numbers assigned; no judgment call resolved;
  no new entry added to `07`'s register (that is design state, and it is the maintainer's).
- **Companions:** `reviews/pre-phase3/` and `reviews/post-phase7/` (both fully resolved).

---

## Verdict

**The surface is in materially better shape than at the last audit, and the one serious finding is not a doc bug
at all — it is a shipped measurement that is wrong.**

Phase 10 was itself a truth-in-shipping pass, and it shows: the three over-claims it retracted are *genuinely*
gone from `product/` (`graph.observed.json` appears in no shipped file; the `sensitive` marker survives only as
`drain.py`'s deliberately-structural `_sensitive()`; the refused `commitment` node field is deleted and
`schemas.md:39` now carries an explicit do-not-re-add note). Six auto-fixes is half the last audit's thirteen, and
none of them is in the shipped package's *behaviour* — they are stale numbers, a retired mechanism in the README,
and two enumerations that lost a member.

**The finding with teeth is JF1: the context-budget estimator under-reports by ~21%, which is the exact failure
D167 declared it could not have.** D167 derived `chars_per_token: 3.2` from a single observation — `11-roadmap.md`
was 85,083 chars when it paged at the 25 000-token ceiling — and concluded "≤ 3.40 chars/token", then shipped 3.2
"for margin below the measured bound". That inference does not hold: paging gives an **upper** bound on
chars/token, and margin below an upper bound buys nothing, because safety requires a **lower** bound. Measured
directly during this audit against the very tokenizer that enforces the ceiling: `07-open-questions.md` paged at
**26,879 tokens for 71,287 chars = 2.652 chars/token**. The gate scores that file **22,277 — green, with 2.7k of
apparent headroom — while it demonstrably cannot be read in one call.** `shared/schemas.md`, a **shipped** doc,
believes it has 4.4k of headroom and actually has about 200 tokens.

That is one class of failure, not a one-off. The other five auto-fixes are the familiar shape — a decision retired
a mechanism or completed a phase, and the blast-radius sweep reached the primary surface but not a terse one.
**Two are recurrences of findings this repo has already fixed once**, which is the honest reading and is worth
stating plainly:

- **A2 is last audit's A13 again.** `11`'s own Phase-5 paragraph *records the lesson* ("this paragraph is the
  historical framing of *why it opened*, not a live 'next slice' pointer — it read as one for four phases after
  Phase 5 closed") and then, nine lines later, re-creates the identical construct for Phase 10. Writing the lesson
  down in the same paragraph did not prevent re-making it.
- **A5 is last audit's A10 again** — a maintenance target declared by the owner (`prioritize`) and by `loop.md`'s
  own prose, missing from `loop.md`'s routing table *and* its diagram, and invisible to `check_contracts.py`
  because the linter only checks that *named* targets resolve.

**No finding contradicts a built artifact's behaviour.** Where a doc and the code disagreed, the code was right in
every case; the docs were repaired to it. The one place the *code* is wrong is JF1, and it is logged, not fixed.

The mechanical gates behaved exactly as their honest ceiling predicts: all five green **before** this pass and
green after. They check counts, `D1–DN` ranges, roadmap tags, enum presence, the routing-graph structure and the
ship boundary — none of which is prose or arithmetic. Every finding below lived in one or the other.

---

## Auto-fixed in this commit (pure-coherence — no design call)

| # | File(s) | The drift | Fix |
|---|---|---|---|
| A1 | `README.md:45-48` | **D164 deleted `version` from `plugin.json`** — delivery keys on the **commit SHA**, and `claude plugin update` is no longer a no-op over changed content. The README still told a reader that update "compares *versions*, which move once per release rather than once per commit", i.e. the retired mechanism, as the *reason* to re-install. `commands/update.md:80-85` and `scripts/dev-reinstall.sh:26` both already carry the correction; the front door did not. | Restated to the SHA key, keeping the re-install advice but on its **real** remaining reason: an **uncommitted** working-tree edit has not moved the SHA. |
| A2 | `11-roadmap.md:481` · `:1082` | **`### Phase 10` called "the live pointer" at two sites while `:978` declares it COMPLETE (D176).** The status OWNER contradicting itself about its own current phase — and the *same file* records this exact lesson from Phase 5 at `:475-476`. | Both restated as historical framing + COMPLETE, each stating plainly that **no successor to Phase 10 is declared** → JF2. |
| A3 | `07-open-questions.md:572` | The `[core-ish]` grounding-instruction entry cited `08-decision-log.md` at **~186k** (actual **~209k**) and `11-roadmap.md` at **~32k** (actual **~37k**) — and the second **contradicted `07`'s own `:676`**, which says 37.5k. A `[watch]` entry whose numbers have gone stale is a watch that has stopped working. | Both refreshed and marked *estimated*. |
| A4 | `07-open-questions.md:684` | The register's self-measurement — "**21.4k**, ~3.6k of headroom" — never learned the D176 section appended below it (actual **22.3k** estimated). | Refreshed, and cross-pointed to JF1, since the *estimate* is now the thing in doubt rather than the headroom. |
| A5 | `templates/loop.md:19` (routing table) · `:162` (diagram) | **The doc-size maintenance trigger was missing from the authoritative routing graph.** `prioritize/SKILL.md` step 2 (the owner) declares **three** decoupled triggers and `loop.md`'s own § Maintenance items (`:132`) names all three — but the routing table's trigger cell said "retention or drift" → `document:audit` / `align`, the diagram said the same, and `doc-budget` had no row where the other two each have one. `check_contracts.py` only checks that *named* targets resolve, so a missing member is invisible to it. | Trigger cell + diagram node extended to all three; a `doc-budget → commit` row added, transcribing what § Maintenance items already decides ("a maintenance item is self-contained … flows straight to `commit`"). Linter green. |
| A6 | `06-knowledge.md:142` | The observed layer was tagged **"impl Phase-2/3"** — both phases are COMPLETE and closed **without** it; D175 settled its tier as `[stageable]` and **Phase 10a retracted the two shipped claims that implied it existed** (`codemap.py`, `verify/SKILL.md`). A design doc scheduling work into completed phases reads as "built". | Retagged **UNBUILT**, naming D175's tier and D176's retraction, and stating that the section is a design rather than a description of the tree. |

**Gates after these edits:** all five green (`check-no-spec-refs` *8 shipped paths* · `check-status-coherence`
*20 skills + 2 agents; max D176* · `check_enum_coherence` *4 enum, 1 registry, 3 layout* · `build-release`
*63 shipped files, 22 install entries* · `check_contracts` *0 advisory*). **Full suite: 853 passed** (unchanged —
these are prose edits, and the suite is the proof they changed no behaviour).

---

## Judgment findings (NOT auto-fixed — the maintainer's to resolve)

### JF1 — The context-budget estimator under-reports by ~21%, so the hard gate passes files that cannot be read *(HIGH — the only finding here that is a live defect in shipped code)*
- **Area:** `product/scripts/check_doc_budget.py:63` (`"chars_per_token": 3.2`) · its `:32-33` rationale ·
  `shared/schemas-runtime.md:57-60` (the owner of the numbers) · `shared/memory-model.md:91` (the law) · **D167**
  (the calibration).
- **What the docs claim.** `memory-model.md:91`: for the on-demand set "the hard number is not a preference: it is
  the **Read tool's 25 000-token ceiling**, past which a file cannot be loaded in one call at all. That is
  enforcement that is a *failure*, not advice." D167 is explicit that "**under-reporting is the one failure this
  cannot have, because it lets an unreadable file pass**," and `check_doc_budget.py:32` says 3.2 ships "for margin
  below the measured bound."
- **The incoherence — the derivation is unsound, and it is unsound in the unsafe direction.** D167's single
  observation is that `11-roadmap.md` was **85,083 chars** when it paged at the 25 000-token ceiling. I confirmed
  that char count against git at `9d13b3c`. But "it paged" means tokens **> 25,000**, which yields
  chars/token **< 3.40** — an **upper** bound. A divisor is safe only if the true ratio is **≥** it, so margin
  *below* an upper bound provides no safety at all; the true value is free to sit anywhere beneath it, and it does.
- **Measured, this session, against the tokenizer that actually enforces the ceiling:**
  - `07-open-questions.md` — **71,287 chars → 26,879 tokens** (the Read tool reported the count as it paged) =
    **2.652 chars/token**. The gate scores it **22,277**: green, ~2.7k of apparent headroom, and unreadable.
  - `shared/schemas.md` — 65,779 chars, read whole **without** paging ⇒ <25,000 tokens ⇒ **>2.631 chars/token**.
    Independent, and consistent to within 1%.
  - So the shipped divisor is **~21% too high**, and the error is systematic rather than content-specific.
- **Why this matters more than the arithmetic.** `schemas.md` is a **shipped** doc that `07:648` tracks as
  "~20.6k … ~4.4k of headroom left". At the measured ratio it is at **~24.8k — roughly 200 tokens of headroom.**
  It is one edit from being unreadable, and the file it would fail is the one both `check_contracts.py` and
  `check_enum_coherence.py` parse. The failure is also **silent by construction**: the gate reports green, and the
  only symptom is a consumer paging mid-read — which is precisely how this was found.
- **Why not auto-fixed:** changing a shipped default is a content change to the package, not a coherence repair,
  and the right answer is genuinely not obvious. D167's *Rejected* list already weighed and refused a pip
  tokenizer ("the package is stdlib-only by construction and a size gate does not justify the first dependency"),
  which is the only route to an exact count — so this is a real trade, not an oversight to patch.
- **Options, for the record.** (a) **Re-derive the divisor from a two-sided measurement** — the cheap fix; ~2.6
  is supported by two independent readings here, and the *method* (page a file, read the reported count) is
  repeatable and could be written down so the next calibration is not a one-sided bound again. (b) **Lower it with
  stated margin** — e.g. 2.5, accepting more false advisories for a hard tier that means what it says. (c)
  **Revisit the stdlib-only refusal** for this one number. (d) Leave it and **downgrade the claim** in
  `memory-model.md` from enforcement to estimate — honest, but it forfeits the one property the hard tier exists
  for. *Whatever is chosen, the derivation note in `check_doc_budget.py:32-33` should record that a paging
  observation bounds the ratio from **above** only — that is the reasoning error, and it will otherwise be
  re-made at the next calibration.*

### JF2 — `11` declares no successor to Phase 10, so the status owner cannot answer "what's next" *(MEDIUM — a recurrence of post-phase7 JF4)*
- **Area:** `11`'s *Recommended sequence*. Phases 1–10 are all COMPLETE. A2 above retired the two stale
  "live pointer" sentences, but retiring them does not supply the answer.
- **Incoherence:** `CLAUDE.md`'s *Where we are* sends every reader to `11`'s *Recommended sequence* for "where we
  are and what's left", and `11` is the declared owner of that fact — but after Phase 10 it names no next slice.
  This is **exactly JF4 from the last audit**, one phase later: that one was resolved by D155 opening Phase 8, and
  the same gap has reopened at Phase 10's close.
- **Why not auto-fixed:** what to build next is the maintainer's call, full stop. A coherence pass may say the
  answer is missing; it may not invent one.
- **What the record already offers, without recommending any of it.** `11`'s Phase-10 section explicitly defers
  four candidates *with stated triggers* (proportional-rigor triage · the project-map tab · model+effort routing ·
  symbol-level knowledge paths), and `07` carries two live `[watch]` items that are arguably now due: the
  **`11-roadmap.md` split** (37k, and `07:682` says "Revisit at Phase 10's close" — that close has now happened)
  and the **native-Windows residual** from 10b, which `07:688` states is the realistic unverified case. JF1 above
  is a third candidate. Declaring the sequence *closed* and working the by-space menu is also a legitimate answer —
  `11`'s own framing before D175.

### JF3 — The package's own docs still have no budget gate, and that asymmetry is now load-bearing *(MEDIUM — carried from `07`, sharpened by JF1)*
- **Area:** `07:567-570` (the open residual) · `check_doc_budget.py` (scans a *target project's* docs).
- **Status: verified still true, and now materially worse than when it was filed.** `07` already records this as
  deliberate ("D164 had just *deleted* a meta-gate, and adding one back needs a better reason than symmetry"). The
  better reason has now arrived from two directions: every size figure in `07` is **hand-measured**, and A3/A4
  above are what hand-measurement decays into within one phase; and JF1 shows the numbers were being hand-computed
  with a divisor that is **wrong**, so the manual process was reproducing a systematic error with no check on it.
- **Why not auto-fixed:** it is a build task (extend the gate's scan set to the meta-repo, or add a meta-gate), and
  it should be sequenced **after** JF1 — wiring a gate whose estimator under-reports would encode the error rather
  than catch it. Filed here so the two are resolved in the right order, not so it is resolved now.

---

## Cross-check — what this pass deliberately did NOT touch

- **`08-decision-log.md`** — untouched, per the autonomy contract. D167 carries the unsound derivation JF1 is
  about; it is **correct as history** (it records what was measured and concluded at the time), and the log is
  append-only. The repair belongs in the *code* and its comment, not in the record of the decision.
- **`07`'s open questions** — read in full. None stale, and the register is unusually well-maintained: the D176
  entries correctly record the native-Windows residual and the `loop.md` side-doors parser limit. Only the
  **numbers** were wrong (A3/A4), not the substance. **No new entry was added** — a new open question is design
  state and belongs to the maintainer; JF1–JF3 live here instead.
- **Phase 10's own retractions** — spot-verified rather than trusted: `graph.observed.json` appears in **no**
  shipped file, `self-host` in none, and the refused `commitment` node field is gone from `schemas.md` with an
  explicit do-not-re-add note at `:39`. 10a did what it says it did.
- **`05`'s layout tree** — checked mechanically by extracting every `.workflow/<path>` reference across the
  shipped surface and diffing against the tree (the technique that found last audit's A5). Two paths appear that
  the tree does not list — `.workflow/docs/` and `.workflow/rules/` — and **both are test fixtures only**
  (`test_check_doc_budget.py`, `test_review_bundle.py`). The org-mode `docs_root` case *is* covered, by the tree's
  inline org note at `:202-204` plus the `<docs_root>` variable in `start.md:86`. **No finding** — recorded
  because the absence of one is the useful result here.
- **Historical drive records** (test counts, measured recall figures, timings in `11`) — left as written. They are
  stamped to the decision that produced them and are history, not status.
- **`reviews/pre-phase3/` and `reviews/post-phase7/`** — verified still FULLY RESOLVED. Two post-phase7 findings
  **recurred** in new locations (A13→A2, A10→A5); that is drift in the *surface*, not a residual leaking out of
  those registers, and both are fixed above.

*Register produced autonomously. Auto-fixes applied + committed this run; `08-decision-log.md` untouched; no
D-numbers assigned. JF1–JF3 are the maintainer's to resolve.*
