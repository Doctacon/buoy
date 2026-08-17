Status: pass
Created: 2026-08-16
Updated: 2026-08-17
Target: PR #127 / S and exact schema-v3 operation closure
Ticket: .10x/tickets/done/2026-08-16-migrate-routing-catalog-v3.md
Evidence: .10x/evidence/2026-08-16-routing-catalog-v3-migration.md
Decision: .10x/decisions/buoy-derives-routing-prototypes-from-reviewed-plans.md
Specification: .10x/specs/automatic-routing-after-apply.md
Record-Verdict: pass
Preview-Verdict: go
Post-Operation-Verdict: pass

# Live Routing Catalog V3 Migration Review

## Record authority review

Independent records-phase review bound exact task base / current develop
`D0 = 31d2a7756c5bd712147772a77b606154fb2610c3` with tree
`efc512005e3f31f9b26da408473324c35fc15774` and these settled candidate
identities:

- the same ticket now at
  `.10x/tickets/done/2026-08-16-migrate-routing-catalog-v3.md` (then active)
  blob `28c832131ad097304763a515430ad6e7c7cb6dd5`;
- `.10x/evidence/2026-08-16-routing-catalog-v3-migration.md` blob
  `748b4aa6fb12cb2ac9deab62b8a754a6d07ee0f0`;
- this review path, with `Record-Verdict: pass`, `Preview-Verdict: pending`,
  and `Post-Operation-Verdict: pending`; the independent final rereview binds
  the complete review bytes externally rather than creating a self-hash;
- governing decision blob
  `6905b85d1598292ec1345bf4d20fabceca1e9bd7` and active specification blob
  `38b5d5b85af4f94d3e14a5538c7543758f3674a1` at the header-linked paths.

The exact candidate changes only those three ticket/evidence/review paths. It
binds exact main `R = 4d1efc458fd13b270bf84984ffeb550d5b24fd04`, installed
version `0.5.2.dev28+g4d1efc458`, exact-R `remote_catalog.py` and
`catalog_cli.py` SHA-256 / Git-blob identities, the exact-R wheel and source
hashes, and installed `turbopuffer 2.4.0` with
`DEFAULT_MAX_RETRIES=4` plus the recorded retry-source hashes. Source/lock
validation and record/link/diff checks are required before handoff. The source
validator reports valid active routing receipts and paused publication; the
lock is stable. The exact forbidden-surface comparison against `D0` must remain
empty for source, tests, scripts, README, AGENTS, CHANGELOG, `pyproject.toml`,
`uv.lock`, workflows, specifications, and every non-owned record.

The records distinguish logical SDK invocations from hidden physical transport
attempts, permit Preview GO only for exact v2, require a durably integrated
preview/GO before one bound approval command, preserve same-region/privacy and
optimistic-concurrency boundaries, and make an uncertain write invocation
consume the ticket without retry. They also keep the new diagnostic slices
separate from earlier live provider history.

`Record-Verdict: pass` permits only the exact three-file task-branch commit and
push plus ordinary pull-request handoff to `develop`, including this third
review record. This task session may not open or merge the PR. The verdict is
not Preview GO, Post-Operation PASS,
credential/provider authority, or evidence that a live preview or mutation
occurred; record review inspected no credential and made no provider call. It
grants no source/spec/dependency/workflow change, package install,
model, plan/apply, card/content/backfill/delete, publication, tag, GitHub
Release, protection/ruleset, direct/force-push, or unrelated effect.

## Current boundary

This initial record defines two future independent review gates. It does not
claim that a preview exists, does not predeclare GO or PASS, and authorizes no
credential access, provider request, or mutation. Record-only pre-review of
the three-file authority set cannot substitute for either live verdict below.

## Preview review gate

Before setting `Preview-Verdict`, an independent reviewer must bind:

- the exact installed executable/package version, Python version, exact-R
  commit, wheel/source hashes, both installed migration-module hashes and
  exact-R source blobs, installed `turbopuffer 2.4.0` retry constants/source
  hashes, and migration-help surface;
