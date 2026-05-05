"""Agent-prototype probe — exercises the OpenClaw transcript→prototype pipeline.

This probe scores the *whole ecosystem* with the candidate model serving both
the orchestrator (Captain Nemo) and the inner build coder. For each transcript
fixture we:

  1. Pipe the transcript to `openclaw-cli agent --agent main` (Phase 1: propose).
     The orchestrator runs the `meeting-transcript-to-specs` skill and writes
     proposal.md / design.md / tasks.md under
     /home/admin/code/hermes-config/prototypes/<slug>/openspec/changes/prototype/.
  2. Send a build-confirmation message in the same session (Phase 2: build).
     Captain Nemo calls prototypes.build + sessions_spawn to delegate to the
     prototype-builder subagent, which runs `meeting-specs-to-prototype`,
     scaffolds from _template/, and brings up `docker compose`.
  3. Poll prototypes/.registry/ports.json for the slug; once a port appears
     and the container responds, capture a Playwright screenshot.
  4. Bundle the trajectory + specs + source-tree + screenshot and ship the lot
     to Opus 4.6 with rubrics/prototype-screenshot.md (multimodal judge).
  5. Tear down (compose down -v, rmi, rm -rf, registry edit).

The probe is heavy: ~30-60 minutes per transcript. Default to 1 fixture
(recipe-keeper, the simpler one) unless `quick=False` is overridden.

Set ctx['judge'] != 'opus46' to skip entirely.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))

from judge import JudgeResult, judge, make_client  # noqa: E402

REPO_ROOT = THIS_DIR.parent.parent
TRANSCRIPTS_DIR = THIS_DIR.parent / "datasets" / "prototype-transcripts"
RUBRIC = THIS_DIR.parent / "rubrics" / "prototype-screenshot.md"
PROTOTYPES_DIR = REPO_ROOT / "prototypes"
REGISTRY_PATH = PROTOTYPES_DIR / ".registry" / "ports.json"
OPENCLAW_COMPOSE = REPO_ROOT / "openclaw" / "docker-compose.yml"

# Dedicated agent for the probe — clone of `main` (Captain Nemo) defined in
# ~/.openclaw/openclaw.json with id `eval-nemo`. Same model + tool profile +
# subagent allowlist as main; only difference is the agent id, which gives
# the probe its own session key (`agent:eval-nemo:main`) so accumulated
# conversation history from the user's real chats doesn't contaminate the
# test. The CLI's `--session-id` flag is ignored by the gateway for any
# given agent (the gateway hardcodes `agent:<id>:main` as the session key),
# so a separate agent is the only way to get true session isolation.
EVAL_AGENT = "eval-nemo"

PHASE1_TIMEOUT_S = 900       # 15 min — propose phase, no docker work
PHASE2_TIMEOUT_S = 3600      # 60 min — build phase. Bumped from 40 min on
                             # 2026-05-05: a successful Coder-Next @ t=0.3 run
                             # ran 41 min in Phase 2 (orchestrator improvising
                             # frontend code after the spawned build subagent
                             # finished), squeaking past the prior ceiling.
                             # Hour gives breathing room for the orchestrator
                             # to verify + patch + redeploy without dying mid-
                             # iteration.
SUBPROCESS_GRACE_S = 120
BUILD_POLL_S = 3600          # extra polling AFTER phase 2 returns. Bumped from
                             # 30 min for the same reason — the build subagent
                             # often keeps editing files past the orchestrator
                             # turn boundary; we want to capture the last-state
                             # screenshot, not a transient mid-edit one.
BUILD_POLL_INTERVAL_S = 15
HTTP_PROBE_TIMEOUT_S = 10
SCREENSHOT_TIMEOUT_MS = 30_000
SPECS_SUBPATH = Path("openspec") / "changes" / "prototype"

# Per-process unique suffix for slug uniquification. Set once at import time
# so all fixtures in a single eval invocation share it. Tests can override by
# putting `run_ts` on the ctx dict.
import datetime as _dt
_RUN_TS = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d-%H%M%S")

# Candidate fixtures — order matters: quick-mode runs only the first.
FIXTURES = [
    {
        "id": "recipe-keeper",
        "transcript": "meeting-A.txt",
        "expected_slug": "recipe-keeper",
        "build_message": (
            "Yes, please go ahead and build the prototype. Use the "
            "default Python+FastAPI+SQLite stack."
        ),
    },
    {
        "id": "standup-tracker",
        "transcript": "meeting-B.txt",
        "expected_slug": "standup-tracker",
        "build_message": (
            "Yes, build it. Default stack is fine."
        ),
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# Small helpers
# ──────────────────────────────────────────────────────────────────────────────

def _read_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {}
    try:
        return json.loads(REGISTRY_PATH.read_text())
    except json.JSONDecodeError:
        return {}


def _write_registry(data: dict) -> None:
    REGISTRY_PATH.write_text(json.dumps(data, indent=2) + "\n")


def _slug_already_exists(slug: str) -> bool:
    return slug in _read_registry() or (PROTOTYPES_DIR / slug).exists()


def _truncate(s: str, n: int) -> str:
    if not s:
        return s
    return s if len(s) <= n else s[:n] + f"\n... [truncated, {len(s)-n} more chars]"


def _safe_subprocess_log(name: str, completed: subprocess.CompletedProcess,
                         artefacts: Path) -> None:
    """Persist stdout/stderr of a subprocess for post-mortem."""
    (artefacts / f"{name}.stdout.txt").write_text(completed.stdout or "")
    (artefacts / f"{name}.stderr.txt").write_text(completed.stderr or "")


# ──────────────────────────────────────────────────────────────────────────────
# openclaw-cli wrapper
# ──────────────────────────────────────────────────────────────────────────────

def _openclaw_agent(message: str, *, agent: str = "main",
                    session_id: Optional[str] = None,
                    timeout_s: int) -> dict:
    """Run `openclaw-cli agent` once. Returns parsed JSON or {error, raw}.

    Subprocess runs `docker compose run --rm openclaw-cli ...` against the
    project compose file. We pass the message via env to avoid quoting
    games and a temp file to avoid /tmp pollution.
    """
    cmd = [
        "docker", "compose",
        "-f", str(OPENCLAW_COMPOSE),
        "run", "--rm",
        "openclaw-cli", "agent",
        "--agent", agent,
        "--message", message,
        "--json",
        "--timeout", str(timeout_s),
    ]
    if session_id:
        cmd.extend(["--session-id", session_id])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s + SUBPROCESS_GRACE_S,
        )
    except subprocess.TimeoutExpired as e:
        return {
            "error": f"subprocess timeout after {timeout_s + SUBPROCESS_GRACE_S}s",
            "raw_stdout": (e.stdout or b"").decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""),
            "raw_stderr": (e.stderr or b"").decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or ""),
        }

    out = proc.stdout or ""
    err = proc.stderr or ""

    # The CLI prints banner lines to stderr; the JSON payload comes on stdout.
    # In some configurations it may emit a banner on stdout before the JSON,
    # so try to find the last `{...}` block.
    parsed = None
    for candidate in (out.strip(),):
        try:
            parsed = json.loads(candidate)
            break
        except json.JSONDecodeError:
            pass
    if parsed is None:
        # Try last JSON object in stdout
        match = re.search(r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}\s*\Z", out, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                parsed = None

    return {
        "ok": parsed is not None and proc.returncode == 0,
        "returncode": proc.returncode,
        "parsed": parsed,
        "raw_stdout": out,
        "raw_stderr": err,
    }


def _extract_session_id(cli_result: dict) -> Optional[str]:
    """Best-effort: pull a session id out of the openclaw-cli --json output.

    The JSON shape has shifted across versions; check several keys.
    """
    p = cli_result.get("parsed") or {}
    for key in ("session_id", "sessionId", "id"):
        v = p.get(key)
        if isinstance(v, str) and v:
            return v
    sess = p.get("session")
    if isinstance(sess, dict):
        for key in ("id", "session_id", "sessionId"):
            v = sess.get(key)
            if isinstance(v, str) and v:
                return v
    return None


def _extract_response_text(cli_result: dict) -> str:
    """Best-effort: pull the orchestrator's reply text out of --json output."""
    p = cli_result.get("parsed") or {}
    for key in ("response", "reply", "text", "message", "content", "output"):
        v = p.get(key)
        if isinstance(v, str) and v:
            return v
    if isinstance(p.get("messages"), list) and p["messages"]:
        last = p["messages"][-1]
        if isinstance(last, dict):
            for key in ("content", "text"):
                v = last.get(key)
                if isinstance(v, str) and v:
                    return v
    return ""


