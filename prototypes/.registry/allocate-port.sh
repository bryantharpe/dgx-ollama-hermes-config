#!/usr/bin/env bash
# Allocate (or return existing) host port for a prototype slug.
# Pool: 9000-9099. Usage: allocate-port.sh <slug>
set -euo pipefail

SLUG="${1:?usage: allocate-port.sh <slug>}"
REG_DIR="$(cd "$(dirname "$0")" && pwd)"
PORTS_FILE="${REG_DIR}/ports.json"
LOCK_FILE="${REG_DIR}/.lock"
POOL_START=9000
POOL_END=9099

exec 9>"$LOCK_FILE"
flock 9

[[ -s "$PORTS_FILE" ]] || echo '{}' > "$PORTS_FILE"

existing=$(jq -r --arg s "$SLUG" '.[$s] // empty' "$PORTS_FILE")
if [[ -n "$existing" ]]; then
  echo "$existing"
  exit 0
fi

used=$(jq -r '[.[]] | join(" ")' "$PORTS_FILE")
for port in $(seq "$POOL_START" "$POOL_END"); do
  if ! grep -qw "$port" <<<"$used"; then
    tmp=$(mktemp)
    jq --arg s "$SLUG" --argjson p "$port" '.[$s] = $p' "$PORTS_FILE" > "$tmp"
    mv "$tmp" "$PORTS_FILE"
    echo "$port"
    exit 0
  fi
done

echo "no free ports in ${POOL_START}-${POOL_END}" >&2
exit 1
