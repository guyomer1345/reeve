# Trust & permissions — what this package asks for, and what it refuses

Read this before the first `/start`. An autonomous loop that stops for a prompt on every file write
is not autonomous, so this package asks for **broad local permission**. That is a real ask, and it
should be a considered one rather than a surprise. This file states exactly what is granted, what
stays gated, and what is enforced even when you turn the gates off.

## The shape: broad local, deliberate outward

`/start` installs `.claude/settings.json` with two lists:

| | what | why |
|---|---|---|
| **allow** | local work — `Bash`, `Read`/`Write`/`Edit`, `Task`, web lookups | the loop edits, runs tests and reads constantly; prompting on each one is fatigue, and fatigue is what makes people approve things unread |
| **ask** | anything that leaves the machine — `git push`, `gh`, publish/deploy/cloud CLIs, `ssh`/`scp`/`rsync`, `curl`/`wget` | outward actions are the ones you cannot take back |

Precedence is **deny > ask > allow**, so the outward list always wins over the broad local allow.
Local work runs silently; leaving the machine always stops and asks you.

**Broad-allow is deliberate, not laziness.** An enumerated per-tool safelist was rejected because it
cannot anticipate every project's toolchain, and because `cd x && cmd` chaining defeats prefix-matched
allows anyway — an allowlist that looks precise while being trivially bypassed is worse than an honest
broad one, because it invites trust it has not earned.

## You do not need `--dangerously-skip-permissions`

This is the most important line here. That flag auto-approves **outward** actions too, which destroys
the one gate that matters. The package is built so you never need it: local work is already allowed,
so the only prompts you should see are the ones you actually want to see.

If you are seeing constant prompts for ordinary local work, the settings are not live — that is a
**trust** problem, below, not a reason to reach for the flag.

## Workspace trust — why `/start` touches `~/.claude.json`

Claude Code only honours `.claude/settings.json`'s `permissions.allow` once the launch root is
**trusted**. Until then the allowlist is inert, every local action prompts, and a non-interactive
(`claude -p`) session cannot clear the dialog itself — in headless runs it frequently does not render
at all, so the loop would hang against a dialog nobody can see.

So `/start` records trust for the project root directly. It is merge-preserving, idempotent, atomic,
a no-op if already trusted, and it **refuses to touch an unparseable `~/.claude.json`**, telling you to
accept the dialog by hand instead. If you would rather grant trust yourself, accept the dialog in an
interactive session before running `/start` — the step then does nothing.

Trust is scoped to **that project root's absolute path**. It is not global, and moving the project
means re-establishing it (which is what `/rebind` exists for).

## What is enforced regardless — the floor

Permissions are user-controlled by design: no `CLAUDE.md` and no command can raise its own privileges,
and this package only ever *recommends* a mode. So the guarantees that must not be optional are not
permissions at all — they are a `PreToolUse` hook (`hooks/guard.sh`), which **overrides allow and still
fires under full bypass**:

- **secret-scan** — blocks a commit carrying a staged secret.
- **verify-before-commit** — blocks a commit whose item failed `verify`.
- **protected-branch floor** — blocks a push to `main`/`master` (lowerable per-project, deliberately).
- **remote mutation in org mode** — blocks `git remote add`/`set-url`/`rename` unless acknowledged, so a
  read-only clone cannot silently grow a push path.

These fail **closed**: a degraded read (missing config, malformed JSON, no interpreter) blocks rather
than permits. Silence is only ever allowed to be *more* conservative.

## Honest limits

- **Outward gating under full bypass is not solved by the hook.** `guard.sh` hard-blocks the specific
  operations above, but the general `ask`-on-outward gate is a permission rule, and `--dangerously-skip-
  permissions` bypasses permission rules. Do not use that flag with this loop.
- **Broad local allow means the loop can run arbitrary local commands** — including a project's own
  test/build scripts. That is the point, and it is why the adopted-stack gate refuses to execute a
  tree's own commands until you have declared them, and refuses outright in org mode.
- **Trust is per-root and per-machine.** A synced or copied project does not carry it.
