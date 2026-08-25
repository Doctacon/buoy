Status: active
Created: 2026-08-24
Updated: 2026-08-24
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Authorization: .10x/evidence/2026-08-24-provider-client-invocation-receipt-authorization.md
Prior-Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-review.md
Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md

# Private Canary Provider Client Invocation Receipt

## Purpose and scope

This specification defines the private activation, concurrency, finalization,
exact receipt envelope, validation, serialization handoff, authority, privacy,
and retention lifecycle for canary-only `provider_client_invocation` evidence.
The governed unit, call sites, outcomes, categories, and family objects are
owned by `.10x/specs/provider-client-invocation-accounting.md`.

This receipt is independent of active telemetry v2. It MUST NOT alter or extend
v2 spans, envelopes, queues, DuckDB schema/views, enablement, status, flush,
migration, or retention.

## Terminal authority

A **terminal receipt** is canonical validated JSON bytes returned in process by
a successfully finalized private scope. Missing, incomplete, observer-failed,
invalid, or process-killed state is **unknown**, never zero and never inferred
from logical spans or source maxima.

A zero-count receipt is authoritative only when an explicitly authorized
harness knows the scoped operation reached its terminal result and successful
finalization proves that no governed call or worker remained in flight.
Validator maxima are reachability/safety limits, not authorization or an
operational call budget. Every live canary requires separate explicit authority
for its provider/model/catalog/content operations and budget.

## Private activation interface

Implementation MUST provide one internal, underscore-prefixed context-manager
scope and MUST NOT export it from the package public API. The authorized harness
uses this lifecycle:

```text
with private_receipt_scope() as handle:
    terminal command operation runs
receipt_bytes = handle.receipt()
```

`handle.receipt()` returns `bytes | None`, is callable only after scope exit,
and returns the same immutable canonical bytes on repeated calls. Before exit,
or when authority cannot be proved, it returns null. There is no partial-ledger
or mutable receipt API.

Activation is default-off and possible only by an explicit in-process call to
the private scope. There MUST be no CLI flag, environment trigger, public API,
automatic canary, import-time activation, process-global installation,
automatic filesystem write, telemetry publication, database write, or network
export. When no private scope is active, governed wrappers call their original
expressions without allocating a ledger or serializing a receipt.

The scope MAY expose one internal private catalog-observer capability bound to
its ledger. Merely activating the scope MUST NOT make shared remote-catalog
helpers consult the `ContextVar`. Only automatic retrieve's CLI branch may
obtain and explicitly pass that capability to `read_remote_catalog`; the
reader/helper argument defaults to `None`. Apply, catalog-management, and direct
callers remain unobserved even inside an active scope. This capability is not a
callback API and MUST NOT be retained or accepted after ledger sealing.

Observer allocation or activation failure yields a disabled handle, runs the
body unchanged, and returns null. Scope exit detaches activation and attempts
finalization without swallowing, replacing, or delaying propagation of the
body's return or exception. A harness that needs a receipt for a raised command
exception catches that original exception outside the scope and then reads the
handle.

## Nested and independent scopes

The active ledger is held in a receipt-private `ContextVar`; it MUST NOT reuse
or install OpenTelemetry's current provider/span/context and MUST NOT capture
ambient context, baggage, credentials, or unrelated `ContextVar` state.

A scope entered while another receipt scope is active in the same context is a
no-op nested scope. It MUST NOT replace, split, finalize, or disable the outer
ledger. Governed calls remain attributed to the outer scope; the nested handle
always returns null. Nested setup/read failure MUST NOT affect the outer scope
or the body.

Top-level scopes in distinct contexts are independent and MUST own separate
ledgers. Reset after worker execution and scope exit MUST prevent state leakage
when a thread later serves another context.

## Explicit worker propagation and leases

The implementation MUST follow the existing Buoy private-context callable seam,
but propagate only the receipt ledger in addition to the separately governed
telemetry state. It MUST NOT use a general context copy.

A propagation lease is registered against the active ledger before a namespace
worker is submitted and is released after its callback returns or raises. The
worker temporarily binds only that ledger and restores the prior receipt
context in `finally`. Calls in unpropagated workers are not observed. If
submission fails, a callback never runs, binding/reset fails, or a lease cannot
be released, the ledger becomes incomplete and no receipt is returned; retrieval
behavior is unchanged.

The ledger MUST be thread-safe. Per-route attempt indexes are assigned atomically
and remain contiguous. Concurrent routes may interleave in memory, but receipt
serialization sorts operations and attempts by the rules in the accounting
specification.

## In-flight calls, operation completion, and sealing

Before each governed expression, the ledger atomically registers the attempt
and increments its in-flight count. Return or raise atomically records the
attempt outcome and decrements that count. Logical content and catalog
operations are likewise registered when their existing source boundary begins
and marked terminal in `finally`-equivalent handling without changing the
original result or exception.

On top-level scope exit, finalization MUST NOT wait, join, retry, cancel, or
alter work. It seals successfully only when all of these are true:

- activation and observer state remain healthy;
- every begun logical operation has a terminal outcome;
- in-flight attempt count is zero;
- propagation lease count is zero;
- no update occurred after sealing;
- content and catalog family validation succeeds; and
- canonical encode/decode validation succeeds.

