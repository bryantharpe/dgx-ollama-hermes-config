# Model Eval Harness — Plan

**Date:** 2026-05-02
**Goal:** A repeatable, mostly-quantitative eval harness that Bryan can run against the currently-served vLLM model after every swap, to answer "is this model good for *my* workloads, and is the configuration right?" The harness covers Performance, Coding ability, and Agent ability (tool calls + long-running multi-turn). Results are diff-able across model swaps.
**Effort:** M — three sessions, ~10–12h total.
**Blast radius:** new `eval/` directory + one new Claude Code skill + one new OpenClaw skill. Does not touch the running vLLM service or OpenClaw configuration. Pure read-side.

---

## Architecture

Two layers, separable so each can be developed and tested independently.

```
┌──────────────────────────────────────────────────────────┐
│  Claude Code skill: /eval-current-model                   │
│   → orchestrates probes, calls judge, writes report       │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  Core: eval/runner.py + probes/* + judge.py              │
│   → hits vLLM /v1/* endpoint, scores, persists artefacts  │
└──────────────────────────────────────────────────────────┘
```

Core is plain Python — runnable standalone for CI-like use. Skill layer adds judgment, narrative reports, and ergonomics.

### Roles — orchestrator vs system-under-test

This separation is load-bearing for the eval to be sound:

- **Orchestrator (test driver) = Claude Code, always.** Runs probes, calls judge, writes reports. Hits `vllm:8001/v1` directly for perf / tools / coding / qualitative — OpenClaw is not in the loop.
- **System under test = the model itself,** by default. For one probe specifically (`agent_prototype`), the system-under-test expands to "OpenClaw + model" because the whole point of that probe is to measure the *real* transcript-to-prototype skill chain end-to-end. Claude Code drives OpenClaw via its HTTP API as a *test target*, captures artifacts, then judges.
- **OpenClaw is never the orchestrator.** Earlier drafts considered an OpenClaw skill wrapper that shelled out to Claude Code; that framing is dropped. Running the harness *through* OpenClaw would let OpenClaw's prompt scaffolding and skill-routing become hidden test apparatus, making it impossible to attribute regressions cleanly.

---

## Layout

```
hermes-config/
  eval/
    runner.py                    # CLI: --tier {1,2,full,agent} --endpoint --model --judge {opus46|none}
    probes/
      perf.py                    # tok/s, TTFT, decode @ concurrency 1/2/4, KV headroom
      coding.py                  # HumanEval-mini (50 problems, sandboxed exec) → pass@1
      tools.py                   # BFCL subset (~100 single-turn) → AST/exec accuracy
      agent_loop.py              # mini τ-bench: 10 multi-turn scenarios with mock tools
      agent_prototype.py         # OpenClaw transcript→prototype end-to-end (see below)
      qualitative.py             # 10 OpenClaw-shape prompts → judged
    judge.py                     # Claude API client, structured JSON scoring, prompt-cached
    rubrics/
      coding.md
      agent.md
      openclaw.md
      prototype-screenshot.md    # vision rubric for prototype screenshots
    datasets/
      humaneval-mini.jsonl
      bfcl-subset.jsonl
      agent-scenarios.jsonl
      openclaw-shape.jsonl
      prototype-transcripts/     # 2-3 fixed test transcripts
        meeting-A.txt            # canonical "build me a CRUD app" transcript
        meeting-B.txt            # canonical "build me a dashboard" transcript
    results/
      <model_id>/
        <ISO-timestamp>/
          summary.json           # all numbers, machine-readable
          report.md              # human-readable, with diff vs prior run
          artifacts/
            perf.csv
            coding-outputs.jsonl
            agent-trajectories.jsonl
            prototype-runs/
              meeting-A/
                chat-log.json    # full agent conversation history
                specs.md         # generated specs file
                prototype.tar.gz # generated prototype source tree
                screenshot.png   # headless-browser shot of running prototype
                judge-rubric.json# judge's structured scores
              meeting-B/
                ...
    .claude/
      skills/
        eval-current-model.md
        compare-eval-runs.md
```

---

## Eval categories

### 1. Performance (priority: high)
Pure metrics, no judge.

| Metric | How |
|---|---|
| Decode tok/s @ concurrency=1 | curl loop, 400 tokens, `ignore_eos=true` |
| Decode tok/s @ concurrency=4 | parallel curl, aggregate |
| TTFT @ prompt-len 1k / 16k / 128k | curl with timing |
| KV cache headroom | parse vLLM `/metrics` |
| Prefix-cache hit rate | repeated-prefix workload, parse metrics |

