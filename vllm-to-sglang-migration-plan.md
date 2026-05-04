# vLLM → SGLang Migration

**Date:** 2026-05-02
**Goal:** Migrate the local LLM serving stack on the DGX Spark from `scitrera/dgx-spark-vllm:0.17.0-t5` to `scitrera/dgx-spark-sglang:0.5.10` (or a newer `0.5.10-*-dev` tag) running the same `Intel/Qwen3.6-27B-int4-AutoRound` model. Drive: vLLM has crashed ~8 times during the eval-harness session today (`cudaErrorIllegalAddress` on the MTP+spec-decode path under realistic load), and scitrera's vLLM track has been stalled at the same image since 2026-03-08 while their sglang track shipped a dev tag on 2026-04-29. The maintainer is clearly still publishing on the Spark — just not the vLLM track.
**Effort:** M — two sessions, ~5–7h total. Most of the work is flag translation and side-by-side validation, not destructive cutover.
**Blast radius:** medium. SGLang runs as a *new* compose service on a new port (8002) for the entire validation phase — vLLM at 8001 stays serving openclaw the whole time. Cutover is a single config edit on openclaw plus a one-line compose change. Rollback is reverting both.

---

## Current state (verified 2026-05-02)

- vLLM image: `scitrera/dgx-spark-vllm:0.17.0-t5` — wheel inside is `vllm 0.17.1.dev0+gb31e9326a.d20260307.cu131`. Last published 2026-03-08.
- Model served: `Intel/Qwen3.6-27B-int4-AutoRound` — INT4 weights via Intel's AutoRound + `qwen3_next_mtp` MTP head with `num_speculative_tokens=2`.
- Single-stream decode rate ~21 t/s; concurrent decode (c=2+) **disabled in the eval harness because c=2 reliably crashes the engine on this image with MTP enabled**.
- OpenClaw consumes vLLM via OpenAI-compatible `http://vllm:8000/v1` (host port `0.0.0.0:8001:8000`).
- Custom chat template at `vllm-templates/qwen3.6-27b.jinja` with `enable_thinking` flipped default-OFF.

### scitrera publish cadence (sanity check on the migration premise)

| Track | Last published | Cadence |
|---|---|---|
| sglang (`scitrera/dgx-spark-sglang`) | 2026-04-29 | Active, dev + stable tags |
| llama.cpp (bot-driven) | 2026-05-01 | Multiple commits/day |
| **vLLM (`scitrera/dgx-spark-vllm`)** | **2026-03-08** | Stalled |

If the maintainer's own DGX Spark workload is on sglang now, vLLM updates may not arrive — staying on it is increasingly a bet against the maintainer's roadmap.

---

## Target stack

