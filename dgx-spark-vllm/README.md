# dgx-spark-vllm — local vLLM 0.19+ build for NVFP4 on DGX Spark

In-house container build that adapts **scitrera/cuda-containers** forward
to vLLM 0.19.1 so we can serve NVFP4-quantized models on the DGX Spark
GB10 (ARM64 + Blackwell SM_120). Production `vllm` service in
`../docker-compose.yml` continues to run scitrera's published
`scitrera/dgx-spark-vllm:0.17.0-t5` image — this directory is
side-by-side R&D, not yet wired into the running stack.

For the full upgrade plan, pin matrix, rationale, and rollback shape see:

- **Plan:** `~/.claude/plans/proud-noodling-allen.md`
- **Notes:** `RECIPE-NOTES.md` (Phase 1+2 findings, decision log)

## Layout

```
dgx-spark-vllm/
├── README.md                       this file
├── RECIPE-NOTES.md                 pin matrix + decision log
├── build.sh                        thin wrapper around upstream's build-image.sh
├── recipes/
│   └── vllm-0.19.1-t5.recipe       4-line delta from scitrera's 0.17.0-t5
├── upstream/                       gitignored — clone of scitrera/cuda-containers
├── backups/                        gitignored — git bundle snapshot of upstream
└── build-logs/                     gitignored — per-build logs from build.sh
```

## Why we don't fork the Dockerfile

scitrera's `Dockerfile.llm_inference` is fully recipe-driven via
`--build-arg`. The historical bump pattern (Phase 1 finding) is that
minor vLLM version bumps change one ARG; major base-image bumps change
five. vLLM 0.17 → 0.19.1 is a *minor* bump on this scale (4 ARGs total,
no PyTorch/CUDA change), so we ride upstream's Dockerfile unchanged via
the recipe pipeline. If upstream's Dockerfile changes break us, we
diff and decide whether to fork at that moment.

## Bootstrap (fresh clone of hermes-config)

```bash
cd dgx-spark-vllm
# Option A — clone scitrera fresh (network):
git clone --depth 50 https://github.com/scitrera/cuda-containers.git upstream

# Option B — restore from the bundled snapshot (offline, deterministic):
git clone backups/upstream-cuda-containers-*.bundle upstream
```

Both produce an `upstream/` tree with `container-build/build-image.sh`
and `container-recipes/`. The bundle is pinned at SHA `6120269` (the
HEAD when this directory was authored on 2026-05-02).

## Build

```bash
./build.sh                  # build vllm-0.19.1-t5 (default recipe)
./build.sh --dry-run        # show config + invocation, build nothing
./build.sh --no-cache       # forwarded to docker buildx
./build.sh some-other-name  # build recipes/some-other-name.recipe
```

Output image: `local/dgx-spark-vllm:0.19.1-t5-dev` (per recipe IMAGE_TAG).
The `local/` namespace is intentional — it cannot be confused with or
shadow the upstream `scitrera/dgx-spark-vllm:0.17.0-t5` that production
still uses.

`build.sh` runs three pre-flight checks before invoking upstream:

1. `upstream/container-build/build-image.sh` exists and is executable.
2. `>= 60 GB` free in the docker root dir.
3. `DEV_BASE_IMAGE` from the recipe is reachable on Docker Hub
   (`docker manifest inspect`).

Build logs land in `build-logs/<recipe>-<timestampZ>.log`. Expect
FlashInfer source-build to dominate wall clock (~20–40 min on first
build, faster on rebuilds when the buildx cache is warm).

## Verify a built image

```bash
docker run --rm local/dgx-spark-vllm:0.19.1-t5-dev vllm --version
# expected: 0.19.1
```

## Cleanup / rollback

The build artifacts in `local/` namespace cannot affect production. To
fully reset:

```bash
docker image rm local/dgx-spark-vllm:0.19.1-t5-dev
docker builder prune -f          # reclaim build cache
rm -rf build-logs/ upstream/     # both gitignored, safe to delete
# backups/ contains the offline bundle — keep unless you're certain
```

Production `vllm` (port 8001) is on `scitrera/dgx-spark-vllm:0.17.0-t5`
and is **not affected** by anything done in this directory until Phase 6
of the plan explicitly edits the parent `docker-compose.yml`.

## Recipe pin rationale (one-line summary)

| Field                | Value                                           |
|----------------------|-------------------------------------------------|
| vLLM                 | 0.19.1 — first stable with NVFP4 + DGX Spark fixes (release notes #38126, #37725); avoids 0.20.0's PyTorch 2.11 jump |
| Base image           | `scitrera/dgx-spark-pytorch-{dev,runtime}:2.10.0-v2-cu131` — same as scitrera prod 0.17.0-t5 |
| FlashInfer           | 0.6.6 — vLLM 0.19.1 `cuda.txt` pin              |
| Triton               | 3.6.0 — unchanged from scitrera 0.17.0-t5       |
| Transformers         | 5.5.3 — vLLM 0.19.1 excludes 5.0–5.5.0; 5.5.3 matches scitrera's known-good sglang-0.5.10 |
| PyTorch / CUDA       | 2.10.0 / 13.1.1 — inherited from base image     |

Full delta-vs-0.17 reasoning in `RECIPE-NOTES.md` § "Recipe diff vs 0.17.0-t5".

## Upstream provenance

- Repo: github.com/scitrera/cuda-containers
- Pinned commit: `6120269b465756c4705c36b8be04985ab12875d7` (2026-05-02)
- Bundle: `backups/upstream-cuda-containers-6120269.bundle` (~100 KB,
  full history, gitignored)
- License: see `upstream/LICENSE` after cloning. Our recipe builds on
  top of scitrera's pipeline — we do not redistribute their files.