Premature exit, late use, duplicate completion, overflow, lock/synchronization
failure, worker leakage, or any invariant violation permanently makes that
scope's receipt unavailable. Calls and retrieval continue unchanged.

## Exact receipt object and canonical serialization

The top-level object keys are exactly:

```text
receipt_schema_version   integer exactly 1
unit                     string exactly provider_client_invocation
content                  exact content object from the accounting spec
catalog                  exact catalog object from the accounting spec
```

Unknown or missing keys, duplicate keys, booleans where integers are required,
negative or non-finite numbers, bad enums, invalid UTF-8, inconsistent totals,
out-of-bound arrays/counters, or noncanonical bytes are invalid.

Canonical JSON is UTF-8 with sorted object keys, compact separators, no NaN or
infinity, and a maximum of 65,536 bytes. Finalization MUST build an immutable
model, validate it, canonical-encode it, strict-decode the bytes, revalidate the
same value, and expose bytes only if re-encoding is byte-identical. Decoder and
encoder accept no extension object or payload-selected path.

Serialization/handoff failure returns null. Production code MUST NOT choose a
path, create a directory, or write the bytes. Only the explicitly authorized
harness receives them in process.

## Privacy contract

Every ledger value, immutable model, canonical byte string, validator error,
test fixture, harness handoff, and retained evidence receipt MUST exclude:

- query text or hash, argv, executable name/path, or environment value;
- namespace, source, site, document, row, card, provider, model, or account
  identifier;
- content, title, excerpt, citation, URL, tag, repository/local path, vector,
  cursor, request/response payload, billing payload, credential, token, key, or
  header;
- raw exception/message/status, class/module name, traceback, or stack;
- timestamp/duration, trace/span ID, thread/process ID, ambient telemetry
  resource/context/baggage/link, or unrelated context state.

The only content identity is route rank. The only catalog identity is the three
fixed aggregate categories. Validators and tests MUST use fixed generic reasons
for invalid data and MUST NOT echo rejected values.

## Observer failure isolation

Allocation, activation, context access, propagation, locking, registration,
counting, completion, finalization, validation, encoding, decoding, or handoff
failure MUST return null and MUST NOT change:

- SDK call count, order, arguments, or fallback/pagination behavior;
- result or exception-object identity, traceback propagation, cancellation,
  worker submission, routing, ranking, evidence, output, or exit behavior;
- existing telemetry graph, timing boundaries, persistence, or enablement; or
- provider, model, catalog, content, filesystem, database, network, credential,
  release, or global-tool behavior.

Observer failures emit no stdout/stderr, telemetry, diagnostic callback,
automatic file, or network activity.

## Receipt retention and raw-artifact deletion

Only canonical bytes that pass the full validator and are bound by separate
durable canary evidence to a known terminal command result may be retained.
That sanitized receipt may be retained indefinitely with the evidence record.
The authorized harness MUST delete raw runtime logs, temporary captures, and
other raw canary artifacts after the evidence is recorded.

Buoy production code performs no retention or deletion operation under this
contract. Recurring production telemetry retention/purge behavior is unchanged.
No receipt is automatically written to telemetry storage or any other path.

## Acceptance scenarios

1. Disabled/default-off scope preserves exact body/call/result/exception behavior
   and produces no ledger, bytes, filesystem, telemetry, or network side effect.
2. An active empty top-level scope with a known terminal body produces one valid
   zero-count receipt; reading before exit returns null.
3. A nested scope returns null while all governed calls remain on the outer
   ledger; independent concurrent top-level contexts remain isolated.
4. Explicitly propagated concurrent workers produce deterministic canonical
   ordering; unpropagated or never-run workers cannot yield an authoritative
   receipt.
5. Focused classification tests prove both standard cancellation classes,
   named control-flow exceptions, a custom non-`Exception` `BaseException`, and
   representative ordinary exceptions have exact interrupted/error precedence
   and re-raise the identical object.
6. Normal return, body error, observer failure, premature exit, late call,
   process-incomplete simulation, overflow, and every injected synchronization/
   serialization fault preserve original behavior and return bytes only when
   terminal authority is complete.
7. An active scope alone observes no shared catalog read; only an explicitly
   passed live private capability records automatic retrieve, and a sealed or
   invalid capability yields no receipt without changing the read.
8. Strict decode rejects unknown/missing/duplicate keys, wrong types/enums,
   inconsistent totals, invalid sequence/outcome, conditional-bound overflow,
   invalid UTF-8, noncanonical bytes, and prohibited-data sentinels without
   echoing them.
9. Canonical round-trip and privacy tests inspect exact bytes and require no
   provider/network access, credential, model asset, telemetry store, database,
   filesystem persistence, or global tool state.

## Explicit exclusions

Public API/callback, CLI or environment enablement, recurring production
telemetry, telemetry-v2 extension, automatic disk write, database/store,
migration, production retention/purge change, wire/cost/rate-limit claim,
provider/model/catalog/content operation, live canary, release, and global-tool
behavior are excluded.
