Status: active
Created: 2026-08-28
Updated: 2026-08-28
Supersedes: .10x/decisions/superseded/buoy-uses-private-canary-provider-invocation-receipts.md
Authorization: .10x/evidence/2026-08-28-retrieval-telemetry-v3-authorization.md
Research: .10x/research/2026-08-28-retrieval-telemetry-current-state-and-gaps.md

# Buoy Records Worker and Provider-Attempt Retrieval Telemetry V3

## Context

Retrieval telemetry v2 gives a private command/pipeline stage graph, but the persisted sample predates the default resident inference worker. It cannot distinguish worker from in-process inference, cold start from reuse, or worker failure/fallback. Automatic worker startup and prototype scoring can appear as undifferentiated route-selection time.

Logical namespace and catalog spans are also too coarse for provider diagnosis. Buoy already owns a reviewed private ledger that counts `provider_client_invocation`, one attempt to evaluate a governed provider SDK call expression. The prior decision restricted that ledger to explicitly authorized canaries because v2 was exact and no recurring production contract had been approved. The owner has now approved a strict-private, opt-in v3 surface.

## Decision

Buoy will produce retrieval command observation schema v3 and local telemetry store schema v3.

V3 retains the v2 command/pipeline graph and adds:

1. one governed inference-request span around every command-scoped embedding or cross-encoder invocation, identifying only operation, backend, bounded item count, worker spawn/reuse state when known, primary/fallback role, bounded outcome, and bounded error category;
2. one command-level inference policy distinguishing worker-preferred, explicit in-process opt-out, and compatibility-required in-process execution;
3. one validated provider-accounting summary derived from the existing private ledger, including route-rank-only content attempts and aggregate automatic-catalog attempt categories; and
4. versioned local views for command, stage, inference, and provider-attempt analysis.

A `provider_client_invocation` retains its active meaning: one Buoy SDK call-expression attempt, including local signature rejection and excluding invisible SDK-internal retries. It MUST NOT be labeled a wire send, billed request, or rate-limit unit.

The existing private canary receipt remains available and semantically unchanged. The canary-only decision is superseded only in its prohibition on a separately specified recurring telemetry summary. V3 ordinary telemetry activates the same in-memory accounting solely inside an effective v3 retrieve command and persists only validated content-free fields. Disabled telemetry continues to create no receipt scope or telemetry side effect.

Telemetry remains opt-in only when `BUOY_TELEMETRY=local` and `OTEL_SDK_DISABLED` is not `true`. It remains local DuckDB only and may not export over a network.

The strict privacy boundary remains unchanged. No v3 resource, envelope, queue entry, receipt, state, database value, status output, or diagnostic may retain query text/hash, argv, namespace/corpus/result/provider identity, content, title, citation, URL, local path, vector, credential, header, provider response, raw exception, traceback, ambient OpenTelemetry context, PID, socket identity, worker implementation hash, or model input/output.

Existing v1 and v2 envelopes, queues, tables, and views remain readable and value-equivalent. V3 uses a separate inbox and additive exact schema. Existing stores require an explicit, local, atomic v2-to-v3 migration with a retained fixed v2 backup; producers do not auto-migrate. A fresh store is created directly at v3.

## Alternatives considered

### Keep provider accounting canary-only

Rejected. It would leave ordinary telemetry unable to explain compatibility fallback and catalog/content SDK-call amplification even though a reviewed privacy-safe boundary already exists.

### Instrument SDK HTTP transport

Rejected. It is dependency-version-specific, can expose URL/header/body material, and is unnecessary for the accepted application-boundary unit. Exact wire/cost/rate-limit accounting remains separate research.

### Add fields to v2

Rejected. V2 has exact span names, attributes, envelopes, views, and schema identities. Silent extension would break old-writer rejection, historical meaning, and migration guarantees.

### Enable telemetry by default

Rejected. The owner reaffirmed opt-in local collection and the zero-side-effect disabled invariant.

### Persist query or corpus fingerprints

Rejected. Stable fingerprints create linkability and retention obligations and are unnecessary for worker/provider operational attribution.

### Put telemetry inside the resident worker

Rejected. Provider credentials and command orchestration stay outside the worker, and worker-side persistence would create another writer/privacy/lifecycle surface. Command-side spans and bounded private diagnostics are sufficient.

## Consequences

Current traces can distinguish worker and in-process operations, cold spawn and resident reuse when determinable, and worker-to-in-process fallback without storing model inputs or outputs. Provider attempt rows can explain application-issued catalog/content calls beneath logical spans while remaining honest about transport limits.

The exact envelope, queue, store, migration, and view surface grows substantially. The writer must understand v1/v2/v3 concurrently, preserve old views exactly, and fail closed on incompatible objects. Existing telemetry stores need one explicit migration and a permanent v2 backup unless a future decision adds safe deletion.

The user authorized at most 20 bounded Turbopuffer calls after provider-free tests pass. Implementation should use the smallest lower bound that validates live integration; provider writes and retries beyond the predeclared validation case remain prohibited.
