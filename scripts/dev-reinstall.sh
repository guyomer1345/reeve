#!/usr/bin/env bash
# Reinstall THIS working tree as the locally-installed plugin, at HEAD.
#
# Meta-only tooling — never ships. It exists because of a measured failure, not a
# preference. Installing a plugin COPIES `product/` into
# `~/.claude/plugins/cache/<plugin>/<version>/`; it is a snapshot, not a live link.
# `claude plugin update` compares VERSIONS, and this package's version moves once per
# release, not once per commit — so while the package is being built, `update` is a
# no-op that reports "already at the latest version" over an install that is dozens of
# commits behind. D151 measured exactly that: 12 commits and 17 shipped files stale,
# including the SessionStart rehydrate, on the machine the package was being tested on.
#
# The roadmap already prescribed "force-reinstall before you drive" as a manual step,
# and the drive is the proof the manual step did not hold. A documented step nobody runs
# is not a control. This is the same rule the product applies to itself, applied to the
# workflow that builds it.
#
# Run it before any drive of a test project. Fast, idempotent, and it prints what the
# install now contains so a stale one is visible rather than assumed.
#
#   scripts/dev-reinstall.sh
#
# This fixes the maintainer's own loop, where the fix must be that the version is
# IRRELEVANT. A real installed user has no working tree to reinstall from.
#
# The D151 story above is now HISTORY, not the live mechanism (D164, built): `version` is
# DELETED from plugin.json, so the platform keys delivery on the commit SHA and `claude
# plugin update` is no longer a no-op over changed content. What replaced the version-bump
# plan is a two-hop detector on the SessionStart hook, which tells an install it is stale —
# both audiences share it, with different anchors. This script keeps its own job (reinstall
# from the working tree, which the SHA key cannot cover because the install copies the
# WORKING TREE and a dirty tree has no commit) and now also prunes the cache, because SHA
# versioning abandons a ~2.4MB dir per update and nothing reclaims it. See the tail.
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
plugin="dev-autonomous-workflow"

if ! command -v claude >/dev/null 2>&1; then
  echo "claude is not on PATH — nothing to reinstall into" >&2
  exit 1
fi

head_sha="$(git -C "$root" rev-parse --short HEAD 2>/dev/null || echo "?")"
dirty=""
if ! git -C "$root" diff --quiet 2>/dev/null || ! git -C "$root" diff --cached --quiet 2>/dev/null; then
  dirty=" (+ uncommitted changes — the install copies the WORKING TREE, not HEAD)"
fi
echo "==> reinstalling $plugin from $root @ $head_sha$dirty"

# The marketplace entry may already point here from a previous run; `add` is what picks
# up a moved/renamed checkout, and re-adding an identical one is harmless.
claude plugin marketplace add "$root" >/dev/null 2>&1
claude plugin marketplace update "$plugin" >/dev/null 2>&1

# Uninstall first, deliberately. `install` over an existing install is the path that
# short-circuits on a matching version — the exact no-op this script exists to defeat.
claude plugin uninstall "$plugin" >/dev/null 2>&1

# ...and drop this SHA's cache dir, because uninstall does not. MEASURED, not assumed: with
# the cache keyed on the commit SHA (`version` is gone from plugin.json), a SECOND reinstall
# at the same HEAD reuses the extracted dir and silently ships the FIRST run's bytes — so a
# drive kept exercising a stale package while the working tree had moved on. That is the
# D151 staleness failure returning through the new key, and it defeats the one mechanism
# this phase's exit test depends on. The whole point of this script is that a dirty working
# tree has no SHA of its own; the cache must therefore be re-extracted every single time.
cache_root_pre="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/cache"
head_dir="$(git -C "$root" rev-parse HEAD 2>/dev/null | cut -c1-12)"
if [ -n "$head_dir" ]; then
  for stale in "$cache_root_pre"/*/"$plugin"/"$head_dir"; do
    [ -d "$stale" ] && rm -rf -- "$stale" && echo "    dropped stale cache for $head_dir"
  done
fi
if ! claude plugin install "$plugin"; then
  echo "install failed — run 'claude plugin marketplace add $root' by hand to see why" >&2
  exit 1
fi

echo "==> installed. Roster the install now carries:"
claude plugin list 2>/dev/null | grep -A 6 "$plugin" || true
echo "==> source tree was $root @ $head_sha$dirty"

# ---- keep-2 cache prune (D164 call 4) -------------------------------------------------
# With `version` deleted from plugin.json the cache key is the COMMIT SHA, so every update
# extracts into a NEW directory (~2.4MB) and abandons the previous one. Claude Code has no
# retention policy at all, and `claude plugin uninstall` reclaims nothing either — both
# measured on 2.1.220. A released user updates rarely enough that this is negligible; the
# maintainer reinstalls many times a day, which is why the prune lives here, in meta-only
# tooling, and is never shipped. A plugin deleting siblings of itself inside the CLI's own
# cache would be outside our ship boundary and could yank a directory from under a live
# session (D164 rejected exactly that).
#
# Keep TWO, not one. `claude plugin install` prints "Restart to apply changes", so a
# session that STARTED before this reinstall is still executing out of the previous
# directory; deleting it would break a session that is running right now.
cache_root="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/cache"
live="$(python3 - "$plugin" <<'PY' 2>/dev/null || true
import json, os, sys
name = sys.argv[1]
cfg = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
try:
    reg = json.load(open(os.path.join(cfg, "plugins", "installed_plugins.json")))
except Exception:
    sys.exit(0)
for key, entries in (reg.get("plugins") or {}).items():
    if str(key).partition("@")[0] != name:
        continue
    for e in entries or []:
        p = (e or {}).get("installPath")
        if p:
            print(os.path.realpath(p))
PY
)"

pruned=0
for group in "$cache_root"/*/"$plugin"; do
  [ -d "$group" ] || continue
  # Newest-first by mtime; everything past the second is abandoned. `ls -dt` rather than
  # `find -printf` so this is not GNU-find-only.
  while IFS= read -r dir; do
    [ -n "$dir" ] || continue
    dir="${dir%/}"
    [ -d "$dir" ] || continue
    case "$live" in *"$(realpath "$dir" 2>/dev/null || echo "$dir")"*)
      echo "    keeping (live install)  ${dir##*/}"; continue ;;
    esac
    size="$(du -sh "$dir" 2>/dev/null | cut -f1)"
    rm -rf -- "$dir" && { echo "    pruned  ${dir##*/}  (${size:-?})"; pruned=$((pruned + 1)); }
  done <<< "$(ls -1dt "$group"/*/ 2>/dev/null | tail -n +3)"
done
if [ "$pruned" -gt 0 ]; then
  echo "==> cache prune: removed $pruned abandoned install dir(s), kept the 2 newest"
else
  echo "==> cache prune: nothing to reclaim (<= 2 install dirs)"
fi
