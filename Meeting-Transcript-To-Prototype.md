# Meeting Transcript → Prototype

End-to-end reference for the two-skill pipeline that turns a raw meeting transcript (or idea) into a running, browsable prototype on a local port. Runs entirely air-gapped on the Hermes host — no cloud services involved.

**Two skills, two models, one orchestrator:**

| Skill | Model | Role |
|---|---|---|
| `meeting-transcript-to-specs` | `qwen3.6-35b:128k` (Q8, 131k ctx) | Propose phase — writes `proposal.md` / `design.md` / `tasks.md` |
| `meeting-specs-to-prototype` | `qwen3-coder-next:q5-131k` (Q5, 131k ctx) | Build phase — OpenCode coder writes the actual code |

---

## 1. User flow

```mermaid
flowchart TD
    A([User has an idea or<br/>meeting transcript]) --> B[Open OpenClaw dashboard<br/>https://192.168.10.80/]
    B --> C{Logged in?}
    C -- no --> D[Paste gateway token<br/>approve device pairing]
    D --> E
    C -- yes --> E[Paste transcript +<br/>&quot;generate specs for my-slug&quot;]
    E --> F[Propose skill runs]
    F --> G[(proposal.md + design.md + tasks.md<br/>written to shared prototypes tree)]
    G --> H{Review output}
    H -- edit --> I[Ask orchestrator to revise specs]
    I --> G
    H -- ok --> J[&quot;Build it&quot; → Build skill runs]
    J --> K[Seeder creates skeleton<br/>+ allocates port 9000–9099]
    K --> L[OpenCode session created]
    L --> M[Coder writes feature code<br/>streaming progress to UI]
    M --> N{Stall?}
    N -- yes, 1st time --> O[Orchestrator sends<br/>steer prompt to same session]
    O --> M
    N -- no --> P[Coder: docker compose up +<br/>verify endpoints]
    P --> Q[Pre-archive verify gate]
    Q --> R[Archive changes/ → archive/]
    R --> S[Orchestrator post-build<br/>asset audit]
    S -- missing --> T[Open patch session<br/>fix missing files]
    T --> S
    S -- all 200 --> U([Prototype live at<br/>http://host:&lt;allocated-port&gt;/])
```

---

## 2. Component view (C4-ish)

```mermaid
flowchart TB
    subgraph USR["👤 User"]
        browser["Browser<br/>(phone via Teleport<br/>or laptop on LAN)"]
    end

    subgraph HOST["Hermes host (192.168.10.80)"]
        subgraph EDGE["Edge / TLS"]
            caddy["🔒 openclaw-caddy<br/>:443 / :80<br/>local self-signed CA"]
        end

        subgraph ORCH["Orchestrator tier"]
            gateway["🧠 openclaw-gateway<br/>:18789 (ws, loopback)<br/>runs propose + build skills"]
            cli["openclaw-cli<br/>(one-shot CLI container)"]
        end

        subgraph BUILD["Build tier"]
            opencode["🏗️ opencode<br/>:4096 (http)<br/>runs the build coder"]
            seeder["🌱 prototype-seeder<br/>:8080 (http)<br/>copies _template/<br/>allocates ports"]
        end

        subgraph MODELS["Model tier"]
            ollama["🦙 ollama<br/>:11434<br/>qwen3.6-35b:128k<br/>qwen3-coder-next:q5-131k"]
        end

        subgraph PROTO["Prototype tier"]
            p1["worlds-fair-companion<br/>:9002"]
            p2["ai-conference-test2<br/>:9003"]
            pN["&lt;slug&gt;<br/>:9000–9099"]
        end

        subgraph STORE["Shared storage"]
            fs[("/home/admin/code/hermes-config/prototypes/<br/>_template/, .registry/ports.json,<br/>&lt;slug&gt;/")]
            openclawdata[("~/.openclaw/<br/>skills/, openclaw.json,<br/>workspace/, caddy_data/")]
        end
    end

    browser -- "https://192.168.10.80/" --> caddy
    caddy -- "reverse_proxy<br/>ws:// + http://" --> gateway

    gateway -- "/v1/chat (Q8 35B)" --> ollama
    gateway -- "POST /seed" --> seeder
    gateway -- "POST /session<br/>POST /session/&lt;id&gt;/prompt_async<br/>GET /session/&lt;id&gt;/message" --> opencode

    opencode -- "/v1/chat (Q5 80B coder)" --> ollama
    opencode -- "docker socket" --> p1
    opencode -- "docker socket" --> p2
    opencode -- "docker socket" --> pN

    seeder -- "mkdir + chown<br/>cp -r _template/" --> fs
    opencode -- "reads /prototypes/" --> fs
    gateway -- "reads /home/node/prototypes/" --> fs
    gateway -- "reads/writes /home/node/.openclaw/" --> openclawdata
```

