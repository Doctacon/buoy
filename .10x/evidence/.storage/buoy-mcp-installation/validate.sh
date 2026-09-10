#!/bin/bash
set -euo pipefail
cd /Users/crlough/Code/personal/turbo-search.worktrees/buoy-mcp-server
E="$PWD/.10x/evidence/.storage/buoy-mcp-installation"
T=$(cat "$E/environment-path.txt")
OLD=/tmp/buoy-mcp-runtime.LJClud
run() {
  printf '\n$ %s\n' "$*"
  env -i PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" HOME="$T/h" UV_CACHE_DIR="$OLD/cache/uv" UV_PYTHON_DOWNLOADS=never XDG_CACHE_HOME="$T/cache" HF_HOME="$T/cache/hf" TORCH_HOME="$T/cache/torch" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 "$@"
}
# Refresh the reused source environment's VCS metadata; uv otherwise reuses its
# earlier editable build cache when only source (not pyproject) changed.
run env UV_PROJECT_ENVIRONMENT="$OLD/venv" uv sync --locked --extra mcp --python "$OLD/venv/bin/python" --reinstall-package buoy-search > "$E/source-refresh.log" 2>&1
run "$OLD/venv/bin/python" -c 'import buoy_search, importlib.metadata; print(buoy_search.__version__, importlib.metadata.version("buoy-search")); assert buoy_search.__version__ == importlib.metadata.version("buoy-search")' >> "$E/source-refresh.log" 2>&1
for version in 311 313; do
  P="$T/extra$version/bin/python"
  run "$P" -m unittest discover -s tests -p 'test_*.py' -q > "$E/full-$version.log" 2>&1
  run "$P" scripts/validate_ranking_contract.py > "$E/ranking-$version.log" 2>&1
  run "$P" scripts/validate_ranking_promotion.py --base-ref db5e8e1597e908c30fff76ec2aba565f1e2fbcbc > "$E/promotion-$version.log" 2>&1
  run "$P" scripts/c6_syntax_forecast.py validate > "$E/c6-$version.log" 2>&1
  for mode in base extra; do
    run "$T/$mode$version/bin/python" tests/core/mcp_installation_smoke.py --mode "$mode" --wheel "$T"/dist/*.whl > "$E/installed-$mode-$version.log" 2>&1
  done
  # Execute the existing CI tokenizer/data acceptance verbatim, not a reduced copy.
  run "$T/base$version/bin/python" "$T/ci-base-smoke.py" > "$E/base-data-$version.log" 2>&1
done
run uv lock --check > "$E/lock-check.log" 2>&1
git diff --check > "$E/diff-check.log" 2>&1
