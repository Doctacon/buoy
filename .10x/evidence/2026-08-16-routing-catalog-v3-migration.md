Status: provisional
Created: 2026-08-16
Updated: 2026-08-16
Ticket: .10x/tickets/2026-08-16-migrate-routing-catalog-v3.md
Decision: .10x/decisions/buoy-derives-routing-prototypes-from-reviewed-plans.md
Specification: .10x/specs/automatic-routing-after-apply.md
Release: .10x/tickets/done/2026-08-16-promote-automatic-routing-to-main-once.md
Review: .10x/reviews/2026-08-16-routing-catalog-v3-migration-review.md

# Live Routing Catalog V3 Migration Evidence

## Release and lineage prerequisite

The reviewed automatic-routing implementation reached `develop` at
`7e55f73bb6df428bddd24aa9db80039ba0809923`. The bounded remote-reader float
canonicalization then integrated at
`fc867bebb541f06f116502798a08640df375a3dc`, preserving exact stored hashes and
revisions while accepting provider decimals in the same float32 bucket.

The PR #117 topology repair remained content-neutral and is consumed:
governance integration `034e01c3bb8bfa5726f57bdd5c17c74b7d55dc9f`
led to pre-bridge develop
`f4fcd1c95110222f19826f7966a1e37b174ad82b`; bridge
`2072668d61babe3111056470aff139901950af94` joined that develop with accidental
main squash `0db802ec1a895f289c7600b19c80603986839873`; develop integration
`33e7a52d85ed28a637090cedfa470c5ed9e8196b` retained the exact develop tree;
and closure `4abb931e9a6bd15040287e84dc68bf502e0fea9e` removed the one-time exception.

Release head `4dad7237baf69989b67270a4afb60d3c0444edfc` then merged to `main` through PR
#124 as exact
`R = 4d1efc458fd13b270bf84984ffeb550d5b24fd04`, with ordered parents
`[0db802ec1a895f289c7600b19c80603986839873,
4dad7237baf69989b67270a4afb60d3c0444edfc]` and tree
`a62ac8b774ca66aa4a8ae369daccbe38e0606531`. All seven premerge jobs,
post-main CI, and `Release / Publication paused` passed. The one-time release
authority is consumed and its ticket is done. Current migration-record base /
`origin/develop` is
`31d2a7756c5bd712147772a77b606154fb2610c3`, with sole parent
`4dad7237baf69989b67270a4afb60d3c0444edfc` and tree
`efc512005e3f31f9b26da408473324c35fc15774`.

No bridge or release exception remains active. Neither lineage grants provider
authority; the user's explicit migration request and this executable ticket
provide the narrower preview-first authority.

## Exact installed reader

Read-only local inspection before this record mutation proved:

- sole normal executable `/Users/crlough/.local/bin/buoy` resolves to the
  `buoy-search` uv-tool environment and reports
  `buoy 0.5.2.dev28+g4d1efc458`;
- installed package metadata reports `0.5.2.dev28+g4d1efc458` under CPython
  `3.11.10`;
- installed `buoy_search/remote_catalog.py` has SHA-256
  `9980208230c4743322447b32db75844cfdd2bcb6fc33abda0153d751db8048f1`,
  matching exact-R Git blob
  `27d663ea63edfd01ba82f55c3e5943c71678749c` and the built wheel/source
  archives byte-for-byte for that module;
- installed `buoy_search/catalog_cli.py` has SHA-256
  `4803b57bf9037b026d7ecc3b45b4e6bae9258c96ac13c166f22a7c70a5efb677`,
  matching exact-R Git blob
  `7871cdce67759e1f58c4c5a54197974728b536fe` and the built wheel/source
  archives byte-for-byte for that module;
- installed `turbopuffer` is locked version `2.4.0` with
  `DEFAULT_MAX_RETRIES=4`; installed `_constants.py` has SHA-256
  `3512a85ebc1dc3d3a76139a644cb4c4eb2482068e2b05d1e3ebe8195a570f304`
  and installed `_base_client.py` has SHA-256
  `76cc43f05ee8f265a2b86d5ccd6fed8d94ae7925a427eecf717cea5b7f8eee91`;
  the retry loop permits one initial transport attempt plus four retries and
  reuses one generated retry key internally for a non-GET invocation;