**Key fact about tiers:** `openclaw-gateway` never runs Docker itself — it speaks HTTP to `opencode`, which has the docker socket mounted and starts/manages prototype containers on the host.

---

## 3. Sequence diagram — happy path

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant B as Browser
    participant C as openclaw-caddy
    participant G as openclaw-gateway<br/>(orchestrator, Q8 35B)
    participant M as ollama
    participant S as prototype-seeder
    participant O as opencode<br/>(coder, Q5 80B)
    participant P as Prototype container

    Note over U,B: Phase 0 — User logs in
    U->>B: https://192.168.10.80/#token=...
    B->>C: TLS handshake (local CA)
    C->>G: ws:// upgrade
    G-->>B: dashboard ready
    U->>B: paste transcript + slug

    Note over G,M: Phase 1 — Propose
    B->>G: chat message (transcript)
    G->>M: /v1/chat (qwen3.6-35b:128k)
    M-->>G: writes proposal.md<br/>design.md, tasks.md
    Note right of G: files land at<br/>/home/node/prototypes/&lt;slug&gt;/openspec/changes/prototype/
    G-->>B: "specs ready; build?"
    U->>B: "yes, build"

    Note over G,S: Phase 2 — Seed skeleton
    B->>G: build trigger
    G->>G: ls specs dir (verify 3 files)
    G->>S: POST /seed {slug}
    S->>S: cp -r _template/ <slug>/<br/>allocate port (9000–9099)<br/>chown root:root
    S-->>G: {port, path}

    Note over G,O: Phase 3 — Hand off to OpenCode
    G->>O: POST /session {title}
    O-->>G: {id: ses_…}
    G->>G: write /tmp/opencode_prompt.txt<br/>(build prompt w/ WRAPPER CONTRACT)
    G->>G: build-payload.sh → /tmp/opencode_payload.json
    G->>O: POST /session/<id>/prompt_async
    O-->>G: 204 No Content (async)

    Note over G,P: Phase 4 — Build (background on opencode)
    loop coder tool rounds (30s–4min each)
        O->>M: /v1/chat (qwen3-coder-next:q5-131k)
        M-->>O: tool calls
        O->>O: write/edit src/server/*, src/frontend/*<br/>seed.py, schema.sql
    end
    O->>P: docker compose up -d --build<br/>(via host docker socket)
    P-->>O: container healthy
    loop verify endpoints
        O->>P: docker exec curl localhost:8000/api/...
        P-->>O: 200
    end

    Note over O: Task 4.5 — pre-archive verify gate
    O->>P: curl every /static/… URL<br/>grep schema.sql vs seed.py columns
    P-->>O: all green
    O->>O: mv changes/prototype → archive/prototype
    O->>O: emit final text + step-finish stop

    Note over G,O: Phase 5 — Orchestrator polls & audits
    loop every 30s
        G->>O: GET /session/<id>/message
        O-->>G: {terminal, part_count, latest_text}
        G-->>B: relay latest text
    end
    G->>P: docker exec curl /static/… (post-build audit)
    P-->>G: all 200
    G-->>B: "prototype live at http://host:<port>/"
    U->>B: visit http://192.168.10.80:<port>/
    B->>P: GET / (directly, not through Caddy)
    P-->>B: index.html + /static/... + /api/...
```

---

## 4. Docker networking

```mermaid
flowchart LR
    subgraph HOSTNET["Host network (192.168.10.80 on enP7s7)"]
        subgraph PUBLIC["LAN-reachable ports"]
            p443[":443 / :80<br/>openclaw-caddy"]
            p9002[":9002 worlds-fair-companion"]
            p9003[":9003 ai-conference-test2"]
            pNNNN[":&lt;9000-9099&gt;<br/>per-slug prototypes"]
        end

        subgraph LOOPBACK["Loopback-only ports"]
            p18789["127.0.0.1:18789<br/>openclaw-gateway"]
            p4096["127.0.0.1:4096<br/>opencode"]
            p11434["127.0.0.1:11434<br/>ollama"]
            p8081["127.0.0.1:8081<br/>prototype-seeder"]
        end
    end

    subgraph OPENCLAWNET["openclaw_default network"]
        caddy2["openclaw-caddy"]
        gateway2["openclaw-gateway"]
    end

    subgraph HERMESNET["hermes-config_default network (shared)"]
        gateway3["openclaw-gateway<br/>(also joined here)"]
        opencode2["opencode"]
        ollama2["ollama"]
        seeder2["prototype-seeder"]
        hermes["hermes-agent<br/>(legacy, parallel system)"]
    end

    subgraph PROTONETS["per-prototype networks"]
        wfcnet["worlds-fair-companion_default"]
        acnet["ai-conference-test2_default"]
        otherslugs["&lt;slug&gt;_default"]
    end

    PUBLIC --> caddy2
    LOOPBACK --> gateway2
    LOOPBACK --> opencode2
    LOOPBACK --> ollama2
    LOOPBACK --> seeder2

    caddy2 <-. DNS: openclaw-gateway .-> gateway2
    gateway3 <-. DNS: ollama .-> ollama2
    gateway3 <-. DNS: opencode .-> opencode2
    gateway3 <-. DNS: prototype-seeder .-> seeder2
    opencode2 <-. DNS: ollama .-> ollama2
    opencode2 -. docker socket .-> wfcnet
    opencode2 -. docker socket .-> acnet
    opencode2 -. docker socket .-> otherslugs
```

**Rules of the layout**:

- **Caddy is the only thing published on LAN port 443/80** — all other orchestrator ports are loopback-only on the host. Phone traffic: `https://192.168.10.80/` → Caddy → openclaw-gateway over the `openclaw_default` bridge.
- **openclaw-gateway is dual-homed** on both `openclaw_default` (to receive Caddy's proxy) and `hermes-config_default` (to reach ollama/opencode/seeder by hostname).
- **Prototype containers each create their own bridge network** when `docker compose up` runs. They're NOT on the hermes network. OpenCode reaches them only via the host's docker socket (`docker exec` / `docker inspect`), not by hostname — this is why the verify pattern is `docker exec $NAME curl http://localhost:8000/…` from inside the prototype, not `curl http://<slug>:8000/…` from opencode.
- **Prototype ports published on 0.0.0.0** — accessible from LAN (including phone via Teleport) at `http://192.168.10.80:<port>/`.

---

## 5. Filesystem bind-mounts

```mermaid
flowchart LR
    subgraph HFS["Host filesystem"]
        direction TB
        hprot["/home/admin/code/hermes-config/<br/>prototypes/"]
        hopenclaw["~/.openclaw/"]
        hcaddy[("caddy_data<br/>named volume")]
        hdocker["/var/run/docker.sock"]
    end

    subgraph GW["openclaw-gateway"]
        gprot["/home/node/prototypes"]
        gclaw["/home/node/.openclaw"]
    end

    subgraph OC["opencode"]
        oprot["/prototypes"]
        osock["/var/run/docker.sock"]
    end

    subgraph SEED["prototype-seeder"]
        sprot["/prototypes"]
    end

    subgraph CD["openclaw-caddy"]
        cdata["/data"]
    end

    hprot --> gprot
    hprot --> oprot
    hprot --> sprot
    hopenclaw --> gclaw
    hcaddy --> cdata
    hdocker --> osock
```

**Shared-state highlights:**

- `prototypes/` is bind-mounted into three containers — **openclaw-gateway, opencode, seeder all see the same files at their own prefix.** This is what makes the handoff work: the orchestrator writes specs at `/home/node/prototypes/<slug>/...`, the seeder reads those at `/prototypes/<slug>/...`, opencode reads at `/prototypes/<slug>/...`. Same inodes, three paths.
- `~/.openclaw/skills/` is where the two skills (`meeting-transcript-to-specs`, `meeting-specs-to-prototype`) live, user-local, outside any docker build — edit them and restart `openclaw-gateway` to apply.
- `/var/run/docker.sock` into opencode is what lets the coder run `docker compose up -d --build` on the host; openclaw-gateway does NOT have this socket and so cannot run docker itself.

---

## 6. The three critical paths (for debugging)

| Symptom | Where to look |
|---|---|
| "docker: not found" in orchestrator log | Orchestrator tried to build directly. Skill's HARD BOUNDARY section was ignored — re-read to the model, or steer. |
| Coder 404s on `/static/foo.js` | Pre-archive verify gate missed it, or the coder put the file in a subdir. Check `src/frontend/` — URLs are FLAT against that directory. |
| Prototype container crashloops | Usually schema/seed drift — `docker logs <slug>` shows `sqlite3.OperationalError: table X has no column named Y`. Propose-skill's consistency invariant should have caught it. |
| Build session stalls forever | Q5 coder waiting on something. Check `part_count` across polls — if it hasn't moved for 6 polls (~3 min), steer-on-stall fires; if the steered session also stalls, abort is the only option. |
| UI blank / blocked by an overlay | Coder shipped `class="hidden"` without the CSS rule. Template now ships `.hidden { display: none !important; }` in `style.css` — check it wasn't deleted. |

---

## 7. Command cheat sheet

```bash
# Open the dashboard (phone via Teleport, or laptop on LAN)
https://192.168.10.80/#token=<from ~/.openclaw/openclaw.json gateway.auth.token>

# Or generate a pre-auth URL from the CLI
docker compose -f hermes-config/openclaw/docker-compose.yml run --rm openclaw-cli dashboard --no-open

# Approve a device pairing request (first browser / CLI runtime)
docker compose -f hermes-config/openclaw/docker-compose.yml run --rm openclaw-cli devices list
docker compose -f hermes-config/openclaw/docker-compose.yml run --rm openclaw-cli devices approve <request-id>

# Inspect a running build
curl -s -u "$OPENCODE_USERNAME:$OPENCODE_PASSWORD" http://127.0.0.1:4096/session | jq '.[] | select(.title | startswith("build"))'

# Abort a wedged build
curl -s -u "$OPENCODE_USERNAME:$OPENCODE_PASSWORD" -X POST http://127.0.0.1:4096/session/<id>/abort

# Stop a prototype without removing its image/data
docker compose -f /home/admin/code/hermes-config/prototypes/<slug>/docker-compose.yml down

# Fully remove a prototype (container + image + data + port registry entry)
docker compose -f .../<slug>/docker-compose.yml down -v
docker rmi <slug>:latest
sudo rm -rf /home/admin/code/hermes-config/prototypes/<slug>
# also edit /home/admin/code/hermes-config/prototypes/.registry/ports.json
```
