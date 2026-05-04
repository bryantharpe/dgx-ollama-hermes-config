#!/usr/bin/env bash
# gbrain container entrypoint.
#
# Idempotent first-run bootstrap:
#   1. If /home/admin/.gbrain has no .git, clone the brain-data repo into it.
#      (Empty bind mount on first up; populated mount on subsequent boots.)
#   2. Install the post-commit auto-push hook (overwrites any existing one —
#      the desired behavior is "always background-push to origin/HEAD").
#   3. Configure git user identity inside the container.
#   4. Hand off to `gbrain jobs supervisor` as PID 1 (under tini).
#
# Long-running command is the supervisor — it owns crons + Minions queue.
# stdio MCP is invoked by Claude Code via `docker exec -i gbrain gbrain serve`
# in a separate process; the supervisor doesn't manage MCP sessions.

set -euo pipefail

BRAIN_DIR="${BRAIN_DIR:-/home/admin/.gbrain}"
BRAIN_REMOTE="${BRAIN_REMOTE:-git@github.com:bryantharpe/gbrain-data.git}"
GIT_USER_NAME="${GIT_USER_NAME:-Bryan Tharpe (gbrain)}"
GIT_USER_EMAIL="${GIT_USER_EMAIL:-bryan.tharpe@gmail.com}"

log() { printf '[gbrain-entrypoint] %s\n' "$*" >&2; }

# Re-mount-friendly: the deploy SSH key is mounted read-only at a fixed path.
# Tighten perms via the GIT_SSH_COMMAND env so we don't have to chmod the RO
# mount (which would fail).
KEY_PATH="${KEY_PATH:-/home/admin/.ssh/gbrain_data_deploy_ed25519}"
if [[ -r "$KEY_PATH" ]]; then
  export GIT_SSH_COMMAND="ssh -i $KEY_PATH -o IdentitiesOnly=yes -o UserKnownHostsFile=/home/admin/.ssh/known_hosts -o StrictHostKeyChecking=yes"
  log "deploy key found at $KEY_PATH"
else
  log "WARN: no deploy key at $KEY_PATH — pushes will fail; clone may also fail on first run"
fi

# 1. Brain repo init.
if [[ ! -d "$BRAIN_DIR/.git" ]]; then
  log "no .git in $BRAIN_DIR — cloning $BRAIN_REMOTE"
  # Clone into a temp dir then move contents, since BRAIN_DIR is the bind
  # mount itself and may already contain a stray dotfile from the host.
  if [[ -z "$(ls -A "$BRAIN_DIR" 2>/dev/null || true)" ]]; then
    git clone "$BRAIN_REMOTE" "$BRAIN_DIR"
  else
    log "$BRAIN_DIR not empty — running git init + remote add instead of clone"
    cd "$BRAIN_DIR"
    git init -q
    git remote add origin "$BRAIN_REMOTE" || true
    git fetch origin || log "WARN: fetch failed; brain stays local-only until network/key fixed"
  fi
fi

cd "$BRAIN_DIR"
git config user.name  "$GIT_USER_NAME"
git config user.email "$GIT_USER_EMAIL"

# 2. Post-commit auto-push hook. Backgrounded so commits never block on the
# network. Errors land in /home/admin/.gbrain/.git/post-commit-push.log.
HOOK="$BRAIN_DIR/.git/hooks/post-commit"
# Hook embeds KEY_PATH directly (expanded at write time, not at commit time)
# because `git commit` from a `docker exec` shell does NOT inherit the
# entrypoint's GIT_SSH_COMMAND. The hook must set it itself.
cat > "$HOOK" <<HOOKEOF
#!/usr/bin/env bash
# gbrain auto-push: backgrounded \`git push origin HEAD\` after every commit.
# Failures are logged but never block. Re-run by hand with:
#   GIT_SSH_COMMAND="ssh -i $KEY_PATH -o IdentitiesOnly=yes" \\
#     git -C $BRAIN_DIR push origin HEAD
export GIT_SSH_COMMAND="ssh -i $KEY_PATH -o IdentitiesOnly=yes -o UserKnownHostsFile=/home/admin/.ssh/known_hosts -o StrictHostKeyChecking=yes"
LOG="\$(git rev-parse --git-dir)/post-commit-push.log"
{
  echo "----- \$(date -Is) commit \$(git rev-parse --short HEAD) -----"
  git push origin HEAD 2>&1
} >> "\$LOG" 2>&1 &
disown || true
HOOKEOF
chmod +x "$HOOK"
log "post-commit auto-push hook installed at $HOOK"

