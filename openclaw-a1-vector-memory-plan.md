# OpenClaw A1 — Vector Memory Plan

**Date:** 2026-04-22
**Scope:** Gap-analysis item **A1** from `openclaw-gap-analysis.md`.
**Goal:** Replace FTS-only memory with vector-backed recall via the bundled `memory-lancedb` plugin, using Ollama's `nomic-embed-text` as the local embedding endpoint.
**Credentials required:** none (local Ollama).
**Rollback:** trivial (delete one directory + revert one config block).

---

## Key facts that shape the plan (from reading the plugin source)

1. **`nomic-embed-text` is not in the plugin's hardcoded dimensions table.** The validator at `/app/extensions/memory-lancedb/config.ts` only knows about `text-embedding-3-small` (1536) and `text-embedding-3-large` (3072). Calling it without `embedding.dimensions` set will throw `Unsupported embedding model`. The config **must** explicitly set `"dimensions": 768`.
2. **`embedding.apiKey` is a required field** even for Ollama. The validator accepts a literal string; `"ollama"` is passed as a dummy. Avoid `${OPENAI_API_KEY}` form — env-var expansion throws if the var is unset.
3. **Plugin is bound via slots + entries**, not an `extensions` block:
   - `plugins.slots.memory = "memory-lancedb"` — selects the memory provider.
   - `plugins.entries["memory-lancedb"]` — holds `enabled` + `config`.

## Preconditions

1. `docker exec ollama ollama list` does not currently list an embedding model → will pull.
2. `openclaw-gateway` and `ollama` share a docker network (existing `models.providers.ollama.baseUrl=http://ollama:11434` proves gateway→ollama works).
3. Confirm source-of-truth for `openclaw.json`: the live file at `~/.openclaw/openclaw.json` vs the tracked template at `openclaw/openclaw.json` in this repo. Edit both if diverged.
4. `~/.openclaw/memory/main.sqlite` (current FTS store) stays untouched. LanceDB writes to `~/.openclaw/memory/lancedb/` (new directory). Rollback = delete that dir + revert the `plugins` block.

## Steps

### Step 1 — Pull the embedding model into Ollama

```
docker exec ollama ollama pull nomic-embed-text
```

Verify via the OpenAI-compatible endpoint from inside the gateway's network:

```
docker exec openclaw-gateway sh -c 'curl -s http://ollama:11434/v1/embeddings \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"nomic-embed-text\",\"input\":\"ping\"}" | head -c 200'
```

Expected: JSON with a 768-length `embedding` array.

### Step 2 — Patch `openclaw.json`

Add the top-level `plugins` block (doesn't exist today — confirmed `plugins: null`):

```json
"plugins": {
  "slots": { "memory": "memory-lancedb" },
  "entries": {
    "memory-lancedb": {
      "enabled": true,
      "config": {
        "embedding": {
          "apiKey": "ollama",
          "model": "nomic-embed-text",
          "baseUrl": "http://ollama:11434/v1",
          "dimensions": 768
        },
        "autoCapture": true,
        "autoRecall": true,
        "captureMaxChars": 500
      }
    }
  }
}
```

Leave `dbPath` unset → defaults to `~/.openclaw/memory/lancedb`. Leave `captureMaxChars` at 500 (default).

### Step 3 — Restart the gateway and watch startup

```
docker compose restart openclaw-gateway
docker logs -f openclaw-gateway | head -80
```

Look for: plugin loading without `Unsupported embedding model` / `embedding.apiKey is required` errors; `memory/lancedb/` appearing on host; first embedding request to Ollama.

### Step 4 — Smoke test recall

- Via Control UI, send a distinctive statement (e.g. "My favourite debugging port is 18790"), wait ~10s for auto-capture, open a new session, ask a paraphrased variant ("what port did I mention for debugging?"). Vector recall should surface it; FTS alone would miss on the paraphrase.
- Confirm rows in LanceDB: `ls -la ~/.openclaw/memory/lancedb/`. If the plugin exposes a `memory_recall` tool, invoke it directly.

### Step 5 — Backfill existing FTS memory (optional, second pass)

The old FTS store (29 chunks / 6 files) keeps working independently. The 16 daily files in `workspace/memory/` are the main recall surface. Two options:
- **Lazy:** let `autoCapture` rebuild from future conversations.
- **Active:** one-shot re-indexer that walks `workspace/memory/*.md` and calls `memory_store` per entry.

Recommend lazy first — measure real recall needs before doing the migration pass.

## Validation / acceptance

- `jq '.plugins' ~/.openclaw/openclaw.json` shows the new block.
- `sqlite3 ~/.openclaw/memory/main.sqlite 'select * from meta'` still shows the FTS row (old store intact).
- `~/.openclaw/memory/lancedb/` exists and grows after a few captures.
- A new session recalls a fact stated earlier via a paraphrased query.
- No new ERROR-level lines in `docker logs openclaw-gateway` since restart.

## Rollback

- Remove the `plugins` block from `openclaw.json` → gateway reverts to FTS-only default.
- `rm -rf ~/.openclaw/memory/lancedb/` — deletes the vector store only; FTS and session transcripts untouched.
- `docker compose restart openclaw-gateway`.

## Risks / knowns

- Plugin is `2026.4.1-beta.1` inside the image — still beta-tagged. Watch for startup warnings.
- `autoCapture: true` will start persisting conversational snippets. Reinforce "don't exfiltrate" in `SOUL.md`; consider a path-exclude list if private files start getting captured.
- The healthcheck skill flagged a gateway token-mismatch (1008 unauthorized) on 2026-04-22. *Probably* unrelated to this change — if it resurfaces on restart, it's a separate issue.

---

## Execution log — 2026-04-22

- **Step 1** — `nomic-embed-text` pulled into Ollama; `/v1/embeddings` confirmed 768-dim response from gateway network.
- **Step 2** — `plugins` block added to `~/.openclaw/openclaw.json`. Backup at `~/.openclaw/openclaw.json.bak.2026-04-22`. Repo template (`openclaw/openclaw.json`) deliberately not touched — it's diverged and the live file holds a gateway auth token that shouldn't propagate upstream.
- **Step 3** — gateway auto-reloaded on the config change, then received a manual `docker restart`. Both cycles ended with `memory-lancedb: initialized (db: ..., model: nomic-embed-text)`. No ERROR/FATAL.
- **Step 4** — smoke test passed (user-verified): sent a distinctive statement via Control UI, asked a paraphrased query in a new session, recall returned the expected answer. Host-side confirmation: `~/.openclaw/memory/lancedb/memories.lance/` created at 03:22 (60K), and gateway log shows 5× `memory-lancedb: injecting 1 memories into context` auto-recall events in the 5 minutes after first use.
- **Step 5** — deferred. Old FTS store (29 chunks, 6 files) is untouched. Decision: lazy re-population via `autoCapture` for now; revisit only if recall quality on older material is poor.

**Status: A1 closed.**

### Unrelated observations worth tracking separately
- `[agent/embedded] embedded run timeout` at 15000ms on `slug-gen-*` utility tasks — session-naming helper, not main chat. Pre-existing; not caused by this change but worth watching.
- Gateway `token_mismatch` (1008 unauthorized) warnings are still appearing — unchanged by this work.
