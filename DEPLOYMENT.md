# Hermes Agent + Open WebUI + vLLM Deployment

This document describes the current deployment of Hermes Agent, integrated with Open WebUI as a frontend, vLLM as the local inference backend, and HashiCorp Vault for secret management.

> Migrated from Ollama → vLLM on 2026-04-25. The previous Ollama Modelfiles are archived under `legacy-modelfiles/`. The `ollama_data` Docker volume is intentionally preserved (orphaned) for one-week rollback.

## Architecture

```mermaid
flowchart TD
    Browser["Web Browser<br/>(Local Machine)"]
    SSH["SSH Tunnel<br/>(Port 8080)"]
    WebUI["Open WebUI<br/>(Docker: 8080)"]
    Hermes["Hermes Agent<br/>(Docker: 8642)"]
    vLLM["vLLM<br/>(Docker: 8000)<br/>Intel/Qwen3.6-27B-int4-AutoRound + MTP=2"]
    Vault["HashiCorp Vault<br/>(Docker: 8200)"]

    Browser --> SSH
    SSH --> WebUI
    WebUI -->|OpenAI /v1| Hermes
    WebUI -->|OpenAI /v1| vLLM
    Hermes -->|OpenAI /v1| vLLM
    Hermes -.->|Secrets| Vault
```

## Service Details

### 1. vLLM
- **Container Name**: `vllm`
- **Image**: `scitrera/dgx-spark-vllm:0.17.0-t5` (vLLM 0.17.1.dev0 + Transformers 5.x + PyTorch + CUDA 13.1 + FlashInfer 0.6.2, pre-built for ARM64 + GB10 Blackwell SM_120). The vanilla `vllm/vllm-openai` image is x86_64 only and **will not work** on DGX Spark. The scitrera vLLM track has been stalled at this image since 2026-03-08; their sglang track is more active and runs in parallel as a sidecar — see `vllm-to-sglang-migration-plan.md` and the local NVFP4 build pipeline at `dgx-spark-vllm/` for the longer-term alternatives.
- **Port**: `8000` inside the container; published on the host as `0.0.0.0:8001:8000` (host port 8001 because 8000 is held by an unrelated prototype). Inter-container URL is `http://vllm:8000/v1`; from the DGX host use `http://127.0.0.1:8001/v1`; from the LAN use `http://192.168.10.80:8001/v1`. **vLLM has no built-in auth** — the LAN bind implicitly trusts the LAN. To gate it, switch the publish back to `127.0.0.1:8001:8000` and front it with the existing openclaw Caddy (which already terminates TLS on `192.168.10.80:443`).
- **Model served**: `Intel/Qwen3.6-27B-int4-AutoRound` — Intel's AutoRound INT4 quant of Qwen3.6-27B dense + an `qwen3_next_mtp` MTP draft head preserved through the quant. ~14–18 GB on disk; 1.55× decode-rate over INT4-alone with MTP=2.
- **Single canonical served-model-name**: `qwen3.6-27b-int4:128k`. The previous multi-alias setup was consolidated to one alias on 2026-04-28 (commit `6d88cbc`); all downstream client configs (`hermes-agent` `LLM_MODEL`, `opencode/opencode.json`, `~/.openclaw/openclaw.json`) reference this exact string. Adding a new alias requires a coordinated client + vllm change.
- **First boot**: downloads ~14 GB from HuggingFace and compiles CUDA graphs (MTP adds an extra capture pass). Plan for **8–15 minutes** before `/health` returns 200. The compose healthcheck uses `start_period: 900s` to cover this. Subsequent boots reuse `vllm_hf_cache` + `vllm_compile_cache` (~5–7 min).

#### vLLM serve flags — what each one buys you