- the complete sanitized preview JSON and whole-output digest;
- observed/target/final schema, exact fingerprints and additions, 64-character
  lowercase snapshot revision and projection SHA-256;
- literal `catalog_namespace=buoy-routing-catalog-v1`, exact nonsecret
  `region=gcp-us-central1`, and `same_resolved_region=true` for any approval;
- counts, coverage, sanitized card identities, and comparison with the prior
  stable 17-namespace / 13-row audit without assuming that inventory cannot
  legitimately change;
- `operation_budget`, `operations_performed`, `read_metrics`, all emitted
  logical request-summary categories/totals/billing, mutation/write and verification
  status, and affected IDs; interpret those summaries as logical SDK
  invocations/pages, bind the one-through-five transport-attempt bound per
  invocation, and bind failure-only accounting mode/completeness fields when
  the CLI emits them;
- the catalog-mutation freeze and absence of raw rows, passages, vectors,
  credentials, or unsanitized errors; the exact region is nonsecret and must
  remain recorded rather than redacted.

The reviewer may record GO only for an exact schema-v2, stable, fully accounted
preview with zero writes/deletes/model work and explained inventory. The
verdict must bind that exact output; any new output returns this field to
pending. An exact-v3 preview receives `no-operation-required`, not GO.

Required NO-GO conditions include exact v1 without its separately governed v2
prerequisite, unsupported schema, malformed card, unstable/failed read,
unknown or incomplete new accounting, binding format failure, unexplained
inventory drift, provider-write evidence, privacy leakage, reader mismatch, or
loss of the mutation freeze.

For exact v2, GO may authorize exactly one approval bound to that preview. For
exact v3, approval and schema writes are forbidden; the reviewer must record
`no-operation-required` and close from the reviewed exact-v3 preview.

An exact-v2 GO becomes authority only after the sanitized preview and review
are committed, pushed, and integrated into `develop`. A local, chat-only,
uncommitted, or pending verdict is not approval authority. The reviewed
exact-v3 no-operation path must be durably recorded under the same boundary.

## Approval and failure review boundary

The reviewer must compare the approved command's supplied snapshot and
projection byte-for-byte with the GO preview and prove it used the same
literal catalog namespace `buoy-routing-catalog-v1` and exact region
`gcp-us-central1`. This is optimistic drift detection, not a
provider-atomic catalog compare-and-swap; the mutation freeze must stay intact
through write and readback. Drift/precondition failure must show
`write_attempted=false`. A v2 success may show only one CLI approval / logical
SDK schema-write invocation, empty affected IDs / zero rows, two logical strong
reads, and no other operation.

Installed `turbopuffer 2.4.0` uses four retries. Each logical SDK invocation can
therefore make one through five transport attempts; the write invocation
reuses one generated retry key internally. Emitted request summaries count
logical SDK invocations/pages and do not expose exact physical attempts. The
reviewer must preserve that distinction and forbid a second CLI/operator
approval invocation.

If `write_attempted=true` and verification is incomplete, the result consumes
this ticket's single permitted operator/SDK write invocation, including any
one-through-five internal transport attempts, and is not retry authority.
Preserve exact or `known_lower_bound` logical accounting and the physical bound
and stop. Any later attempt requires a fresh preview, new authority, and new
independent review. Rollback, an operator retry, and a second approval under
this ticket are always forbidden.

## Post-operation review gate

Before setting `Post-Operation-Verdict`, independently verify:

- exact final schema v3 and only the three expected non-filterable additions;
- unchanged vector-inclusive projection, inventory, coverage, card identities,
  card revisions, and empty existing evidence banks;
- zero card/content/example/passage/model/delete/backfill operations and at
  most one logical SDK schema-only write invocation;
- successful command-internal strong readback or a reviewed exact-v3 no-write
  result;
- complete exact logical SDK accounting on success plus transport-attempt
  bounds, with new totals kept separate from unknown diagnostic slices and the
  separate exact five-logical-operation audit;