Output: `perf.csv`, summary deltas vs prior run.

### 2. Coding (priority: high)
Hybrid: deterministic + judge.

- **HumanEval-mini** (50 problems): sandboxed code exec → pass@1 (deterministic).
- **5 multi-file tasks** (e.g. "implement a small TODO API in FastAPI"): code generated, written to temp dir, optionally executed; **Opus 4.6 judges** on a code-quality rubric (correctness, idiomaticness, error handling, test coverage if asked).

### 3. Tool calls (priority: high — agent dimension)
- **BFCL subset** (~100 single-turn): AST + execution scoring → function-call accuracy %. Fully deterministic.

### 4. Agent (long-running) (priority: high)
Two layers: synthetic and real-OpenClaw.

**a) Synthetic agent loops (`agent_loop.py`):**
- 10 multi-turn scenarios with mock tools (booking, search, math).
- Trajectory length: 5–15 turns each.
- **Opus 4.6 judges** trajectory quality + final-state correctness against rubric.

**b) Real OpenClaw scenario — transcript-to-prototype pipeline (`agent_prototype.py`):**
This is the killer test, since it exercises the *real* OpenClaw skill chain (`meeting-transcript-to-specs` Q8 → `meeting-specs-to-prototype` Q5) end-to-end, against the model under test.

Per-run flow for each fixed transcript in `datasets/prototype-transcripts/`:
1. Submit transcript to OpenClaw via its API. Capture every agent message + tool call into `chat-log.json`.
2. After the specs phase, snapshot the generated `specs.md` → save under `artifacts/prototype-runs/<transcript>/specs.md`.
3. After the prototype phase, the prototype-seeder spins up a docker container serving the generated site. Snapshot the generated source tree → `prototype.tar.gz`.
4. Headless browser (Playwright, chromium) navigates to the prototype URL, takes a full-page screenshot → `screenshot.png`.
5. **Tear down the prototype container immediately** — artifacts persist on disk so we don't need it running anymore.
6. **Opus 4.6 (multimodal) judges**, in a single API call per transcript, with prompt caching on the rubric prefix:
   - Chat log: trajectory coherence, tool-use correctness, error recovery, total turns vs target.
   - Specs markdown: completeness against transcript requirements, structure quality.
   - Screenshot: visual quality, requirement coverage (does it actually look like the thing the transcript asked for?), no broken UI.
7. Output: structured JSON scores into `judge-rubric.json`. Aggregate to a single composite "agent-prototype" score in `summary.json`.

Comparison: subsequent runs diff the JSON scores against the most recent run for the same transcript, and Opus 4.6 also diffs the *current* artifacts vs the *previous* artifacts (chat log, specs, screenshot) to call out behavior regressions in plain English in `report.md`.

This is what makes the eval fundamentally OpenClaw-shaped — we're not measuring abstract capability, we're measuring "did this model just do my real job worse than the last one?"

### 5. Qualitative (priority: medium)
- 10 hand-authored OpenClaw-shape prompts (orchestration, structured outputs, reasoning toggle behavior, refusal calibration). Each judged by Opus 4.6 on a 1–5 rubric.

---

## Tiers

| Tier | What runs | Wall-time | Judge cost (Opus 4.6 + cache) |
|---|---|---|---|
| **`--tier=1`** (every swap) | perf, BFCL, IFEval-tiny, qualitative | ~10–15 min | ~$0.20 |
| **`--tier=agent`** (when an agent regression is suspected) | tier 1 + synthetic agent + transcript-to-prototype (1 transcript) | ~30–40 min | ~$0.80 |
| **`--tier=full`** (big swaps) | everything, both transcripts | ~60–90 min | ~$1.50–$2.00 |

Costs are estimates; will calibrate after Session 2 with real measurements.

---

## Judge model

**Opus 4.6** (`claude-opus-4-6`) for all judging.

Why Bryan chose 4.6 over 4.7: explicit preference. The harness passes `model="claude-opus-4-6"` everywhere; if a future swap to 4.7 is wanted, it's a one-line change in `judge.py`.

Judge calls use **prompt caching** on the rubric prefix to keep cost down across many graded outputs in the same run — every probe that uses the same rubric shares a cache prefix.

Multimodal: Opus 4.6 receives both text artifacts (chat log JSON, specs markdown) and images (prototype screenshots) in the same judge call for the prototype scenario.

---

## Output: report.md shape

