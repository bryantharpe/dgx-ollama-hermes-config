# scripts/

Helpers for the OpenClaw memory pipeline.

## The memory pipeline, in one picture

```
/new or /reset fires in a Nemo session
        │
        ▼
bundled session-memory hook  ──►  ~/.openclaw/workspace/memory/<date>-<slug>.md
        │                         (markdown, human-readable)
        ▼
workspace session-memory-embed hook  ──►  Hindsight (Fly.io) /v1/default/banks/bryan-default/memories
                                           └── async fact extraction via Cerebras Qwen 235B
                                           └── stored in Neon Postgres + pgvector
```

Hindsight does its own chunking and fact extraction, so the hook ships each
journal `.md` as one retain item with `update_mode: replace` (idempotent
upsert keyed by filename-derived `document_id`).

The workspace hook lives at
`~/.openclaw/workspace/hooks/session-memory-embed/{HOOK.md,handler.js}`.

## `backfill-hindsight-from-journal.mjs`

Backfills `~/.openclaw/workspace/memory/*.md` into Hindsight. Run manually for
a full rebuild or after wiping the bank.

```
# default: all .md files
set -a; . ~/.openclaw/.env; set +a
node backfill-hindsight-from-journal.mjs

# single file
node backfill-hindsight-from-journal.mjs --file /path/to/file.md

# wait for fact extraction inline (slower, useful for verification)
node backfill-hindsight-from-journal.mjs --sync
```

Required env (already in `~/.openclaw/.env` after the cutover):
- `HINDSIGHT_API_URL`
- `HINDSIGHT_API_TENANT_API_KEY`
- `HINDSIGHT_BANK_ID`

Idempotent: each file uses a stable `document_id` of
`openclaw-journal-<basename-without-md>` with `update_mode: replace`, so
Hindsight upserts cleanly on re-run.

After an async run, poll the worker until ops drain:

```
TOKEN="$HINDSIGHT_API_TENANT_API_KEY"
APP="$HINDSIGHT_API_URL"
curl -s -H "Authorization: Bearer $TOKEN" \
  "$APP/v1/default/banks/$HINDSIGHT_BANK_ID/operations?status=running" | jq
```

## Smoke-testing recall

Use the Hindsight recall endpoint directly (no separate verify script needed):

```
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "$APP/v1/default/banks/$HINDSIGHT_BANK_ID/memories/recall" \
  -d '{"query":"what outdoor projects am I planning?"}' | jq
```

## Disabling the hook

```
docker exec openclaw-gateway sh -c 'cd /app && node openclaw.mjs hooks disable session-memory-embed'
```

## Bank stats

```
curl -s -H "Authorization: Bearer $TOKEN" \
  "$APP/v1/default/banks/$HINDSIGHT_BANK_ID/stats" | jq
```

## Backups

- `~/.openclaw/openclaw.json.bak.pre-hindsight-<stamp>` — pre-cutover plugin config.
- `~/.openclaw/workspace/hooks/session-memory-embed/handler.js.bak.pre-hindsight-<stamp>` — original LanceDB writer.
- `~/.openclaw/memory/lancedb/` — last LanceDB store; preserved through the
  one-week hold per the Phase 3 decommission plan, then archived to
  `~/lancedb-pre-hindsight-<date>.tar.gz` and removed.
- `/home/admin/code/hermes-config/openclaw/docker-compose.yml.bak.pre-hindsight-<stamp>`
- `/home/admin/code/hermes-config/openclaw/.env.bak.pre-hindsight-<stamp>`

Rollback within the hold week: re-enable `memory-lancedb` plugin in
`~/.openclaw/openclaw.json`, restore `handler.js` from the timestamped backup,
`docker compose -f openclaw/docker-compose.yml restart openclaw-gateway`.

## Archived (pre-Hindsight)

These scripts are kept for historical reference and rollback only. They will
be removed after the Phase 3 decommission window:

- `backfill-lancedb-from-journal.mjs` — the LanceDB-era backfill.
- `verify-lancedb-recall.mjs` — old smoke-test for Ollama+LanceDB recall.
- `archive/openclaw-memory-sweep.sh` — wrapper invoking the workspace
  hook's `sweep.mjs` inside the gateway. Hindsight handles consolidation
  server-side, so the daily reconciliation is no longer needed.
- `archive/systemd/openclaw-memory-sweep.{service,timer}` — opt-in user
  timer for the daily 03:15 sweep, now disabled.
