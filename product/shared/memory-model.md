# Memory Model — what the loop may rewrite, change, or never touch

The design law for every durable file the workflow reads or writes. A file earns its place only if it
holds **non-derivable intent** or is the loop's **cross-session memory**; everything else is **generated on
demand** or **enforced by CI** — prose rots silently, code and checks fail loudly.

## Three tiers — encoded by location + filename so a skill knows its rights
| Tier | Rule | Examples |
|---|---|---|
| **VOLATILE** | rewrite freely each iteration | `.workflow/state.json`, `handoff.md` |
| **STABLE** | change **only in the same item as the code that changes it**, CI-gated | `docs/spec/`, `docs/architecture.md` |
| **APPEND-ONLY** | **supersede, never edit** | `docs/decisions/`, the per-file `# Sessions` sections |

## Consequences (binding on all skills)
- `execute` / `refine` touch STABLE files only as part of the item that changes the code.
- `document` owns STABLE doc + diagram freshness (same-item) and the APPEND-ONLY `# Sessions` log.
- A `decision-record` is never edited — a reversal is a **new** record that supersedes (status flip).
- Structural code maps are **generated, never hand-written** — not a tier, an output.
- Enforceable rules live in lint/test/CI/hooks, not prose; prose shrinks to non-derivable intent.
- **Always-read files are bounded by construction:** `CLAUDE.md`, `state.json`, `handoff.md`, `loop.md`
  hold current state only — rewritten in place, never grown — so the loop can't inflate its own context cost.
  History lives in git. The **retention & archival law** for the append-only tier is the read-law companion
  (below): **cap-and-archive** — last-*K* on disk, the rest in git.
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
or the architecture doc — that schedules a doc-fix, not a prune. *Open:* `K`/thresholds; Sessions
**distillation** (postmortems → lessons) is deferred.
