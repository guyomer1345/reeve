# 06 — Knowledge Structure (Space 6)

## Goal **[DECIDED]**
A per-project, LLM-optimized knowledge base the workflow inherently builds and reads — the thing that
lets it document-as-it-goes and stay autonomous. Two halves: a **code graph** + **per-file
experiential memory**.

## Lineage **[DECIDED — D1 research]**
- **Karpathy's LLM-Wiki** = the pattern → **ADOPT** (`index.md` + an append-only log,
  wikilinks/backlinks, ingest/query/lint). *Our schema carries the append-only log as the per-file
  `# Sessions` sections inside each node, not a separate `log.md` (D59).*
- **OKF (Open Knowledge Format)** = the formalized on-disk schema → **ADAPT** (directory of markdown,
  frontmatter with a required `type`, relative-link edges, reserved `index.md`/`log.md`).
- **llms.txt** = thin root manifest / agent entry point → small role.

## Schema **[DECIDED — format only; located by D62]**
`docs/knowledge/` committed with the repo; a thin `llms.txt` sits at `<project_root>/` and points in (D62):
```
<project_root>/
├── llms.txt              # agent entry point (H1 + summary + pointers)
└── docs/knowledge/
    ├── index.md          # catalog of all nodes
    ├── graph.json        # machine-readable typed edge list + per-node centrality (impact & orchestration)
    └── nodes/<repo-path>/<file>.md   # one node per source file
```
Per-file node:
- **frontmatter:** `type`, `path`, `purpose` (the file's job), `tags`, `last_reviewed`.
- **typed, directional edges:** `affects` / `affected_by`, each with a `why` (store `affects` as
  primary; derive `affected_by` as backlinks to avoid drift).
- **a `# Sessions` append-only log:** postmortems (`## [date] kind | title` + Symptom/Cause/Fix/Avoid)
  — the per-file debug memory.

## Purpose: code-derived vs spec-derived **[DECIDED]**
Store both: **intent** (from spec/roadmap) and **actual role** (from code). Divergence between them is
itself a signal (drift / scope creep / bug).

## Steal from prior art **[DECIDED]**
Aider repomap (tree-sitter + PageRank): auto-extract *structural* edges (imports/calls) mechanically,
so the LLM only authors the *semantic* `why` + impact judgment. (Code Property Graph validates typed
edges; nobody combines a typed impact-graph + per-file memory → open intersection.) We steal the
*approach*, not the *tool* — see the generator decision below (D68).

## Generated vs durable — the split **[DECIDED — D39, sharpens the above]**
The two halves sit on opposite sides of the design law (`shared/memory-model.md`, D38): the **structural
graph** (`graph.json`, imports/calls) is **generated** (mechanically, from imports/calls) — regenerable, never
authoritative prose, never hand-edited (a hand-maintained map goes stale and lies). The **experiential
memory** (per-file `why` + the `# Sessions` postmortems) is the **only durable hand-written layer** — the
non-derivable intent that earns its tokens. (Code Property Graph is overkill for context — security-scan
step only.)

## Generation, the two lenses & the node seed **[DECIDED — D68, pressure-tested on a real repo]**
- **Generator = an own script per stack, not an external tool.** `/start` emits a `.workflow/` code-map
  generator the same way it emits `checks.sh`: Python via stdlib `ast`, other stacks via a zero-dep
  regex-extraction + per-language resolver arm (tree-sitter reserved for parse-hard languages — D74). Regenerable,
  near-zero-dep, cheap to re-run. *External tools were tested and rejected:*
  `repomix` packs context (signatures + token counts), not a typed import graph; aider-repomap does the graph
  but is a heavyweight install to ship into every consuming project.
- **`graph.json` carries TWO centrality lenses, not one "importance" rank** — both fall out of the same
  import graph for free:
  - **impact** (forward PageRank — most-depended-upon): *"if this changes, what ripples?"* → `debug` /
    `planner` blast-radius.
  - **orchestration** (reverse PageRank / fan-out — composes many): *"where does behaviour live / where does
    feature X go?"*
  Neither is "importance." The run showed impact centrality surfaces the *data foundation* (models, config,
  base) and buries the *behavioural core*; orchestration surfaces the engine + ingestion + flow routes. The
  **product narrative itself** (what the app is *for*, what counts as core) is in neither lens — it is pure
  intent, carried only by the durable layer + the ingested `CLAUDE.md`/spec.
- **Three-tier node seed** (makes "eager graph, lazy semantics" safe — a lazy node is never an empty shell):
  - `[G]` **generated-structural** — path, type, edge targets, the two lenses. **All files, eager.**
  - `[X]` **generated-extractive** — a cheap LLM-summarised `purpose.actual` + tags, for a prioritised set.
    **The prioritised set = both lenses (impact ∪ orchestration) ∪ the spec's declared core flows — never
    impact alone**, else seeding documents the plumbing and skips the behavioural core (the miss the two lenses
    exist to prevent). Mechanism deferred to implementation.
  - `[D]` **durable** — the non-derivable `why` / intent-vs-actual / `# Sessions`. **Authored on touch** by
    `document`. This is the layer that earns its tokens — the product.

## Multi-language coverage **[DECIDED — D72, research-ranked by prevalence]**
Coverage is **three tiers**, not D70's arm-vs-fallback binary (whose fallback was never built — so *today* a
non-Python repo gets no graph at all, empty not degraded). What varies by language is only **edge resolution**;
the node set + directory clusters are identical everywhere and the two lenses inherit edge quality — so the cost
of a language is its **resolver**, not its parser.
- **Tier 0 — generic floor** (dir tree + shallow-regex imports, zero-dep): the long-tail safety net so an
  un-armed repo still gets nodes + clusters. The floor, not the strategy. **Node-recognition ≠ edge-extraction**
  (D75): the floor *nodes* any recognized source language (so an exotic-language repo still gets nodes+clusters —
  "never nothing"), and adds *edges* only for the subset with an import regex; resolution is family-scoped
  (intra-language, C/C++ share). Graphless data/markup/config/doc artifacts are excluded (no import graph).
