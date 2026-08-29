Status: recorded
Created: 2026-08-28
Updated: 2026-08-28
Ticket: .10x/tickets/done/2026-08-28-integrate-provider-accounting-into-telemetry-v3.md
Spec: .10x/specs/retrieve-provider-invocation-telemetry-v3.md
Review: .10x/reviews/2026-08-28-retrieve-provider-invocation-telemetry-v3-review.md

# Retrieve Provider Invocation Telemetry V3 Implementation Evidence

## Scope and activation seam

Implemented provider accounting for the explicit internal schema-v3 command session. Production retrieve command creation/publication remains schema v2 until inbox-v3/writer/store/migration support exists; no v3 payload is published through inbox-v2 and no enabled v2 observation is suppressed.

An effective internal v3 command enters exactly one existing private provider-receipt scope after trace setup and before the command body can reach catalog/content provider expressions. The scope exits and seals after command provider work is terminal. The producer then maps canonical receipt bytes to exact v3 provider fields. Disabled telemetry, v2 commands, nested command traces, setup failure, and direct v1 retrieval do not activate this surface.

## Implemented behavior

- Added command-scoped receipt lifecycle activation only for effective schema v3.
- Preserved original body return/exception identity while sealing on normal and exceptional command exits.
- Added failure-isolated `bytes | None` handoff and exact `complete|unavailable` mapping. Missing, malformed, noncanonical, observer-failed, and nested-disabled receipts become unavailable with null families, never authoritative zero.
- Replaced the unavailable-only envelope fixture validator with independent exact content/catalog validation: keys, types, enums, booleans-as-integers rejection, contiguous route/attempt order, server/client fallback grammar, outcome/error agreement, content bounds, catalog category counts, aggregate totals, source order, terminal composition, 40,001 success, and exact 40,002 terminal reachability.
- Added post-graph provider reconciliation: complete content operations must exactly match the validated pipeline final fanout and namespace route-rank set; a namespace success requires provider success while a namespace failure may retain provider success when failure occurred after the SDK expression; commands without a pipeline require zero content operations.
- Added catalog reach reconciliation: explicit modes prohibit catalog work; automatic accounting may be non-null only when the validated command graph contains the routing-catalog span; an OK catalog span requires provider success, while an ERROR span permits zero attempts before the first SDK expression or a completed provider outcome followed by local failure.
- Kept provider accounting as non-timed envelope data. No synthetic per-attempt spans or timestamps were added.
- Thread-worker lease propagation, capability-explicit catalog observation, provider SDK calls, compatibility/pagination behavior, existing private canary receipts, and v1/v2 envelope semantics remain unchanged.
- Passed provider accounting to the dormant persistence seam for the downstream storage child; v3 persistence remains intentionally disabled.

## Changed source and tests

Source:

- `src/buoy_search/telemetry/envelope.py`
- `src/buoy_search/telemetry/producer.py`

Tests:

- `tests/telemetry/test_retrieve_provider_telemetry_v3.py` (new)
- `tests/telemetry/test_retrieve_inference_telemetry_v3.py`
- `tests/provider_receipts/test_provider_invocation_receipt_integration.py`

## Deterministic provider-free coverage

Tests prove:

- explicit preview produces authoritative complete zero content/catalog accounting;
- live explicit server-RRF compatibility fallback preserves one route and exact failed-server/successful-client attempts;
- minimum automatic preview catalog read preserves two list, one metadata, and two card calls as five attempts;
- six-attempt content grammar, 40,001 successful catalog maximum, exact 40,002 all-success terminal maximum, and invalid successful 40,002 classification;
- invalid UTF-8/JSON/canonical shape, duplicate keys, wrong unit/schema, boolean counts, mismatched totals, impossible source order, overflow, mixed terminal calls, and preview/content mismatch reject or downgrade as governed;
- disabled, v2, and direct-v1 paths never enter the receipt scope;
- a nested preexisting canary remains authoritative while the nested v3 accounting is unavailable;
- command exceptions propagate as the identical object after a complete receipt seals;
- complete canonical envelope round-trip and full command graph validation; and
- explicit-single, explicit-multi, and automatic content count/rank/fanout contradictions reject after otherwise-valid graph construction;
- failed-before-catalog automatic commands reject fabricated catalog reach, while failure inside the catalog stage before an SDK expression retains complete authoritative zero;
- partial multi-route envelopes reconcile provider terminal errors with failed namespace spans while preserving the valid provider-success/namespace-failure post-expression case; and
- a provider-free fake receives prohibited query, provider-response, raw-error, cursor, header, credential, and ambient-context sentinels through governed `_invoke` callbacks, after which receipt mapping and canonical v3 encoding exclude every sentinel.

The existing provider-receipt suites continue to cover concurrent route ordering, optional-schema call sites, pagination, cancellation/control-flow classification, observer faults, worker leases, exact canonical receipt bytes, and capability isolation.

## Validation

Python 3.13 focused integrated suite:

```text
uv run --python 3.13 --with pytest pytest -q tests/telemetry/test_retrieve_provider_telemetry_v3.py tests/telemetry/test_retrieve_inference_telemetry_v3.py tests/provider_receipts tests/retrieval/test_embedding_worker.py tests/retrieval/test_automatic_routing.py tests/retrieval/test_multi_namespace_retrieval.py tests/retrieval/test_retrieval_evidence.py
266 passed, 263 subtests passed
```

Python 3.11 isolated changed-path suite:

```text
uv run --isolated --python 3.11 --with pytest pytest -q tests/telemetry/test_retrieve_provider_telemetry_v3.py tests/telemetry/test_retrieve_inference_telemetry_v3.py tests/provider_receipts tests/retrieval/test_embedding_worker.py tests/retrieval/test_automatic_routing.py tests/retrieval/test_multi_namespace_retrieval.py tests/retrieval/test_retrieval_evidence.py
266 passed, 263 subtests passed
```

Full suites after final changes:

```text
Python 3.13: 1302 passed, 57 warnings, 1394 subtests passed
Python 3.11 isolated: 1302 passed, 57 warnings, 1394 subtests passed
```

The 57 warnings are the pre-existing lxml `strip_cdata` deprecation warnings.

Static validation:

```text
python3 -m compileall: pass
git diff --check: pass
staged diff: empty
```

## Side effects

- Turbopuffer/provider/network calls: 0
- Provider/catalog/content writes: 0
- Real telemetry store opens/mutations: 0
- Model download/inference: 0
- Commits/staging/push/release: 0

`uv` created isolated dependency environments under its normal test behavior.

## Residual work and risks

- Inbox-v3, writer/store schema v3, migration, normalized tables/views, status/flush, and production command activation remain owned by the downstream storage/integration tickets.
- The normalized storage transaction and analytical views have not yet consumed these persistence-ready provider fields.
- Independent acceptance review passed after the cross-graph and privacy-test repairs. Parent-observed validation passed with `39 passed, 62 subtests passed`; see `.10x/reviews/2026-08-28-retrieve-provider-invocation-telemetry-v3-review.md`.