- exact-R wheel
  `buoy_search-0.5.2.dev28+g4d1efc458-py3-none-any.whl` has SHA-256
  `e8e02fd23b2e33469b34e467ef9ae145e144c993f0fa0e16d86df66c6f023210`;
- exact-R source archive
  `buoy_search-0.5.2.dev28+g4d1efc458.tar.gz` has SHA-256
  `2cf485ce9cf098443a0dc90eff176fbb1e88392c4f5bb0c3d260df27b049881f`;
- locked Python 3.11 runtime constraints have SHA-256
  `1a79b1a9691c8a69577714899ee8999bb12c6bc63fdf317031cb1c54050185e9`;
- `buoy catalog migrate-routing-v3 --help` succeeds and exposes only the
  expected snapshot, projection, approval, region, and JSON options;
- read-only environment inspection resolved the nonsecret exact region
  `gcp-us-central1`; no credential value was inspected.

Artifact build, validation, and installation were local prerequisite effects.
They performed no provider request, model inference, catalog/content
operation, publication, tag, or GitHub Release action. This record task did not
read credentials or call the provider. The executor must repeat both
migration-module hashes, installed SDK version/retry constants and hashes,
executable/package identity, and help checks, then re-observe credential
presence privately, record the exact resolved region, and require it to remain
`gcp-us-central1` immediately before the new preview.

## Post-release/pre-v3 diagnostic accounting boundary

Only the enumerated post-release/pre-v3 diagnostics below made no live write.
Their logical SDK accounting must remain divided into these non-combinable
slices:

1. One earlier v3 preview and one conditional v2-prerequisite preview each
   failed safely during a strong read before snapshot binding. Each emitted
   `write_attempted=false`, zero writes/deletes/model inferences, and
   `request_accounting_mode=unknown_partial_read`. The logical SDK request and
   physical transport-attempt counts for each attempt are unknown.
2. A sanitized direct diagnosis isolated one malformed
   `site-www-aurelio-ai-v1` row, but its logical SDK request count and physical
   attempt count were not proven exact and remain unknown. No
   write/delete/model operation occurred.
3. A separate stable two-pass raw audit is the only exact logical-request
   slice: five logical SDK operations total, comprising two namespace-list
   pages, one metadata invocation, and two catalog-query pages. Transport
   retries were not observed, so physical attempts remain unknown. It observed
   exact schema v2, 17 live namespaces, 13 catalog rows, stable sanitized digest
   `0bf681d931f2358b295aac50e1ad7cb597b4e2872080079770e7a0e34d3d2bad`,
   and zero writes/deletes/model inferences.

The Aurelio row had an empty evidence bank and already-correct stored
prototype hash and card revision; no row repair was allowed or performed. Its
failure was harmless provider decimal transport drift now handled by the
installed exact-main float32-canonical reader. The combined logical-request
total and every diagnostic physical-attempt total remain unknown because the
first two slices are unknown and transport retries are hidden. Within these
three diagnostic slices only, writes are exactly zero. Never report the
five-logical-operation audit as the diagnostic total or as physical HTTP
attempts.

These diagnostic slices are not all provider history. Earlier, separately
governed live effects include the initial catalog schema/two-row cutover in
`.10x/evidence/2026-07-18-remote-routing-catalog-live-cutover.md`, the later v2
schema/example sequence governed by
`.10x/tickets/2026-08-15-migrate-routing-catalog-v2-and-examples.md` and
`.10x/evidence/2026-08-15-routing-catalog-v2-migration.md`, and the conditional
Dagster card-row write attempt recorded in
`.10x/evidence/2026-08-15-routing-prototype-float-incident.md`. Other historical
content/provider work also remains outside this task's accounting slice. No
claim that all-history provider writes were zero is made here.

