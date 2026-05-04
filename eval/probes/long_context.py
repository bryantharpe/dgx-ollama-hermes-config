"""Long-context recall probe (needle-in-haystack).

For each (target_context_tokens, position_fraction) sample:
  1. Build a haystack of approximately target_context_tokens by tiling a
     benign filler passage.
  2. Insert a unique, factoid-style "needle" sentence at the requested
     fractional position.
  3. Send the haystack to the model with a question asking for the exact
     needle string.
  4. Score: the canonical needle substring appears verbatim in the response.

Tier 1 runs the minimum useful sample: middle-of-document at 16k and 128k
tokens. Tier=full extends across more lengths and positions (added later).

Headline metric: needle_recall (fraction of samples passed).
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

import httpx

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))
from api import post_chat  # noqa: E402

HTTP_TIMEOUT = 600.0
CHARS_PER_TOKEN = 4  # rough; Qwen tokenizers run ~3.5-4 chars/token on plain English


# Benign, repetitive-but-grammatical filler. Public-domain prose adapted
# from generic descriptive writing — chosen to be coherent enough that we
# can't accidentally fail because the model rejects gibberish, and dull
# enough that no sentence stands out near the needle.
FILLER_PARAGRAPH = (
    "The afternoon light slanted across the meadow in long pale stripes, "
    "and the wind moved through the tall grass without urgency. Far above, "
    "a single hawk traced lazy circles in the warm thermals, watching "
    "without expectation. The river that ran along the edge of the field "
    "was low for the season, and the stones along its bank were white "
    "with old salt. Children had been here in the morning, leaving the "
    "soft earth marked with the prints of bare feet and the wheels of a "
    "small wooden cart, but they had gone home before noon and the field "
    "had returned to its older quiet. A handful of butterflies crossed "
    "the path now and then, never staying long, and the bees worked the "
    "clover with the patient methodical rhythm that bees have always had. "
    "The sky was the deep clear blue of late summer, the kind that makes "
    "the green of the hills seem darker than it is. Somewhere a tractor "
    "started up, ran for a few seconds, and stopped again. The sound "
    "carried a long way in the still air and then was gone, and the only "
    "noise left was the small movements of the grass and the occasional "
    "distant call of a bird whose name nobody in the village remembered. "
)
# Approx 1170 chars => ~290 tokens per paragraph. To reach 128k tokens we
# need ~440 repetitions; cheap to generate at runtime.

NEEDLE_TEXT = "The secret pass-phrase for the Hermes evaluation is 'mango-7913-purple'."
NEEDLE_ANSWER = "mango-7913-purple"

# A plausible-looking distractor sentence with the same shape, different topic,
# different value. Used in the distractor-stretch sample.
DISTRACTOR_TEXT = (
    "The secret pass-phrase for the production cluster is 'avocado-4218-blue'."
)
DISTRACTOR_ANSWER = "avocado-4218-blue"  # the WRONG answer; we score recall of NEEDLE_ANSWER

QUESTION = (
    "Read the document above. Inside it there is exactly one sentence that "
    "states a secret pass-phrase. Reply with ONLY the pass-phrase string, "
    "in single quotes (e.g. 'foo-bar-baz'). Do not explain or restate the "
    "sentence."
)

QUESTION_DISTRACTOR = (
    "Read the document above. It contains TWO sentences that look similar — "
    "one mentions the 'production cluster' and one mentions the 'Hermes "
    "evaluation'. Reply with ONLY the pass-phrase associated with the "
    "Hermes evaluation, in single quotes (e.g. 'foo-bar-baz'). Do not "
    "explain or restate the sentence."
)


def _build_haystack(target_tokens: int, position_fraction: float) -> str:
    target_chars = target_tokens * CHARS_PER_TOKEN
    repeats = (target_chars // len(FILLER_PARAGRAPH)) + 2
    base = FILLER_PARAGRAPH * repeats
    base = base[:target_chars]
    insert_at = int(target_chars * position_fraction)
    # snap to nearest space so we don't slice mid-word
    while insert_at > 0 and base[insert_at] != " ":
        insert_at -= 1
    return base[:insert_at] + " " + NEEDLE_TEXT + " " + base[insert_at:]


def _build_distractor_haystack(target_tokens: int) -> str:
    """Plant the decoy at fraction 0.30 and the real needle at 0.70."""
    target_chars = target_tokens * CHARS_PER_TOKEN
    repeats = (target_chars // len(FILLER_PARAGRAPH)) + 2
    base = FILLER_PARAGRAPH * repeats
    base = base[:target_chars]
    decoy_at = int(target_chars * 0.30)
    needle_at = int(target_chars * 0.70)
    while decoy_at > 0 and base[decoy_at] != " ":
        decoy_at -= 1
    while needle_at > 0 and base[needle_at] != " ":
        needle_at -= 1
    # insert needle first (later position) so we don't shift the decoy index
    base = base[:needle_at] + " " + NEEDLE_TEXT + " " + base[needle_at:]
    return base[:decoy_at] + " " + DISTRACTOR_TEXT + " " + base[decoy_at:]


def _ask(endpoint: str, model: str, haystack: str, ctx: dict,
         question: str = QUESTION) -> str:
    body = {
        "model": model,
        "messages": [
            {"role": "user", "content": haystack + "\n\n---\n\n" + question},
        ],
        # 256 not 64 — reasoning models (DeepSeek V4 Pro, OpenAI o-series)
        # need budget to think through the prompt before emitting the answer.
        # 256 is still tiny in absolute terms; the needle itself is ~30 tokens.
        "max_tokens": 256,
        "temperature": 0.0,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    data = post_chat(endpoint, body, ctx, "long_context", timeout=HTTP_TIMEOUT)
    msg = data["choices"][0]["message"]
    raw = (msg.get("content")
           or msg.get("reasoning_content")
           or msg.get("reasoning")
           or "")
    return re.sub(r"<think>.*?</think>\s*", "", raw, flags=re.DOTALL | re.IGNORECASE).strip()


# Sample shape: (label, builder_fn, question_text, context_tokens).
# Builders take no arguments — they're closures over the sample's parameters.
def _basic(target_tokens: int, position_fraction: float):
    label = f"{target_tokens//1000}k@{position_fraction:.2f}"
    return (
        label,
        lambda: _build_haystack(target_tokens, position_fraction),
        QUESTION,
        target_tokens,
    )


def _distractor(target_tokens: int):
    label = f"{target_tokens//1000}k+distractor"
    return (
        label,
        lambda: _build_distractor_haystack(target_tokens),
        QUESTION_DISTRACTOR,
        target_tokens,
    )


# Tier 1: middle-position at 16k + 128k (saturated for Qwen 27B), plus stretch:
# 128k near-end (0.95 — "lost in the haystack" at extreme position) and a
# 64k haystack with a plausible distractor needle.
TIER1_SAMPLES = [
    _basic(16_000, 0.50),
    _basic(128_000, 0.50),
    _basic(128_000, 0.95),
    _distractor(64_000),
]
TIER_FULL_EXTRA = [
    _basic(4_000, 0.50),
    _basic(64_000, 0.25),
    _basic(64_000, 0.50),
    _basic(64_000, 0.75),
    _basic(128_000, 0.25),
    _basic(128_000, 0.75),
    _distractor(128_000),
]


def run(ctx: dict) -> dict:
    endpoint = ctx["endpoint"]
    model = ctx["model"]
    quick = ctx.get("quick", False)
    artefacts_dir = ctx["artefacts_dir"]

    if quick:
        samples = [_basic(4_000, 0.50)]
    elif os.environ.get("EVAL_LONGCTX_FULL"):
        samples = TIER1_SAMPLES + TIER_FULL_EXTRA
    else:
        samples = TIER1_SAMPLES

    results = []
    passed = 0
    for label, build_fn, question, ctx_tokens in samples:
        haystack = build_fn()
        t0 = time.perf_counter()
        try:
            answer = _ask(endpoint, model, haystack, ctx, question=question)
            elapsed = time.perf_counter() - t0
            recalled = NEEDLE_ANSWER in answer
            tripped_distractor = (
                question is QUESTION_DISTRACTOR and DISTRACTOR_ANSWER in answer
            )
        except Exception as e:
            answer = f"<error: {type(e).__name__}: {e}>"
            elapsed = time.perf_counter() - t0
            recalled = False
            tripped_distractor = False
        if recalled:
            passed += 1
        results.append({
            "label": label,
            "context_tokens": ctx_tokens,
            "elapsed_seconds": elapsed,
            "recalled": recalled,
            "tripped_distractor": tripped_distractor,
            "answer_excerpt": answer[:200],
        })
        marker = "PASS" if recalled else "FAIL"
        suffix = " (picked DECOY)" if tripped_distractor else ""
        print(f"  [{label}] {marker}{suffix}  ({elapsed:.1f}s)", flush=True)

    needle_recall = passed / len(samples) if samples else 0.0

    artefacts_path = artefacts_dir / "long-context.jsonl"
    artefacts_path.write_text(
        "\n".join(__import__("json").dumps(r) for r in results) + "\n"
    )

    return {
        "headline_key": "needle_recall",
        "needle_recall": needle_recall,
        "passed": passed,
        "total": len(samples),
        "distractor_trips": sum(1 for r in results if r.get("tripped_distractor")),
        "samples": results,
    }
