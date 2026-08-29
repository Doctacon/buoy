#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel)
UV_BIN=$(command -v uv)
PYTHON_BIN=$(command -v python3)
ORIGINAL_HOME=${HOME:?}
OFFLINE_UV_CACHE="$ORIGINAL_HOME/.cache/uv"
LOCK_PATH="$REPO_ROOT/uv.lock"
LOCK_SHA256=ad7508159bc00271b21fc598bad07b56045329c938ed4fbd37a5a18d71c4c254
RUNTIME_EXPORT_SHA256=63dd2f01c9a32a1ff45cc3d0dc77fcb1fb91b0a398441e405d7ab78204d19384
FROZEN_IDENTITY_SHA256=5f7fbf88d914ab73fca4a2de2beb9fc608146b3122deabd773c74ca544bf5938
PINNED_VERSION=0.5.2.dev125+gf64b6ad27.d20260829
PINNED_SOURCE_DATE_EPOCH=1787961600
RUN_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/buoy-v3-wheel-lifecycle.XXXXXX")
DIST_ROOT="$RUN_ROOT/dist"
DIST_REPEAT_ROOT="$RUN_ROOT/dist-repeat"
HOME_ROOT="$RUN_ROOT/home"
VENV_ROOT="$RUN_ROOT/venv"
cleanup() {
  rm -rf "$DIST_ROOT" "$DIST_REPEAT_ROOT" "$HOME_ROOT" "$VENV_ROOT" "$RUN_ROOT"
}
trap 'printf "lifecycle_failed_line=%s\n" "$LINENO" >&2' ERR
trap cleanup EXIT INT TERM
mkdir -m 700 "$DIST_ROOT" "$DIST_REPEAT_ROOT" "$HOME_ROOT" "$VENV_ROOT"
chmod 700 "$RUN_ROOT" "$DIST_ROOT" "$DIST_REPEAT_ROOT" "$HOME_ROOT" "$VENV_ROOT"

test -d "$OFFLINE_UV_CACHE"
test "$(shasum -a 256 "$LOCK_PATH" | awk '{print $1}')" = "$LOCK_SHA256"
test "$("$UV_BIN" --version | awk '{print $2}')" = 0.11.7
export HOME="$HOME_ROOT"
export UV_CACHE_DIR="$OFFLINE_UV_CACHE"
export UV_OFFLINE=1
export UV_PYTHON_DOWNLOADS=never
export PIP_NO_INDEX=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=0
export SOURCE_DATE_EPOCH="$PINNED_SOURCE_DATE_EPOCH"
export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BUOY_SEARCH="$PINNED_VERSION"
export TZ=UTC
export LC_ALL=C
export BUOY_TELEMETRY=local
export NO_COLOR=1
export TERM=dumb
export HTTP_PROXY=http://127.0.0.1:9
export HTTPS_PROXY=http://127.0.0.1:9
export ALL_PROXY=http://127.0.0.1:9
export NO_PROXY=localhost,127.0.0.1
unset TURBOPUFFER_API_KEY TURBOPUFFER_API_TOKEN OPENAI_API_KEY ANTHROPIC_API_KEY
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN GOOGLE_APPLICATION_CREDENTIALS
unset BUOY_HOME XDG_CACHE_HOME XDG_CONFIG_HOME XDG_DATA_HOME XDG_STATE_HOME OTEL_EXPORTER_OTLP_ENDPOINT
unset UV_CONFIG_FILE UV_INDEX UV_DEFAULT_INDEX UV_EXTRA_INDEX_URL UV_INDEX_URL

test "$SOURCE_DATE_EPOCH" = 1787961600
test "$SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BUOY_SEARCH" = 0.5.2.dev125+gf64b6ad27.d20260829
test "$UV_CACHE_DIR" = "$ORIGINAL_HOME/.cache/uv"

INPUT_ROOT="$HOME_ROOT/private-inputs"
mkdir -m 700 "$INPUT_ROOT"
QUERY_INPUT="$INPUT_ROOT/query.input"
NAMESPACE_INPUT="$INPUT_ROOT/namespace.input"
"$PYTHON_BIN" - "$QUERY_INPUT" "$NAMESPACE_INPUT" <<'PY'
from pathlib import Path
import secrets
import sys

