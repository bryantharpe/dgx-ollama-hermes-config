#!/usr/bin/env bash
# Run Caddy and Hindsight (via upstream start-all.sh) as siblings.
# start-all.sh has its own SIGTERM trap and supervises hindsight-api +
# control-plane internally; we just need to keep Caddy alongside it and
# forward signals from Fly to both top-level children.

set -eu

term() {
    [ -n "${CADDY_PID:-}" ] && kill -TERM "$CADDY_PID" 2>/dev/null || true
    [ -n "${HINDSIGHT_PID:-}" ] && kill -TERM "$HINDSIGHT_PID" 2>/dev/null || true
}
trap term TERM INT

caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &
CADDY_PID=$!

/app/start-all.sh &
HINDSIGHT_PID=$!

# Returns when any child exits. Whichever dies first, kill the other so
# Fly restarts the whole machine instead of running half a stack.
wait -n
EXIT=$?
term
wait
exit "$EXIT"
