Status: active
Created: 2026-08-24
Updated: 2026-08-24
Authorization: .10x/evidence/2026-08-24-provider-invocation-receipt-canary-recovery-authorization.md
Review: .10x/reviews/2026-08-24-provider-invocation-receipt-canary-recovery-authorization-review.md
Original-Decision: .10x/decisions/one-time-live-provider-invocation-receipt-canary.md
Blocked-Predecessor: .10x/tickets/2026-08-24-run-one-time-live-provider-invocation-receipt-canary.md
Predecessor-Failure: .10x/evidence/2026-08-24-provider-invocation-receipt-canary-preflight-failure.md
Recovery-Ticket: .10x/tickets/2026-08-24-recover-one-time-live-provider-invocation-receipt-canary.md

# One-Time Live Provider Invocation Receipt Canary Recovery

## Context

The original one-time canary ticket stopped during candidate preparation after
its one permitted build. Its immutable failure evidence proves that the exact
reviewed wheel was produced, but two wrapper assumptions returned nonzero: the
wrapper treated uv's normal output-directory `.gitignore` as a forbidden
artifact, and a later partial inspector looked for a routing revision at an
unverified generic JSON location. The original ticket is blocked permanently
under its no-rebuild/no-retry preparation contract. No live command began, so
its sole live operation authority remains unconsumed.

The owner has now approved one separately shaped recovery. This recovery does
not resume, reactivate, rewrite, or erase the blocked predecessor and does not
reinterpret its failure as a successful preflight. It exclusively rebinds the
same single unconsumed live-command authority to a new ticket; it does not add a
second command. The reviewed implementation remains exact source commit
`0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`.

## Decision

Authorize `.10x/tickets/2026-08-24-recover-one-time-live-provider-invocation-receipt-canary.md`
to make exactly one fresh offline wheel build and one forward-only preflight
attempt. If and only if that complete preparation passes and an independent
reviewer records **GO** against its exact sanitized preparation evidence and
candidate identities, the same ticket may start exactly one automatic live
retrieval under every unchanged gate of the original decision.

This decision is active authority for a future recovery sequence, but the
recovery ticket is open and inactive. This records-only turn does not activate
preparation, build a wheel, inspect operational state, seek GO, or start the
command.

### Exact candidate and one-build boundary

The recovery MUST use exact reviewed source commit
`0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`. Its one build MUST produce exactly
one wheel with version `0.5.2.dev87+g0b27c4eaa`, size 730602 bytes, 78 safe
members, and SHA-256
`42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87`.
Any mismatch or incomplete validation is permanent recovery failure. There is
no rebuild, corrected inspector rerun, validation retry, alternate source, or
alternate wheel.

Wheel enumeration is independent of output-directory marker enumeration. The
output directory may contain the one expected regular, nonsymlink uv-generated
`.gitignore` beside the one expected regular, nonsymlink wheel and no other
entry; the marker is not a distribution artifact and MUST NOT be included in
the wheel count. A directory without the optional marker is acceptable only if
the one wheel is exact and no other entry exists.

### Exact routing identity

The candidate MUST reproduce routing artifact SHA-256
`79c780a5c3ffebfe5569d463663c30d681cf224aec3ddfb1e03202641b97ed1e`.
Routing authority is checked through the reviewed production loader/validator,
not a newly invented partial parser. The actual schema-v3 paths are top-level
`/schema_version` exactly integer `3`, top-level `/calibration_revision`
exactly `active-anchor-e559a8aa-v1`, the complete top-level `/bindings` object
bound in the recovery ticket, and
`/receipts/cli_module_sha256` exactly
`c6b575e160c5379b8a7214b3434a06d47864f0414e1478f44bcddeff313609ce`.
No generic `/revision`, `/bindings/revision`, or other invented revision path is
valid.

### Forward-only preparation and GO

Preparation is one attempt. A build command start consumes the one fresh-build
authority. Any preparation failure stops this recovery permanently even though
no live command has started. A passing preparation MUST be recorded in bounded,
content-free evidence and independently reviewed against this decision, both
active receipt specifications, the original gates, and the exact candidate.
Only an explicit independent **GO** tied to the exact evidence commit and still-
identical candidate permits the live phase. Silence, a general PASS, partial
review, stale evidence, or candidate drift is not GO.

