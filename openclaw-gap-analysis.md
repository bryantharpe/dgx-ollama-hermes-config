# OpenClaw Gap Analysis

**Date:** 2026-04-21
**Host:** DGX Spark (hermes-config)
**Install:** `ghcr.io/openclaw/openclaw:2026.4.1` as docker containers `openclaw-gateway` + `openclaw-cli` + `openclaw-caddy`
**Scope:** read-only analysis; nothing modified or installed.

> ### Status update — 2026-04-22
>
> One day after this analysis, executed against the Group A priorities. Snapshot of progress:
>
> - **✅ A1 — vector memory: DONE.** `memory-lancedb` plugin wired to `http://ollama:11434/v1` with `nomic-embed-text:latest` (768-dim); `autoCapture` + `autoRecall` on. FTS store preserved untouched at `~/.openclaw/memory/main.sqlite`; new vector store at `~/.openclaw/memory/lancedb/memories.lance/`. Smoke test confirmed auto-recall on paraphrased queries. Plan and execution log: `openclaw-a1-vector-memory-plan.md`.
> - **✅ A2 — bootstrap: DONE.** Bonding ritual completed in Control UI. The OpenClaw agent chose its own name: **Wren** 🐦 (small observant bird, direct/dry vibe). `IDENTITY.md`, `USER.md`, `TOOLS.md` (infra-seeded by DevOps + personal scaffolding), and `SOUL.md` (new boundary + proactivity additions) populated. `BOOTSTRAP.md` deleted. "Just here for now" channel decision honored. Plan and log: `openclaw-a2-bootstrap-plan.md`.
> - **✅ A4 — model identity: DONE** (before this review's execution work — done by Bryan directly). Current model: `ollama/hermes-orchestrator:qwen3.6-128k`, with `reasoning: true` and `maxTokens: 16384`. A Hermes-tuned Qwen3.6-35B-A3B at 128k context.
> - **✅ A3 — external channel: DONE** (by Bryan directly, 2026-04-22). **Telegram** wired via the bundled `@openclaw/telegram` plugin. Live config: `channels.telegram.enabled: true`, `dmPolicy: "pairing"`, `groupPolicy: "allowlist"`, `streaming: "partial"`. Bot token lives in the live `~/.openclaw/openclaw.json` only — not committed to this repo. The sibling `@openclaw/signal` extension was looked at as an alternative; Telegram won on integration maturity (Grammy SDK, throttler, runner, full Bot API via `@BotFather`) vs. Signal which has no SDK deps and a blurb that literally reads "more setup".
> - **○ A5, A6, B1–B6, C1–C7 — not yet started.**
>
> Re-ranked ordering: **A6 (URGENT) → B2 → A5 → B-series**. A6 moves up: the Telegram channel is live before the operator-role split, so the next device that pairs will still inherit `operator.admin`. B2 (populate `HEARTBEAT.md`) pairs naturally with the new channel — so first heartbeats do something useful when they arrive via Telegram.
>
> **Terminology clarification added post-facto:** "Hermes" is the *model tag* currently wired as OpenClaw's brain. "OpenClaw" is the *agent harness / platform*. "Wren" is the OpenClaw agent's chosen name from the A2 ritual. Where this document uses "Hermes" in a model-identity sense (esp. A4), that still reads right; where it refers to "the agent", read as "Wren / the OpenClaw agent".

> ### Status update — 2026-04-23
>
> Two days further on. Knocked out the A6 urgency and one B-series item:
>
> - **✅ A6 — operator role split + exec tightening: DONE.** Control UI device (phone browser at 192.168.2.3) rotated down to `operator.read + operator.write + operator.approvals` — `operator.admin` and `operator.pairing` dropped. Token + device envelope (`scopes` + `approvedScopes` in `paired.json`) aligned so a re-pair won't silently reissue. Runtime device (`clientId: cli`) kept at full scopes; it needs them. Exec policy flipped from `security: full / ask: off` to `security: allowlist / ask: on-miss / strictInlineEval: true` — unknown commands now prompt via the UI `exec.approval.requested` channel; inline interpreter eval (`python -c`, `node -e`) always prompts even when the interpreter is allowlisted. Also added `gateway.auth.rateLimit` (10 attempts / 60s / 300s lockout) since bind is `lan`, not loopback. `openclaw security audit`: went from **2 warn → 0 warn**. Commit: `62b6193`.
> - **✅ B4 — web-search adapter: DONE.** Brave Search API wired end-to-end. `BRAVE_API_KEY` lives in `openclaw/.env` (mode 600), passed through to `openclaw-gateway` and `openclaw-cli` via compose. `tools.web.search.provider: "brave"` + `plugins.entries.brave.enabled: true` in the tracked snapshot and live config. `plugins list` shows `Brave Plugin → loaded`; direct probe to `api.search.brave.com` from inside the gateway container returned HTTP 200. Commit: `0b96769`.
> - **Secondary snapshot refresh:** while in the tracked `openclaw/openclaw.json`, also committed the previously-uncommitted live-config snapshot drift (trustedProxies, hermes-orchestrator model, memory-lancedb, telegram shape, session-memory-embed hook). Tracked snapshot now matches live again.
> - **○ A5, B1, B2, B3, B5, B6, C1–C7 — not yet started.**
>
> Re-ranked ordering: **B2 → A5 → B1/B6 → B3/B5**. B2 (heartbeat payload) stays top — heartbeat's still burning tokens returning `HEARTBEAT_OK` on an empty template, and Telegram is live to deliver the output. A5 (cloud fallback) is second now that A6 is done (operator scope no longer a prerequisite). B1+B6 pair naturally: stand up vault for secrets first, then wire the first MCP server against it.
>
> **Appendix deltas:** *Paired devices:* 2 (not 3; down from earlier snapshot), scopes no longer uniform — one runtime at full `operator.*`, one UI at `read+write+approvals`. *`openclaw security audit`:* 0 critical / 0 warn. Everything else in the appendix is still accurate as of 2026-04-23.

---

## Phase 1 — Current Setup Inventory

### 1.1 Where things live

| Path / thing | Present? | Notes |
|---|---|---|
| `~/.openclaw/` (host) | ✅ | Bind-mounted to `/home/node/.openclaw/` in the gateway/cli containers |
| `~/.openclaw/skills/` (managed/user) | ✅ | 2 user skills; see §1.5 |
| `~/.agents/skills/` (personal) | ❌ | Directory does not exist |
| Bundled skills (`/app/skills/` in container) | ✅ | **55 bundled skills shipped with the image** |
| Bundled extensions (`/app/extensions/`) | ✅ | **85 extensions bundled**; only 41 `enabledByDefault: true` (mostly provider adapters); messaging channels are all opt-in |
| `openclaw.json` gateway config | ✅ | `~/.openclaw/openclaw.json` + tracked template at `openclaw/openclaw.json` in this repo |
| `SOUL.md` | ⚠️ default template | `workspace/SOUL.md` — default, un-customised |
| `IDENTITY.md` / `USER.md` | ⚠️ empty templates | Placeholder skeletons — bootstrap never completed |
| `BOOTSTRAP.md` | ⚠️ still present | Was supposed to be deleted after first-run bonding; first-run setup is incomplete |
| `CLAUDE.md` in workspace | ❌ | Not created |
| `AGENTS.md` | ✅ | Default template, unmodified |
| `HEARTBEAT.md` | ⚠️ empty template | No scheduled checks configured |
| `TOOLS.md` | ⚠️ empty template | No local device/host notes captured |

### 1.2 Channels wired up

| Channel | Bundled? | Enabled? | Notes |
|---|---|---|---|
| **Web chat / Control UI** | — core | ✅ | HTTP on `127.0.0.1:18789`, TLS via Caddy at `https://192.168.10.80/` with internal CA |
| WhatsApp | ✅ ext | ❌ | Opt-in, not configured |
| iMessage (via BlueBubbles or native) | ✅ ext × 2 | ❌ | Opt-in |
| Slack | ✅ ext | ❌ | Opt-in |
| Signal | ✅ ext | ❌ | Opt-in |
| Telegram | ✅ ext | ❌ | Opt-in |
| Discord | ✅ ext | ❌ | Opt-in |
| Matrix, MS Teams, Google Chat, IRC, LINE, Nostr, etc. | ✅ ext | ❌ | All opt-in |
| CLI | core | ✅ | `openclaw-cli` container, `docker exec -it openclaw-cli openclaw ...` |

**Reality:** only the web chat / Control UI is in active use. Bridge port `18790` is bound (companion-app pairing bridge) but no companion app is currently paired for an external channel.

### 1.3 Model provider

`openclaw.json.models.providers`:

```json
{
  "ollama": {
    "baseUrl": "http://ollama:11434",
    "api": "ollama",
    "models": [{
      "id": "qwen3.6-35b:128k",
      "reasoning": false,
      "contextWindow": 128000,
      "maxTokens": 8192
    }]
  }
}
```

Default agent model: `ollama/qwen3.6-35b:128k`.

**Is this the local Hermes fine-tune?** ⚠️ **No — this is the base Qwen3.6-35B-A3B (Q8_0) at 128k.** Ollama reports the model's system prompt as *"You are a helpful assistant…"*, not a Hermes persona. The Ollama cache does contain Hermes tags (`hermes4-70b:131k`, `hermes-architect:latest`, and `HermesModelfile` in this repo declares one `FROM qwen3.6-35b:128k`), **but openclaw itself is pointed at the base model, not at any Hermes tag**. Flagging explicitly because your brief said "Hermes fine-tune on Qwen3 35B A3B" — the config doesn't reflect that today.

The `reasoning: false` flag disables the model's native `<think>` channel, so the agent loses a capability the base model actually has (Ollama reports `thinking` in the model's capabilities list).