Path(sys.argv[1]).write_text(secrets.token_hex(24), encoding="utf-8")
Path(sys.argv[2]).write_text(secrets.token_hex(16), encoding="utf-8")
PY
chmod 600 "$QUERY_INPUT" "$NAMESPACE_INPUT"
"$PYTHON_BIN" - "$RUN_ROOT" "$DIST_ROOT" "$DIST_REPEAT_ROOT" "$HOME_ROOT" "$VENV_ROOT" "$INPUT_ROOT" "$QUERY_INPUT" "$NAMESPACE_INPUT" <<'PY'
from pathlib import Path
import stat
import sys

for raw in sys.argv[1:7]:
    assert stat.S_IMODE(Path(raw).stat().st_mode) == 0o700
for raw in sys.argv[7:]:
    assert stat.S_IMODE(Path(raw).stat().st_mode) == 0o600
PY

cd "$REPO_ROOT"
RUNTIME_EXPORT="$RUN_ROOT/runtime-lock.txt"
"$UV_BIN" export --offline --frozen --no-dev --no-emit-project --no-header \
  --format requirements.txt --output-file "$RUNTIME_EXPORT" \
  >"$RUN_ROOT/export.stdout" 2>"$RUN_ROOT/export.stderr"
test "$(shasum -a 256 "$RUNTIME_EXPORT" | awk '{print $1}')" = "$RUNTIME_EXPORT_SHA256"

"$UV_BIN" build --out-dir "$DIST_ROOT" >"$RUN_ROOT/build.stdout" 2>"$RUN_ROOT/build.stderr"
"$UV_BIN" build --out-dir "$DIST_REPEAT_ROOT" >"$RUN_ROOT/build-repeat.stdout" 2>"$RUN_ROOT/build-repeat.stderr"
WHEEL_NAME=buoy_search-0.5.2.dev125+gf64b6ad27.d20260829-py3-none-any.whl
SDIST_NAME=buoy_search-0.5.2.dev125+gf64b6ad27.d20260829.tar.gz
WHEEL_SHA256=deee5e93d68533e2465a0fc0d0b85fa9262d6591decc4890bf208f9560abfdf4
SDIST_SHA256=92c707410d94538a61dee94d26f9efc941cdedd16a23bdc8e4cd4c644a8a5072
WHEEL_PATH="$DIST_ROOT/$WHEEL_NAME"
SDIST_PATH="$DIST_ROOT/$SDIST_NAME"
REPEAT_WHEEL_PATH="$DIST_REPEAT_ROOT/$WHEEL_NAME"
REPEAT_SDIST_PATH="$DIST_REPEAT_ROOT/$SDIST_NAME"
for artifact in "$WHEEL_PATH" "$SDIST_PATH" "$REPEAT_WHEEL_PATH" "$REPEAT_SDIST_PATH"; do
  test -f "$artifact"
done
test "$(shasum -a 256 "$WHEEL_PATH" | awk '{print $1}')" = "$WHEEL_SHA256"
test "$(shasum -a 256 "$SDIST_PATH" | awk '{print $1}')" = "$SDIST_SHA256"
test "$(shasum -a 256 "$REPEAT_WHEEL_PATH" | awk '{print $1}')" = "$WHEEL_SHA256"
test "$(shasum -a 256 "$REPEAT_SDIST_PATH" | awk '{print $1}')" = "$SDIST_SHA256"
cmp "$WHEEL_PATH" "$REPEAT_WHEEL_PATH"
cmp "$SDIST_PATH" "$REPEAT_SDIST_PATH"

"$UV_BIN" venv --allow-existing --python 3.11 "$VENV_ROOT" >"$RUN_ROOT/venv.stdout" 2>"$RUN_ROOT/venv.stderr"
"$UV_BIN" pip sync --offline --require-hashes --strict \
  --python "$VENV_ROOT/bin/python" "$RUNTIME_EXPORT" \
  >"$RUN_ROOT/sync.stdout" 2>"$RUN_ROOT/sync.stderr"
"$UV_BIN" pip install --offline --no-index --no-deps \
  --python "$VENV_ROOT/bin/python" "$WHEEL_PATH" \
  >"$RUN_ROOT/install.stdout" 2>"$RUN_ROOT/install.stderr"
