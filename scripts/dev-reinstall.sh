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
# SUPERSEDED (D164): the released-user half is NOT a version bump plus a gate refusing an
# un-bumped release — that plan is dropped. `version` is DELETED from plugin.json so the
# platform keys delivery on the commit SHA, and a two-hop detector on the SessionStart
# hook tells an install it is stale. Both audiences now share that detector, with
# different anchors. This script keeps its own job (reinstall from the working tree) and
# gains a keep-2 cache prune at build, because SHA versioning abandons a ~2.4MB cache dir
# per update and nothing — not even `claude plugin uninstall` — reclaims it.
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
if ! claude plugin install "$plugin"; then
  echo "install failed — run 'claude plugin marketplace add $root' by hand to see why" >&2
  exit 1
fi

echo "==> installed. Roster the install now carries:"
claude plugin list 2>/dev/null | grep -A 6 "$plugin" || true
echo "==> source tree was $root @ $head_sha$dirty"