**Cloud fallback?** ❌ None. 41 cloud provider extensions are `enabledByDefault: true` (anthropic, openai, google, etc.) but **zero** are configured with credentials in `openclaw.json.models.providers` — so cloud models are reachable via adapter code but not routable from the agent.

### 1.4 Tools — enabled vs gated

```json
"tools": { "exec": { "security": "full", "ask": "off" } }
```

- `security: "full"` + `ask: "off"` means the exec tool is effectively ungated inside the container.
- `exec-approvals.json` has **accumulated an `allow-always` allowlist** of `ls`, `curl`, `cat`, `grep`, `echo`, plus several project-specific commands and `build-payload.sh`. Any first-time-new command should still prompt, but with `ask: off` the friction is low.
- Container runs as `node` (UID 1000) — no docker socket mounted, no privileged mode. Hardening at the docker layer is solid; the in-container permission posture is very permissive.

### 1.5 Skills installed (surfaced to the model)

From the last live session snapshot (`agents/main/sessions/sessions.json`), the agent's `resolvedSkills` includes exactly:

**Bundled (6):**
- `clawflow` — flow/orchestration substrate
- `clawflow-inbox-triage` — example ClawFlow pattern
- `healthcheck` — host security hardening
- `node-connect` — pairing diagnostics
- `skill-creator` — author/audit new skills
- `weather` — wttr.in / Open-Meteo

