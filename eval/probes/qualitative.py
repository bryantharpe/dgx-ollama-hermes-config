"""Qualitative probe — OpenClaw-shape single-turn prompts, judged by Opus 4.6.

Each case sends a prompt to vLLM, captures the response, and submits to the
judge with the qualitative.md rubric. Headline metric: mean score / 5.

Set ctx['judge'] == 'none' to skip this probe entirely (deterministic-only run).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))

from judge import JudgeResult, judge, make_client  # noqa: E402
from api import post_chat  # noqa: E402

DATASET = THIS_DIR.parent / "datasets" / "qualitative.jsonl"
RUBRIC = THIS_DIR.parent / "rubrics" / "qualitative.md"
HTTP_TIMEOUT = 180.0


def _load_cases() -> list[dict]:
    out = []
    with DATASET.open() as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


SYSTEM_NO_PREAMBLE = (
    "You are a precise, instruction-following assistant. When the user asks "
    "for a specific output format or specific content, produce ONLY that "
    "output — no preamble, no chain-of-thought, no explanation, no markdown "
    "wrapping unless explicitly requested. If asked for 'ONLY a JSON object', "
    "output only the JSON object. If asked for 'ONLY a number', output only "
    "the number. Do not show your reasoning process. Do not say 'Here's a "
    "thinking process' or 'Let me work through this'. Just produce the "
    "requested output directly."
)


def _ask_candidate(endpoint: str, model: str, prompt: str, ctx: dict) -> str:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_NO_PREAMBLE},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 512,
        "temperature": 0.0,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    data = post_chat(endpoint, body, ctx, "qualitative", timeout=HTTP_TIMEOUT)
    msg = data["choices"][0]["message"]
    # content || reasoning_content (sglang) || reasoning (OpenRouter)
    raw = (msg.get("content")
           or msg.get("reasoning_content")
           or msg.get("reasoning")
           or "")
    import re
    return re.sub(r"<think>.*?</think>\s*", "", raw, flags=re.DOTALL | re.IGNORECASE).strip()


def run(ctx: dict) -> dict:
    if ctx.get("judge") != "opus46":
        return {
            "headline_key": "mean_score",
            "mean_score": None,
            "skipped": True,
            "skip_reason": "qualitative probe requires --judge=opus46",
        }

    endpoint = ctx["endpoint"]
    model = ctx["model"]
    quick = ctx.get("quick", False)
    artefacts_dir = ctx["artefacts_dir"]

    rubric_md = RUBRIC.read_text()
    cases = _load_cases()
    if quick:
        cases = cases[:3]

    judge_client = make_client()
    results = []
    total_score = 0
    total_cost = 0.0

    for i, case in enumerate(cases, 1):
        try:
            response = _ask_candidate(endpoint, model, case["prompt"], ctx)
        except Exception as e:
            results.append({
                "id": case["id"], "category": case["category"],
                "score": None, "error": f"candidate call failed: {e!r}",
            })
            print(f"  [{i:2}/{len(cases)}] ERROR {case['id']} (candidate)", flush=True)
            continue

        # Build the content the judge sees: the prompt, the response, and the
        # author's intent note. The intent helps the judge know what good
        # looks like for *this specific* prompt.
        judge_content = (
            f"## Prompt sent to candidate\n\n{case['prompt']}\n\n"
            f"## Author's intent (what 'good' looks like for this prompt)\n\n"
            f"{case.get('intent', '(none provided)')}\n\n"
            f"## Candidate response\n\n```\n{response}\n```\n"
        )

        try:
            verdict: JudgeResult = judge(
                rubric_md=rubric_md,
                content_text=judge_content,
                client=judge_client,
            )
        except Exception as e:
            results.append({
                "id": case["id"], "category": case["category"],
                "score": None, "candidate_response": response,
                "error": f"judge call failed: {e!r}",
            })
            print(f"  [{i:2}/{len(cases)}] ERROR {case['id']} (judge)", flush=True)
            continue

        total_score += verdict.score
        total_cost += verdict.usage.cost_usd
        results.append({
            "id": case["id"],
            "category": case["category"],
            "score": verdict.score,
            "rationale": verdict.rationale,
            "candidate_response": response,
            "usage": verdict.usage.model_dump(),
        })
        print(
            f"  [{i:2}/{len(cases)}] {verdict.score}/5  {case['id']}  "
            f"(${verdict.usage.cost_usd:.4f})",
            flush=True,
        )

    scored = [r for r in results if r.get("score") is not None]
    mean_score = (sum(r["score"] for r in scored) / len(scored)) if scored else 0.0

    (artefacts_dir / "qualitative-cases.jsonl").write_text(
        "\n".join(json.dumps(r) for r in results) + "\n"
    )

    return {
        "headline_key": "mean_score",
        "mean_score": mean_score,
        "scored": len(scored),
        "total": len(cases),
        "judge_cost_usd": total_cost,
    }
