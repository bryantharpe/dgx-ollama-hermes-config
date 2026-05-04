"""Tool-calling probe (tools-hard).

Hand-authored single-response function-call cases. Each sends a prompt and a
tools schema to /v1/chat/completions and scores the model's tool_calls output
deterministically. Designed to NOT saturate at 1.000 on a 27B-class model:
includes parallel tool calls, large-catalog noise, underspecification (model
must clarify, not hallucinate), datetime/decimal/boolean/list/enum tricks,
and "no extras" enforcement.

Case schema (JSONL):
  id              str    — stable identifier
  prompt          str    — user message
  tools           list   — OpenAI tools array
  expected_calls  list   — list of {name, args}; empty means NO calls expected
  args_strict     list   — keys whose value must equal expected exactly
  args_substring  list   — keys whose expected value must be a substring of
                           actual (case-insensitive). Useful for free-text args.
  args_listset    list   — keys whose value is a list, scored as set equality
  args_present    list   — keys that must simply exist (non-null) in actual
                           (used for nested objects where exact value varies)
  allow_extras    bool   — if true, extra tool_calls beyond expected don't fail.
                           Default false.
  _intent         str    — author note, ignored by scorer.

Headline metric: accuracy (passed / total).
"""
from __future__ import annotations

import json
from pathlib import Path

import sys
import httpx

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))
from api import post_chat  # noqa: E402

DATASETS = [
    THIS_DIR.parent / "datasets" / "tools-hard.jsonl",
    THIS_DIR.parent / "datasets" / "tools-stretch.jsonl",
]
HTTP_TIMEOUT = 120.0


def _load_cases() -> list[dict]:
    cases = []
    for path in DATASETS:
        if not path.exists():
            continue
        with path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    cases.append(json.loads(line))
    return cases


def _call(endpoint: str, model: str, case: dict, ctx: dict) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": case["prompt"]}],
        "tools": case["tools"],
        "tool_choice": "auto",
        "temperature": 0.0,
        "max_tokens": 1024,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    return post_chat(endpoint, body, ctx, "tools", timeout=HTTP_TIMEOUT)


def _extract_tool_calls(resp: dict) -> list[dict]:
    """Return all tool_calls as a list of {name, args} dicts. args may be None
    if the arguments JSON didn't parse (recorded as a parse_error)."""
    choices = resp.get("choices") or []
    if not choices:
        return []
    msg = choices[0].get("message") or {}
    raw_calls = msg.get("tool_calls") or []
    out = []
    for tc in raw_calls:
        fn = tc.get("function") or {}
        name = fn.get("name")
        raw_args = fn.get("arguments")
        if isinstance(raw_args, dict):
            args = raw_args
            parse_error = False
        elif isinstance(raw_args, str):
            try:
                args = json.loads(raw_args)
                parse_error = False
            except json.JSONDecodeError:
                args = None
                parse_error = True
        else:
            args = {}
            parse_error = False
        out.append({"name": name, "args": args, "_raw_arguments": raw_args,
                    "_parse_error": parse_error})
    return out


def _normalize_expected(case: dict) -> list[dict]:
    """Backwards-compat: lift legacy `expected_call` (single dict | null)
    into the new `expected_calls` list shape."""
    if "expected_calls" in case:
        return case["expected_calls"] or []
    legacy = case.get("expected_call")
    if legacy is None:
        return []
    return [legacy]


def _args_match(expected: dict, actual: dict, scoring: dict) -> tuple[bool, list[str]]:
    """Return (matched, notes). Empty expected dict + no scoring rules => trivial pass."""
    notes: list[str] = []
    if actual is None:
        return False, ["arguments JSON did not parse"]

    for key in scoring.get("args_strict", []):
        if key not in expected:
            continue  # rule doesn't apply to this expected call
        if key not in actual:
            notes.append(f"missing strict arg {key!r}")
            return False, notes
        if actual[key] != expected[key]:
            notes.append(
                f"strict arg {key!r}: {actual[key]!r} != {expected[key]!r}"
            )
            return False, notes

    for key in scoring.get("args_substring", []):
        if key not in expected:
            continue
        if key not in actual:
            notes.append(f"missing substring arg {key!r}")
            return False, notes
        a = str(actual[key]).lower()
        e = str(expected[key]).lower()
        if e not in a:
            notes.append(f"substring arg {key!r}: {a!r} does not contain {e!r}")
            return False, notes

    for key in scoring.get("args_listset", []):
        if key not in expected:
            continue
        if key not in actual:
            notes.append(f"missing listset arg {key!r}")
            return False, notes
        a_norm = {str(x).strip().lower() for x in (actual[key] or [])}
        e_norm = {str(x).strip().lower() for x in (expected[key] or [])}
        if a_norm != e_norm:
            notes.append(f"listset arg {key!r}: {a_norm} != {e_norm}")
            return False, notes

    for key in scoring.get("args_present", []):
        if key not in actual or actual.get(key) in (None, "", [], {}):
            notes.append(f"missing present arg {key!r}")
            return False, notes

    return True, []


