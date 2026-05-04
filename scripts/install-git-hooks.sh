#!/usr/bin/env bash
# Install repo-local git hooks. Idempotent. Run after cloning fresh.
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_SRC="$REPO_ROOT/scripts/git-hooks"
HOOKS_DST="$REPO_ROOT/.git/hooks"

if [ ! -d "$HOOKS_SRC" ]; then
  echo "FATAL: $HOOKS_SRC does not exist"
  exit 1
fi

install -d "$HOOKS_DST"
for src in "$HOOKS_SRC"/*; do
  [ -f "$src" ] || continue
  name="$(basename "$src")"
  install -m 755 "$src" "$HOOKS_DST/$name"
  echo "installed: $HOOKS_DST/$name"
done
