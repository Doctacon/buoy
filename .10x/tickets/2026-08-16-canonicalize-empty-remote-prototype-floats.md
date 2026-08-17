Status: active
Created: 2026-08-16
Updated: 2026-08-16
Specification: .10x/specs/remote-empty-prototype-float-canonicalization.md

# Canonicalize Empty Remote Prototype Floats

## Outcome

Allow the exact remote reader to restore an otherwise valid empty-prototype
schema-v2/v3 card when Turbopuffer serializes its non-ANN float array within
the same float32 buckets as the already-canonical base vector.

## Scope

- Apply the existing float32 canonicalizer to provider-returned
  `routing_prototype_vector` values before persisted card validation, regardless
  of evidence count.
- Preserve every local card byte, hash, revision, writer, schema, routing,
  model, request, and content behavior.
- Add same-bucket acceptance and adjacent-bucket fail-closed regressions for an
  empty prototype bundle.
- Run focused/full supported-Python validation, source/distribution checks,
  independent review, and prepare the normal work-to-develop PR handoff.

## Acceptance

- The exact live failure shape—stored canonical hash/revision, zero examples,
  and provider decimal drift—parses without changing either identity scalar.
- Adjacent float32 buckets remain rejected as stale.
- Existing non-empty prototype, schema-v1, base-vector, and remote-catalog tests
  remain green.
- No provider, credential, model, schema, card/content write, migration,
  publication, or history rewrite occurs in this source task.

## External effects

None. Live catalog preview/migration resumes only after this exact compatible
reader reaches `main` and replaces the installed tool.
