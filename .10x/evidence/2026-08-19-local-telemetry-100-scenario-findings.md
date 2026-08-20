Status: recorded
Created: 2026-08-19
Updated: 2026-08-19
Decision: .10x/decisions/buoy-records-opt-in-local-retrieval-telemetry.md
Subject: develop@3787e0eabd2720732fb5c68ca168f926342ae454

# Local Telemetry 100-Scenario Diagnostic Findings

## Evidence class

This was an owner-requested diagnostic campaign over the completed direct-
DuckDB telemetry slice. It was not preregistered as a release gate and is not
retroactively represented as governed acceptance evidence. Its results are a
durable design input for the private local writer ticket.

All scenarios used isolated temporary homes. They did not read or change the
real `~/.buoy`, installed Buoy tool, credentials, providers, models,
namespaces, catalog/content state, or network telemetry destination. The exact
subject tree remained clean.

## Matrix and result

The campaign comprised 30 functional/correctness scenarios, 35 privacy and
resilience scenarios, and 35 paired performance/storage scenarios: 100 total.
All scenario assertions passed after one documented test-harness ordering
assertion was corrected and the full affected matrix reran cleanly.

- Functional/correctness: 30/30 passed.
- Privacy/resilience: 35/35 passed.
- Performance/storage equivalence: 35/35 paired retrieval results or errors
  matched exactly.
- The performance track persisted 34 expected traces. One held-lock scenario
  intentionally exercised the documented nonblocking drop, and the following
  scenario recovered normally.

Sensitive sentinels for query, namespace, model path, content, URL, local
path, identifiers, tags, credentials, argv, raw errors, and unrelated
`ContextVar` values were absent from the governed database rows. Ambient
OpenTelemetry context stayed separate; hostile filesystem/schema fixtures
failed closed; injected sink/transaction failures preserved retrieval; and
database graph integrity held.

## Material findings

The direct sink had two operational limits:

1. Synchronized writers were intentionally lossy. Twelve successful thread
   retrievals persisted one trace, and eight successful process retrievals
   persisted one trace, because database-lock acquisition used zero wait.
2. Same-process persisted overhead was p50 30.364 ms, p95 34.711 ms, and p99
   37.808 ms, but the first enabled append in a fresh process paid the first
   Python parameter-binding cost. A warmed persistent environment measured
   about 0.9--1.0 seconds; first environment use measured 11--16.6 seconds.
   The dominant statement was the first parameterized
   `system.duckdb_columns()` schema query, not OpenTelemetry span creation.

The final performance database contained 34 traces, 171 spans, and 7 events
and remained schema-valid. These measurements motivate moving DuckDB work out
of the short-lived retrieval path and replacing lock-loss with a bounded
durable local handoff.

## Artifact identities

The temporary campaign artifacts were intentionally outside the repository.
Their content identities were recorded at completion:

- functional result JSON SHA-256:
  `5d045ad3e8984574e545ed7a9cad0a71658913fd399d3c796fb8a6ed15e2cd23`;
- privacy/resilience result JSON SHA-256:
  `8f810b232f69302477c932376acb3f8a74b04b6ef31a6093912f9e2e24b04d99`;
- performance report SHA-256:
  `d1f07c92fe77cdad6d7cc10ac90d65962240b2776765017047904669802d70a5`;
- cold-diagnostic JSON SHA-256:
  `1fc03674a58da3fdc3cf052b8f5cda239d1f3c1ad4f543d5c2bceb01db00dfeb`;
  and
- consolidated report SHA-256:
  `fea372b3deed995d7bc5ff12ecb24b7b9395427302d00247b4cfa32c35e1cf7d`.

The hashes establish identity, not long-term artifact availability. This
record therefore preserves the decision-relevant aggregate results and states
their limitations directly.
