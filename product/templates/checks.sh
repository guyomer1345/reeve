#!/usr/bin/env bash
# .workflow/checks.sh — the per-item mechanical gate.
#
# SHIPPED FIXED. /start copies this file VERBATIM from templates/checks.sh; the only
# per-project input is .workflow/checks.env, a data file /start writes from stack
# detection. Do NOT hand-edit this file — re-running /start (or a plugin update)
# re-copies it, and any local edit is lost. Per-project variation belongs in checks.env.
#
# Two modes:
#   --fix [files...]  zero-judgment fixers (formatter + linter --fix) over the passed
#                     files only. The commit skill scopes these to the item's staged
#                     files — never a repo-wide sweep. Not a gate (always exits 0); the
#                     authoritative check is --check, re-run afterwards.
#   --check           the gate: format-check + lint + typecheck + test (whichever the
#                     stack defines), then the plan-coverage gates over EVERY open item's
#                     promises.json. Exits non-zero on any drift — used by the git
#                     pre-commit hook and by the commit skill after --fix.
#
# checks.env contract (all optional; empty/unset = skip that check):
#   FMT_FIX   formatter, write mode   — a command PREFIX; the staged file list is appended
#   LINT_FIX  linter, --fix mode      — a command PREFIX; the staged file list is appended
#   FMT_CHECK formatter, check mode   — runs repo-wide (carries its own path, e.g. `.`)
#   LINT      linter, check mode      — runs repo-wide
#   TYPECHECK typechecker             — runs repo-wide (omit for languages without one)
#   TEST      test runner             — runs repo-wide
#   STACK_GATE_NONE  a REASON string — the third stack-gate state (see --check below).
#                    Non-empty means the executable stack gate is off BY DECLARATION.
# The coverage gates below are stack-AGNOSTIC (they read only .workflow/) and ship fixed
# in .claude/scripts/ — they are never part of checks.env.
#
# THREE stack-gate states, not two. `unset` and `deliberately none` are different facts and
# the runner must not conflate them:
#   1. WIRED           — one or more of FMT_CHECK/LINT/TYPECHECK/TEST set. Normal.
#   2. NOT YET WIRED   — all unset, STACK_GATE_NONE unset. Fine on an empty bootstrap tree;
#                        BLOCKS the moment source exists under project_root (the fail-closed
#                        backstop below), because forgetting to wire it is the silent-defeat
#                        state and must be loud.
#   3. DECLARED NONE   — STACK_GATE_NONE carries a reason. The runner then executes NOTHING
#                        out of checks.env, in either mode, and says so on every run. This
#                        exists for a tree whose code must never be executed on this machine
#                        (checks.env is `source`d and the fixers run through `eval`, so an
#                        adopted `TEST=` is arbitrary code execution). Refusal is structural,
#                        not remembered: if something later re-fills checks.env, the
#                        declaration still wins and the conflict is REPORTED rather than
#                        silently obeyed. The stack-agnostic coverage gates always still run.
set -uo pipefail

MODE="${1:-}"; shift 2>/dev/null || true
[ -n "$MODE" ] || { echo "usage: checks.sh --fix [files...] | --check" >&2; exit 2; }

# Per-project stack commands (data written by /start). Sourced, so it is trusted project
# config at the same level as this file — it is committed alongside it.
[ -f .workflow/checks.env ] && . .workflow/checks.env

SCRIPTS=".claude/scripts"
fail=0

# State 3 (see the header): announce the declaration and name anything it is REFUSING.
# Announcing on every run is the point — a disarmed executable gate that says nothing is
# indistinguishable from one nobody wired, which is the confusion this state exists to end.
declared_none() {
  echo "+ stack gate: DECLARED NONE — $STACK_GATE_NONE" >&2
  echo "  (nothing from checks.env is executed, by declaration)" >&2
  local v refused=""
  for v in FMT_FIX LINT_FIX FMT_CHECK LINT TYPECHECK TEST; do
    [ -n "${!v:-}" ] && refused="$refused $v"
  done
  [ -n "$refused" ] && {
    echo "  REFUSED — set in checks.env despite the declaration, NOT executed:$refused" >&2
    echo "  Something re-wired checks.env (a re-run of /start's stack adoption?). Clear those" >&2
    echo "  values or drop STACK_GATE_NONE — the declaration wins either way." >&2
  }
  return 0
}

