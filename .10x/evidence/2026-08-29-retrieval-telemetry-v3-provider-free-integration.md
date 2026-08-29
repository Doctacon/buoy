Status: recorded
Created: 2026-08-29
Updated: 2026-08-29
Ticket: .10x/tickets/done/2026-08-28-validate-retrieval-telemetry-v3-integration.md
Decision: .10x/decisions/buoy-records-worker-and-provider-attempt-retrieval-telemetry-v3.md
Review: .10x/reviews/2026-08-29-retrieval-telemetry-v3-integration-review.md

# Retrieval Telemetry V3 Provider-Free Integration Evidence

## Scope

Validated the complete current retrieval telemetry v3 implementation without Turbopuffer/provider calls, credential access, provider writes, model download/inference, real telemetry-store access/migration, staging, commit, push, or release.

This phase exercised production-default v3 command publication, inference and provider normalization, views, disabled behavior, v1/v2 compatibility, synthetic v2 migration, packaging, and an installed-wheel lifecycle in private temporary homes. It also tightened the user documentation for caller-observed inference timing and safe provider-attempt analysis.

## Aggregate acceptance map

- **Production v3:** Current command creation publishes canonical v3 through inbox-v3; the writer commits exact schema 3 and all normalized rows atomically.
- **Inference:** Deterministic fixtures cover worker spawned/reused, in-process primary, worker failure plus in-process fallback, double failure, opt-out/compatibility policy, routing/query/rerank/evidence parentage, and evidence score reuse.
- **Provider accounting:** Provider-free governed callbacks cover complete/unavailable authority, explicit content attempts/fallbacks, automatic catalog categories, failures/interruptions, route/fanout/catalog graph agreement, maxima, and strict privacy.
- **Views:** The exact ordered scenario matrix covers preview, pre-pipeline failure, live success/failure, worker spawn/reuse, fallback, catalog-only, content-only, and automatic combined rows.
- **Disabled behavior and equivalence:** Existing enabled/disabled command, output, routing-error, retriever result, observer-fault, provider-call, ranking, and evidence fixtures remain exact and passed in both full suites. Disabled telemetry creates no queue/store publication.
- **Compatibility/migration:** V1 direct-library and v2 command envelopes/views remain exact. Synthetic v2-to-v3 migration preserves old rows/view identities and both fixed backups under crash/retry and terminal-drain tests.
- **Privacy/no network:** Production-default entrypoint tests pass prohibited values through query, content, provider response/error, credential, ambient context, and worker seams, then scan queue, receipts, state, normalized store, management output, scratch, and backups. Management socket/DNS denial tests pass.

## Dual-runtime full suites

The first Python 3.13 attempt used an unnecessarily long temporary HOME. That pushed worker Unix-socket paths above the established 100-byte limit and produced 32 worker-test failures before worker startup. This was a harness-path error, not a product regression or provider/model action. The temporary root was removed and the suite was rerun once with the required short private HOME.

Exact Python 3.13 command:

```bash
env -u TURBOPUFFER_API_KEY -u BUOY_TELEMETRY -u OTEL_SDK_DISABLED \
  HOME=/tmp/bv3-313 UV_OFFLINE=1 HF_HUB_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  PYTHONDONTWRITEBYTECODE=1 \
  uv run --python 3.13 --with pytest pytest -q
```

Result: `1327 passed, 57 warnings, 1408 subtests passed`.

Exact isolated Python 3.11 command:

```bash
env -u TURBOPUFFER_API_KEY -u BUOY_TELEMETRY -u OTEL_SDK_DISABLED \
  HOME=/tmp/bv3-311 UV_OFFLINE=1 HF_HUB_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  PYTHONDONTWRITEBYTECODE=1 \
  uv run --isolated --python 3.11 --with pytest pytest -q
```

Result: `1327 passed, 57 warnings, 1408 subtests passed`.

The warnings are the pre-existing lxml `strip_cdata` deprecations. Both short
private homes were removed by command traps. Runtime identities were:

```text
Python 3.13.0 (Clang 18.1.8)
Python 3.11.5 (Clang 13.0.0)
buoy-search 0.5.2.dev125+gf64b6ad27.d20260829
source environment DuckDB 1.5.4
uv 0.11.7
Darwin 25.5.0 arm64 / macOS 26.5.1
```

Focused migration/CLI integration command:

```bash
HOME=/tmp/bv3focused UV_OFFLINE=1 HF_HUB_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  uv run --python 3.13 --with pytest pytest -q \
  tests/telemetry/test_telemetry_v3_storage.py \
  tests/telemetry/test_telemetry_v2_storage.py \
  tests/telemetry/test_telemetry_cli.py \
  tests/telemetry/test_retrieve_command_telemetry.py
```

