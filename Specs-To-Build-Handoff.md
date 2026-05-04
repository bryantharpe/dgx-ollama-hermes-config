# Specs → Build handoff (skill → plugin → subagent)

How clicking "yes, build it" in chat actually starts a docker container.

> Companion to `Meeting-Transcript-To-Prototype.md` (which covers the wider system). This doc zooms into the **single moment of handoff** between the propose skill and the build pipeline.

---

## TL;DR

The propose skill writes specs and asks "build it?". When you say yes:

1. **Captain Nemo** (the `main` agent) calls a plugin tool **`prototypes.build`**, which does NO building — it just validates inputs and **returns a structured `spawnArgs` payload**.
2. Nemo then calls the OpenClaw built-in **`sessions_spawn(...spawnArgs)`** to start a *new session* belonging to a *separate agent* (the **`prototype-builder` subagent**).
3. The prototype-builder runs autonomously: reads the specs, writes code, runs `docker compose up`, calls `prototypes.verify`, then `prototypes.archive`, then ends.
4. Nemo polls and reports back to you in chat.

Both agents are bound to the same model (`vllm/qwen3.6-27b-int4:128k` as of the 2026-05-03 cutover).

---

## Sequence — what happens after you say "build it"

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant N as Captain Nemo<br/>(main agent)
    participant P as openclaw-prototypes<br/>plugin (in gateway)
    participant S as sessions_spawn<br/>(OpenClaw built-in)
    participant B as prototype-builder<br/>(subagent, new session)
    participant D as Docker daemon<br/>(host socket)

    Note over U,N: Phase 4 of meeting-transcript-to-specs<br/>specs already on disk; chat shows "revise / stop / build?"
    U->>N: "yes, build it"
    Note over N: Reads SKILL.md Phase 4:<br/>"call prototypes.build → sessions_spawn(...spawnArgs)"

    N->>P: prototypes.build(slug, feature="prototype")
    Note right of P: src/build.ts<br/>1. validate slug regex<br/>2. confirm openspec/changes/<feature>/ exists<br/>3. compose `task` prompt<br/>4. return spawnArgs
    P-->>N: {ok: true, spawnArgs: {...}, next: "Call sessions_spawn"}

    N->>S: sessions_spawn(agentId="prototype-builder",<br/>task=..., cwd=slugDir, runTimeoutSeconds=3600, ...)
    S->>B: create new session,<br/>load builder workspace,<br/>send `task` as initial user message
    S-->>N: {sessionId: ...} (returns immediately;<br/>build runs in background)

    Note over B,D: Build runs autonomously
    B->>B: Read proposal.md / design.md / tasks.md
    B->>P: prototypes.allocate(slug)<br/>(if not already seeded)
    P-->>B: copies _template/ → slugDir,<br/>reserves port in .registry/ports.json
    B->>B: Write code (5 file classes only):<br/>requirements.txt, schema.sql,<br/>seed.py, api.py, frontend/*
    B->>D: docker compose up -d --build<br/>(via /var/run/docker.sock)
    D-->>B: container healthy
    B->>P: prototypes.verify(slug) — pre-archive gate
    P->>D: docker exec curl /api/* + /static/*<br/>+ schema vs seed column check
    P-->>B: {ok: true, failures: []}
    B->>P: prototypes.archive(slug, feature)<br/>(MUST be last call — Wrapper Contract B)
    P-->>B: mv openspec/changes → openspec/archive
    B-->>S: end turn (final summary text + demo URL)

    Note over N,B: Meanwhile Nemo polls
    loop until subagent terminates
        N->>S: sessions_history / session_status
        S-->>N: latest progress + part_count
        N-->>U: relay updates in chat
    end
    S-->>N: subagent terminal
    N-->>U: "prototype live at http://host:<port>/"
```

---

## Each component, with file paths

### 1. The propose skill — `meeting-transcript-to-specs`

- **Active install:** `~/.openclaw/skills/meeting-transcript-to-specs/SKILL.md`
- **Phase 4 instruction (line 87):** *"call `prototypes.build(slug, feature)` to construct the spawn args, then `sessions_spawn(...spawnArgs)` to start the build agent"*
- The skill never builds anything itself. Its job ends at writing the three OpenSpec files and asking the user.

### 2. The plugin — `openclaw-prototypes`

- **In-container path:** `/home/node/.openclaw/plugins/openclaw-prototypes/`
- **Plugin id:** `prototypes` (registered via `index.ts`, declared in `openclaw.plugin.json`)
- **Default `prototypesRoot`:** `/home/node/prototypes/` (host: `hermes-config/prototypes/`)
- **Default port range:** 9000–9099
- **Hindsight bank for `store_spec`:** `bryan-prototypes`

Six tools the plugin registers (in `index.ts` order):

| Tool                       | Source file        | Who calls it                          | What it does                                                                                              |
|----------------------------|--------------------|---------------------------------------|-----------------------------------------------------------------------------------------------------------|
| `prototypes.allocate`      | `src/allocate.ts`  | `prototype-builder` (build start)     | Copies `_template/` into `prototypes/<slug>/`, reserves a port in `.registry/ports.json`                  |
| `prototypes.list`          | `src/list.ts`      | `main` (Nemo, when asked)             | Lists known prototypes + ports                                                                            |
| `prototypes.store_spec`    | `src/store-spec.ts`| `main` (end of propose skill)         | Retains the spec to Hindsight bank `bryan-prototypes` for cross-prototype recall (failure non-fatal)      |
| `prototypes.archive`       | `src/archive.ts`   | `prototype-builder` (last call)       | `mv openspec/changes/<feature>/ → openspec/archive/<feature>/` — Wrapper Contract B                       |
| `prototypes.verify`        | `src/verify.ts`    | `prototype-builder` (pre-archive gate)| `docker exec curl` every `/api/*` route + `/static/*` URL; schema-vs-seed column drift check               |
| **`prototypes.build`**     | `src/build.ts`     | `main` (Nemo, after user approval)    | **Validates + returns `spawnArgs`. Does NOT build.** Hands the keys to `sessions_spawn`.                  |

### 3. `prototypes.build` — the handoff itself

`src/build.ts` does exactly four things — no Docker, no model calls, no code:

```typescript
async execute(_id, params) {
  // 1. validate slug + feature against ^[a-z][a-z0-9-]{1,63}$
  // 2. assert prototypesRoot/<slug>/openspec/changes/<feature>/ exists
  // 3. compose task prompt:
  const task = [
    `Build the prototype at ${slugDir}.`,
    ``,
    `Spec directory: ${changesDir}`,
    `Slug: ${slug}`,
    `Feature: ${feature}`,
    ``,
    `Read proposal.md / design.md / tasks.md from the spec directory,`,
    `then implement per your AGENTS.md operating guide. Call`,
    `prototypes.verify(slug=...) before archive. End with`,
    `prototypes.archive(slug=..., feature=...).`,
  ].join("\n");
  // 4. return spawnArgs (NOT a session id — Nemo still has to spawn it)
  return {
    spawnArgs: {
      runtime: "subagent",
      mode: "run",
      agentId: "prototype-builder",
      task,
      cwd: slugDir,
      runTimeoutSeconds: timeoutSeconds,  // default 3600
      label: `build ${slug}/${feature}`,
    },
    next: "Call sessions_spawn with the spawnArgs above to start the build.",
  };
}
```

### 4. `sessions_spawn` — the actual spawn

OpenClaw built-in (not in the plugin). It:

- Creates a brand-new session for `agentId: "prototype-builder"`
- Loads that agent's workspace (`builder-workspace/AGENTS.md`, etc — the prototype-builder has its OWN workspace, separate from Nemo's `~/.openclaw/workspace/`)
- Feeds `task` as the first user message of the new session
- Sets `cwd` to `prototypes/<slug>/`
- Returns the session id immediately — the build runs in the background (Nemo doesn't block)

### 5. The `prototype-builder` subagent

- **Definition:** `~/.openclaw/openclaw.json` → `agents.list[id=prototype-builder]`
- **Workspace AGENTS.md:** `~/.openclaw/plugins/openclaw-prototypes/builder-workspace/AGENTS.md` (in-container)
- **Tools:** `coding` profile + `prototypes.allocate / archive / verify`
- **Denied:** `sessions_spawn` (so it can't spawn its own subagents), `browser`, `canvas`
- **Sandbox:** `off` (it needs the docker socket)
- **Model:** `vllm/qwen3.6-27b-int4:128k` (same as Nemo)

The builder's AGENTS.md enforces three Wrapper Contracts that override anything else:

- **A) Task bookkeeping** — flip `- [ ]` to `- [-]` before each task, `- [x]` after. The change file is the live progress signal.
- **B) Archive on turn end** — last tool call MUST be `prototypes.archive`. Always. Even on failure. Even on giving up.
- **C) Stop-on-failure** — if `docker compose up` or `prototypes.verify` fails, do NOT edit-loop the skeleton. Emit error → summary → archive → end.

And the "5 file classes" the builder is allowed to touch:

1. Python deps → append to `requirements.txt`
2. Tables → append to `src/database/schema.sql`
3. Seed data → append to `src/database/seed.py` (INSERT OR IGNORE for idempotency)
4. Routes → append to `src/server/api.py` (reuse existing `get_db` / `read_json` / `write_json`)
5. UI → edit `src/frontend/index.html`; new JS/CSS under `src/frontend/js/` and `src/frontend/css/`

Everything else (`Dockerfile`, `docker-compose.yml`, `start.sh`, `main.py`, etc.) is correct-by-construction from `_template/` and MUST NOT be edited.

---

## Why two separate agents?

| Concern              | Captain Nemo (main)                       | Prototype Builder (subagent)              |
|----------------------|-------------------------------------------|-------------------------------------------|
| **Job**              | Conversational orchestrator               | Headless coder                            |
| **Tools**            | `messaging` profile + `prototypes.build` + `sessions_spawn` + `prototypes.list / verify / store_spec` | `coding` profile + `prototypes.allocate / archive / verify` |
| **Docker socket?**   | No                                        | Yes (sandbox off, mounted)                |
| **Can spawn subagents?** | Yes (allowed: `prototype-builder`)    | No (denied)                               |
| **Workspace context**| `~/.openclaw/workspace/AGENTS.md` (Nemo's persona, broad) | `builder-workspace/AGENTS.md` (build invariants, narrow) |
| **Lifetime**         | Long-lived per chat session               | One spawn per build, ends after archive   |

This split is intentional: the orchestrator stays light (small system prompt, no heavy build context), and the builder gets a narrow, opinionated guide (5 file classes, 3 wrapper contracts, no chit-chat).

---

## Where the candidate model is exercised

The eval harness's `agent_prototype` probe scores the *whole pipeline*. With both agents bound to the same `vllm/qwen3.6-27b-int4:128k`, a single run exercises the model in **two distinct roles**:

| Role          | Model needs to…                                                                          |
|---------------|------------------------------------------------------------------------------------------|
| Orchestrator (Nemo) | Read transcript → invoke propose skill → write 3 spec files → ask user → invoke `prototypes.build` → invoke `sessions_spawn` → poll `sessions_history` → relay results |
| Coder (builder)     | Read 3 spec files → plan tasks → write SQL/Python/HTML → run docker compose → recover from any error → call verify → call archive |

A model that's great at coding but terrible at tool-call sequencing will fail the orchestrator role even if the coder role would have shipped clean code, and vice versa. That's the "ecosystem" signal the probe is designed to surface.

---

## Failure modes to watch for

| Symptom in chat                                                | Where to look                                                                 |
|----------------------------------------------------------------|--------------------------------------------------------------------------------|
| "I called prototypes.build but no container appeared"          | Nemo forgot the second step. Check chat for `sessions_spawn` after `prototypes.build` — the plugin only returns args; spawn is required. |
| `spec directory does not exist: ...`                           | Propose skill wrote specs to wrong path, or slug mismatch. Check `prototypes/<slug>/openspec/changes/prototype/`. |
| Builder never calls `prototypes.archive`                       | Wrapper Contract B violation. Look at builder's last 3 tool calls — should always end on archive. |
| `prototypes.verify` returns failures, builder ignores them     | Wrapper Contract C violation. Builder should fix in one round, then archive even if still red, then end. |
| Nemo loops on `prototypes.build` instead of progressing        | Nemo doesn't know it's already built. Check whether the previous archive ran. |
| Build "succeeded" but `http://host:<port>/` is 502             | Container started but app crashed on boot. Usually schema/seed drift — `docker logs <slug>` shows the SQL error. |

---

## Quick command cheats

```bash
# Inspect the plugin source as-installed (in-container, since the host bind is empty)
docker exec openclaw-gateway ls /home/node/.openclaw/plugins/openclaw-prototypes/src

# See which tools an agent has access to (reads from openclaw.json)
jq '.agents.list[] | {id, model, tools}' ~/.openclaw/openclaw.json

# See current port allocations
cat /home/admin/code/hermes-config/prototypes/.registry/ports.json | jq

# See the most recent prototype-builder session
ls -lat ~/.openclaw/agents/prototype-builder/sessions/ 2>/dev/null | head -5

# Tail a running build
docker compose -f /home/admin/code/hermes-config/prototypes/<slug>/docker-compose.yml logs -f
```
