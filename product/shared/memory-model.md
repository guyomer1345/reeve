# Memory Model — what the loop may rewrite, change, or never touch

The design law for every durable file the workflow reads or writes. A file earns its place only if it
holds **non-derivable intent** or is the loop's **cross-session memory**; everything else is **generated on
demand** or **enforced by CI** — prose rots silently, code and checks fail loudly.

## Three tiers — encoded by location + filename so a skill knows its rights
| Tier | Rule | Examples |
|---|---|---|
| **VOLATILE** | rewrite freely each iteration | `.workflow/state.json`, `handoff.md` |
| **STABLE** | change **only in the same item as the code that changes it**, CI-gated | `docs/spec.md`, `docs/architecture.md` |
| **APPEND-ONLY** | **supersede, never edit** | `docs/decisions/`, the per-file `# Sessions` sections |

## Consequences (binding on all skills)
- `execute` / `refine` touch STABLE files only as part of the item that changes the code.
- `document` owns STABLE doc + diagram freshness (same-item) and the APPEND-ONLY `# Sessions` log.
- A `decision-record` is never edited — a reversal is a **new** record that supersedes (status flip).
- Structural code maps are **generated, never hand-written** — not a tier, an output.
- Enforceable rules live in lint/test/CI/hooks, not prose; prose shrinks to non-derivable intent.
- **Always-read files are bounded by construction, and now by a CHECK:** `CLAUDE.md`, `state.json`,
  `handoff.md`, `loop.md` hold current state only — rewritten in place, never grown — so the loop can't inflate
  its own context cost. History lives in git. "By construction" was for a long time an *assertion with no
  mechanism*, which is how a file can grow past the point of being readable while the doc claiming it cannot
  sits right next to it; the **context-budget law** below is the enforcement. The **retention & archival law**
  for the append-only tier is the read-law companion (below): **cap-and-archive** — last-*K* on disk, the rest
  in git.
- **Don't duplicate state an external system owns:** e.g. GitHub issue open/closed — the backlog holds
  only the `github_ref` pointer; mirroring the state locally creates drift + post-commit bookkeeping.
- **`backlog.md` is a live open queue, not append-only:** rewritten in place; closed items **leave**
  (`prioritize` GCs at pick time — roadmap items `commit` flipped done, `issue` entries whose `github_ref` is
  closed). Bounded by open-WIP, not age — so it sits outside the append-only retention set.

