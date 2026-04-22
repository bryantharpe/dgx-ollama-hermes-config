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
- `openclaw.json` — tracked template of `~/.openclaw/openclaw.json` (Ollama provider + agent defaults).
- `~/.openclaw/` (on host) — live state: config, skills, agents, credentials, workspace.
