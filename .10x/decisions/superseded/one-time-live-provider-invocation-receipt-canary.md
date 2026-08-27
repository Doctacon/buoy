Status: superseded
Created: 2026-08-24
Updated: 2026-08-24
Superseded-By: .10x/decisions/provider-invocation-receipt-live-canary-attempts-are-permanently-stopped.md
Authorization: .10x/evidence/2026-08-24-provider-invocation-probe-and-live-canary-authorization.md
Architecture: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Ticket: .10x/tickets/2026-08-24-run-one-time-live-provider-invocation-receipt-canary.md

# One-Time Live Provider Invocation Receipt Canary

## Context

The owner authorized a private application-boundary receipt because logical
namespace spans cannot prove how many governed Buoy SDK call expressions were
attempted. Active specifications define a default-off private in-process scope,
strict canonical receipt, separate catalog/content families, and unknown
missing-receipt semantics. The fake-only implementation parent and four
children remain open and inactive; no receipt implementation exists yet.

Historical real-store canary and installed telemetry-pilot decisions are
consumed. Their evidence proves useful bounded procedures for exact candidate
identity, private credential loading, offline cached-model operation, pre/post
cache and telemetry-store identities, no retry, content-free retention, and
cleanup. It does not authorize another retrieval. The current owner approval,
recorded at the authorization evidence above, grants a separate future
one-time operation only after fake-only integration passes independent review.

## Decision

Authorize exactly one automatic live retrieval under
`.10x/tickets/2026-08-24-run-one-time-live-provider-invocation-receipt-canary.md`
once every dependency and preflight in that ticket passes and the open ticket is
separately activated.

### Dependency and exact candidate

The canary MUST wait until the fake-only receipt implementation and integration
are complete at one exact commit, all repository validation passes without live
provider/model/store effects, and independent review passes that exact
integrated commit. The canary MUST build one exact wheel from that reviewed
commit in an owner-private isolated temporary source/runtime and MUST prove the
wheel, installed isolated package, dependencies, entry point, receipt source,
CLI receipt, and governing source identities. It MUST NOT install or replace a
global tool, release, deploy, publish, push, or mutate repository refs.

### One automatic live operation

The isolated candidate MUST run exactly one automatic live retrieval through
the specified private in-process receipt scope and receive the canonical bytes
in process after the command operation is terminal. The harness MUST use the
existing intended credential source, the current remote catalog, and the
record-backed approved automatic case `m01-dagster-turbopuffer-quality` loaded
privately at runtime from the exact approved
`automatic-multi-corpus-retrieval-v1` dataset, SHA-256
`29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`.
No query, argv, namespace, catalog/card, content, result, credential, or private
path value enters repository records.

The command begins once. Start consumes the sole live authority. Failure,
interruption, ambiguity, missing receipt, invalid receipt, rejected receipt, or
cleanup/review gap grants no retry, substitution, follow-up retrieval, or
receipt inference.

### Model, telemetry, provider, and store boundary