## The read-law companion
The write law above says *who may edit*; the **retention/read law** says *how much loads*. The append-only
tier is bounded by **cap-and-archive** — last-*K* entries on disk, older entries dropped to git (the working
tree is a bounded **cache**, git the **ledger**). A deterministic **retention script** (`scripts/retention.py`,
shipped → `.claude/scripts/`, stdlib Python, idempotent) runs in an **`audit` maintenance item** that
`prioritize` injects on a count/size threshold: it caps each node's `# Sessions` to `config.retention.sessions_k`
(older → git, a one-line head marker `<!-- retention: N Sessions entries archived -> git @ <sha> -->`), GCs
superseded `decisions/` bodies to git + tombstones `decisions/index.md`, and prunes a closed `items/<id>/`
**only** once `document` has folded its essence and written a `promoted.json` marker (no marker → never pruned,
so the mechanical pass can't delete un-promoted memory). The `git log` cold-start read is bounded by
`handoff.base_sha`. Only the prose deletion-test over `CLAUDE.md`+`rules/` needs the LLM (mechanical → enforced).
**Staleness** (a doc that's *wrong*, not *big*) is a separate diff-based signal — code changed without its node
or the architecture doc — that schedules a doc-fix, not a prune. *Open:* `K`/thresholds.

**Sessions distillation is no longer deferred.** Compression beats raw retention: a dropped entry that was first
distilled to its lesson leaves something behind, and a dropped raw entry leaves nothing. So the `audit` item
**distills before `retention.py` caps** — each entry about to fall past *K* is reduced to a one-line lesson
appended to the node's **`# Lessons`** section, which is append-only and *not* capped (a lesson is already the
compressed form; re-compressing it would be the loss distillation exists to prevent). The raw entry then drops to
git as before. Two things are load-bearing and both are easy to get wrong:
- **Order:** the script is deterministic and cannot distil, so the model's pass runs **first**. Distilling after
  the cap means distilling from git.
- **Placement:** `# Lessons` is a **top-level** section and sits **before** `# Sessions`, never inside it.
  `# Sessions` is the terminal section and its region runs to EOF once entries begin, so a `## Lessons` nested
  under it would be parsed as a *session entry* and could be dropped by the very cap it was written to survive.

## The distillation law
Every summarising step in this package — the `audit` item's `# Lessons` pass above, `/dispatch`'s `handoff.md`,
the thread rotation in `answer` — replaces a long record with a short one. The hazard is not size, it is
**authority**: a distillation inherits the standing of the record it replaces while **shedding the doubt attached
to the individual claims inside it**. Measured, not theorised — a thread handoff restated a *fabricated* answer as
sourced fact, dropped the caveat two earlier turns had raised against it, and contradicted itself three paragraphs
later; the turns holding the evidence had just been cleared by the same rotation.

**A distillation may DROP, POINT and QUOTE. It may never RESTATE.**
- **Drop** whatever is re-derivable from a record that still exists. Re-derivation is cheap and honest; a summary
  of it is neither — and a claim that is *not* re-derivable from the record is precisely an invented one.
- **Point** at an owner — a file, an id, a section, a sha — and at most what it *says*, in a form one read settles.
  Two pointers that contradict each other are a legitimate carry; your conclusion about which is right is not.
- **Quote** the human verbatim. Their own words are the one thing no other record holds.
- **Never restate** a conclusion in your own voice. That is the move that turns a claim into a fact, and it is the
  only one of the four that can launder an invention into durable memory.

**Its force is graded by what happens to the source.** Where the source survives the distillation — `# Lessons`
drops its raw entry to *git*, `handoff.md` sits on an intact git/backlog/`parked/` and **mirrors** the
machine-owned parts rather than restating them — the law is guidance and a bad distillation is recoverable. Where
the source is **destroyed** it is binding and structural: the conversation thread is RUNTIME and gitignored, so
rotation is the one place in this package where the distillation becomes the *only* surviving copy.
`shared/schemas.md § conversation-thread` states what that handoff may carry, and that list is a floor, not an
example.

## The context-budget law
The retention law above bounds the **append-only** tier. Everything else a session reads — the brief, the
routing graph, the spec, a rule, a knowledge node — was bounded only by the claim above. **`check_doc_budget.py`**
(shipped → `.claude/scripts/`, stdlib, read-only) is the mechanism: it sizes every workflow-owned doc against
its **role's** budget, **in tokens** (model-window-agnostic, like `context.warn_pct`), **two tiers per role**.
- **HARD** fails `checks.sh` on every commit — it is cheap, decidable and always-whole, because it reads sizes
  and not content. For the on-demand set the hard number is not a preference: it is the **Read tool's
  25 000-token ceiling**, past which a file cannot be loaded in one call at all. That is enforcement that is a
  *failure*, not advice.
- **ADVISORY** never fails a build; `prioritize` injects a `doc-budget` maintenance item. Both tiers exist
  because an aggressive-only budget is red on a clean install, and a gate that fires on a fresh bootstrap is one
  a human learns to skip — so the aspiration is tracked as work instead of as a broken build.
- **Over budget is a TICKET, never an auto-edit.** You cannot drop half a spec doc to git the way retention drops
  a Sessions entry; splitting prose coherently is judgment. The remedy is a **split-and-pointer**: a lean
  survivor, a detail file, and a head marker in the survivor. Trim and split; never delete content that carries
  non-derivable intent. **Two marker forms**, because the detail can be dead or alive:
  - `<!-- doc-budget: detail split -> <path> @ <sha> -->` — **archived**: the detail is frozen and recoverable
    from git, mirroring retention's own Sessions marker. Its target is *expected* to be absent from disk.
  - `<!-- doc-budget: detail split -> <path> -->` — **live sibling**: the detail is a real file still being
    edited. It carries no sha, because a sha on a live file is stale at the next edit and sends a reader to git
    for something sitting next to them. (`shared/schemas.md` → `shared/schemas-runtime.md` is the shipped case.)
- **A split doc is still ONE doc to anything that parses it.** A reference of the form `<doc> § <section>`
  resolves across both halves — the section name is the anchor. Any *machine* consumer must read through
  `check_doc_budget.read_with_splits`, which follows the marker, recursively and cycle-guarded; `check_contracts.py`
  and the meta-repo's `check_enum_coherence.py` both do. Parsing the survivor alone reads strictly less than the
  schema declares, and the two shipped readers were measured breaking in *opposite* directions on the real split
  (one hard-failed with five false errors, the other turned two legitimate enum values into "novel" advisories).
  **The sizer deliberately does not follow the pointer** — the survivor is under the wall precisely because the
  detail moved out — but the detail file *is* budgeted, as its own row and always as **on-demand**, so the remedy
  cannot produce a file this gate stopped watching.
- **It does not re-check truth.** `align` owns "is this doc *wrong*"; this owns "is this doc *too big*". Two
  owners, no overlap. `config.doc_budget` (`shared/schemas.md`) owns the numbers, decoupled from `retention` and
  `align` because doc size is neither memory pressure nor drift risk.
- The **VOLATILE tier is out of scope on purpose**: `handoff.md` is already capped mechanically at injection
  time by the `SessionStart` hook, and one bound with two owners is a bound that drifts.