- no credential/raw-row/passage/vector disclosure and no publication,
  deployment, protection, branch, or unrelated external effect.

Only a recorded post-operation PASS may change evidence to `recorded` and move
the ticket to
`.10x/tickets/done/2026-08-16-migrate-routing-catalog-v3.md`. That closure must
change the evidence/review `Ticket:` links to the done path and integrate the
records-only result. Preview, GO, operation, and closure facts remain
append-only; only current status/verdict/link fields and the ticket path
advance. Any failed, uncertain, or mismatched state remains open and receives
no PASS.

## Historical verdicts before operation

- Preview verdict: go under the one-time exhaustive-field exception below.
- Post-operation verdict was pending at the Preview GO checkpoint; no v3
  operation had then been reviewed.

## One-time exception and Preview GO

### Integrated authority and exact preflight

PR #126 integrated the initial three-record authority. It bound base
`31d2a7756c5bd712147772a77b606154fb2610c3`, one-commit head
`ae708f3846e665eecf854a38bc41e214563e7ed8`, and exactly the ticket, evidence,
and review paths. CI run `32004320577` passed Python 3.13 job `95310638934`,
Python 3.11 job `95310639046`, and Build distributions job `95311183447`;
hosted comments and reviews were empty. Ordinary squash integration
`e4993e86e65d0e57a80baf887749b6d1fa29a708` has sole parent
`31d2a7756c5bd712147772a77b606154fb2610c3` and exact tree
`4e51d5297eb18b4b872544cc34b21bd42ffcd1ab`. Main remained exact `R`.

Contemporaneous preflight reverified exact installed Buoy version
`0.5.2.dev28+g4d1efc458`, CPython `3.11.10`, `catalog_cli.py` SHA-256 / exact-R
blob
`4803b57bf9037b026d7ecc3b45b4e6bae9258c96ac13c166f22a7c70a5efb677` /
`7871cdce67759e1f58c4c5a54197974728b536fe`, `remote_catalog.py` SHA-256 /
exact-R blob
`9980208230c4743322447b32db75844cfdd2bcb6fc33abda0153d751db8048f1` /
`27d663ea63edfd01ba82f55c3e5943c71678749c`, and installed
`turbopuffer 2.4.0` with `DEFAULT_MAX_RETRIES=4` and the recorded
`_constants.py` / `_base_client.py` hashes. Command help passed. Credential
presence was privately true without retaining its value or output; exact
region was `gcp-us-central1`. The mutation freeze began before preview and has
remained uninterrupted, with no catalog operation since.

The exact command

```text
/Users/crlough/.local/bin/buoy catalog migrate-routing-v3 --region gcp-us-central1 --json
```

exited `0` with empty stderr and bound literal catalog namespace
`buoy-routing-catalog-v1`.

### One-output digest exception

The original stdout file was not captured, so
`raw_stdout_sha256=unavailable-not-captured`. No raw stdout or raw digest is
claimed, and the evidence's parsed
field capture is not represented as raw stdout or as a reconstruction of
unavailable stdout bytes. A second provider read solely to create that digest
is forbidden.

For this exact output only, review replaces only the raw-output digest
requirement with the evidence's exhaustive ordered parsed object and
`canonical_structured_preview_sha256=0d9e217022c3d651408551edbf2132e79a6244de05f955e562ce7c24b385cbc2`.
The digest was independently recomputed from exactly
`json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`
encoded as UTF-8 with no trailing newline.

The object binds every top-level field: `affected_ids`, `approved`,
`card_identities`, `catalog_namespace`, `command`, `counts`, `coverage`,
`expected_projection_sha256`, `expected_snapshot_revision`,
`final_projection_sha256`, `mutation_status`, `observed_projection_sha256`,
`observed_snapshot_revision`, `old_reader_warning`, `operation_budget`,
`operations_performed`, `read_metrics`, `region`, `request_summary`, `schema`,
`snapshot_revision`, and `verification_complete`, including every nested value
and array order. It explicitly proves top-level `write_attempted`, `failure`,
`rows_affected`, `retry_requires_fresh_preview`, `request_accounting_mode`,
`operation_accounting_complete`, `known_lower_bound_request_summary`, and
`accounting_complete` absent, plus `request_summary.accounting_complete`
absent. No failure, retry, accounting-mode, or accounting-completeness field
was present on this successful preview.