"$UV_BIN" pip check --python "$VENV_ROOT/bin/python" \
  >"$RUN_ROOT/check.stdout" 2>"$RUN_ROOT/check.stderr"
"$UV_BIN" pip freeze --python "$VENV_ROOT/bin/python" \
  >"$RUN_ROOT/freeze.unsorted" 2>"$RUN_ROOT/freeze.stderr"
LC_ALL=C sort "$RUN_ROOT/freeze.unsorted" >"$RUN_ROOT/freeze.txt"
grep -v '^buoy-search @ ' "$RUN_ROOT/freeze.txt" >"$RUN_ROOT/runtime-freeze.txt"
OBSERVED_FROZEN_IDENTITY_SHA256=$(shasum -a 256 "$RUN_ROOT/runtime-freeze.txt" | awk '{print $1}')
test "$OBSERVED_FROZEN_IDENTITY_SHA256" = "$FROZEN_IDENTITY_SHA256"
test "$(wc -l < "$RUN_ROOT/runtime-freeze.txt" | tr -d ' ')" = 108

QUERY=$(cat "$QUERY_INPUT")
NAMESPACE=$(cat "$NAMESPACE_INPUT")
"$VENV_ROOT/bin/buoy" retrieve "$QUERY" --namespace "$NAMESPACE" --dry-run --json >"$RUN_ROOT/preview.stdout" 2>"$RUN_ROOT/preview.stderr"
"$VENV_ROOT/bin/buoy" telemetry flush --timeout 60 --json >"$RUN_ROOT/flush.stdout" 2>"$RUN_ROOT/flush.stderr"
"$VENV_ROOT/bin/buoy" telemetry status --json >"$RUN_ROOT/status.stdout" 2>"$RUN_ROOT/status.stderr"
"$VENV_ROOT/bin/buoy" telemetry --help >"$RUN_ROOT/help.stdout" 2>"$RUN_ROOT/help.stderr"

test ! -s "$RUN_ROOT/preview.stderr"
test ! -s "$RUN_ROOT/flush.stderr"
test ! -s "$RUN_ROOT/status.stderr"
test ! -s "$RUN_ROOT/help.stderr"
grep -q 'flush' "$RUN_ROOT/help.stdout"
grep -q 'status' "$RUN_ROOT/help.stdout"

"$VENV_ROOT/bin/python" - "$RUN_ROOT/flush.stdout" "$RUN_ROOT/flush.bounded" <<'PY'
import json
import sys

value = json.load(open(sys.argv[1], encoding="utf-8"))
assert value["outcome"] == "flushed"
assert value["schema_version"] == 3
assert value["snapshot"] == 1
assert value["committed"] == 1
assert value["pending"] == 0
assert value["replayed"] == value["conflicts"] == value["rejected"] == 0
bounded = {key: value[key] for key in (
    "schema_version", "outcome", "snapshot", "committed", "replayed",
    "conflicts", "rejected", "pending", "elapsed_ms",
)}
open(sys.argv[2], "w", encoding="utf-8").write(json.dumps(bounded, sort_keys=True))
PY

"$VENV_ROOT/bin/python" - "$RUN_ROOT/status.stdout" "$RUN_ROOT/status.bounded" <<'PY'
import json
import sys

value = json.load(open(sys.argv[1], encoding="utf-8"))
assert value["requested"] is True and value["effective"] is True
assert value["enablement_reason"] == "enabled"
assert value["schema_version"] == 3 and value["overall"] == "healthy"
assert value["store"]["state"] == "compatible"
assert value["store"]["schema_version"] == 3
assert value["store"]["persisted_runs_snapshot"] == 1
assert value["queue"]["state"] == "empty"
assert value["queue"]["ready"] == value["queue"]["claimed"] == 0
assert value["queue"]["v1_ready"] == value["queue"]["v1_claimed"] == 0
assert value["queue"]["v2_ready"] == value["queue"]["v2_claimed"] == 0
assert value["queue"]["v3_ready"] == value["queue"]["v3_claimed"] == 0
assert value["accounting"]["incomplete"] is False
assert value["accounting"]["durability_degraded"] is False
bounded = {
    "requested": value["requested"],
    "effective": value["effective"],
    "enablement_reason": value["enablement_reason"],
    "schema_version": value["schema_version"],
    "overall": value["overall"],
    "store": {
        "state": value["store"]["state"],
        "schema_version": value["store"]["schema_version"],
        "persisted_runs_snapshot": value["store"]["persisted_runs_snapshot"],
    },
    "queue": {
        key: value["queue"][key]
        for key in ("state", "ready", "claimed", "v1_ready", "v1_claimed", "v2_ready", "v2_claimed", "v3_ready", "v3_claimed")
    },
    "accounting": {
        "incomplete": value["accounting"]["incomplete"],
        "durability_degraded": value["accounting"]["durability_degraded"],
    },
}
open(sys.argv[2], "w", encoding="utf-8").write(json.dumps(bounded, sort_keys=True))
PY

