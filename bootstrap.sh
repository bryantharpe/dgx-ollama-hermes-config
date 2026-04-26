#!/bin/bash
set -e

# vLLM serves Qwen3.6-35B-A3B-FP8 multi-aliased to all the model names existing
# clients send. ORCHESTRATOR_TAG is the canonical name written into
# hermes-agent's config.yaml on first boot.
ORCHESTRATOR_TAG="qwen3.6-35b:128k"

echo "🚀 Starting Hermes services..."
docker compose up -d

echo "⌛ Waiting for vLLM to finish loading Qwen3.6-35B-A3B-FP8..."
echo "   (first run downloads ~37 GB and compiles CUDA graphs — expect 8–15 min)"
until curl -fsS http://127.0.0.1:8001/health >/dev/null 2>&1; do
  sleep 5
done
echo "✅ vLLM is healthy."

echo "⌛ Waiting for hermes-agent config.yaml..."
until docker exec hermes-agent test -f /opt/data/config.yaml 2>/dev/null; do
  sleep 2
done
CFG_NEEDS_RESTART=0
if ! docker exec hermes-agent grep -q "default: \"$ORCHESTRATOR_TAG\"" /opt/data/config.yaml; then
  echo "🔧 Updating ~/.hermes/config.yaml model.default → $ORCHESTRATOR_TAG"
  docker exec hermes-agent sed -i "s|default: \"[^\"]*\"|default: \"$ORCHESTRATOR_TAG\"|" /opt/data/config.yaml
  CFG_NEEDS_RESTART=1
fi
# `model.providers.custom.base_url` is loaded from the on-disk config and
# overrides the OPENAI_API_BASE_URL env var. Pin it to the vLLM service so
# upgrading from a pre-vLLM config doesn't leave a stale ollama URL behind.
if docker exec hermes-agent grep -qE 'base_url: *"(http://ollama:11434/v1|http://localhost:11434/v1)"' /opt/data/config.yaml; then
  echo "🔧 Updating ~/.hermes/config.yaml base_url → http://vllm:8000/v1"
  docker exec hermes-agent sed -i \
    -e 's|http://ollama:11434/v1|http://vllm:8000/v1|g' \
    -e 's|http://localhost:11434/v1|http://vllm:8000/v1|g' \
    /opt/data/config.yaml
  CFG_NEEDS_RESTART=1
fi
if [ "$CFG_NEEDS_RESTART" = "1" ]; then
  docker restart hermes-agent >/dev/null
fi

echo "✨ Hermes is ready to go!"
