#!/bin/bash
set -euo pipefail
cd /Users/crlough/Code/personal/turbo-search.worktrees/buoy-mcp-server
E="$PWD/.10x/evidence/.storage/buoy-mcp-installation"
T=$(cat "$E/environment-path.txt")
OLD=/tmp/buoy-mcp-runtime.LJClud
H="$T/h"
C="$OLD/cache/uv"
run() {
  printf '\n$ %s\n' "$*"
  env -i PATH="$OLD/venv/bin:$OLD/venv311/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" HOME="$H" UV_CACHE_DIR="$C" UV_PYTHON_DOWNLOADS=never XDG_CACHE_HOME="$T/cache" HF_HOME="$T/cache/hf" TORCH_HOME="$T/cache/torch" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 "$@"
}
git rev-parse HEAD > "$E/source-head.txt"
git status --short > "$E/source-status.txt"
run env UV_PROJECT_ENVIRONMENT="$OLD/venv" uv sync --locked --extra mcp --python 3.13
run env UV_PROJECT_ENVIRONMENT="$OLD/venv311" uv sync --locked --extra mcp --python 3.11
run env UV_PROJECT_ENVIRONMENT="$OLD/venv" uv run --locked --extra mcp buoy mcp --help
run uv lock --check
run uv build --out-dir "$T/dist"
run uv export --locked --extra mcp --no-dev --no-emit-project --output-file "$T/constraints.txt" >/dev/null
for version in 313 311; do
  if [ "$version" = 313 ]; then P="$OLD/venv/bin/python"; else P="$OLD/venv311/bin/python"; fi
  for mode in base extra; do
    run uv venv --python "$P" "$T/$mode$version"
    set -- "$T"/dist/*.whl
    test "$#" -eq 1
    wheel="$1"
    if [ "$mode" = extra ]; then install="$wheel[mcp]"; else install="$wheel"; fi
    run uv pip install --python "$T/$mode$version/bin/python" --constraint "$T/constraints.txt" "$install"
  done
done
