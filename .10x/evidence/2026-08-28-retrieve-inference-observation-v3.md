Status: recorded
Created: 2026-08-28
Updated: 2026-08-28
Ticket: .10x/tickets/done/2026-08-28-implement-retrieve-inference-observation-v3.md
Spec: .10x/specs/retrieve-inference-telemetry-v3.md
Review: .10x/reviews/2026-08-28-retrieve-inference-observation-v3-review.md

# Retrieve Inference Observation V3 Implementation Evidence

## Scope and activation seam

Implemented the bounded in-memory v3 command/envelope and inference observation milestone. Production `retrieve_command_trace` deliberately remains schema v2 and continues publishing only v2 work until the downstream provider and queue/store/migration children can supply canonical provider accounting and a safe inbox-v3 consumer.

After source inspection revealed that this ticket excluded the distinct v3 queue required for safe publication, the supervisor explicitly directed this milestone to remain in-memory/test-only. No v3 payload is published through inbox-v2, no otherwise-enabled production v2 trace is suppressed, and no v3 queue/store path was added.

The internal `_schema_version=3` command seam is exercised only by tests. Its canonical fixture uses exact unavailable provider accounting solely to complete the test envelope shape. Ordinary commands do not claim that placeholder.

## Implemented behavior

- Added canonical v3 command rows/envelope encode/decode with the retained v2 command/pipeline graph, required inference policy, strict inference span attributes, parent relationships, timing containment, command-wide fallback grammar, cardinality bounds, and content-free unavailable-provider fixture seam.
- Added `buoy.inference.request` around actual encode/score calls for explicit v3 sessions.
- Added worker lifecycle reporting from the worker request path itself: `reused` is established only after validating a compatible greeting, `spawned` only after the launched instance reaches that same contact boundary, and every pre-contact failure remains `unknown`; no post-request filesystem/process probing.
- Added command worker/fallback instrumentation producing failed `worker/primary` followed by `in_process/fallback` without changing the existing one-warning/failure latch. Fallback factory/model construction occurs before the request span; only the actual encode/score call is timed.
- Added in-process embedder/reranker wrappers only when an explicit v3 session is active. Direct v1 and production v2 callers receive the original object unchanged.
- Added inference policy derivation for worker-preferred, forced in-process, and compatibility in-process. Every late identity/capability rejection downgrades the candidate policy to compatibility-in-process, while preview derives policy from established configuration without loading models or spawning/contacting a worker. Current production v2 sanitization ignores the new policy argument.
- Hardened canonical fallback grammar: the first fallback must immediately pair with the failed worker logical request and match its parent, operation, and item count; later command-latched fallback calls may use their independently governed parent/operation/count.
- Routed fresh in-process evidence scoring through the instrumented command reranker so its actual score call is a child of `buoy.evidence.assess`; complete existing scores still produce no synthetic request.
- Preserved direct retriever credential/model construction ordering and current worker protocol, IPC frames, model identity, timeouts, idle lifecycle, ranking, routing, evidence decisions, provider calls, output, and exception behavior.
- Updated the existing provider receipt source audit narrowly to permit the one literal unavailable-v3 fixture unit in `telemetry/envelope.py`; every other telemetry source remains prohibited from provider receipt/accounting activation in this child.

## Changed source and tests

Source:

- `src/buoy_search/telemetry/envelope.py`
- `src/buoy_search/telemetry/producer.py`
- `src/buoy_search/cli/main.py`
- `src/buoy_search/retrieval/embedding_worker.py`
- `src/buoy_search/retrieval/retriever.py`

Tests:

- `tests/telemetry/test_retrieve_inference_telemetry_v3.py` (new)
- `tests/retrieval/test_embedding_worker.py`
- `tests/provider_receipts/test_provider_invocation_receipt_integration.py`

## Provider-free validation

All commands completed without Turbopuffer/provider calls and without opening or mutating the real telemetry store.

1. Python 3.13 focused telemetry/retrieval review-fix suite:

```text
uv run --python 3.13 --with pytest pytest -q tests/telemetry tests/retrieval/test_embedding_worker.py tests/retrieval/test_automatic_routing.py tests/retrieval/test_multi_namespace_retrieval.py tests/retrieval/test_retrieval_evidence.py tests/provider_receipts/test_provider_invocation_receipt_integration.py
387 passed, 403 subtests passed
```

2. Python 3.11 focused changed-path suite:

