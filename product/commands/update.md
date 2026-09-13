---
description: Update an already-initialised project onto the currently-installed workflow package — refresh the package-owned files, regenerate the code-map, and never touch what the project owns. The sibling of /start, for a project that has already been started.
argument-hint: "(no arguments)"
---

# /update — migrate this project onto the installed package version

`/start` initialises a project **once**. When the plugin is later updated, the project's copy of
the package — the scripts and hooks under `.claude/`, the copied `loop.md` / `checks.sh` /
`settings.json`, the orchestrator brief — is still the **old** one. `/update` is what moves it
forward. Re-running `/start` cannot do this: it reports "already initialised" by design, and a
hand-copy risks the project's own work.

**The one rule.** The project's build state is sacred. Parked checkpoints, decision records,
the spec, adopted docs, `[D]` durable bodies, human-set config knobs, the backlog, the handoff —
none of it is yours to rewrite. You refresh **the package**, regenerate **what is derived from
code**, and leave everything else exactly as it is.

**`/update` is interactive-only**, for the same reason `/start` is: it writes into `.claude/`,
which Claude Code guards **above** the settings allowlist, so a non-interactive session has no
grant path and would silently skip those writes.

## The ownership taxonomy this implements

Four rows, and the count is not the point — *who authors the file after it lands* is. Everything below
follows from that one question.

| | What | What happens |
|---|---|---|
| **(a) package-owned** | manifest `install[]` scripts + hooks; the copied `loop.md`, `checks.sh`, `settings.json`; the orchestrator brief's **managed block** | **refreshed** from the new package |
| **(b) target-owned** | `[D]` bodies (`# Sessions` / `Purpose` / edge-`why`), adopted docs, the spec, decision records, human-set `config.json` knobs, `checks.env`, `codemap.sh`, and all live loop state (`backlog` · `handoff` · `state` · `items` · `parked` · `outbox` · `inbox` · `secrets`) | **never touched** |
| **(b′) seeded-then-owned** | `.workflow/directives.md` — the package ships its starting content, the **operator** grows it | **created if absent, never refreshed** |
| **(c) regenerate-from-code** | `docs/knowledge/graph.json` + the `[G]` node frontmatter | **regenerated** by `codemap.sh`; `[D]` bodies preserved and re-attached |

## 0. Refuse the wrong situations
- **No `.workflow/`** → this project was never started. Say so and stop: the command is `/start`.
- **Bootstrap still in flight** (`.workflow/handoff.md`'s `bootstrap:` is `installed` / `ingesting` /
  `discussing` / `reconcile-parked`) → do **not** update mid-bootstrap. Report the state and stop;
  finish the bootstrap (or resolve the parked reconcile) first, then update.
- **An item is mid-build** (`state.json` `status: building` with a `current_item`) → say so and ask
  before proceeding. Refreshing the package under a half-built item is safe for the *files*, but the
  running session is holding stale instructions in context; the clean moment is at an item boundary.
- **Uncommitted changes in the working tree** → show `git status --short` and ask whether to proceed.
  An update is much easier to reason about (and to revert) from a clean tree.

**And one situation to WARN about and then proceed anyway** — the project's runtime half is not bound to this
machine:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rebind.py" check --project-root "${CLAUDE_PROJECT_DIR}"
```
Anything other than `HEALTHY` → say so plainly, name `/rebind`, and **continue the update**. Do not block. Two
reasons, and they are not stylistic. `/update` is **repo-side only** — `update_reconcile.py` reads the manifest,
the project's files and `install-set.json`, and never touches a runtime path, so it does not depend on the
binding at all. And blocking would **deadlock**: `rebind.py` ships *inside* the package `/update` installs, so a
project stranded on a version that predates `/rebind` could never reach the fix. The one thing to defer is §5.2
(restarting the daemon) — an unbound project has no runtime root for the daemon to start against; tell the human
to run `/rebind` and then start the console.

## 1. Plan — read-only, and show the human
Run the **new package's** reconcile runner. This is the one deliberate exception to `/start`'s
never-invoke-in-place rule: an update must be driven by the version being installed, because that
is the version that knows how to reach itself. It holds no state, so reading it in place is safe.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update_reconcile.py" plan \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" --project-root "${CLAUDE_PROJECT_DIR}"
```