# ──────────────────────────────────────────────────────────────────────────────
# Build-status polling + screenshot
# ──────────────────────────────────────────────────────────────────────────────

def _wait_for_port(slug: str, deadline: float) -> Optional[int]:
    while time.time() < deadline:
        port = _read_registry().get(slug)
        if isinstance(port, int):
            return port
        time.sleep(BUILD_POLL_INTERVAL_S)
    return None


def _wait_for_http_200(port: int, deadline: float) -> Optional[int]:
    """Poll http://localhost:<port>/ until status<500 or deadline. Returns last status."""
    last_status: Optional[int] = None
    while time.time() < deadline:
        try:
            r = httpx.get(f"http://localhost:{port}/",
                          timeout=HTTP_PROBE_TIMEOUT_S,
                          follow_redirects=True)
            last_status = r.status_code
            if r.status_code < 500:
                return r.status_code
        except Exception:
            last_status = None
        time.sleep(5)
    return last_status


def _capture_screenshot(port: int, out_path: Path) -> Optional[str]:
    """Run Playwright to capture a viewport screenshot. Returns error or None."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        return f"playwright import failed: {e}"

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            page.set_default_timeout(SCREENSHOT_TIMEOUT_MS)
            try:
                page.goto(f"http://localhost:{port}/", wait_until="domcontentloaded")
                # Best-effort wait for app to settle; don't fail if network never idles.
                try:
                    page.wait_for_load_state("networkidle", timeout=8_000)
                except Exception:
                    pass
                page.screenshot(path=str(out_path), full_page=False)
            finally:
                ctx.close()
                browser.close()
    except Exception as e:
        return f"playwright capture failed: {type(e).__name__}: {e}"
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Spec collection + cleanup
# ──────────────────────────────────────────────────────────────────────────────

def _read_spec_files(slug: str) -> dict:
    base = PROTOTYPES_DIR / slug / SPECS_SUBPATH
    out = {}
    for name in ("proposal.md", "design.md", "tasks.md"):
        p = base / name
        if p.exists():
            try:
                out[name] = p.read_text()
            except Exception as e:
                out[name] = f"<read-error: {e}>"
        else:
            out[name] = None
    return out


def _list_source_tree(slug: str, max_lines: int = 200) -> str:
    src = PROTOTYPES_DIR / slug
    if not src.exists():
        return "(no project directory)"
    lines: list[str] = []
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src)
        # Skip openspec/ artifacts and node_modules-style noise
        if str(rel).startswith("openspec/") or "__pycache__" in rel.parts:
            continue
        if path.is_file():
            try:
                size = path.stat().st_size
            except OSError:
                size = -1
            lines.append(f"{size:>8}  {rel}")
        if len(lines) >= max_lines:
            lines.append(f"... (truncated at {max_lines} entries)")
            break
    return "\n".join(lines) if lines else "(empty)"


def _cleanup(slug: str, artefacts: Path) -> dict:
    """Best-effort teardown. Logs each step's outcome to artefacts."""
    log: list[str] = []

    proto_dir = PROTOTYPES_DIR / slug
    compose = proto_dir / "docker-compose.yml"
    if compose.exists():
        try:
            r = subprocess.run(
                ["docker", "compose", "-f", str(compose), "down", "-v"],
                capture_output=True, text=True, timeout=120,
            )
            log.append(f"compose down: rc={r.returncode}")
        except Exception as e:
            log.append(f"compose down: ERR {e}")

    try:
        r = subprocess.run(
            ["docker", "rmi", "-f", f"{slug}:latest"],
            capture_output=True, text=True, timeout=60,
        )
        log.append(f"rmi: rc={r.returncode}")
    except Exception as e:
        log.append(f"rmi: ERR {e}")

    if proto_dir.exists():
        try:
            shutil.rmtree(proto_dir)
            log.append("rmtree: ok")
        except PermissionError:
            # Seeder may have written root-owned files (chown root:root in Phase 2)
            try:
                r = subprocess.run(
                    ["sudo", "-n", "rm", "-rf", str(proto_dir)],
                    capture_output=True, text=True, timeout=30,
                )
                log.append(f"sudo rm: rc={r.returncode}")
            except Exception as e:
                log.append(f"rmtree: PermissionError, sudo failed: {e}")
        except Exception as e:
            log.append(f"rmtree: ERR {e}")

    reg = _read_registry()
    if slug in reg:
        try:
            del reg[slug]
            _write_registry(reg)
            log.append("registry: removed")
        except Exception as e:
            log.append(f"registry: ERR {e}")

    (artefacts / "cleanup.log").write_text("\n".join(log) + "\n")
    return {"steps": log}