case "$MODE" in
  --fix)
    # Fixers run only over the passed (staged) files, never repo-wide. FMT_FIX/LINT_FIX are
    # prefixes; `"$@"` appends the file list, each token quoted. Best-effort — --check gates.
    # Each runs in a SUBSHELL so a `cd`-ing command cannot leak its CWD into this runner.
    if [ -n "${STACK_GATE_NONE:-}" ]; then
      declared_none            # refuse the fixers too — they are `eval`'d the same way
    elif [ "$#" -gt 0 ]; then
      [ -n "${FMT_FIX:-}" ]  && { echo "+ $FMT_FIX $*" >&2;  ( eval "$FMT_FIX \"\$@\"" )  || true; }
      [ -n "${LINT_FIX:-}" ] && { echo "+ $LINT_FIX $*" >&2; ( eval "$LINT_FIX \"\$@\"" ) || true; }
    fi
    exit 0
    ;;
  --check)
    # State 3 short-circuits BOTH the backstop and the stack commands. It has to take the
    # backstop with it: the backstop's whole premise is that an empty checks.env means someone
    # FORGOT, and here it means someone DECIDED — blocking on a declared state would deadlock
    # the first commit in a tree that is never allowed to wire a gate at all.
    if [ -n "${STACK_GATE_NONE:-}" ]; then
      declared_none
    else
    # Fail-CLOSED stack-gate backstop: source under project_root with NO stack check wired is the
    # silent-defeat state. A greenfield stack locks in decision-engineer, but if nothing then fills
    # checks.env (the stack-wiring step at tech_stack lock), --check would run ONLY the coverage
    # gates and a failing test would wave through the commit. So: if no --check stack command is set
    # AND the product tree already holds source, block. The positive path (filling checks.env at
    # lock) makes the common case work; THIS makes forgetting it loud instead of silent. Skips
    # cleanly on the empty bootstrap tree (no source yet) and once checks.env is wired.
    #
    # `git ls-files -- "$proot"` REQUIRES project_root to be inside this repo — an external
    # absolute path makes git exit 128 with empty stdout and the backstop silently no-ops. That
    # is not a latent bug but the reason org mode keeps the brain and the code in ONE repo
    # (project_root ".") instead of pointing at a tree elsewhere on the machine.
    if [ -z "${FMT_CHECK:-}${LINT:-}${TYPECHECK:-}${TEST:-}" ]; then
      proot="$(python3 -c 'import json; print(json.load(open(".workflow/config.json")).get("project_root") or ".")' 2>/dev/null || echo .)"
      if git ls-files -- "$proot" 2>/dev/null | grep -Eiq '\.(py|pyi|js|jsx|ts|tsx|mjs|cjs|go|java|cs|rb|rs|c|cc|cpp|cxx|h|hpp|hh|php|swift|kt|kts|scala|m|mm|clj|ex|exs|dart|lua|sh)$'; then
        echo "BLOCKED: source under '$proot' but .workflow/checks.env wires no stack gate" >&2
        echo "  (FMT_CHECK/LINT/TYPECHECK/TEST all unset). The stack must be wired when tech_stack" >&2
        echo "  locks: specialize rules + fill checks.env (the stack-wiring step — /start step 5)." >&2
        echo "  If this tree's code must NEVER be executed here, that is the third state, not this" >&2
        echo "  one: set STACK_GATE_NONE=\"<reason>\" in checks.env (coverage gates keep running)." >&2
        fail=1
      fi
    fi

    # Each stack command runs in a SUBSHELL. This is load-bearing, not tidiness: a natural
    # command like `cd project && pytest` would otherwise `cd` THIS shell, and the coverage-gate
    # loop below (paths relative to CWD) would then find zero items and SILENTLY skip every gate.
    [ -n "${FMT_CHECK:-}" ] && { echo "+ $FMT_CHECK" >&2; ( eval "$FMT_CHECK" ) || fail=1; }
    [ -n "${LINT:-}" ]      && { echo "+ $LINT" >&2;      ( eval "$LINT" )      || fail=1; }
    [ -n "${TYPECHECK:-}" ] && { echo "+ $TYPECHECK" >&2; ( eval "$TYPECHECK" ) || fail=1; }
    [ -n "${TEST:-}" ]      && { echo "+ $TEST" >&2;      ( eval "$TEST" )      || fail=1; }
    fi

    # Plan-coverage gates over every OPEN item (its dir is committed while open). Stack-
    # agnostic, shipped fixed. A missing promises.json means the planner has not written one
    # yet — skip it; a malformed one fails loudly (a broken manifest SHOULD block a commit).
    shopt -s nullglob
    for m in .workflow/items/*/promises.json; do
      echo "+ coverage gates: $m" >&2
      python3 "$SCRIPTS/check_promise_coverage.py"   "$m" || fail=1
      python3 "$SCRIPTS/check_criterion_discharge.py" "$m" || fail=1
      python3 "$SCRIPTS/check_decision_coverage.py"   "$m" || fail=1
    done

    # Chain-forecast gates over every committed forecast. Two lints because they settle
    # two different facts (one owner each): the GRAPH half asks whether every event names
    # a real loop.md node — the property that keeps the forecast a reading of the routing
    # graph rather than a second one — and the LIFECYCLE half checks shape, the required
    # horizon, and the names-only invariant that is the whole reason a forecast is safe to
    # commit. Both belong on the commit gate rather than only in the skill: the record is
    # committed, so a malformed one would otherwise enter history unchallenged.
    for fc in .workflow/forecasts/*.json; do
      echo "+ forecast gates: $fc" >&2
      python3 "$SCRIPTS/check_contracts.py" --forecast "$fc" --loop .workflow/loop.md || fail=1
      python3 "$SCRIPTS/forecast.py" lint "$fc" || fail=1
    done

    # The context-budget gate. It belongs on the commit gate rather than only on a schedule
    # because it is cheap, decidable and always-whole — it reads file SIZES, not content, so
    # running it every time costs nothing and there is no partial-scan question to get wrong.
    # HARD tier only: the advisory tier schedules a trim as a maintenance item, and failing a
    # commit over an advisory is how a gate becomes something people route around.
    echo "+ doc budget" >&2
    python3 "$SCRIPTS/check_doc_budget.py" --project-root . || fail=1

    exit "$fail"
    ;;
  *)
    echo "usage: checks.sh --fix [files...] | --check" >&2; exit 2
    ;;
esac
