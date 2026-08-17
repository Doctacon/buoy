Status: done
Created: 2026-08-16
Updated: 2026-08-16
Specification: .10x/specs/remote-empty-prototype-float-canonicalization.md
Evidence: .10x/evidence/2026-08-16-empty-remote-prototype-float-canonicalization.md
Review: .10x/reviews/2026-08-16-empty-remote-prototype-float-canonicalization-review.md

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

The task branch was pushed, draft PR #118 was opened, and its hosted CI ran.
No merge, deployment, provider request or mutation, model call, live migration,
publication, tag, Release, README change, branch-protection change, or history
rewrite occurred. Live catalog preview/migration resumes only after this exact
compatible reader reaches `main` and replaces the installed tool.

## Closure

- Implementation commit:
  `6ad5e1c85d33d8e63b568fda8abbedc44b233125`.
- PR #118 targets exact `develop@7e55f73bb6df428bddd24aa9db80039ba0809923`;
  hosted CI run `31988110171` passed Python 3.11 job `95266561616`, Python 3.13
  job `95266561637`, and distribution job `95266865418`.
- Complete Python 3.11 and 3.13 suites each passed `851/851`; source,
  distribution, ranking, C6, lock, compile, and diff validation passed.
- Evidence:
  `.10x/evidence/2026-08-16-empty-remote-prototype-float-canonicalization.md`.
- Independent review:
  `.10x/reviews/2026-08-16-empty-remote-prototype-float-canonicalization-review.md`
  (PASS).
- No live card/schema/content mutation, model inference, publication, tag,
  Release, README change, branch-protection change, or history rewrite occurred.
