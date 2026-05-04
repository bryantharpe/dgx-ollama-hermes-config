#!/usr/bin/env bash
# Install + enable the hermes-backup systemd units.
#
# Copies systemd/*.service and *.timer to /etc/systemd/system/, runs
# daemon-reload, and enables --now the three timers (daily/weekly/monthly).
#
# Why the docker chroot dance? `systemctl daemon-reload` and `systemctl
# enable` need to talk to PID 1's DBUS socket — that requires CAP_SYS_ADMIN
# (effectively root). We don't have a sudoers entry for systemctl, but admin
# IS in the docker group, so a privileged container chrooted into the host
# can run systemctl as if from the host. One-time install, scoped exactly
# to the three units defined in this repo.
#
# Usage: scripts/install-backup-timers.sh

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(dirname "$HERE")
UNITS_SRC="$REPO_ROOT/systemd"

if ! ls "$UNITS_SRC"/hermes-backup*.service >/dev/null 2>&1; then
  echo "fatal: no unit files in $UNITS_SRC" >&2
  exit 1
fi

echo "[1/3] copying unit files to /etc/systemd/system/"
docker run --rm \
  -v "$UNITS_SRC:/src:ro" \
  -v /etc/systemd/system:/dest \
  alpine sh -c '
    for u in /src/hermes-backup*.service /src/hermes-backup*.timer; do
      install -m 0644 -o root -g root "$u" /dest/
      echo "  installed $(basename "$u")"
    done
  '

echo "[2/3] systemctl daemon-reload (via privileged chroot)"
docker run --rm --privileged --pid=host -v /:/host alpine \
  chroot /host /usr/bin/systemctl daemon-reload

echo "[3/3] enabling timers"
docker run --rm --privileged --pid=host -v /:/host alpine \
  chroot /host /usr/bin/systemctl enable --now \
    hermes-backup.timer hermes-backup-check.timer hermes-backup-prune.timer

echo
echo "active timers:"
systemctl list-timers 'hermes-backup*' --no-pager