| Flag | Why |
|------|-----|
| `--max-model-len 262144` | Native context for Qwen3.6 family. INT4 weights are ~14 GB and FP8 KV cache at 262k context fits in 128 GB unified at `--gpu-memory-utilization=0.75`. Drop to 131072 if memory ever tightens. |
| `--gpu-memory-utilization 0.75` | DGX Spark's 128 GB is **unified memory** shared with the Grace CPU, OS, and any other containers. The vLLM default of 0.9 overcommits; 0.75 (~91 GB target) is the right setting when no other heavy GPU workloads are loaded. If you boot ComfyUI or another container that holds tens of GB resident, vllm will crash-loop with `ValueError: Free memory on device cuda:0 (X/121.69 GiB) on startup is less than desired GPU memory utilization` — either stop the other container, or drop this to 0.55 + `--max-model-len 32768`. |
| `--kv-cache-dtype fp8` | Halves attention memory at negligible quality loss. |
| `--enable-prefix-caching` | KV cache reuse across requests sharing a system-prompt prefix — big win for openclaw's long bootstrap context. |
| `--enable-chunked-prefill` + `--max-num-batched-tokens 16384` | Long prefills interleave with decode so short queries don't stall behind a 200k-token prompt. |
| `--max-num-seqs 4` | Right-sized concurrency for single-user interactive use. |
| `--reasoning-parser qwen3` | Splits `<think>...</think>` into the OpenAI `reasoning_content` field cleanly. **Required** for the 27B-INT4: this model's chat template (custom-mounted at `/etc/vllm/qwen3.6-27b.jinja`) defaults `enable_thinking=false`, so the parser is a no-op for routine traffic but correctly extracts reasoning when openclaw passes `chat_template_kwargs={"enable_thinking":true}` per request. ⚠️ If you swap to a model whose template ships zero thinking plumbing (e.g. Qwen/Qwen3-Coder-Next-FP8), this flag mis-classifies all output as reasoning and the OpenAI response comes back with `content: null` AND `reasoning_content: null` — drop it for those models. |
| `--chat-template /etc/vllm/qwen3.6-27b.jinja` | Custom template with `enable_thinking` flipped default-OFF. Without it, the 27B reasons indefinitely on small orchestration tasks. |
| `--enable-auto-tool-choice` | Required when any client sends `tool_choice: "auto"` (hermes-agent, opencode, OpenClaw all do). |
| `--tool-call-parser qwen3_coder` | **Critical.** The `hermes` parser returns HTTP 400 on `tool_choice=auto` for this model family — see NVIDIA forum thread `362784`. Qwen's HF model card explicitly specifies `qwen3_coder`. |
| `--language-model-only` | Skips the model's vision tower (none of our clients use it; saves ~3 GB and startup time). |
| `--speculative-config={"method":"qwen3_next_mtp","num_speculative_tokens":2}` | MTP speculative decoding via the draft head Intel's AutoRound preserved from upstream. Measured 1.55× over INT4-alone in Phase 1 perf bench. =2 chosen per Intel's model card; =3 yields diminishing returns. |
| `--served-model-name qwen3.6-27b-int4:128k` | Single canonical alias — see model section above. |

#### Tool-calling sanity check after deploy

```bash
curl -s http://127.0.0.1:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"qwen3.6-27b-int4:128k",
    "messages":[{"role":"user","content":"What is the weather in Paris?"}],
    "tools":[{"type":"function","function":{"name":"get_weather","parameters":{"type":"object","properties":{"city":{"type":"string"}}}}}],
    "tool_choice":"auto",
    "chat_template_kwargs":{"enable_thinking":false}
  }' | jq '.choices[0].message.tool_calls'
```

Must return a non-null `tool_calls` array. If it returns raw text or a 400, the parser flag is wrong. (The `chat_template_kwargs.enable_thinking=false` line matches what openclaw passes per request, so this curl mirrors a real call shape.)

### 2. Hermes Agent
- **Container Name**: `hermes-agent`
- **Image**: `hermes-agent:latest` (built from `./hermes-agent`)
- **Port**: `8642`
- **Role**: An "agentic" wrapper around the LLM. Manages tool execution (terminal, file system, web search) and sessions.
- **Backend**: Connected to vLLM via `http://vllm:8000/v1`.
- **API Server**: Enabled with key from `HERMES_API_KEY` env var.

### 3. Open WebUI
- **Container Name**: `open-webui`
- **Image**: `ghcr.io/open-webui/open-webui:main`
- **Port**: `8080`
- **Role**: The primary user interface.
- **Connections** (multi-URL OpenAI provider form via `OPENAI_API_BASE_URLS=...;...`):
    - **Hermes Agent** at `http://hermes-agent:8642/v1` (orchestrated chats with tools, memory, skills).
    - **vLLM** at `http://vllm:8000/v1` (raw model access, no orchestration).
