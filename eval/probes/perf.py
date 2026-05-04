"""Performance probe.

Measures decode tok/s @ concurrency 1 and 4, TTFT @ prompt-lengths 1k and 16k,
KV cache utilisation and prefix-cache hit rate (parsed from vLLM /metrics if
available).

Headline metric: decode_tok_s_c1 (single-stream decode rate, in tokens/sec).
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))
from api import add_to_ledger, usage_cost  # noqa: E402

OUTPUT_TOKENS = 200          # decode-rate sample length
WARMUP_TOKENS = 32           # first request is discarded
LONG_PROMPT_TOK_TARGETS = [1024, 16384]
HTTP_TIMEOUT = 600.0
# vLLM 0.17.0-t5 + MTP speculative-decoding stack has hit
# `cudaErrorIllegalAddress` reliably at concurrency=2 and crashed the engine
# (Engine restart, dropped requests). No concurrent-decode test runs by
# default. Set EVAL_PERF_CONCURRENCY=N to opt in once the engine is on a
# version where MTP+concurrency is stable.
DEFAULT_CONCURRENCY = 0


def _chat(endpoint: str, model: str, prompt: str, max_tokens: int,
          ctx: dict, stream: bool = False) -> dict[str, Any]:
    """Single non-streaming chat completion. Returns parsed JSON.
    Also credits any usage-based candidate cost to the ledger."""
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        # vLLM-specific: keep generating to full max_tokens for stable timing.
        # Remote endpoints (OpenRouter) ignore this; that's fine — we just get
        # natural-stop completions which makes tok/s slightly less stable.
        "ignore_eos": True,
        # disable thinking so we time pure decode, not chain-of-thought
        "chat_template_kwargs": {"enable_thinking": False},
        "stream": stream,
    }
    if stream:
        body["stream_options"] = {"include_usage": True}
    r = httpx.post(
        f"{endpoint}/chat/completions",
        json=body,
        headers=ctx.get("auth_headers") or {},
        timeout=HTTP_TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    add_to_ledger(ctx, "perf", usage_cost(data.get("usage"), ctx.get("candidate_pricing")))
    return data


def _ttft_streaming(endpoint: str, model: str, prompt: str, ctx: dict) -> float:
    """Open a streaming completion, return seconds until first content token."""
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8,
        "temperature": 0.0,
        "ignore_eos": True,
        "chat_template_kwargs": {"enable_thinking": False},
        "stream": True,
    }
    t0 = time.perf_counter()
    with httpx.stream("POST", f"{endpoint}/chat/completions",
                      json=body,
                      headers=ctx.get("auth_headers") or {},
                      timeout=HTTP_TIMEOUT) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            payload = line[len("data:"):].strip()
            if payload == "[DONE]":
                break
            try:
                chunk = json.loads(payload)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            if delta.get("content") or delta.get("reasoning_content"):
                return time.perf_counter() - t0
    return time.perf_counter() - t0


def _decode_rate(endpoint: str, model: str, ctx: dict,
                 max_tokens: int = OUTPUT_TOKENS) -> dict:
    """Single-stream decode rate (tok/s) over a freshly-issued request."""
    prompt = "Count from one to one thousand, one number per line."
    t0 = time.perf_counter()
    resp = _chat(endpoint, model, prompt, max_tokens=max_tokens, ctx=ctx)
    elapsed = time.perf_counter() - t0
    completion_tokens = resp.get("usage", {}).get("completion_tokens", max_tokens)
    return {
        "tokens": completion_tokens,
        "seconds": elapsed,
        "tok_s": completion_tokens / elapsed if elapsed > 0 else 0.0,
    }


def _decode_rate_concurrent(endpoint: str, model: str, n: int, ctx: dict,
                            max_tokens: int = OUTPUT_TOKENS) -> dict:
    prompt = "Count from one to one thousand, one number per line."
    t0 = time.perf_counter()
    with cf.ThreadPoolExecutor(max_workers=n) as ex:
        futs = [ex.submit(_chat, endpoint, model, prompt, max_tokens, ctx)
                for _ in range(n)]
        results = [f.result() for f in cf.as_completed(futs)]
    elapsed = time.perf_counter() - t0
    total_tokens = sum(r.get("usage", {}).get("completion_tokens", 0) for r in results)
    return {
        "concurrency": n,
        "total_tokens": total_tokens,
        "seconds": elapsed,
        "aggregate_tok_s": total_tokens / elapsed if elapsed > 0 else 0.0,
        "per_stream_tok_s": (total_tokens / n) / elapsed if elapsed > 0 else 0.0,
    }


def _make_long_prompt(target_tokens: int) -> str:
    # Rough: 4 chars/token. Filler is plain ASCII so tokenization is predictable.
    chars = target_tokens * 4
    filler = ("The quick brown fox jumps over the lazy dog. " * (chars // 45 + 1))[:chars]
    return filler + "\n\nIn one short sentence, what animal jumped?"


def _scrape_metrics(endpoint: str) -> dict:
    """vLLM exposes Prometheus metrics on the same host at /metrics (not under /v1).

    Returns a small subset we care about. Best-effort — returns {} on failure.
    """
    base = endpoint.rsplit("/v1", 1)[0]
    try:
        r = httpx.get(f"{base}/metrics", timeout=5.0)
        r.raise_for_status()
    except Exception:
        return {}
    text = r.text
    out: dict[str, float] = {}
    patterns = {
        "kv_cache_usage_perc": r"^vllm:gpu_cache_usage_perc(?:\{[^}]*\})?\s+([0-9eE\.\+\-]+)",
        "num_requests_running": r"^vllm:num_requests_running(?:\{[^}]*\})?\s+([0-9eE\.\+\-]+)",
        "num_requests_waiting": r"^vllm:num_requests_waiting(?:\{[^}]*\})?\s+([0-9eE\.\+\-]+)",
        "prefix_cache_hits_total": r"^vllm:prefix_cache_hits(?:_total)?(?:\{[^}]*\})?\s+([0-9eE\.\+\-]+)",
        "prefix_cache_queries_total": r"^vllm:prefix_cache_queries(?:_total)?(?:\{[^}]*\})?\s+([0-9eE\.\+\-]+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text, re.MULTILINE)
        if m:
            try:
                out[key] = float(m.group(1))
            except ValueError:
                pass
    if "prefix_cache_hits_total" in out and "prefix_cache_queries_total" in out:
        q = out["prefix_cache_queries_total"]
        out["prefix_cache_hit_rate"] = (
            out["prefix_cache_hits_total"] / q if q > 0 else 0.0
        )
    return out


def run(ctx: dict) -> dict:
    endpoint = ctx["endpoint"]
    model = ctx["model"]
    quick = ctx.get("quick", False)

    # 1. Warm-up — discarded.
    print("  warmup...", flush=True)
    _decode_rate(endpoint, model, ctx, max_tokens=WARMUP_TOKENS)

    # 2. Single-stream decode rate.
    print("  decode @ c=1...", flush=True)
    c1 = _decode_rate(endpoint, model, ctx, max_tokens=OUTPUT_TOKENS if not quick else 64)

    # 3. Concurrent decode rate. Off by default — the Spark vLLM 0.17.0-t5
    # MTP path has crashed at c=2; opt in by setting EVAL_PERF_CONCURRENCY.
    n_conc = int(os.environ.get("EVAL_PERF_CONCURRENCY", DEFAULT_CONCURRENCY))
    if n_conc > 0:
        print(f"  decode @ c={n_conc} (env-gated)...", flush=True)
        try:
            c_concurrent = _decode_rate_concurrent(
                endpoint, model, n=n_conc, ctx=ctx,
                max_tokens=OUTPUT_TOKENS if not quick else 64,
            )
        except Exception as e:
            c_concurrent = {
                "concurrency": n_conc,
                "error": f"{type(e).__name__}: {e}",
                "skipped": True,
            }
            print(f"  decode @ c={n_conc} failed: {e}; continuing.", flush=True)
    else:
        c_concurrent = {
            "concurrency": 0,
            "skipped": True,
            "skip_reason": "concurrent decode disabled by default on vLLM 0.17.0-t5+MTP "
                           "(cudaErrorIllegalAddress); set EVAL_PERF_CONCURRENCY to opt in",
        }
        print("  decode @ c=N skipped (env-gated).", flush=True)

    # 4. TTFT at varying prompt lengths.
    ttft_samples: list[dict] = []
    for target in LONG_PROMPT_TOK_TARGETS:
        if quick and target > 4096:
            continue
        print(f"  TTFT @ prompt~{target} tok...", flush=True)
        prompt = _make_long_prompt(target)
        try:
            seconds = _ttft_streaming(endpoint, model, prompt, ctx)
            ttft_samples.append({"prompt_target_tokens": target, "ttft_seconds": seconds})
        except Exception as e:
            ttft_samples.append({"prompt_target_tokens": target,
                                 "error": f"{type(e).__name__}: {e}"})

    # 5. Metrics scrape.
    metrics = _scrape_metrics(endpoint)

    return {
        "headline_key": "decode_tok_s_c1",
        "decode_tok_s_c1": c1["tok_s"],
        "decode_c1": c1,
        "decode_concurrent": c_concurrent,
        "ttft": ttft_samples,
        "metrics": metrics,
    }
