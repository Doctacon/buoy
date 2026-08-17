Status: recorded
Created: 2026-08-16
Updated: 2026-08-17
Ticket: .10x/tickets/done/2026-08-16-migrate-routing-catalog-v3.md
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

## Authority integration and contemporaneous preview preflight

The initial authority records integrated through PR #126. Exact PR base was
`31d2a7756c5bd712147772a77b606154fb2610c3`; exact one-commit head was
`ae708f3846e665eecf854a38bc41e214563e7ed8`; and the exact three changed paths
were this evidence, its ticket, and its review. CI run `32004320577` passed
Python 3.13 job `95310638934`, Python 3.11 job `95310639046`, and Build
distributions job `95311183447`. Hosted comments and reviews were empty. The
ordinary squash integration is
`e4993e86e65d0e57a80baf887749b6d1fa29a708`, with sole parent
`31d2a7756c5bd712147772a77b606154fb2610c3` and exact tree
`4e51d5297eb18b4b872544cc34b21bd42ffcd1ab`. Exact main remained
`R = 4d1efc458fd13b270bf84984ffeb550d5b24fd04`.

Immediately before preview, read-only preflight reverified:

- sole executable `/Users/crlough/.local/bin/buoy`, package/version
  `0.5.2.dev28+g4d1efc458`, and CPython `3.11.10`;
- installed `catalog_cli.py` SHA-256
  `4803b57bf9037b026d7ecc3b45b4e6bae9258c96ac13c166f22a7c70a5efb677`
  against exact-R blob `7871cdce67759e1f58c4c5a54197974728b536fe`;
- installed `remote_catalog.py` SHA-256
  `9980208230c4743322447b32db75844cfdd2bcb6fc33abda0153d751db8048f1`
  against exact-R blob `27d663ea63edfd01ba82f55c3e5943c71678749c`;
- installed `turbopuffer 2.4.0`, `DEFAULT_MAX_RETRIES=4`, `_constants.py`
  SHA-256
  `3512a85ebc1dc3d3a76139a644cb4c4eb2482068e2b05d1e3ebe8195a570f304`,
  and `_base_client.py` SHA-256
  `76cc43f05ee8f265a2b86d5ccd6fed8d94ae7925a427eecf717cea5b7f8eee91`;
- successful `catalog migrate-routing-v3 --help`, credential presence privately
  true without retaining its value or output, and exact nonsecret region
  `gcp-us-central1`.

The routing-catalog mutation freeze began before preview and remained
uninterrupted through capture and review. No catalog operation has occurred
since this preview. The exact command

```text
/Users/crlough/.local/bin/buoy catalog migrate-routing-v3 --region gcp-us-central1 --json
```

exited `0` with empty stderr.

## One-time exhaustive-field preview binding

The original stdout file was not retained, so
`raw_stdout_sha256=unavailable-not-captured`. No raw-output digest is claimed,
and the parsed capture below is not represented as raw stdout or as a
reconstruction of unavailable stdout bytes. A second provider read solely to
obtain a raw-output digest is forbidden.

For this output only, the independently reviewed one-time exception replaces
only the raw-output digest with an exhaustive ordered capture of every parsed
JSON field and an independently recomputed structured digest. The following
object is ordered recursively by key:

```json
{
  "affected_ids": [],
  "approved": false,
  "card_identities": [
    {
      "card_revision": "5d91be183324820cd544681096895e8e26af559c4e116362f74a9a198f361e09",
      "namespace": "routing-test-fleetdeck-v1",
      "row_id": "bc_55e61a2303a028ef758a9b3109fb6e69e5e816d288207cffb9418cf41b894"
    },
    {
      "card_revision": "f118fe4959e2a46a28eb5d04e5d109380a63deff9e57ed8f18e87d74e8e18ec4",
      "namespace": "routing-test-fleetshield-v1",
      "row_id": "bc_25b74c624a9dad2d6c14e2b3ea87b7f4d9559495acd14bd8dbb94f4d6ff5f"
    },
    {
      "card_revision": "132fdfced513e80671ec6b4c40048ca54b3854149a9808c16db183180216109b",
      "namespace": "routing-test-orbitstock-v1",
      "row_id": "bc_a1eef2fbc223f2771fc129d26dcf59dede0d7017c63e79c36c9cca67ae761"
    },
    {
      "card_revision": "e009324f6a8d8e4c073be5cf379d1318c3136cd61e001401372a8dff5ea08049",
      "namespace": "routing-test-orbitwatch-v1",
      "row_id": "bc_19ae3de0120123c8cd2947d2f049003c27503de936fb9bff69e6302aea9e5"
    },
    {
      "card_revision": "868cad7d4beec3409734761aaa859fbef33bb35c747a2ad5a651172e904fdc5a",
      "namespace": "site-dagster-io-benchmark-v1",
      "row_id": "bc_c861f601295c592d8c2b1cfa2f3c6a1aafc581ad5a0aa409c094731a29d3e"
    },
    {
      "card_revision": "a225f5ee64b682f69bfd7e5b22a9f5151220e12874e9d5c081e73663b68b76eb",
      "namespace": "site-dagster-io-v1",
      "row_id": "bc_dde01f1e5f88e9078c088fb3819ec683c74c1523b2bf1b10b2f1fc55b4db5"
    },
    {
      "card_revision": "0ca826e3c5a89a2e3f69b220a238b0f3fee28df2e879adf11042e53f6c10ecf3",
      "namespace": "site-developer-salesforce-com-v1",
      "row_id": "bc_61070833c9d31c93dec5d6354200e3d98a2860080695b020f59507402172e"
    },
    {
      "card_revision": "20fb6bf187d4ecb3c5cb81c3eaa4c2c0b2f9ba4dd074928fabe2fa2b0137910d",
      "namespace": "site-oscilar-com-v1",
      "row_id": "bc_504c979785839b90ccc580949ba74c4e98e780d105336834a0e4aa698ffb3"
    },
    {
      "card_revision": "886029bcb65d06f085387955eac31bf58ed4d13867356f21fcbda9ade0eafc5d",
      "namespace": "site-rentptr-com-v1",
      "row_id": "bc_b5aac4db8a1713e4a77f0904ef46ba65f60cd272cf7fd6595866ce08b9665"
    },
    {
      "card_revision": "2e68d97ed37bb32f2e8c8929ee727fc1c7c3903c67b735afcb15ebd2ea280e38",
      "namespace": "site-turbopuffer-com-v1",
      "row_id": "bc_759119f10bf4a5502a4177c5ee7a833b6a90676982c42bc0a0949f0875d29"
    },
    {
      "card_revision": "c6c73fe50ba1f43f4c5852ebd33e5019a87a1cd4ef83f2fffe924326c8ebb99d",
      "namespace": "site-whiteboxgeo-com-v1",
      "row_id": "bc_0a4def95e12c5db6a88d57f90f056f91024e4f7a1653cf813cbb60961f84d"
    },
    {
      "card_revision": "4f7b38c80552a1c6e6686c44da035a8b317ab48e5f6feb6ae4fc06ff28200dd0",
      "namespace": "site-www-aurelio-ai-v1",
      "row_id": "bc_3f1b50121da245c98098ee63fdf7afac3a37d51af83cf34cc2f517b9f52b3"
    },
    {
      "card_revision": "09bd6be824d913db57c8e78034f1f4c56159abe4765aca9c0f9c9197a6e2895b",
      "namespace": "site-www-thistle-co-v1",
      "row_id": "bc_a3f6a1295c53b7b1149673a24169c23cabf0aff9ff115a3b8c42b25b54d0f"
    }
  ],
  "catalog_namespace": "buoy-routing-catalog-v1",
  "command": "catalog migrate-routing-v3",
  "counts": {
    "card_count": 13,
    "content_live_count": 14,
    "control_plane_count": 3,
    "disabled_count": 5,
    "eligible_count": 8,
    "incompatible_count": 0,
    "listed_total": 17,
    "missing_card_count": 1,
    "stale_target_count": 0
  },
  "coverage": {
    "disabled_ids": [
      "routing-test-fleetdeck-v1",
      "routing-test-fleetshield-v1",
      "routing-test-orbitstock-v1",
      "routing-test-orbitwatch-v1",
      "site-dagster-io-benchmark-v1"
    ],
    "eligible_ids": [
      "site-dagster-io-v1",
      "site-developer-salesforce-com-v1",
      "site-oscilar-com-v1",
      "site-rentptr-com-v1",
      "site-turbopuffer-com-v1",
      "site-whiteboxgeo-com-v1",
      "site-www-aurelio-ai-v1",
      "site-www-thistle-co-v1"
    ],
    "incompatible_ids": [],
    "missing_card_ids": [
      "site-docs-aurelio-ai-v1"
    ],
    "stale_target_ids": []
  },
  "expected_projection_sha256": "eb006aff8058da775ffd9a3dcae19e41050cf2b471b831aa95755c2e1cca5a38",
  "expected_snapshot_revision": "abb0d38193c8c00963fff6536bcf755f3bf707942a2b1f1ba4fa90b74f5a4ce8",
  "final_projection_sha256": "eb006aff8058da775ffd9a3dcae19e41050cf2b471b831aa95755c2e1cca5a38",
  "mutation_status": "preview",
  "observed_projection_sha256": "eb006aff8058da775ffd9a3dcae19e41050cf2b471b831aa95755c2e1cca5a38",
  "observed_snapshot_revision": "abb0d38193c8c00963fff6536bcf755f3bf707942a2b1f1ba4fa90b74f5a4ce8",
  "old_reader_warning": "Exact schema-v1/v2 readers fail closed after this additive migration; deploy the v1/v2/v3-compatible reader first.",
  "operation_budget": {
    "card_writes": 0,
    "content_operations": 0,
    "content_writes": 0,
    "deletes": 0,
    "model_inferences": 0,
    "schema_writes": 1,
    "strong_read_calls": 2
  },
  "operations_performed": {
    "card_writes": 0,
    "content_operations": 0,
    "content_writes": 0,
    "deletes": 0,
    "model_inferences": 0,
    "schema_writes": 0,
    "strong_read_calls": 1
  },
  "read_metrics": {
    "billing": [
      {
        "billable_logical_bytes_queried": 256000000,
        "billable_logical_bytes_returned": 58409
      },
      {
        "billable_logical_bytes_queried": 256000000,
        "billable_logical_bytes_returned": 58409
      }
    ],
    "card_query_pages": 2,
    "metadata_requests": 1,
    "namespace_list_pages": 2
  },
  "region": "gcp-us-central1",
  "request_summary": {
    "billing": [
      {
        "billable_logical_bytes_queried": 256000000,
        "billable_logical_bytes_returned": 58409
      },
      {
        "billable_logical_bytes_queried": 256000000,
        "billable_logical_bytes_returned": 58409
      }
    ],
    "catalog_page_query_requests": 2,
    "metadata_requests": 1,
    "mutation_verification_query_requests": 0,
    "namespace_list_requests": 2,
    "total_requests": 5,
    "write_requests": 0
  },
  "schema": {
    "additions": {
      "routing_evidence_vectors": {
        "filterable": false,
        "type": "[]float"
      },
      "routing_evidence_vectors_hash": {
        "filterable": false,
        "type": "string"
      },
      "routing_passages": {
        "filterable": false,
        "type": "[]string"
      }
    },
    "final_fingerprint_sha256": "e273200baa7161ce130ca4745d7e9e810e971cf8007ed4636b04cec9e3b6e23b",
    "final_version": 2,
    "observed_fingerprint_sha256": "e273200baa7161ce130ca4745d7e9e810e971cf8007ed4636b04cec9e3b6e23b",
    "observed_version": 2,
    "target_version": 3
  },
  "snapshot_revision": "abb0d38193c8c00963fff6536bcf755f3bf707942a2b1f1ba4fa90b74f5a4ce8",
  "verification_complete": false
}
```