"$VENV_ROOT/bin/python" - "$HOME_ROOT" "$RUN_ROOT/views.bounded" <<'PY'
from pathlib import Path
import json
import sys
import duckdb

home = Path(sys.argv[1]).resolve()
database = (home / ".buoy" / "telemetry" / "telemetry.duckdb").resolve()
assert database.is_relative_to(home)
with duckdb.connect(str(database), read_only=True) as connection:
    command = connection.execute("""
        SELECT observation_schema_version, execution_mode, retrieval_mode,
               command_outcome, inference_policy, pipeline_duration_ms,
               worker_encode_requests, worker_score_requests,
               in_process_encode_requests, in_process_score_requests,
               worker_spawned_requests, worker_reused_requests,
               worker_error_requests, fallback_requests
        FROM retrieval_command_runs_v3
    """).fetchall()
    stages = connection.execute(
        "SELECT stage, status_code FROM retrieval_stage_latency_v3 ORDER BY stage"
    ).fetchall()
    stage_count = len(stages)
    inference_count = connection.execute(
        "SELECT count(*) FROM retrieval_inference_requests_v3"
    ).fetchone()[0]
    provider = connection.execute("""
        SELECT accounting_status, unit, content_logical_operation_count,
               content_invocation_count, content_success_count,
               content_error_count, content_interrupted_count,
               catalog_outcome, catalog_invocation_count,
               catalog_namespace_list_page_count, catalog_metadata_count,
               catalog_card_query_page_count, catalog_success_count,
               catalog_error_count, catalog_interrupted_count
        FROM retrieval_provider_summary_v3
    """).fetchall()
    content_invocation_count = connection.execute(
        "SELECT count(*) FROM retrieval_provider_content_invocations_v3"
    ).fetchone()[0]
expected_command = [[3, "preview", "explicit_single", "success", "worker_preferred", None, 0, 0, 0, 0, 0, 0, 0, 0]]
expected_provider = [["complete", "provider_client_invocation", 0, 0, 0, 0, 0, None, 0, 0, 0, 0, 0, 0, 0]]
expected_stages = [
    ["buoy.cli.bootstrap", "OK"],
    ["buoy.output.render", "OK"],
    ["buoy.retrieve.prepare", "OK"],
]
value = {
    "retrieval_command_runs_v3": [list(row) for row in command],
    "retrieval_stage_latency_v3": [list(row) for row in stages],
    "retrieval_stage_latency_v3_count": stage_count,
    "retrieval_inference_requests_v3_count": inference_count,
    "retrieval_provider_summary_v3": [list(row) for row in provider],
    "retrieval_provider_content_invocations_v3_count": content_invocation_count,
}
assert value["retrieval_command_runs_v3"] == expected_command
assert value["retrieval_stage_latency_v3"] == expected_stages
assert value["retrieval_stage_latency_v3_count"] == 3
assert value["retrieval_inference_requests_v3_count"] == 0
assert value["retrieval_provider_summary_v3"] == expected_provider
assert value["retrieval_provider_content_invocations_v3_count"] == 0
open(sys.argv[2], "w", encoding="utf-8").write(json.dumps(value, sort_keys=True))
PY

"$VENV_ROOT/bin/python" - "$RUN_ROOT/runtime-freeze.txt" "$RUN_ROOT/identity.bounded" <<'PY'
import hashlib
import importlib.metadata as metadata
import json
import platform
import sys