It prints one line per package-owned path. Read them as:
- `ADD` / `REFRESH` — routine; the package changed.
- `SAME` — nothing to do.
- `REFRESH?` — **no install ledger**, so this file's provenance cannot be proven. That is the
  signature of an install made before ledgers existed (an absent `workflow_version` says the same
  thing). Everything is still refreshed; the difference is that nothing can be *removed* and the
  human-facing files need explicit confirmation.
- `LOCAL-EDIT` — the file differs from what the package wrote: **a human edited it**, and a refresh
  discards that edit. Surface each one.
- `ORPHAN` — recorded by a previous install, no longer shipped, still byte-identical to what we
  wrote ⇒ **provably ours** ⇒ removed. `ORPHAN-EDITED` is flagged and never removed.
- `BRIEF-UNMARKED` — the root `CLAUDE.md` has no managed block, so the orchestrator brief is left
  alone (see §4).
- `SEED` / `SEEDED` — a **seed** (`update_reconcile.py`'s `SEEDS`): `SEED` means it is absent and will be
  created from the package for the first time; `SEEDED` means it is already there and is **left alone**. There
  is deliberately no third state. A seed is package-*supplied* but project-*owned*, so it is never hashed into
  the ledger: an operator's edits to `.workflow/directives.md` must never read as a `LOCAL-EDIT` to confirm
  away, and a package that later stopped shipping the seed must never see their file as a removable `ORPHAN`.
  If you find yourself wanting to refresh one, the answer is no — the refresh would delete the standing
  directives the channel exists to keep alive across a `/clear`.
- `STAMP old -> new` — the version transition. `old == new` is a **no-op update**: report the
  summary and stop unless the human explicitly wants a re-sync.
  **What these values are:** the package ships **no** `version` field, so Claude Code keys
  the install on the **commit SHA** and that SHA is the stamp. The old caveat here — *"a dev install
  can move without the version moving"* — is therefore **gone**: content that moved gets a new SHA,
  so `old == new` now means the content genuinely did not move. `unknown` is the one exception and is
  never treated as a no-op, because failing to resolve a version is not the same as not moving.
  This equality test is the **only** thing the version is used for, besides display and the
  absent-check — nothing anywhere orders it, which is exactly why a SHA is allowed to be the key
  (every migration decision is content-hash driven through `install-set.json`).

**Show the human the plan before applying anything.** For every `LOCAL-EDIT` and `REFRESH?` on
`.claude/settings.json` or the brief, show the actual diff (`diff -u` the on-disk file against
`${CLAUDE_PLUGIN_ROOT}/templates/…`) and say plainly what will be lost. The runner **blocks** the
apply on those files until `--confirm-overwrite` is passed — so this is a real gate, not a
reminder. If the human wants to keep a `settings.json` personalization, move it to
`.claude/settings.local.json` **first**: Claude Code merges that over `settings.json`, the package
never writes it, and the customization then survives every future update.

## 2. Apply
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/update_reconcile.py" apply \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" --project-root "${CLAUDE_PROJECT_DIR}"
```
Add `--confirm-overwrite` only after the human has seen the diffs and agreed. Exit `2` means it
refused for exactly that reason — do not work around it by copying files yourself.

Apply writes the package files, **creates any absent seed** (and touches no present one), removes proven orphans, stamps
`.workflow/config.json` → `workflow_version`, and rewrites `.workflow/install-set.json` (the
ledger the *next* update reads). It touches nothing else — that is enforced by the runner, not by
this prose.

## 3. Regenerate what is derived from code
The code-map is generated, never migrated: a new package version may emit a new `graph.json`
schema or new node frontmatter, and the only correct way to get it is to re-run the generator.

- Run **`bash .workflow/codemap.sh`** to rebuild `docs/knowledge/graph.json` and the `[G]`
  (generated) node frontmatter.
- **Preserve every `[D]` body.** The durable half of a knowledge node — `# Sessions`, `Purpose`,
  the edge `why` prose — is authored by `document` over the project's whole life and is category
  (b). Regeneration replaces frontmatter and re-attaches those bodies unchanged. If the new schema
  cannot carry a `[D]` body forward, **flag it for the human and stop** — never auto-rewrite an
  authored body. (MVP is an idempotent reconcile; there is no migration-script ledger, deliberately.)
- If `codemap.sh` itself is missing or fails, say so and stop before committing — a project without
  a regenerable code-map is a finding, not something to paper over.
- `.workflow/checks.env` is **target-owned** and not refreshed. If the new package added a gate
  that needs a new key, say so and offer to add it — never rewrite the human's stack commands.
- **`.gitignore` is target-owned too, and `/update` does not write it.** If the new package introduced a runtime
  path (`shared/schemas.md` names each one as RUNTIME + gitignored), the existing project's ignore file predates
  it and will happily commit it. Name the missing line, offer to add it, and let the human say yes — the same
  posture as `checks.env`. Do not silently edit the file: it is frequently hand-curated, and a runtime path left
  out is a tidiness bug, while a rewritten `.gitignore` can start tracking or untracking product code.

## 4. The orchestrator brief
The brief lives in the target's root `CLAUDE.md` inside a **managed block** (the
`reeve:brief:begin` / `:end` markers, owned by `shared/schemas.md`). `/update`
replaces only what is between those markers, in greenfield, brownfield **and org** installs, so
project notes around it are never touched. **In org mode the brief is at `.claude/CLAUDE.md`, not the root
file** — refresh it there and leave the root `CLAUDE.md` alone; it belongs to the product's owner and the
workflow has never written a byte of it.

