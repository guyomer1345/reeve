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
| **ask** | anything that **changes something you do not own** — `git push`, `gh`, publish/deploy/cloud CLIs, `ssh`/`scp`/`rsync` | outward actions are the ones you cannot take back |

Precedence is **deny > ask > allow**, so the outward list always wins over the broad local allow.
Local work runs silently; an action that **changes** something beyond this machine stops and asks you.
Merely *reading* from the network does not — see `curl`/`wget` below, and read that before assuming
the ask list is an egress boundary. It is not one.

**Broad-allow is deliberate, not laziness.** An enumerated per-tool safelist was rejected because it
cannot anticipate every project's toolchain, and because `cd x && cmd` chaining defeats prefix-matched
allows anyway — an allowlist that looks precise while being trivially bypassed is worse than an honest
broad one, because it invites trust it has not earned.

**`curl` and `wget` are NOT on the ask list, and the reasoning is the same one.** They were, and the
principle above does not fit them: `curl -sL <url>` is a **read**, and a read takes nothing back. The
line worth drawing is not network / no-network — `WebFetch` and `WebSearch` are broad-allow and both
reach the internet — it is **read-only** fetching versus **arbitrary egress carrying a body**. That
line cannot be drawn here: `curl` spans the whole range in one binary, and prefix-matched argument
patterns are fragile by Claude Code's own documentation, so it is all-or-nothing.
And gating it bought nothing, because **`Bash` is broad-allow**: `python3 -c "import urllib.request…"`,
`nc`, `/usr/bin/wget` and `cd /tmp && curl …` all ran unprompted the whole time. The rule stopped the
model that spelled its intent plainly and missed every other route — precisely the "trust it has not
earned" this package refuses elsewhere. **Read the ask list as a statement of intent about
irreversible change, not as an egress boundary. There is no egress boundary. If you need one, it has
to live below the permission layer** — a `PreToolUse` hook, a sandbox, or a network policy.

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
permissions at all — they are `PreToolUse` hooks (`hooks/guard.sh` on shell commands, `hooks/dispatch_guard.py`
on subagent dispatch), which **override allow and still fire under full bypass**:

- **secret-scan** — blocks a commit carrying a staged secret.
- **verify-before-commit** — blocks a commit whose item failed `verify`.
- **protected-branch floor** — blocks a push to `main`/`master` (lowerable per-project, deliberately).
- **remote mutation in org mode** — blocks `git remote add`/`set-url`/`rename` unless acknowledged, so a
  read-only clone cannot silently grow a push path.
- **dispatch fidelity** — blocks handing a loop node to a general worker. Every other gate here protects the
  repo from the loop; this one protects the loop from itself, because a worker dispatched without its role
  arrives with none of the rules above it and improvises whatever the prompt left out.

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
- **An `ask` in an unattended drive is a STOP, not a tripwire.** The ask list was calibrated for a
  session with a human in front of it, where a prompt costs a second. Left running overnight, the same
  rule halts the loop until somebody comes back — a cost nobody chose, inherited from the attended
  design. Until an ask can defer to the outbox the way `push` and `issue` already do, treat every entry
  on that list as a scheduled interruption of an unattended run, and keep the list to things that
  genuinely warrant one.
