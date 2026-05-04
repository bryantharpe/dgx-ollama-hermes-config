"""Endpoint helpers — auth headers + cost tracking for the candidate model.

Most of the harness historically targeted local engines (vLLM, sglang, ollama)
that need no auth. Adding OpenRouter (or the Anthropic API as a candidate)
means each probe needs to send Authorization headers AND optionally track
USD cost per call so we can surface "this run cost $X" alongside the scores.

This module centralises both concerns. Probes import `endpoint_headers()`
once, fold the result into their httpx calls, and use `usage_cost()` when
they have a usage dict back from the API.

Cost ledger lives in ctx['candidate_cost_ledger'] (a dict-of-floats keyed
by probe name). The runner sums it for the final summary and enforces the
--max-cost ceiling.
"""
from __future__ import annotations

import os
from typing import Optional

import httpx

# ── User-Agent / referrer for OpenRouter (used in their dashboard). ─────────
HARNESS_REFERRER = "https://github.com/bryantharpe/hermes-config"
HARNESS_TITLE = "hermes-config eval harness"

_OPENROUTER_DOMAIN = "openrouter.ai"
_ANTHROPIC_DOMAIN = "api.anthropic.com"


def endpoint_headers(endpoint: str) -> dict:
    """Build any required auth headers for `endpoint`.

    Returns {} for local endpoints (vLLM, sglang, ollama). Raises if a
    remote endpoint needs a key but the matching env var is unset — fail
    fast at startup, don't wait until the first probe.
    """
    if _OPENROUTER_DOMAIN in endpoint:
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError(
                "endpoint is OpenRouter but OPENROUTER_API_KEY is not set. "
                "Export it (preferably above the bashrc interactive guard) "
                "and re-launch the harness."
            )
        return {
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": HARNESS_REFERRER,
            "X-Title": HARNESS_TITLE,
        }
    if _ANTHROPIC_DOMAIN in endpoint:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "endpoint is Anthropic API but ANTHROPIC_API_KEY is not set."
            )
        # The Anthropic native messages API uses a different shape than OpenAI;
        # this only works if the harness probes call /v1/messages explicitly.
        # Bare /v1/chat/completions on api.anthropic.com is not supported.
        return {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        }
    return {}  # local engine — no auth


def fetch_model_pricing(endpoint: str, model: str,
                        timeout: float = 10.0) -> Optional[dict]:
    """For OpenRouter, look up the per-token USD pricing for `model`.

    Returns {"prompt": <usd_per_token>, "completion": <usd_per_token>}
    or None if the endpoint isn't OpenRouter, the model isn't found, or
    the lookup fails. None disables cost tracking for that run (probes
    will still record token counts).
    """
    if _OPENROUTER_DOMAIN not in endpoint:
        return None
    # The /v1/models endpoint on OpenRouter returns the same data as
    # /api/v1/models with the same shape; just hit it relative to the
    # configured endpoint to avoid url-mangling.
    try:
        r = httpx.get(f"{endpoint.rstrip('/')}/models", timeout=timeout)
        r.raise_for_status()
    except Exception:
        return None
    for m in r.json().get("data", []):
        if m.get("id") == model:
            p = m.get("pricing") or {}
            try:
                return {
                    "prompt": float(p.get("prompt", 0) or 0),
                    "completion": float(p.get("completion", 0) or 0),
                }
            except (TypeError, ValueError):
                return None
    return None


def usage_cost(usage: Optional[dict], pricing: Optional[dict]) -> float:
    """Convert a chat-completion usage dict into USD using pricing dict."""
    if not pricing or not usage:
        return 0.0
    return (usage.get("prompt_tokens", 0) * pricing.get("prompt", 0)
            + usage.get("completion_tokens", 0) * pricing.get("completion", 0))


def add_to_ledger(ctx: dict, probe_name: str, cost_usd: float) -> None:
    """Accumulate candidate cost in the per-probe ledger on ctx."""
    if cost_usd <= 0:
        return
    ledger = ctx.setdefault("candidate_cost_ledger", {})
    ledger[probe_name] = ledger.get(probe_name, 0.0) + cost_usd


def total_candidate_cost(ctx: dict) -> float:
    return sum((ctx.get("candidate_cost_ledger") or {}).values())


def post_chat(endpoint: str, body: dict, ctx: dict, probe_name: str,
              timeout: float = 120.0) -> dict:
    """POST /chat/completions with auth headers + cost tracking.

    Replaces the bare `httpx.post(...).raise_for_status(); .json()` pattern in
    probes. Pulls auth_headers and candidate_pricing out of ctx; on a
    successful response, credits any usage-based cost to the probe's slot
    in the ledger.
    """
    r = httpx.post(
        f"{endpoint}/chat/completions",
        json=body,
        headers=ctx.get("auth_headers") or {},
        timeout=timeout,
    )
    r.raise_for_status()
    data = r.json()
    add_to_ledger(
        ctx, probe_name,
        usage_cost(data.get("usage"), ctx.get("candidate_pricing")),
    )
    return data