Result: `104 passed, 209 subtests passed`.

## Packaging and literal installed-wheel lifecycle

The final replay-independent executable evidence is:

```text
.10x/evidence/scripts/2026-08-29-retrieval-telemetry-v3-installed-wheel-lifecycle.sh
sha256 f527b1f45001ec825ec26d7efa33df9e1d7b5a597a92c5029944e3e5f0478a85
mode 0755; 15,476 bytes
```

It was run literally from the repository root with:

```bash
.10x/evidence/scripts/2026-08-29-retrieval-telemetry-v3-installed-wheel-lifecycle.sh
```

The script contains no substituted example values or omitted command shape. It
creates fresh mode-0700 run, dist, repeat-dist, HOME, venv, and private-input
roots, plus fresh random mode-0600 query/namespace files whose values are never
printed or retained. It removes provider/cloud credentials, enables
`BUOY_TELEMETRY=local`, sets uv/pip/model/tokenizer offline controls, disables
Python downloads, and directs ambient HTTP(S)/all-proxy traffic to a closed
loopback port.

### Replay controls and dependency identity

The script no longer asks uv to resolve its ambient cache location or to choose
runtime dependency versions while installing the wheel. It explicitly binds
the standard offline artifact cache at `$ORIGINAL_HOME/.cache/uv`; that cache
is transport only. Version and artifact selection are governed by the asserted
lock/export hashes below:

```json
{"deterministic_second_build":true,"setuptools_scm_override":"0.5.2.dev125+gf64b6ad27.d20260829","source_date_epoch":1787961600,"uv":"0.11.7","uv_lock_sha256":"ad7508159bc00271b21fc598bad07b56045329c938ed4fbd37a5a18d71c4c254"}
```

`SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BUOY_SEARCH` is the distribution-specific
setuptools-scm override used by Hatch VCS. `SOURCE_DATE_EPOCH=1787961600`
(`2026-08-29T00:00:00Z`) is exported and asserted before both builds. The script
also fixes UTC, C locale, and Python hash seed.

The exact current `uv.lock` is asserted before use. The script exports the
runtime dependency graph with `uv export --offline --frozen --no-dev
--no-emit-project --no-header`, asserts the export hash, installs it with
`uv pip sync --offline --require-hashes --strict`, then installs the exact local
wheel with `--offline --no-index --no-deps`, so wheel installation performs no
dependency re-resolution.

```json
{"lines":2512,"sha256":"63dd2f01c9a32a1ff45cc3d0dc77fcb1fb91b0a398441e405d7ab78204d19384"}
```

The sorted frozen dependency identity excludes only the temp-path-bearing local
wheel line. Its 108 exact runtime distributions are asserted by count and hash.
The local wheel identity is separately asserted in the exact installed identity
object; this object is compared to a literal expected object before it is
written or printed:

```json
{"frozen_runtime":{"distributions":108,"sha256":"5f7fbf88d914ab73fca4a2de2beb9fc608146b3122deabd773c74ca544bf5938"},"implementation":"CPython","packages":{"buoy-search":"0.5.2.dev125+gf64b6ad27.d20260829","duckdb":"1.5.4","opentelemetry-sdk":"1.44.0","turbopuffer":"2.4.0"},"python":"3.11.5"}
```

### Deterministic artifacts

Two independent dist directories were built consecutively under the same fixed
controls. Both wheel files were byte-identical and both sdists were
byte-identical (`cmp` passed); every first and second build hash matched:

```text
buoy_search-0.5.2.dev125+gf64b6ad27.d20260829-py3-none-any.whl
sha256 deee5e93d68533e2465a0fc0d0b85fa9262d6591decc4890bf208f9560abfdf4

buoy_search-0.5.2.dev125+gf64b6ad27.d20260829.tar.gz
sha256 92c707410d94538a61dee94d26f9efc941cdedd16a23bdc8e4cd4c644a8a5072
```

### Installed v3 lifecycle

The installed public CLI executed production-default schema-v3 explicit
preview, flush, status, and telemetry help. Help was required to contain both
`flush` and `status`. Raw outputs stayed in the private run root and were
reduced to these bounded byte counts before deletion:

