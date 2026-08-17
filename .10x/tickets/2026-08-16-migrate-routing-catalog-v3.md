Status: active
Created: 2026-08-16
Updated: 2026-08-16
Depends-On: .10x/tickets/done/2026-08-16-promote-automatic-routing-to-main-once.md
Decision: .10x/decisions/buoy-derives-routing-prototypes-from-reviewed-plans.md
Specification: .10x/specs/automatic-routing-after-apply.md
Evidence: .10x/evidence/2026-08-16-routing-catalog-v3-migration.md
Review: .10x/reviews/2026-08-16-routing-catalog-v3-migration-review.md

# Migrate the Live Routing Catalog to Schema V3

## Outcome

Honor the user's explicit request to complete the live migration after the
automatic-routing reader reached `main`: use the installed exact-main reader
to obtain a fresh zero-write preview and, only after an independent GO
on that exact preview, perform at most one snapshot-and-projection-bound
schema-only approval. Finish with exact-v3 readback and independent review.

## Authority prerequisites

- This three-record authority set must first pass independent record review,
  commit and push on
  `work/migrate-live-routing-catalog-v3-after-release`, and integrate through
  an ordinary reviewed squash PR to `develop`. This task session may not open
  or merge that PR and may not contact the provider.
- The completed release ticket is
  `.10x/tickets/done/2026-08-16-promote-automatic-routing-to-main-once.md`.
  Exact released `main` is
  `R = 4d1efc458fd13b270bf84984ffeb550d5b24fd04`; its ordered parents are
  `[0db802ec1a895f289c7600b19c80603986839873,
  4dad7237baf69989b67270a4afb60d3c0444edfc]` and its tree is
  `a62ac8b774ca66aa4a8ae369daccbe38e0606531`.
- Before the first new provider request, the executor must freshly prove the
  sole normal-use `buoy` executable and package are still exact-R version
  `0.5.2.dev28+g4d1efc458`, both installed migration modules match their
  exact-R source identities recorded in evidence, installed `turbopuffer`
  remains locked version `2.4.0` with `DEFAULT_MAX_RETRIES=4` and the recorded
  retry-loop source identities, and `catalog migrate-routing-v3` help succeeds.
  Any mismatch stops before credentials or provider access.
- The executor must re-observe credential presence without recording the
  credential value and must record the nonsecret exact resolved region at
  execution time. The current exact region is `gcp-us-central1`; any mismatch,
  missing, or ambiguous configuration stops. Recorded command templates use
  `<verified-region>` only as a placeholder; execution substitutes the exact
  value. Preview and any approved command must both bind
  `catalog_namespace=buoy-routing-catalog-v1`, exact region
  `gcp-us-central1`, and `same_resolved_region=true`.
- From the start of preview through independent review, approval, readback,
  and final review, the operator must maintain a routing-catalog mutation
  freeze. Any known concurrent catalog mutation invalidates the preview.

## Phase 1: exact zero-write preview

Run exactly one installed-reader preview:

```text
/Users/crlough/.local/bin/buoy catalog migrate-routing-v3 \
  --region <verified-region> --json
```

The preview must complete one logical strong read and perform zero schema,
card, or content writes, zero deletes, and zero model inference. Preserve a
sanitized JSON result and its whole-output digest. Record:

- observed/target/final schema versions, exact schema fingerprints, and the
  exact three v3 additions;
- literal `catalog_namespace=buoy-routing-catalog-v1` and exact nonsecret
  `region=gcp-us-central1`;
- the 64-character lowercase snapshot revision and projection SHA-256;
- counts, coverage sets, sanitized card identities, inventory comparison, and
  unchanged projection authority;
- `operation_budget`, `operations_performed`, `read_metrics`, every emitted
  `request_summary` category and total, and billing metadata;
- `mutation_status`, `write_attempted` when present, `verification_complete`,
  affected IDs, and every failure or uncertainty; failure-only accounting mode
  and completeness fields are recorded when the CLI emits them.

One logical strong read can require multiple SDK request invocations/pages due
to namespace and card pagination. The emitted `read_metrics` and
`request_summary` count those logical SDK invocations, not physical HTTP
attempts. With the installed SDK's four retries, each logical invocation can
make one through five transport attempts; the exact physical-attempt count is
not observed. Never substitute `strong_read_calls` for the logical SDK total or
mislabel logical counts as physical requests. Do not record credentials, raw
provider rows, passage text, vectors, or unsanitized errors.

## Phase 2: independent preview GO/NO-GO

The review at
`.10x/reviews/2026-08-16-routing-catalog-v3-migration-review.md` must bind the
exact reader identity, preview digest, schema/fingerprints, snapshot revision,
projection, inventory/card identities, exact emitted successful request
metrics/categories/totals/billing,
literal `catalog_namespace=buoy-routing-catalog-v1`, exact
`region=gcp-us-central1`, the same-region assertion, credential-redaction
boundary, and zero-write result. Its initial `pending` fields grant no
authority.

GO is permitted only when the preview is internally exact, accounting is
complete, no write/model/delete occurred, bindings are lowercase 64-character
hex, and any difference from the prior stable audit's 17 namespaces / 13
catalog rows is explained and accepted rather than silently ignored.

- Exact schema v2 is the only state eligible for GO and may proceed to the one
  bound approval below.
- Exact schema v3 requires no migration. The reviewer records
  `no-operation-required`, forbids approval and any schema write, and closes
  from the reviewed exact-v3 preview under the final-state requirements.
