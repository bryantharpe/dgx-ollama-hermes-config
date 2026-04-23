# OpenClaw

Runs the published `ghcr.io/openclaw/openclaw:latest` image as two containers (`openclaw-gateway` + `openclaw-cli`) joined to the shared Hermes docker network so it can reach `ollama:11434` by hostname.

## Prerequisites

The top-level Hermes stack must be up so the `hermes-config_default` docker network exists:

```bash
cd /home/admin/code/hermes-config
docker compose up -d ollama
```

## First-run setup

```bash
cd /home/admin/code/hermes-config/openclaw

# 1. Local env (gitignored)
cp .env.example .env

# 2. OpenClaw config into the state dir that gets bind-mounted
mkdir -p ~/.openclaw/workspace
cp openclaw.json ~/.openclaw/openclaw.json

# 3. (Optional) set a gateway token if you want auth on the local API
# Edit .env and set OPENCLAW_GATEWAY_TOKEN=...
```

The tracked `openclaw.json` is a **sanitized snapshot of the live config**, not an auto-seeded source of truth. `docker compose up` never reads it — it's only used by the explicit `cp` above for a fresh first-run. Placeholders to fill in before or after copying:

- `channels.telegram.botToken` — empty; set to the value from `@BotFather`.
- `channels.telegram.enabled` — shipped as `false` so an empty bot token doesn't crash the plugin. Flip to `true` after the token is in.
- `gateway.auth.token` — not present; the gateway auto-generates it on first boot (see "Open the Control UI" below).
- `BRAVE_API_KEY` (in `.env`, not `openclaw.json`) — required for the `web_search` tool. Tracked config wires Brave as the provider (`tools.web.search.provider = "brave"` + `plugins.entries.brave.enabled = true`); the gateway reads the key from env. Get one at [brave.com/search/api](https://brave.com/search/api/) and set a usage cap in the Brave dashboard.

If you edit the live config at `~/.openclaw/openclaw.json`, consider re-snapshotting the tracked template afterwards so it doesn't drift stale.

Skills live under `~/.openclaw/skills/` and are picked up automatically via the bind-mount.

### Required config keys

The tracked `openclaw.json` already contains the three keys the dockerized gateway needs on first boot. If you rebuild `~/.openclaw/openclaw.json` from scratch, make sure they're still present:

- `gateway.mode = "local"` — current `ghcr.io/openclaw/openclaw:latest` refuses to start without it.
- `gateway.controlUi.allowedOrigins` must include `http://127.0.0.1:18789` and `http://localhost:18789`. The gateway binds to `0.0.0.0` inside the container (see next note), so the Control UI enforces an origin allowlist even though the host-side port is loopback-only.
- `OPENCLAW_GATEWAY_BIND=lan` in `.env` — binding `loopback` inside the container breaks docker port forwarding, because docker NATs inbound traffic through the container's eth0 rather than its loopback interface. The compose file still binds the host-side port to `127.0.0.1:18789` only.

## Run

```bash
docker compose up -d
docker compose ps
docker compose logs -f openclaw-gateway
```

Health check: `curl -sf http://127.0.0.1:18789/healthz`

## Open the Control UI

The gateway authenticates Control UI connections with a token stored at `~/.openclaw/openclaw.json` under `gateway.auth.token` (auto-generated on first boot). Browsing to `http://127.0.0.1:18789/` without it will get rate-limited after a few attempts. Print a pre-authenticated URL instead:

```bash
docker compose run --rm openclaw-cli dashboard --no-open
```

Paste the `http://127.0.0.1:18789/#token=...` URL into your browser.

### First connect: device pairing

The gateway token gets your browser to the login card, but each browser (and each CLI runtime) is a separate **device** that has to be approved before it can connect. You'll see "pairing required" on first connect.

After clicking Connect once, run:

```bash
docker compose run --rm openclaw-cli devices list        # find the pending request from your browser's IP (e.g. 172.19.0.1)
docker compose run --rm openclaw-cli devices approve <request-id>
```

Then click Connect again in the browser — it's paired until you revoke it.

The gateway's internal **runtime** also pairs as a separate device for tool execution (e.g. `exec`). If the agent reports "Exec approval registration failed: pairing required" in a tool result, run `devices list` again — you'll see a pending `repair` request asking to extend an existing paired device's scopes from `operator.read` to include `operator.write` + `operator.approvals`. Approve it the same way. This typically happens on first use of the `exec` tool after a container recreate.

### Operator scopes — don't grant admin/pairing to chat clients

New pairing requests (Control UI, phone, future Telegram-paired clients) default to asking for all five operator scopes: `operator.read`, `operator.write`, `operator.admin`, `operator.approvals`, `operator.pairing`. The last two are privileged (`admin` = `/config set|unset`; `pairing` = approve further device pairings). **Don't leave them on a chat client.**

The current policy on this deployment:

- **Gateway runtime device** (the internal CLI agent, `clientId: cli`) — full scopes; needs them to run `exec` and resolve approvals.
- **Control UI / phone browser** (`clientId: openclaw-control-ui`) — reduced to `operator.read + operator.write + operator.approvals`. Config edits go through file edit + gateway restart, not `/config set`.
- **Any new device** (esp. channel-paired) — approve, then immediately rotate down:
  ```bash
  docker compose run --rm openclaw-cli devices rotate \
    --device <deviceId> --role operator \
    --scope operator.read --scope operator.write --scope operator.approvals
  ```
  `devices rotate` only changes the **token** scopes; also edit `~/.openclaw/devices/paired.json` to reduce `scopes` and `approvedScopes` on that device entry, then `docker compose restart openclaw-gateway`, so a future re-pair doesn't reissue admin/pairing.

## Use the CLI

```bash
docker exec -it openclaw-cli openclaw --version
docker exec -it openclaw-cli openclaw skills list
docker exec -it openclaw-cli openclaw agent --message "hello"
```

## Stop

```bash
docker compose down
```

## Layout

- `docker-compose.yml` — gateway + cli services, joined to `hermes-config_default`.
- `.env.example` — env contract (image, paths, ports, timezone, token).
- `openclaw.json` — sanitized snapshot of `~/.openclaw/openclaw.json` (Ollama provider, agent defaults, memory-lancedb, telegram shape, session-memory-embed hook). Used for first-run copy only; never mounted.
- `~/.openclaw/` (on host) — live state: config, skills, agents, credentials, workspace.
