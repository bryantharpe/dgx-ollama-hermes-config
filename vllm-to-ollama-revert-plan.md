# vLLM → Ollama Revert

**Date:** 2026-05-04
**Goal:** Move primary inference from `scitrera/dgx-spark-vllm:0.17.0-t5` (Intel/Qwen3.6-27B-int4-AutoRound + MTP=2) back to Ollama serving a similar Qwen3.6-27B GGUF. Preserve the 256K context window, tool-call capability, and OpenAI-compatible API contract that every downstream client depends on. Keep vLLM running but unused for a one-week soak as rollback path.
**Effort:** M — one focused session ~3–5 h for the cutover, plus a hands-off ~7-day soak before vLLM decommission.
**Blast radius:** medium. Every client config that names a model tag or inference URL is touched (`hermes-agent`, `opencode`, `~/.openclaw/openclaw.json`, `custom-models.json`, `dashboard-config/config.json`, `Open WebUI`). The cutover is reversible by a single `git revert` + container restart for the entire ~7-day soak window.

---

## Motivation (verified 2026-05-04)

vLLM's structural advantage on this host has shrunk to where the operating cost of the engine no longer pays for itself:

1. **Crash recurrence.** vLLM 0.17.0-t5 has crashed with `cudaErrorIllegalAddress` (engine death + container restart) ~8 times in the past two days. Both today's crashes (13:12:07 and 21:20:08) hit the same code path: `gpu_model_runner.py:250 → async_copy_ready_event.synchronize()`. Triggers correlate with long-prompt prefills on the AutoRound INT4 + MTP-augmented compile graph. Concurrency was 1 at both crashes; spec-decode wasn't even active for the failing step. This is a single-stream long-context bug, not a load issue.
2. **Original justification was MoE throughput.** vLLM's win was 35B-A3B-FP8 (MoE) at ~46–48 t/s — 3–4× Ollama's rate. We retired that model on 2026-04-28 in favor of dense 27B-INT4. Without MoE, vLLM-with-MTP is 20 t/s vs Ollama Q4 at ~10.6 t/s — only ~2× faster, and ~22% faster if MTP is disabled. The headache budget no longer matches the throughput delta.
3. **Upstream maintenance gap.** The scitrera vLLM track has been stalled at the same image since 2026-03-08. Their sglang track is publishing dev tags weekly; their llama.cpp track ships multiple times a day. We've started a local 0.19+ build pipeline (`dgx-spark-vllm/`) just to escape the stall — that's a substantial engineering investment driven entirely by the maintenance gap.
4. **Workaround pile.** Per-engine custom chat template (thinking-toggle), per-model parser flag selection (`qwen3_coder` vs `hermes` returning 400), prefix-caching disabled for Coder-Next due to mamba experimental warning, NVFP4 blocked on the stalled image, etc. Each item is small; cumulatively they're the tax we keep paying.

Ollama's tradeoffs in the other direction (slower decode, slower large-context TTFT, no chunked prefill / prefix caching) are accepted in exchange for: stable engine, active upstream, simpler tool-call story (single `PARSER` directive in the Modelfile), and faster small-context TTFT.

### Cross-engine perf, current data (from `eval/results/COMPARISON.md`)

| Engine + config | Decode t/s c=1 | TTFT @ 1k | TTFT @ 16k | Tools acc | Coding p@1 | Qual /5 |
|---|---|---|---|---|---|---|
| vLLM 27B-INT4 + MTP=2 | **20–22** | 4.45 s | 15.7 s | **0.950** | 0.600 | 3.20 |
| vLLM 27B-INT4 no MTP | ~12.9 | (similar) | (similar) | (same) | (same) | (same) |
| Ollama Q4 27B (abl) | 10.6 | **1.84 s** | 25.3 s | 0.893 | 0.600 | 3.40 |
| sglang NVFP4 27B | 12.4 | 0.50 s | 10.8 s | 0.821 | 0.600 | 3.90 |

Ollama is competitive on quality, slower on raw decode, faster on small-context TTFT, slower on large-context TTFT.

---

## Target stack

