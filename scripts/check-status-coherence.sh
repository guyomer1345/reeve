#!/usr/bin/env bash
# Fail if a live guiding doc states a roster COUNT or a decision RANGE that has
# drifted from ground truth.
#
# Status is DERIVED data (a projection over "which files/decisions exist"). A
# hardcoded count/range copied into prose rots silently the moment the tree
# changes — the exact failure this gate exists to catch loudly. Companion to
# check-no-spec-refs.sh: that one keeps provenance OUT of the package; this one
# keeps status numbers HONEST in the docs.
#
# Scope: the roster count is authoritative in the roster table (list = count);
# the decision range is authoritative in the decision log (max heading). Prose
# elsewhere must MATCH or not state the number. The steady state is "no hardcoded
# count" — this gate then guards against a stale one creeping back.
#
# It does NOT scan 08-decision-log.md: that is the append-only historical record,
# where a past count/range was true when written.
set -uo pipefail
cd "$(dirname "$0")/.."

# --- ground truth (the product now lives under product/, the design docs under docs/design/) ---
skills=$(find product/skills -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l | tr -d ' ')
agents=$(find product/agents -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')
caps=$((skills + agents))
maxd=$(grep -hoE '^## D[0-9]+' docs/design/08-decision-log.md | grep -oE '[0-9]+' | sort -n | tail -1)

# --- live status-bearing docs (the append-only log is excluded) ---
docs=(docs/design/0[0-79]-*.md docs/design/1[01]-*.md README.md CLAUDE.md product/shared/*.md)

fail=0
flag() { echo "  $1" >&2; fail=1; }

# roster counts: "<N> skills" / "<N> agents" / "<N> capabilit(y|ies)[ files]"
# grep -o prints "FILE:LINE:MATCH"; strip to MATCH before pulling the number so
# the line-number prefix can't masquerade as the count.
while IFS= read -r hit; do
  [ -z "$hit" ] && continue
  match=${hit##*:}
  n=$(printf '%s' "$match" | grep -oE '[0-9]+' | head -1)
  case "$match" in
    *skill*)     [ "$n" = "$skills" ] || flag "$hit  (tree has $skills skills)";;
    *agent*)     [ "$n" = "$agents" ] || flag "$hit  (tree has $agents agents)";;
    *capabilit*) [ "$n" = "$caps" ]   || flag "$hit  (tree has $caps capabilities = $skills skills + $agents agents)";;
  esac
done < <(grep -rnoE '[0-9]+ (skills|agents|capabilit(y|ies)( files)?)' "${docs[@]}" 2>/dev/null || true)

# decision range: "D1–D<N>" upper bound must equal the log's max decision
while IFS= read -r hit; do
  [ -z "$hit" ] && continue
  upper=$(printf '%s' "${hit##*:}" | grep -oE 'D[0-9]+' | tail -1 | tr -d 'D')
  [ "$upper" = "$maxd" ] || flag "$hit  (log's max decision is D$maxd)"
done < <(grep -rnoE 'D1[-–—]D[0-9]+' "${docs[@]}" 2>/dev/null || true)

# ownership: the roadmap build-status tags (**[core]/[stageable]/[later]/[done]**)
# belong to 11-roadmap.md ALONE — "what's left / at what phase" has one owner. A
# bold status tag surfacing in any other doc = a second status source growing
# silently (the "new source in 30 chats" failure). Block it: a new source is
# adopted deliberately (declare its owner), never accreted. Bold-wrapped so prose
# like "[later] symbol" doesn't trip it.
while IFS= read -r hit; do
  [ -z "$hit" ] && continue
  case "$hit" in
    docs/design/11-roadmap.md:*) ;;  # the owner — allowed
    *) flag "$hit  (roadmap status tag outside its owner, docs/design/11-roadmap.md)";;
  esac
done < <(grep -rnoE '\*\*\[(core|stageable|later|done)[^]]*\]\*\*' "${docs[@]}" 2>/dev/null || true)

if [ "$fail" -ne 0 ]; then
  echo "BLOCKED: status count/range drift — the docs disagree with the tree (see below):" >&2
  echo "         status is derived; state 'the roster' / point at the source, or fix the number." >&2
  exit 1
fi
echo "OK: roster counts + decision range coherent ($skills skills + $agents agents; max D$maxd)"