- **The default precise arm = zero-dep** (D74): the floor's regex extraction + a real per-language **resolver**.
  The cost is the resolver, not the parser — Python (stdlib `ast`) and **JS/TS** (tsconfig/jsconfig `paths`+`baseUrl`
  aliases + TS extension/index/barrel resolution) are both this. A precise arm subclasses the floor, so no-config →
  it degrades exactly to the floor.
- **tree-sitter = reserved, not the mechanism** (D74 revises D72). Reach for it only where a language's *lexical
  structure* genuinely defeats regex extraction (e.g. C/C++ preprocessor/templates), shipped as a **graceful
  optional upgrade** (absent → the floor). Rejected as the default: the Python binding is version-fragile across
  environments, and for JS/TS the value was resolution, not parsing.
**Build set = prevalence, not ease** (Octoverse/SO/RedMonk 2024–25): Python (done) → JS/TS (one arm) → Java → C#
→ C++ — GitHub's "~80% of new repos = six languages" set — then Go / Rust / PHP. Because repos are polyglot
(median ~3 / mean ~4.5 languages), ~5 arms resolve most of *most* repos. Ease breaks ties on **order only**: Go is
pulled early (compiler-grade graph, near-free), C++ sequences last in-wave (needs `compile_commands.json`).
Graphless artifacts (SQL, HTML/CSS, shell, JSON/YAML, Markdown, Dockerfile, HCL) are **not** arms — no
file-to-file import graph. Arms are **not demand-gated** — validation is free (any public repo), so the common set
is built up front; the Phase-4 demo forces exercising ≥1 non-Python arm.
**Built (D73/D74/D77):** the shared engine + tier-0 floor + **five precise arms** ship as
`scripts/codemap/codemap.py` — one language-agnostic driver over pluggable arms (add a language = `extensions` +
`index()` + `edges()`, driver untouched). Precise arms, each **measured against ground truth** (D77 — `_resolve`
per specifier vs `package.json`/`go.mod`, not a proxy count), with a per-language **`fidelity` + `known_gaps`**
that is measured, not inferred from tier:
- **Python** (`ast`) — high; edges ARE imports. Re-confirmed on flask: **40/40 sampled edges real** (0
  fabricated). Gaps (both present on flask) = dynamic imports (8 files), `__init__` re-export aliasing (5 edges).
- **JS/TS** (`JsTsArm`) — tsconfig `paths`/`baseUrl`, extension/index/barrel, workspace packages (npm/pnpm/yarn) by
  exact name, and `package.json` exports/imports **subpath** maps (incl. **dist→src** derivation for unbuilt
  monorepos). On express/vue/vite/hono: **0 fabricated edges**, ~87–100% relative + ~95–100% workspace recall.
- **Go** (`GoArm`, package==dir) — go.mod module-prefix → target dir → every non-test `.go` file. **100% intra
  recall** (gin/cobra); replaced a **broken+unsound** floor (0% recall + fabricated stdlib edges).
- **Java** (`JavaArm`, two-pass) — top-level-type FQN index; resolves imports **+ same-package + inline-FQN** refs
  (the **measured 24%** of edges on gson that carry no import); soundness by repo-declared-only gating.
  Same-package channel precision **≈100%** measured on commons-lang (976 same-pkg edges) + okhttp — Java's
  camelCase members make a type/member name collision rare, so the theoretical over-edge doesn't materialize.
