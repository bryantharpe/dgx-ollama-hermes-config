# scitrera/dgx-spark-vllm — pin matrix and bump pattern

Working notes for the vLLM 0.19+ NVFP4 build (see plan at
`~/.claude/plans/proud-noodling-allen.md`).

Source recipes pulled from
github.com/scitrera/cuda-containers @ HEAD = `6120269` (2026-05-02 clone).

## Phase 1 status: COMPLETE

The headline finding is **much better than feared** — see "Bump pattern"
and "Implications for Phase 3" below.

---

## Pin matrix (DGX Spark, ARM64 + Blackwell SM_120, `-t5` Transformers 5.x)

| Recipe         | Date       | Base image (dev / runtime)                          | CUDA   | PyTorch | FlashInfer | Triton | Transformers | vLLM source                                |
|----------------|-----------|-----------------------------------------------------|--------|---------|------------|--------|--------------|--------------------------------------------|
| 0.14.0-t5      | ~Jan 2026 | `dgx-spark-pytorch-{dev,runtime}:2.10.0-cu131`      | 13.1.0 | 2.10.0  | 0.6.1      | 3.5.1  | 5.0.0+git    | scitrera/vllm fork (`v0.14.0+glm4-moe-lite-mla`) |
| 0.15.0-t5      | ~Feb 2026 | `dgx-spark-pytorch-{dev,runtime}:2.10.0-cu131`      | 13.1.0 | 2.10.0  | 0.6.2      | 3.5.1  | 5.0.0        | upstream `v0.15.0`                          |
| 0.15.1-t5      | ~Feb 2026 | `dgx-spark-pytorch-{dev,runtime}:2.10.0-cu131`      | 13.1.0 | 2.10.0  | 0.6.2      | 3.5.1  | 5.0.0        | upstream `v0.15.1`                          |
| 0.16.0-t5      | 2026-02-13| `dgx-spark-pytorch-{dev,runtime}:2.10.0-v2-cu131`   | 13.1.1 | 2.10.0  | 0.6.5      | 3.6.0  | 5.3.0        | upstream `v0.16.0`                          |
| **0.17.0-t5** *(prod)* | 2026-03-07| `dgx-spark-pytorch-{dev,runtime}:2.10.0-v2-cu131`   | 13.1.1 | 2.10.0  | 0.6.5      | 3.6.0  | 5.3.0        | upstream `v0.17.0`                          |
| nightly-t5 *(experimental)* | rolling   | `dgx-spark-pytorch-{dev,runtime}:2.10.0-v2-cu131`   | 13.1.1 | 2.10.0  | 0.6.3      | 3.6.0  | `main`       | vllm-project/vllm `main`                    |

Note the experimental `sglang-0.5.10` recipe (top-level, current) sits on a
**newer** base — `dgx-spark-pytorch-dev:2.11.0-v1-cu132` (CUDA 13.2.0 +
PyTorch 2.11.0). FlashInfer 0.6.7.post3, Transformers 5.5.3. This proves
scitrera has a published 2.11/cu132 base lineage we can use if vLLM 0.19+
turns out to require it.

The `container-recipes/next/` directory exists but is **empty** —
confirms scitrera has not begun a 0.18+ recipe yet, so we are leading.

## Bump pattern (what changes between minor versions)

The build infrastructure (`container-build/build-image.sh` +
`Dockerfile.llm_inference`) is **recipe-driven**. A "recipe" is a
flat key=value file (~15 lines) that the build script translates to
`docker buildx build --build-arg KEY=VALUE`. The Dockerfile itself is
parametric and rarely changes.

Verified bump deltas (commits `dc87212` and `a4c0aef` in upstream):

- **0.15.1 → 0.16.0** (`dc87212`, 2026-02-13) — *medium bump*:
  - VLLM_VERSION 0.15.1 → 0.16.0
  - FLASHINFER_VERSION 0.6.2 → 0.6.5
  - TRITON_VERSION 3.5.1 → 3.6.0
  - TRANSFORMERS_VERSION 5.0.0 → 5.3.0
  - Base image bumped: `2.10.0-cu131` → `2.10.0-v2-cu131` (CUDA 13.1.0 → 13.1.1)
  - Dockerfile.llm_inference touched: ~60 lines changed for "late
    transformers installation" (the `TRANSFORMERS_REF` / `TRANSFORMERS_PRE`
    handling visible in the current Dockerfile lines 120–135).

- **0.16.0 → 0.17.0** (`a4c0aef`, 2026-03-07) — *trivial bump*:
  - VLLM_VERSION 0.16.0 → 0.17.0
  - **Nothing else changed.** Same base, same FlashInfer, same Triton,
    same Transformers, no Dockerfile delta.