```json
{"build-repeat.stderr":413,"build-repeat.stdout":0,"build.stderr":399,"build.stdout":0,"check.stderr":195,"check.stdout":0,"export.stderr":0,"export.stdout":189138,"flush.stderr":0,"flush.stdout":139,"freeze.stderr":129,"help.stderr":0,"help.stdout":658,"install.stderr":421,"install.stdout":0,"preview.stderr":0,"preview.stdout":2281,"status.stderr":0,"status.stdout":951,"sync.stderr":2439,"sync.stdout":0,"venv.stderr":342,"venv.stdout":0}
```

Bounded flush output:

```json
{"committed":1,"conflicts":0,"elapsed_ms":10927,"outcome":"flushed","pending":0,"rejected":0,"replayed":0,"schema_version":3,"snapshot":1}
```

Bounded status output:

```json
{"accounting":{"durability_degraded":false,"incomplete":false},"effective":true,"enablement_reason":"enabled","overall":"healthy","queue":{"claimed":0,"ready":0,"state":"empty","v1_claimed":0,"v1_ready":0,"v2_claimed":0,"v2_ready":0,"v3_claimed":0,"v3_ready":0},"requested":true,"schema_version":3,"store":{"persisted_runs_snapshot":1,"schema_version":3,"state":"compatible"}}
```

Exact privacy-safe schema-v3 analytical-view rows:

```json
{"retrieval_command_runs_v3":[[3,"preview","explicit_single","success","worker_preferred",null,0,0,0,0,0,0,0,0]],"retrieval_inference_requests_v3_count":0,"retrieval_provider_content_invocations_v3_count":0,"retrieval_provider_summary_v3":[["complete","provider_client_invocation",0,0,0,0,0,null,0,0,0,0,0,0,0]],"retrieval_stage_latency_v3":[["buoy.cli.bootstrap","OK"],["buoy.output.render","OK"],["buoy.retrieve.prepare","OK"]],"retrieval_stage_latency_v3_count":3}
```

The database path was derived only beneath the temporary HOME and asserted to
resolve beneath that HOME before read-only DuckDB inspection. No query,
namespace, trace/span identity, path, timestamp, provider identity, credential,
or raw command output was printed or retained. The script proved zero writer or
embedding-worker survivors, removed both dist roots, HOME, venv, and enclosing
run root, then executed literal `test ! -e` checks:

```text
PROCESS_SURVIVORS=0
ABSENCE_CHECKS={"dist":true,"dist_repeat":true,"home":true,"run":true,"venv":true}
```

The owner's real telemetry store was never opened.

## Static and contract validation

Final focused command after the evidence/documentation repairs:

```bash
env -u TURBOPUFFER_API_KEY -u BUOY_TELEMETRY -u OTEL_SDK_DISABLED \
  HOME=/tmp/bv3-final-focused UV_OFFLINE=1 HF_HUB_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
  TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1 \
  uv run --python 3.13 --with pytest pytest -q \
  tests/telemetry/test_retrieve_command_telemetry.py \
  tests/telemetry/test_telemetry_v3_storage.py \
  tests/telemetry/test_telemetry_cli.py
```

Result: `57 passed, 58 subtests passed`; the private HOME was removed by the
command trap.

```text
bash -n literal lifecycle script: pass
literal lifecycle script mode/SHA-256 assertion: pass
uv.lock SHA-256 and replay-control source assertions: pass
second fixed-control wheel/sdist byte comparison: pass
exact frozen runtime and installed identity assertions: pass
documentation/docstring truth assertions: pass
python3 -m compileall -q src/buoy_search: pass
git diff --check: pass
staged files: 0
process survivors: 0
validate_ranking_contract.py: pass
validate_ranking_promotion.py --base-ref HEAD --comparison-mode exact: unchanged authority, pass
c6_syntax_forecast.py validate: pass
```

The first ranking-promotion invocation omitted the mandatory local comparison base and exited with the expected harness-configuration error before validation. It was rerun with explicit `HEAD`/`exact` comparison and passed; ranking defaults are unchanged.

## Documentation

`docs/telemetry.md` now explicitly states that inference duration is caller-observed backend wait, includes worker IPC/startup reached by the request, is not worker-internal CPU time, and must not be added to its parent stage. Current examples use `retrieval_command_runs_v3`, `retrieval_stage_latency_v3`, `retrieval_inference_requests_v3`, and `retrieval_provider_summary_v3`; retained v1 views are explicitly labeled historical/direct-library. Provider examples reiterate that `provider_client_invocation` is not a wire, billing, rate-limit, or SDK-internal-retry unit. The migration section truthfully documents that fixed compatibility key `pending_v2` reports the next-version v3 queue snapshot during v2→v3. It also states that repeat schema-3 migration performs bounded validation/reconciliation and may refresh writer state and remove only recognized validated post-publication scratch; it is not described as a read-only no-op. Producer pipeline and `StoreReconcileResult` docstrings now describe their shared v2/v3 truth.

