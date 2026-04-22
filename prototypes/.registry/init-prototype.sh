#!/usr/bin/env bash
# Seed a new prototype from the _template skeleton and allocate a host port.
#
# Safe to re-run. Idempotency semantics:
#   - Skeleton files (Dockerfile, docker-compose.yml, start.sh, .dockerignore,
#     .gitignore, and the three __init__.py files) are ALWAYS force-overwritten
#     from the template — they are correct-by-construction and must never
#     drift. This converges stale/broken copies from prior failed runs.
#   - Feature files (src/server/main.py, src/server/api.py, src/database/*.sql,
#     src/database/seed.py, src/frontend/**, requirements.txt) are preserved
#     if they already exist; missing ones are filled in from the template.
#   - Port allocation reuses the prior entry for the same slug.
#
#   With --reset, the target directory is wiped first and everything is
#   re-seeded from the template. Use this to recover from a badly-broken
#   prior build.
#
# Usage: init-prototype.sh [--reset] <slug>
# Prints the allocated host port on stdout.
set -euo pipefail

RESET=false
if [[ "${1:-}" == "--reset" ]]; then
  RESET=true
  shift
fi

SLUG="${1:?usage: $0 [--reset] <slug>}"
case "$SLUG" in
  _*|.*|"")
    echo "ERROR: slug must not start with '_' or '.'" >&2
    exit 64
    ;;
esac

REG_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$REG_DIR/.." && pwd)"
TEMPLATE="$ROOT/_template"
TARGET="$ROOT/$SLUG"

[[ -d "$TEMPLATE" ]] || { echo "ERROR: template not found at $TEMPLATE" >&2; exit 66; }

FRESH_CREATE=false
if [[ ! -d "$TARGET" ]]; then
  FRESH_CREATE=true
fi

if $RESET && [[ -d "$TARGET" ]]; then
  echo "--reset: removing $TARGET" >&2
  rm -rf "$TARGET"
  FRESH_CREATE=true
fi

mkdir -p "$TARGET"
# data/ is a runtime volume; Docker may have already created it as root-owned.
# Ensure it exists but never copy contents into it (would hit EACCES).
mkdir -p "$TARGET/data"

# Fill in any missing files from template (preserves existing feature edits).
# find + per-file test is portable and handles EACCES gracefully — no reliance
# on `cp -n` (which triggers a GNU deprecation warning) or bulk `cp -r`
# (which descends into root-owned data/).
while IFS= read -r rel; do
  src="$TEMPLATE/${rel#./}"
  dst="$TARGET/${rel#./}"
  if [[ ! -e "$dst" ]]; then
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
  fi
done < <(cd "$TEMPLATE" && find . -type f -not -path "./data/*")

# Strip placeholder README on fresh creates — build agent writes its own.
if $FRESH_CREATE; then
  rm -f "$TARGET/README.md"
fi

# ALWAYS force-overwrite skeleton files. These are correct-by-construction
# and should never drift. If Hermes (or a prior failed build) rewrote them,
# this converges them back to the template version. Feature files are not
# touched.
SKELETON_FILES=(
  "Dockerfile"
  "docker-compose.yml"
  "start.sh"
  ".dockerignore"
  ".gitignore"
  "src/__init__.py"
  "src/server/__init__.py"
  "src/database/__init__.py"
)
for f in "${SKELETON_FILES[@]}"; do
  mkdir -p "$(dirname "$TARGET/$f")"
  cp -f "$TEMPLATE/$f" "$TARGET/$f"
done

PORT=$("$REG_DIR/allocate-port.sh" "$SLUG")

cat > "$TARGET/.env" <<EOF
PROTOTYPE_NAME=$SLUG
PROTOTYPE_PORT=$PORT
EOF

echo "$PORT"