The operation MUST use exact cached model `BAAI/bge-small-en-v1.5` at revision
`5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, float32, through unchanged
production automatic device selection. Enforced offline/local-only settings,
network policy limited to the authorized provider reads, and complete pre/post
cache root/ref/full-manifest identity MUST prove no download or cache mutation.
No OS/model cache clearing, repair, eviction, or forced device is authorized.

Telemetry MUST be disabled for the harness and child. The real telemetry store,
queue, receipts, backup, writer state, schema, and files MUST remain untouched.
The ticket binds their pre/post content-free filesystem identities without
opening, migrating, flushing, writing, or running telemetry commands.

Provider effects are read-only. The automatic operation MAY perform only the
current strong remote-catalog reads and selected content retrieval reads that
existing source performs. It MUST NOT invoke provider/catalog/card/namespace/
content create, update, upsert, delete, mutation, repair, or management paths.
It MUST NOT change credentials or remote telemetry.

### Receipt acceptance gates

After the automatic operation reaches its original terminal result and after
the private scope finalizes, the harness MUST strict-validate exact canonical
receipt schema version 1 under both active specifications. Acceptance requires:

- `unit` exactly `provider_client_invocation`;
- a valid automatic catalog family with at most 5 application-boundary
  invocations;
- a valid content family with at most 18 application-boundary invocations;
- no catalog or content `error` or `interrupted` operation/attempt;
- exact counts, sequences, source-order grammar, canonical UTF-8 JSON bytes,
  round-trip byte identity, size bound, and privacy contract; and
- a known terminal original command outcome preserved independently of receipt
  acceptance.

The 5/18 budgets are post-operation sanitized-receipt acceptance gates. They do
not preempt the operation, do not constrain or prove physical wire sends, SDK-
internal retries, billing, cost, or rate-limit use, and are not permission to
infer those quantities. A missing, incomplete, observer-failed, malformed,
noncanonical, over-budget, error, or interrupted receipt fails the canary and
means provider-invocation acceptance is unknown or rejected as applicable. The
harness MUST NOT infer zero/counts from source maxima, command success, logical
spans, provider output, or a missing receipt.

Receipt rejection MUST NOT replace, wrap, suppress, rewrite, or report a false
original command result/exception/exit outcome. The evidence records the
content-free original command outcome truthfully and separately from the canary
acceptance verdict.

### Retention, cleanup, and privacy

Only one canonical validated sanitized receipt that satisfies every acceptance
gate may be retained indefinitely, together with bounded content-free evidence:
exact candidate/runtime/host/model/cache/store identities, generic original
command outcome, generic acceptance/cleanup outcomes, process/effect inventory,
and review references. If no receipt passes, no receipt or partial ledger is
retained.

After durable sanitized evidence exists, delete and verify absence of the query,
argv, namespaces, catalog/card values, content, result, credential material,
private paths, raw stdout/stderr, errors/stacks, temporary receipt copies,
harness/scripts, source copy, wheel, isolated runtime, manifests containing
paths, and all raw analysis/runtime artifacts. The credential value MUST never
be printed, copied into arguments, logged, or persisted. Records and retained
receipt MUST satisfy the active receipt privacy contract.

## Failure and consumption boundaries

- Any dependency, exact-commit review, candidate, dataset, credential-source,
  offline/cache, telemetry-store, process, provider-write-denial, privacy, or
  side-effect preflight failure stops before the command and consumes no live
  authority.
- Command start consumes the sole operation authority. Every terminal/nonterminal
  failure after start stops without retry. There is no replacement case,
  receipt-only rerun, provider retry, telemetry operation, or repair authority.
- If the command raises or is interrupted, the harness preserves that exact
  original outcome, finalizes best effort as specified, and fails the canary;
  it performs cleanup but no second command.
- Missing/invalid/over-budget/error/interrupted receipt fails after operation
  without changing the command's truthful outcome and without inferring calls.
- Uncertain process termination or external side effect is a failed canary and
  must be escalated; it does not grant retry or unrelated cleanup authority.
- This decision remains active only while its single operation authority is
  unconsumed. After execution it MUST be superseded by consumption, whether the
  canary passes or fails.

## Supersession and consumed authority

The original preparation activation and its one permitted build were consumed
when candidate validation returned nonzero. The ticket stopped before a live
command and was later given one separately ratified recovery successor. That
successor also consumed its preparation activation and one permitted build,
then stopped before a live command. Current owner-ratified terminal disposition
is recorded at
`.10x/decisions/provider-invocation-receipt-live-canary-attempts-are-permanently-stopped.md`.
This one-time decision is historical provenance only and grants no preparation,
validation, investigation, recovery, GO, live command, or retry authority.

## Side-effect inventory and provenance

- **State transition:** one isolated candidate process and one automatic live
  retrieval; user-ratified. No production installation or repository mutation.
- **Provider/catalog/content:** current catalog and selected content reads only;
  user-ratified. No writes or management operations.
- **Receipt:** one private in-process terminal receipt may be produced and only
  a fully validated accepted canonical receipt retained; user-ratified and
  specification-backed.
- **Telemetry/store:** telemetry disabled; real store/queue/backup/writer/schema
  untouched and byte/manifest-identical pre/post; user-ratified.
- **Model/cache/device:** exact cached revision, float32, production auto-device,
  offline/no download, cache identity unchanged; user-ratified.
- **Credential:** existing intended source loaded privately only at runtime;
  value never printed or persisted; user-ratified and prior-procedure-backed.
- **Process/filesystem:** owner-private wheel/runtime/harness/raw artifacts are
  temporary and removed; accepted canonical receipt plus bounded evidence are
  the only retained artifacts; user-ratified.
- **Recipients/cadence:** no telemetry or receipt recipient and no recurrence;
  one-time local evidence only; user-ratified.
- **Failure/retry/escalation:** forward-only, no retry after command start;
  generic failure reported to the owner; user-ratified.
- **Money/security/privacy:** read operation may have provider-side effects
  unknown to this application-boundary receipt; no billing/rate-limit/transport
  claim. Exact privacy and credential limits are user-ratified.
- **Launch authority:** current owner approval is durable at the linked evidence;
  separate ticket activation remains required after reviewed integration.
- **Operational owner:** repository owner; exact execution delegated under the
  bounded ticket and subject to independent review.

## Alternatives considered

### Treat fake-only validation as sufficient

Rejected. Fakes prove instrumentation grammar and isolation but not that one
real automatic command yields an authoritative receipt under current catalog
and provider behavior.

### Extend telemetry v2 or write the receipt automatically

Rejected. The active receipt architecture is intentionally private,
default-off, and independent of telemetry v2. Persistence would add schema,
path, retention, and accidental enablement obligations.

### Use the global tool or release first

Rejected. An exact isolated wheel from the independently reviewed integration
commit is sufficient and avoids global installation, release, rollback, and
version-drift effects.

### Retry a missing or over-budget receipt

Rejected. Retrying would add provider effects and bias evidence. Missing receipt
is unknown, and the budgets are post-operation acceptance gates rather than
pre-operation wire limits.

## Consequences

A passing canary can retain one content-free canonical application-boundary
receipt proving the governed Buoy SDK call attempts for one exact automatic live
operation. It cannot prove physical sends, SDK retries, cost, billing, or
rate-limit use. A failure remains truthful, consumes the one-time operation if
started, and produces no retry authority.

The implementation parent and all four fake-only children remain the immediate
work. This decision does not activate them or this canary ticket. No live
operation may occur in the same records-only turn that creates this authority.
