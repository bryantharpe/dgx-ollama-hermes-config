# gbrain — personal knowledge brain

Local deployment of [garrytan/gbrain](https://github.com/garrytan/gbrain) on the DGX Spark, configured for **minimum cloud exposure**: PGLite (embedded, local DB), local embeddings via Ollama, local chat via vLLM, Cerebras only for heavy synthesis. No HTTP MCP, no OAuth, no public ports.

## What lives where

| | Path / location |
|---|---|
| Image build context | `./gbrain/` (this directory) |
| gbrain code (in image) | `/opt/gbrain/` — pinned to upstream SHA `c2ae4dbfc58d` (v0.25.1) |
| Brain data (host) | `/home/admin/.gbrain/` (markdown source-of-truth + `.git` for auto-push) |
| Database | `gbrain-postgres` container, volume `gbrain_postgres_data`, no published ports |
| Brain remote | `git@github.com:bryantharpe/gbrain-data.git` (private) |
| Deploy key | `/home/admin/.ssh/gbrain_data_deploy_ed25519` (mode 600) |
| MCP transport | stdio via `docker exec -i gbrain gbrain serve` |
| Compose profile | `gbrain` (opt-in; not auto-started) |
| Long-running command | `gbrain jobs supervisor --concurrency 4` (Minions queue, dream cycle, cron skills) |

## Authoring workflow (markdown-first)

The canonical workflow:

1. **Author** a markdown file directly under `/home/admin/.gbrain/<type>/<slug>.md` (e.g. `concepts/local-first-ai.md`). Frontmatter looks like `---\ntype: concept\n---`.
2. **Index** with `docker exec gbrain gbrain import /home/admin/.gbrain/<type>/`. This embeds the page (via ollama) and updates the Postgres index.
3. **Commit + push** with `git -C /home/admin/.gbrain commit -am "..."`. The post-commit hook auto-pushes to `bryantharpe/gbrain-data`.

`gbrain put <slug>` writes only to the database — it doesn't create a markdown file on disk, so there's nothing for git to commit/push. **For anything you want backed up, author the markdown file first, then import.**

Query from the CLI: `docker exec gbrain gbrain query "..."`. Query from Claude Code: the registered `mcp__gbrain__*` tools.

## Why Postgres (not the bundled PGLite)

PGLite is gbrain's "ready in 2 seconds for evaluation" mode, not its production target. Its exclusive file lock blocks `gbrain jobs supervisor`, which means **no autonomous brain features**: no `dream` cycle (nightly enrichment), no Minions queue (durable background jobs), no cron skills (signal-detector, brain-ops, daily-task-prep, etc).

Postgres adds:

- One container (`pgvector/pgvector:pg17`, official multi-arch image)
- One volume (`gbrain_postgres_data`, restic-backed up nightly)
- One secret (`GBRAIN_POSTGRES_PASSWORD` in `.env`)
- ~150 MB idle RAM

In return: full feature set. Doctor goes from 75/100 → 85/100 (plus brain_score climbs as autonomous link/timeline extraction runs). The tradeoff is heavily one-sided.

## Local-providers patch

Upstream gbrain v0.25.1 hardcodes:

- OpenAI client (`new OpenAI()`, no `baseURL`) for embeddings
- `text-embedding-3-large` model name
- `vector(1536)` PGLite column type

`gbrain/Dockerfile` applies surgical sed patches at build time so all three become env-driven (`GBRAIN_EMBEDDING_BASE_URL`, `GBRAIN_EMBEDDING_MODEL`, `GBRAIN_EMBEDDING_DIMENSIONS`) plus the `vector()` column matches the configured dimension. The patches are visible in `gbrain/Dockerfile`; bumping the upstream SHA may require updating the literal-string anchors. The build verifies each patch landed via `grep -q` and fails loudly if the upstream surface changed.

To revert to upstream defaults (OpenAI cloud embeddings): drop the patch RUN block from the Dockerfile, leave `GBRAIN_EMBEDDING_*` env vars unset.

## Why pin to v0.25.1, not latest

v0.26.0 (2026-05-03) introduced the OAuth 2.1 HTTP MCP server + admin dashboard. We deliberately do **not** want that — stdio is safer for a local-only deployment. Staying on v0.25.1 keeps the OAuth/HTTP code path out of the binary entirely.

To bump:
1. Read `garrytan/gbrain` CHANGELOG since `c2ae4dbfc58d`
2. Update `ARG GBRAIN_SHA=...` in `Dockerfile`
3. `docker compose --profile gbrain build gbrain`
4. `docker compose --profile gbrain up -d gbrain`

## First-time bootstrap

Order matters because the entrypoint clones the brain-data repo on first start, which requires the deploy key to be registered.

1. **Generate the deploy key** (already done — `/home/admin/.ssh/gbrain_data_deploy_ed25519`):
   ```bash
   ssh-keygen -t ed25519 -f /home/admin/.ssh/gbrain_data_deploy_ed25519 -N ""
   ```
2. **Register the public key** on `bryantharpe/gbrain-data` GitHub repo (Settings → Deploy keys → Add → paste `*.pub` contents → check "Allow write access").
3. **Generate the Postgres password** and add to `.env`:
   ```bash
   echo "GBRAIN_POSTGRES_PASSWORD=$(openssl rand -hex 32)" >> .env
   ```
4. **Build and start** (Postgres comes up first, then gbrain):
   ```bash
   docker compose --profile gbrain build gbrain
   docker compose --profile gbrain up -d gbrain-postgres
   docker compose --profile gbrain up -d gbrain
   docker logs -f gbrain   # watch first-run init + supervisor start
   ```
4. **Validate**:
   ```bash
   docker exec gbrain gbrain doctor
   docker exec gbrain gbrain skillpack-check --quiet && echo OK
   docker exec gbrain gbrain jobs smoke
   ```
5. **Wire MCP** in `~/.claude/server.json`:
   ```json
   {
     "mcpServers": {
       "gbrain": { "command": "docker", "args": ["exec", "-i", "gbrain", "gbrain", "serve"] }
     }
   }
   ```

## Lifecycle commands

```bash
# pause without deleting (both services)
docker compose --profile gbrain stop gbrain gbrain-postgres

# remove containers, keep all data (Postgres volume + brain dir survive)
docker compose --profile gbrain rm -sf gbrain gbrain-postgres

# full nuke (local) — remote keeps all pushed commits; markdown survives
docker compose --profile gbrain rm -sf gbrain gbrain-postgres
docker volume rm hermes-config_gbrain_postgres_data
rm -rf /home/admin/.gbrain

# rebuild after Dockerfile / SHA change (no data loss)
docker compose --profile gbrain build gbrain
docker compose --profile gbrain up -d gbrain
```

**Recovering from a fresh checkout / disaster:**

```bash
git clone git@github.com:bryantharpe/gbrain-data.git /home/admin/.gbrain
docker compose --profile gbrain up -d gbrain-postgres gbrain
docker exec gbrain gbrain import /home/admin/.gbrain/concepts/   # or other dirs
```

The Postgres volume restic-snapshots nightly with the rest of `/var/lib/docker/volumes`. The markdown is in the `gbrain-data` GitHub repo. Both are independently recoverable.

## Auto-push to gbrain-data

The entrypoint installs a `post-commit` hook in `/home/admin/.gbrain/.git/hooks/post-commit` that backgrounds `git push origin HEAD` after every gbrain page edit. Failures don't block commits — they get logged at `/home/admin/.gbrain/.git/post-commit-push.log`.

Manual catch-up if pushes fall behind:
```bash
GIT_SSH_COMMAND='ssh -i /home/admin/.ssh/gbrain_data_deploy_ed25519' \
  git -C /home/admin/.gbrain push origin HEAD
```

## Coexistence with Hindsight

Both memory backends run side-by-side and serve different roles:

| | Hindsight | gbrain |
|---|---|---|
| Memory type | Episodic — what was said in conversations | Semantic — curated knowledge about the world |
| Capture | Autopilot via `session-memory-embed` hook on `/reset` | Deliberate via `gbrain import` / skill ingestion |
| Recall via MCP | `mcp__hindsight__*` tools | `mcp__gbrain__*` tools |
| Storage | Neon Postgres (cloud) + Cerebras extraction | PGLite (local) + Ollama embeddings |

Claude Code picks the right tool per query type. There is no migration / replacement plan — they're complementary.

## Disabled by design

| What | Why |
|---|---|
| HTTP MCP server, OAuth 2.1, ngrok, admin dashboard | Stdio MCP is sufficient and exposes nothing. Pinning to v0.25.1 means the OAuth code is not even in the binary. |
| Twilio (voice notes, SMS) | Removes a third-party voice path |
| Gmail / Calendar / Twitter / Perplexity recipes | No additional cloud egress |
| Groq Whisper (audio ingestion) | No audio at start; revisit if needed |
| `archive-crawler` skill | gbrain refuses to run it without `archive-crawler.scan_paths:` set in `.gbrainrc` — safe-by-default fence |

## Troubleshooting

**Container exits immediately on `up -d`.**
Check `docker logs gbrain`. Most likely the entrypoint's first-run clone failed because the deploy key isn't registered yet. Register the public key on GitHub, then `docker compose --profile gbrain up -d gbrain`.

**`gbrain doctor` complains about half-migrated state.**
Run `docker exec gbrain gbrain upgrade` to apply pending schema migrations.

**Auto-push isn't reaching GitHub.**
```bash
tail /home/admin/.gbrain/.git/post-commit-push.log
GIT_SSH_COMMAND='ssh -i /home/admin/.ssh/gbrain_data_deploy_ed25519 -v' \
  git -C /home/admin/.gbrain push origin HEAD 2>&1 | head -30
```

**Postgres connection refused at startup.**
```bash
docker logs gbrain-postgres --tail 30                # check pg state
docker exec gbrain-postgres pg_isready -U gbrain     # should print "accepting connections"
grep GBRAIN_POSTGRES_PASSWORD /home/admin/code/hermes-config/.env
```
If the password isn't in `.env`, compose fails before either service starts.

**Supervisor not running / dream cycle inactive.**
```bash
docker exec gbrain gbrain doctor | grep supervisor   # should show running=true
docker logs gbrain | grep "Minion worker"            # confirms handler registration
```
If the supervisor crashed >10 times in a 24h window it'll back off. Inspect `~/.gbrain/audit/supervisor-*.jsonl` (inside the brain dir) for crash details.

**Embeddings calls return 404.**
Verify ollama has `nomic-embed-text`:
```bash
docker exec ollama ollama list | grep nomic-embed-text
curl -s http://localhost:11434/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"nomic-embed-text","input":"test"}' | head -c 200
```

**vLLM rejects the chat model alias.**
The compose env var `GBRAIN_LLM_MODEL=qwen3.6-27b-int4:128k` must match vLLM's `--served-model-name`. If vLLM is mid-benchmark on a different model alias, gbrain calls will 404 — restore the production alias or update `GBRAIN_LLM_MODEL` in `.env` accordingly.
