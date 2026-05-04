#!/usr/bin/env bash
# Source this file to load B2 + restic credentials from .env.backup.
# Usage: . scripts/backup-env.sh
# Idempotent — safe to source multiple times.

__here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
__repo_root=$(dirname "$__here")
__envfile="$__repo_root/.env.backup"

if [[ ! -r "$__envfile" ]]; then
  echo "fatal: $__envfile not readable" >&2
  return 1 2>/dev/null || exit 1
fi

set -a
# shellcheck disable=SC1090
. "$__envfile"
set +a

for __v in B2_ACCOUNT_ID B2_ACCOUNT_KEY B2_BUCKET RESTIC_REPOSITORY RESTIC_PASSWORD; do
  if [[ -z "${!__v:-}" ]]; then
    echo "fatal: $__v is not set in $__envfile" >&2
    return 1 2>/dev/null || exit 1
  fi
done

unset __here __repo_root __envfile __v