- Exact schema v1, unsupported schema, malformed card, unstable read,
  incomplete accounting, failed preview, unexplained inventory drift, leaked
  sensitive data, or any binding ambiguity is NO-GO. Schema v1 requires a
  separately governed v2 operation before a new v3 preview.

Any preview drift requires a new preview and new independent review. A verdict
never transfers between preview outputs.

For exact v2, the sanitized preview evidence and independent GO must be
append-only, committed, pushed, and integrated into `develop` before the
approval command. A local, chat-only, uncommitted, or merely pending verdict
cannot authorize approval. Exact v3 follows the same durable evidence path to
`no-operation-required` closure but never reaches approval.

## Phase 3: one exact bound approval

Only after recorded independent GO on exact schema v2, run at most one command
using the exact values from that same preview:

```text
/Users/crlough/.local/bin/buoy catalog migrate-routing-v3 \
  --expected-snapshot-revision <preview-snapshot-revision> \
  --expected-projection-sha256 <preview-projection-sha256> \
  --approve --region <verified-region> --json
```

The maximum permitted mutation is one Buoy approval command and one logical
SDK schema-write invocation that adds the v3 fields and affects zero rows/IDs,
followed by the command's own second logical strong read. Installed
`turbopuffer 2.4.0` can make one through five transport attempts inside that
single SDK invocation under its four-retry policy while reusing one generated
retry key internally. Those transport attempts are not separately observed by
the CLI. There are zero card/content writes, deletes, model inferences, passage
backfills, and routing-example edits. Exact v3 never reaches this phase.

The repeated pre-write strong read and exact snapshot/projection comparisons
are optimistic drift detection, not a provider-atomic compare-and-swap across
the catalog. The mutation freeze must therefore remain in force through the
write and readback. A mismatch stops before the logical write invocation; a
concurrent mutation or inability to maintain the freeze is a stop condition.

Snapshot or projection drift must fail before a write. Any failed or uncertain
attempt after `write_attempted=true` consumes this ticket's single permitted
operator/SDK write invocation and stops without a second command or rollback,
even though the SDK may already have made up to five transport attempts.
Preserve the emitted exact or known-lower-bound logical accounting and the
physical-attempt bound. Any later attempt requires a fresh preview, new
authority, and new independent review; this ticket can never authorize a
second approval because an outcome is inconvenient or ambiguous.

## Phase 4: readback, review, and closure

For a successful v2 migration, use the approval command's built-in post-write
strong readback; do not issue a separate repeat strong-read command or logical
read. Require:

- exact final schema v3 and expected v3 fingerprint;
- unchanged vector-inclusive projection, inventory, card identities,
  revisions, and coverage;
- exactly the three non-filterable schema additions
  `routing_passages: []string`, `routing_evidence_vectors: []float`, and
  `routing_evidence_vectors_hash: string`;
- affected IDs empty, rows affected zero, and no card/content/model/delete
  operation;
- complete exact logical SDK request accounting on success plus the applicable
  one-through-five transport-attempt bound per logical invocation, separated
  from the earlier diagnostic slices whose physical attempts remain unknown.

Existing cards remain an empty generated-passage bank. This operation does not
make old cards source-aware: only a fresh reviewed plan/apply or separately
governed backfill may populate routing passages and vectors.

Independent post-operation review must record PASS before the evidence becomes
`recorded` and this ticket moves to
`.10x/tickets/done/2026-08-16-migrate-routing-catalog-v3.md`. Closure changes
the evidence/review `Ticket:` links to that done path and durably integrates
the record-only closure. Each phase preserves prior evidence and verdict
history append-only; only current status/verdict/link fields and the ticket
path advance. A reviewed exact-v3 no-write path closes under the same
final-state and accounting requirements.

## Acceptance

- Exact-R reader identity is verified before the first provider request, and a
  pre-v3 reader is never restored to normal use after live v3 exists.
- A successful, fully accounted exact-v2 zero-write preview receives
  independent GO; exact v3 receives `no-operation-required` closure instead.
- Any approval is bound to that exact preview, follows a durably integrated GO,
  and has at most one CLI command / logical SDK schema-write invocation.
- The operation performs no more than one logical schema-only write invocation
  (one through five SDK transport attempts under one internally reused retry
  key) and zero row,
  card, content, model, delete, example, or passage-backfill mutations.
- Final reviewed state is exact v3 with unchanged catalog projection and card
  authority; every logical SDK invocation/category/total/billing entry and
  applicable failure mode is recorded, while physical attempts retain truthful
  one-through-five bounds per invocation.
- Earlier diagnostic physical-attempt counts remain unknown; they are never
  collapsed into the separate five-logical-operation audit or the new logical
  operation totals and transport-attempt bounds.
- Evidence and both phased verdicts close durably without exposing secrets,
  raw rows, passages, or vectors.

## External effects and exclusions

After this ticket integrates and an exact-v2 Preview GO is durably integrated,
the user's request permits only the live reads required by the reviewed
preview/approval contract and at most one CLI approval / logical
schema-v2-to-v3 schema-write invocation, with the SDK's one-through-five
transport-attempt bound and no second operator invocation. It authorizes no
card row or content mutation, passage backfill, plan/apply run, routing-example
edit, namespace deletion, model work, schema rollback, second
operator/CLI/application retry, package install, deployment, tag, GitHub
Release, publication, protection/ruleset
change, direct/force push, credential change, or unrelated operation.

This record-creation task permits only the exact three-file branch, validation,
commit, and task-branch push. It performs no credential or provider access and
grants no PR creation or integration authority to its own session.
