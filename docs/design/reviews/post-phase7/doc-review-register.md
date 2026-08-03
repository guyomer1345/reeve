# Post-Phase-7 Doc-Review Register (coherence cold-audit)

**The D89 tier-3 phase-boundary `align` cold-audit** — the full-surface read-only sweep the `align` skill reserves
as an explicit one-off, run because diff-scoped `align` is anchor-blind and the surface has moved **46 commits /
D114 → D154** since the last one.
COHERENCE, not substance: does the whole surface agree with itself and with the built artifacts? Where a
doc↔artifact drift was a *mechanical* D80 repair (stale ref / retired mechanism still named / a decided fact a
second copy never learned / a doc contradicting its own owner) it was **auto-fixed** in this commit; where it needs
**judgment** (a design call, an ambiguous ownership, a build task) it is **logged below**, not resolved.

- **Base commit:** `3fb93dd` (the pre-Phase-3 register, 2026-07-16). Branch `main`. **HEAD:** `9d13b3c`.
- **Scope:** 46 commits, 105 files, +21,020/−3,632 lines — **D114 → D154**, i.e. the whole console/bus build
  (Phase 3), the demo + release surface (Phase 4), pre-test hardening (Phase 5), onboarding (Phase 6), and the
  machine-move work (Phase 7). Nothing in that range had ever been cold-audited.
- **Method:** five meta-gates run green first → the **entire** doc surface (`00`–`11`, both registers, `CLAUDE.md`,
  `README.md`) and the **entire** shipped surface (17 skills · 2 agents · 4 commands · `shared/` · `templates/` ·
  `rules/` · `MANIFEST.json`, plus `bus.py`/`drain.py`/`check_contracts.py`/`check_enum_coherence.py` where a doc
  claim had to be checked against real behaviour) read in one context rather than fanned out — coherence is a
  cross-document property, and a fan-out fragments exactly the comparison being made. Every finding was
  **re-verified against the actual artifact** before acting.
- **Autonomy contract honoured:** no `08-decision-log.md` edits; no D-numbers assigned; no judgment call resolved.
- **Companion:** `reviews/pre-phase3/` (the D89-style predecessor, fully resolved).

---

## Verdict

**The surface is coherent, and the drift that existed is one shape repeating.** Ten of the thirteen auto-fixes are
the *same failure*: a later decision **retired a mechanism** and the capture-time blast-radius sweep (D80) reached
the primary surface but not the terse or secondary ones — a schema's routing bullet, a layout-tree row, a roster
sub-list, a `Still open` line. Precisely the D89 root cause, on a surface D89 hardened against it — which is the
honest reading: **tiers 2–3 back the sweep, they do not replace it.**

Two findings are worse than cosmetic and both are **in the shipped package**:

1. **`shared/schemas.md` contradicted itself about the `sensitive` marker.** Line 161 says "there is no
   `sensitive` marker … a composer still sending `sensitive` gets a `400`"; lines 171/275/480/483 still told a
   producer to mark one — as did `skills/checkpoint`. A skill author following the routing bullet would have
   composed a payload `bus.py` **rejects**. This is a doc that *instructs* a defect, not one that merely lags.
2. **`05`'s layout tree — the D114-declared owner of every `.workflow/` path's commit-class / `bus:` / `pin` —
   was missing two paths** that landed after it (`install-set.json`, D139; `statusline.delegate`, D136). The
   `check_enum_coherence.py` layout rules hold *listed* rows to their consumers; **they cannot see an absent
   row**, so a new path acquires no owner silently. That is D114's own failure mode recurring one layer up.

The mechanical gates behaved exactly as their honest ceiling predicts. All five were green **before** this pass and
green after: they check counts, `D1–DN` ranges, roadmap tags, enum presence, the routing-graph structure and the
ship boundary — none of which is prose. Every finding below lived in prose.

**No finding contradicts a built artifact's behaviour.** Where a doc and the code disagreed, the code was right in
every case; the docs were repaired to it.

---

## Auto-fixed in this commit (pure-coherence — no design call)

