#!/usr/bin/env python3
"""Render a markdown comparison of eval runs across models.

Walks `eval/results/<model>/<timestamp>/summary.json`, picks the latest run
per model by default (or all runs with --all), and writes a comparison table
to `eval/results/COMPARISON.md`.

Usage:
    python compare.py                  # latest per model → COMPARISON.md
    python compare.py --all            # every run, grouped by model
    python compare.py --include foo,bar  # only these model names
    python compare.py --out custom.md
    python compare.py --print          # also write to stdout

Idempotent — re-runs overwrite the output file.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Optional

THIS_DIR = Path(__file__).resolve().parent
RESULTS_ROOT = THIS_DIR / "results"
DEFAULT_OUT = RESULTS_ROOT / "COMPARISON.md"


def _collect_runs(roots: Optional[set[str]] = None) -> list[dict]:
    """Read every summary.json under results/. Each entry includes the model
    dir, timestamp dir, and the parsed summary."""
    out = []
    if not RESULTS_ROOT.exists():
        return out
    for model_dir in sorted(RESULTS_ROOT.iterdir()):
        if not model_dir.is_dir():
            continue
        if roots and model_dir.name not in roots:
            continue
        for ts_dir in sorted(model_dir.iterdir()):
            summary_path = ts_dir / "summary.json"
            if not summary_path.exists():
                continue
            try:
                summary = json.loads(summary_path.read_text())
            except json.JSONDecodeError:
                continue
            out.append({
                "model_dir": model_dir.name,
                "timestamp": ts_dir.name,
                "path": ts_dir,
                "summary": summary,
            })
    return out


def _is_complete(run: dict) -> bool:
    """A run is 'complete' if it didn't abort and no probe errored. Used to
    avoid ranking partial-data runs as competitive in the latest-per-model
    view (e.g. an engine crash mid-run leaves stub probe results)."""
    s = run["summary"]
    if s.get("aborted_after"):
        return False
    for probe in s.get("probes", {}).values():
        if probe.get("status") == "error":
            return False
    return True


# Tier preference order — "richer" tiers beat lighter ones when picking
# latest-per-model, so a single tier=1 smoke doesn't mask the most recent
# tier=full baseline.
_TIER_RANK = {"full": 3, "agent": 2, "1": 1}


def _run_score(run: dict) -> tuple:
    """Sort key for picking the best run per model:
    (complete?, tier-rank, timestamp). Higher tuple wins."""
    tier = run["summary"].get("tier", "")
    return (
        1 if _is_complete(run) else 0,
        _TIER_RANK.get(tier, 0),
        run["timestamp"],
    )


def _latest_per_model(runs: list[dict]) -> list[dict]:
    """Pick the best representative run per model_dir, preferring (in order):
    completeness → tier richness → recency. So a tier=full from yesterday
    beats a tier=1 smoke from today, and an aborted run never wins if a
    complete one exists."""
    best: dict[str, dict] = {}
    for r in runs:
        cur = best.get(r["model_dir"])
        if cur is None or _run_score(r) > _run_score(cur):
            best[r["model_dir"]] = r
    return list(best.values())


def _ttft_for(perf: dict, target_tokens: int) -> Optional[float]:
    for sample in perf.get("ttft", []):
        if sample.get("prompt_target_tokens") == target_tokens:
            return sample.get("ttft_seconds")
    return None


def _judge_cost(probes: dict) -> float:
    total = 0.0
    for name in ("qualitative", "agent_loop"):
        p = probes.get(name) or {}
        total += p.get("judge_cost_usd") or 0.0
    return total


def _format_value(v, fmt: str = ".2f") -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "✓" if v else "✗"
    if isinstance(v, (int, float)):
        return format(v, fmt)
    return str(v)


# Rows (label, accessor, format, "higher is better")
ROWS = [
    ("decode tok/s c=1",  lambda p: p["perf"].get("decode_tok_s_c1"),  ".2f", True),
    ("TTFT @ 1k tok (s)",  lambda p: _ttft_for(p["perf"], 1024),        ".2f", False),
    ("TTFT @ 16k tok (s)", lambda p: _ttft_for(p["perf"], 16384),       ".2f", False),
    ("tools accuracy",     lambda p: (p.get("tools") or {}).get("accuracy"),    ".3f", True),
    ("coding pass@1",      lambda p: (p.get("coding") or {}).get("pass_at_1"),  ".3f", True),
    ("long_context recall", lambda p: (p.get("long_context") or {}).get("needle_recall"), ".3f", True),
    ("qualitative mean (/5)", lambda p: (p.get("qualitative") or {}).get("mean_score"), ".2f", True),
    ("agent_loop mean (/5)",  lambda p: (p.get("agent_loop") or {}).get("mean_score"),  ".2f", True),
]


def _render_table(runs: list[dict]) -> str:
    if not runs:
        return "_(no runs found)_\n"

    # Sort runs by model dir name (stable, deterministic)
    runs = sorted(runs, key=lambda r: (r["model_dir"], r["timestamp"]))

    lines = []
    lines.append("| Metric | " + " | ".join(r["model_dir"] for r in runs) + " |")
    lines.append("|---" + "|---" * len(runs) + "|")

    for label, accessor, fmt, higher_better in ROWS:
        vals = [accessor(r["summary"]["probes"]) for r in runs]
        # Mark best per row if multiple non-null and not all equal.
        finite = [v for v in vals if isinstance(v, (int, float))]
        best_val = (max(finite) if (finite and higher_better)
                    else (min(finite) if finite else None))
        cells = []
        for v in vals:
            if isinstance(v, (int, float)) and v == best_val and len(set(finite)) > 1:
                cells.append(f"**{_format_value(v, fmt)}**")
            else:
                cells.append(_format_value(v, fmt))
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    # Wall-time + judge cost rows (informational)
    walls = [r["summary"].get("wall_seconds") for r in runs]
    costs = [_judge_cost(r["summary"]["probes"]) for r in runs]
    lines.append("| wall time (min) | " + " | ".join(
        _format_value(w / 60.0 if w else None, ".1f") for w in walls) + " |")
    lines.append("| judge cost (USD) | " + " | ".join(
        f"${c:.3f}" if c else "—" for c in costs) + " |")

    # Engine + tier metadata, if present
    tiers = [r["summary"].get("tier", "?") for r in runs]
    lines.append("| tier | " + " | ".join(tiers) + " |")

    timestamps = [r["timestamp"] for r in runs]
    lines.append("| timestamp | " + " | ".join(t for t in timestamps) + " |")

    # Failure callouts
    notes = []
    for r in runs:
        for probe_name, probe in r["summary"]["probes"].items():
            if probe.get("status") == "error":
                notes.append(
                    f"- ⚠ **{r['model_dir']}**: probe `{probe_name}` errored "
                    f"({probe.get('error', '<no msg>')})"
                )
            elif probe.get("skipped"):
                notes.append(
                    f"- ℹ️ **{r['model_dir']}**: probe `{probe_name}` skipped "
                    f"({probe.get('skip_reason', '<no reason>')})"
                )
        if r["summary"].get("aborted_after"):
            notes.append(
                f"- ⚠ **{r['model_dir']}**: run aborted after probe "
                f"`{r['summary']['aborted_after']}`"
            )
    if notes:
        lines.append("")
        lines.append("**Notes:**")
        lines.extend(notes)

    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--all", action="store_true",
                    help="Include every run, not just latest per model")
    ap.add_argument("--include", default="",
                    help="Comma-separated model dir names to include (default: all)")
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help=f"Output markdown path (default: {DEFAULT_OUT})")
    ap.add_argument("--print", action="store_true", dest="also_print",
                    help="Also print to stdout")
    args = ap.parse_args()

    include = set(s.strip() for s in args.include.split(",") if s.strip()) or None
    runs = _collect_runs(include)
    if not args.all:
        runs = _latest_per_model(runs)

    title_qual = "all runs" if args.all else "latest run per model"
    out_lines = [
        f"# Eval comparison — {title_qual}",
        "",
        f"_Generated: {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}_  ",
        f"_Source: `eval/results/<model>/<ts>/summary.json` ({len(runs)} run(s))_",
        "",
        "Per-row, **bold** marks the best score among present (non-null) values "
        "for that metric (higher-is-better for accuracy/recall/score; lower-is-"
        "better for TTFT). Single-value rows aren't bolded.",
        "",
        _render_table(runs),
    ]
    text = "\n".join(out_lines)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    print(f"wrote {out_path} ({len(runs)} run(s))", flush=True)
    if args.also_print:
        print()
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