`canonical_structured_preview_sha256=0d9e217022c3d651408551edbf2132e79a6244de05f955e562ce7c24b385cbc2`
is computed as
SHA-256 over
`json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`
encoded as UTF-8 with no trailing newline. This value binds only the parsed
object above, not unavailable stdout bytes.

The successful preview contains no top-level `write_attempted`, `failure`,
`rows_affected`, `retry_requires_fresh_preview`, `request_accounting_mode`,
`operation_accounting_complete`, `known_lower_bound_request_summary`, or
`accounting_complete` field; its `request_summary` also contains no
`accounting_complete`. No failure/retry/accounting-mode/completeness field is
present anywhere in the captured success payload.

The exact target-v3 fingerprint
`f596eccb4878fc462d4ea7165a553bd0f21b13bbce46af70a867999daedc888a` was
derived independently from exact-R source; it was not emitted in this preview
payload and is therefore not included in its structured digest.

## Preview assessment and external effects

The preview observed exact schema v2 and ended at exact schema v2. Snapshot
revision and observed/expected/final vector-inclusive projection are internally
identical. Its three target additions are exactly the non-filterable passage,
evidence-vector, and evidence-vector-hash fields. It performed one logical
strong read: two namespace-list calls, one metadata call, and two card-query
pages, for five logical SDK calls total. With four SDK retries per call, the
unobserved physical-attempt count is bounded to 5–25. It performed zero schema,
card, or content writes; zero content operations, deletes, and model
inferences; empty affected IDs; and no mutation-verification query.

