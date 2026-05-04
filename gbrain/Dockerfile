# gbrain (https://github.com/garrytan/gbrain) — agent-operated personal brain.
#
# Pinned to v0.25.1 (commit c2ae4dbfc58d, 2026-05-02). v0.26+ added the OAuth
# 2.1 HTTP MCP server which we deliberately do NOT use (stdio-only deployment),
# so v0.25.1 keeps the attack surface smaller. Bump deliberately when new
# skills land.
#
# Multi-arch: oven/bun:1 ships amd64 + arm64 layers; works on the DGX Spark
# (aarch64 + Blackwell). No CUDA needed in this image — embeddings/inference
# are HTTP calls to ollama / vllm / cerebras over the bridge network.

FROM oven/bun:1

ARG GBRAIN_SHA=c2ae4dbfc58d
ARG GBRAIN_REPO=https://github.com/garrytan/gbrain.git

# git for clone + post-commit pushes; openssh-client for git@github.com:...;
# tini for clean signal handling under `gbrain jobs supervisor`.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        git ca-certificates openssh-client tini \
 && rm -rf /var/lib/apt/lists/*

# oven/bun:1 already ships a `bun` user at uid=1000 gid=1000 with home
# /home/bun. Rename it to `admin` and move its home to /home/admin so the
# in-container path matches the host bind-mount target. UID/GID stay 1000:1000.
RUN usermod  -l admin -d /home/admin -m bun \
 && groupmod -n admin bun

# Clone gbrain at the pinned SHA. Cloning runs as root (needs apt-installed
# git binaries), then we chown to admin so `bun install` runs unprivileged.
RUN git clone "${GBRAIN_REPO}" /opt/gbrain \
 && cd /opt/gbrain \
 && git checkout "${GBRAIN_SHA}" \
 && chown -R admin:admin /opt/gbrain

# ── Local-providers patch ────────────────────────────────────────────────
# Upstream gbrain hardcodes `new OpenAI()` (no baseURL) + the model name
# `text-embedding-3-large` + `vector(1536)` in the schema. For a fully-local
# deploy with ollama's nomic-embed-text (768 dims), several files need
# surgical edits. Each sed is bounded by literal string-match anchors so a
# future SHA bump that touches an unrelated line still applies cleanly
# (or fails loudly via the grep verifications at the end).
#
# Files patched:
#   embedding.ts             — model, dim, OpenAI client baseURL → env
#   pglite-schema.ts         — vector(1536)→vector(N), seed values
#   schema-embedded.ts       — same; auto-generated from schema.sql,
#                              loaded at runtime by both PGLite + Postgres
#   schema.sql               — canonical source (kept in sync defensively)
#   postgres-engine.ts       — defensive: fallback model string in INSERT
#   pglite-engine.ts         — defensive: same
#
# Reverting to upstream defaults: drop this RUN block + leave
# GBRAIN_EMBEDDING_* env vars unset in compose.
ARG GBRAIN_EMBED_DIM=768
ARG GBRAIN_EMBED_MODEL=nomic-embed-text
# Note: sed delimiter is `@` (not `|`) so the JS `||` operator in the
# replacement strings doesn't confuse the parser.
RUN cd /opt/gbrain \
 && sed -i \
      -e "s@^const MODEL = 'text-embedding-3-large';@const MODEL = process.env.GBRAIN_EMBEDDING_MODEL || 'text-embedding-3-large';@" \
      -e "s@^const DIMENSIONS = 1536;@const DIMENSIONS = parseInt(process.env.GBRAIN_EMBEDDING_DIMENSIONS || '1536', 10);@" \
      -e "s@client = new OpenAI();@client = new OpenAI({ baseURL: process.env.GBRAIN_EMBEDDING_BASE_URL, apiKey: process.env.OPENAI_API_KEY || 'none' });@" \
      src/core/embedding.ts \
 && sed -i \
      -e "s@vector(1536)@vector(${GBRAIN_EMBED_DIM})@g" \
      -e "s@('embedding_model', 'text-embedding-3-large')@('embedding_model', '${GBRAIN_EMBED_MODEL}')@" \
      -e "s@('embedding_dimensions', '1536')@('embedding_dimensions', '${GBRAIN_EMBED_DIM}')@" \
      src/core/pglite-schema.ts src/core/schema-embedded.ts src/schema.sql \
 && sed -i \
      -e "s@chunk.model || 'text-embedding-3-large'@chunk.model || (process.env.GBRAIN_EMBEDDING_MODEL || 'text-embedding-3-large')@g" \
      src/core/postgres-engine.ts src/core/pglite-engine.ts \
 && grep -q "process.env.GBRAIN_EMBEDDING_MODEL" src/core/embedding.ts \
 && grep -q "vector(${GBRAIN_EMBED_DIM})" src/core/pglite-schema.ts \
 && grep -q "vector(${GBRAIN_EMBED_DIM})" src/schema.sql \
 && grep -q "vector(${GBRAIN_EMBED_DIM})" src/core/schema-embedded.ts \
 || (echo "FATAL: local-providers patch failed to apply" && exit 1)

USER admin
RUN cd /opt/gbrain && bun install --frozen-lockfile
USER root

# Skip `bun link` — it tries to write to /usr/local/bin during the RUN step
# and produces fragile global state. Drop a thin wrapper instead. The wrapper
# lets `gbrain <args>` resolve to bun running the pinned entrypoint, and
# survives bind-mount weirdness because nothing depends on a global symlink
# pointing into /home/admin/.bun.
RUN printf '#!/bin/sh\nexec /usr/local/bin/bun /opt/gbrain/src/cli.ts "$@"\n' \
        > /usr/local/bin/gbrain \
 && chmod 755 /usr/local/bin/gbrain

# Pre-trust github.com for SSH pushes. Using known_hosts (not StrictHostKeyChecking=no)
# so a MITM'd push fails loudly instead of silently writing to a bad key.
RUN install -d -o admin -g admin -m 700 /home/admin/.ssh \
 && ssh-keyscan -t ed25519,rsa github.com > /home/admin/.ssh/known_hosts \
 && chown admin:admin /home/admin/.ssh/known_hosts \
 && chmod 644 /home/admin/.ssh/known_hosts

COPY --chmod=755 entrypoint.sh /usr/local/bin/gbrain-entrypoint

USER admin
WORKDIR /home/admin

# tini reaps zombies + forwards SIGTERM cleanly to the supervisor.
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/gbrain-entrypoint"]
