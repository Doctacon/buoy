Status: active
Created: 2026-08-15
Updated: 2026-08-15
Decision: .10x/decisions/routing-catalog-v2-migration-is-reader-first-and-revision-bound.md
Specification: .10x/specs/routing-catalog-v2-migration.md

# Migrate Routing Catalog V2 and Reviewed Examples

## Outcome

After the compatible reader is integrated and deployed, provide one bounded,
preview-first operator for adding the exact four-field routing-prototype schema
bundle and one bounded operator for conditionally updating only a card's
reviewed routing examples. Production routing remains the legacy base-vector
selector throughout this ticket.

## Scope

- Add `buoy catalog migrate-routing-v2` with a zero-write preview and an
  approval path bound to the exact observed catalog snapshot and projection.
- The approved migration performs one schema-only Turbopuffer write, no row
  write, no content write, and no delete, then proves an exact v2 strong read.
- Add `buoy catalog set-routing-examples NAMESPACE` with a zero-write preview
  and an approval path bound to the exact observed card revision.
- The approved example edit preserves every non-prototype card field and the
  exact legacy semantic hash/vector/hash, performs one conditional card-row
  write, and proves the resulting card through strong readback.
- Preserve reviewed routing examples across every later ordinary apply,
  including generated website cards. Source generation may neither invent nor
  clear operator-owned routing examples.
- Add exact JSON/text output, redacted failures, request accounting, focused
  tests, public documentation, evidence, and independent review.

## Acceptance

- Both commands fail before mutation on wrong schema, snapshot, projection,
  card revision, inventory drift, malformed examples, incompatible reader, or
  provider/model error.
- Migration preview performs no model inference and zero provider writes. It
  binds the complete v1 snapshot, every namespace/card revision, the
  vector-inclusive catalog projection, exact four schema additions, and the
  old-reader incompatibility warning.
- Migration approval requires both expected snapshot revision and expected
  projection SHA-256, repeats the strong read, performs exactly one schema-only
  request, and proves v2 has the same rows, revisions, base vectors, and card
  projection. Already-exact v2 is an idempotent zero-write success.
- Example preview performs at most the required local projection inference and
  zero provider writes. Approval requires an exact expected card revision and
  repeats the strong read before model work.
- Example approval changes only `updated_at`, `card_revision`, and the exact
  four-field routing-prototype bundle. The write is conditional on the observed
  card revision and must affect exactly the intended deterministic row ID.
- Existing reviewed examples survive ordinary generated and manual card
  refreshes while verified source, retrieval, and lineage fields continue to
  advance normally.
- No command changes the production router, confidence artifact, content
  namespace, content row, enablement, title, summary, alias, tag, retrieval
  contract, lineage, credential, package release, or publication state.
- Focused and full Python 3.11/3.13 tests, source/distribution validation, clean
  install, diff checks, exact live previews, and independent review pass before
  any approved provider mutation.

## External effects

Source implementation and tests are provider-inert. After review, the owner has
authorized one exact shared-catalog schema mutation and conditional reviewed
example updates under the command contracts above. Every mutation requires a
fresh strong read, exact expected digests/revisions, a recorded preview, and an
independent go/no-go review. Any drift stops and requires a new preview.

## Exclusions

Routing activation, confidence-threshold approval, content reindexing, content
namespace writes, card enable/disable, card semantic rewrites, generated
routing examples, bulk unbound
upserts, prototype ANN indexing, second catalogs, overlays, rollback by schema
deletion, tags/aliases derived from examples, and cleanup deletion of the four
test corpora.

## Blockers

- Checkpoint-one reader promotion/deployment, the exact reviewed examples and
  owner-approved canary freeze, checkpoint-two source validation, and the
  independent source PASS are complete and recorded in the evidence/review.
- The migration operator must still be integrated and deployed from its exact
  reviewed commit before any live preview or provider mutation.
- A fresh live schema-v1 preview requires working catalog credentials, exact
  snapshot/projection capture, and a separate independent go/no-go before the
  one schema-only approval request. Every example update then requires its own
  fresh revision-bound preview and readback.
