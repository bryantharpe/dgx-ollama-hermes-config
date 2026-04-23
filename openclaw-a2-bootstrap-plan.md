# OpenClaw A2 — Finish Bootstrap

**Date:** 2026-04-22
**Scope:** Gap-analysis item **A2** from `openclaw-gap-analysis.md`.
**Goal:** Complete the first-run bonding ritual so the OpenClaw agent wakes up with continuity — a populated `IDENTITY.md`, `USER.md`, and `TOOLS.md`, a curated `SOUL.md`, and no lingering `BOOTSTRAP.md`. Every future session will load these as memory, per `AGENTS.md`'s "Session Startup" convention.

> **Naming note:** "OpenClaw" = the agent/harness running in the gateway container. "Hermes" = the model tag currently wired as its brain (`hermes-orchestrator:qwen3.6-128k`). The point of the ritual is for the OpenClaw agent to *pick its own name* — so we deliberately don't call it "Hermes" below.
**Effort:** S.
**Blast radius:** local files under `~/.openclaw/workspace/`. No container restart required. Nothing external touched.

---

## Current state (verified 2026-04-22)

| File | State | Source |
|---|---|---|
| `IDENTITY.md` | 636 B — default template (placeholders only) | needs conversation |
| `USER.md` | 477 B — default template | needs conversation |
| `SOUL.md` | 1673 B — already populated with substantive content; not default | optional tune-up |
| `TOOLS.md` | 860 B — default template | can be pre-seeded from infra (my work) |
| `BOOTSTRAP.md` | 1471 B — still present; its own instructions say to delete when bonding completes | delete at end |
| `HEARTBEAT.md` | 193 B — template-only, belongs to gap-analysis item **B2**, not A2 | out of scope |
| `MEMORY.md` | missing | out of scope for A2 — grows organically per `AGENTS.md` |
| `CLAUDE.md` in workspace | missing | intentional — that's a Claude Code convention, not OpenClaw's |

## Split of work

### Part 1 — DevOps prep (my work, pre-ritual)

1. **Snapshot** the four workspace files (`IDENTITY.md`, `USER.md`, `TOOLS.md`, `BOOTSTRAP.md`) to `.bak.2026-04-22` copies alongside them. Cheap insurance.
2. **Pre-seed `TOOLS.md`** with factual infrastructure notes I have visibility into and the OpenClaw agent would otherwise have to discover:
   - Docker services currently running on this host (names, ports)
   - OpenClaw's own ports (gateway `18789`, companion bridge `18790`, dashboard `9000`)
   - Ollama model catalogue + which tag the agent is currently wired to
   - LAN IP (`192.168.10.80`) and Caddy TLS endpoint
   - Key host paths (`~/.openclaw`, `prototypes/`, `hermes-config/`)
   - Known UID-mismatch caveat for the openclaw-dashboard container (from stored memory)
   Structure matches the "Examples" section of the template so the agent can extend it in the same shape. Mark the seeded section as "infrastructure facts — extend with your own device/preference notes" so the ritual still includes adding personal details (voice preferences, speaker names, etc.).
3. **Do NOT** pre-populate `IDENTITY.md` or `USER.md`. Those are the relational content the ritual is *for* — and `IDENTITY.md` specifically is where the agent chooses its own name. Writing them for it would defeat the point.
4. **Do NOT** delete `BOOTSTRAP.md` yet — the ritual instructs the agent to delete it at the end, and Bryant may want to confirm that happened.

### Part 2 — The ritual (Bryant + OpenClaw agent, in Control UI)

Per `BOOTSTRAP.md`:

1. In Control UI, start a fresh session. The OpenClaw agent should read `BOOTSTRAP.md` on startup and open with something like "Hey. I just came online. Who am I? Who are you?"
2. Conversationally settle:
   - Agent's **name**, **creature/nature**, **vibe**, **emoji** → agent writes `IDENTITY.md`.
   - Bryant's **name**, what to call him, **timezone**, context/care/projects notes → agent writes `USER.md`.