Inventory reconciles exactly: 17 listed namespaces equal 3 control-plane plus
14 live content namespaces; 13 cards equal 8 eligible plus 5 disabled, with
zero incompatible or stale cards. `site-docs-aurelio-ai-v1` is the sole live
content namespace missing a card. It is distinct from the present, parsed, and
eligible `site-www-aurelio-ai-v1` card. The missing docs site remains excluded
from automatic routing until a future separately governed registration; this
schema migration grants no card creation, registration, or backfill authority.
The 17/13 inventory matches the prior stable audit, so the real coverage gap is
nonblocking for this schema-only migration.

The earlier “Pending fresh preview” and “External effects so far” paragraphs
are preserved append-only and describe only the pre-preview authority-record
session. This appended phase supersedes their current temporal reading. The
preview itself made the five logical read calls above and no write. That
records-only amendment branch made no provider call and did not inspect a
credential. At that checkpoint it authorized no approval until its exact three
amended records, including independent Preview GO, integrated into `develop`.

## Integrated Preview GO and one approved operation

PR #127 integrated the exhaustive preview and independent GO into `develop`
as ordinary squash commit
`S = 2dc00f5dec73820b63a71c2cf860e43ad4cc4f63`, with sole parent
`e4993e86e65d0e57a80baf887749b6d1fa29a708` and tree
`a4a90aa70f5d6610234d9d07959a642d4acfe455`. Its exact head was
`ddef40e2a53e7c5781279d3178f2fa2385f487ae`; CI run `32006692705`
passed Python 3.11 job `95317528721`, Python 3.13 job `95317528730`,
and Build distributions job `95318192181`. The PR changed only the three
migration records; hosted comments and reviews were empty. Exact main remained
`R = 4d1efc458fd13b270bf84984ffeb550d5b24fd04`.

Immediately before approval, the executor freshly reverified:

- sole normal executable `/Users/crlough/.local/bin/buoy`, exact-R package
  version `0.5.2.dev28+g4d1efc458`, and CPython `3.11.10`;
- installed `catalog_cli.py` SHA-256
  `4803b57bf9037b026d7ecc3b45b4e6bae9258c96ac13c166f22a7c70a5efb677`
  against exact-R blob `7871cdce67759e1f58c4c5a54197974728b536fe`;
- installed `remote_catalog.py` SHA-256
  `9980208230c4743322447b32db75844cfdd2bcb6fc33abda0153d751db8048f1`
  against exact-R blob `27d663ea63edfd01ba82f55c3e5943c71678749c`;