If the plan said `BRIEF-UNMARKED`, the install predates the markers. Do **not** guess where the
brief is. Show the human the current `CLAUDE.md`, propose wrapping the existing orchestrator
section in the markers (or appending a fresh marked block if there is none), and let them confirm.
Once marked, every later update refreshes it automatically.

## 5. Verify, summarize, commit
1. **Verify the install the same way `/start` step 7 does** — every manifest `install[].dest`
   present, no excluded test file leaked. Re-run `plan`: it should now report `SAME` for every
   package-owned path — and `SEEDED`, never `SEED`, for every seed (the ledger present too). A
   leftover `ADD`/`REFRESH`/`SEED` means a write was
   skipped — the signature of a non-interactive session hitting the `.claude/` guard. Report it and
   **do not commit**.
2. **Restart the daemon on the new code.** The console daemon is a long-lived process still running
   the *old* `bus.py`. Run `python3 .claude/scripts/bus.py stop` then
   `python3 .claude/scripts/bus.py ensure --workflow-dir .workflow`, and surface the URL.
3. **Write the change summary** for the human: old version → new version, what was refreshed, what
   was removed, what was flagged (local edits kept or overwritten, `ORPHAN-EDITED`, an unmarked
   brief, a `[D]` body that could not be carried forward), and anything they must do themselves.
4. **Stage the commit receipt** — `.workflow/maintenance/<item-id>.json`
   `{ item, kind: "update", summary }`, deleting any earlier receipt as you write yours
   (`shared/schemas.md` § commit-receipt). Use an id naming the motion, e.g.
   `update-<old>-to-<new>`. An update commit carries **package files and zero item files**, so it
   has no `verify-verdict` and the commit gate cannot otherwise tell a legitimately verify-free
   commit from one whose verify was skipped. The receipt is what tells it. It must be **staged in
   this commit** — an unstaged receipt sitting in the tree exempts nothing.

   **Never obtain this commit by editing `state.json`.** `status: building` with no current item
   is a legal state at a boundary and is not the thing blocking you; flipping it to `idle` turns
   the gate off for the duration, leaves a window where a crash makes the file lie about the
   loop's position, and misreports the loop to the console as "awaiting steering" while a wave is
   in flight. Never fake another motion's `kind` either — the kinds are validated.
5. **Commit** the update as one commit (the refreshed package files, the regenerated code-map,
   `config.json`, `install-set.json`, the receipt) with a message naming both versions. Runtime
   paths are gitignored and stay out of it.
6. **Tell them to `/clear` and start a fresh session.** This one is holding the old brief and the
   whole update transcript in context; the loop should resume from `handoff.md` on the new package.
