#!/bin/bash
# Local builds use the same immutable component path as release workflows.
set -Eeuo pipefail
project_dir=$(cd "$(dirname "$0")" && pwd)
[ -z "$(git -C "$project_dir" status --porcelain)" ] || {
  printf 'Commit source changes before building a release.\n' >&2
  exit 1
}
exec python3 "$project_dir/scripts/build-components.py" "$@"
