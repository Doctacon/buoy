Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/decisions/one-time-live-provider-invocation-receipt-canary-recovery.md, .10x/tickets/2026-08-24-recover-one-time-live-provider-invocation-receipt-canary.md, .10x/tickets/2026-08-24-run-one-time-live-provider-invocation-receipt-canary.md, .10x/evidence/2026-08-24-provider-invocation-receipt-canary-preflight-failure.md
Review: .10x/reviews/2026-08-24-provider-invocation-receipt-canary-recovery-authorization-review.md

# Provider Invocation Receipt Canary Recovery Authorization

## What was observed

The owner explicitly approved one separately shaped recovery for the blocked
one-time provider-invocation receipt canary. The approval authorizes records in
this turn, not activation or execution. It preserves the predecessor as blocked
and its failure evidence as immutable while assigning one fresh build/preflight
attempt and the same single unconsumed live-command authority to a new ticket.

## Exact current owner approval

The current instruction states exactly:

> Create a new active one-time recovery decision, focused authorization evidence quoting the exact current approval, and one bounded open/inactive recovery ticket. Keep the original canary ticket blocked and its failure evidence immutable; do not pretend it resumed. The new ticket owns exactly one fresh build/preflight attempt and, only after independent GO, the same single live command authority. Bind exact reviewed source 0b27c4eaa2449493125f4040af3cd1f7c926b531/tree 9017c4a335938faca80cdded54545df8b79c12f8, exact expected wheel version 0.5.2.dev87+g0b27c4eaa, size 730602, 78 members and SHA-256 42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87. The fresh build may run once only and must reproduce all identities; no rebuild/retry.
>
> Correct only the two false preflight assumptions: the output directory may contain exactly one expected regular uv-generated .gitignore beside exactly one wheel, and no other entry; enumerate/validate the wheel independently rather than count the marker as an artifact. Routing identity must use the full reviewed artifact hash plus actual schema-v3 paths: top-level schema_version exactly 3, calibration_revision exactly active-anchor-e559a8aa-v1, exact full bindings object from reviewed artifact, and receipts.cli_module_sha256 exactly c6b575e160c5379b8a7214b3434a06d47864f0414e1478f44bcddeff313609ce; prohibit any invented generic revision path. Require use of the already reviewed routing/package validators where possible rather than a new partial parser.
>
> Preserve every original live-canary gate unchanged: isolated install, current cache/ref/assets including historical 159-entry digest, untouched telemetry filesystem without DB open, credential-source presence/value privacy, exact approved case/dataset digest, one automatic command only, no retry, read-only provider, offline exact model/auto-device, catalog<=5/content<=18 post-operation receipt gates, canonical receipt privacy/retention, original outcome truth, raw cleanup, no global/release/ref mutation. A new prep failure stops permanently; command start consumes the sole live authority. The new ticket must not activate or execute in this records-only turn and must depend on done integration plus reference the blocked predecessor/failure. Update graph references minimally. Commit a records-only candidate, validate paths/status/privacy and return RECOVERY-AUTH-CANDIDATE with commit/tree/changed paths.

The instruction also explicitly prohibited this turn from modifying source/tests
or running build, install, model, credential, provider, network, telemetry,
store, or global operations.

## Record-backed identity and procedure facts

Read-only inspection confirmed:

- done integration source commit
  `0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
  `9017c4a335938faca80cdded54545df8b79c12f8`, passed independent review in
  `.10x/reviews/2026-08-24-provider-invocation-receipt-integration-review.md`;
- exact integration closure evidence at
  `.10x/evidence/2026-08-24-provider-invocation-receipt-integration-closure.md`
  binds the 730602-byte, 78-member wheel and SHA-256
  `42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87`;
- the reviewed routing artifact SHA-256 is
  `79c780a5c3ffebfe5569d463663c30d681cf224aec3ddfb1e03202641b97ed1e`,
  and its actual schema-v3 structure uses top-level `schema_version`, top-level
  `calibration_revision`, top-level `bindings`, and
  `receipts.cli_module_sha256`;
- the reviewed production `load_routing_confidence_calibration` path performs
  strict field, binding, active-authority, and source-receipt validation and is
  the primary routing validator for recovery;
- prior package evidence at
  `.10x/evidence/2026-07-19-remove-buoy-v0-4-environment-aliases.md`,
  `.10x/evidence/2026-07-15-buoy-v0-3-0-preparation.md`, and
  `.10x/evidence/2026-08-23-stale-ci-release-automation-call-reconciliation.md`
  establishes that uv may generate an output-directory `.gitignore`, which is
  not a distribution artifact and must be excluded from artifact enumeration;
  and
- historical pilot evidence binds the exact 159-entry model-cache manifest at
  SHA-256
  `c395f5807452ede94efade87f5be77c0492911e6ac5936a85ce9aaf72ac4263f`.

## Authorized records-only scope

Authorized now:

- create this focused authorization evidence;
- create one active recovery decision and one bounded open/inactive ticket;
- add only a minimal successor reference and truthful append-only note to the
  blocked predecessor ticket;
- perform read-only source/record/Git inspection and records-only validation;
  and
- commit the bounded records-only candidate for independent review.

Not authorized now:

- activate either preparation or the live phase;
- run a build, install, package test, model/cache operation, credential read,
  provider/network operation, telemetry/store/database operation, or global
  operation;
- modify source, tests, specifications, the original decision, or immutable
  preflight failure evidence; or
- create a wheel, runtime, harness, receipt, raw operational log, release,
  deployment, publication, push, or ref mutation.

## What this supports

This supports the authority and exact contract of the recovery decision/ticket
and the records-only candidate. It supports no claim that preparation passed,
GO was issued, a candidate currently exists, a cache/store identity was checked,
a credential was read, a provider call occurred, or a receipt exists.

## Limits

The recovery remains open and inactive. Independent review of this records
candidate is still required. Future preparation has one attempt only; any
failure ends the recovery. Even a passing preparation cannot start the live
command without exact independent GO. The original canary remains blocked, its
failure remains truthful, and there is still at most one live command authority.
