#!/usr/bin/env python3
"""Eval harness orchestrator.

Runs probes against an OpenAI-compatible endpoint (vLLM), aggregates JSON
results, writes summary.json + report.md under results/<model>/<timestamp>/.

Usage:
    python runner.py --tier 1 --endpoint http://localhost:8001/v1 \
                     --model qwen3.6-27b-int4:128k --judge none

Tiers:
    1     = perf + tools + coding (deterministic only, no judge)
    full  = tier 1 + qualitative + agent (judge required, session 2+)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import traceback
from pathlib import Path

import httpx

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

from probes import perf, tools, coding, long_context, qualitative, agent_loop, agent_prototype  # noqa: E402
from api import (  # noqa: E402
    endpoint_headers, fetch_model_pricing, total_candidate_cost,
)


def health_check(endpoint: str, timeout: float = 5.0) -> bool:
    """Poll the engine's health endpoint, handling vLLM/sglang and ollama
    conventions:
      - vLLM, sglang: /health (200 = ready) outside /v1
      - ollama:       no /health, but /v1/models returns 200 once loaded
    """
    base = endpoint.rstrip("/")
    no_v1 = base.rsplit("/v1", 1)[0]
    for url in (f"{no_v1}/health", f"{base}/models"):
        try:
            r = httpx.get(url, timeout=timeout)
            if r.status_code == 200:
                return True
        except Exception:
            pass
    return False


def wait_for_health(endpoint: str, max_wait_seconds: int = 60) -> bool:
    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        if health_check(endpoint):
            return True
        time.sleep(2)
    return False

PROBES_BY_TIER = {
    "1": [
        ("perf", perf.run),
        ("tools", tools.run),
        ("coding", coding.run),
        ("long_context", long_context.run),
    ],
    "agent": [
        ("perf", perf.run),
        ("tools", tools.run),
        ("coding", coding.run),
        ("qualitative", qualitative.run),
        ("agent_loop", agent_loop.run),
    ],
    "full": [
        ("perf", perf.run),
        ("tools", tools.run),
        ("coding", coding.run),
        ("long_context", long_context.run),
        ("qualitative", qualitative.run),
        ("agent_loop", agent_loop.run),
        ("agent_prototype", agent_prototype.run),
    ],
    # Just the heavy end-to-end probe — useful for iterating on it without
    # paying for the full deterministic + qualitative tier each time.
    "prototype": [
        ("agent_prototype", agent_prototype.run),
    ],
}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="vLLM model eval harness")
    ap.add_argument("--tier", choices=list(PROBES_BY_TIER.keys()), default="1")
    ap.add_argument("--endpoint", default="http://localhost:8001/v1",
                    help="OpenAI-compatible base URL (default: %(default)s)")
    ap.add_argument("--model", default="qwen3.6-27b-int4:128k",
                    help="Model id served by --endpoint")
    ap.add_argument("--judge", choices=["opus46", "none"], default="none",
                    help="Judge model. 'none' = deterministic probes only.")
    ap.add_argument("--out", default=str(THIS_DIR / "results"),
                    help="Results root directory")
    ap.add_argument("--quick", action="store_true",
                    help="Slash sample sizes for fast iteration during dev")
    ap.add_argument("--max-cost", type=float, default=5.0,
                    help="Bail between probes if accumulated CANDIDATE cost "
                         "exceeds this (USD). Judge cost is tracked separately. "
                         "Default 5.0; set to 0 to disable the cap.")
    return ap.parse_args()


def safe_model_dirname(model: str) -> str:
    # filesystem-safe; preserves enough to recognize the model
    return model.replace("/", "_").replace(":", "_")


def write_report_md(summary: dict, results_dir: Path) -> None:
    """Render a tiny human-readable report. Diff vs prior run lands in session 3."""
    md = []
    md.append(f"# Eval — {summary['model']} @ {summary['timestamp']}")
    md.append("")
    md.append(f"- **Endpoint:** `{summary['endpoint']}`")
    md.append(f"- **Tier:** `{summary['tier']}`")
    md.append(f"- **Judge:** `{summary['judge']}`")
    md.append(f"- **Wall-time:** {summary['wall_seconds']:.1f}s")
    md.append("")
    md.append("## Scores")
    md.append("")
    md.append("| Probe | Status | Headline metric | Value |")
    md.append("|---|---|---|---|")
    for probe_name, probe_result in summary["probes"].items():
        status = probe_result.get("status", "?")
        headline_key = probe_result.get("headline_key")
        headline_value = probe_result.get(headline_key) if headline_key else None
        if isinstance(headline_value, float):
            headline_value = f"{headline_value:.3f}"
        md.append(f"| {probe_name} | {status} | {headline_key or '-'} | {headline_value or '-'} |")
    md.append("")
    md.append("Full numbers in `summary.json`.")
    (results_dir / "report.md").write_text("\n".join(md) + "\n")


def main() -> int:
    args = parse_args()
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_root = Path(args.out)
    results_dir = out_root / safe_model_dirname(args.model) / timestamp
    artefacts_dir = results_dir / "artifacts"
    artefacts_dir.mkdir(parents=True, exist_ok=True)

    # Compute auth headers + pricing once at startup. Fail fast if a remote
    # endpoint needs a key that isn't in env.
    try:
        auth_headers = endpoint_headers(args.endpoint)
    except RuntimeError as e:
        print(f"FATAL: {e}", file=sys.stderr)
        return 2
    candidate_pricing = fetch_model_pricing(args.endpoint, args.model)
    if "openrouter.ai" in args.endpoint and candidate_pricing is None:
        print(f"WARN: couldn't fetch pricing for {args.model!r} on OpenRouter; "
              "candidate cost will NOT be tracked or capped this run.",
              file=sys.stderr)

    ctx = {
        "endpoint": args.endpoint.rstrip("/"),
        "model": args.model,
        "judge": args.judge,
        "quick": args.quick,
        "artefacts_dir": artefacts_dir,
        "auth_headers": auth_headers,
        "candidate_pricing": candidate_pricing,
        "candidate_cost_ledger": {},
    }

    summary = {
        "model": args.model,
        "endpoint": args.endpoint,
        "tier": args.tier,
        "judge": args.judge,
        "timestamp": timestamp,
        "probes": {},
    }

    # Pre-flight: refuse to run if the endpoint isn't healthy.
    if not health_check(args.endpoint):
        print(f"FATAL: {args.endpoint} health check failed. "
              "Is vLLM running and ready?", file=sys.stderr)
        return 2

    # Pre-flight: refuse if any probe in this tier needs the judge but no API key.
    needs_judge = any(
        name in {"qualitative", "agent_loop", "agent_prototype"}
        for name, _ in PROBES_BY_TIER[args.tier]
    )
    if needs_judge and args.judge == "opus46" and not os.environ.get("ANTHROPIC_API_KEY"):
        print("FATAL: --judge=opus46 requested but ANTHROPIC_API_KEY is not set. "
              "Either export the key or run with --judge=none "
              "(judged probes will be skipped).", file=sys.stderr)
        return 2

    t0 = dt.datetime.now()
    probes_to_run = PROBES_BY_TIER[args.tier]

    for probe_name, probe_fn in probes_to_run:
        print(f"\n=== {probe_name} ===", flush=True)
        try:
            probe_result = probe_fn(ctx)
            probe_result.setdefault("status", "ok")
        except Exception as e:
            probe_result = {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
            print(f"  ERROR: {e}", flush=True)
        summary["probes"][probe_name] = probe_result

        # If a probe knocked the engine over, give it a chance to recover
        # before we pile errors onto the next one.
        if not health_check(args.endpoint):
            print("  ! endpoint unhealthy after probe — waiting up to 90s...",
                  flush=True)
            if not wait_for_health(args.endpoint, max_wait_seconds=90):
                print("  ! endpoint still down — aborting remaining probes.",
                      flush=True)
                summary["aborted_after"] = probe_name
                break

        # --max-cost ceiling — only meaningful when pricing is known.
        if args.max_cost > 0:
            running = total_candidate_cost(ctx)
            if running >= args.max_cost:
                print(f"  ! candidate cost ${running:.3f} hit --max-cost cap "
                      f"${args.max_cost:.2f} — aborting remaining probes.",
                      flush=True)
                summary["aborted_after"] = f"{probe_name} (cost cap)"
                break

    summary["wall_seconds"] = (dt.datetime.now() - t0).total_seconds()
    summary["candidate_cost_usd"] = total_candidate_cost(ctx)
    summary["candidate_cost_by_probe"] = ctx.get("candidate_cost_ledger") or {}
    summary["candidate_pricing"] = candidate_pricing  # may be None

    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    write_report_md(summary, results_dir)

    # Auto-refresh the cross-model comparison so disk always reflects the
    # latest per-model snapshot. Best-effort; doesn't fail the run.
    try:
        import subprocess
        subprocess.run(
            [sys.executable, str(THIS_DIR / "compare.py")],
            check=False, timeout=30,
        )
    except Exception as e:
        print(f"  (compare.py refresh skipped: {e})", flush=True)

    print(f"\nResults: {results_dir}")
    return 0 if all(p.get("status") == "ok" for p in summary["probes"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