```text
uv run --isolated --python 3.11 --with pytest pytest -q tests/telemetry/test_retrieve_inference_telemetry_v3.py tests/retrieval/test_embedding_worker.py tests/retrieval/test_automatic_routing.py tests/retrieval/test_multi_namespace_retrieval.py tests/retrieval/test_retrieval_evidence.py tests/telemetry/test_retrieve_command_telemetry.py tests/telemetry/test_telemetry_producer.py tests/telemetry/test_telemetry_v2_storage.py tests/provider_receipts/test_provider_invocation_receipt_integration.py
246 passed, 299 subtests passed
```

3. Python 3.13 full suite after review fixes:

```text
uv run --python 3.13 --with pytest pytest -q
1290 passed, 57 warnings, 1369 subtests passed
```

4. Python 3.11 isolated full suite after review fixes:

```text
uv run --isolated --python 3.11 --with pytest pytest -q
1290 passed, 57 warnings, 1369 subtests passed
```

5. Accepted follow-up review matrix on both runtimes:

```text
uv run --python 3.13 --with pytest pytest -q tests/telemetry/test_retrieve_inference_telemetry_v3.py tests/retrieval/test_embedding_worker.py tests/retrieval/test_automatic_routing.py tests/retrieval/test_multi_namespace_retrieval.py tests/retrieval/test_retrieval_evidence.py
163 passed, 94 subtests passed

uv run --isolated --python 3.11 --with pytest pytest -q tests/telemetry/test_retrieve_inference_telemetry_v3.py tests/retrieval/test_embedding_worker.py tests/retrieval/test_automatic_routing.py tests/retrieval/test_multi_namespace_retrieval.py tests/retrieval/test_retrieval_evidence.py
163 passed, 94 subtests passed
```

6. Static checks:

```text
python compileall over five changed source modules: pass
git diff --check: pass
```

The only warnings were the pre-existing lxml `strip_cdata` deprecation warnings.

## Deterministic coverage

Tests prove:

- first contacted launched worker reports spawned, later compatible contact reports reused, incompatible greeting and launched model failure report unknown, and a post-greeting response failure reports reused;
- an enabled-versus-injected-telemetry-fault matrix at the actual command worker session proves worker success, worker-to-fallback success, and worker-plus-fallback double failure retain exact backend/factory call counts, fallback selection, warning text/output, lifecycle observations, returned-object identity, and fallback-exception identity;
- disabled telemetry does not enter the inference context or register the lifecycle callback;
- fake-clock boundaries place fallback construction before the request start and the backend call within request start/end;
- automatic routing encode/score requests nest beneath route selection, result score beneath rerank, and fresh evidence score beneath evidence assessment;
- complete existing evidence scores invoke neither loader nor inference request;
- worker plus fallback double failure preserves bounded error categories and two error requests;
- exact v3 canonical round trip and acceptance of command-latched later fallback shapes;
- malformed immediate pairs with changed parent, operation, count, or an intervening worker request are rejected only after an independently decodable witness proves each altered span's generic parent/operation/timing validity;
- encode/score item bounds, root/summary policy identity, unknown attributes, invalid state/parent, and unpaired fallback are rejected;
- late identity/capability failures downgrade policy and compatible preview performs no model/process work;
- v1/v2 envelope/store/CLI tests remain passing; and
- exact-byte inspection excludes the full specified query, passage, vector, score, PID, path, custom-model, credential, provider-response, raw-exception, ambient-context, and worker-frame sentinel matrix.

## Side effects and repository state

- Turbopuffer calls: 0
- Provider/catalog/content writes: 0
- Real telemetry store opens/mutations: 0
- Model download/inference: 0 (fake worker tests only)
- Commits/staging/push/release: 0
- Staged files after validation: 0

`uv` created isolated test environments and used dependency caches under its normal test tooling behavior; no project source/cache contract was mutated by model/provider work.

## Residual work and risks

- Production retrieve commands intentionally remain schema v2. The provider child must populate exact v3 provider accounting, and the storage child must add inbox-v3/writer/store/migration support before atomically switching command creation/publication.
- The current v3 provider validator accepts only the exact unavailable fixture. Complete content/catalog authority remains wholly owned by the next child.
- Stable v3 analytical views and request aggregates are not part of this milestone.
- Independent review passed after two repair rounds. Parent-observed focused validation on the reconciled worktree passed with `163 passed, 94 subtests passed`; see `.10x/reviews/2026-08-28-retrieve-inference-observation-v3-review.md`.
