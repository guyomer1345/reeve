---
description: Bootstrap the disciplined-builder workflow in this project and become the orchestrator. Auto-detects greenfield (empty) vs brownfield (existing code), scaffolds workflow state, and hands off to building the spec (greenfield) or ingesting the existing code (brownfield).
argument-hint: "[greenfield|brownfield]  (optional — auto-detected if omitted)"
---

# /start — bootstrap the workflow (the `init` capability)

Run once to turn the current directory into a workflow-driven project and initialise this session as the
**orchestrator**. Conceptually this is `init`; it is exposed as `/start` because `/init` is a
built-in Claude Code command.

## 0. Detect mode & guard
- If `.workflow/` already exists, the scaffold is present — but a `.workflow/` on disk proves only that a
  *previous* `/start` scaffolded, **not** that it finished. Two completeness checks apply, in order: first
  whether the **install** completed (the step-7 verification: every manifest `install[].dest` present + the
  daemon reachable — a non-interactive first run leaves a **half-installed, uncommitted hollow scaffold**),
  then whether the **bootstrap motion** completed (the `bootstrap:` phase line in `.workflow/handoff.md` —
  the install finishing is **not** the project being initialised):
  - **Install incomplete** (a hollow scaffold from an earlier non-interactive run) → do **not** re-scaffold and do
    **not** report "already initialised"; **resume the install** — re-run steps 4–7 (idempotent copies + the
    verification gate). Say plainly you are completing a previous half-init, not starting over.
  - **Install complete, bootstrap incomplete** (`handoff.md`'s `bootstrap:` is `installed`/`ingesting`/
    `discussing` — or absent, the signature of an older install) → do **not** report "already initialised" and do
    **not** stop: **resume the motion** — run `ingest` (§3) / `discuss` (§2) now, in this session. If the phase is
    `reconcile-parked`, report the open reconcile checkpoint (console + `parked/`) and stop — the motion is
    waiting on a human verdict, not on you.
  - **Bootstrap complete** (`bootstrap: complete`) → the project is fully initialised. Do **not** clobber: report
    current state and offer to resume from `.workflow/handoff.md`. Stop.