## Side effects and cleanup

- Turbopuffer/provider/network calls: 0
- Credential reads: 0
- Provider/catalog/content writes: 0
- Model construction/inference/download: 0
- Real telemetry-store opens/mutations/migration: 0
- Staged files/commits/push/release: 0
- Temporary writer survivors: 0
- Retained raw query/provider/telemetry artifacts: 0

`uv` used the explicitly bound standard local cache only as offline artifact transport. The asserted `uv.lock`, frozen hash-bearing export, dependency-free local-wheel install, and asserted installed identity controlled selection. Final artifact hashes were retained above, both deterministic build roots matched byte-for-byte, and every temporary distribution/install/home/run directory was deleted and proved absent.

## Aggregate review repairs

Final review found that migration-v3 database candidates had incorrectly reused
the 16 MiB initialization/WAL cap. The repair removes size caps from valid
migration database and backup candidates while retaining the bounded WAL cap.
Candidate authority now comes from exact private metadata plus canonical
source/schema/history validation and streaming content identity, not an
initialization-size heuristic. Migration copying and validation remain
chunked/trace-streamed; no complete database or history is retained in memory.

The prior test that rejected both an oversized database and WAL was replaced.
A valid exact schema-v2 source is expanded beyond 16 MiB without changing its
validated schema/history, then exercised through crashes at `scratch_validated`
and `backup_published`. Both the >16 MiB migration database candidate and >16
MiB backup candidate/final backup recover to exact schema 3. A separate hostile
WAL above 16 MiB remains untouched and fail-closed. The final two-case focused
check passed on Python 3.13 after the cross-runtime full suites.

Internal migration finalization now uses version-neutral
`next_version_paths`/`next_version_queue` names. The fixed public JSON/text key
`pending_v2` is unchanged. Production-v3 producer docstrings, migration result
comments, user documentation, and `CHANGELOG.md` now describe current behavior.

## Live-validation recommendation and authority ambiguity

Provider-free evidence is sufficient for implementation acceptance: every semantic branch, normalized row, privacy boundary, migration contract, and production-default local artifact is directly exercised. No live provider operation is required to establish code correctness.

Optional live validation remains a user-owned decision because the owner's phrase “up to 20 bounded calls” is ambiguous between CLI retrieval executions and `provider_client_invocation` units:

1. **If the ceiling means CLI retrieve executions:** run exactly one automatic live command, no retry, using the already governed live query contract from `.10x/specs/cross-encoder-worker-three-command-live-ab.md`. It would exercise automatic catalog plus content accounting and a cold worker with later same-command reuse. One command consumes 1/20 command slots, but source permits 6..40,019 Buoy SDK call expressions, so it cannot satisfy a 20-SDK-attempt ceiling.
2. **If the ceiling means Buoy SDK call expressions:** run exactly one explicit-multi live command with exactly two prebound namespaces, no retry. Catalog calls are zero and content is source-bounded to 2..12 `provider_client_invocation` units, within 20. It can exercise embedding-worker spawn plus cross-encoder reuse and content accounting, but it intentionally leaves live automatic-catalog accounting unvalidated.

Either optional case must use a mode-0700 short temporary HOME/telemetry store, prebound read-only existing model caches with offline/no-download controls, credential presence-only preflight and no retention, public retrieve CLI only, provider read methods only, raw stdout/stderr deletion after redacted hash/count reduction, source/cache pre/post equality, complete v3 row/privacy inspection, no provider writes, no retry, and zero worker/writer survivors. The parent directed this child not to choose between those meanings or execute a live call before explicit clarification.

## Residual risks

- Offline replay requires the exact hash-matching distributions and build backends to already exist in the explicitly bound standard uv cache. Missing artifacts fail closed because network and Python downloads remain disabled; cache contents cannot change the asserted lock/export/installed identities.
- No archive nondeterminism remained in the two consecutive fixed-control builds: both wheel and sdist comparisons were byte-identical.
- No real Turbopuffer response traversed the new ordinary telemetry surface in this phase; provider-free fakes and the unchanged governed call sites are the current evidence.
- The owner's existing schema-v2 telemetry database remains unmigrated by design.
- Final aggregate review passed after reproducibility repair. The parent literally reran the retained installed-wheel lifecycle script with identical bounded outputs; see `.10x/reviews/2026-08-29-retrieval-telemetry-v3-integration-review.md`.