This exception waives no other condition and transfers to no other output. The
exact target-v3 fingerprint
`f596eccb4878fc462d4ea7165a553bd0f21b13bbce46af70a867999daedc888a` is a
separate exact-R source derivation, not an emitted preview field and not part of
the structured digest.

### Bound preview findings

The exhaustive object proves observed/final schema v2 with fingerprint
`e273200baa7161ce130ca4745d7e9e810e971cf8007ed4636b04cec9e3b6e23b`, target
schema v3 with exactly the three non-filterable additions, snapshot revision
`abb0d38193c8c00963fff6536bcf755f3bf707942a2b1f1ba4fa90b74f5a4ce8`, and
identical observed/expected/final projection
`eb006aff8058da775ffd9a3dcae19e41050cf2b471b831aa95755c2e1cca5a38`.

The inventory is internally exact and matches the prior stable 17/13 audit:
17 listed equals 3 control-plane plus 14 live content namespaces; 13 cards
equals 8 eligible plus 5 disabled, with zero incompatible and zero stale.
`site-docs-aurelio-ai-v1` is the one content namespace missing a card, distinct
from present eligible `site-www-aurelio-ai-v1`. The missing docs site remains
excluded from automatic routing until separately governed registration. This
real coverage gap is nonblocking for the schema-only migration and grants no
card creation, registration, or backfill authority.

The preview performed one logical strong read and five logical SDK calls: two
namespace-list calls, one metadata call, and two card-query pages. Physical
transport attempts were not observed and are bounded to 5–25. Both billing
entries record `256000000` logical bytes queried and `58409` returned. The
preview performed zero schema/card/content writes, content operations, deletes,
model inferences, and mutation-verification queries; affected IDs are empty.

### Verdict and approval hold

`Preview-Verdict: go` binds only this exhaustive object, structured digest,
snapshot, projection, exact-R reader, region/catalog, inventory explanation,
accounting, privacy boundary, and uninterrupted freeze. At that checkpoint,
post-operation review remained pending; Preview GO was not PASS or evidence
that a migration write had occurred.

Approval remained HOLD until this exact three-record exception and Preview GO
integrated into `develop`. Before approval, the executor had to freshly rebind
the installed exact-R identities, private credential presence, exact region,
and uninterrupted freeze. Only then could it invoke exactly once:

```text
/Users/crlough/.local/bin/buoy catalog migrate-routing-v3 --expected-snapshot-revision abb0d38193c8c00963fff6536bcf755f3bf707942a2b1f1ba4fa90b74f5a4ce8 --expected-projection-sha256 eb006aff8058da775ffd9a3dcae19e41050cf2b471b831aa95755c2e1cca5a38 --approve --region gcp-us-central1 --json
```

That records-only review branch made no provider call and inspected no
credential. Its verdict permitted only exact three-record validation, commit,
push, and ordinary PR handoff; its session could not approve, open or merge a
PR, or change source, dependencies, workflows, specifications, publication,
provider state, or any unrelated surface.

## Independent post-operation PASS

Independent post-operation review binds exact closure base
`S = 2dc00f5dec73820b63a71c2cf860e43ad4cc4f63`, sole parent
`e4993e86e65d0e57a80baf887749b6d1fa29a708`, and tree
`a4a90aa70f5d6610234d9d07959a642d4acfe455`. PR #127 had exact head
`ddef40e2a53e7c5781279d3178f2fa2385f487ae`, exactly the three migration
record paths, and ordinary squash integration `S`; CI run `32006692705`
passed Python 3.11 job `95317528721`, Python 3.13 job `95317528730`, and
Build distributions job `95318192181`. Hosted PR comments and reviews were
empty; this independent records review supplies the substantive verdict.
Exact main remained `R = 4d1efc458fd13b270bf84984ffeb550d5b24fd04`.

