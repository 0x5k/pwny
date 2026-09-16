#!/usr/bin/env bash
# Run with sudo inside a dedicated experiment directory on the Pi.
set -euo pipefail
experiment_dir="$(cd "$(dirname "$0")" && pwd)"
cd "$experiment_dir"
sha256sum -c runtime.squashfs.sha256
mkdir -p rootfs
if mountpoint -q rootfs; then
  echo 'Refusing to reuse an already mounted experiment root' >&2
  exit 1
fi
mount -t squashfs -o loop,ro,nodev,nosuid runtime.squashfs rootfs
trap 'umount "$experiment_dir/rootfs"' EXIT
python3 pi_monitor.py "$experiment_dir/rootfs" "$experiment_dir/results"
