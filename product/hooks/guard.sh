#!/usr/bin/env bash
# PreToolUse(Bash) guard for the disciplined-builder loop.
#
# Enforces the gates that are legitimate HARD blocks — operations you never *want*
# to perform, so there is no approve-and-proceed path:
#   - secret-scan          : never commit a secret staged in the diff
#   - verify-before-commit : never commit an item whose verify-verdict is a fail
#   - protected-branch push: the loop never moves main/master (a human does)
#   - push secret-scan     : never send a secret in the outgoing commit range
#   - obscured outward act : an outward action hidden in a chain/subshell is forced
#                            to run directly, so this guard can parse it
#
# Why the push floor is here and not a permission prompt: an outward action is
# approved through the outbox + a console release, and the loop fires it later at a
# scheduler boundary — possibly with nobody at the terminal. A static `ask` on the
# push would prompt into a terminal no one is watching and block the very
# away-release it was meant to protect. So the harness stays out of the outward path
# and THIS is the floor. Exit 2 blocks the call, overrides allow rules, and fires
# under bypassPermissions mode, so an `allow` rule cannot weaken any gate below.
#
# Fail-CLOSED on the gated operations: if python3 is unavailable we match against the
# raw hook payload instead of the parsed command, so removing python3 cannot disable
# the gate; and a push whose refspec cannot be parsed is refused rather than guessed.
# The git-native pre-commit hook is the backstop for wrapper paths (make / editor /
# IDE) whose top-level command this PreToolUse hook never sees.
set -uo pipefail

payload="$(cat)"
cmd="$(printf '%s' "$payload" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' \
  2>/dev/null || true)"
# Fallback: python3 absent (cmd empty) → match against the raw payload, not nothing.
hay="$cmd"; [ -z "$hay" ] && hay="$payload"

block() { echo "BLOCKED by disciplined-builder guard: $1" >&2; exit 2; }

# One secret pattern, used by both the commit gate and the push gate.
SECRET_RE='(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[A-Za-z0-9_-]{35}|[sr]k_live_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(api[_-]?key|secret|password|token)["'"'"' ]*[:=]["'"'"' ]*[A-Za-z0-9/+_-]{12,})'

# Resolve the git SUBCOMMAND accurately. A flags-only regex is not enough: git's global
# options can carry a SEPARATE value (`git -c core.pager=cat commit`, `git -C /path push`),
# and the value token doesn't start with `-`, so a `(-flag)*` pattern stops matching and
# the subcommand slips past. Parse properly, and keep a regex only for the no-python3 path.
subcmd="$(printf '%s' "$cmd" | python3 -c '
import shlex, sys
raw = sys.stdin.read()
try:
    t = shlex.split(raw)
except ValueError:
    sys.exit(0)
TAKES_VAL = {"-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
i = 0
while i < len(t):                       # find the git invocation (also `sudo git`, `/usr/bin/git`)
    if t[i] == "git" or t[i].endswith("/git"):
        i += 1
        break
    i += 1
else:
    sys.exit(0)
while i < len(t):                       # walk past global options to the subcommand
    a = t[i]
    if a in TAKES_VAL:
        i += 2
        continue
    if a.startswith("-"):
        i += 1
        continue
    print(a)
    break
' 2>/dev/null || true)"

# $1 = subcommand. True when the command is `git <subcommand>`.
is_git() {
  if [ -n "$subcmd" ]; then [ "$subcmd" = "$1" ]; return; fi
  # Unparsed (python3 absent) → generous regex over the raw payload; a false positive is
  # safe here, a miss is a bypass. Allows both `-flag` and a bare `key=value` (the `-c` value).
  printf '%s' "$hay" | grep -Eq "(^|[^[:alnum:]/])git([[:space:]]+(-[^[:space:]]+|[^[:space:]-][^[:space:]]*=[^[:space:]]*))*[[:space:]]+$1([^[:alnum:]]|\$)"
}

# --- commit gates ---
if is_git commit; then
  # secret-scan on the staged diff
  staged="$(git diff --cached 2>/dev/null || true)"
  if printf '%s' "$staged" | grep -Eiq "$SECRET_RE"; then
    block "possible secret in the staged diff (secret-scan). Remove it or use a placeholder before committing."
  fi

  # verify-before-commit: a set item must have a PASSING verdict on disk
  item="$(python3 -c 'import json; print(json.load(open(".workflow/state.json")).get("current_item") or "")' 2>/dev/null || true)"
  if [ -n "$item" ]; then
    verdict=".workflow/items/$item/verify-verdict.md"
    [ -f "$verdict" ] || block "item $item has no verify-verdict; run verify before committing."
    if grep -Eiq 'pass[^[:alnum:]]{1,8}false' "$verdict"; then
      block "item $item has a failing verify-verdict; run debug -> refine -> verify before committing."
    fi
  fi
fi

# --- push floor: never move a protected branch, never push a secret ---
if is_git push; then
  # The refspec cannot be read out of a raw JSON payload — refuse rather than guess.
  [ -n "$cmd" ] || block "cannot parse the push refspec (python3 unavailable); the protected-branch floor fails closed."

  # main/master are always protected and cannot be removed; config may only ADD to the set.
  protected="main master"
  extra="$(python3 - <<'PY' 2>/dev/null || true
import json
try:
    cfg = json.load(open(".workflow/config.json"))
    names = cfg.get("guard", {}).get("protected_branches", []) or []
    print(" ".join(str(n) for n in names))
except Exception:
    pass
PY
)"
  [ -n "$extra" ] && protected="$protected $extra"

  # --all / --mirror move every branch, protected ones included.
  if printf '%s' "$cmd" | grep -Eq '(^|[[:space:]])--(all|mirror)([[:space:]]|$)'; then
    block "git push --all/--mirror would move a protected branch ($protected). Push an explicit feature branch instead."
  fi

  # Resolve target branch(es): explicit refspecs win, else the upstream / current branch.
  targets="$(python3 - "$cmd" <<'PY' 2>/dev/null || true
