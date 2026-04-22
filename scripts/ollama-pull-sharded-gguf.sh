#!/usr/bin/env bash
# Pull a multi-part (sharded) GGUF from HuggingFace, merge it locally with
# llama-gguf-split, and register the merged result as an Ollama tag.
#
# Ollama (as of 0.x) doesn't support sharded GGUFs directly — this works
# around that by doing a one-time download + merge. After registration the
# source shards and merged temp file can be deleted; the blob lives in
# Ollama's store.
#
# Usage:
#   ollama-pull-sharded-gguf.sh <hf-repo> <folder> <shard-basename> <num-shards> <ollama-tag> <modelfile>
#
# Example:
#   ollama-pull-sharded-gguf.sh \
#     bartowski/Qwen_Qwen3-Coder-Next-GGUF \
#     Qwen_Qwen3-Coder-Next-Q5_K_M \
#     Qwen_Qwen3-Coder-Next-Q5_K_M \
#     2 \
#     qwen3-coder-next:q5-131k \
#     /home/admin/code/hermes-config/Modelfile.qwen3-coder-next-q5-131k
#
# The Modelfile passed in must use `FROM /tmp/merged.gguf` — this script
# copies the merged blob into the ollama container at that path, runs
# `ollama create`, and cleans up.

set -euo pipefail

HF_REPO="${1:?hf-repo (e.g. bartowski/Qwen_Qwen3-Coder-Next-GGUF) required}"
HF_FOLDER="${2:?folder (e.g. Qwen_Qwen3-Coder-Next-Q5_K_M) required}"
SHARD_BASENAME="${3:?shard basename (e.g. Qwen_Qwen3-Coder-Next-Q5_K_M) required}"
NUM_SHARDS="${4:?num shards (e.g. 2) required}"
OLLAMA_TAG="${5:?ollama tag (e.g. qwen3-coder-next:q5-131k) required}"
MODELFILE="${6:?path to Modelfile required; FROM must be /tmp/merged.gguf}"

STAGING="${STAGING_DIR:-/home/admin/gguf-staging/${SHARD_BASENAME}}"
LLAMA_IMAGE="${LLAMA_IMAGE:-ghcr.io/ggml-org/llama.cpp:full}"

mkdir -p "$STAGING"
cd "$STAGING"

printf 'Downloading %d shards from https://huggingface.co/%s/resolve/main/%s/\n' \
  "$NUM_SHARDS" "$HF_REPO" "$HF_FOLDER"

# Download all shards in parallel
pids=()
for i in $(seq 1 "$NUM_SHARDS"); do
  pad=$(printf '%05d' "$i")
  total=$(printf '%05d' "$NUM_SHARDS")
  fname="${SHARD_BASENAME}-${pad}-of-${total}.gguf"
  url="https://huggingface.co/${HF_REPO}/resolve/main/${HF_FOLDER}/${fname}"
  if [[ -f "$fname" && -s "$fname" ]]; then
    printf '  %s already present (%s)\n' "$fname" "$(du -h "$fname" | cut -f1)"
    continue
  fi
  ( curl -L -C - -o "$fname" "$url" >/dev/null 2>&1 && echo "  downloaded: $fname" ) &
  pids+=($!)
done
for pid in "${pids[@]}"; do wait "$pid"; done

# Merge via a transient llama.cpp container
MERGED="${STAGING}/merged.gguf"
printf 'Merging %d shards -> %s\n' "$NUM_SHARDS" "$MERGED"
docker run --rm \
  --entrypoint /app/llama-gguf-split \
  -v "$STAGING":/stage \
  "$LLAMA_IMAGE" \
  --merge "/stage/${SHARD_BASENAME}-00001-of-$(printf '%05d' "$NUM_SHARDS").gguf" \
  "/stage/merged.gguf"

# Copy into ollama container and register
printf 'Copying merged blob into ollama container (%s GiB)\n' "$(du --block-size=G "$MERGED" | cut -f1)"
docker cp "$MERGED" ollama:/tmp/merged.gguf
docker cp "$MODELFILE" ollama:/tmp/Modelfile.pull
docker exec ollama ollama create "$OLLAMA_TAG" -f /tmp/Modelfile.pull
docker exec ollama rm -f /tmp/merged.gguf /tmp/Modelfile.pull

# Clean up host staging
printf 'Cleaning up host staging at %s\n' "$STAGING"
rm -rf "$STAGING"

printf '\nDone. Verify with: docker exec ollama ollama show %s\n' "$OLLAMA_TAG"