| # | File(s) | The drift | Fix |
|---|---|---|---|
| A1 | `shared/schemas.md` (`checkpoint` setup route :171 · `inbox-message` verdict :275 · `secret store` header :480 + owner :483) | **D152 deleted the `sensitive` marker** (`returns` now *means* credential; `bus.py` `400`s a composer that still sends one) — but four sites still say "a `returns` value **marked** `sensitive`", contradicting the same file's own line 161. A producer following them gets a `400`. | Reworded to the structural test (a non-empty `returns` **is** the trigger; the field, not a flag). |
| A2 | `skills/checkpoint/SKILL.md:84` | Same retired marker, **four lines after** the skill's own line 61 states there is none. | Same. |
| A3 | `03-website.md:151` | "a `sensitive` verdict is redacted from the drain's output" — same retired marker (the file already carries the D152 correction at :107). | Reworded to "a credential-bearing verdict — one carrying a non-empty `returns`". |
| A4 | `05-shared-state.md:177` · `commands/start.md:73` · `skills/ingest/SKILL.md:17` | `codemap.sh` still described as **"generated per-stack"** — D72/D74 revised it to a thin **stack-independent** auto-dispatching wrapper, and `06`/`11`/`start.md:206` all say so. `start.md` contradicted **itself** (line 73 vs step 6). `ingest` names it as a per-stack input it must have. | All three reworded to the stack-independent wrapper, naming D72/D74 in `05`. |
| A5 | `05-shared-state.md` (layout tree) | **`install-set.json`** (D139, committed) and **`statusline.delegate`** (D136, RUNTIME/gitignored) are absent from the tree D114 made the OWNER of commit-class / `bus:` / `pin`. Both are scaffolded by `start.md` and have `schemas.md` owners stating those exact properties; the enum gate cannot detect a missing row. | Both rows added, transcribing the properties from their `schemas.md` owners (`bus:none`; `statusline.delegate` `no-pin`, with the reason). Gate green. |
| A6 | `10-roster.md:8-23` (Package layout) | "Claude-Code-native plugin source **at the repo root**" and "the spec (`00`–`10`)" — both retired by **D125** (`product/` is the plugin root; the record is `docs/design/00`–`11`). The `templates/` list also omitted `checks.sh` (D127) and `hooks/` listed only `guard.sh` (4 of 5 shipped hooks missing); `scripts/` was absent entirely. | Rooted under `product/`, pointed at `MANIFEST.json` as the authoritative boundary, and the four sub-lists brought to the shipped set. |
| A7 | `10-roster.md:113,126` | `/start`'s greenfield path still reads "→ **(stub)** console →", and "Stubbed sub-steps to expand: console launch, full disk layout" — the daemon is BUILT (D115/D116) and is `/start` **step 5** (D132); the layout is `05`'s tree (D114). The exact D89 class (a stale "stub" beside a built artifact); D129 already removed the twin of this from `start.md`. | Both restated as closed, naming the decisions that closed them. |
| A8 | `CLAUDE.md` (Where we are) | The section that says it "stays deliberately thin so it can't drift" carried a **copy of the phase list** — "the 4-phase order is …" — while `11` had grown to **seven** phases, all complete. A second copy of a status fact whose owner is `11`. | The copy is gone; the section now states plainly that it carries no phase list and no phase count, and names why. |
| A9 | `04-checkpoints.md:114` | Test-from-anywhere still routed through a "**Cloudflare tunnel**" — the unauthed tunnel D112 retired as unbuildable. `00:41` already carries the correction. | Reworded to the identity-gated remote surface (D112), stating the tunnel is retired. |
| A10 | `templates/loop.md` (routing table + diagram) | `create-demo`'s **refine-cap → `discuss`** escalation is in the skill's Workflow, Route **and** Calls (added there by the pre-Phase-3 A7) and is decided by D103/D154 — but it is **absent from `loop.md`**, the authoritative routing graph (D80). `check_contracts.py` only checks that targets *resolve*, so a missing edge is invisible to it. An orchestrator routing from `loop.md` alone would never escalate; it would auto-proceed past a cap that says never auto-proceed. | Row + dashed diagram edge added. |
| A11 | `01-orchestrator.md:95` · `09-intake.md:4,171` | Three sites declare the rest of the macro-loop (execute → test → document → audit → next) **still OPEN**, while `07` — the **owner** of the open-questions register — records it **CLOSED** (D47: the spine is `10` + `loop.md`). | All three restated as closed, pointing at the owner. `09`'s `Still open` list loses the stale entry. |
| A12 | `00-vision.md:5` | The package is described as "skills + subagents + hooks + slash commands + **MCP** + CLAUDE.md". **Nothing MCP ships** (zero references anywhere under `product/`), `CLAUDE.md` and `README.md` both omit it, and D90 rejected the in-session blocking MCP tool as the runtime foundation. | `MCP` → `scripts`, with a one-line note on why there is none. |
| A13 | `11-roadmap.md:401` | **"Recommended next slice — Phase 5"** — Phase 5 is COMPLETE, as are 6 and 7. The status OWNER's own next-slice pointer had been stale for three phases. | Reframed as the historical why-it-opened paragraph (matching how the Phase-4 line was reframed at :550) and states plainly that **no successor to Phase 7 is declared** → JF4. |