- **Then a third check, on a different axis entirely — is this project BOUND to this machine?** The two above ask
  *did a previous `/start` finish*; this asks *did it finish **here***. The durable half is committed and travels
  for free; the runtime half is machine-local and gitignored, so a move to another machine (or a rebuild of this
  one) leaves a project that is fully initialised and whose whole runtime tree is unreachable. A human on a new
  machine types `/start` first, so this is where they must be caught — it is the **fourth completeness state**:
  *installed + bootstrapped + **unbound***.
  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rebind.py" check --project-root "${CLAUDE_PROJECT_DIR}"
  ```
  Anything other than `HEALTHY` (or `NOT-STARTED`, which just means you are in the normal first-run case below)
  → **stop and route to `/rebind`**. Report what `check` said and do not proceed.
  **This is a guard, not a repair.** Do not re-scaffold, do not "resume the motion", and above all do not treat an
  unbound project as bootstrap-incomplete: `/start`'s motion re-runs `ingest`, and re-ingesting a 95-node
  brownfield project because its runtime pointer is stale is the wrong blast radius by an order of magnitude.
  Re-binding is also an **N-times** job (every machine move) and `/start` is a **once** command. `/rebind` owns it.
- Else pick the mode: `$ARGUMENTS` if given, otherwise **detect** — existing source files present →
  **brownfield**; empty (or package only) → **greenfield**. **Confirm the detected mode with the user**
  before proceeding (mis-classifying is costly).
- **`/start` is interactive-only.** The install (step 4) writes into `.claude/`, which Claude Code guards **above**
  the settings allowlist — trust and a `Write`/`Bash` allow do *not* waive it, so a non-interactive session
  (`claude -p`, the relaunch-runner) has no grant path and silently skips those writes. Run `/start` in an
  interactive session where the `.claude/` write prompts can be accepted; step 7 verifies the writes landed and
  **refuses to commit a hollow scaffold** if they did not. (The relaunch-runner never runs `/start` — it only
  resumes an already-initialised project — so this constraint does not touch away-autonomy.)

## 1. Shared steps (both modes)
**Progress is visible from the first minute.** At every stage boundary of this motion (each numbered step here,
and each `ingest` stage on brownfield), publish `.workflow/state.json` (atomic write-temp → rename) as
`{"status": "building", "phase": "bootstrap", "node": "start:<step>", "note": "<one human-readable line, e.g.
'installing package (step 4)' or 'seeding knowledge nodes 40/95'"}`, and print the same one-line banner in the
terminal. The console's "Now" panel renders exactly these fields, so the human sees the bootstrap move instead of
a silent half hour. `phase: "bootstrap"` is present only during this motion (`schemas.md` owns the shape); the
loop's normal `state.json` takes over when the motion ends.

1. **repo-setup:** ensure git is initialised (`git init -b main`), a git identity is set, and a
   `.gitignore` exists. If a remote is wanted and `gh` is unauthenticated → raise `checkpoint`(kind=setup)
   → `setup-guide` for `gh auth login`. If already authenticated, create/push directly.
2. **Scaffold the workflow layout** (provisional — EXPAND):
   ```
   .workflow/
     config.json       # project_root + run config      (committed)
     loop.md           # routing graph + diagram        (committed)
     checks.sh         # mechanical-gate runner — installed FIXED from templates/ (--fix / --check) (committed)
     checks.env        # per-stack commands checks.sh reads — data /start writes (committed)
     codemap.sh        # code-map runner — a thin stack-independent wrapper (one auto-dispatching call into the shipped engine; writes docs/knowledge/graph.json) (committed)
     state.json        # live position — RUNTIME, add to .gitignore
     orchestrator.lock # single-orchestrator liveness marker (runner's precondition) — RUNTIME, add to .gitignore
     install-set.json  # what this install wrote + the hashes — /update's ledger (committed)
     handoff.md        # durable resume anchor          (committed)
     backlog.md        # live OPEN queue (issues + roadmap; closed leave) (committed)
     outbox/           # RUNTIME — pending outward-action queue (push/issue awaiting a console release); add to .gitignore
   <project_root>/     # the product (greenfield: project/ ; brownfield: repo root)
     llms.txt          # thin agent entry point → docs/knowledge/  (committed)
     rules/            # engineering rules — specialized baseline, subtree-overridable (committed)
     docs/             # docs-root — durable product knowledge
       spec.md         # product spec — ONE file (discuss fills this)  (committed)
       architecture.md # inline Mermaid-C4 (document-owned)  (committed)
       knowledge/      # code map                            (committed)
       decisions/      # decision-records = ADRs (append-only) (committed)
   ```
   `.workflow/items/<id>/`, `.workflow/align/` and `.workflow/demo-approvals.json` are **not** scaffolded here —
   `planner` `mkdir`s each item dir on demand, `align` `mkdir`s `.workflow/align/` on its first run (writing
   `anchor.json`), and `check_demo_bundle.py --promote` writes the approvals file the first time a demo is
   approved. All three are **committed** when they appear (the gitignore below is an allowlist of runtime paths,
   so a new durable file is committed by default — which is the right default for a ledger).
   Add the **runtime** paths to the target's `.gitignore` — `state.json`, `runtime.json`, `bus.json`, `bus.lock`,
   `orchestrator.lock`, `alerts.json`, `outbox/`, `parked/`, `inbox/`, **`secrets/`**, `remote_token`, `statusline.delegate`, `demos/`, and the per-ticket worktrees (created at runtime by the
   bus/orchestrator, not scaffolded here); the durable artifacts (`config.json`, `loop.md`, `checks.sh`,
   `checks.env`, `codemap.sh`, `handoff.md`, `backlog.md`, `items/`, and `docs/`) are committed. **`secrets/` holds live
   credentials** a human hands over at a setup checkpoint — it must be gitignored *and* live on a filesystem that
   honours `0600`; it is never swept by the retention pass.
3. **Place the runtime tree on a filesystem that can hold it.** Check the mount under the launch root. The
   atomicity- and mode-sensitive runtime paths (`state.json`, `bus.json`, `bus.lock`, `orchestrator.lock`, `alerts.json`, `parked/`,
   `inbox/`, `outbox/`, `secrets/`, `remote_token`) need a **local** filesystem: on a network-style or Windows-interop mount, `rename` is not
   reliably atomic and — the one that bites silently — **a file created `0600` can come back world-readable with no
   error at all**, which would leave the console's capability token and any stored credential readable by other
   users on the machine.
   **Do not decide either half of this by hand** — both the check and the location are code-owned:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rebind.py" bind --project-root "${CLAUDE_PROJECT_DIR}"
   ```
   (Read in place from the plugin root deliberately, and only here: step 4 has not copied it into the project
   yet, and this is a one-shot, stateless read invoked by an interactive command — not a long-lived reference
   that a later plugin update could pull out from under. `bind`, not `apply`: on a project's first minute there
   is nothing to have lost, so it does no loss accounting and never guesses a loop position.)
   On a fresh scaffold this measures the mount (a `0600` create, then a `stat` — behaviour, not a mount-type
   guess), derives the runtime root, creates it `0700`, stamps it with this project's identity, and writes the
   pointer if and only if one is needed. Report what it did.
   - **Local mount (the common case):** nothing to do. `.workflow/` is the runtime root; no pointer is written.
   - **Network-style / interop mount** (e.g. a repo under a mounted Windows drive): the tree is created at
     `$XDG_STATE_HOME/dev-autonomous-workflow/<slug>-<hash-of-the-project's-abspath>` and
     **`.workflow/runtime.json`** = `{"runtime_root": "<abs path>"}` is written. That pointer is how every other
     process finds the relocated tree, so it stays on the repo mount and is **gitignored** (the path is
     machine-specific — committing it would hand a clone a wrong root). Tell the user plainly that `.workflow/`
     now spans two filesystems, and why.
   **Never pick the path yourself.** It used to be prose, and a chosen path meant two projects with the same
   basename in different parents derived the *same* root and cross-bound two live installs — silent, two-project
   corruption. The hash of the absolute path is what prevents it, and the determinism is also what lets `/rebind`
   guess a canonical location from the project alone when a pointer is lost.
   - Committed artifacts (`handoff.md`, `backlog.md`, `config.json`, `docs/`) **never** relocate — they live with the
     repo by definition. Only the runtime half moves.
4. **Install the package into the project.** Claude Code exposes the bundled package at
   **`${CLAUDE_PLUGIN_ROOT}`** and the project root at **`${CLAUDE_PROJECT_DIR}`** (both substituted in this
   command). Always copy *out* of the plugin into the project — never invoke a shipped script in place, because
   `${CLAUDE_PLUGIN_ROOT}` is replaced on every plugin update.
   - **Orchestrator brief** (the driver). **In both modes the brief goes into the root `CLAUDE.md` wrapped in
     the managed-block markers** — `shared/schemas.md` owns the exact strings:
     ```
     <!-- dev-autonomous-workflow:brief:begin -->
     <!-- managed block: /update replaces everything between these markers. Put project notes OUTSIDE them. -->
     …the filled template…
     <!-- dev-autonomous-workflow:brief:end -->
     ```
     Greenfield wraps its brief too even though it is writing a fresh file: the markers are what let a later
     `/update` refresh the brief **without** clobbering notes the human adds to that file afterwards, and a
     greenfield `CLAUDE.md` collects those notes just as surely as a brownfield one. One shape, both modes.
     - **greenfield:** write the launch-root **`CLAUDE.md`** from `${CLAUDE_PLUGIN_ROOT}/templates/orchestrator-CLAUDE.md`
       (fill `<project>`/`<project_root>`, wrap in the markers) and put the product under **`project/`** (its own
       `CLAUDE.md` left to the product); set `project_root: ./project`.
     - **brownfield:** the product stays at the repo root; wrap that same filled template in the markers and
       **append** it to the *existing* root `CLAUDE.md` (never clobber — idempotent via the markers); read
       that existing `CLAUDE.md` as a **primary ingest source**; set `project_root: .`.
   - Copy `${CLAUDE_PLUGIN_ROOT}/templates/loop.md` → **`.workflow/loop.md`** and write
     **`.workflow/config.json`** (`project_root` + run config).
   - **Capture any pre-existing statusline *before* the copy (composition — never clobber).** The template
     `settings.json` wires the interactive context governor's `statusLine`, and a project `statusLine` shadows
     the user's global one; so the governor **delegates** to whatever statusline already existed rather than
     replacing it. Record that command into **`.workflow/statusline.delegate`** (gitignored) *before* overwriting
     `.claude/settings.json` — the shipped `statusline.py` runs it and appends only the budget banner. Idempotent
     (a resumed install finds only the governor itself and writes nothing), and a no-op when the user has no
     statusline (the governor then renders its own minimal base line):
     ```bash
     python3 - <<'PY'
     import json, os
     GOV = "statusline.py"                         # our own command — never delegate to it
     candidates = [".claude/settings.local.json", ".claude/settings.json",
                   os.path.expanduser("~/.claude/settings.json")]
     found = None
     for p in candidates:                          # highest precedence first
         try:
             cmd = (json.load(open(p)).get("statusLine") or {}).get("command", "")
         except Exception:
             cmd = ""
         if cmd and GOV not in cmd:
             found = cmd; break
     if found:
         os.makedirs(".workflow", exist_ok=True)
         open(".workflow/statusline.delegate", "w").write(found + "\n")
         print("statusline: composing over existing ->", found)
     else:
         print("statusline: no pre-existing statusline to compose over (governor renders its own base)")
     PY
     ```
   - Copy `${CLAUDE_PLUGIN_ROOT}/templates/settings.json` → **`.claude/settings.json`** (loop permission rules:
     `allow` local actions; the outbox-covered outward classes — `git push`, `gh issue` — are deliberately
     **not** `ask`ed, because they are approved through the outbox + a console `release` and fired later at a
     boundary, when a terminal prompt would reach nobody; every other outward command — deploy / publish / cloud /
     network — stays `ask`). The template also wires the **interactive context governor**: a `statusLine`
     (`.claude/scripts/statusline.py`) that shows a persistent banner once context passes `config.context.warn_pct`
     telling the human to run `/dispatch` then `/clear`; a `SessionStart` hook that re-injects
     `.workflow/handoff.md` on matcher `clear` so a cleared session **auto-rehydrates**; and a `PreCompact` backstop
     that preserves the handoff through an auto-compaction. That same `SessionStart` hook is wired on `startup` and
     `resume` as well, where it does a *different* job: it re-asserts `.git/hooks/pre-commit`, because
     `.git/hooks/` is not part of the repository and so a **clone** of an already-bootstrapped project arrives with
     the mechanical gate silently missing — and a clone runs neither `/start` nor `/rebind`. It installs when
     absent, is silent when identical, and **never clobbers a foreign hook**. `/dispatch` (a shipped command) writes a complete handoff on
     demand so the `/clear` is always safe.
   - **Install the shipped scripts + hooks — from the manifest, not enumerated here.** Read
     **`${CLAUDE_PLUGIN_ROOT}/MANIFEST.json`**; for every `{src, dest}` in its **`install`** array, copy
     `${CLAUDE_PLUGIN_ROOT}/<src>` → `${CLAUDE_PROJECT_DIR}/<dest>` (creating parent dirs). **Honour the manifest
     `exclude`:** when `<src>` is a **directory** (e.g. `scripts/codemap`), do not copy files matching an `exclude`
     glob — the beside-code tests must not land in the target, and neither must build cruft (a plugin sourced
     from a working directory rather than a release snapshot carries `__pycache__/*.pyc`, which slips past a
     `test_*.py` glob because a `.pyc` basename is not a `*.py`). Read the globs from the manifest rather than
     hardcoding them here, e.g.
     `rsync -a --exclude='test_*.py' --exclude='*.pyc' --exclude='*.pyo' <src>/ <dest>/` (or `cp -r` then delete
     the matches); step 7's verification rejects a leaked excluded file. That manifest is the
     **single source** for what installs into `.claude/`; because nothing is listed here, a script added to the
     package is picked up automatically — the drift that once dropped `loop.sh` and the demo-bundle lint from a
     hand-kept copy list cannot recur. Everything it installs is **stack-agnostic** (it reads only the workflow's
     own `.workflow/`+`docs/` layout), so it ships fixed — never generated per-stack. What the set does, for
     orientation (the manifest, not this prose, is authoritative on *which* files ship):
     - the **console daemon** (`bus.py`) — the detached local HTTP daemon that serves the supervision console and
       is a human's channel to the loop while it is busy, parked, or dead; a per-project copy is what **keys it
       per project** (its lock, discovery record, and port all derive from that project's runtime root, so two
       projects cannot collide), with its **drain bookkeeper** (`drain.py` — the boundary-inbox drain the
       orchestrator runs each turn: which messages are new, in what order they apply, the watermark, what may be
       pruned) and **launcher** (`loop.sh`) beside it. Both resolve paths *through* the daemon, so all three must
       land in the same `.claude/scripts/`. With `config.runner` on, **start/resume the orchestrator via
       `bash .claude/scripts/loop.sh`, not bare `claude`** — a bare start is invisible to the relaunch-runner (the
       one operator residual, same footing as the single-orchestrator run-constraint);
     - the **code-map extractor** (`codemap/`) the generated `.workflow/codemap.sh` invokes to build the knowledge
       graph; the **retention** enforcer `document` (audit mode) runs to bound the append-only tier; the
       **coverage gates** + the **contract linter** that `checks.sh --check` / `align`'s mechanical layer invoke
       (a load-bearing promise can't ship with no resolvable / boundary test; no `artifact` criterion without a
       mechanical `discharge`; no governing decision mapped to no step; every routing target resolves); and the
       **demo-bundle lint** `create-demo` runs before it parks a sandbox (the CSP enforces *isolation*, but
       *self-contained* — no external hosts, no `eval`, build-free — it does not, so a slip renders locally and
       blanks over the remote surface); and the **reconcile runner** (`update_reconcile.py`) that records this
       install's ledger below (step 7) and that `/update` later drives to migrate the project onto a newer package;
     - the git **hooks** into **`.claude/hooks/`** — `guard.sh` (secret-scan + verify-before-commit + the **push
       floor**: never move a protected branch, never push a secret) and `pre-commit.sh` (the mechanical-gate
       backstop, registered as the git hook in step 6), plus `verify_check.py`, the **shared verify-before-commit
       helper both hooks call** (so the two gates enforce it identically; it fails closed and derives the item from
       the staged diff, immune to state.json shape/path drift). `build-once-per-wave` is deferred.
   - **Trust the workspace so the shipped allowlist is live.** Claude Code only honours
     `.claude/settings.json`'s `permissions.allow` when the launch root is **trusted**; until then `claude -p`
     (and the relaunch-runner) ignore the allowlist and **stall on the first tool prompt** — and on WSL the
     interactive trust dialog frequently does not render, so the loop cannot clear it itself. Establish trust
     directly by recording it in `~/.claude.json` (exactly what accepting the dialog does), keyed by the launch
     root's **absolute** path — merge-preserving, idempotent, atomic, and a no-op if already trusted:
     ```bash
     python3 - "$(pwd)" <<'PY'
     import json, os, sys
     root = os.path.abspath(sys.argv[1])
     p = os.path.expanduser("~/.claude.json")
     try:
         data = json.load(open(p))
     except FileNotFoundError:
         data = {}
     except Exception:
         sys.exit("WARN: ~/.claude.json is unparseable — not touching it; accept the trust dialog by hand.")
     entry = data.setdefault("projects", {}).setdefault(root, {})
     if entry.get("hasTrustDialogAccepted") is True:
         print("trust: already accepted for", root); raise SystemExit
     entry["hasTrustDialogAccepted"] = True
     tmp = p + ".tmp"
     json.dump(data, open(tmp, "w"), indent=2)
     os.replace(tmp, p)
     print("trust: marked", root, "trusted in ~/.claude.json")
     PY
     ```
     Tell the human plainly what you did and why — this is a real trust grant on their machine (the equivalent of
     clicking *"trust this folder"*): the workspace is now trusted so the loop's pre-approved local actions run
     without a prompt. If the script warned that `~/.claude.json` was unparseable, say so and have them accept the
     dialog (or set `projects["<abs path>"].hasTrustDialogAccepted: true`) by hand.
   - **Surface the one-time permission message** to the human: *"This is an autonomous loop. This workspace is
     now **trusted** (recorded in `~/.claude.json`) — that is what makes the **running loop's** pre-approved local
     actions run prompt-free. (The one-time `/start` install writes into `.claude/`, which Claude Code guards
     **above** trust — those are the prompts you accept during setup; they are not waived by trust, and going
     forward the loop's allowlisted local actions do not prompt.) If a trust dialog still appears in your setup,
     accept it. Pushes and issue create/close are
     **not** approved by a terminal prompt — they queue to `.workflow/outbox/` and wait for you to release them
     from the console, so the loop keeps working while you are away; deploys and other outward commands still ask.
     Two things are hard blocks, not prompts, and nothing can waive them: the loop never moves `main`/`master`,
     and it never pushes a secret. You don't need `--dangerously-skip-permissions`."*
5. **Bring the console up and put it in front of the user — the bootstrap's front door.** Run
   `python3 .claude/scripts/bus.py ensure --workflow-dir .workflow` **now, immediately after the install copies
   land** — the rest of the bootstrap (rules-wiring, and on brownfield the whole `ingest` build) is the long
   half, and the human should watch it from the console, not stare at a silent terminal. The command is
   **adopt-or-spawn and idempotent**: it adopts a daemon that is already up and only spawns one if none is,
   because spawning fresh would drop messages already sitting in the inbox.
   - **Surface the URL as a headline, not a log line.** Print it on its own, clearly marked
     (`Console: http://127.0.0.1:<port>/ — open this now`), and **best-effort open a browser on it**: try
     `wslview <url>` → `xdg-open <url>` → `open <url>` → `explorer.exe <url>`, first available wins; if none
     exists (headless/SSH), the printed URL is the always-works fallback — say the user can reach it from a
     browser on the host machine. **Never let the opener block the bootstrap** — run it detached with a hard
     timeout and ignore its exit status: on WSL `xdg-open` sits for ~2 minutes before giving up, which stalls
     the motion at the exact moment the human is being told to look at the console.
     ```bash
     ( for o in wslview xdg-open open explorer.exe; do
         command -v "$o" >/dev/null 2>&1 && { timeout 5 "$o" "$URL" >/dev/null 2>&1 & break; }
       done ) &
     ```
     The printed URL is the contract; the auto-open is a convenience that must never cost time.
   - **State the interaction contract, in one short paragraph, right here** (and again at the end of the
     motion): *"The terminal is where we talk — live dialogue and design discussion. The console is where you
     watch and steer: live bootstrap progress, checkpoint verdicts, and an **intake form** for feature
     requests/priorities. You can use it right now — anything you file while I build queues durably and is
     triaged the moment the bootstrap finishes."* (Intake filed during bootstrap lands in `inbox/` and is
     drained at the first scheduler boundary after the reconcile/spec gate — nothing is lost, nothing acted on
     prematurely.)
   - The daemon is **detached into its own session**, so it outlives this session, a `/clear`, a `--resume`, and
     the terminal closing. That is the point: a verdict must be deliverable while the loop is busy, parked, or
     dead.
   - If it reports a **warning about file mode**, relay it rather than swallowing it: it means this filesystem
     ignored the `0600` on the token file, so the console's capability token is readable by other users on the
     machine. The fix is to place the runtime tree on a local filesystem (step 3).
   - On WSL the daemon dies a few seconds after the last terminal closes (a detached process cannot hold the
     distro alive); it comes back on the next `/start`, and nothing already written to the inbox is lost.
6. **Specialize rules + wire enforcement** (the disciplined layer). The **stack-dependent** half — specializing
   the `rules/` `— enforced by:` tags to concrete tools, filling `.workflow/checks.env`, wiring the concrete
   enforcers, and adding build-output `.gitignore` patterns — is **the stack-wiring step**. Run it **only when a
   stack is known**:
   - **Brownfield** (or greenfield with a stack already declared in the spec): the stack is detectable now — run
     the stack-wiring step here, adopt-and-gap-fill (never clobber an existing config).
   - **Greenfield with no stack yet** (an empty `project/`): there is **nothing to detect**. Seed only the
     stack-independent floor now — the rules **baseline** (unspecialized), `checks.sh` verbatim, a **coverage-only**
     `checks.env`, the git backstop, the `codemap.sh` wrapper — and **defer the stack-wiring step to `tech_stack`
     lock**: the orchestrator re-runs it the moment `decision-engineer` resolves the stack (see `.workflow/loop.md`
     → *Stack-wiring at tech_stack lock*). Until then `checks.sh --check` **fails the commit closed** the instant
     source lands under `project_root` with no stack gate wired — so a missed re-run cannot silently disarm the
     gate, it stops the loop loudly instead.
   - **Seed the rules.** Copy the package baseline `${CLAUDE_PLUGIN_ROOT}/rules/*.md` → **`<project_root>/rules/`**. When the
     stack is known, rewrite each `— enforced by: <mechanism>` tag with the
     project's *concrete* tool (e.g. `formatter` → `prettier`/`black`/`gofmt`), so the agent reads real commands.
     Nearest-file-wins: this project copy is the floor a subtree `rules/` can override.
   - **Wire the enforcers named by the tags.** For each enforceable principle, install the concrete gate from
     the detected stack: `.editorconfig`, formatter, linter, typechecker (where the language has one), the
     test-runner script, a dependency-audit step, and a **CI workflow** that runs format-check + lint +
     typecheck + test on push/PR. **Greenfield:** write these from the detected stack. **Brownfield:** *adopt*
     what already exists — never clobber a config the project ships; record the existing tool as the enforcer
     in the specialized `rules/`, and only **gap-fill** the missing ones.
   - **Install `.workflow/checks.sh` + write `.workflow/checks.env`** — the one mechanical-gate runner both
     callers share (`--fix` for the `commit` skill in-loop; `--check`, fail non-zero on drift, for the git hook).
     **Copy `${CLAUDE_PLUGIN_ROOT}/templates/checks.sh` → `.workflow/checks.sh` VERBATIM — never author it
     freehand.** It ships fixed and tested; its invariant, error-prone half (the `--fix`/`--check` dispatch, the
     loop over each open item's `promises.json` running the stack-agnostic `check_promise_coverage.py` /
     `check_criterion_discharge.py` / `check_decision_coverage.py`, and the exit aggregation) must not be
     re-derived per bootstrap — a syntax slip there dead-ends the loop at its first commit. Its **only**
     per-project input is a small **data** file you write from the detected stack, `.workflow/checks.env`
     (`KEY="value"` lines; empty/unset skips that check):
     - `FMT_FIX` / `LINT_FIX` — formatter-write / linter-`--fix`, as command **prefixes** (the runner appends the
       item's staged file list in `--fix`, so `commit` scopes fixers to staged files, never a repo-wide sweep);
     - `FMT_CHECK` / `LINT` / `TYPECHECK` / `TEST` — the repo-wide `--check` gates (each carries its own path;
       omit `TYPECHECK` for a language with no typechecker).
     **Greenfield with no stack yet writes an empty (coverage-only) `checks.env` now and fills these at
     `tech_stack` lock** (the stack-wiring step above); the `checks.sh` backstop fails the commit closed if source
     lands before then. Both files are committed. `--check` also runs the three stack-agnostic coverage gates over every open item —
     a load-bearing promise with no resolvable / boundary test, an `artifact` criterion with no `discharge`, or a
     governing decision mapped to no step fails the commit (the mechanical plan-coverage gates; teeth, not advice).
   - **Register the git backstop.** Install `pre-commit.sh` (copied to `.claude/hooks/` in step 4) as git's
     `.git/hooks/pre-commit` (copy or symlink — git requires the exact name `pre-commit`) so a commit made
     *outside* the loop still hits `checks.sh --check`.
   - **Generate `.workflow/codemap.sh`** — the code-map runner: a single call to the shipped engine
     (`.claude/scripts/codemap/codemap.py <project_root>`), which auto-dispatches each file to its language arm
     and writes `docs/knowledge/graph.json` (a typed import graph plus the *impact* and *orchestration* centrality
     signals per file, and a per-language coverage summary tagging each language's arm tier). **Python** (stdlib
     `ast`), **JS/TS** (`tsconfig`/`jsconfig` `paths`+`baseUrl` aliases + extension/index resolution), **Go**,
     **Java**, and **C#** have precise resolver arms; every other recognized source language falls to the **tier-0
     generic floor** (directory-cluster nodes + shallow-regex imports, precision-first resolution, same `graph.json`
     contract) so a repo in any recognized language gets at least nodes + clusters + both lenses — never nothing.
     (Further precise arms are zero-dep resolvers that plug into the same engine as they land — C++ needs a
     compile-DB, so it stays on the floor for now; tree-sitter is reserved for parse-hard languages, shipped as an
     optional upgrade.) Regenerable — the loop re-runs it and never hand-edits the graph.
   - **Externals → checkpoint.** Anything needing an account or a provider choice (CI host, deploy creds) is an
     outward/setup step → raise `checkpoint`(kind=setup) → `setup-guide`, don't guess.
7. **Verify the install landed, then commit — never commit a hollow scaffold.** This gate is what makes the
   half-installed state impossible: initialisation is "done" only when the scaffold **and** the installed files are
   present. Assert every manifest `install[].dest` exists in the project, no excluded test file leaked into an
   installed directory, and the daemon answered in step 5:
   ```bash
   python3 - "${CLAUDE_PLUGIN_ROOT}" "${CLAUDE_PROJECT_DIR}" <<'PY'
   import fnmatch, json, os, sys
   plugin, project = sys.argv[1], sys.argv[2]
   man = json.load(open(os.path.join(plugin, "MANIFEST.json")))
   missing = [e["dest"] for e in man["install"]
              if not os.path.exists(os.path.join(project, e["dest"]))]
   leaked = []
   for e in man["install"]:
       d = os.path.join(project, e["dest"])
       if os.path.isdir(d):
           for root, _, files in os.walk(d):
               for f in files:
                   if any(fnmatch.fnmatch(f, os.path.basename(p)) for p in man.get("exclude", [])):
                       leaked.append(os.path.relpath(os.path.join(root, f), project))
   if missing or leaked:
       for m in missing: print("MISSING:", m)
       for l in leaked:  print("LEAKED excluded file:", l)
       sys.exit(1)
   print("install verified:", len(man["install"]), "entries present, no excluded leaks")
   PY
   ```
   - **All present (exit 0)** → **stamp the install, write both ledgers, then commit**:
     - add `"workflow_version": "<version>"` to `.workflow/config.json`, read from
       `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` — the migration key a future `/update` diffs against;
       without it an installed copy cannot say which package snapshot it holds;
     - **record the install-set** — run
       `python3 .claude/scripts/update_reconcile.py record --plugin-root "${CLAUDE_PLUGIN_ROOT}" --project-root "${CLAUDE_PROJECT_DIR}"`,
       which writes **`.workflow/install-set.json`**: every path this install wrote, with the hash it wrote.
       That record is what lets a later `/update` tell a **retired package file** (recorded by us, no longer
       shipped ⇒ removable) from **a file the human dropped in** (never recorded ⇒ never touched), and a
       pristine package file from a hand-edited one. Without it, an update can only ever flag. If the command
       warns that no managed brief block was found, fix the `CLAUDE.md` markers now (step 4) rather than
       leaving a future `/update` unable to refresh the brief;
     - write the bootstrap phase line **`bootstrap: installed`** into `.workflow/handoff.md` — the durable
       ledger §0's re-run guard keys on;
     - commit the initialised scaffold. **The commit is not the end of `/start`** — it closes the *install*,
       not the *bootstrap*. Continue immediately with §2 (greenfield) / §3 (brownfield) in this same session.
   - **Anything missing (exit 1)** → **STOP. Do not commit.** A missing `install[].dest` means the `.claude/` writes
     were skipped — the signature of a **non-interactive** `/start` (Claude Code guards `.claude/` above the
     settings allowlist, so `claude -p` has no grant path). Report exactly which files are missing and that
     `/start` must be re-run in an **interactive** session where the `.claude/` write prompts can be accepted. The
     scaffold stays **uncommitted**, so the re-run resumes cleanly via step 0 rather than reporting "already
     initialised" over a hollow tree.

## 2. Greenfield (new project)  — fully supported
- Scaffold an empty `<project_root>/docs/` (spec, architecture, knowledge, decisions); it grows as the project
  is built.
- **Continue now — do not stop at the commit.** Update the ledger to **`bootstrap: discussing`** and invoke
  **`discuss`** (inception) in this session to build the spec from zero — restating the interaction contract
  (step 5) once as the dialogue opens, since this is the moment the human starts talking to the loop. When the
  spec lands, flip the ledger to **`bootstrap: complete`** → then the normal loop (`prioritize → planner → …`).

## 3. Brownfield (integrate existing codebase)  — driven end-to-end
- **Rules + enforcement are already adopted** by shared step 6 (adopt existing configs, gap-fill the missing
  enforcers, layer our `rules/` on top). That is the *habits* half of integration; the **docs → knowledge** half
  is the `ingest` skill below.
- **Run `ingest` now, in this session — the scaffold commit was not the end of `/start`.** Update the ledger to
  **`bootstrap: ingesting`** first. The skill runs `.workflow/codemap.sh` to build the structural graph, seeds
  `docs/knowledge/` nodes, and reconstructs the spec from the existing `CLAUDE.md`/docs + code — into
  `docs/spec.md`, **or into the project's own adopted spec file when it already has one** (tagged
  `unspecified`), publishing the `state.json` progress markers at every stage (the §1 preamble — the console is
  watching). **Adopt an existing `docs/`** if present — write to known subpaths, never clobber; namespace
  ours on a name collision. Match subpaths **case-insensitively**: `docs/` here sits on the repo mount, which on
  Windows / WSL `/mnt/*` 9p / macOS is case-insensitive, so a workflow-owned `docs/architecture.md` and an
  adopted `docs/ARCHITECTURE.md` are one file — adopt the existing case-variant in place, never write a lowercase
  twin over it. The durable per-file `why`/Sessions stay empty until `document` authors them on first touch.
- **Reconciliation checkpoint** — `ingest` surfaces the reconstructed understanding ("here's what I think the
  app does, its core flows, its stack") via a blocking `checkpoint` for the user to confirm/correct; confirmed
  invariants flip `unspecified → locked` before the loop drives. Parking it sets the ledger to
  **`bootstrap: reconcile-parked`** — the motion ends **here**, at its designed human gate: tell the user the
  reconcile is waiting (console link + terminal), restate the interaction contract once, and end this context
  window — the loop resumes on the verdict in a fresh session (the drain/runner picks it up), never by rolling
  the bootstrap window into feature work.
- The session that consumes the reconcile verdict flips the ledger to **`bootstrap: complete`** and hands to
  the normal loop.

## Expand later
- Additional **code-map language arms** — Python (`ast`), **JS/TS** (tsconfig resolver), **Go**, **Java**, and
  **C#** precise arms plus the **tier-0 generic floor** (all other recognized languages) ship today; the next
  prevalence-ranked precise arms (C++ — needs a compile-DB — then Rust · PHP) are **zero-dep resolver arms** on the
  same engine + `graph.json` contract, each upgrading its language from the floor's best-effort edges to precise
  resolution. tree-sitter is reserved for parse-hard languages (optional upgrade — absent → the floor).
- The full **disk layout** — the tree above is a provisional first cut.
