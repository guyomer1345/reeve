# Pre-Phase-3 Doc-Review Register (coherence cold-audit)

**The D89-style phase-boundary `align` cold-audit — the closing coherence gate before Phase 3.**
COHERENCE, not substance: does the whole surface agree with itself and with the built artifacts (the input
Phase 3 builds from)? Where a doc↔artifact drift was a *mechanical* D80 repair (stale ref / wrong list /
missing decided key / doc contradicting an already-decided fact) it was **auto-fixed** in this commit; where it
needs **judgment** (a design call, an ambiguous ownership, a substance gap) it is **logged below**, not resolved.

- **Base commit:** `6badf8c` (pressure-test register F1–F14). Branch `main`.
- **Method:** four meta-gates run green → a 6-way read-only finder fan-out (schemas · counts/enums · shipped-ref
  discipline · D90–D107 blast-radius · checkpoints/demo/intake · orchestrator/console/agents) → every finding
  re-verified against the actual artifact before acting. No `08-decision-log.md` edits; no D-numbers assigned.
- **Companion:** `reviews/pre-phase3/pressure-test-register.md` (Chat 1 substance pass, F1–F14) — cross-checked
  below.

---

## Verdict

**The surface IS Phase-3-ready.** The Phase-2 reversals (checkpoints→outbox, map-as-tab, no-SSE,
outward-action-is-not-a-checkpoint, park-and-yield) propagated cleanly; counts/enums/roster are single-source and
gate-green; the shipped package is free of spec-internal reference leaks. The drift that existed was a cluster of
**doc↔artifact mismatches the mechanical gates can't see** (a stale code-map arm list, a gitignore contradiction,
a schema missing a decided key, pre-D90/pre-D105 phrasings) — all auto-fixed. The remaining items below are
**judgment calls or known substance gaps**, none of which blocks starting Phase 3; several (JF1, JF5) should be
pinned early in the C1→C2 build.

---

## Auto-fixed in this commit (pure-coherence — no design call)

