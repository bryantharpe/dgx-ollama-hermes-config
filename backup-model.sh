#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_BASE="$REPO_DIR/backups"
RUNTIME_CONFIG="$HOME/.hermes/config.yaml"
COMPOSE_DIR="$REPO_DIR"

FILES_TO_BACKUP=(
  "$REPO_DIR/HermesModelfile"
  "$REPO_DIR/docker-compose.yml"
  "$REPO_DIR/bootstrap.sh"
  "$REPO_DIR/test_api.sh"
  "$RUNTIME_CONFIG"
)

latest_backup() {
  ls -1td "$BACKUP_BASE"/model-swap-* 2>/dev/null | head -1
}

cmd_backup() {
  local ts
  ts=$(date +%Y%m%d-%H%M%S)
  local dest="$BACKUP_BASE/model-swap-$ts"
  mkdir -p "$dest"

  for f in "${FILES_TO_BACKUP[@]}"; do
    if [ -f "$f" ]; then
      cp "$f" "$dest/$(basename "$f")"
      echo "  backed up $(basename "$f")"
    else
      echo "  skipped $(basename "$f") (not found)"
    fi
  done

  docker exec ollama ollama list > "$dest/ollama-models.txt" 2>/dev/null || true
  echo "Backup saved to $dest"
}

cmd_restore() {
  local src
  src=$(latest_backup)
  if [ -z "$src" ]; then
    echo "No backup found in $BACKUP_BASE" >&2
    exit 1
  fi
  echo "Restoring from $src ..."

  for f in HermesModelfile docker-compose.yml bootstrap.sh test_api.sh; do
    if [ -f "$src/$f" ]; then
      cp "$src/$f" "$REPO_DIR/$f"
      echo "  restored $f"
    fi
  done

  if [ -f "$src/config.yaml" ]; then
    cp "$src/config.yaml" "$RUNTIME_CONFIG"
    echo "  restored ~/.hermes/config.yaml"
  fi

  echo "Restarting hermes-agent..."
  cd "$COMPOSE_DIR" && docker compose restart hermes-agent
  echo "Restore complete."
}

cmd_rollback_model() {
  local src
  src=$(latest_backup)
  if [ -z "$src" ] || [ ! -f "$src/ollama-models.txt" ]; then
    echo "No backup with model list found" >&2
    exit 1
  fi

  local old_model
  old_model=$(grep -oP '\S*qwen3-next\S*' "$src/ollama-models.txt" | head -1)
  if [ -z "$old_model" ]; then
    echo "Could not detect previous model name from backup" >&2
    exit 1
  fi

  echo "Unloading current model and reloading $old_model ..."
  curl -sf http://localhost:11434/api/generate \
    -d "{\"model\":\"qwen3.6-35b:128k\",\"keep_alive\":0}" > /dev/null 2>&1 || true

  curl -sf http://localhost:11434/api/generate \
    -d "{\"model\":\"$old_model\",\"prompt\":\"\",\"keep_alive\":-1}" > /dev/null 2>&1

  echo "Model $old_model reloaded in VRAM."
  echo "Run './backup-model.sh restore' to also revert config files."
}

case "${1:-}" in
  backup)         cmd_backup ;;
  restore)        cmd_restore ;;
  rollback-model) cmd_rollback_model ;;
  *)
    echo "Usage: $0 {backup|restore|rollback-model}"
    echo ""
    echo "  backup          Snapshot config files before a model swap"
    echo "  restore         Restore config files from latest backup + restart hermes-agent"
    echo "  rollback-model  Unload new model, reload old model in Ollama VRAM"
    exit 1
    ;;
esac