def _score_case(case: dict, actual_calls: list[dict]) -> dict:
    expected_calls = _normalize_expected(case)
    allow_extras = bool(case.get("allow_extras", False))
    notes: list[str] = []

    # Drop any actuals with parse errors and record them
    parse_errors = [c for c in actual_calls if c.get("_parse_error")]
    valid_actuals = [c for c in actual_calls if not c.get("_parse_error")]
    if parse_errors:
        notes.append(f"{len(parse_errors)} tool_call(s) with unparseable arguments")

    # Case 1: no calls expected
    if not expected_calls:
        if len(valid_actuals) == 0 and not parse_errors:
            return {"passed": True, "notes": notes}
        names = [c.get("name") for c in valid_actuals] + ["<parse_err>"] * len(parse_errors)
        notes.append(f"expected NO tool calls, got {names}")
        return {"passed": False, "notes": notes}

    # Case 2: too few or too many actual calls
    if not allow_extras and len(valid_actuals) != len(expected_calls):
        notes.append(
            f"call count mismatch: expected {len(expected_calls)}, "
            f"got {len(valid_actuals)} valid"
        )
        return {"passed": False, "notes": notes}
    if allow_extras and len(valid_actuals) < len(expected_calls):
        notes.append(
            f"call count too low: expected ≥{len(expected_calls)}, "
            f"got {len(valid_actuals)} valid"
        )
        return {"passed": False, "notes": notes}

    # Greedy match: for each expected call, find an unmatched actual with same
    # name AND args matching all scoring rules.
    scoring = {
        "args_strict": case.get("args_strict", []),
        "args_substring": case.get("args_substring", []),
        "args_listset": case.get("args_listset", []),
        "args_present": case.get("args_present", []),
    }
    used = [False] * len(valid_actuals)
    for exp in expected_calls:
        matched_idx = None
        for i, act in enumerate(valid_actuals):
            if used[i]:
                continue
            if act["name"] != exp["name"]:
                continue
            ok, _ = _args_match(exp.get("args") or {}, act.get("args") or {}, scoring)
            if ok:
                matched_idx = i
                break
        if matched_idx is None:
            notes.append(
                f"no valid actual call matched expected {exp['name']}({exp.get('args') or {}})"
            )
            return {"passed": False, "notes": notes}
        used[matched_idx] = True

    return {"passed": True, "notes": notes}


def run(ctx: dict) -> dict:
    endpoint = ctx["endpoint"]
    model = ctx["model"]
    quick = ctx.get("quick", False)
    artefacts_dir = ctx["artefacts_dir"]

    cases = _load_cases()
    if quick:
        cases = cases[:5]

    results = []
    passed = 0
    for i, case in enumerate(cases, 1):
        try:
            resp = _call(endpoint, model, case, ctx)
            actual = _extract_tool_calls(resp)
            score = _score_case(case, actual)
        except Exception as e:
            actual = []
            score = {"passed": False, "notes": [f"error: {e!r}"]}
        if score["passed"]:
            passed += 1
        results.append({
            "id": case["id"],
            "passed": score["passed"],
            "notes": score["notes"],
            "actual_calls": actual,
        })
        marker = "PASS" if score["passed"] else "FAIL"
        print(f"  [{i:2}/{len(cases)}] {marker} {case['id']}", flush=True)

    accuracy = passed / len(cases) if cases else 0.0

    (artefacts_dir / "tools-cases.jsonl").write_text(
        "\n".join(json.dumps(r) for r in results) + "\n"
    )

    return {
        "headline_key": "accuracy",
        "accuracy": accuracy,
        "passed": passed,
        "total": len(cases),
        "datasets": [p.name for p in DATASETS if p.exists()],
    }
