#!/usr/bin/env bash
# Restore helper for the restic B2 repo.
#
# Subcommands:
#   list                              list all snapshots
#   list <snapshot>                   list files within a snapshot
#   file <path> [snapshot]            restore one path to a /tmp scratch dir
#   volume <name> [snapshot]          restore a docker named volume in place
#   system [snapshot]                 full restore to / (interactive confirm)
#
# `snapshot` defaults to "latest". Use a short ID (e.g. 3dab37cc) to pin.

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# shellcheck source=./backup-env.sh
. "$HERE/backup-env.sh"

CMD="${1:-help}"

run_restic_with_retry() {
  local attempt rc
  for attempt in 1 2 3 4 5; do
    set +e
    sudo -E /usr/local/bin/restic "$@"
    rc=$?
    set -e
    if [[ $rc -eq 0 ]]; then return 0; fi
    echo "restic exit=$rc on attempt $attempt; sleeping 15s..." >&2
    sleep 15
  done
  return 1
}

case "$CMD" in
  list)
    if [[ $# -ge 2 ]]; then
      run_restic_with_retry --option b2.connections=4 ls "$2"
    else
      run_restic_with_retry --option b2.connections=4 snapshots
    fi
    ;;

  file)
    PATH_ARG="${2:-}"
    SNAP="${3:-latest}"
    if [[ -z "$PATH_ARG" ]]; then
      echo "usage: restore.sh file <path> [snapshot]" >&2; exit 1
    fi
    SCRATCH="/tmp/restic-restore-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$SCRATCH"
    echo "Restoring $PATH_ARG from snapshot $SNAP to $SCRATCH..."
    run_restic_with_retry --option b2.connections=4 restore "$SNAP" \
      --include "$PATH_ARG" --target "$SCRATCH"
    echo
    echo "Done. Files at: $SCRATCH$PATH_ARG"
    ;;

  volume)
    NAME="${2:-}"
    SNAP="${3:-latest}"
    if [[ -z "$NAME" ]]; then
      echo "usage: restore.sh volume <name> [snapshot]" >&2; exit 1
    fi
    VOL_PATH="/var/lib/docker/volumes/$NAME"
    cat <<EOF
About to restore $VOL_PATH from snapshot $SNAP, in place.
Existing contents at that path will be overwritten.
Stop any docker service that mounts this volume first.
EOF
    read -rp "Continue? (yes/NO): " ans
    [[ "$ans" == "yes" ]] || { echo "aborted"; exit 1; }
    run_restic_with_retry --option b2.connections=4 restore "$SNAP" \
      --include "$VOL_PATH" --target /
    echo "Restored. Restart any service that uses this volume."
    ;;

  system)
    SNAP="${2:-latest}"
    cat <<EOF
=== FULL SYSTEM RESTORE ===
This restores snapshot $SNAP to / (the entire root filesystem).
Existing files will be overwritten if present in the snapshot.
Intended for bare-metal recovery. NOT for routine ops.
EOF
    read -rp "Type YES (uppercase) to proceed: " ans
    [[ "$ans" == "YES" ]] || { echo "aborted"; exit 1; }
    run_restic_with_retry --option b2.connections=4 restore "$SNAP" --target /
    echo "System restore done. Reboot recommended."
    ;;

  ""|help|-h|--help)
    sed -n '2,11p' "$0" | sed 's|^# \{0,1\}||'
    ;;

  *)
    echo "unknown subcommand: $CMD" >&2
    "$0" help
    exit 1
    ;;
esac