- The previous `OLLAMA_BASE_URL` provider was dropped — vLLM does not implement Ollama-native `/api/*`. If you miss the Ollama-side dropdown, that capability is gone (one-way door).

### 4. HashiCorp Vault
- **Container Name**: `vault`
- **Image**: `hashicorp/vault`
- **Port**: `8200`
- **Role**: Secure storage for sensitive API keys and credentials.
- **Status**: Currently running in Dev Mode with `VAULT_DEV_ROOT_TOKEN_ID=root`.

### 5. gbrain (personal knowledge brain)

Additive to Hindsight, not a replacement. Hindsight = episodic session memory; gbrain = curated semantic knowledge (people, companies, meetings, articles, books). See `gbrain/README.md` for full operations doc.

Two services:

- **`gbrain-postgres`**: `pgvector/pgvector:pg17`, no published ports, `gbrain_postgres_data` volume (restic-backed nightly). Stores the brain (pages, embeddings, knowledge graph, Minions queue, supervisor state). Local-only; no cloud DB.
- **`gbrain`**: built from `./gbrain`, pinned to `garrytan/gbrain` SHA `c2ae4dbfc58d` = v0.25.1 (deliberately pre-OAuth-HTTP-server). Runs `gbrain jobs supervisor` as the long-running command — the canonical worker that handles the dream cycle, Minions queue, and durable agent runs.

Common attributes:

- **Profile**: `gbrain` — does **not** auto-start with `docker compose up -d`. Explicit start with `docker compose --profile gbrain up -d gbrain`. Drop the profile gate after baseline stability.
- **Ports**: none. MCP exposure is stdio-only via `docker exec -i gbrain gbrain serve` (registered host-side via `claude mcp add` in `~/.claude.json`).
- **Brain markdown location**: `/home/admin/.gbrain/` on the host — its **own private git repo**, separate from this hermes-config repo. Remote is `git@github.com:bryantharpe/gbrain-data.git` (private). Auto-pushes after every commit via the `post-commit` hook installed by the entrypoint.
- **Deploy key**: `/home/admin/.ssh/gbrain_data_deploy_ed25519` (private, mode 600). Public half registered as a write-enabled deploy key on the `gbrain-data` repo.
- **Local-providers patch**: `gbrain/Dockerfile` applies build-time sed patches because gbrain v0.25.1 hardcodes the OpenAI client (no `baseURL`), the `text-embedding-3-large` model name, and `vector(1536)` schema. Patches make all three env-driven so we can route to local ollama at 768 dims. See `gbrain/README.md` § "Local-providers patch".
- **Providers** (minimum cloud egress):
  - Embeddings → `http://ollama:11434/v1` (`nomic-embed-text`, local)
  - Routine LLM → `http://vllm:8000/v1` (`qwen3.6-27b-int4:128k`, local)
  - Heavy synthesis → `https://api.cerebras.ai/v1` (`qwen-3-235b-a22b-instruct-2507`, free tier — same override Hindsight uses)
- **Disabled at install**: HTTP MCP, OAuth, ngrok, Twilio, Gmail, Calendar, Twitter, Perplexity, Groq audio, archive-crawler. No skillpacks installed by default — `gbrain skillpack install <name>` is opt-in.

#### Enable / disable / rollback

```bash
# enable for the first time (after deploy key registered + GBRAIN_POSTGRES_PASSWORD set)
docker compose --profile gbrain up -d gbrain-postgres
docker compose --profile gbrain up -d gbrain

# pause without deleting (both services)
docker compose --profile gbrain stop gbrain gbrain-postgres

# remove containers, keep all data (Postgres volume + brain dir survive)
docker compose --profile gbrain rm -sf gbrain gbrain-postgres

# full nuke (also wipes local brain markdown — remote retains pushed commits)
docker compose --profile gbrain rm -sf gbrain gbrain-postgres
docker volume rm hermes-config_gbrain_postgres_data
rm -rf /home/admin/.gbrain
```

Independent recovery paths:
- **Postgres volume**: backed up nightly via restic→B2 alongside other Docker volumes. `scripts/restore.sh volume hermes-config_gbrain_postgres_data` to restore.
- **Markdown source**: in the `gbrain-data` GitHub remote. `git clone git@github.com:bryantharpe/gbrain-data.git /home/admin/.gbrain` to recover, then `gbrain import` to repopulate the Postgres index from the markdown.

