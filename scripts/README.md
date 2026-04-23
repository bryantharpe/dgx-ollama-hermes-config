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
workspace session-memory-embed hook  ──►  ~/.openclaw/memory/lancedb (LanceDB)
                                           └── via Ollama nomic-embed-text
```

The workspace hook lives at
`~/.openclaw/workspace/hooks/session-memory-embed/{HOOK.md,handler.js,sweep.mjs}`.

## `backfill-lancedb-from-journal.mjs`

Ingests the journal into LanceDB. Run manually when you want a full rebuild.

```
# default: all .md files in ~/.openclaw/workspace/memory
node backfill-lancedb-from-journal.mjs

# single file
node backfill-lancedb-from-journal.mjs --file /path/to/file.md
```

Must run inside the openclaw-gateway container (needs `/app/node_modules`):

```
docker cp backfill-lancedb-from-journal.mjs openclaw-gateway:/app/_bf.mjs
docker exec openclaw-gateway sh -c 'cd /app && node _bf.mjs'
docker exec openclaw-gateway rm /app/_bf.mjs
```

Idempotent: per-file `delete WHERE text LIKE '[journal:<basename>#%'` before
insert, so re-runs don't duplicate.

## `verify-lancedb-recall.mjs`

Runs a few test queries and prints the top-3 hits per query. Sanity check that
recall is working.

```
docker cp verify-lancedb-recall.mjs openclaw-gateway:/app/_v.mjs
docker exec openclaw-gateway sh -c 'cd /app && node _v.mjs "my query"'
docker exec openclaw-gateway rm /app/_v.mjs
```

## `openclaw-memory-sweep.sh`

Wrapper that invokes the workspace hook's `sweep.mjs` inside the gateway
container. Idempotent; exits quietly if the container isn't running.

Enable the opt-in systemd timer (daily 03:15 sweep) to heal from any missed
hook fires:

```
cp scripts/systemd/openclaw-memory-sweep.* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now openclaw-memory-sweep.timer
systemctl --user list-timers openclaw-memory-sweep.timer
```

If you want the timer to run when you're not logged in:

```
loginctl enable-linger admin
```

## Disabling the hook

```
docker exec openclaw-gateway sh -c 'cd /app && node openclaw.mjs hooks disable session-memory-embed'
```

## Removing the orphan FTS store

If you're confident memory-lancedb is the only memory path you care about:

```
rm -f ~/.openclaw/memory/main.sqlite
rm -f ~/.openclaw/memory/main.sqlite.bak.*
```

## Backups

- `~/.openclaw/memory/lancedb.bak.<timestamp>/` — pre-backfill snapshot.
- `~/.openclaw/memory/main.sqlite.bak.<timestamp>` — stale FTS store.

Restore LanceDB by stopping the gateway, swapping directories, starting it
back up.