## Pending fresh preview and approval evidence

No new provider request has occurred under this ticket. After these records
integrate, append only sanitized facts from the installed exact-main reader
preview:

- output SHA-256, observed/final/target schema and fingerprints, the exact v3
  additions, snapshot revision, projection SHA-256, counts, coverage, card
  identities, and comparison with the 17/13 historical inventory;
- literal `catalog_namespace=buoy-routing-catalog-v1`, exact nonsecret
  `region=gcp-us-central1`, and `same_resolved_region=true` for any approval;
- `mutation_status`, `write_attempted`, `verification_complete`, affected IDs,
  `operation_budget`, `operations_performed`, `read_metrics`, and every
  `request_summary` category, total, and billing entry; record failure-only
  accounting mode and completeness fields only when emitted;
- credential-presence without the credential value, plus confirmation that no
  raw row, passage, vector, credential, or unsanitized error entered durable
  evidence;
- the independent Preview GO/NO-GO target and verdict.

The preview facts and exact-v2 independent GO must be committed, pushed, and
integrated into `develop` before approval; pending, local, chat-only, or
uncommitted review is not authority. If and only if that durable review returns
GO for exact schema v2, append the exact sanitized bound command shape,
approval-output digest, schema/write/readback result, unchanged
projection/inventory/card/revision proof, and exact or lower-bound logical
request accounting. A v2 success should report two logical strong reads and
one logical SDK schema-write invocation. Emitted request categories count
logical SDK invocations/pages; they do not reveal physical transport attempts.
Under installed `turbopuffer 2.4.0`, each logical invocation is bounded to one
through five physical attempts, and the single non-GET write invocation reuses
one generated retry key internally. A reviewed exact-v3 preview requires no
operation and must record
`no-operation-required`, zero approvals, and zero schema writes.

Snapshot/projection comparison is an optimistic pre-write guard, not an atomic
provider compare-and-swap. Evidence must prove literal catalog namespace
`buoy-routing-catalog-v1`, exact region `gcp-us-central1`, an uninterrupted
mutation freeze, exact pre-write bindings, and exact post-write
unchanged-projection readback.

Any failed or uncertain result after `write_attempted=true` remains recorded
as such and consumes this ticket's single permitted operator/SDK write
invocation, which may already include up to five transport attempts. It
triggers no second approval command, rollback, or operator retry. Any later
attempt requires a fresh preview, new authority, and new independent review.
Do not infer exact accounting where the CLI reports `unknown_partial_read` or
`known_lower_bound`.

## Schema-only and privacy boundary

Exact remote schema v3 is schema v2 plus only these non-filterable fields:

- `routing_passages: []string`;
- `routing_evidence_vectors: []float`;
- `routing_evidence_vectors_hash: string`.

The migration changes schema only. It does not populate these fields, mutate a
card revision, alter routing examples, or backfill any passage/vector bank.
Existing cards remain empty-bank. Future fresh reviewed plan/apply runs can
populate source-derived passages; any historical-card backfill is separately
governed. Because future raw rows can contain excerpts and vectors, durable
evidence must never include raw provider payloads, passages, vectors, or
credentials.

## External effects so far

At this pre-review checkpoint, this task has created only an isolated records
worktree and these three uncommitted records. Read-only Git/ref,
installed-package, artifact-hash, help, source, and lock inspection occurred.
The only remaining effects authorized for this record session are its bounded
commit and task-branch push. No credential was read; no provider request,
schema or row write, model inference, content operation, delete, plan/apply,
backfill, deployment, publication, tag, GitHub Release, protection/ruleset
change, direct/force push, PR, or merge occurred.

Future record phases are append-only. The reviewed preview/GO phase durably
adds sanitized facts before approval. The operation phase appends its result
and review without rewriting prior facts. Final closure alone advances
statuses/verdicts, moves the ticket to
`.10x/tickets/done/2026-08-16-migrate-routing-catalog-v3.md`, changes this
record's and the review's `Ticket:` link to that done path, and integrates the
records-only closure.
