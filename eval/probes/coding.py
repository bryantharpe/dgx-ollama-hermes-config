"""Coding probe (coding-hard, sandboxed).

Hand-authored coding problems with a difficulty curve designed to NOT saturate
on a 27B-class model: bug-finding, structural constraints (must be a generator,
must not import X), performance-gated (tight per-problem timeout), edge-case-
heavy specs, and non-canonical signatures.

For each problem:
  1. Send the prompt to /v1/chat/completions.
  2. Extract Python code from the response (handles ```python fences).
  3. AST-check structural constraints (must_be_generator, must_not_import).
  4. Run the candidate solution + reference tests inside a throwaway
     `python:3.12-slim` container with --network=none and a per-problem timeout.

Headline metric: pass@1.

Failure categorisation (in `summary`):
  syntax_failures      — code didn't parse (response truncation, malformed)
  constraint_failures  — code parsed but violated a structural constraint
  logic_failures       — code parsed and ran but tests failed
  timeout_failures     — exceeded max_runtime_ms in the sandbox
"""
from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

import sys
import httpx

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))
from api import post_chat  # noqa: E402

DATASET = THIS_DIR.parent / "datasets" / "coding-hard.jsonl"
HTTP_TIMEOUT = 240.0
SANDBOX_IMAGE = "python:3.12-slim"
SANDBOX_MEM = "512m"
DEFAULT_TASK_TIMEOUT_MS = 5000  # default per-problem budget if not specified
SANDBOX_OVERHEAD_MS = 8000      # docker run startup + image load overhead


SYSTEM_PROMPT = textwrap.dedent("""\
    You are a coding assistant. The user will give you a Python function —
    either a signature with docstring (write it from scratch), or a buggy
    implementation (return the corrected version). Reply with a SINGLE
    Python code block containing only the complete function definition.
    Do not include explanations, examples, or test code outside the
    function. Honor any constraints stated in the docstring (e.g. "must
    be a generator", "must not import X", performance budgets).
""").strip()


def _load_problems() -> list[dict]:
    out = []
    with DATASET.open() as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


_THINK_TAG_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)


def _response_text(message: dict) -> str:
    """Extract response text, falling back across engine-specific fields and
    stripping Qwen-style <think>...</think> wrappers.

    Engines disagree on where chain-of-thought-shaped output lands:
    - vLLM:    `content` (verbose, includes the thinking)
    - sglang:  `reasoning_content` when --reasoning-parser=qwen3 routes it,
               `content` otherwise
    - ollama:  `content` with literal <think>...</think> wrappers
    - OpenRouter: `content` for the answer + `reasoning` for chain-of-thought;
               on hard prompts the answer can land in `reasoning` with
               `content` empty
    """
    raw = (message.get("content")
           or message.get("reasoning_content")
           or message.get("reasoning")
           or "")
    return _THINK_TAG_RE.sub("", raw).strip()


def _generate_solution(endpoint: str, model: str, prompt: str, ctx: dict) -> str:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 2048,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    data = post_chat(endpoint, body, ctx, "coding", timeout=HTTP_TIMEOUT)
    return _response_text(data["choices"][0]["message"])


_FENCE_RE = re.compile(r"```(?:python)?\s*\n?(.*?)```", re.DOTALL | re.IGNORECASE)
_OPEN_FENCE_RE = re.compile(r"```(?:python)?\s*\n?", re.IGNORECASE)


def _extract_code(content: str) -> str:
    """Pull code out of the model's response.

    Prefers a fully-fenced ```python ... ``` block. If only an opening fence is
    present (truncation, or model forgot to close), strips it and returns the
    rest. Otherwise returns content as-is.
    """
    m = _FENCE_RE.search(content)
    if m:
        return m.group(1).strip()
    open_m = _OPEN_FENCE_RE.search(content)
    if open_m:
        return content[open_m.end():].strip()
    return content.strip()