- **Engine:** Ollama (already in `docker-compose.yml`, currently dormant on host port `11434`).
- **Model:** `bartowski/Qwen3.6-27B-Instruct-GGUF:Q5_K_M` (~20 GB on disk, near-FP16 quality at ~80% of FP16 size). Pulled via `ollama pull hf.co/bartowski/...`.
- **Local tag:** `qwen3.6-27b:128k` (matches the existing client URL conventions; the `:128k` suffix is the canonical alias, not a literal context limit — actual context is 256K).
- **Context:** 262144 tokens, native for the Qwen3.6 family.
- **KV cache:** `q8_0` (32 GB at 256K — fits comfortably with the ~20 GB weights in 128 GB unified). Requires `OLLAMA_FLASH_ATTENTION=1`.
- **Tool-call capability:** `PARSER qwen3.5` directive in the Modelfile (handles the whole Qwen3.x MoE family architecture; structures `thinking`/`tool_calls` into separate response fields).
- **Internal URL:** `http://ollama:11434/v1` (drop-in replacement for `http://vllm:8000/v1`).
- **Concurrency:** `OLLAMA_NUM_PARALLEL=1` (matches vLLM's c=1 reality on this host; raising later is cheap if needed).
- **Pin-resident:** `OLLAMA_KEEP_ALIVE=-1` (keep the model loaded across requests; otherwise first request after idle pays the full load time).

### Memory budget at 256K context

```
Qwen3.6-27B has GQA: kv_heads=8, head_dim=128, layers≈64
KV cache  = ctx × kv_heads × head_dim × layers × 2(K+V) × bytes
          = 262144 × 8 × 128 × 64 × 2 × bytes
```

| KV dtype | KV cache @ 256K | Weights Q5_K_M | Total | Headroom in 128 GB |
|---|---|---|---|---|
| f16 (default) | ~69 GB | ~20 GB | ~89 GB | tight (other containers exist) |
| **q8_0 (chosen)** | **~34 GB** | **~20 GB** | **~54 GB** | **~74 GB free** |
| q4_0 | ~17 GB | ~20 GB | ~37 GB | ~91 GB free |

`q8_0` is the right pick: comfortable headroom, negligible quality vs f16, room to add a side container without crashes.

---

## Phased plan

### Phase 0 — Decide model + quant (15 min)

The vLLM-served `Intel/Qwen3.6-27B-int4-AutoRound` is a vLLM-specific quant with no GGUF equivalent. Pick a similar dense 27B GGUF:

| Tag | Size | Notes |
|---|---|---|
| `bartowski/Qwen3.6-27B-Instruct-GGUF:Q4_K_M` | ~17 GB | balanced; matches prior Ollama bench size |
| **`bartowski/Qwen3.6-27B-Instruct-GGUF:Q5_K_M`** | **~20 GB** | **default — quality bump from prior Q4 baseline, fits memory budget** |
| `bartowski/Qwen3.6-27B-Instruct-GGUF:Q6_K` | ~22 GB | near-FP16; bench against Q5 to see if worth +2 GB |
| `huihui-ai/Qwen3.6-27B-abliterated-GGUF:Q4_K_M` | ~17 GB | known-baseline (already in COMPARISON.md as `qwen3.6-27b-abl-q4-ollama`); use if we want zero re-baseline drift |

Decision: **start with `Q5_K_M`**. Bench it once; if `Q6_K` shows a meaningful eval jump, swap. The abliterated variant is held in reserve as a known-baseline fallback.

### Phase 1 — Pull and register the model (30 min)

```bash
docker exec -it ollama ollama pull hf.co/bartowski/Qwen3.6-27B-Instruct-GGUF:Q5_K_M
```

Author `Modelfile.qwen3.6-27b-q5_k_m` at the repo root, modeled after `Modelfile.qwen3.6-35b-a3b-q6-65k`:

```
FROM hf.co/bartowski/Qwen3.6-27B-Instruct-GGUF:Q5_K_M
PARAMETER num_ctx 262144
PARAMETER num_predict 16384
PARAMETER temperature 0.7
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"
PARSER qwen3.5
RENDERER qwen3.5
SYSTEM """You are a helpful assistant."""
```

Register: `docker exec ollama ollama create qwen3.6-27b:128k -f /Modelfile.qwen3.6-27b-q5_k_m`.

**Verify capabilities** before proceeding — the `PARSER` directive determines whether tools work:

```bash
docker exec ollama ollama show qwen3.6-27b:128k
# Capabilities block MUST list `tools`. If not, the PARSER line was ignored.
```

### Phase 2 — Compose changes (30 min)

Update the `ollama:` service block in `docker-compose.yml`:

```yaml
ollama:
  environment:
    - OLLAMA_KEEP_ALIVE=-1
    - OLLAMA_KV_CACHE_TYPE=q8_0
    - OLLAMA_FLASH_ATTENTION=1        # required for non-f16 KV cache
    - OLLAMA_NUM_PARALLEL=1
    - OLLAMA_NUM_GPU=999              # offload all layers to GPU
    # CUDA env (already there from vLLM era)
    - NVIDIA_VISIBLE_DEVICES=all
    - NVIDIA_DRIVER_CAPABILITIES=compute,utility
```

vLLM stays in compose, untouched. Both services run side-by-side throughout the validation phase.

### Phase 3 — Smoke tests (45 min)

Three gates, in order. Stop at the first failure.

```bash
# 1) Direct ollama — does the model respond at all?
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.6-27b:128k","messages":[{"role":"user","content":"pong"}],"max_tokens":20}'

# 2) Tool-call surface — PARSER directive working?
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"qwen3.6-27b:128k",
    "messages":[{"role":"user","content":"What is the weather in Paris?"}],
    "tools":[{"type":"function","function":{"name":"get_weather","parameters":{"type":"object","properties":{"city":{"type":"string"}}}}}],
    "tool_choice":"auto"
  }' | jq '.choices[0].message.tool_calls'
# Must return non-null tool_calls with name + arguments JSON.

# 3) 256K context — no OOM, returns within reasonable time
# (use the eval long_context probe as the prompt builder)
cd eval && .venv/bin/python -u runner.py --tier 1 \
  --endpoint http://localhost:11434/v1 \
  --model qwen3.6-27b:128k --judge none
# Expect: perf + tools + coding + long_context all complete cleanly.
```

### Phase 4 — Client cutover (1 h)

Change every reference from `qwen3.6-27b-int4:128k` (and `vllm:8000`) to `qwen3.6-27b:128k` (and `ollama:11434`).

| File | Change |
|---|---|
| `docker-compose.yml` (`hermes-agent` env) | `LLM_MODEL=qwen3.6-27b:128k`; `OPENAI_API_BASE_URL=http://ollama:11434/v1` |
| `docker-compose.yml` (`opencode` env) | model + base URL same as above |
| `~/.openclaw/openclaw.json` | provider block (`baseUrl`, `models[].id`); `agents.defaults.model.primary`; `main.model`; `prototype-builder.model` (4 fields). Backup before edit. |
| `opencode/opencode.json` | provider URL + default model id |
| `custom-models.json` | model entry |
| `openclaw/dashboard-config/config.json` | model tag |

Restart consumers in order: `hermes-agent`, `openclaw-gateway`, `opencode`, `open-webui`. Verify each:

```bash
# hermes-agent
curl -s -H "X-Hermes-API-Key: $HERMES_API_KEY" http://localhost:8642/v1/models | jq '.data[].id'

# openclaw — ping Captain Nemo end-to-end
docker compose -f openclaw/docker-compose.yml run --rm openclaw-cli \
  agent --agent main --message "Reply: pong" --json --timeout 60

# opencode — list sessions
curl -s -u "$OPENCODE_USERNAME:$OPENCODE_PASSWORD" http://localhost:4096/session | jq

# open-webui — visit http://localhost:8080, dropdown shows qwen3.6-27b:128k
```

### Phase 5 — Re-baseline the eval (45 min)

```bash
cd eval && source ~/.eval-keys
.venv/bin/python -u runner.py --tier full --judge opus46 \
  --endpoint http://localhost:11434/v1 \
  --model qwen3.6-27b:128k --max-cost 5.0
```

Compare against `qwen3.6-27b-abl-q4-ollama` row already in `COMPARISON.md`. Acceptance: **no regression vs that prior Ollama baseline**, and **`long_context` actually completes** (the failure mode that triggered this revert).

If long_context hits its own issue under Ollama, that's a different bug — surface and decide.

### Phase 6 — Soak (~7 days, hands-off)

Use the system normally. Telegram chats, prototype builds, Open WebUI sessions. Watch for:
- Tool-call regressions (Captain Nemo unable to call `prototypes.build` etc.)
- Long-context wedges (a transcript longer than ~30 K tokens triggering OOM or unresponsive)
- Quality drift on the prototype-build path (do the same transcripts produce comparable specs/code?)

Any regression: `git revert <cutover-commit>` + restart consumers; vLLM stays serving, fully operational throughout the soak.

### Phase 7 — Decommission vLLM (when soak passes, ~30 min)

Only run after at least 7 days of stable Ollama operation:

1. Drop the `vllm:` and `vllm-test-*` blocks from `docker-compose.yml`.
2. Move `vllm-templates/` → `legacy-vllm/vllm-templates/` (don't delete — useful reference for the sglang/NVFP4 path).
3. Move `dgx-spark-vllm/` → `legacy-vllm/dgx-spark-vllm/` (same reasoning; the local 0.19+ build pipeline stays as a future-options-preserved artefact, not as live infra).
4. Optional: drop `vllm_hf_cache` and `vllm_compile_cache` volumes (~20 GB freed). Keeping them costs nothing and accelerates a hypothetical future re-cutover.
5. Update `README.md` + `DEPLOYMENT.md` to reflect Ollama as the inference engine. (`Specs-To-Build-Handoff.md` references the served-model name only — no change needed if the new tag matches the alias.)
6. Update `CLAUDE.md` scope-of-ownership.

---

## Validation criteria

The revert is "done" when all of these pass:

- [ ] `docker exec ollama ollama show qwen3.6-27b:128k` lists `tools` in capabilities
- [ ] Direct `/v1/chat/completions` with tools returns structured `tool_calls`
- [ ] All five clients (hermes-agent, openclaw, opencode, open-webui, eval-harness) talk to Ollama with no fallback errors
- [ ] `eval/runner.py --tier full` completes end-to-end without engine death
- [ ] No regression vs `qwen3.6-27b-abl-q4-ollama` baseline on tools / coding / qualitative / agent_loop
- [ ] One real prototype build (e.g. recipe-keeper transcript) lands a working container
- [ ] One Telegram session with Captain Nemo runs cleanly for 5+ turns
- [ ] 7 days elapsed with no cutover-related rollback

---

## Rollback shape

For ~7 days the cutover is fully reversible without any data movement:

```bash
git revert <cutover-commit>            # restores all client configs
docker compose up -d hermes-agent openclaw-gateway opencode open-webui
# (vLLM was never stopped; clients now point at it again)
```

After Phase 7 (vLLM removed from compose), rollback requires bringing the `vllm:` block back from git history — still ~5 min, but a real edit rather than a one-shot revert.

---

## Decisions made

- **Q5_K_M GGUF over Q4_K_M** — the 27B Q4 from the prior bench scored qualitative 3.40, which left room to grow. Q5 fits the memory budget and gets us closer to FP16 quality.
- **q8_0 KV cache, not f16** — gives ~74 GB headroom in unified memory; allows a side container (ComfyUI etc.) without crashes. f16 KV at 256K is too tight on this host.
- **`OLLAMA_NUM_PARALLEL=1`** — matches vLLM's c=1 reality; raising later is cheap. Higher concurrency on Ollama is a separate experiment, not part of this revert.
- **Keep vLLM in compose during soak** — the rollback simplicity is worth ~20 GB of cold cache for a week.
- **`dgx-spark-vllm/` and `vllm-templates/` are preserved, not deleted** — they're R&D artefacts for the longer-term NVFP4 / sglang path, independent of which engine serves today.

---

## Open questions (deferrable)

- **Q6_K vs Q5_K_M** — worth a side-by-side eval after Phase 5 baseline lands. Q6 fits the budget; the question is whether the +2 GB buys measurable quality.
- **Long-context behavior under Ollama at 200 K+ tokens** — vLLM's chunked prefill is gone; Ollama processes the prompt linearly. TTFT at 256 K may be unpleasant. Acceptable for the prototype-builder path (specs are smaller); may matter for one-off long-doc summaries.
- **Should `OLLAMA_NUM_PARALLEL` go higher than 1?** — depends on whether interactive chat + a background prototype build want to overlap. Defer until soak surfaces a real conflict.
- **sglang as an even-better alternative** — if Ollama disappoints on quality, the sglang sidecar already running on `:8002` is the next stop, NOT a return to vLLM-INT4. The migration plan at `vllm-to-sglang-migration-plan.md` covers that path.