The takeaway: scitrera's track record is "minor vLLM bumps are usually
one ARG change; CUDA/PyTorch base bumps are the expensive ones, and they
happen rarely (twice in the lineage so far — at 0.16 and at sglang-0.5.10)."

## Build flow (Dockerfile.llm_inference)

The Dockerfile does seven stages, all driven by build-args:

1. `builder_with_python_deps` — installs FlashInfer trio
   (`flashinfer-python` + `-cubin` + `-jit-cache`) from
   `flashinfer.ai/whl/cu130` index, plus `xgrammar`, `fastsafetensors`,
   cudnn-frontend, cutlass-dsl, ray, numba.
2. `triton_builder` — clones triton at `${TRITON_REF}` (defaults to
   `v${TRITON_VERSION}`), submodule update, `uv build` to wheels.
3. `vllm_builder` — clones `${VLLM_REPO}` (default upstream) at
   `${VLLM_REF}` (default `v${VLLM_VERSION}`), runs
   `python3 use_existing_torch.py`, strips `flashinfer` from
   `requirements/cuda.txt`, strips triton + fastsafetensors from
   `requirements/test.txt`, then `uv pip install --no-build-isolation .`.
4. Late `transformers` install — ARG-driven (`TRANSFORMERS_REF` >
   `TRANSFORMERS_VERSION` > `TRANSFORMERS_PRE` > do-nothing).
5. `directory_split.sh` — chops `dist-packages/` into 4 sub-dirs to dodge
   Docker layer-size limits; excludes `transformers*` so the t4/t5
   variants share lower layers.
6. `tiktoken_fetcher` (parallel branch) — downloads `o200k_base.tiktoken`,
   `cl100k_base.tiktoken`, plus the Nemotron-3-Nano reasoning parser.
7. `vllm_runtime` (final) — copies the four split dist-packages dirs from
   the builder into the runtime base, copies tiktoken assets, sets
   `PATH=/data/vllm:$PATH`.

Build-args we care about (subset of `KNOWN_BUILD_ARGS` from `build-image.sh`):
`DEV_BASE_IMAGE, RUN_BASE_IMAGE, FLASHINFER_VERSION, FLASHINFER_PRE,
TRITON_VERSION, TRITON_REF, VLLM_VERSION, VLLM_REF, VLLM_REPO,
TRANSFORMERS_VERSION, TRANSFORMERS_REF, TRANSFORMERS_PRE`.

## Phase 1 exit criterion — answered

**Q:** Is the 0.17 → 0.19 jump trivial (bump three ARGs) or non-trivial
(FlashInfer 0.7 source build, PyTorch 2.11 ABI)?

**A (provisional, pending Phase 2 cross-reference against vLLM 0.19.1
release notes):**

It looks **likely trivial**. Three reasons:

1. The historical bump pattern shows 0.16→0.17 was one ARG. Even the
   expensive 0.15→0.16 bump touched only build-args + a published-base
   bump.
2. The `vllm-nightly-t5` experimental recipe builds vllm@main against the
   *exact* same 2.10.0-v2-cu131 base our current 0.17 prod uses. If
   nightly main can build on that base, 0.19.1 release should as well.
3. The "next" dir is empty, but the scitrera maintainer has a clear
   pattern of incremental bumps — they haven't shipped 0.18+ yet
   probably because their Spark prod is happy on 0.17, not because of a
   blocker.

The realistic Phase 3 deliverable is therefore probably **a 15-line recipe
file**, not a forked Dockerfile. The strategy shifts from "draft a new
Dockerfile" to "drop a new recipe into `dgx-spark-vllm/recipes/` and
invoke `build-image.sh` against the upstream working tree" — much
cheaper to iterate.

## Implications for Phase 3 (revised approach)

**Original plan:** author `dgx-spark-vllm/Dockerfile.vllm-0.19.1-t5` from
scratch.

**Revised plan (proposed for Phase 3):**

1. Copy `vllm-0.17.0-t5.recipe` to a new file
   `dgx-spark-vllm/recipes/vllm-0.19.1-t5.recipe` with **only** the
   variables we change (vLLM version, possibly FlashInfer version per
   Phase 2 cross-reference).
2. Change `IMAGE_TAG` to `local/dgx-spark-vllm:0.19.1-t5-dev` so it
   cannot be confused with an upstream scitrera artifact.
3. `build.sh` becomes a thin wrapper that invokes
   `upstream/container-build/build-image.sh -f
   <our-recipe>` with logs piped to `dgx-spark-vllm/build-logs/`.
4. We do not fork the Dockerfile or the build script. If they break, we
   `git pull` upstream/.