# 3. Sanity: print git config + last commit so first-boot logs are useful.
log "git config: user=$(git config user.name) <$(git config user.email)>"
log "git remote: $(git remote get-url origin 2>/dev/null || echo 'NONE')"
log "last commit: $(git log -1 --format='%h %s' 2>/dev/null || echo 'EMPTY (new brain)')"

# 4. Initialize the brain. Idempotent via config.json check.
# - If GBRAIN_DATABASE_URL is set: Postgres mode (full feature set, supervisor
#   runs the dream cycle + Minions queue + cron skills).
# - If unset: PGLite mode (single-process, on-demand only).
if [[ ! -f "$BRAIN_DIR/config.json" ]]; then
  if [[ -n "${GBRAIN_DATABASE_URL:-}" ]]; then
    log "no config.json — initializing Postgres-backed brain"
    # `gbrain init --url ...` accepts a libpq URL and writes it to config.json.
    gbrain init --url "$GBRAIN_DATABASE_URL" </dev/null 2>&1 | sed 's/^/[gbrain init] /' >&2 || {
      log "ERROR: gbrain init failed; check logs above"
      exit 1
    }
  else
    log "no config.json — initializing PGLite-backed brain (no GBRAIN_DATABASE_URL set)"
    gbrain init </dev/null 2>&1 | sed 's/^/[gbrain init] /' >&2 || {
      log "ERROR: gbrain init failed; check logs above"
      exit 1
    }
  fi
  log "gbrain init complete"
fi

# 5. .gitignore: exclude the PGLite database (binary, derived from markdown +
# regenerable). Idempotent — only writes if missing. Markdown pages stay
# tracked; everything else listed here is ephemeral or sensitive.
GITIGNORE="$BRAIN_DIR/.gitignore"
if [[ ! -f "$GITIGNORE" ]]; then
  log "writing $GITIGNORE"
  cat > "$GITIGNORE" <<'GIEOF'
# PGLite database — derived from markdown pages, regenerable via `gbrain doctor`.
brain.pglite/
# Background-job scratch + supervisor audit logs.
audit/
*.log
.cache/
# Bun + node leftovers if any tooling drops them here.
node_modules/
GIEOF
fi

# 6. First-time commit: if HEAD doesn't exist, stage tracked files and make
# an initial commit. Auto-push hook will then push to origin.
if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
  log "no commits yet — making initial commit"
  git add .gitignore config.json 2>/dev/null || true
  git commit -m "gbrain: initial brain ($(date -Is))" || {
    log "WARN: initial commit failed (likely nothing to commit yet); continuing"
  }
fi

# 7. Long-running command.
#
# Postgres mode: `gbrain jobs supervisor` is the canonical worker (Minions
# queue, dream cycle, cron skills, durable agent runs). PGLite mode: the
# supervisor would crash on the file-lock conflict, so we fall back to
# `sleep infinity` — the container only serves on-demand `gbrain serve` (MCP)
# and `gbrain query`/`gbrain import` via `docker exec`.
if [[ -n "${GBRAIN_DATABASE_URL:-}" ]]; then
  log "Postgres mode — starting \`gbrain jobs supervisor\`"
  exec gbrain jobs supervisor --concurrency 4
else
  log "PGLite mode — skipping supervisor; keeping container alive for MCP + on-demand exec"
  exec sleep infinity
fi