The review rechecked the fresh pre-approval identity of the sole exact-R
Buoy executable/package at version `0.5.2.dev28+g4d1efc458` under CPython
`3.11.10`; installed `catalog_cli.py` and `remote_catalog.py` hashes against
exact-R blobs; installed `turbopuffer 2.4.0`, `DEFAULT_MAX_RETRIES=4`, and
both retry-source hashes; command help; privately true credential presence
without retaining value/output; exact region `gcp-us-central1`; literal
catalog `buoy-routing-catalog-v1`; and the uninterrupted mutation freeze.

The bound snapshot and projection in the once-invoked approval command match
Preview GO byte-for-byte. The command exited `0` with empty stderr. Its raw
stdout is 7,349 bytes including the trailing newline, SHA-256
`44af6e7158123803e2079c820a80c6d0c29938ee197682a16a4afbe62363b22a`;
its canonical sorted compact JSON is 5,994 bytes without a trailing newline,
SHA-256
`aed3a9af26e42073a3463b587e049970fe51d8d11c621dca5c4af87561d1aea5`.
The evidence preserves the complete sanitized 22-field object, explicit
success-field omissions, and the exhaustive preview-to-approval delta.

That result proves exact schema v3, final fingerprint
`f596eccb4878fc462d4ea7165a553bd0f21b13bbce46af70a867999daedc888a`,
only the three expected non-filterable additions, and
`verification_complete=true`. Snapshot
`abb0d38193c8c00963fff6536bcf755f3bf707942a2b1f1ba4fa90b74f5a4ce8`
and projection
`eb006aff8058da775ffd9a3dcae19e41050cf2b471b831aa95755c2e1cca5a38`
remain unchanged. All 13 card identities/revisions, the 17/13 inventory,
counts, coverage, and the one explained missing-card gap are unchanged;
`affected_ids=[]`.

The command performed exactly two logical strong reads and one logical
schema-write invocation, with all card/content/example/passage/vector/model/
delete/backfill counters zero. Complete accounting is 11 logical SDK
invocations: four namespace-list pages, two metadata reads, four card-query
pages, zero separate mutation-verification queries, and one write. Four read
billing entries each report `256000000` queried / `58409` returned; the write
billing entry reports zero row bytes written, not zero schema invocation.
Installed retry behavior bounds the 11 logical calls to 11–55 hidden physical
attempts and the sole write to one–five attempts under one reused idempotency
key. There was no second approval or separate repeat-read command.

Exact-R source makes a successful built-in readback compare every full card
before/after, including stored vectors, routing examples, passages, evidence
vectors, and evidence-vector hashes. Together with
`verification_complete=true`, unchanged projection/identities/revisions, and
the exact operation counters, this proves unchanged existing card payloads
and empty new evidence banks. It proves a schema-only migration, not a card
registration, routing-evidence backfill, or source-aware conversion of old
cards.

`Post-Operation-Verdict: pass` is limited to this exact output and operation.
The earlier HOLD became historical when PR #127 integrated as exact `S`; the
once-invoked successful approval consumed all provider authority in this
ticket. No retry, rollback, second provider command/read, registration,
plan/apply, or backfill is authorized. No credential or raw provider row,
passage, or vector is recorded. There was no publication, deployment, package
install, tag, GitHub Release, protection/ruleset, branch, model, or unrelated
effect.

The closure itself is provider-free and changes only this review, the linked
evidence, and the ticket moved to the linked done path. It may validate,
commit, push, and undergo ordinary PR handoff only; it grants its own session
no provider, credential, PR creation/integration, direct-push, or unrelated
authority. Preview GO remains valid historical evidence, and the final PASS
permits evidence status `recorded` and ticket status `done`.