**User (2), in `~/.openclaw/skills/`:**
- `meeting-transcript-to-specs`
- `meeting-specs-to-prototype` (proven handoff to OpenCode build agent)

**What's gated off:** `openclaw.json.skills.allowBundled: []` — explicitly empty, which hides the other 49 bundled skills (among them: `slack`, `discord`, `whatsapp`, `imsg`, `gmail`, `apple-*`, `notion`, `github`, `gh-issues`, `obsidian`, `spotify-player`, `session-logs`, `summarize`, `tmux`, `xurl`, `video-frames`, `voice-call`, `mcporter`, `openai-whisper`, `sherpa-onnx-tts`, `weather`/`summarize`, etc.). They're on disk but invisible to the model until allowlisted.

### 1.6 MCP servers

| Item | State |
|---|---|
| MCP support compiled into gateway | ✅ **First-class** — `@modelcontextprotocol/sdk` is imported in the shipped `/app/dist/mcp/plugin-tools-serve.js` and a standalone `/app/dist/mcp-cli-*.js` exists |
| MCP servers wired in `openclaw.json` | ❌ None configured |
| `mcporter` CLI skill | ✅ on disk (`/app/skills/mcporter/`) but not in `allowBundled` |
| `mcporter` binary installed | ❌ Not on `$PATH` in the container |

Net: **OpenClaw is MCP-capable out of the box, but no MCP servers are registered and no MCP client CLI is active.** This is one of the largest unrealised capabilities.

### 1.7 Heartbeat / scheduler