- installed `turbopuffer 2.4.0`, `DEFAULT_MAX_RETRIES=4`,
  `_constants.py` SHA-256
  `3512a85ebc1dc3d3a76139a644cb4c4eb2482068e2b05d1e3ebe8195a570f304`,
  and `_base_client.py` SHA-256
  `76cc43f05ee8f265a2b86d5ccd6fed8d94ae7925a427eecf717cea5b7f8eee91`;
- successful migration-command help, privately true credential presence
  without retaining its value or output, exact region `gcp-us-central1`,
  literal catalog `buoy-routing-catalog-v1`, and the uninterrupted mutation
  freeze.

The executor then invoked this exact command once and no second
operator/CLI/application approval:

```text
/Users/crlough/.local/bin/buoy catalog migrate-routing-v3 --expected-snapshot-revision abb0d38193c8c00963fff6536bcf755f3bf707942a2b1f1ba4fa90b74f5a4ce8 --expected-projection-sha256 eb006aff8058da775ffd9a3dcae19e41050cf2b471b831aa95755c2e1cca5a38 --approve --region gcp-us-central1 --json
```

It exited `0` with empty stderr. Captured raw stdout is 7,349 bytes including
its trailing newline and has SHA-256
`44af6e7158123803e2079c820a80c6d0c29938ee197682a16a4afbe62363b22a`.
Its canonical representation is exactly
`json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`
encoded as UTF-8 with no trailing newline: 5,994 bytes with SHA-256
`aed3a9af26e42073a3463b587e049970fe51d8d11c621dca5c4af87561d1aea5`.

## Exhaustive approved-result capture

The captured sanitized 22-field JSON result, ordered recursively by key, is:

```json
{
  "affected_ids": [],
  "approved": true,
  "card_identities": [
    {
      "card_revision": "5d91be183324820cd544681096895e8e26af559c4e116362f74a9a198f361e09",
      "namespace": "routing-test-fleetdeck-v1",
      "row_id": "bc_55e61a2303a028ef758a9b3109fb6e69e5e816d288207cffb9418cf41b894"
    },
    {
      "card_revision": "f118fe4959e2a46a28eb5d04e5d109380a63deff9e57ed8f18e87d74e8e18ec4",
      "namespace": "routing-test-fleetshield-v1",
      "row_id": "bc_25b74c624a9dad2d6c14e2b3ea87b7f4d9559495acd14bd8dbb94f4d6ff5f"
    },
    {
      "card_revision": "132fdfced513e80671ec6b4c40048ca54b3854149a9808c16db183180216109b",
      "namespace": "routing-test-orbitstock-v1",
      "row_id": "bc_a1eef2fbc223f2771fc129d26dcf59dede0d7017c63e79c36c9cca67ae761"
    },
    {
      "card_revision": "e009324f6a8d8e4c073be5cf379d1318c3136cd61e001401372a8dff5ea08049",
      "namespace": "routing-test-orbitwatch-v1",
      "row_id": "bc_19ae3de0120123c8cd2947d2f049003c27503de936fb9bff69e6302aea9e5"
    },
    {
      "card_revision": "868cad7d4beec3409734761aaa859fbef33bb35c747a2ad5a651172e904fdc5a",
      "namespace": "site-dagster-io-benchmark-v1",
      "row_id": "bc_c861f601295c592d8c2b1cfa2f3c6a1aafc581ad5a0aa409c094731a29d3e"
    },
    {
      "card_revision": "a225f5ee64b682f69bfd7e5b22a9f5151220e12874e9d5c081e73663b68b76eb",
      "namespace": "site-dagster-io-v1",
      "row_id": "bc_dde01f1e5f88e9078c088fb3819ec683c74c1523b2bf1b10b2f1fc55b4db5"
    },
    {
      "card_revision": "0ca826e3c5a89a2e3f69b220a238b0f3fee28df2e879adf11042e53f6c10ecf3",
      "namespace": "site-developer-salesforce-com-v1",
      "row_id": "bc_61070833c9d31c93dec5d6354200e3d98a2860080695b020f59507402172e"
    },
    {
      "card_revision": "20fb6bf187d4ecb3c5cb81c3eaa4c2c0b2f9ba4dd074928fabe2fa2b0137910d",
      "namespace": "site-oscilar-com-v1",
      "row_id": "bc_504c979785839b90ccc580949ba74c4e98e780d105336834a0e4aa698ffb3"
    },
    {
      "card_revision": "886029bcb65d06f085387955eac31bf58ed4d13867356f21fcbda9ade0eafc5d",
      "namespace": "site-rentptr-com-v1",
      "row_id": "bc_b5aac4db8a1713e4a77f0904ef46ba65f60cd272cf7fd6595866ce08b9665"
    },
    {
      "card_revision": "2e68d97ed37bb32f2e8c8929ee727fc1c7c3903c67b735afcb15ebd2ea280e38",
      "namespace": "site-turbopuffer-com-v1",
      "row_id": "bc_759119f10bf4a5502a4177c5ee7a833b6a90676982c42bc0a0949f0875d29"
    },
    {
      "card_revision": "c6c73fe50ba1f43f4c5852ebd33e5019a87a1cd4ef83f2fffe924326c8ebb99d",
      "namespace": "site-whiteboxgeo-com-v1",
      "row_id": "bc_0a4def95e12c5db6a88d57f90f056f91024e4f7a1653cf813cbb60961f84d"
    },
    {
      "card_revision": "4f7b38c80552a1c6e6686c44da035a8b317ab48e5f6feb6ae4fc06ff28200dd0",
      "namespace": "site-www-aurelio-ai-v1",
      "row_id": "bc_3f1b50121da245c98098ee63fdf7afac3a37d51af83cf34cc2f517b9f52b3"
    },
    {
      "card_revision": "09bd6be824d913db57c8e78034f1f4c56159abe4765aca9c0f9c9197a6e2895b",
      "namespace": "site-www-thistle-co-v1",
      "row_id": "bc_a3f6a1295c53b7b1149673a24169c23cabf0aff9ff115a3b8c42b25b54d0f"
    }
  ],
  "catalog_namespace": "buoy-routing-catalog-v1",
  "command": "catalog migrate-routing-v3",
  "counts": {
    "card_count": 13,
    "content_live_count": 14,
    "control_plane_count": 3,
    "disabled_count": 5,
    "eligible_count": 8,
    "incompatible_count": 0,
    "listed_total": 17,
    "missing_card_count": 1,
    "stale_target_count": 0
  },
  "coverage": {
    "disabled_ids": [
      "routing-test-fleetdeck-v1",
      "routing-test-fleetshield-v1",
      "routing-test-orbitstock-v1",
      "routing-test-orbitwatch-v1",
      "site-dagster-io-benchmark-v1"
    ],
    "eligible_ids": [
      "site-dagster-io-v1",
      "site-developer-salesforce-com-v1",
      "site-oscilar-com-v1",
      "site-rentptr-com-v1",
      "site-turbopuffer-com-v1",
      "site-whiteboxgeo-com-v1",
      "site-www-aurelio-ai-v1",
      "site-www-thistle-co-v1"
    ],
    "incompatible_ids": [],
    "missing_card_ids": [
      "site-docs-aurelio-ai-v1"
    ],
    "stale_target_ids": []
  },
  "expected_projection_sha256": "eb006aff8058da775ffd9a3dcae19e41050cf2b471b831aa95755c2e1cca5a38",
  "expected_snapshot_revision": "abb0d38193c8c00963fff6536bcf755f3bf707942a2b1f1ba4fa90b74f5a4ce8",
  "final_projection_sha256": "eb006aff8058da775ffd9a3dcae19e41050cf2b471b831aa95755c2e1cca5a38",
  "mutation_status": "migrated",
  "observed_projection_sha256": "eb006aff8058da775ffd9a3dcae19e41050cf2b471b831aa95755c2e1cca5a38",
  "observed_snapshot_revision": "abb0d38193c8c00963fff6536bcf755f3bf707942a2b1f1ba4fa90b74f5a4ce8",
  "old_reader_warning": "Exact schema-v1/v2 readers fail closed after this additive migration; deploy the v1/v2/v3-compatible reader first.",
  "operation_budget": {
    "card_writes": 0,
    "content_operations": 0,
    "content_writes": 0,
    "deletes": 0,
    "model_inferences": 0,
    "schema_writes": 1,
    "strong_read_calls": 2
  },
  "operations_performed": {
    "card_writes": 0,
    "content_operations": 0,
    "content_writes": 0,
    "deletes": 0,
    "model_inferences": 0,
    "schema_writes": 1,
    "strong_read_calls": 2
  },
  "read_metrics": {
    "billing": [
      {
        "billable_logical_bytes_queried": 256000000,
        "billable_logical_bytes_returned": 58409
      },
      {
        "billable_logical_bytes_queried": 256000000,
        "billable_logical_bytes_returned": 58409
      },
      {
        "billable_logical_bytes_queried": 256000000,
        "billable_logical_bytes_returned": 58409
      },
      {
        "billable_logical_bytes_queried": 256000000,
        "billable_logical_bytes_returned": 58409
      }
    ],
    "card_query_pages": 4,
    "metadata_requests": 2,
    "namespace_list_pages": 4
  },
  "region": "gcp-us-central1",
  "request_summary": {
    "billing": [
      {
        "billable_logical_bytes_queried": 256000000,
        "billable_logical_bytes_returned": 58409
      },
      {
        "billable_logical_bytes_queried": 256000000,
        "billable_logical_bytes_returned": 58409
      },
      {
        "billable_logical_bytes_queried": 256000000,
        "billable_logical_bytes_returned": 58409
      },
      {
        "billable_logical_bytes_queried": 256000000,
        "billable_logical_bytes_returned": 58409
      },
      {
        "billable_logical_bytes_written": 0
      }
    ],
    "catalog_page_query_requests": 4,
    "metadata_requests": 2,
    "mutation_verification_query_requests": 0,
    "namespace_list_requests": 4,
    "total_requests": 11,
    "write_requests": 1
  },
  "schema": {
    "additions": {
      "routing_evidence_vectors": {
        "filterable": false,
        "type": "[]float"
      },
      "routing_evidence_vectors_hash": {
        "filterable": false,
        "type": "string"
      },
      "routing_passages": {
        "filterable": false,
        "type": "[]string"
      }
    },
    "final_fingerprint_sha256": "f596eccb4878fc462d4ea7165a553bd0f21b13bbce46af70a867999daedc888a",
    "final_version": 3,
    "observed_fingerprint_sha256": "e273200baa7161ce130ca4745d7e9e810e971cf8007ed4636b04cec9e3b6e23b",
    "observed_version": 2,
    "target_version": 3
  },
  "snapshot_revision": "abb0d38193c8c00963fff6536bcf755f3bf707942a2b1f1ba4fa90b74f5a4ce8",
  "verification_complete": true
}
```