- **C#** (`CSharpArm`, namespace-aware two-pass) — namespace stack (file-/block-scoped, nested), `using`→**used-name
  intersection** (never the whole namespace), same-namespace, inline FQN, `using static`; partial types → all files.
  newtonsoft **107 → 3731 edges** (3.9/node). Intersection precision measured on AutoMapper (fluent-DSL worst case)
  + eShopOnWeb (app code): a **head-token filter** (a member-access token `x.Order` / `.Include<>()` /
  `MemberList.Source` is NOT a type reference) lifts precision **97.2 → 98.9%** with **no recall loss**; the ~1%
  residual = a property/enum-member *declared* with a same-namespace type's name (`public string Source`) — beyond a
  regex arm, so C# stays **`medium`**.
Every other recognized source language falls to the floor — noded regardless (D75), with edges where a regex exists.
**Bias precision, standing rule for the static arms:** a fabricated edge is sticky (the observed layer, D78, can only
ADD missed edges, never retract a false one — "not exercised" ≠ "not a dependency"), while a missed edge self-heals
through runtime capture. So when a channel measures noisy, tighten toward precision and accept the recall loss (the
C# head-token filter is the worked example).
**Deferred arms (defer rationale):** **C++**, **Rust** (`mod`), and **PHP** (`require`) stay on the **tier-0 floor**
— its relative/sibling resolution is the sound subset for each, and a precise arm is built **on demand by prevalence**
when a real repo needs one, not up front (C++ additionally needs `compile_commands.json`). tree-sitter stays reserved
for parse-hard languages.

## The graph is a LIVING artifact — a durable observed layer **[DESIGNED + VERIFIED — D78; impl Phase-2/3]**
Static arms are precision-first but recall-imperfect (dynamic imports, DI, reflection, C# source-gen, dynamic
dispatch are structurally invisible to *any* static analysis). D78 makes the loop's **own activity** close that
recall gap so the graph improves as the project runs, rather than staying at its static ceiling.
- **Two DISTINCT graphs** (merging corrupts both): a **dependency graph** ("A needs B") = static + observed-runtime
  + observed-debug, precision-first; and a **temporal-coupling graph** ("A changes with B") = co-edit affinity.
- **Load-bearing insight — activity buys RECALL not precision:** runtime/debug *add* a missed edge; nothing cheaply
  *retracts* a false one ("not exercised" ≠ "not a dependency"). So arms stay precision-first (validates D77's
  soundness discipline) and the loop accretes the missing recall.
- **Two-layer storage:** `graph.json` (static, regenerated freely by arms) + `graph.observed.json` (the durable
  `[D]` layer, accreted, stable-node-ID-keyed); regenerate = re-run arms **+ merge** the observed layer whose
  endpoints survive. Every edge carries **`provenance`** (`static-arm`|`observed-runtime`|`observed-debug`) +
  confidence — subsumes the D77 fidelity signal. This resolves the regenerate-vs-incremental question (below).
- **Capture home = `verify` as a pure observer** (it already executes the affected flow; write lives in a
  `document`/`commit` post-step, keeping verify artifact-only per D76); `debug` is the premium causal supplement.
  Emergent: the graph is most accurate exactly where the project is most active.
- **Mechanism (measured):** `sys.monitoring` fire-once+`DISABLE` (Py 3.12+) = **1.0×**; naive hook = 14× (rejected);
  coverage-artifact harvest (~1.5×) is the universal fallback. Trigger **selectively** where an arm's `known_gaps`
  flag dynamism. Verified on a Python fixture (catches a dynamic-dispatch edge static can't, soundly) + requests
  (clean code → 0 new: benefit is conditional on dynamism).

## Granularity **[DECIDED]**
Start file-level; leave a seam for symbol/function-level later.

## Maintenance / freshness **[DECIDED — D61 closed the mechanisms]**
The structural graph regenerates (it cannot drift); `document` keeps durable docs + the inline-C4 architecture
doc fresh in the **same item as the code**; an `audit` pass keeps guidance high-signal. **Retention (D61):**
each node's `# Sessions` is **cap-and-archived** — last-*K* raw entries on disk, older entries dropped to git
with a one-line archive pointer; a deterministic script does this, so the entry format is **strict/lint-parseable**
(`## [date] kind | title`) to split entries mechanically. A `Lessons` zone (distilled patterns) is left as a
**deferred** signal-quality feature. **Staleness** = a diff-based signal (code changed without its node) that
schedules a doc-fix, not a prune. **Regenerate-vs-incremental is resolved (D78):** the static layer regenerates
(cannot drift), the durable *observed* layer accretes and is **merged** on regenerate (endpoints that survive);
open D78 follow-ons = node-ID stability across renames + observed-edge staleness/decay.