| # | File(s) | The drift | Fix |
|---|---|---|---|
| A1 | `commands/start.md` (code-map §§4, Expand-later) | Doc says only **Python + JS/TS** have precise arms and frames Go/Java/C# as future — but `scripts/codemap/codemap.py` **ships 5 precise arms** (Python, JS/TS, Go, Java, C#) with passing tests. Doc↔artifact drift the enum gate confirms only for `11`. | Listed all 5 shipped precise arms; C++ (compile-DB) + Rust/PHP as the remaining floor-only languages. |
| A2 | `commands/start.md` (step 2) | "Add `.workflow/state.json` to `.gitignore`; **everything else is committed**" — would commit the runtime dirs (`bus.json`,`outbox/`,`parked/`,`inbox/`,`demos/`, worktrees) the same file + `05` mark gitignored. Internal contradiction. | Gitignore the full runtime set; enumerate the committed durable set. |
| A3 | `shared/schemas.md` (`config.json`) | `config.demo.max_refine_rounds` is a decided knob **read by the shipped `create-demo` skill** + referenced 5× in docs, but `demo` was absent from the config schema (the D80 owner). | Added the `demo` bullet (`max_refine_rounds`, default 3). |
| A4 | `05-shared-state.md` (commit policy) | The runtime-gitignored enumeration omitted `outbox/` and `demos/`, though the layout tree just above marks both gitignored RUNTIME. | Added `outbox/` + `demos/`. |
| A5 | `05-shared-state.md` (layout tree) | The canonical layout omitted `checks.sh`, `codemap.sh` (both scaffolded by `start.md`) and `align/` (mkdir'd by `align`). | Added all three to the tree. |
| A6 | `shared/schemas.md` (`parked-ticket`) | `worktree`/`branch` were listed unqualified (= required), but a pre-build (intake-stage) `demo`/`reconcile` park has neither (D104). | Marked `worktree?`/`branch?` optional + noted the pre-build case. |
| A7 | `skills/create-demo/SKILL.md` (Route + Calls) | The escalate-to-`discuss` edge on refine-cap-exhaustion is in the skill's own Workflow step 4 (+ decided) but was **absent from its Route + Calls** — the routing graph under-represented its own body. (`discuss` is a valid node → contract linter stays green.) | Added the `→ discuss` edge to Route + Calls. |
| A8 | `01-orchestrator.md` (Invariants split) | Listed the outward-action gate as "settings `ask` rule" under *enforced* — D105 demoted the harness `ask` to a backstop under the `config.outward`/outbox model over the `guard.sh` floor. | Reworded to the D105 model. |
| A9 | `01-orchestrator.md` (driver summary) | "Checkpoints (block on the bus)" — pre-D90 live-wait shorthand. | "durable park on the bus — D90". |
| A10 | `04-checkpoints.md` (MVP-scope flow) | Top-of-doc flow read "hits a checkpoint → **blocks (waits on the bus)**" — the live-wait model D90 overturned to park-and-yield-then-interleave. | Reworded to park/yield/interleave + resume via `claude --resume`. |
| A11 | `04-checkpoints.md` (motivating example) | The Polar example names screenshot/screen-share/live-feedback with no marker, though the Help set below **Defers** exactly those. Misread risk. | Tagged it as the aspiration; MVP ships the deep-link + breadcrumb step-list. |
| A12 | `02-agents.md` (banner + 3 section tags) | Asserted the collision-independence test is "still open" (D91 **closed** it) and tagged roster sketch sections `[OPEN]` (closed by `10`). Stale derived-status (the D80 owner-drift pattern). | Banner → DECIDED (D91); tags → SUPERSEDED/CLOSED→`10`, DECIDED→D91. |
| A13 | `scripts/check-no-spec-refs.sh` | The leak pattern `\bD[0-9]{1,2}\b` catches only D0–D99, but the log is at **D107** — a future leaked `D105` would pass the gate silently. | Broadened to `{1,3}` (verified: catches `D105`/`D9`, still skips the `D-001` record id and `3D`). |

All four meta-gates green after these edits (`check-status-coherence` · `check_enum_coherence` · `check_contracts`
· `check-no-spec-refs`); gate test suites green (12+12).

---

## Judgment findings (NOT auto-fixed — the maintainer's call)

### JF1 — The inbox-drain / scheduler-boundary step is absent from the shipped driver artifacts *(MEDIUM)*
- **Area:** `templates/orchestrator-CLAUDE.md` (read→place→advance) + `templates/loop.md` (routing table) vs D91/D93/D26 + `shared/schemas.md` (inbox-message: "dispatched at a scheduler boundary by kind").
- **Incoherence:** the boundary drain (resume-parked-first +aging → start-new → sleep; verdict→`--resume`, intake→promote, control→apply, release→fire outbox) is fully decided and schema-specified, but neither driver template contains it — an orchestrator following its brief literally would park at a checkpoint and never consume the verdict that unparks it. `01`'s own control-algorithm paragraph (`:86-88`) mirrors the template and likewise omits it.
- **Why not mechanical:** the bus/outbox **build rides Phase 3** (the templates correctly reflect the pre-bus MVP), so this is not *current* drift — but there is **no discoverable marker** that the drain must be wired when the bus lands (unlike `start.md:110`'s explicit `⛔ STUB` for the console). Wiring it now needs a **cadence-per-kind design confirmation**; that's a design step, not a repair.
- **Options:** (a) wire the drain step into `orchestrator-CLAUDE.md` + `loop.md` + `01`:86-88 now (design confirmation required); (b) drop a `⛔ STUB — inbox-drain/interleaving wiring, Phase 3` marker mirroring `start.md:110` (minimal); (c) accept as tracked in `11` and revisit at C2. **Recommend (b) now, (a) at C2.**

### JF2 — The gitignored secret store has no path, D80 owner, or gitignore entry *(MEDIUM · = pressure-test F9)*
- **Area:** referenced 4× (`04:70`, `shared/schemas.md:128,144`, `skills/checkpoint/SKILL.md:41`) and located 0× — absent from the `05` layout, the `start.md` gitignore scaffold, and the D93 native-FS pin set; no owner declared.
- **Why not mechanical:** picking the path (e.g. `.workflow/secrets/`) + owner + 0600/ACL creation is a **design call** (a load-bearing runtime artifact holding live credentials). This is the D80 adoption gap the pressure-test's F9 already names.
- **Options:** adopt under D80 — fixed path on the native-FS pin, owner = orchestrator writes / audit-prune deletes, add to the gitignore scaffold + `05` layout + a schema entry (reuse the D95 token-file discipline).

### JF3 — `outbox/` (and `demos/`) are absent from the served-read list and the native-FS pin list *(LOW–MEDIUM · = pressure-test F14 completeness)*
- **Area:** `05:20-22` serves reads from `state.json/backlog.md/parked/graph.json` (no `outbox/`), yet `05:136` says "the console renders the pending `outbox/`"; `05:104-105` pins the atomicity-sensitive subtree as `state.json/bus.json/parked/inbox/` — omitting `outbox/`, though `shared/schemas.md:157` marks it atomic-write single-writer RUNTIME.
- **Why not mechanical:** it extends a **D93 enumeration that predates the D105 `outbox/`** — an adoption/ownership call (add `outbox/`+`demos/` explicitly, *or* adopt a general "all atomicity-sensitive runtime dirs are native-FS-pinned / all `.workflow` files are served from disk" rule so new dirs inherit).

### JF4 — Checkpoint deadline default + reminder cadence are unpinned *(MEDIUM · = pressure-test completeness)*
- **Area:** `shared/schemas.md` `parked-ticket.deadline` has no default; D97 names aging/reminders but no interval; no `config.checkpoint.*` key exists.
- **Why not mechanical:** choosing the shipped-default deadline + reminder cadence is a **design call**. (Note: the away-*delivery* of that reminder is pressure-test F4 substance.)
- **Options:** add `config.checkpoint.deadline_*` + a cadence to the shipped-default pattern (and to the `config.json` schema).

### JF5 — `09:170` describes the commitment-status resolver as a keyed `purpose.intent` lookup *(LOW · = pressure-test completeness)*
- **Area:** `09-intake.md:170` "resolves the changed code node → its spec element (via the node's `purpose.intent`)" reads as a structured foreign key; the actual `align` resolver is **LLM judgment** over the eager `[G]` graph + decision records + the STABLE spec.
- **Why not mechanical:** tightening the wording risks mischaracterizing a **mechanism that isn't built yet**; and a node *does* carry an extracted purpose, so the phrase isn't strictly wrong. A precision call for the maintainer.

### JF6 — D35 and D60 lack forward-pointers to D105 *(LOW · blocked by the autonomy contract, not by ambiguity)*
- **Area:** `08:275` (D35 "*Mechanics OPEN → `07`*") and `08:577-588` (D60 "disposition deferred") — neither back-annotates D105, which states it closes D35's mechanics + retires D60's `checkpoints/`. The repo has an established forward-pointer convention (D54/D70/D72/D73).
- **Why not auto-fixed:** the autonomy contract forbids editing `08-decision-log.md`. **Recommend the maintainer add the one-line pointers** to match convention.

### JF7 — `11-roadmap.md` reuses C1/C2/C3 for two different things *(LOW)*
- **Area:** Phase-3 *build* items (`11:61-72` — "C1 read-only console / C2 comms bus / C-map") vs Phase-2 *cluster-C checkpoint* sub-items (`11:229-233` — "C1 data model / C2 triggers / C3 help set"); `11:251` "(C1 console → C2 bus)" leans on the build sense. A pre-existing label collision (not introduced by D90–D107) that can misread.
- **Why not mechanical:** relabeling (e.g. `P3-a`/`P3-b` for the build items) is an editorial choice the maintainer owns.

### JF8 — `check-no-spec-refs.sh` doesn't catch prose doc-slug references *(LOW · gate-hardening)*
- **Area:** the gate catches backtick bare numbers (`` `05` ``) but a prose `see 08-decision-log.md` / `07-open-questions` would pass. Clean today; the most natural way a leak would actually be written.
- **Why not auto-fixed:** adding a doc-slug alternation is a **pattern-breadth judgment** (false-positive risk). (The unambiguous half — the D100+ blind spot — WAS fixed, A13.) Recommend adding a slug alternation.

### JF9 — Intake→backlog promotion doesn't stamp the source bus ticket *(LOW · = pressure-test completeness)*
- **Area:** `shared/schemas.md` `inbox.intake = {ticket, ask, node_ids?}`; when promoted to a backlog `issue`, the item's `source` doesn't carry the bus ticket, so the "my requests" surface can't correlate an intake to its promoted item (verdict + release ARE legible via token/action-id).
- **Why not mechanical:** adding a correlation stamp is a small **mechanism/schema call** (where the source ticket rides on promotion).

---

## Cross-check of the pressure-test register (Chat 1, F1–F14) — mission item 7

Chat 1's substance/coherence split holds. **All of F1–F14 are correctly classified substance/scoping** — none is a
coherence issue misfiled as substance. Notes:

- **F1** (inbox consume/idempotency), **F2** (single-writer election), **F3** (config.outward inert + guard.sh
  push-floor), **F4** (away-alert path), **F5** (interleaving file-disjoint under divergence), **F6** (tunnel
  trust), **F7** (demo refine-counter durable home), **F8** (≤3 cap counts parks), **F10** (bus daemon
  provenance/keying), **F11** (daemon idle-shutdown vs parked), **F13** (issue-create non-idempotent), **F14**
  (MVP away-autonomy scoping) — **substance/scoping, confirmed.** Not touched (they need decisions).
- **F3 coherence cousin** — the `01:89-90` "settings `ask` rule" framing was a *coherence* sub-issue → **auto-fixed
  (A8)**. The core F3 (config.outward inert vs the static `settings.json ask` + the empty guard.sh push-floor)
  stays substance.
- **F9 coherence cousin** — the secret store's **D80-owner/location** gap is logged as **JF2**; the core (its
  disposition) is substance.
- **F12 (CSP over-claims egress) — the coherence half is a NON-ISSUE in the docs.** `09` / `create-demo` / `05`
  already attribute "no external hosts / no eval" to **format discipline** and scope the `sandbox` CSP to
  origin-isolation only — they do **not** over-claim CSP egress-enforcement. The single residual imprecision lives
  in **D102's rationale prose in `08`** ("the two invariants a CSP actually enforces"), which is **out of this
  pass's edit scope** (no `08` edits). Flagged for the maintainer's `08` housekeeping, not a doc fix.
- **The "hand to the doc-review" completeness list** (register §"Lower-severity") was actioned: config.demo schema
  → **A3**; parked-ticket requiredness → **A6**; create-demo escalate-to-`discuss` edge → **A7** — all fixed.
  inbox-drain → **JF1**; deadline default → **JF4**; enumeration completeness → **JF3**; D106 wording → **JF5**;
  my-requests correlation → **JF9** — all logged. The `checks.sh` per-stack generator remains a tracked **build**
  task (`11`/`07`), not a doc fix.

*Register produced autonomously. Auto-fixes applied + committed this run; `08-decision-log.md` untouched; no
D-numbers assigned. The JF items are the maintainer's to resolve.*
