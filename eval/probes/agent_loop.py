"""Agent-loop probe — multi-turn scenarios with mock tools, judged by Opus 4.6.

For each scenario:
  1. Send `task` as user message + `tools` + `tool_choice=auto`.
  2. If the model emits tool_call(s), each is dispatched to scenario `mock(...)`,
     which returns a string the harness feeds back as a `tool` message.
  3. Loop until the model emits a final text answer with no tool calls, or
     until `max_turns` is reached.
  4. Submit the full trajectory to Opus 4.6 with the agent.md rubric.

Scenarios are defined inline because mock tool implementations are Python
callables — easier than serializing scriptable behaviour as JSONL.

Headline metric: mean trajectory score / 5.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

import httpx

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))

from judge import JudgeResult, judge, make_client  # noqa: E402
from api import post_chat  # noqa: E402

RUBRIC = THIS_DIR.parent / "rubrics" / "agent.md"
HTTP_TIMEOUT = 240.0


import re as _re
_THINK_RE = _re.compile(r"<think>.*?</think>\s*", _re.DOTALL | _re.IGNORECASE)


def _strip_think(s: str) -> str:
    return _THINK_RE.sub("", s).strip()


# ----- Tool schema helpers ----------------------------------------------------

def _fn(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


# ----- Scenarios --------------------------------------------------------------

def _flight_mock(name: str, args: dict) -> str:
    if name == "search_flights":
        return json.dumps([
            {"flight_id": "UA123", "carrier": "United", "depart": "08:00", "arrive": "16:30", "price": 320},
            {"flight_id": "DL456", "carrier": "Delta",  "depart": "10:15", "arrive": "18:45", "price": 290},
            {"flight_id": "AA789", "carrier": "American", "depart": "14:00", "arrive": "22:30", "price": 350},
        ])
    if name == "book_flight":
        if args.get("flight_id") in {"UA123", "DL456", "AA789"}:
            return json.dumps({"status": "booked", "confirmation": "PNR-XYZ42",
                               "flight_id": args["flight_id"]})
        return json.dumps({"status": "error", "reason": f"unknown flight_id {args.get('flight_id')!r}"})
    return json.dumps({"error": f"unknown tool {name!r}"})


def _user_lookup_mock(name: str, args: dict) -> str:
    if name == "find_user_by_email":
        if args.get("email") == "alice@example.com":
            return json.dumps({"status": "not_found",
                               "hint": "no user with that email — try find_user_by_name with first name"})
        return json.dumps({"status": "not_found"})
    if name == "find_user_by_name":
        if (args.get("name") or "").lower().strip().startswith("alice"):
            return json.dumps({"id": 7, "name": "Alice Chen", "email": "alice.chen@example.com",
                               "role": "engineer"})
        return json.dumps({"status": "not_found"})
    if name == "get_user_orders":
        if args.get("user_id") == 7:
            return json.dumps([
                {"order_id": "O-1001", "total": 49.99, "status": "shipped"},
                {"order_id": "O-1042", "total": 12.50, "status": "pending"},
            ])
        return json.dumps({"status": "not_found", "user_id": args.get("user_id")})
    return json.dumps({"error": f"unknown tool {name!r}"})


def _bill_split_mock(name: str, args: dict) -> str:
    if name == "subtract":
        return json.dumps({"result": float(args["a"]) - float(args["b"])})
    if name == "divide":
        if float(args["b"]) == 0:
            return json.dumps({"error": "divide by zero"})
        return json.dumps({"result": float(args["a"]) / float(args["b"])})
    if name == "multiply":
        return json.dumps({"result": float(args["a"]) * float(args["b"])})
    return json.dumps({"error": f"unknown tool {name!r}"})


def _weather_mock(name: str, args: dict) -> str:
    if name == "get_weather":
        city = (args.get("city") or "").lower()
        if "paris" in city:
            return json.dumps({"city": "Paris", "tomorrow": {"high_c": 12, "low_c": 6,
                               "condition": "rainy", "rain_chance_pct": 80}})
        if "tokyo" in city:
            return json.dumps({"city": "Tokyo", "tomorrow": {"high_c": 24, "low_c": 18,
                               "condition": "clear"}})
        return json.dumps({"city": args.get("city"), "status": "unavailable"})
    return json.dumps({"error": f"unknown tool {name!r}"})


def _schedule_mock(name: str, args: dict) -> str:
    if name == "get_user_calendar":
        if (args.get("user_id") or "").lower() == "bob":
            # Bob's calendar for next Tuesday (2026-05-12) Pacific. Times in 24h Pacific.
            return json.dumps({
                "user_id": "bob",
                "date": "2026-05-12",
                "timezone": "America/Los_Angeles",
                "busy_blocks": [
                    {"start": "09:00", "end": "10:00", "title": "1:1"},
                    {"start": "12:00", "end": "13:00", "title": "Lunch"},
                    {"start": "15:30", "end": "16:30", "title": "Standup"},
                ],
            })
        return json.dumps({"status": "not_found"})
    if name == "create_event":
        # Validate the model didn't propose a slot inside Bob's busy blocks
        # OR inside lunch (12:00-13:00).
        start = (args.get("start_time") or "")
        bad_lunch = any(s in start for s in ["T12:", "T12:30", " 12:", "12:00", "12:30"])
        bad_busy = any(s in start for s in ["T09:", "T15:30", "09:00", "15:30"])
        if bad_lunch or bad_busy:
            return json.dumps({"status": "error",
                               "reason": "conflict with existing block on Bob's calendar"})
        return json.dumps({"status": "created", "event_id": "evt_42",
                           "start_time": args.get("start_time"),
                           "duration_minutes": args.get("duration_minutes")})
    return json.dumps({"error": f"unknown tool {name!r}"})


SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "flight_booking",
        "task": "Book me a flight from SFO to JFK on November 12, 2026. Pick the cheapest option.",
        "goal": "Search flights for SFO→JFK on 2026-11-12, identify the cheapest from the list "
                "(DL456 at $290), then call book_flight with that flight_id. Final response should "
                "name the carrier and confirmation code.",
        "max_turns": 6,
        "tools": [
            _fn("search_flights",
                "Search available flights between two airports on a date.",
                {
                    "origin": {"type": "string"},
                    "destination": {"type": "string"},
                    "date": {"type": "string", "description": "ISO 8601 date"},
                },
                ["origin", "destination", "date"]),
            _fn("book_flight",
                "Book a specific flight by its flight_id (returned from search_flights).",
                {"flight_id": {"type": "string"}},
                ["flight_id"]),
        ],
        "mock": _flight_mock,
    },
    {
        "id": "user_lookup_with_recovery",
        "task": "Look up Alice (alice@example.com) and tell me about her recent orders.",
        "goal": "find_user_by_email returns not_found with a hint to try find_user_by_name. "
                "Model should adapt: call find_user_by_name(name='Alice'), get id=7, then "
                "call get_user_orders(user_id=7), then summarise the two orders.",
        "max_turns": 8,
        "tools": [
            _fn("find_user_by_email",
                "Look up a user by email. Returns user record or not_found.",
                {"email": {"type": "string"}},
                ["email"]),
            _fn("find_user_by_name",
                "Look up a user by their first or full name (case-insensitive).",
                {"name": {"type": "string"}},
                ["name"]),
            _fn("get_user_orders",
                "Get recent orders for a user by their integer ID.",
                {"user_id": {"type": "integer"}},
                ["user_id"]),
        ],
        "mock": _user_lookup_mock,
    },
    {
        "id": "bill_split_math",
        "task": "Split a $237.00 dinner bill across 4 people, but Alice already paid $30 of it. "
                "How much does each of the OTHER three people owe to make things even? Use the "
                "calculator tools, then give me a single dollar figure.",
        "goal": "Compute (237 - 30) / 3 = $69. (Each other person owes $69; Alice has effectively "
                "paid 30 + her share already.) Tools: subtract then divide. Final answer: $69.",
        "max_turns": 6,
        "tools": [
            _fn("subtract", "Compute a - b.",
                {"a": {"type": "number"}, "b": {"type": "number"}}, ["a", "b"]),
            _fn("divide", "Compute a / b.",
                {"a": {"type": "number"}, "b": {"type": "number"}}, ["a", "b"]),
            _fn("multiply", "Compute a * b.",
                {"a": {"type": "number"}, "b": {"type": "number"}}, ["a", "b"]),
        ],
        "mock": _bill_split_mock,
    },
    {
        "id": "weather_recommendation",
        "task": "What's the weather in Paris tomorrow, and what should I pack for the day?",
        "goal": "Call get_weather(city='Paris'). Receive: high 12C, low 6C, rainy, 80% rain "
                "chance. Final response should give the weather summary AND sensible packing "
                "advice (rain jacket, layers) — both are required.",
        "max_turns": 4,
        "tools": [
            _fn("get_weather",
                "Get tomorrow's weather forecast for a city.",
                {"city": {"type": "string"}},
                ["city"]),
        ],
        "mock": _weather_mock,
    },
    {
        "id": "schedule_with_constraint",
        "task": "Schedule a 30-minute meeting with Bob on 2026-05-12 (he's in Pacific time). "
                "Pick a slot that avoids his lunch hour (12-1pm Pacific) and any existing "
                "blocks on his calendar. Confirm the booked time.",
        "goal": "Call get_user_calendar(user_id='bob') to see busy blocks "
                "(09:00, 12:00 lunch, 15:30 standup). Pick a free slot — e.g. 10:00, 11:00, "
                "13:00, 14:00 — and call create_event with that start_time and "
                "duration_minutes=30. Final response should state the chosen time.",
        "max_turns": 6,
        "tools": [
            _fn("get_user_calendar",
                "Get a user's calendar busy-blocks for a given date.",
                {
                    "user_id": {"type": "string"},
                    "date": {"type": "string", "description": "ISO 8601 date"},
                },
                ["user_id", "date"]),
            _fn("create_event",
                "Create a calendar event. start_time is ISO 8601; duration in minutes.",
                {
                    "title": {"type": "string"},
                    "start_time": {"type": "string"},
                    "duration_minutes": {"type": "integer"},
                    "attendees": {"type": "array", "items": {"type": "string"}},
                },
                ["title", "start_time", "duration_minutes"]),
        ],
        "mock": _schedule_mock,
    },
]


# ----- Agent loop -------------------------------------------------------------

def _vllm_chat(endpoint: str, model: str, messages: list[dict],
               tools: list[dict], ctx: dict) -> dict:
    body = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.0,
        "max_tokens": 1024,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    return post_chat(endpoint, body, ctx, "agent_loop", timeout=HTTP_TIMEOUT)


def _run_scenario(endpoint: str, model: str, scenario: dict, ctx: dict) -> dict:
    messages: list[dict] = [{"role": "user", "content": scenario["task"]}]
    trajectory: list[dict] = [{"turn": 0, "role": "user", "content": scenario["task"]}]
    final_text: str | None = None
    halt_reason = "max_turns"

    for turn in range(1, scenario["max_turns"] + 1):
        try:
            resp = _vllm_chat(endpoint, model, messages, scenario["tools"], ctx)
        except Exception as e:
            trajectory.append({"turn": turn, "role": "error", "error": f"{type(e).__name__}: {e}"})
            halt_reason = "vllm_error"
            break

        msg = resp["choices"][0]["message"]
        tool_calls = msg.get("tool_calls") or []

        # Record assistant turn (text and/or tool_calls) into the trajectory.
        traj_entry = {"turn": turn, "role": "assistant",
                      "text": _strip_think(msg.get("content") or msg.get("reasoning_content") or msg.get("reasoning") or "")}
        if tool_calls:
            traj_entry["tool_calls"] = [
                {
                    "id": tc.get("id"),
                    "name": (tc.get("function") or {}).get("name"),
                    "arguments": (tc.get("function") or {}).get("arguments"),
                }
                for tc in tool_calls
            ]
        trajectory.append(traj_entry)

        if not tool_calls:
            # Fallback across fields: sglang routes thinking-shaped output
            # to reasoning_content; vLLM keeps it in content; ollama leaves
            # raw <think>...</think> wrappers. Either way, we want the
            # model's last word, stripped of think-tag noise.
            final_text = _strip_think(msg.get("content") or msg.get("reasoning_content") or msg.get("reasoning") or "")
            halt_reason = "final_response"
            break

        # Append assistant message (preserve tool_calls structure for vLLM)
        messages.append({
            "role": "assistant",
            "content": msg.get("content") or "",
            "tool_calls": tool_calls,
        })

        # Dispatch each tool call to the scenario mock and append `tool` messages.
        for tc in tool_calls:
            tc_id = tc.get("id")
            fn = tc.get("function") or {}
            tname = fn.get("name") or ""
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
            except json.JSONDecodeError:
                args = {}

            try:
                result = scenario["mock"](tname, args)
            except Exception as e:
                result = json.dumps({"error": f"mock raised {type(e).__name__}: {e}"})

            trajectory.append({
                "turn": turn,
                "role": "tool",
                "tool_call_id": tc_id,
                "name": tname,
                "result": result,
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": result,
            })

    return {
        "id": scenario["id"],
        "task": scenario["task"],
        "goal": scenario["goal"],
        "max_turns": scenario["max_turns"],
        "tool_names": [t["function"]["name"] for t in scenario["tools"]],
        "trajectory": trajectory,
        "final_text": final_text,
        "halt_reason": halt_reason,
    }


def _judge_trajectory(rubric_md: str, scenario_run: dict, judge_client) -> JudgeResult:
    # Compact rendering of the trajectory for the judge.
    lines = [
        f"## Task\n\n{scenario_run['task']}",
        "",
        f"## Tools available to the model\n\n```json\n"
        f"{json.dumps(scenario_run.get('tool_names', []), indent=2)}\n```",
        "",
        f"## Goal state (what 'done correctly' looks like)\n\n{scenario_run['goal']}",
        "",
        f"## Halt reason: `{scenario_run['halt_reason']}`",
        "",
        "## Trajectory",
        "",
    ]
    for entry in scenario_run["trajectory"]:
        if entry["role"] == "user":
            lines.append(f"### Turn {entry['turn']} — user")
            lines.append(entry["content"])
        elif entry["role"] == "assistant":
            lines.append(f"### Turn {entry['turn']} — assistant")
            if entry.get("text"):
                lines.append(entry["text"])
            for tc in entry.get("tool_calls", []) or []:
                lines.append(f"  → tool_call `{tc['name']}` args={tc['arguments']}")
        elif entry["role"] == "tool":
            lines.append(
                f"### Turn {entry['turn']} — tool result `{entry['name']}` "
                f"(call {entry.get('tool_call_id')})"
            )
            lines.append(f"```\n{entry['result']}\n```")
        elif entry["role"] == "error":
            lines.append(f"### Turn {entry['turn']} — ERROR\n\n{entry.get('error')}")
        lines.append("")
    lines.append(f"## Final natural-language response\n\n{scenario_run.get('final_text') or '(none — model halted before final response)'}")

    return judge(
        rubric_md=rubric_md,
        content_text="\n".join(lines),
        client=judge_client,
    )


def run(ctx: dict) -> dict:
    if ctx.get("judge") != "opus46":
        return {
            "headline_key": "mean_score",
            "mean_score": None,
            "skipped": True,
            "skip_reason": "agent_loop probe requires --judge=opus46",
        }

    endpoint = ctx["endpoint"]
    model = ctx["model"]
    quick = ctx.get("quick", False)
    artefacts_dir = ctx["artefacts_dir"]

    rubric_md = RUBRIC.read_text()
    scenarios = SCENARIOS[:2] if quick else SCENARIOS

    judge_client = make_client()
    results = []
    total_score = 0
    total_cost = 0.0

    for i, scenario in enumerate(scenarios, 1):
        print(f"  [{i}/{len(scenarios)}] running {scenario['id']}...", flush=True)
        run_data = _run_scenario(endpoint, model, scenario, ctx)
        try:
            verdict = _judge_trajectory(rubric_md, run_data, judge_client)
        except Exception as e:
            results.append({
                "id": scenario["id"], "score": None,
                "halt_reason": run_data["halt_reason"],
                "error": f"judge call failed: {e!r}",
            })
            print(f"      JUDGE ERROR: {e}", flush=True)
            continue

        total_score += verdict.score
        total_cost += verdict.usage.cost_usd
        results.append({
            "id": scenario["id"],
            "score": verdict.score,
            "rationale": verdict.rationale,
            "halt_reason": run_data["halt_reason"],
            "turns_taken": max(e["turn"] for e in run_data["trajectory"]),
            "trajectory": run_data["trajectory"],
            "final_text": run_data["final_text"],
            "usage": verdict.usage.model_dump(),
        })
        print(
            f"      → {verdict.score}/5  halt={run_data['halt_reason']}  "
            f"turns={results[-1]['turns_taken']}  (${verdict.usage.cost_usd:.4f})",
            flush=True,
        )

    scored = [r for r in results if r.get("score") is not None]
    mean_score = (sum(r["score"] for r in scored) / len(scored)) if scored else 0.0

    (artefacts_dir / "agent-loop.jsonl").write_text(
        "\n".join(json.dumps(r) for r in results) + "\n"
    )

    return {
        "headline_key": "mean_score",
        "mean_score": mean_score,
        "scored": len(scored),
        "total": len(scenarios),
        "judge_cost_usd": total_cost,
    }