Trade-off: we depend on `upstream/` staying around. Since `upstream/` is
gitignored and we want the recipes anyway, we accept this dependency and
document the `git clone` step in `dgx-spark-vllm/README.md` (Phase 3).

## Phase 2 — vLLM 0.19.1 vs 0.20.0 cross-reference (COMPLETE 2026-05-02)

Source-of-truth: `requirements/cuda.txt` and `requirements/common.txt`
fetched directly from vllm-project/vllm at refs `v0.17.0`, `v0.19.1`,
`v0.20.0` via `gh api`. Plus the model card for
`sakamakismile/Qwen3.6-27B-NVFP4` and its MTP sibling.

### Hard pins by version

| Pin                    | scitrera 0.17.0-t5 *(prod)* | vLLM v0.19.1 (`cuda.txt`) | vLLM v0.20.0 (`cuda.txt`) |
|------------------------|-----------------------------|---------------------------|---------------------------|
| `torch`                | 2.10.0                      | **2.10.0** ✅              | **2.11.0** 🚨              |
| `torchvision`          | 0.25.0                      | 0.25.0                    | 0.26.0                    |
| `flashinfer-python`    | 0.6.5                       | **0.6.6** (tiny bump)     | 0.6.8.post1               |
| `flashinfer-cubin`     | (bundled w/ python)         | **0.6.6** explicit        | 0.6.8.post1               |
| `nvidia-cudnn-frontend`| (auto)                      | `>=1.13.0,<1.19.0` cap    | same                      |
| `numba`                | (latest)                    | 0.61.2                    | 0.65.0                    |
| `triton` (test pin)    | 3.6.0                       | **3.6.0** ✅               | 3.6.0                     |
| `transformers`         | 5.3.0                       | **>=5.5.1** 🚨 (5.0–5.5.0 explicitly excluded) | same |
| `apache-tvm-ffi`       | (any, installed manually)   | (any)                     | 0.1.9 explicit            |
| `tilelang`             | (n/a)                       | (n/a)                     | 0.1.9 explicit (NEW dep)  |
| `nvidia-cutlass-dsl`   | (latest)                    | `>=4.4.0.dev1`            | `>=4.4.2`                 |
| `quack-kernels`        | (auto)                      | `>=0.2.7`                 | `>=0.3.3`                 |

### Decision: target **vLLM 0.19.1**

Reasons in priority order:
1. **PyTorch base unchanged.** 0.19.1 stays on `torch==2.10.0` →
   reuses `scitrera/dgx-spark-pytorch-{dev,runtime}:2.10.0-v2-cu131` →
   no base-image rebuild needed. 0.20.0 requires `torch==2.11.0` which
   means moving to the `2.11.0-v1-cu132` base — known-published
   (sglang-0.5.10 uses it) but bigger blast radius and additional bumps
   ride along (tilelang, apache-tvm-ffi, numba).