3. Optional: open `SOUL.md` together — it already has substantive content, but this is the window to tweak boundaries/voice while you're in the mood.
4. Optional: skim `TOOLS.md` — add personal devices/voices/preferences on top of the infrastructure seed.
5. Channel question ("just here, WhatsApp, or Telegram?") — **answer "just here for now"**; the external-channel wiring is gap-analysis **A3** and we're not ready for it until **A6** (role split) is done.
6. Agent deletes `BOOTSTRAP.md`. Done.

## Validation

- `wc -c ~/.openclaw/workspace/{IDENTITY,USER,TOOLS}.md` returns non-template byte counts.
- `grep -l "_Fill this in during your first conversation_" ~/.openclaw/workspace/IDENTITY.md` → no match (placeholder text replaced).
- `ls ~/.openclaw/workspace/BOOTSTRAP.md` → no such file.
- Next session startup in Control UI: agent references user by name and signature emoji unprompted.
- Vector memory (A1) should also capture the bonding conversation automatically — `~/.openclaw/memory/lancedb/memories.lance/` grows.

## Rollback

Every `.bak.2026-04-22` copy is next to its original. To undo:
```
for f in IDENTITY USER TOOLS BOOTSTRAP; do
  cp ~/.openclaw/workspace/$f.md.bak.2026-04-22 ~/.openclaw/workspace/$f.md 2>/dev/null
done
```
No container restart needed; the gateway reads these files lazily per session.

## Risks / knowns

- The agent has had intermittent tool-call timeouts today (2026-04-22 stall logs) — note this is in the OpenClaw runtime, independent of the Hermes model. If the ritual stalls mid-way, a half-completed `IDENTITY.md` is recoverable via the `.bak` snapshot.
- `autoCapture` is now on (A1), so the ritual conversation will be embedded into long-term memory. That is a feature here, not a risk — continuity of identity is literally the point.
- `TOOLS.md` seed will mention internal ports and the LAN IP but no secrets (no tokens, no vault keys). Safe to keep in the workspace.

---

## Execution log — 2026-04-22

### Part 1 (DevOps prep)
- Snapshots saved: `IDENTITY.md.bak.2026-04-22`, `USER.md.bak.2026-04-22`, `TOOLS.md.bak.2026-04-22`, `BOOTSTRAP.md.bak.2026-04-22`.
- `TOOLS.md` seeded (860 B → 4781 B) with two sections: **Infrastructure facts** (host, LAN IP, UID caveat, endpoints, docker services, model catalogue, paths, ports) and empty **Personal notes** scaffolding. No secrets.
- Side-verification: confirmed the port-9000 memory is still accurate — dashboard UI at `192.168.10.80:9000` is served via the gateway container's `8080:9000` publish because the dashboard container shares the gateway's network namespace. TOOLS.md reflects this correctly.

### Part 2 (ritual, in Control UI) — Bryan + the OpenClaw agent
Agent now identifies as **Wren** 🐦 — small observant bird, direct / dry vibe. Ritual outcomes on disk:
- `IDENTITY.md`: name, creature, vibe, emoji filled (avatar slot intentionally left empty).
- `USER.md`: name (Bryan), call-name (Bryan), timezone (CT/CDT). `Notes` and `Context` left to grow lazily.
- `SOUL.md`: three substantive additions — "never risk host hardware", "external-of-Docker actions always ask first", and a new **Proactivity** section ("only check in on things when Bryan asks").
- `BOOTSTRAP.md`: deleted. Ritual closed per its own instructions.
- Channel decision: "just here for now" — no new plugins/skills enabled, no companion paired. Clean.

### Deferred within A2 (explicitly optional)
- `IDENTITY.md` avatar slot (cosmetic).
- `USER.md` notes + context paragraph — intended to grow over time.
- `TOOLS.md` personal-notes section scaffolding (Cameras / TTS / SSH / device nicknames / preferences).

### Side observation
- `AGENTS.md` was also modified during the session (7874 → 7935 bytes). Not part of the ritual; looks like Wren making notes in its own home file. Not rolled back.

**Status: A2 closed.**