```markdown
# Eval — qwen3.6-27b-int4:128k @ 2026-05-02T18:30Z

## Summary vs previous (qwen3.6-27b-int4:128k @ 2026-04-29T14:00Z)
| Metric | Prev | Now | Δ |
|---|---|---|---|
| Decode tok/s (c=1) | 20.0 | 19.8 | -1% |
| HumanEval pass@1 | 0.62 | 0.60 | -3% |
| BFCL accuracy | 0.84 | 0.86 | +2% |
| Agent trajectory score | 4.1 | 4.0 | -2% |
| Prototype composite | 3.8 | 3.6 | -5%  ⚠ |

## Regressions called out by judge
- Prototype screenshot for meeting-A is missing the "delete" button that prior run included. ...

## Full numbers
[expandable section]
```

---

## Phasing

### Session 1 — scaffolding + deterministic probes (~3–4h) — **DONE 2026-05-02**
- `eval/` directory, `runner.py` CLI, results layout
- `probes/perf.py`, `probes/tools.py` (BFCL-mini, 20 cases), `probes/coding.py` (HumanEval-mini, 10 problems, sandboxed via `python:3.12-slim --network=none`)
- IFEval integration deferred to Session 2 (lm-evaluation-harness adds a real dep weight; first baseline already meaningful without it)
- Hardenings landed during validation: pre-flight + between-probe `/health` gate; concurrent-decode default dropped to c=2 after c=4 triggered `cudaErrorIllegalAddress` in vLLM 0.17.0-t5 + MTP; full raw response persisted to artifacts; syntax-vs-logic split for coding failures
- **First baseline (qwen3.6-27b-int4:128k):** decode tok/s c=1 = 20.1, c=2 aggregate = 42.4, TTFT 1k = 1.30s / 16k = 15.76s, BFCL accuracy = 1.000, HumanEval-mini pass@1 = 0.900

### Session 2 — judge + qualitative + synthetic agent (~3–4h)
- `judge.py` with Claude API client, prompt caching, structured JSON scoring
- `rubrics/*.md` authored
- `probes/qualitative.py`, `probes/agent_loop.py`
- Validation: `--tier=agent --judge=opus46` runs end-to-end, judge cost logged.

### Session 3 — transcript-to-prototype probe + skills + diffing (~3–4h)
- `probes/agent_prototype.py` — the real OpenClaw end-to-end test, including Playwright screenshot capture and prototype-container teardown. Claude Code drives OpenClaw's HTTP API as a *test target* (not as orchestrator).
- `datasets/prototype-transcripts/` — 2 fixed transcripts authored
- `compare-eval-runs.md` skill — diffs two timestamped runs for the same model
- `eval-current-model.md` Claude Code skill — orchestrates a full or tier-1 run, writes the markdown report
- Validation: full run produces a `report.md` with prior-run diff and judge regression callouts.

---

## Decisions made

- **Judge model: Opus 4.6** (Bryan explicit choice).
- **Claude Code is the only orchestrator.** OpenClaw appears exactly once — as the system-under-test inside the `agent_prototype` probe — and never drives the harness. Earlier draft of an OpenClaw skill wrapper is dropped.
- **Prototype eval saves artifacts to disk** (chat-log.json, specs.md, prototype.tar.gz, screenshot.png) so the prototype docker container can be torn down immediately after the screenshot — no long-lived running prototype needed.
- **OpenClaw scenario uses real transcript-to-prototype skill chain**, not a synthetic stand-in, because that's the actual workload.
- **Hand-authored datasets to start.** Real OpenClaw transcripts can be mined later once the harness shape is proven.
- **Plain Python core, skill layer on top** — so the harness is usable without Claude Code if needed (e.g. cron'd nightly).

## Open questions (deferrable)

- **Test transcript content** — need to author 2 transcripts representative of Bryan's actual prototype-skill usage. Will draft in Session 3 and confirm with Bryan.
- **HumanEval sandbox** — run inside a throwaway docker container with no network and a CPU/memory cap, or in a local restricted subprocess? Docker is safer; subprocess is simpler. Default to docker.
- **Should perf probes warm KV cache first?** Yes — first request is unrepresentative. Will add a discard-first-N-requests option.
- **Retention policy for `results/`** — keep last N runs per model, archive older? Defer; will accumulate slowly enough that this isn't urgent.

## Validation

End-to-end success criteria:
- `python eval/runner.py --tier=1` against current vLLM produces `summary.json` + `report.md` in under 15 min.
- `python eval/runner.py --tier=full` produces same plus prototype artifacts + judge scores in under 90 min.
- `report.md` contains a side-by-side diff vs the prior run for the same model.
- Re-running tier=1 immediately produces near-identical numbers (variance < 5% on perf metrics).
- `/eval-current-model` skill works from inside Claude Code.