The successful payload contains no top-level `write_attempted`, `failure`,
`rows_affected`, `retry_requires_fresh_preview`,
`request_accounting_mode`, `operation_accounting_complete`,
`known_lower_bound_request_summary`, or `accounting_complete` field; its
`request_summary` also contains no `accounting_complete`. No
failure/retry/accounting-mode/completeness field is present anywhere in this
success result.

Relative to the exact exhaustive preview object, the approved result changed
only these values:

- `approved: false -> true` and
  `mutation_status: "preview" -> "migrated"`;
- `operations_performed.schema_writes: 0 -> 1` and
  `operations_performed.strong_read_calls: 1 -> 2`;
- `read_metrics.namespace_list_pages: 2 -> 4`,
  `metadata_requests: 1 -> 2`, `card_query_pages: 2 -> 4`, and two
  identical read-billing entries became four;
- `request_summary.namespace_list_requests: 2 -> 4`,
  `metadata_requests: 1 -> 2`,
  `catalog_page_query_requests: 2 -> 4`,
  `total_requests: 5 -> 11`, `write_requests: 0 -> 1`, and the two read
  billing entries became four plus one
  `{"billable_logical_bytes_written": 0}` entry;
- `schema.final_version: 2 -> 3`,
  `schema.final_fingerprint_sha256` changed from
  `e273200baa7161ce130ca4745d7e9e810e971cf8007ed4636b04cec9e3b6e23b`
  to
  `f596eccb4878fc462d4ea7165a553bd0f21b13bbce46af70a867999daedc888a`;
  and
