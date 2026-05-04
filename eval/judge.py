"""Claude Opus 4.6 judge — scores model outputs against a rubric.

Architecture:
- Rubric (long, stable across many calls in one session) is sent as the system
  prompt with `cache_control: ephemeral, ttl: 1h`. Subsequent calls in the same
  session pay ~0.1× for the rubric portion instead of full price.
- Structured output via strict tool use — `submit_grade(score: 1-5, rationale)`
  with `tool_choice` forcing the tool. Avoids fragile JSON-in-text parsing.
- Thinking disabled (judging is well-scoped and we want predictable cost).
- Multimodal-ready: pass `image_paths=[...]` to include screenshots in the
  user content (used by the prototype-judging probe in Session 3).
- Per-call cost tracking using current Opus 4.6 pricing.

Bryan's explicit choice: claude-opus-4-6 (not 4.7). One-line swap if changed.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Literal, Optional

import anthropic
from pydantic import BaseModel, Field

JUDGE_MODEL = "claude-opus-4-6"
DEFAULT_MAX_TOKENS = 1024

# Opus 4.6 pricing per 1M tokens (USD). Update if pricing changes.
PRICE_INPUT_BASE_PER_M = 5.00
PRICE_OUTPUT_PER_M = 25.00
PRICE_CACHE_WRITE_5M_PER_M = 6.25     # 1.25× base
PRICE_CACHE_WRITE_1H_PER_M = 10.00    # 2.00× base
PRICE_CACHE_READ_PER_M = 0.50         # 0.10× base


GRADE_TOOL = {
    "name": "submit_grade",
    "description": (
        "Submit your numeric grade (1=worst, 5=best) and a short rationale "
        "for the content under evaluation. Use the rubric in the system "
        "prompt as the source of truth for what each score means."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "enum": [1, 2, 3, 4, 5],
                "description": "Score per the rubric anchors.",
            },
            "rationale": {
                "type": "string",
                "description": "1-3 sentences citing specific evidence from the content.",
            },
        },
        "required": ["score", "rationale"],
        "additionalProperties": False,
    },
}


class JudgeUsage(BaseModel):
    input_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    output_tokens: int
    cost_usd: float


class JudgeResult(BaseModel):
    score: int = Field(ge=1, le=5)
    rationale: str
    usage: JudgeUsage


def _compute_cost_usd(usage: anthropic.types.Usage, ttl: str) -> float:
    write_rate = (
        PRICE_CACHE_WRITE_1H_PER_M if ttl == "1h" else PRICE_CACHE_WRITE_5M_PER_M
    )
    creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
    read = getattr(usage, "cache_read_input_tokens", 0) or 0
    return (
        usage.input_tokens * PRICE_INPUT_BASE_PER_M
        + creation * write_rate
        + read * PRICE_CACHE_READ_PER_M
        + usage.output_tokens * PRICE_OUTPUT_PER_M
    ) / 1_000_000


def _image_block(image_path: Path) -> dict:
    suffix = image_path.suffix.lstrip(".").lower()
    media_type = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
    }.get(suffix)
    if media_type is None:
        raise ValueError(f"unsupported image suffix: {suffix!r}")
    data = base64.standard_b64encode(image_path.read_bytes()).decode()
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def make_client() -> anthropic.Anthropic:
    """Build a client, refusing if no API key is set so callers fail clearly."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Required for --judge=opus46. "
            "Either export it or run with --judge=none."
        )
    return anthropic.Anthropic()


def judge(
    *,
    rubric_md: str,
    content_text: str,
    image_paths: Optional[list[Path]] = None,
    cache_ttl: Literal["5m", "1h"] = "1h",
    model: str = JUDGE_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    client: Optional[anthropic.Anthropic] = None,
) -> JudgeResult:
    """Grade `content_text` (and optional images) against `rubric_md`.

    The rubric is the first content seen by the model and is marked for caching;
    repeated calls within ttl pay ~0.1× for the rubric portion. The minimum
    cacheable prefix on Opus 4.6 is 4096 tokens — shorter rubrics will silently
    not cache (no error, just `cache_read_input_tokens=0`).
    """
    if client is None:
        client = make_client()

    user_content: list[dict] = []
    for img in image_paths or []:
        user_content.append(_image_block(Path(img)))
    user_content.append({"type": "text", "text": content_text})

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[{
            "type": "text",
            "text": rubric_md,
            "cache_control": {"type": "ephemeral", "ttl": cache_ttl},
        }],
        messages=[{"role": "user", "content": user_content}],
        tools=[GRADE_TOOL],
        tool_choice={"type": "tool", "name": "submit_grade"},
        thinking={"type": "disabled"},
    )

    tool_block = next(
        (b for b in response.content if b.type == "tool_use"
         and b.name == "submit_grade"),
        None,
    )
    if tool_block is None:
        raise RuntimeError(
            f"judge did not return a tool_use block; stop_reason={response.stop_reason}"
        )

    args = tool_block.input
    usage = JudgeUsage(
        input_tokens=response.usage.input_tokens,
        cache_creation_input_tokens=getattr(
            response.usage, "cache_creation_input_tokens", 0
        ) or 0,
        cache_read_input_tokens=getattr(
            response.usage, "cache_read_input_tokens", 0
        ) or 0,
        output_tokens=response.usage.output_tokens,
        cost_usd=_compute_cost_usd(response.usage, ttl=cache_ttl),
    )
    return JudgeResult(
        score=int(args["score"]),
        rationale=str(args["rationale"]),
        usage=usage,
    )
