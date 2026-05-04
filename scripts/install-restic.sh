#!/usr/bin/env bash
# Install restic to /usr/local/bin/restic on this host.
#
# Why a docker container? /usr/local/bin is root-owned and our sudoers entry
# (/etc/sudoers.d/restic-backup) only grants NOPASSWD for the restic binary
# itself, not for `install` or `cp`. Since admin is already in the docker
# group (root-equivalent for filesystem writes via container mounts), we use
# a throwaway Alpine container to land the binary. No new privilege granted.
#
# Usage: ./install-restic.sh [version]    e.g. v0.18.1 (default)

set -euo pipefail

VERSION="${1:-v0.18.1}"
VER_NUM="${VERSION#v}"

case "$(uname -m)" in
  x86_64)  ARCH=amd64 ;;
  aarch64) ARCH=arm64 ;;
  *) echo "unsupported arch: $(uname -m)" >&2; exit 1 ;;
esac

TARBALL="restic_${VER_NUM}_linux_${ARCH}.bz2"
URL="https://github.com/restic/restic/releases/download/${VERSION}/${TARBALL}"
SUMS_URL="https://github.com/restic/restic/releases/download/${VERSION}/SHA256SUMS"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"

echo "[1/4] downloading $TARBALL"
curl -sSfL --max-time 180 -o "$TARBALL" "$URL"

echo "[2/4] downloading SHA256SUMS"
curl -sSfL --max-time 30 -o SHA256SUMS "$SUMS_URL"

echo "[3/4] verifying checksum"
grep -E "  ${TARBALL}$" SHA256SUMS | sha256sum -c -

echo "[4/4] decompressing + installing to /usr/local/bin/restic"
bunzip2 "$TARBALL"
BIN="restic_${VER_NUM}_linux_${ARCH}"
chmod +x "$BIN"

docker run --rm \
  -v "$TMPDIR:/work:ro" \
  -v /usr/local/bin:/dest \
  alpine \
  sh -c "install -m 0755 -o root -g root /work/$BIN /dest/restic"

echo
echo "installed:"
/usr/local/bin/restic version