- `verification_complete: false -> true`.

Every other field, nested value, array order, all 13 card identities and
revisions, counts, coverage sets, snapshot revision, and observed/expected/
final vector-inclusive projection stayed byte-for-value identical to the
preview capture.

## Exact-v3 assessment and operation accounting

The result proves an exact v2-to-v3 migration with only the three expected
non-filterable additions: `routing_passages: []string`,
`routing_evidence_vectors: []float`, and
`routing_evidence_vectors_hash: string`. Final fingerprint is
`f596eccb4878fc462d4ea7165a553bd0f21b13bbce46af70a867999daedc888a`;
`verification_complete=true`; snapshot revision remains
`abb0d38193c8c00963fff6536bcf755f3bf707942a2b1f1ba4fa90b74f5a4ce8`;
and observed, expected, and final vector-inclusive projection remain
`eb006aff8058da775ffd9a3dcae19e41050cf2b471b831aa95755c2e1cca5a38`.

Inventory remains exactly 17 listed = 3 control-plane + 14 live content
namespaces, with 13 cards = 8 eligible + 5 disabled, zero incompatible, zero
stale, and the same one missing `site-docs-aurelio-ai-v1` card. The missing
docs site remains distinct from present `site-www-aurelio-ai-v1`, excluded
from routing, and outside this ticket's registration/backfill authority.
`affected_ids=[]`.

The command performed exactly two logical strong reads and one logical schema
write, with zero card writes, content writes, content operations, deletes, or
model inferences. It made 11 logical SDK invocations: four namespace-list
pages, two metadata requests, four card-query pages, zero separate
mutation-verification queries, and one write. Four read billing entries each
report `256000000` billable logical bytes queried and `58409` returned.
The write billing entry reports zero row bytes written; that is consistent with
the recorded schema-only mutation and does not mean the logical schema-write
invocation was absent.

The installed four-retry SDK policy bounds the 11 logical invocations to
11–55 unobserved physical transport attempts. The one logical write invocation
is bounded to one–five physical attempts under one internally reused
idempotency key. The exact physical-attempt count remains unobserved. No second
approval or separate repeat strong-read command was issued.

Exact-R source requires the successful command-internal post-write strong read
to compare every full card before/after, including vectors, routing examples,
routing passages, routing evidence vectors, and evidence-vector hashes, in
addition to the vector-inclusive projection, identities, revisions, counts,
and coverage. Therefore `verification_complete=true` proves all 13 stored
card payloads unchanged and the three new banks empty on existing cards. It
also proves no card/example/passage/vector/backfill mutation. This operation
does not populate old cards; it only permits future separately reviewed
`buoy plan` / `buoy apply` executions to populate their own routing
evidence.

## Closure effects and authority disposition

The earlier approval HOLD was satisfied only when PR #127 integrated as exact
`S`; its statements remain historical rather than current. The bound command
was invoked once, completed successfully, and consumed this ticket's one-time
provider authority. No retry, rollback, second approval, provider read,
registration, card creation, plan/apply, or backfill is authorized after this
result.

The operation exposed no credential, raw row, passage, or vector. Beyond the
11 logical calls recorded above and their hidden retry bound, it caused no
model, content, card, delete, publication, deployment, package install, tag,
GitHub Release, branch protection/ruleset, Git-ref, or unrelated external
effect. This provider-free closure branch reads no credential, makes no
provider request, and changes only the three migration records. The earlier
pre-preview, preview, and HOLD paragraphs are retained append-only and are
time-scoped by this completed phase.
