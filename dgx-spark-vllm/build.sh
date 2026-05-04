#!/bin/bash
# build.sh — thin wrapper around scitrera's build-image.sh for our local
# vLLM 0.19.1-t5 image. Pre-flight checks, log capture, no Dockerfile fork.
#
# Usage:   ./build.sh              # build vllm-0.19.1-t5 (default)
#          ./build.sh <recipe>     # build a different recipe under recipes/
#          ./build.sh --no-cache   # forwarded to upstream build-image.sh
#          ./build.sh --dry-run    # show config without building
#
# Outputs:
#   - Image:  local/dgx-spark-vllm:0.19.1-t5-dev (per recipe IMAGE_TAG)
#   - Log:    build-logs/<recipe>-<timestamp>.log
#
# Pre-flight checks (abort with non-zero exit):
#   - upstream/ clone exists
#   - >= 60 GB free in /var/lib/docker
#   - DEV_BASE_IMAGE in recipe is reachable on Docker Hub
#
# See dgx-spark-vllm/RECIPE-NOTES.md for the upgrade plan and pin rationale.
# See dgx-spark-vllm/README.md for cleanup / rollback.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECIPES_DIR="${SCRIPT_DIR}/recipes"
LOGS_DIR="${SCRIPT_DIR}/build-logs"
UPSTREAM_BUILD="${SCRIPT_DIR}/upstream/container-build/build-image.sh"
MIN_FREE_GB=60

# ── Argument parsing ─────────────────────────────────────────────────────
RECIPE_NAME="vllm-0.19.1-t5"
PASSTHROUGH_ARGS=()
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-cache)
            PASSTHROUGH_ARGS+=("$1"); shift ;;
        -n|--dry-run)
            DRY_RUN=true
            PASSTHROUGH_ARGS+=("$1"); shift ;;
        -h|--help)
            grep -E '^#( |$)' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*)
            echo "Unknown option: $1" >&2; exit 1 ;;
        *)
            RECIPE_NAME="$1"; shift ;;
    esac
done

RECIPE_FILE="${RECIPES_DIR}/${RECIPE_NAME}.recipe"

# ── Pre-flight: upstream clone present? ──────────────────────────────────
if [[ ! -x "$UPSTREAM_BUILD" ]]; then
    echo "ERROR: upstream build script missing or not executable:" >&2
    echo "       $UPSTREAM_BUILD" >&2
    echo "Recover with one of:" >&2
    echo "  git clone --depth 50 https://github.com/scitrera/cuda-containers.git \\" >&2
    echo "      ${SCRIPT_DIR}/upstream" >&2
    echo "  # OR from the bundled snapshot:" >&2
    echo "  git clone ${SCRIPT_DIR}/backups/upstream-cuda-containers-*.bundle \\" >&2
    echo "      ${SCRIPT_DIR}/upstream" >&2
    exit 1
fi

# ── Pre-flight: recipe file present? ─────────────────────────────────────
if [[ ! -f "$RECIPE_FILE" ]]; then
    echo "ERROR: recipe not found: $RECIPE_FILE" >&2
    echo "Available recipes:" >&2
    ls -1 "${RECIPES_DIR}"/*.recipe 2>/dev/null | xargs -n1 basename | sed 's/^/  /' >&2
    exit 1
fi

# ── Pre-flight: disk space ───────────────────────────────────────────────
DOCKER_ROOT="$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || echo /var/lib/docker)"
FREE_GB=$(df -BG --output=avail "$DOCKER_ROOT" 2>/dev/null | tail -1 | tr -d 'G ' || echo 0)
if [[ "$FREE_GB" -lt "$MIN_FREE_GB" ]]; then
    echo "ERROR: only ${FREE_GB} GB free in $DOCKER_ROOT (need >= ${MIN_FREE_GB})." >&2
    echo "Free space with: docker builder prune -af && docker image prune -af" >&2
    exit 1
fi

# ── Pre-flight: base image reachable? ────────────────────────────────────
DEV_BASE=$(grep -E '^DEV_BASE_IMAGE=' "$RECIPE_FILE" | head -1 | cut -d= -f2-)
if [[ -n "$DEV_BASE" ]]; then
    if ! docker manifest inspect "$DEV_BASE" >/dev/null 2>&1; then
        echo "ERROR: cannot reach base image: $DEV_BASE" >&2
        echo "Check Docker Hub connectivity or recipe DEV_BASE_IMAGE pin." >&2
        exit 1
    fi
fi

# ── Build ────────────────────────────────────────────────────────────────
mkdir -p "$LOGS_DIR"
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG_FILE="${LOGS_DIR}/${RECIPE_NAME}-${TIMESTAMP}.log"

echo "=== build.sh ==="
echo "Recipe:   $RECIPE_FILE"
echo "Log:      $LOG_FILE"
echo "Free:     ${FREE_GB} GB in $DOCKER_ROOT"
echo "Base:     $DEV_BASE  (reachable)"
echo

# upstream/build-image.sh accepts an absolute recipe path as the first
# positional argument. Tee output so we get both live console + log file.
"$UPSTREAM_BUILD" "${PASSTHROUGH_ARGS[@]}" "$RECIPE_FILE" 2>&1 | tee "$LOG_FILE"

if $DRY_RUN; then
    echo
    echo "[dry-run] No image was built."
    exit 0
fi

# ── Post-build: confirm image landed ─────────────────────────────────────
IMAGE_TAG=$(grep -E '^IMAGE_TAG=' "$RECIPE_FILE" | head -1 | cut -d= -f2-)
if docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
    echo
    echo "=== Build complete ==="
    echo "Image:    $IMAGE_TAG"
    docker image inspect "$IMAGE_TAG" --format \
        'Created:  {{.Created}}{{println}}Size:     {{.Size}} bytes'
    echo "Log:      $LOG_FILE"
else
    echo "ERROR: build script returned 0 but image not found: $IMAGE_TAG" >&2
    exit 1
fi