def _check_constraints(code: str, constraints: dict) -> tuple[bool, list[str]]:
    """AST-check structural constraints on the candidate code.

    Returns (passed, violations). On parse failure returns (False, ['<reason>'])
    so the caller can short-circuit before sandboxing.
    """
    if not constraints:
        return True, []
    violations: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, [f"parse error: {e.msg} (line {e.lineno})"]

    must_be_generator = constraints.get("must_be_generator", False)
    must_not_import = set(constraints.get("must_not_import", []))
    must_be_class = constraints.get("must_be_class", False)

    if must_not_import:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in must_not_import:
                        violations.append(f"forbidden import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root in must_not_import:
                    violations.append(f"forbidden import: from {node.module}")

    if must_be_generator:
        # Find the top-level function def(s) and check at least one contains a yield.
        any_generator = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for sub in ast.walk(node):
                    if isinstance(sub, (ast.Yield, ast.YieldFrom)):
                        any_generator = True
                        break
        if not any_generator:
            violations.append("not a generator: no `yield` found in any function body")

    if must_be_class:
        has_class = any(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
        if not has_class:
            violations.append("must define a class — no class definition found")

    return (len(violations) == 0), violations


def _ensure_sandbox_image() -> bool:
    """Pull python:3.12-slim once if missing. Returns True on success."""
    inspect = subprocess.run(
        ["docker", "image", "inspect", SANDBOX_IMAGE],
        capture_output=True, text=True,
    )
    if inspect.returncode == 0:
        return True
    pull = subprocess.run(
        ["docker", "pull", SANDBOX_IMAGE],
        capture_output=True, text=True, timeout=180,
    )
    return pull.returncode == 0


def _run_in_sandbox(workdir: Path, task_timeout_ms: int) -> dict:
    """Run /work/runner.py inside an isolated container. Returns
    {"passed": bool, "stdout": str, "stderr": str, "exit_code": int,
     "timed_out": bool}.

    The host-side `timeout=` is task_timeout_ms + sandbox overhead, so a
    runaway program is killed at the docker layer. The runner.py also installs
    a SIGALRM at task_timeout_ms inside the container so a timeout is reported
    cleanly when the program is well-behaved.
    """
    host_timeout_s = (task_timeout_ms + SANDBOX_OVERHEAD_MS) / 1000.0
    cmd = [
        "docker", "run", "--rm",
        "--network=none",
        f"--memory={SANDBOX_MEM}",
        "--cpus=1.0",
        "--read-only",
        "--tmpfs", "/tmp:size=16m",
        "-v", f"{workdir}:/work:ro",
        "-w", "/work",
        SANDBOX_IMAGE,
        "python", "-u", "/work/runner.py",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=host_timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        return {
            "passed": False,
            "stdout": stdout,
            "stderr": f"TIMEOUT (sandbox killed by host after {host_timeout_s:.1f}s)",
            "exit_code": -1,
            "timed_out": True,
        }
    timed_out = proc.returncode == 124 or "TASK_TIMEOUT" in proc.stderr
    return {
        "passed": proc.returncode == 0,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "exit_code": proc.returncode,
        "timed_out": timed_out,
    }


_RUNNER_TEMPLATE = textwrap.dedent("""\
    import signal, sys, traceback, time

    def _timeout(signum, frame):
        raise TimeoutError("TASK_TIMEOUT after {task_timeout_s}s")
    signal.signal(signal.SIGALRM, _timeout)
    # Use setitimer for sub-second precision on the in-task budget.
    signal.setitimer(signal.ITIMER_REAL, {task_timeout_s})

    try:
        with open('/work/solution.py') as f:
            code = f.read()
        ns = {{'__name__': '__sandbox__'}}
        exec(compile(code, 'solution.py', 'exec'), ns)
        with open('/work/tests.py') as f:
            tests = f.read()
        exec(compile(tests, 'tests.py', 'exec'), ns)
    except TimeoutError as e:
        print('TASK_TIMEOUT', e, file=sys.stderr)
        sys.exit(124)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
    sys.exit(0)
""")


def _evaluate_one(problem: dict, raw_code: str, sandbox_ready: bool) -> dict:
    code = _extract_code(raw_code)
    constraints = problem.get("constraints") or {}
    task_timeout_ms = int(constraints.get("max_runtime_ms", DEFAULT_TASK_TIMEOUT_MS))

    # Stage 1: syntax. Distinguishes "model output never parsed" (truncation,
    # malformed fence) from real "tests failed".
    syntax_ok = True
    syntax_error = None
    try:
        compile(code, problem["id"] + ".py", "exec")
    except SyntaxError as se:
        syntax_ok = False
        syntax_error = f"{type(se).__name__}: {se.msg} (line {se.lineno})"

    # Stage 2: structural constraints (only if syntax is ok).
    constraint_ok = True
    constraint_violations: list[str] = []
    if syntax_ok and constraints:
        constraint_ok, constraint_violations = _check_constraints(code, constraints)

    result = {
        "id": problem["id"],
        "raw_response": raw_code,
        "extracted_code": code,
        "syntax_ok": syntax_ok,
        "syntax_error": syntax_error,
        "constraint_ok": constraint_ok,
        "constraint_violations": constraint_violations,
        "task_timeout_ms": task_timeout_ms,
        "passed": False,
    }
    if not sandbox_ready:
        result["error"] = "sandbox image unavailable"
        return result
    if not syntax_ok or not constraint_ok:
        result["sandbox_skipped"] = True
        return result

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        (td_path / "solution.py").write_text(code + "\n")
        (td_path / "tests.py").write_text(problem["tests"] + "\n")
        (td_path / "runner.py").write_text(
            _RUNNER_TEMPLATE.format(task_timeout_s=task_timeout_ms / 1000.0)
        )
        sb = _run_in_sandbox(td_path, task_timeout_ms=task_timeout_ms)

    result["passed"] = sb["passed"]
    result["sandbox_exit_code"] = sb["exit_code"]
    result["stderr_excerpt"] = sb["stderr"][:400] if sb["stderr"] else ""
    result["timed_out"] = sb.get("timed_out", False)
    return result


def run(ctx: dict) -> dict:
    endpoint = ctx["endpoint"]
    model = ctx["model"]
    quick = ctx.get("quick", False)
    artefacts_dir = ctx["artefacts_dir"]

    if not shutil.which("docker"):
        return {
            "headline_key": "pass_at_1",
            "pass_at_1": 0.0,
            "passed": 0,
            "total": 0,
            "skipped": True,
            "skip_reason": "docker not available on host",
        }

    sandbox_ready = _ensure_sandbox_image()

    problems = _load_problems()
    if quick:
        problems = problems[:3]

    per_problem = []
    passed = 0
    for i, prob in enumerate(problems, 1):
        try:
            content = _generate_solution(endpoint, model, prob["prompt"], ctx)
        except Exception as e:
            per_problem.append({
                "id": prob["id"], "passed": False,
                "error": f"generation failed: {e!r}",
            })
            print(f"  [{i:2}/{len(problems)}] FAIL {prob['id']} (gen error)", flush=True)
            continue
        result = _evaluate_one(prob, content, sandbox_ready)
        per_problem.append(result)
        if result["passed"]:
            passed += 1
        marker = "PASS" if result["passed"] else "FAIL"
        print(f"  [{i:2}/{len(problems)}] {marker} {prob['id']}", flush=True)

    pass_at_1 = passed / len(problems) if problems else 0.0
    syntax_failures = sum(1 for r in per_problem if not r.get("syntax_ok", True))
    constraint_failures = sum(
        1 for r in per_problem
        if r.get("syntax_ok", True) and not r.get("constraint_ok", True)
    )
    timeout_failures = sum(1 for r in per_problem if r.get("timed_out", False))
    logic_failures = sum(
        1 for r in per_problem
        if r.get("syntax_ok", True)
        and r.get("constraint_ok", True)
        and not r.get("timed_out", False)
        and not r.get("passed", False)
    )

    (artefacts_dir / "coding-problems.jsonl").write_text(
        "\n".join(json.dumps(r) for r in per_problem) + "\n"
    )

    return {
        "headline_key": "pass_at_1",
        "pass_at_1": pass_at_1,
        "passed": passed,
        "total": len(problems),
        "syntax_failures": syntax_failures,         # response truncation / malformed
        "constraint_failures": constraint_failures, # AST check failed (forbidden import, no yield, etc.)
        "timeout_failures": timeout_failures,       # exceeded max_runtime_ms
        "logic_failures": logic_failures,           # tests failed
        "dataset": DATASET.name,
        "sandbox_image": SANDBOX_IMAGE if sandbox_ready else None,
    }