- Heartbeat **is active** — recent `sessions.json` shows `origin.label: "heartbeat"` on 9 origins, with the last heartbeat poll at 2026-04-21 17:15 UTC.
- `HEARTBEAT.md` is the default template (empty) — so heartbeats currently fire, the agent reads an empty file, and it returns `HEARTBEAT_OK` without doing anything useful. Tokens burn; nothing productive happens.
- No dedicated cron/scheduler rows in `tasks/runs.sqlite` (all 56 rows are `runtime=cli`, not `cron`). Based on `AGENTS.md` guidance, a cron subsystem exists but isn't in use on this install.

### 1.8 Memory backend

`~/.openclaw/memory/main.sqlite` (229 KB):

- Tables: `meta`, `files`, `chunks`, `embedding_cache`, `chunks_fts` (FTS5 shadow tables)
- Row counts: **29 chunks, 6 files, 0 embeddings**
- Meta row: `{"model":"fts-only","provider":"none",...}` — **FTS-only, no vectors**
- `sqlite-vec` extension: **not loaded** (no vec-prefixed virtual tables)
- `memory-lancedb` extension: bundled (opt-in); expects OpenAI-compatible embedding endpoint (Ollama's `/v1` would work) — **not enabled**
- No auto-capture / auto-recall configured

Workspace long-term memory (`~/.openclaw/workspace/memory/`): 10 daily `.md` files (Apr 19–20), no `MEMORY.md` curated summary — a manual journaling convention from `AGENTS.md`.

Sessions transcript volume: **1 main session file, 607 JSONL lines, 604 KB** (`d06f56ee-….jsonl`). Fairly small so far.

### 1.9 Auth / consent / "agent-passport" equivalent

OpenClaw implements this as **device-pair + scope tokens + per-command approvals**:

- Ed25519 keypair in `identity/device.json`
- `devices/paired.json`: 3 devices currently paired (the gateway runtime itself, and 2 Control-UI browser sessions), all at scope set `[operator.admin, operator.read, operator.write, operator.approvals, operator.pairing]` — i.e. **one effective role: god-mode operator**. No separate `read-only` or `guest` role in use.
- `exec-approvals.json`: per-command allowlist, currently 10 `allow-always` entries.
- TLS-pinned gateway token in `openclaw.json.gateway.auth.token`.

Net: consent plumbing exists, but as configured it's coarse-grained and permissive. There's no equivalent of an `agent-passport` per-channel scope token (e.g. "this Slack-bot device can only reply in #general"). One operator role for all callers.

---

## Phase 2 — Gap Analysis vs. Generalised Assistant

### 2.1 Eight capability areas

| # | Capability | State | What's there | What's not |
|---|---|---|---|---|
| 1 | **Memory & context persistence** | **PARTIAL** | SQLite session store; FTS index over 29 memory chunks; per-day `memory/YYYY-MM-DD.md` files; explicit compaction convention in `AGENTS.md` | No vector recall (FTS-only, `provider: none`); no `sqlite-vec`; `memory-lancedb` bundled but not configured; no `MEMORY.md` curated; compaction is prompted but not automated |
| 2 | **Multi-channel communication** | **MISSING** | Web chat + CLI only. Bridge port ready. Bundled extensions for all major channels. | No WhatsApp/Slack/iMessage/Signal/Telegram/Discord channel wired. No bundled `slack`/`whatsapp`/`imsg` skill in `allowBundled`. No companion-app paired. |
| 3 | **Filesystem + shell execution** | **PARTIAL** | `exec` works; docker-level sandbox (no docker socket, no host FS beyond `~/.openclaw` and `prototypes/`); allow-always learning | In-container `ask: off` + `security: full` is effectively ungated; single operator role; no sub-agent with write-denied scope for risky paths |
| 4 | **Web access + browser automation** | **PARTIAL** | `browser` extension `enabledByDefault: true`; Playwright-core bundled at `/app/dist/extensions/diffs/node_modules/playwright-core/` incl. MCP bundle | No web-search skill active (Brave/DDG/Exa/Tavily/Firecrawl/Perplexity all opt-in and off); no `xurl` in `allowBundled`; no browser-control skill surfaced to the model |
| 5 | **Proactive heartbeat / scheduling** | **PARTIAL** | Heartbeat actively polling (9 recent); `AGENTS.md` documents the cron-vs-heartbeat discipline | `HEARTBEAT.md` is an empty template, so polls are no-ops; no cron jobs registered; no inbox/calendar/notification checks wired |
| 6 | **Multi-session orchestration** | **PRESENT (fragile)** | `clawflow` runtime in the active skills; proven OpenCode handoff (meeting-specs-to-prototype); `tasks/runs.sqlite` tracks child sessions | 32/56 CLI task runs failed (~57% failure rate) — the pattern works but isn't hardened; no automatic retry/recovery beyond the steer-once pattern; single "main" agent identity (no `coder`, `researcher`, etc.) |
| 7 | **Dynamic tool/skill discovery (MCP)** | **PARTIAL** | MCP SDK compiled in; gateway has routes scoped `mcp*`; `mcp-cli` binary shipped; `mcporter` skill on disk | Zero MCP servers configured; `mcporter` binary not installed; no MCP skill in `allowBundled`; no dynamic tool discovery at runtime |
| 8 | **Identity / credentials / consent gating** | **PARTIAL** | Device-pair (Ed25519) + scope token + `exec-approvals.json` allowlist; TLS via Caddy | One role (`operator.admin`) for every paired device; per-channel identity not scoped (if Slack were wired, that device would inherit god-mode); no secret store (vault container exists at 127.0.0.1:8200 but openclaw isn't talking to it) |

### 2.2 Local-model specifics

| Question | Answer |
|---|---|
| **Is the configured model actually the Hermes fine-tune?** | **No.** Config points at `ollama/qwen3.6-35b:128k` which is the base Qwen3.6-35B-A3B Q8 with system prompt *"You are a helpful assistant"*. Hermes tags exist in Ollama (`hermes4-70b:131k`, `hermes-architect:latest`) but aren't referenced. |
| **Reliable structured tool-calls?** | **Qualified yes, with friction.** Qwen3.6-A3B advertises `tools` capability in Ollama. openclaw disables `reasoning: false` → no `<think>` preamble. No grammar / JSON-mode / outlines constraint is wired; the gateway relies on the model emitting native tool calls. In practice the tasks DB shows **32/56 task runs failed** and the most recent build session stalled at `part_count=37` — tool-call brittleness is a real recurring failure mode. |
| **Fallback to a cloud model?** | **No.** Only the `ollama` provider is populated in `models.providers`. 41 cloud adapter extensions are bundled and default-enabled, but no API keys → no routable cloud model. |
| **Context window** | 128k declared (`contextWindow: 128000`); Ollama model supports up to 262144; `maxTokens: 8192` output cap is conservative. |

---

## Phase 3 — Prioritised Recommendations

### Group A — Foundational gaps (fix first to earn the "general" claim)

| # | What | Why it matters | Implementation path | Effort | Security/trust |
|---|---|---|---|---|---|
| ✅ A1 | **Enable vector memory** (`memory-lancedb` + local embed endpoint) | FTS can't answer "what did we decide about X last month" fuzzily. Vector recall is the difference between useful long-term memory and a keyword search. | Add `memory-lancedb` to `openclaw.json` plugins with `embedding.baseUrl=http://ollama:11434/v1`, an embedding model (e.g. `bge-m3` or `nomic-embed-text` pulled into Ollama), `autoCapture: true`, `autoRecall: true`. Migrate existing 29 FTS chunks by re-indexing. | **M** | Memory will capture more — reinforce the "don't exfiltrate" red line in SOUL, and consider a `memory.exclude` path list for secrets. |
| ✅ A2 | **Populate `IDENTITY.md` / `USER.md` / `SOUL.md`, delete `BOOTSTRAP.md`** | Every session currently starts cold with no idea who the user is. The "general assistant" vibe depends on continuity. | One conversational pass with the agent to fill the three files; delete BOOTSTRAP.md per its own instructions. | **S** | Low — local files only. |
| ✅ A3 | **Wire at least one external channel** (recommend Slack *or* Telegram first) | Without this, it's not an *assistant* — it's a web chat window. Proactive reach-out is impossible. | Add `slack` (or `telegram`) to `openclaw.json` plugins with bot token, add the bundled skill of the same name to `skills.allowBundled`. | **M** | Channel bot token = external surface. Scope the Slack app narrowly (one workspace, one channel for 1:1 DM first); add a per-channel scope token and restrict that device's `operator.write`. |
| ✅ A4 | **Switch agent to the Hermes fine-tune (if that's actually what you want)** — or explicitly decide to stay on base Qwen3.6 | Your stated goal was "Hermes fine-tune", current config uses base Qwen3.6 with a generic system prompt. Either rename the decision or change the config. | Option (a): point `agents.defaults.model.primary` at `ollama/hermes4-70b:131k` or a dedicated `hermes-qwen3.6-35b` Modelfile. Option (b): keep base but update the system prompt and this memo to reflect the deliberate choice. | **S** | If Hermes removes some safety/alignment tuning, weigh that against broader scope of tasks and channels. |
| A5 | **Wire a cloud fallback provider** (Anthropic or OpenAI) with a narrow routing rule | Qwen3.6 tool-call failure rate on your existing workload is ~57%. A cloud fallback for "when local fails N times on a tool-use turn" is a force multiplier disguised as a foundational gap. | Add `anthropic` (or `openai`) to `models.providers` with an API key from vault; add a per-agent `model.fallback` chain or `llm.onToolFailure` rule if openclaw supports it; otherwise add an `escalate` skill. | **M** | Cloud calls ship prompts off-box. Scope what gets routed (e.g. only explicit `/escalate`, never heartbeat). Gate with per-call consent or a hard token cap. |
| ✅ A6 | **Tighten consent gating** — at least split operator roles | Right now the Control UI browser device has the same `operator.admin` scope as the runtime. If/when Slack is wired, that bot device will inherit everything. | Add a `reader` and `responder` scope set; downgrade the UI device to `responder` unless `operator.admin` is explicitly claimed; flip `tools.exec.ask` from `off` to `ask-once-per-pattern` for network-touching commands. | **M** | Pure upside — reduces blast radius. |

### Group B — Force multipliers (already works, unlocks meaningfully more)

| # | What | Why | Implementation | Effort | Security |
|---|---|---|---|---|---|
| B1 | **Add MCP servers** — start with `gmail`, `github`, `linear` (whichever you use) | MCP is compiled in and dormant. A few MCP servers unlock dozens of tools without authoring skills. | Install `mcporter` (`npm i -g mcporter` inside the container or a sidecar), add `mcporter` skill to `allowBundled`, `mcporter auth <server>`, add server entries. | **M** | Each MCP server is a credential surface. Store tokens in vault; confirm the MCP server is pinned by version. |
| B2 | **Populate `HEARTBEAT.md` with 3–4 concrete rotating checks** | Heartbeats fire already. Today they're no-ops. | List the checks from `AGENTS.md` section "Things to check" — inbox, calendar, weather, PR mentions — keyed to the channels/MCPs you wire. Add `memory/heartbeat-state.json` rate-limiting. | **S** | Heartbeats reaching out externally depends on A3+B1 — don't over-signal. |
| B3 | **Expand `skills.allowBundled`** with the no-auth skills that make the assistant feel generalist | 49 bundled skills are sitting dormant. `summarize`, `session-logs`, `tmux`, `xurl`, `video-frames`, `healthcheck` (already in), `weather` (already in), `mcporter` (depends on B1) all add surface with zero credential cost. | Edit `openclaw.json.skills.allowBundled` — explicit allowlist of 8–12 names. | **S** | Each skill = new attack surface for prompt injection. Review the ones that touch external URLs (`xurl`) before adding. |
| ✅ B4 | **Vendor a web-search adapter** (one of Brave / DDG / SearxNG / Exa) | `browser` extension + Playwright is already bundled — pairing it with a search API makes open-world research work. | Add e.g. `brave` provider + API key; add `browser` skill surface to `allowBundled` so the model knows it can browse; test. | **M** | External API call + fetched content in-context. Consider a URL allowlist for the heartbeat flow. |
| B5 | **Add per-session agent identities** (`coder`, `researcher`, `tidy`) | You already use the `build` OpenCode agent sub-agent pattern. Extending that to openclaw's own sub-agents gives you distinct model+skill+scope sets — easier to debug, easier to constrain. | Add entries under `agents.<name>.model`, `agents.<name>.skills.allowBundled`; invoke via `clawflow`. | **M** | Decomposition reduces blast radius — a `researcher` can have `operator.read` only. |
| B6 | **Wire the vault container for secrets** | HashiCorp Vault is running at `127.0.0.1:8200` but unused by openclaw. Storing `OPENCODE_PASSWORD`, Slack tokens, MCP server creds in vault with short-lived tokens beats `.env`. | Write a small bootstrap step in `bootstrap.sh` or an openclaw pre-start hook that pulls secrets from vault and injects them as env. | **M** | Strict win. Just ensure the vault root token isn't itself in `.env`. |

### Group C — Nice-to-haves (polish, niche domains)

- **C1 — `session-logs` skill**: condense transcripts into a MEMORY.md bulk-import pass during heartbeat quiet hours. **S.**
- **C2 — Voice in/out** (`talk-voice` is already enabled, `sag`/`openai-whisper` bundled): adds another modality, minor footprint. **S/M.**
- **C3 — Exact-timing cron for 1:1s / standups**: if Slack/Calendar is wired, cron for "0900 Monday, post weekly plan". **S.**
- **C4 — Companion phone app pairing** (Android/iOS): bridge port is already listening on 18790. If you want assistant-on-the-go. **M** — introduces a remote device surface; pair scopes carefully.
- **C5 — Grammar-constrained tool-call decoding**: configure Ollama to enforce a JSON grammar on tool-call turns (via `format: json` or a custom grammar if supported), cutting parse failures. **M** — investigation required; depends on the Qwen3.5 parser in the Modelfile.
- **C6 — Compaction policy**: the 607-line session JSONL is small today but grows unbounded. A compaction skill that summarises turns N..M into one system message past a threshold. **M.**
- **C7 — Per-channel "voice" tuning** (already called out in AGENTS.md: no markdown tables on Discord/WhatsApp, bullet lists instead) — codify as a skill or a system-prompt fragment tied to the `channel` value. **S.**

---

## Next 3 concrete actions

> **Update 2026-04-23:** A6 and B4 both shipped — see 2026-04-23 status block at top. New next 3:
>
> 1. **Populate `HEARTBEAT.md` (B2) with 3–4 concrete rotating checks.** Highest-payoff/lowest-effort item now: heartbeats fire hourly and burn tokens returning `HEARTBEAT_OK` on an empty template. With Telegram live, a useful payload ("any unread 1:1 Telegram DMs? any calendar event in the next 30 min? weather for CT?") makes the channel feel alive. Add `memory/heartbeat-state.json` rate-limiting so the agent doesn't re-signal the same check every hour.
> 2. **Wire a cloud fallback (A5) + vault for its key (B6 — ride-along).** Stand up `~/.openclaw/.env` reads from vault, add `anthropic` (or `openai`) to `models.providers` with a vault-issued key, then add a narrow routing rule ("on explicit `/escalate`, never heartbeat"). Mitigates the Qwen3.6 tool-call brittleness (57% failure in task logs). Scope gate now reliable thanks to A6.
> 3. **First MCP server (B1) — start with the one you actually use daily.** Install `mcporter` (sidecar or npm-global in the gateway), add `mcporter` to `skills.allowBundled`, `mcporter auth <server>` for gmail or github or linear, add the server entry under the MCP config. Tokens go into vault alongside A5's fallback key.

**Previous Next 3 (preserved):**

- **2026-04-22 revision** was A6 (urgent) → B2 → A5. A6 ✅ done 2026-04-23; B2 and A5 carry forward.
- **Original (2026-04-21):** A4 ✅ · A1 ✅ 2026-04-22 · A3 ✅ 2026-04-22.

---

### Appendix — raw signals worth knowing

- **Tool-call failure rate:** 32 failed / 23 succeeded / 1 timed_out in `tasks/runs.sqlite` (runtime=cli). 57% failure. Most recent build session aborted on a stall at `part_count=37` per `workspace/memory/2026-04-20-openclaw-control-ui.md`.
- **Skills gated off:** 49 of 55 bundled skills (`skills.allowBundled: []`).
- **Extensions gated off:** 44 of 85 (opt-in), including every messaging channel.
- **Providers configured:** 1 of 41 (`ollama` only).
- **MCP servers configured:** 0 (despite SDK being compiled in).
- **Paired devices:** ~~3 (all with full `operator.admin` scope)~~ → **2** as of 2026-04-23 (runtime at full scopes, Control UI at `read+write+approvals`).
- **Workspace daily memory files:** 10 (Apr 19–20, 2026), no curated `MEMORY.md`.
- **Bootstrap:** not completed (`BOOTSTRAP.md` still present, `IDENTITY.md`/`USER.md` empty).
