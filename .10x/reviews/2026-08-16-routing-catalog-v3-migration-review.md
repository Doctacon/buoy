Status: pending
Created: 2026-08-16
Updated: 2026-08-16
Target: exact three-record authority plus future live preview, operation, and closure
Ticket: .10x/tickets/2026-08-16-migrate-routing-catalog-v3.md
Evidence: .10x/evidence/2026-08-16-routing-catalog-v3-migration.md
Decision: .10x/decisions/buoy-derives-routing-prototypes-from-reviewed-plans.md
Specification: .10x/specs/automatic-routing-after-apply.md
Record-Verdict: pass
Preview-Verdict: pending
Post-Operation-Verdict: pending

# Live Routing Catalog V3 Migration Review

## Record authority review

Independent records-phase review bound exact task base / current develop
`D0 = 31d2a7756c5bd712147772a77b606154fb2610c3` with tree
`efc512005e3f31f9b26da408473324c35fc15774` and these settled candidate
identities:

- `.10x/tickets/2026-08-16-migrate-routing-catalog-v3.md` blob
  `28c832131ad097304763a515430ad6e7c7cb6dd5`;
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

## Pending verdicts

- Preview verdict: pending; no live preview has been reviewed.
- Post-operation verdict: pending; no v3 operation has been reviewed.
