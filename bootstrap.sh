#!/bin/bash
set -e

ORCHESTRATOR_TAG="qwen3.6-35b:128k"

# (tag, modelfile) pairs
MODELS=(
  "hermes4-70b:131k Modelfile.hermes4-70b-131k"
  "qwen3.6-35b-a3b:q6-65k Modelfile.qwen3.6-35b-a3b-q6-65k"
)

echo "🚀 Starting Hermes services..."
docker compose up -d

echo "⌛ Waiting for Ollama to be ready..."
until docker exec ollama ollama list >/dev/null 2>&1; do
  sleep 2
done

for pair in "${MODELS[@]}"; do
  TAG="${pair%% *}"
  MF="${pair#* }"
  if ! docker exec ollama ollama list | grep -q "$TAG"; then
    echo "📥 Registering $TAG from $MF..."
    docker cp "$MF" "ollama:/tmp/$MF"
    docker exec ollama ollama create "$TAG" -f "/tmp/$MF"
    echo "✅ $TAG created."
  else
    echo "✅ $TAG already exists."
  fi
done

# Point runtime config.yaml at the new orchestrator. ~/.hermes is owned
# by root inside the hermes-agent container (mode 700), so the sed runs
# via `docker exec` rather than host-side.
echo "⌛ Waiting for hermes-agent config.yaml..."
until docker exec hermes-agent test -f /opt/data/config.yaml 2>/dev/null; do
  sleep 2
done
if ! docker exec hermes-agent grep -q "default: \"$ORCHESTRATOR_TAG\"" /opt/data/config.yaml; then
  echo "🔧 Updating ~/.hermes/config.yaml model.default → $ORCHESTRATOR_TAG"
  docker exec hermes-agent sed -i "s|default: \"[^\"]*\"|default: \"$ORCHESTRATOR_TAG\"|" /opt/data/config.yaml
  docker restart hermes-agent >/dev/null
fi

echo "✨ Hermes is ready to go!"