#### MCP from Claude Code

Add to `~/.claude/server.json`:

```json
{
  "mcpServers": {
    "gbrain": { "command": "docker", "args": ["exec", "-i", "gbrain", "gbrain", "serve"] }
  }
}
```

---

## Network Configuration

All services are deployed within the same Docker network (default bridge). They communicate using internal Docker DNS:

| Source | Destination | Protocol | Internal URL |
|--------|-------------|----------|--------------|
| Open WebUI | Hermes Agent | HTTP | `http://hermes-agent:8642/v1` |
| Open WebUI | vLLM | HTTP | `http://vllm:8000/v1` |
| Hermes Agent | vLLM | HTTP | `http://vllm:8000/v1` |
| OpenCode | vLLM | HTTP | `http://vllm:8000/v1` |
| OpenClaw (sibling stack) | vLLM | HTTP | `http://vllm:8000/v1` (via `openclaw-ollama-proxy` socat sidecar on `127.0.0.1:18791`, which now forwards to `vllm:8000` rather than `ollama:11434`) |
| Hermes Agent | Vault | HTTP | `http://vault:8200` |

---

## Vault Setup & Secrets Management

Secrets are managed via Vault. To initialize Vault with the required secrets (Home Assistant, Brave Search, etc.), run the bootstrap script:

```bash
./setup_vault.sh
```

This script will:
1. Start the Vault container if it's not already running.
2. Read secrets from your local `.env` file.
3. Inject them into Vault at the path `secret/gemini-cli`.

### Manual Secret Access
You can verify secrets inside the container:
```bash
docker exec -it vault vault kv get secret/gemini-cli
```

---

## Accessing the UI over SSH

To access the interface from your local machine, use SSH port forwarding:

```bash
# Run this on your LOCAL computer
ssh -L 8080:localhost:8080 user@remote-ip
```

