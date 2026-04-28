#!/bin/bash
# Push the repo's openclaw.json to the live gateway config and restart it.
#
# Repo-authoritative workflow: edit `openclaw/openclaw.json` (no real secrets,
# only `${VAR}` placeholders), keep secrets in `openclaw/.env`, run this.
#
# UI changes that the gateway writes back to ~/.openclaw/openclaw.json get
# clobbered on the next sync — that is the intent.
set -euo pipefail

cd "$(dirname "$0")"

REPO_CONFIG="./openclaw.json"
LIVE_CONFIG="${OPENCLAW_CONFIG_DIR:-/home/admin/.openclaw}/openclaw.json"

# Pull secret env vars from openclaw/.env (won't override anything already exported).
if [ -f .env ]; then
  set -a; . ./.env; set +a
fi

# Collect every ${VAR} placeholder the repo file references and verify each is set.
PLACEHOLDERS=$(grep -oE '\$\{[A-Z_][A-Z0-9_]*\}' "$REPO_CONFIG" | sort -u | tr -d '${}')
MISSING=()
for v in $PLACEHOLDERS; do
  [ -z "${!v:-}" ] && MISSING+=("$v")
done
if [ "${#MISSING[@]}" -gt 0 ]; then
  echo "ERROR: required env vars not set: ${MISSING[*]}" >&2
  echo "       add them to openclaw/.env or export before running." >&2
  exit 1
fi

# Backup current live config (timestamped, alongside the file).
STAMP=$(date +%Y%m%d-%H%M%S)
cp -p "$LIVE_CONFIG" "${LIVE_CONFIG}.bak.synccfg-${STAMP}"

# Substitute only the placeholders we found — never anything else.
ENVSUBST_VARS=$(printf '${%s} ' $PLACEHOLDERS)
envsubst "$ENVSUBST_VARS" < "$REPO_CONFIG" > "$LIVE_CONFIG"

# Validate the result before restarting anything.
if ! python3 -c "import json,sys; json.load(open('$LIVE_CONFIG'))" 2>/dev/null; then
  echo "ERROR: rendered config is not valid JSON. Restoring backup." >&2
  mv "${LIVE_CONFIG}.bak.synccfg-${STAMP}" "$LIVE_CONFIG"
  exit 1
fi

echo "✅ wrote $LIVE_CONFIG (backup: ${LIVE_CONFIG}.bak.synccfg-${STAMP})"

# Restart the gateway in-place. Force-recreate the proxy + dashboard because
# they share the gateway's network namespace via `network_mode: service:...`
# — restart-in-place keeps the gateway container ID stable, but if a previous
# manual recreate broke the netns ref, the dependents will need to be rebound.
docker compose restart openclaw-gateway
docker compose up -d --force-recreate openclaw-ollama-proxy openclaw-dashboard
echo "✅ openclaw-gateway restarted (+ proxy/dashboard recreated)"