If GO is denied, unavailable, stale, or qualified, the command MUST NOT start.
Owned temporary artifacts are then cleaned without a rebuild or live operation.
GO grants no repair, replacement, preview, or additional command.

### Preserved live-canary contract

Every original live gate remains unchanged: one isolated install; exact current
model cache/ref/assets including the historical 159-entry manifest SHA-256
`c395f5807452ede94efade87f5be77c0492911e6ac5936a85ce9aaf72ac4263f`;
real telemetry filesystem untouched and inspected only as files without a
store/database open; intended credential-source presence with value privacy;
exact approved case `m01-dagster-turbopuffer-quality` from
`automatic-multi-corpus-retrieval-v1` at SHA-256
`29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`;
exact cached `BAAI/bge-small-en-v1.5` revision
`5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, float32, unchanged production
automatic-device behavior, and enforced offline/no-download operation; current
catalog/content reads only; and no telemetry, provider write, model/cache
mutation, global tool, release, deployment, publication, push, or ref mutation.

After GO, exactly one automatic command may start through the private in-process
receipt scope. Start consumes the sole live authority. There is no preview,
explicit retrieval, substitution, receipt-only rerun, provider retry, or second
command. The original command return/exception/exit outcome remains truthful
and separate from receipt acceptance.

Receipt validation remains post-operation and canonical under both active
specifications. Catalog `invocation_count` MUST be at most 5 and content
`invocation_count` at most 18, with no `error` or `interrupted` operation or
attempt. These are sanitized application-boundary acceptance gates, not wire,
SDK-retry, billing, cost, or rate-limit claims. Missing, invalid, noncanonical,
over-budget, error, interrupted, incomplete, or observer-failed receipt fails
without inference or retry.

Only one fully accepted canonical privacy-safe receipt and bounded content-free
evidence may be retained. Query, argv, namespace/card/catalog/content/result,
credential value, private paths, raw output/errors/stacks, temporary receipt
copies, scripts, source, wheel, runtime, path-bearing manifests, and other raw
artifacts MUST be deleted and absence verified. Failure retains no receipt or
partial ledger. Cleanup never widens into unrelated state.

## Side-effect inventory and provenance

- **Preparation:** one isolated source, one wheel build, one isolated install,
  and provider-free preflight; owner-ratified. No retry or alternate artifact.
- **GO:** independent review of exact sanitized preparation evidence is a hard
  stop gate; owner-ratified. It adds no operation authority.
- **Live command:** the predecessor's one unconsumed automatic command is moved
  exclusively to the recovery ticket; owner-ratified. No duplicate authority.
- **Provider/catalog/content:** current read path only; no writes, repair, or
  management operation; unchanged from the original decision.
- **Model/cache/device:** exact cached revision, float32, production auto-device,
  offline, full manifest unchanged; unchanged from the original decision.
- **Telemetry/store:** disabled and filesystem-identical without database open;
  unchanged from the original decision.
- **Credential/privacy/retention:** intended source only, value never printed or
  persisted, accepted canonical receipt only, raw cleanup; unchanged.
- **Global/release/repository:** no global install, release, deployment,
  publication, push, ref mutation, or unrelated mutation; unchanged.
- **Failure:** any new preparation failure ends recovery permanently; command
  start consumes live authority; every later failure stops without retry.
- **Operational owner:** repository owner, with independent GO and final review
  required by the bounded ticket.

## Alternatives considered

### Resume the blocked predecessor

Rejected. Its one-build/no-retry preparation contract is exhausted, and its
failure evidence must remain immutable and truthful.

### Treat the prior wheel as an accepted candidate

Rejected. Partial checks passed, but the complete preflight ledger did not. The
owner authorized one fresh build rather than post-hoc promotion.

### Suppress uv's `.gitignore` or count every directory entry as an artifact

Rejected. Prior reviewed packaging evidence establishes uv's normal marker.
Artifact enumeration must identify wheel files independently while complete
directory validation still rejects every unapproved entry.

### Add a generic routing revision parser

Rejected. The reviewed artifact is schema v3, has top-level
`calibration_revision`, and already has a strict production loader/validator.
A partial parser would repeat the failed assumption and weaken authority.

## Consequences

The project has one forward-only recovery path and still only one possible live
command. Preparation can fail without provider access and without consuming the
live command, but it cannot be retried. A passing preparation still cannot start
the command until exact independent GO. The original ticket remains blocked and
its failure record remains historical truth.
