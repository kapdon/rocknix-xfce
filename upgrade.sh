#!/bin/bash
# Replace the LXC system from components, preserving home and shared files.
set -Eeuo pipefail
self_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
for helper in "$self_dir/upgrade-lxc.py" "$self_dir/payload/bin/rocknix-lxc-upgrade"; do
  if [ -f "$helper" ]; then exec python3 "$helper" "$@"; fi
done
printf 'Missing LXC updater; no files were changed.\n' >&2
exit 1