freeze = open(sys.argv[1], "rb").read()
value = {
    "python": platform.python_version(),
    "implementation": platform.python_implementation(),
    "packages": {
        name: metadata.version(name)
        for name in ("buoy-search", "duckdb", "turbopuffer", "opentelemetry-sdk")
    },
    "frozen_runtime": {
        "distributions": len(freeze.splitlines()),
        "sha256": hashlib.sha256(freeze).hexdigest(),
    },
}
expected = {
    "python": "3.11.5",
    "implementation": "CPython",
    "packages": {
        "buoy-search": "0.5.2.dev125+gf64b6ad27.d20260829",
        "duckdb": "1.5.4",
        "turbopuffer": "2.4.0",
        "opentelemetry-sdk": "1.44.0",
    },
    "frozen_runtime": {
        "distributions": 108,
        "sha256": "5f7fbf88d914ab73fca4a2de2beb9fc608146b3122deabd773c74ca544bf5938",
    },
}
assert value == expected
open(sys.argv[2], "w", encoding="utf-8").write(json.dumps(value, sort_keys=True))
PY

process_count() {
  local matches
  matches=$(pgrep -f "$VENV_ROOT/bin/python.*buoy_search\.(telemetry\.writer|retrieval\.embedding_worker)" || true)
  if [[ -z "$matches" ]]; then
    printf '0'
  else
    printf '%s\n' "$matches" | wc -l | tr -d ' '
  fi
}
for _ in $(seq 1 80); do
  [[ "$(process_count)" == 0 ]] && break
  sleep 0.25
done
SURVIVORS=$(process_count)
test "$SURVIVORS" = 0

"$VENV_ROOT/bin/python" - "$RUN_ROOT" "$RUN_ROOT/output-bytes.bounded" <<'PY'
from pathlib import Path
import json
import sys

root = Path(sys.argv[1])
names = (
    "export.stdout", "export.stderr", "build.stdout", "build.stderr",
    "build-repeat.stdout", "build-repeat.stderr", "venv.stdout", "venv.stderr",
    "sync.stdout", "sync.stderr", "install.stdout", "install.stderr",
    "check.stdout", "check.stderr", "freeze.stderr",
    "preview.stdout", "preview.stderr", "flush.stdout", "flush.stderr",
    "status.stdout", "status.stderr", "help.stdout", "help.stderr",
)
value = {name: (root / name).stat().st_size for name in names}
open(sys.argv[2], "w", encoding="utf-8").write(json.dumps(value, sort_keys=True))
PY

printf 'BUILD_CONTROLS={"deterministic_second_build":true,"setuptools_scm_override":"%s","source_date_epoch":%s,"uv":"0.11.7","uv_lock_sha256":"%s"}\n' "$PINNED_VERSION" "$SOURCE_DATE_EPOCH" "$LOCK_SHA256"
printf 'RUNTIME_EXPORT={"lines":%s,"sha256":"%s"}\n' "$(wc -l < "$RUNTIME_EXPORT" | tr -d ' ')" "$RUNTIME_EXPORT_SHA256"
printf 'ARTIFACTS={"sdist":{"name":"%s","sha256":"%s"},"wheel":{"name":"%s","sha256":"%s"}}\n' "$SDIST_NAME" "$SDIST_SHA256" "$WHEEL_NAME" "$WHEEL_SHA256"
printf 'IDENTITY=%s\n' "$(cat "$RUN_ROOT/identity.bounded")"
printf 'OUTPUT_BYTES=%s\n' "$(cat "$RUN_ROOT/output-bytes.bounded")"
printf 'FLUSH=%s\n' "$(cat "$RUN_ROOT/flush.bounded")"
printf 'STATUS=%s\n' "$(cat "$RUN_ROOT/status.bounded")"
printf 'V3_VIEWS=%s\n' "$(cat "$RUN_ROOT/views.bounded")"
printf 'PROCESS_SURVIVORS=%s\n' "$SURVIVORS"

rm -rf "$DIST_ROOT" "$DIST_REPEAT_ROOT" "$HOME_ROOT" "$VENV_ROOT"
test ! -e "$DIST_ROOT"
test ! -e "$DIST_REPEAT_ROOT"
test ! -e "$HOME_ROOT"
test ! -e "$VENV_ROOT"
rm -rf "$RUN_ROOT"
test ! -e "$RUN_ROOT"
trap - EXIT INT TERM
printf 'ABSENCE_CHECKS={"dist":true,"dist_repeat":true,"home":true,"run":true,"venv":true}\n'