# ──────────────────────────────────────────────────────────────────────────────
# Per-fixture run
# ──────────────────────────────────────────────────────────────────────────────

def _run_fixture(fixture: dict, ctx: dict, fixture_dir: Path) -> dict:
    # Mint a unique slug per run by suffixing with the run timestamp. The
    # transcript fixture text gets rewritten to substitute the new slug
    # everywhere `expected_slug` appears, so the orchestrator's instructions
    # match the slug we'll check on disk.
    #
    # Why: openclaw's Hindsight memory backend retains every prior
    # `prototypes.store_spec` to the `bryan-prototypes` bank (per
    # ~/.openclaw/openclaw.json). On repeat runs, recall fires on the
    # stable slug and Captain Nemo refuses to regenerate ("recipe-keeper
    # specs are already written"). Uniquifying the slug sidesteps that
    # without disturbing the bank.
    base_slug = fixture["expected_slug"]
    run_ts = ctx.get("run_ts") or _RUN_TS
    slug = f"{base_slug}-eval-{run_ts}"

    transcript_path = TRANSCRIPTS_DIR / fixture["transcript"]
    raw_transcript = transcript_path.read_text()
    transcript = raw_transcript.replace(base_slug, slug)

    fixture_dir.mkdir(parents=True, exist_ok=True)
    print(f"  → fixture {fixture['id']} (slug={slug})", flush=True)

    # Refuse to run if the slug already exists — would clobber real work.
    # (Highly unlikely with the timestamp suffix, but kept as a safety net.)
    if _slug_already_exists(slug):
        print(f"    ! slug {slug!r} already exists in registry or filesystem; "
              "skipping fixture to avoid clobbering existing work.", flush=True)
        return {
            "id": fixture["id"],
            "slug": slug,
            "status": "skipped_slug_exists",
            "score": None,
        }

    run_record: dict = {
        "id": fixture["id"],
        "base_slug": base_slug,
        "slug": slug,
        "transcript_chars": len(transcript),
    }

    # ── Phase 1: propose ─────────────────────────────────────────────────────
    # Mint a fresh session id for this fixture so Captain Nemo's in-session
    # conversation history doesn't contaminate the test. By default
    # `openclaw-cli agent --agent main` reuses the agent's default session,
    # which can carry weeks of unrelated chat history (Telegram, dashboard,
    # prior eval runs). With a fresh UUID, both Phase 1 and Phase 2 land in
    # an isolated session that only sees this fixture's two messages.
    session_id = str(uuid.uuid4())
    run_record["session_id"] = session_id

    print("    Phase 1: propose...", flush=True)
    t0 = time.time()
    phase1_message = (
        "Please run the meeting-transcript-to-specs skill on the following "
        "transcript. Generate the three OpenSpec artifacts (proposal.md, "
        "design.md, tasks.md) at the canonical path. Once done, ask if I want "
        "to build it.\n\n--- TRANSCRIPT ---\n\n" + transcript
    )
    phase1 = _openclaw_agent(phase1_message,
                             agent=EVAL_AGENT,
                             session_id=session_id,
                             timeout_s=PHASE1_TIMEOUT_S)
    run_record["phase1_seconds"] = round(time.time() - t0, 1)
    run_record["phase1_returncode"] = phase1.get("returncode")
    _safe_subprocess_log("phase1", subprocess.CompletedProcess(
        args=[], returncode=phase1.get("returncode") or -1,
        stdout=phase1.get("raw_stdout", ""), stderr=phase1.get("raw_stderr", ""),
    ), fixture_dir)
    (fixture_dir / "phase1.json").write_text(
        json.dumps(phase1.get("parsed") or {"_unparsed": True}, indent=2, default=str)
    )
    phase1_text = _extract_response_text(phase1)

    specs_phase1 = _read_spec_files(slug)
    specs_present_phase1 = sum(1 for v in specs_phase1.values() if v)

    # If specs didn't land, there's no point spending 40 minutes in phase 2;
    # but still try, because some skill versions write specs only on the build
    # turn (rare) or write to alt paths we can't see.
    if specs_present_phase1 == 0:
        print(f"      ! no spec files at {PROTOTYPES_DIR / slug / SPECS_SUBPATH}; "
              "phase 1 produced nothing usable. Continuing to phase 2 for evidence.",
              flush=True)

    # ── Phase 2: build ───────────────────────────────────────────────────────
    print("    Phase 2: build...", flush=True)
    t0 = time.time()
    phase2 = _openclaw_agent(
        fixture["build_message"],
        agent=EVAL_AGENT,
        session_id=session_id,
        timeout_s=PHASE2_TIMEOUT_S,
    )
    run_record["phase2_seconds"] = round(time.time() - t0, 1)
    run_record["phase2_returncode"] = phase2.get("returncode")
    _safe_subprocess_log("phase2", subprocess.CompletedProcess(
        args=[], returncode=phase2.get("returncode") or -1,
        stdout=phase2.get("raw_stdout", ""), stderr=phase2.get("raw_stderr", ""),
    ), fixture_dir)
    (fixture_dir / "phase2.json").write_text(
        json.dumps(phase2.get("parsed") or {"_unparsed": True}, indent=2, default=str)
    )
    phase2_text = _extract_response_text(phase2)

    # ── Wait for the prototype to come up (in case CLI returned early) ───────
    print("    Waiting for prototype port + HTTP...", flush=True)
    deadline = time.time() + BUILD_POLL_S
    port = _wait_for_port(slug, deadline)
    http_status: Optional[int] = None
    if port is not None:
        print(f"      port allocated: {port}; probing HTTP...", flush=True)
        http_status = _wait_for_http_200(port, deadline)
        print(f"      last HTTP status: {http_status}", flush=True)
    else:
        print(f"      no port for {slug!r} after {BUILD_POLL_S}s", flush=True)

    container_running = False
    if port is not None:
        try:
            r = subprocess.run(
                ["docker", "ps", "--filter", f"name={slug}", "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=10,
            )
            container_running = bool(r.stdout.strip())
        except Exception:
            pass

    build_status = {
        "port": port,
        "container_running": container_running,
        "http_status": http_status,
        "registry_entry": slug in _read_registry(),
    }
    (fixture_dir / "build-status.json").write_text(json.dumps(build_status, indent=2))
    run_record["build_status"] = build_status

    # ── Screenshot ───────────────────────────────────────────────────────────
    screenshot_path = fixture_dir / "screenshot.png"
    screenshot_error: Optional[str] = None
    if port is not None and http_status is not None and http_status < 500:
        screenshot_error = _capture_screenshot(port, screenshot_path)
        if screenshot_error:
            print(f"      screenshot: {screenshot_error}", flush=True)
        else:
            print(f"      screenshot: {screenshot_path.name}", flush=True)
    else:
        screenshot_error = "skipped: no reachable HTTP endpoint"
        print("      screenshot: skipped (no reachable HTTP)", flush=True)
    run_record["screenshot_error"] = screenshot_error

    # ── Re-read specs (some build flows write design tweaks) ─────────────────
    specs_final = _read_spec_files(slug)
    source_tree = _list_source_tree(slug)
    (fixture_dir / "source-tree.txt").write_text(source_tree)
    for name, content in specs_final.items():
        if content:
            (fixture_dir / f"spec-{name}").write_text(content)

    # ── Judge ────────────────────────────────────────────────────────────────
    rubric_md = RUBRIC.read_text()
    spec_section_lines = []
    for name in ("proposal.md", "design.md", "tasks.md"):
        body = specs_final.get(name)
        if body is None:
            spec_section_lines.append(f"### {name}\n\n*(missing — file not written by propose phase)*\n")
        else:
            spec_section_lines.append(f"### {name}\n\n```markdown\n{_truncate(body, 8000)}\n```\n")

    judge_text = "\n".join([
        "# Agent-prototype run for grading",
        "",
        f"## Transcript ({fixture['transcript']})",
        "",
        f"```\n{transcript}\n```",
        "",
        "## Phase 1 — propose (orchestrator response, JSON-extracted text)",
        "",
        f"- subprocess returncode: `{phase1.get('returncode')}`",
        f"- session_id: `{session_id or '(none extracted)'}`",
        f"- wall: {run_record['phase1_seconds']}s",
        "",
        "Reply text:",
        f"```\n{_truncate(phase1_text, 6000) or '(empty)'}\n```",
        "",
        "## Phase 1 — specs written",
        "",
        *spec_section_lines,
        "",
        "## Phase 2 — build (orchestrator response, JSON-extracted text)",
        "",
        f"- subprocess returncode: `{phase2.get('returncode')}`",
        f"- wall: {run_record['phase2_seconds']}s",
        "",
        "Reply text:",
        f"```\n{_truncate(phase2_text, 6000) or '(empty)'}\n```",
        "",
        "## Build status (after polling)",
        "",
        f"```json\n{json.dumps(build_status, indent=2)}\n```",
        "",
        "## Source tree under prototypes/<slug>/ (excluding openspec/)",
        "",
        f"```\n{_truncate(source_tree, 6000)}\n```",
        "",
        "## Screenshot",
        "",
        ("(attached as image to this message)" if screenshot_error is None
         else f"*(no screenshot — {screenshot_error})*"),
    ])

    (fixture_dir / "judge-input.md").write_text(judge_text)

    image_paths = [screenshot_path] if screenshot_error is None else None
    judge_client = ctx.get("_judge_client") or make_client()
    ctx["_judge_client"] = judge_client

    try:
        verdict: JudgeResult = judge(
            rubric_md=rubric_md,
            content_text=judge_text,
            image_paths=image_paths,
            client=judge_client,
        )
        run_record["score"] = verdict.score
        run_record["rationale"] = verdict.rationale
        run_record["judge_cost_usd"] = verdict.usage.cost_usd
        run_record["judge_usage"] = verdict.usage.model_dump()
        print(f"    → score: {verdict.score}/5  (${verdict.usage.cost_usd:.4f})",
              flush=True)
    except Exception as e:
        run_record["score"] = None
        run_record["judge_error"] = f"{type(e).__name__}: {e}"
        print(f"    ! judge failed: {e}", flush=True)

    # ── Cleanup (best-effort) ────────────────────────────────────────────────
    print("    Cleanup...", flush=True)
    cleanup_result = _cleanup(slug, fixture_dir)
    run_record["cleanup"] = cleanup_result

    return run_record


# ──────────────────────────────────────────────────────────────────────────────
# Entry point (matches probe contract)
# ──────────────────────────────────────────────────────────────────────────────

def run(ctx: dict) -> dict:
    if ctx.get("judge") != "opus46":
        return {
            "headline_key": "mean_score",
            "mean_score": None,
            "skipped": True,
            "skip_reason": "agent_prototype probe requires --judge=opus46",
        }

    if not OPENCLAW_COMPOSE.exists():
        return {
            "headline_key": "mean_score",
            "mean_score": None,
            "skipped": True,
            "skip_reason": f"openclaw compose not found at {OPENCLAW_COMPOSE}",
        }

    if not RUBRIC.exists():
        return {
            "headline_key": "mean_score",
            "mean_score": None,
            "skipped": True,
            "skip_reason": f"rubric not found at {RUBRIC}",
        }

    artefacts_dir = ctx["artefacts_dir"]
    quick = ctx.get("quick", False)
    fixtures = FIXTURES[:1] if quick else FIXTURES

    results: list[dict] = []
    total_judge_cost = 0.0

    for i, fixture in enumerate(fixtures, 1):
        fixture_dir = artefacts_dir / "agent-prototype" / fixture["id"]
        try:
            rec = _run_fixture(fixture, ctx, fixture_dir)
        except Exception as e:
            print(f"  [{i}/{len(fixtures)}] FATAL {fixture['id']}: {e}", flush=True)
            rec = {"id": fixture["id"], "score": None,
                   "fatal_error": f"{type(e).__name__}: {e}"}
        results.append(rec)
        total_judge_cost += rec.get("judge_cost_usd") or 0.0

    scored = [r for r in results if isinstance(r.get("score"), int)]
    mean_score = (sum(r["score"] for r in scored) / len(scored)) if scored else 0.0

    out_path = artefacts_dir / "agent-prototype.jsonl"
    out_path.write_text("\n".join(json.dumps(r, default=str) for r in results) + "\n")

    return {
        "headline_key": "mean_score",
        "mean_score": mean_score,
        "scored": len(scored),
        "total": len(fixtures),
        "judge_cost_usd": total_judge_cost,
    }
