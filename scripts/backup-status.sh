#!/usr/bin/env bash
# One-shot status view for the hermes off-host backup.
#
# Read-only — safe to run anytime, including during a backup.
# Default mode is fast (no big repo queries). Use --full to also fetch
# total repo size from B2 (slower; can take 30s+ on first call).
#
# Usage: scripts/backup-status.sh [--full]

set -uo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(dirname "$HERE")
FULL=0
[ "${1:-}" = "--full" ] && FULL=1

# shellcheck source=./backup-env.sh
. "$HERE/backup-env.sh"

bold() { printf '\n\033[1m%s\033[0m\n' "$*"; }

# Run a restic command via sudo with a timeout + one retry.
# We use sudo -E because the local cache at ~/.cache/restic is owned by root
# (backup.sh runs restic as root via the NOPASSWD entry). Mixing admin and
# root invocations against the same cache produces "permission denied"
# errors. Standardizing on sudo -E gives consistent cache ownership.
# Args: TIMEOUT_SEC restic_args...
restic_q() {
  local t=$1; shift
  local out rc
  for _ in 1 2; do
    out=$(timeout "$t" sudo -E /usr/local/bin/restic --no-lock --option b2.connections=4 "$@" 2>&1); rc=$?
    [ $rc -eq 0 ] && { echo "$out"; return 0; }
  done
  echo "(restic failed: $out)" >&2
  return $rc
}

bold "Schedule"
systemctl list-timers 'hermes-backup*' --no-pager 2>/dev/null \
  | grep -E 'NEXT|hermes-backup|^[0-9]+ timers' | head -5

bold "Most recent snapshots (restic — ground truth for 'did it actually run')"
snap_json=$(restic_q 60 snapshots --json) || snap_json='[]'
echo "$snap_json" | jq -r '
  if length == 0 then "  (no snapshots yet)"
  else (.[-5:] | reverse | .[] |
    "  " + .short_id + "  " +
    (.time | sub("T"; " ") | sub("\\..*"; "")) + "  " +
    "host=" + .hostname + "  tags=" + (.tags | join(",")))
  end'

bold "Last attempted service runs (systemd may show success for trivial no-ops)"
for svc in hermes-backup hermes-backup-check hermes-backup-prune; do
  result=$(systemctl show "$svc.service" -p Result --value 2>/dev/null)
  exec_start=$(systemctl show "$svc.service" -p ExecMainStartTimestamp --value 2>/dev/null)
  active=$(systemctl show "$svc.service" -p ActiveState --value 2>/dev/null)
  [ -z "$exec_start" ] && exec_start='(never)'
  [ -z "$result" ] && result='(none)'
  printf '  %-32s active=%-10s result=%-10s started=%s\n' \
    "$svc.service" "$active" "$result" "$exec_start"
done

bold "Recent log (last 10 lines of .backup.log)"
log="$REPO_ROOT/.backup.log"
if [ -f "$log" ]; then
  tail -10 "$log" | sed 's/^/  /'
else
  echo "  (no log yet at $log)"
fi

if [ $FULL -eq 1 ]; then
  bold "Repo size (--full; slower)"
  stats=$(restic_q 90 stats --mode raw-data --json)
  if [ -n "$stats" ] && echo "$stats" | jq -e . >/dev/null 2>&1; then
    bytes=$(echo "$stats" | jq -r '.total_size // 0')
    files=$(echo "$stats" | jq -r '.total_file_count // 0')
    gib=$(awk -v b="$bytes" 'BEGIN{printf "%.2f", b/1024/1024/1024}')
    printf '  raw_data=%s GiB  files=%s\n' "$gib" "$files"
  else
    echo "  (couldn't fetch stats — try again in a minute)"
  fi
fi

bold "Common ops"
cat <<'EOF'
  scripts/backup-status.sh --full          this report + repo size (slower)
  systemctl list-timers 'hermes-backup*'   raw timer schedule
  journalctl -u hermes-backup.service -f   follow a running run
  scripts/backup.sh                        manual ad-hoc backup
  scripts/restore.sh help                  list/file/volume/system restore
EOF
