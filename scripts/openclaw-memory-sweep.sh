#!/usr/bin/env bash
# Full reconcile of ~/.openclaw/workspace/memory/*.md into the memory-lancedb
# store. Safety net behind the session-memory-embed workspace hook — idempotent,
# safe to run on any cadence.
#
# Usage: ./openclaw-memory-sweep.sh
# Exit: non-zero if the gateway isn't running or the sweep script is missing.

set -euo pipefail

CONTAINER="${OPENCLAW_CONTAINER:-openclaw-gateway}"
SWEEP_PATH="/home/node/.openclaw/workspace/hooks/session-memory-embed/sweep.mjs"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "openclaw-memory-sweep: container '$CONTAINER' not running; skipping" >&2
  exit 0
fi

exec docker exec "$CONTAINER" sh -c "cd /app && node $SWEEP_PATH"