- Image: **`scitrera/dgx-spark-sglang:0.5.10`** initially (most recent stable). Promote to `0.5.10-20260429-dev1` only if a feature we need is dev-only.
- Server entry: `python -m sglang.launch_server` (the image's default CMD).
- Same model: `Intel/Qwen3.6-27B-int4-AutoRound` via `--quantization auto-round`.
- Same chat template: reuse `vllm-templates/qwen3.6-27b.jinja` mounted into the sglang container at `/etc/sglang/qwen3.6-27b.jinja`.
- Port: host `0.0.0.0:8002` → container `30000` (sglang's default port). vLLM stays on 8001.

---

## Flag translation (vLLM → sglang)

Verified against `sgl-project/sglang/blob/main/python/sglang/srt/server_args.py`.

| vLLM flag (current) | SGLang equivalent | Notes |
|---|---|---|
| `Intel/Qwen3.6-27B-int4-AutoRound` (positional) | `--model-path Intel/Qwen3.6-27B-int4-AutoRound` | sglang uses `--model-path` |
| `--host=0.0.0.0` | `--host=0.0.0.0` | same |
| `--port=8000` | `--port=30000` (or whatever container port we expose) | sglang's default is 30000 |
| `--max-model-len=262144` | `--context-length=262144` | rename only |
| `--gpu-memory-utilization=0.75` | `--mem-fraction-static=0.75` | rename only |
| `--kv-cache-dtype=fp8` | `--kv-cache-dtype=fp8_e5m2` | sglang names the variant explicitly; verify which the model expects |
| `--enable-prefix-caching` | (default ON via RadixAttention) | drop the flag; equivalent or better than vLLM's prefix cache |
| `--enable-chunked-prefill` | `--chunked-prefill-size=16384` | combined with the next row |
| `--max-num-batched-tokens=16384` | `--max-prefill-tokens=16384` | sglang separates prefill from decode budget |
| `--max-num-seqs=4` | `--max-running-requests=4` | rename only |
| `--reasoning-parser=qwen3` | `--reasoning-parser=qwen3` | same flag (sglang adopted vLLM's name) |
| `--enable-auto-tool-choice` + `--tool-call-parser=qwen3_coder` | `--tool-call-parser=qwen3_coder` | sglang has a single combined flag |
| `--chat-template=/etc/vllm/qwen3.6-27b.jinja` | `--chat-template=/etc/sglang/qwen3.6-27b.jinja` | same shape, different mount path |
| `--speculative-config={'method':'qwen3_next_mtp','num_speculative_tokens':2}` | `--speculative-algorithm=EAGLE` (or `MTP` if newer flag exists) + `--speculative-num-steps=2` + `--speculative-num-draft-tokens=2` | **Open question — Qwen3.6 MTP support in sglang needs confirmation; see Open Questions** |
| (none) | `--quantization auto-round` | required to load the AutoRound INT4 weights |
| (none) | `--served-model-name qwen3.6-27b-int4:128k` | match the existing vLLM `served-model-name` so openclaw doesn't need to change the model id |

---

## Phasing

### Session A — stand up sglang side-by-side (~3h)

1. **Pull the image** to the Spark before touching compose: `docker pull scitrera/dgx-spark-sglang:0.5.10`. Confirm it's ARM64 + SM_120 by checking `docker image inspect`. Cancel and switch tags if the build doesn't include the right arch.
2. **Add a `sglang` service to `docker-compose.yml`** alongside the existing `vllm` service:
   - Same `vllm_hf_cache` HF cache volume (mounted read-only) — no need to re-download 14 GB of weights.
   - Separate `sglang_compile_cache` volume for sglang's compile artefacts.
   - Mount `vllm-templates/qwen3.6-27b.jinja` at `/etc/sglang/qwen3.6-27b.jinja` (read-only).
   - Port: `0.0.0.0:8002:30000`.
   - Same `ipc: host`, same NVIDIA env vars.
   - Translated command-line per the table above.
3. **Bring it up**: `docker compose up -d sglang` and tail logs until "model loaded". First-run will populate the sglang compile cache (~5–10 min on Blackwell SM_120).
4. **Health check**: `curl http://localhost:8002/health` → 200; `curl http://localhost:8002/v1/models` → returns the served model id.
5. **Smoke chat completion** (no tools, single turn, `enable_thinking=false`) — confirm output is sensible and there's no preamble leak in the immediate first reply. **If MTP isn't loading in sglang, fail fast here and revisit speculative-decoding flags before continuing.**
6. **Tool-call smoke test**: a single BFCL-mini-style request through the existing `eval/probes/tools.py` against `--endpoint http://localhost:8002/v1`. Confirm tool_calls round-trip cleanly.

**Validation criteria for Session A:** `curl /v1/chat/completions` returns 200 with non-empty content; one parallel-tool-call test passes; no engine crash within 10 minutes of idle + intermittent requests.

### Session B — A/B against vLLM, then cut over (~3h)

1. **Run the eval harness against both endpoints** back-to-back:
   - `python runner.py --tier full --endpoint http://localhost:8001/v1 --model qwen3.6-27b-int4:128k --judge opus46` (vLLM baseline — already have today's run in `eval/results/`)
   - `python runner.py --tier full --endpoint http://localhost:8002/v1 --model qwen3.6-27b-int4:128k --judge opus46` (sglang)
2. **Compare** the resulting `summary.json` files side-by-side. Headline metrics to watch:
   - `perf.decode_tok_s_c1` — should be within ±10% of vLLM (sglang and vLLM are similar speed for INT4 + spec-decode at single-stream)
   - `tools.accuracy` — should match within 1–2 cases (model behaviour-driven, engine-agnostic)
   - `coding.pass_at_1` — same
   - `qualitative.mean_score` — same (model behaviour, not engine)
   - `agent_loop.mean_score` — same
   - **Engine stability**: did the qualitative probe complete? On vLLM today it crashed twice. If sglang completes a full `--tier=full` run without the engine going down, that alone justifies the migration.
3. **Decision gate**: if sglang scores within noise on quality metrics AND completes a full run without crashing, proceed to cutover. Otherwise file findings and stay on vLLM.
4. **Cutover**:
   - Stop sglang briefly, rebind it to host port `8001` (the port openclaw is configured for) by editing the compose service's port mapping.
   - Stop vLLM (rename the compose service to `vllm-legacy` and comment out so it doesn't auto-restart, but keep the YAML for one-line revert).
   - `docker compose up -d sglang` on port 8001.
   - Verify openclaw reconnects (check `~/.openclaw/logs/`).
   - End-to-end smoke test through OpenClaw dashboard: a real tool-using conversation.
5. **Tag the working state in git**: `git tag sglang-cutover-2026-05-XX`. Easy rollback marker.

**Validation criteria for Session B:** sglang on port 8001 serves OpenClaw end-to-end with no functional regression; eval harness scores within agreed bands; one full hour of soak with no engine crash.

### Decommission (~1 week after cutover)

- Remove the commented `vllm-legacy` block from compose.
- Delete `vllm_hf_cache` volume **only after confirming sglang is reading from it / has its own copy** (likely they share — verify before any volume cleanup).
- Update `DEPLOYMENT.md` and the docker-compose comment block to reflect the new engine.

---

## Decisions made

- **Side-by-side, not in-place**, throughout validation. OpenClaw stays on vLLM until sglang is proven. No serving downtime.
- **Same model, same chat template, same `served-model-name`**. The point of this migration is the *engine*, not the model — keeping everything else fixed makes the comparison clean and rollback trivial.
- **Stable tag `0.5.10` over the dev tag** as the starting target. Promote to `-dev1` only if a needed feature is dev-only.
- **Reuse the existing HF cache volume** for the model weights — avoids 14 GB re-download.
- **Rollback strategy is "revert the compose edit"** — no irreversible state changes during cutover. The vLLM `0.17.0-t5` image stays on disk; reverting takes <60s.

---

## Open questions (resolve in Session A)

- **Does sglang 0.5.10 support Qwen3.6 MTP speculative decoding?** vLLM uses `qwen3_next_mtp` method; sglang may have implemented MTP under a different algorithm name (probably `EAGLE` or a Qwen-specific variant). If MTP isn't supported, we lose the ~1.5x decode speedup and land at ~13 t/s instead of ~21 t/s — still acceptable, but worth knowing before cutover.
- **Does sglang's `--quantization auto-round` correctly load Intel's INT4 weights?** sglang's `--quantization` choice list explicitly includes `auto-round`; verify by inspecting model load logs for the right kernel selection.
- **Does the existing chat template work as-is?** sglang accepts Jinja2 templates the same way vLLM does, but Qwen3.6's template uses `chat_template_kwargs.enable_thinking` — verify that openclaw's request shape (which doesn't pass `chat_template_kwargs` per call) still gets the default-OFF behaviour from our custom template under sglang.
- **What's sglang's `kv-cache-dtype` value for FP8?** vLLM uses `fp8`; sglang's options are `fp8_e5m2` and `fp8_e4m3` — pick the one that matches Intel's AutoRound expectations. Default is `auto`; that may be safest.
- **Does sglang have an MTP-related crash analogue?** vLLM's `cudaErrorIllegalAddress` happens during the MTP path under spec-decode. sglang has its own spec-decode implementation; the failure mode (if any) will be different. Plan: bring it up *with* MTP enabled and stress-test through eval-harness `--tier=full`. If it crashes, retry with `--speculative-algorithm` removed (single-stream decode only) as a fallback.
- **Does OpenClaw have any vLLM-specific assumptions?** Probably not (it talks OpenAI-compat HTTP), but worth a fast read of the openclaw config for any vLLM-prefixed flag.
- **Should we keep the `chat_template_kwargs` chat-template flip pattern, or use sglang-native `--reasoning-parser=qwen3` to handle thinking mode?** Both are real options; the chat template gives openclaw its current behaviour for free, but the parser is more idiomatic in sglang.

---

## Risks (and mitigations)

| Risk | Mitigation |
|---|---|
| AutoRound INT4 won't load on sglang | Keep vLLM running. Try FP8 weights of the same model as fallback (`Qwen/Qwen3.6-27B-FP8` exists). |
| MTP doesn't port across engines, decode speed drops below acceptable | Acceptable temporarily — single-stream is still 13 t/s. Long-term path: NVFP4 + MTP via newer sglang (already supported via `--quantization mxfp8`/`fp8`). |
| sglang has its own engine-crash pattern under load | Eval harness already has health-gating between probes. Will catch this in Session B before cutover. |
| OpenClaw config breaks during cutover | Tag git state first; cutover is one-line revert. |
| HF cache volume mount conflicts (vLLM holding write lock during sglang spin-up) | Mount sglang's reference as read-only (`:ro`). Both engines can read from a shared cache concurrently. |
| Disk space — sglang compile cache grows | Watch `docker system df`. Compile cache should be ≤2 GB. |

---

## Validation

End-to-end success criteria for the migration:

- sglang serves the same model id (`qwen3.6-27b-int4:128k`) at the same OpenAI-compatible API surface OpenClaw expects.
- `eval/runner.py --tier=full --judge=opus46` against sglang completes without engine crash AND scores within ±5% on perf, ±2 cases on tools, equivalent on coding/qualitative/agent_loop.
- OpenClaw end-to-end smoke (a tool-using conversation through the dashboard) returns a coherent response with the new engine.
- 1-hour soak after cutover: no engine restart, no 500s in logs.
- One-line rollback verified during Session B (uncomment vLLM, comment sglang, `docker compose up -d`).