import shlex, subprocess, sys
try:
    toks = shlex.split(sys.argv[1])
except ValueError:
    sys.exit(0)                      # unparseable -> emit nothing -> caller fails closed
if "push" not in toks:
    sys.exit(0)
rest = toks[toks.index("push") + 1:]
TAKES_VAL = {"--repo", "-o", "--push-option", "--receive-pack", "--exec"}
pos, skip = [], False
for t in rest:
    if skip:
        skip = False
        continue
    if t in TAKES_VAL:
        skip = True
        continue
    if t.startswith("-"):
        continue
    pos.append(t)
refspecs = pos[1:] if len(pos) > 1 else []
out = []
for r in refspecs:
    dst = r.split(":")[-1].lstrip("+")          # HEAD:main -> main ; +main -> main
    if dst.startswith("refs/heads/"):
        dst = dst[len("refs/heads/"):]
    out.append(dst)
if not out:                                     # bare `git push` -> push.default / upstream
    for argv in (["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
                 ["git", "branch", "--show-current"]):
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                out.append(r.stdout.strip().split("/")[-1])
                break
        except Exception:
            pass
print("\n".join(t for t in out if t))
PY
)"
  [ -n "$targets" ] || block "cannot resolve the push target branch; the protected-branch floor fails closed."

  while IFS= read -r t; do
    [ -n "$t" ] || continue
    for p in $protected; do
      if [ "$t" = "$p" ]; then
        block "the loop never pushes the protected branch '$t'. Push a feature branch — a human moves '$t'."
      fi
    done
  done <<EOF
$targets
EOF

  # Secret-scan the OUTGOING range: a commit can reach the branch by a path the
  # commit gate never saw (wrapper/IDE commit), so re-check what is actually leaving.
  upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
  if [ -n "$upstream" ]; then
    outgoing="$(git diff "$upstream"..HEAD 2>/dev/null || true)"
  else
    outgoing="$(git log -p --all --not --remotes 2>/dev/null || true)"
  fi
  if printf '%s' "$outgoing" | grep -Eiq "$SECRET_RE"; then
    block "possible secret in the outgoing commit range (push secret-scan). Rewrite the history carrying it before pushing."
  fi
fi

# --- obscured outward actions: force a direct invocation this guard can parse ---
outward='git[[:space:]]+push|gh[[:space:]]+(issue|pr|release|repo|api)|(npm|yarn|pnpm)[[:space:]]+(publish|run[[:space:]]+deploy)|(docker|cargo|gem|twine)[[:space:]]+(push|publish|upload)|(vercel|netlify|fly|flyctl|serverless|pulumi)[[:space:]]|terraform[[:space:]]+apply'
chain='&&|\|\||;|\$\(|`'
if printf '%s' "$hay" | grep -Eq "$outward" && printf '%s' "$hay" | grep -Eq "$chain"; then
  block "outward action hidden in a chain/subshell — run it as a single direct command so the outward gates (protected-branch + secret-scan floor, and any approval rule) can read it."
fi

exit 0