2. **Triton unchanged** (3.6.0 across all three).
3. **CUDA unchanged** (13.1.1 via the `-v2-cu131` base).
4. **Lower-risk delta:** four lines change from the 0.17.0-t5 recipe.
5. **NVFP4 stable on Blackwell.** v0.19.0 release notes mention
   "DGX Spark fix (#38126)" and "fix NVFP4 NaN on desktop Blackwell
   (#37725)" explicitly — 0.19.x is the version that hardens NVFP4
   for our exact target. v0.19.1 adds patch fixes on top.
6. **Model card alignment.** `sakamakismile/Qwen3.6-27B-NVFP4` model
   card states verbatim: *"Requirements: NVIDIA Blackwell GPU
   (SM 120), vLLM >= 0.19"* and was tested on **vLLM 0.19.1rc1**.

### Recipe diff vs 0.17.0-t5 (4 lines)

```
- VLLM_VERSION=0.17.0
+ VLLM_VERSION=0.19.1

- FLASHINFER_VERSION=0.6.5
+ FLASHINFER_VERSION=0.6.6

- TRANSFORMERS_VERSION=5.3.0
+ TRANSFORMERS_VERSION=5.5.3
  # 5.5.3 (not 5.5.1 floor) to match scitrera's sglang-0.5.10 recipe —
  # known-good in scitrera's CI matrix on the same dependency graph.

- IMAGE_TAG=scitrera/dgx-spark-vllm:0.17.0-t5
+ IMAGE_TAG=local/dgx-spark-vllm:0.19.1-t5-dev
  # `local/` namespace so it can never shadow upstream scitrera image.
```

Everything else (DEV_BASE_IMAGE, RUN_BASE_IMAGE, TRITON_VERSION) stays
identical. **Phase 1's prediction held: this is a recipe-only bump,
no Dockerfile fork.**

### NVFP4 model selection for Phase 5 bench

Two candidates, both vLLM ≥0.19 + Blackwell SM 120:

| Model                                            | Quant format         | MTP support                | Expected decode speedup |
|--------------------------------------------------|----------------------|----------------------------|--------------------------|
| `sakamakismile/Qwen3.6-27B-NVFP4`                | `compressed-tensors` | ❌ ("no MTP head")          | NVFP4 alone (~25–30 t/s estimate, vs 12.9 t/s INT4-alone in our prior bench → ~2x) |
| `sakamakismile/Qwen3.6-27B-Text-NVFP4-MTP`       | `modelopt` (NVIDIA native fast path) | ✅ via `qwen3_5_mtp` method, num_speculative_tokens=3, ~1.9× decode multiplier per model card | NVFP4 + MTP — **this is the production candidate** |

**Phase 5 plan adjustment:** bench BOTH. The non-MTP variant proves the
engine works (NVFP4 path is healthy). The MTP variant is the one we
actually ship if green — it's the apples-to-apples comparison vs our
current INT4+MTP=2 = 20 t/s baseline.

Notable serve-command differences vs current INT4+MTP prod:

```
  --speculative-config '{"method":"qwen3_next_mtp", ...}'  # current INT4
  --speculative-config '{"method":"qwen3_5_mtp", ...}'     # NVFP4-MTP variant

  --tool-call-parser=qwen3_coder    # current — keep
  --quantization=modelopt           # NEW — required for the modelopt-format MTP variant
                                    # (auto-detected for compressed-tensors variant)
  --max-num-seqs=4                  # current — DROP TO 2 for NVFP4-MTP per model card
                                    # (silent OOM risk above 2)
```

`--max-num-seqs=2` ceiling for the MTP-NVFP4 variant is a noteworthy
production trade-off — single-user interactive is fine (we're already at
4 max), but it caps concurrent OpenClaw orchestration if that ever
matters.

### Outstanding risks (newly identified in Phase 2)

- **`nvidia-cudnn-frontend<1.19.0` cap.** The scitrera 0.17 image
  installs `nvidia-cudnn-frontend` without an upper bound; if the
  installed version drifts to >=1.19.0, vLLM 0.19.1 will fail at import.
  Phase 4 pre-build check: `docker run --rm
  scitrera/dgx-spark-pytorch-dev:2.10.0-v2-cu131 pip show
  nvidia-cudnn-frontend | grep Version`.
- **MTP method name change** (`qwen3_5_mtp` vs `qwen3_next_mtp`) —
  pure config, but the docker-compose command line in our prod must
  flip in lockstep with the model swap. No engine-side risk.
- **`compressed-tensors` package dependency** — vLLM 0.19+ uses
  `compressed-tensors` for the non-MTP NVFP4 model. Likely already
  pulled by vLLM's own deps but worth checking that the install
  succeeds on first build.

### Phase 3 specifics now nailed down

The Phase 3 recipe file content is essentially fixed:

```
DOCKERFILE=Dockerfile.llm_inference
TARGET=vllm_runtime

DEV_BASE_IMAGE=scitrera/dgx-spark-pytorch-dev:2.10.0-v2-cu131
RUN_BASE_IMAGE=scitrera/dgx-spark-pytorch-runtime:2.10.0-v2-cu131

FLASHINFER_VERSION=0.6.6
TRITON_VERSION=3.6.0

TRANSFORMERS_VERSION=5.5.3

VLLM_VERSION=0.19.1

IMAGE_TAG=local/dgx-spark-vllm:0.19.1-t5-dev
```

## What still needs to be confirmed (Phase 4 pre-flight, not Phase 2)

- Whether the published `scitrera/dgx-spark-pytorch-{dev,runtime}:
  2.10.0-v2-cu131` images are reachable on Docker Hub from this host
  (cheap to test in Phase 4 pre-flight: `docker pull ...`).
- `nvidia-cudnn-frontend` actual version in the dev base image (see
  outstanding risks above).
- Whether `compressed-tensors` and any NVFP4-specific Python deps
  install cleanly on first build cycle.

## Resume notes (for the next session picking this up)

- The clone is at `dgx-spark-vllm/upstream/` (gitignored). Recipes are
  in `upstream/container-recipes/`, archive in `archive/`, the build
  script is `upstream/container-build/build-image.sh`, the parametric
  Dockerfile is `upstream/container-build/Dockerfile.llm_inference`.
- `git -C dgx-spark-vllm/upstream log` is fully unshallowed.
- This file is the working document — Phase 2 should append (not
  rewrite) into the "What still needs to be confirmed" section.
- Production vLLM was untouched in Phase 1.
