#!/usr/bin/env bash
# Daily off-host backup driver.
# Loads .env.backup, runs `restic backup` with the excludes list, retries on
# transient B2 errors, appends to .backup.log. Designed for either ad-hoc or
# systemd-timer invocation.
#
# Source paths include root-only directories (/etc, /var/lib/docker/volumes,
# /root) so the run uses `sudo -E /usr/local/bin/restic`. The
# /etc/sudoers.d/restic-backup rule grants this without a password.
#
# Usage: scripts/backup.sh [--dry-run]

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(dirname "$HERE")

# shellcheck source=./backup-env.sh
. "$HERE/backup-env.sh"

LOG_FILE="$REPO_ROOT/.backup.log"
EXCLUDES="$HERE/excludes.txt"

SOURCES=(
  /home
  /etc
  /usr/local
  /root
  /var/lib/docker/volumes
)

DRY_RUN=()
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=(--dry-run)
fi

ts() { date -Iseconds; }
log() { printf '[%s] %s\n' "$(ts)" "$*" | tee -a "$LOG_FILE" >&2; }

run_restic_with_retry() {
  local attempt rc
  for attempt in 1 2 3 4 5; do
    set +e
    sudo -E /usr/local/bin/restic "$@" 2>&1 | tee -a "$LOG_FILE"
    rc=${PIPESTATUS[0]}
    set -e
    if [[ $rc -eq 0 ]]; then
      return 0
    fi
    log "restic exit=$rc on attempt $attempt; sleeping 15s before retry"
    sleep 15
  done
  log "restic failed after 5 attempts; giving up"
  return 1
}

log "=== backup start ${DRY_RUN[*]} ==="
log "host=$(hostname) user=$(whoami) repo=$RESTIC_REPOSITORY"

run_restic_with_retry backup \
  "${DRY_RUN[@]}" \
  --verbose=2 \
  --tag auto \
  --tag "host=$(hostname)" \
  --tag "$(date +%Y-%m-%d)" \
  --exclude-file "$EXCLUDES" \
  --exclude-caches \
  --option b2.connections=4 \
  "${SOURCES[@]}"

log "=== backup end ==="