**Gates after these edits:** all five green (`check-no-spec-refs` *8 shipped paths* · `check-status-coherence`
*17 skills + 2 agents; max D154* · `check_enum_coherence` *4 enum, 1 registry, 3 layout* · `build-release`
*54 shipped files, 18 install entries* · `check_contracts` *0 advisory*). **Full suite: 584 passed** (unchanged —
these are prose edits; the suite is the proof they changed no behaviour).

---

## Judgment findings (NOT auto-fixed by the audit — **all four resolved by D155**)

> **STATUS: FULLY RESOLVED (2026-08-03) → D155.** The audit shipped its thirteen mechanical fixes and **zero**
> judgment calls, per the D89 contract; the maintainer then asked for the calls, and all four are taken in D155:
> **JF1** → `align` step 3 gains the **approved-demo lens** it had been credited with and never given (a read, not
> a gate; bounded by the register's existing dedup); **JF2** → retagged `[stageable — a BUILD needing a browser
> drive]` and taken **off** the align queue, since this pass proved a coherence sweep cannot discharge it — the
> field stays declared regardless, because it is what lets `returns` mean credential; **JF3** → **`docs/spec.md`,
> ONE file**, is canonical and the five directory sites are repointed (decided mechanically: D154's refine ledger
> hashes exactly one file, so a directory would silently weaken the newest floor); **JF4** → **Phase 8 opened** —
> release discipline (D151) ahead of the interaction-model rework, because it is the only open item harming a real
> installed user today. Full call + what was rejected: **D155**. *The statements below are the audit's original
> framing, kept as the record of what it found.*

### JF1 — `align` has no lens for the D154 backwards gap, and the roadmap queued it to *this* pass *(MEDIUM)*
- **Area:** `11:188-194` **[fix-later — bundle with the `align` pass; `align` is the natural detector, not a new
  gate]** vs `skills/align/SKILL.md` step 3, whose baked-in standing checks are exactly two: the
  **status-ownership** lens and the **promise↔plan mirror** lens.
- **Incoherence:** D154 put a mechanical floor under "edit the spec first" *going forward*; nothing looks backwards.
  Any project whose history contains an approved demo can hold a spec that never learned a decision made in a
  refine round — and the evidence is gone, because the terminal `approve` deletes the bundle. The roadmap names
  `align` as the detector and queued the work here, but **`align` was never given the lens**, so running the pass
  as shipped does not perform the detection the roadmap says it performs.
- **Why not auto-fixed:** adding a third standing lens to a shipped skill is a content change to the package, not
  a coherence repair — it changes what `align` *does*, and D89's contract reserves that for the maintainer.
- **Recommendation (one approval from landing):** add to `align` step 3's standing checks —
  *"**the approved-demo lens** — for any item whose history contains a terminal `approve` on a `kind: demo`
  checkpoint raised **before** the refine ledger existed, read the item's spec slice against its decision/verdict
  history and flag a decision the spec does not carry. There is no bundle left to diff, so this is a read, not a
  gate; a hit routes as an ordinary `create-issue` at the spec element's commitment."*
- **Note on this repo:** not applicable to the meta-repo's own surface (it hosts no demo history), so nothing was
  detectable here. The one measured instance was repaired by hand during the D154 drive.

### JF2 — `artifacts` still has no shipped producer *(MEDIUM · carried, not resolvable by a doc pass)*
- **Area:** `11:180-187` **[fix-later — bundle with the `align` pass]**; `shared/schemas.md:155-160`.
- **Status: verified still true, and correctly disclosed.** The field is declared, validated as strictly as
  `returns`, and pruned-from-nothing; the console's setup form renders one input per declared
  `request.tasks[].secrets[]` name, and `secrets[]` *means* credential, so the form emits `returns` only.
  `schemas.md` states this in place rather than leaving it to be discovered — so it is a **known gap, not a lie**,
  which is the property D147 established.
- **Why not auto-fixed:** it is a **build task** (a request-side `tasks[].artifacts[]` declaration + form
  rendering), not a coherence repair — and the roadmap's own note is the reason to keep it that way: it **touches
  the setup form**, the surface that broke twice under human hands in D148/D149, so it wants a browser drive.
  A coherence pass cannot discharge it; it can only confirm the disclosure is honest, which it is.

### JF3 — `docs/spec/` (a directory) vs `docs/spec.md` (a file): two owners disagree *(MEDIUM)*
- **Area:** `shared/schemas.md:8` pins the `spec` artifact at **`<project_root>/docs/spec.md`** (and `:304`
  reasons about that path); the D130 brownfield drive produced `docs/spec.md`; two shipped tests
  (`test_check_demo_bundle.py`, `test_update_reconcile.py`) use it. Against that: `05:198` (layout tree) + `05:254`
  (memory tiers), `shared/memory-model.md:11`, `commands/start.md:84` + `:426`, and `11:235` all say **`docs/spec/`**.
- **Incoherence:** `10` says artifact formats are owned by `schemas.md`; `05`'s tree owns the *layout*. Both are
  real owners and they name different things, so there is no owner to defer to — which is why this is not a
  mechanical repair. Nothing breaks today (`check_demo_bundle.py`'s `spec_ref.path` is free-form and
  repo-relative, precisely so a brownfield adoptee need not be `docs/spec.md`), so this is latent, not live.
- **Why not auto-fixed:** picking the canonical shape is a design call with real consequences — a **single file**
  is what the code and the one real drive actually produce; a **directory** is what a large multi-part spec wants
  and what `discuss` filling "the spec" over a project's life may grow into. Recommend declaring one owner
  (`schemas.md`, matching the driven reality) and repointing the other five, **or** adopting `docs/spec/` as a
  directory whose canonical entry is `docs/spec.md` — but say which, once, in the owner.

### JF4 — `11` declares no successor to Phase 7, so the status owner cannot answer "what's next" *(MEDIUM)*
- **Area:** `11`'s *Recommended sequence*. Phases 1–7 are all COMPLETE. A13 retired the stale "next slice =
  Phase 5" pointer, but retiring it does not supply the answer.
- **Incoherence:** `CLAUDE.md` sends every reader to `11`'s *Recommended sequence* for "where we are and what's
  left", and `11` is the declared owner of that fact — but after Phase 7 it names no next slice. The only
  candidate stated anywhere is the **interaction-model rework** (browser-primary async chat), which lives in `07`
  as an open question whose build the maintainer **deliberately deferred behind a proper re-drive** (D132 note),
  and which `11:643` gestures at in a Phase-6 aside rather than in the sequence.
- **Why not auto-fixed:** what to build next is the maintainer's call, full stop. A coherence pass may say the
  answer is missing; it may not invent one.
- **Options:** (a) open **Phase 8** in `11` for the async-chat rework, promoting it out of `07` the way D135
  promoted `/update` into Phase 6; (b) declare the sequence **closed** and state that work is now
  `[stageable]`-driven off the by-space list, which several remaining items already are; (c) name a
  first-dogfooding/self-hosting slice, which `07`'s project-state-view entry has wanted since 2026-06-30.

---

## Cross-check — what this pass deliberately did NOT touch

- **`08-decision-log.md`** — untouched, per the autonomy contract. Two entries carry prose that a future
  housekeeping pass may want (D152's "the marker is DELETED" is stated in `07` as a struck-through open question;
  D154's residual is stated in `11`), but neither is drift: the log is append-only history and is *correct as
  history*.
- **Open questions in `07`** — read in full, none stale. The D151 entry (a released install cannot learn it is
  stale while `version` stays `0.1.0`) is correctly OPEN with two concrete options, one of which is a **sixth
  meta-gate** in `build-release.py`. That is a live, un-actioned decision, not a coherence finding.
- **Historical drive records** (test counts, node/edge counts, timings in `11`) — left as written. They are
  stamped to the decision that produced them and are history, not status.
- **`docs/design/reviews/pre-phase3/`** — verified still FULLY RESOLVED; all nine JF items traced to their
  closures (D108/D111/D113/D114 + the two fixed directly). No residual leaked into this range.

*Register produced autonomously. Auto-fixes applied + committed this run; `08-decision-log.md` untouched; no
D-numbers assigned. JF1–JF4 are the maintainer's to resolve.*
