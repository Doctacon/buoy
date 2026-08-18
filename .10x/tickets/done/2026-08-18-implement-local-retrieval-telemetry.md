Status: done
Created: 2026-08-18
Updated: 2026-08-18
Decision: .10x/decisions/buoy-records-opt-in-local-retrieval-telemetry.md
Specification: .10x/specs/local-retrieval-telemetry.md
Evidence: .10x/evidence/2026-08-18-local-retrieval-telemetry.md
Review: .10x/reviews/2026-08-18-local-retrieval-telemetry-review.md

# Implement Local Retrieval Telemetry

## Outcome

Add an opt-in, content-free OpenTelemetry trace for each live retrieval and
persist it as queryable local DuckDB history at
`~/.buoy/telemetry/telemetry.duckdb` without a Collector, cloud destination,
or change to retrieval behavior.

## Owned scope

- Add the OpenTelemetry Python SDK as one runtime dependency and update the
  locked dependency graph.
- Add a private local telemetry module that owns enablement, span allowlists,
  in-memory buffering, context propagation helpers, the DuckDB schema/views,
  private path creation, locking, atomic append, and total failure isolation.
- Instrument live explicit-single, explicit-multi, and automatic retrieval at
  the retriever boundary for embedding, namespace query, reranking, evidence,
  widening, and final outcomes.
- Add focused unit/integration/privacy/concurrency/failure tests.
- Add concise user documentation, changelog entry, governing records,
  evidence, and independent review.

## Required implementation properties

- `BUOY_TELEMETRY=local` is the only enabling Buoy value;
  `OTEL_SDK_DISABLED` remains an overriding standard kill switch.
- Disabled telemetry has zero filesystem/network/output/background effects.
- Enabled telemetry writes only the canonical private DuckDB path after a live
  retrieval, in one nonblocking-lock-guarded transaction.
- The persistence layer enforces exact span/event/attribute allowlists and
  stores no query, content, namespace identifier, path, credential, raw error,
  command argument, vector, or provider payload.
- Automatic exception recording and stack traces are disabled.
- Telemetry failure never changes retrieval behavior or output.
- Executor context propagation preserves one trace tree across namespace
  worker threads.
- Existing certified CLI, routing, evidence, and routing-quality files stay
  byte-identical; automatic pre-retrieval timing is explicitly excluded.
- Existing applied-state databases and local assets are never inspected,
  attached, migrated, rewritten, pruned, or deleted.

## Validation

- focused telemetry/retriever/multi-namespace/automatic-retrieval tests;
- full unittest discovery on Python 3.11 and Python 3.13;
- exact persisted-value privacy scan using adversarial sentinels;
- lock contention, filesystem/schema failure, and original-exception tests;
- certified source-receipt comparison to the exact base;
- `uv lock --check`, in-memory compilation, source/ranking/C6 validators;
- distribution build/inspection and clean-wheel telemetry smoke;
- exact owned-path review and `git diff --check`; and
- independent correctness/privacy/compatibility review before integration.

## External effects boundary

Authorized effects are the isolated `work/local-retrieval-telemetry` branch and
worktree, bounded records/source/tests/docs/dependency changes, local temporary
validation assets, commit, branch push, pull request, and a separate reviewed
squash merge into `develop` as explicitly requested by the owner.

No provider/model/credential operation, remote telemetry export, existing
local-asset mutation, installed-tool replacement, `main` change, release,
publication, tag, GitHub Release, or branch-protection change is authorized.

## Exclusions

Dry-run traces, catalog/route-selection timing, crawl/plan/apply/eval telemetry,
metrics, logs, raw usage history, query fingerprinting, subjective feedback,
Collector configuration, OTLP export, trace UI, cloud backend, retention/purge,
automatic pruning, telemetry CLI commands, provider auto-instrumentation, and
changes to ranking/routing/evidence behavior are excluded.

## Progress

- 2026-08-18: The owner approved the local DuckDB design and explicitly asked
  for implementation and integration into `develop`. Created isolated branch
  `work/local-retrieval-telemetry` from exact `develop`
  `df8b82ee` in `/private/tmp/buoy-local-retrieval-telemetry`.
- 2026-08-18: Implemented the private OpenTelemetry provider, explicitly
  propagated trace parent state, canonical local DuckDB schema/views,
  nonblocking locked atomic sink, retrieval-stage instrumentation, user
  documentation, and adversarial privacy/failure/schema tests. Review probes
  drove repairs for atomic first initialization, ambient-context isolation,
  lazy SDK failure handling, UTC timestamp binding, and non-binding,
  system-qualified schema validation.
- 2026-08-18: The completed worktree passed 21 telemetry tests, 137 combined
  telemetry/retrieval tests, and all 904 tests on both Python 3.11 and 3.13.
  Lock/source/ranking/C6/compile/diff checks passed. Python 3.11 and 3.13
  produced byte-identical validated distributions, and an isolated clean-wheel
  trace persisted the expected analytical rows with private permissions.
- 2026-08-18: Independent exact-commit review passed 21 telemetry tests, 138
  focused tests, all 117 established retrieval tests with telemetry enabled,
  a full 904-test Python 3.11 run, zero-network audit, schema-security probes,
  and exact scope/receipt checks. No correctness, privacy, network,
  failure-isolation, compatibility, or documentation blocker remains.
- 2026-08-18: Implementation commit
  `3a9aa15db39829171d5c9fc74754d48b9629e224`, tree
  `3b58627d4279f48bf9418156bd86f5e6a2ec1de2`, is ready for bounded closure,
  branch publication, exact-head CI, and the separately reviewed squash merge
  into `develop` explicitly requested by the owner.