Then visit **[http://localhost:8080](http://localhost:8080)** in your browser.

> **Note**: If you get an `ERR_SSL_PROTOCOL_ERROR`, ensure you are using `http://` and not `https://`. Using `http://127.0.0.1:8080` instead of `localhost` can also help bypass browser-forced HTTPS.

## Backup & Restore

Off-host backups go to **Backblaze B2** via **restic** (client-side encrypted, deduplicated). Established 2026-05-03; first full snapshot landed `4d0c29d8`.

### What's where

| | |
|---|---|
| Tool | `restic` 0.18.1 at `/usr/local/bin/restic` (installed by `scripts/install-restic.sh`) |
| Repo | `b2:tharpe-dgx-spark:dgx-spark` (Backblaze B2, private bucket, SSE-B2, lifecycle "keep only the last version") |
| Credentials | `.env.backup` (gitignored, mode 600) — `B2_ACCOUNT_ID`, `B2_ACCOUNT_KEY`, `B2_BUCKET`, `RESTIC_REPOSITORY`, `RESTIC_PASSWORD` |
| Sudo grant | `/etc/sudoers.d/restic-backup` — `admin ALL=(root) NOPASSWD: SETENV: /usr/local/bin/restic` |
| Excludes | `scripts/excludes.txt` — system pseudo-fs, regenerable caches, build artifacts |
| Log | `.backup.log` (admin-owned, append-only) |

The restic password is **not recoverable** if lost — Backblaze cannot decrypt the repo. Keep at minimum two offline copies (password manager + paper/USB).

### Source paths covered

`/home`, `/etc`, `/usr/local`, `/root`, `/var/lib/docker/volumes` — everything stateful. Docker image/layer storage (`/var/lib/docker/{overlay2,containers,image,...}`) is excluded since images come from registries and ephemeral state isn't data.

### Schedule

Three systemd timers, installed by `scripts/install-backup-timers.sh`. Verify with `systemctl list-timers 'hermes-backup*'`.

| Timer | When | Service |
|---|---|---|
| `hermes-backup.timer` | daily 03:00 UTC | full incremental snapshot |
| `hermes-backup-check.timer` | weekly Sun 04:00 UTC | `restic check --read-data-subset=5%` |
| `hermes-backup-prune.timer` | monthly 1st 05:00 UTC | `restic forget --keep-daily 14 --keep-weekly 8 --keep-monthly 12 --keep-yearly 3 --prune` |

All `Persistent=true` so missed firings catch up on next boot.

### Restoring

Use `scripts/restore.sh`:

```bash
scripts/restore.sh list                              # list snapshots
scripts/restore.sh list <snap-id>                    # list files in a snapshot
scripts/restore.sh file <abs-path> [snap]            # → /tmp/restic-restore-<ts>/<path>
scripts/restore.sh volume <docker-vol-name> [snap]   # restore in place; prompts
scripts/restore.sh system [snap]                     # full restore to / ; YES gate
```

`snap` defaults to `latest`. The wrapper handles the B2 cold-connection retry pattern (first attempt often hits `context deadline exceeded`; retries usually succeed on attempt 2).

**Bare-metal recovery on a fresh DGX Spark:**

1. Stock OS install + nvidia drivers (`bootstrap.sh`)
2. `git clone <hermes-config-remote> ~/code/hermes-config`
3. Drop B2 creds + `RESTIC_PASSWORD` into `~/code/hermes-config/.env.backup` (the only thing not recoverable from git; comes from your password manager)
4. `bash ~/code/hermes-config/scripts/install-restic.sh`
5. Add the sudoers entry: `echo 'admin ALL=(root) NOPASSWD: SETENV: /usr/local/bin/restic' | sudo tee /etc/sudoers.d/restic-backup && sudo chmod 440 /etc/sudoers.d/restic-backup`
6. `bash ~/code/hermes-config/scripts/restore.sh system`
7. Reboot, then `bash ~/code/hermes-config/scripts/install-backup-timers.sh` to re-arm the schedule

The repo + four credential values are sufficient to fully reconstitute the host.

### Manual ops

```bash
# ad-hoc backup (same logic as the daily timer)
scripts/backup.sh
scripts/backup.sh --dry-run                          # estimate-only

# inspect
. .env.backup && restic --no-lock snapshots
. .env.backup && restic --no-lock stats --mode raw-data

# rotate the B2 application key
# 1) generate a new app key in the B2 console (scoped to this bucket)
# 2) update B2_ACCOUNT_ID + B2_ACCOUNT_KEY in .env.backup
# 3) delete the old key in the B2 console
```

## Troubleshooting

### Build agent silently queues but never executes

Symptom: `opencode` accepts a `/session/<id>/prompt_async` POST but polling `/session/<id>/message` returns 0 assistant parts indefinitely.

Cause under vLLM: the wrong `--tool-call-parser` is set on the `vllm` container. With `hermes` (the obvious-but-wrong choice for this model family), tool-calls return raw text instead of structured `tool_calls` and OpenCode has nothing to dispatch.

Fix:
```bash
docker exec vllm sh -c 'ps -o args -p 1' | grep -o -- '--tool-call-parser[= ][^ ]*'
# Must report: --tool-call-parser=qwen3_coder
# If it reports `hermes`, edit docker-compose.yml and `docker compose up -d vllm`.
```

Sanity-check the tool-call surface end-to-end with the curl from the vLLM service section above.

### No models in dropdown
1. Check the **Admin Settings > Connections** in Open WebUI.
2. Verify the **OpenAI API** URLs are `http://hermes-agent:8642/v1` (key = `HERMES_API_KEY`) AND `http://vllm:8000/v1` (key = `none`). Open WebUI accepts both via the `OPENAI_API_BASE_URLS` semicolon-separated form.
3. `curl http://127.0.0.1:8001/v1/models | jq '.data[].id'` should list `qwen3.6-27b-int4:128k` (single canonical alias).

### Resetting Password
If you forget your admin password, you can reset it via the database inside the container:
```bash
docker exec -it open-webui python3 -c "import bcrypt; import sqlite3; password = b'NEW_PASSWORD'; salt = bcrypt.gensalt(); hashed = bcrypt.hashpw(password, salt).decode(); conn = sqlite3.connect('/app/backend/data/webui.db'); cursor = conn.cursor(); cursor.execute('UPDATE auth SET password = ? WHERE email = ?', (hashed, 'YOUR_EMAIL')); conn.commit(); print('Success')"
```
