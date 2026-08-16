Status: recorded
Created: 2026-08-15
Updated: 2026-08-15
Ticket: .10x/tickets/2026-08-15-activate-bounded-prototype-routing.md

# Bounded Prototype Routing Activation Evidence

## Result

The task branch now packages the owner-approved schema-v2 active authority for
bounded prototype routing. Automatic descriptor-free retrieval uses the
certified prototype shortlist and local reranker; exact title/alias routing,
explicit namespaces, maximum fanout three, content retrieval, evidence
assessment, result ranking, compact output, and JSON contracts retain their
governed boundaries.

This is task-branch readiness, not integration, publication, or deployment.
No `develop` or `main` branch, installed user command, tag, release, package
registry, or provider resource changed in this activation checkpoint.

## Ordered source and certification receipts

The first clean dormant wiring commit was
`a8190f3a0284b876f46ff5616eb9d9d9b26d2d65`, tree
`3b16198bbb826f5bf6c2dcfdf5e663a8604e0c5f`. Its read-only report exposed
three phase-coupled test assumptions when the packaged authority was simulated
as active. The authority was restored to the exact collect bytes before any
further commit. No production or evaluator source was changed.

The independently reviewed test-only repair was committed as
`d171cd887f615158a196dbeef8fa93830818ea64`, tree
`184c7cd83ad5d93591d05bb1d286d07941c360b1`. It changed only the test fixture,
two evaluator/package test files, and its review record. The final clean
dormant certification is:

- report
  `/private/tmp/buoy-routing-activation-cert-d171cd8.XLW6iQ/routing-quality-65.d171cd8.json`;
- mode `0600`, 384955 bytes, raw SHA-256
  `6b02379f20147d004ff03cd2d90cdb6bd820e8f008be42d218578981f6db5977`;
- exact clean commit/tree `d171cd887f615158a196dbeef8fa93830818ea64` /
  `184c7cd83ad5d93591d05bb1d286d07941c360b1`;
- suite
  `0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5`;
- eligible catalog projection
  `e559a8aac5a4f7fb808f137b1c6a3710b6cd5b6764fc84f7f06120e33307ef7c`;
- score/margin floors `-10.167728424072266` /
  `1.0735645294189453`;
- six calibration cases, ordered-ID digest
  `23a863f53b44ec741185bf27f903824931dd9d84bd08e907c8f2b94e1f70ce1f`,
  with zero incorrect high-confidence singletons;
- 59 certification cases, ordered-ID digest
  `536a6417f0882ac073d7f4cedda30c05594b5ae9447a998e62d264677ca69149`;
  and
- passing quality-verdict digest
  `cb26318f93e61ed7874bfe4db5139f2f3eb2bdc52d1d3908c278ce9e2f8aca4d`.

The complete catalog, threshold calibration, all 65 candidate observations,
all 65 legacy observations, both complete metric objects, quality verdict,
call accounting, and read-only boundary are exactly equal as parsed objects to
the original owner-approved report at SHA-256
`d9369f82d47d17fd0a7388246348c258d97b12f956ca9796e3afaa5442255a9d`.
Candidate routing remains `67/67`, every eligible corpus remains at exact
Recall@3 and shortlist Recall@12 of `1.0`, average initial fanout is
`1.5932203389830508`, maximum fanout is `3`, all `23/23` named and `10/10`
multi-corpus cases pass, and no incorrect or no-answer confident singleton
exists. The same-snapshot legacy selector remains `63/67` with average fanout
`2.0338983050847457`.

The first report from `a8190f3`, SHA-256
`331adfd845a2433f519ebf7a31394e6319802962a210c99aad578337851b4f3d`,
is retained only as superseded audit history. It is not an active-authority
receipt.

## Active authority

The exact packaged artifact is
`src/buoy_search/data/automatic_routing_confidence_calibration.json`, schema
version `2`, ID/revision `automatic-routing-confidence-v2` /
`active-16357c62-e559a8aa-v1`, `mode=active`, owner approved, certification
passing, 2671 bytes, raw SHA-256
`3412bdb20f928de226e159344cac04ec52587da4134d6c079e9fc53a6aa75d9d`.

It binds both the original authorization and the final dormant report plus
these exact raw source receipts:

- evaluator runner `scripts/evaluate_routing_quality.py`:
  `6f179cb93ef85754e05e86bf8f300f1d430aefa34cccbf3ae7e23feb618402cc`;
- evaluator scorer `src/buoy_search/routing_quality.py`:
  `be8792b94698f8775760988583eb912a187da666a03f6a0ae234b4d26d014079`;
- routing module `src/buoy_search/routing.py`:
  `340f7f804923dad9a9fb0c563507b3cdb807260e7713dbeffe881138921198c5`;
- CLI module `src/buoy_search/cli.py`:
  `27fef95c69a82fe733863b193e44bbe9821383a49e02321a1bfda184b1ea9dff`;
- evidence module `src/buoy_search/evidence.py`:
  `78b792098ee0c49bedc7c135dffc33f4096f7d92222bc437f5d8438f1e015c7b`;
  and
- prior collect artifact:
  `23fb14c49263933a2adb2299a9c04089888fb2ec734b790d9eadda2df295cbed`.

The source no-argument loader returns only this active authority after
recomputing the installed scorer/routing/CLI/evidence hashes. A valid
schema-v1 collect artifact preserves the legacy selector. Invalid,
unapproved, malformed, drifted, or model-failing automatic state stops before
content construction, and an active-path failure never falls back to the
legacy selector. Explicit namespaces bypass this authority and every
automatic dependency.

## Calls and external effects

The final live certification made exactly 65 routing-query inferences, 65
bounded local reranker calls over 3185 passages (49 maximum per call), two
namespace-list pages, one metadata request, and two catalog-query pages. It
made zero shortlist/per-card provider queries, zero content queries, zero
provider writes, zero content-resource acquisitions, and zero model downloads.
The superseded certification made the same read-only calls before its test-only
gate was corrected. Neither run exposed mutation methods.

No schema, namespace, card, example, content row, credential, or provider state
was written or deleted. The report privacy audits found no canary question,
routing example, passage, vector contents, payload, credential, or environment
secret. No package was published, and no tag, GitHub Release, registry object,
or deployment was created.

## Validation

The final active tree passed:

- `152/152` focused activation/routing/evidence/package tests under Python
  3.11 and `152/152` under Python 3.13;
- `805/805` full repository tests under Python 3.11 and `805/805` under Python
  3.13;
- exact source-release validation with active module and evaluator-runner
  receipts, frozen ranking validation, C6 forecast validation, compilation,
  and diff hygiene;
- a real 69-file diagnostic active wheel at SHA-256
  `d617e9065b62ec1dcb5925da0015e474893fc06c0d9638438b8c59f73feee9d4`
  and 140-file diagnostic active source distribution at SHA-256
  `e9309364a03f2ed244939eaf47d9faca27a1378a9284f0172dba7a44782d70ec`;
  and
- source/wheel/source-distribution agreement on the exact artifact, three
  approved canaries, 65-case suite, four installed module receipts, and
  source-distribution evaluator-runner receipt. The wheel's installed package
  bytes, run without the source checkout on the import path under the complete
  locked dependency runtime, returned the active approved revision and the
  final dormant commit receipt through the no-argument loader.

The diagnostic active archives identify the uncommitted artifact phase and are
not publication artifacts. An exact post-commit build remains the final
handoff check.

Route selection is live-certified. Downstream retrieval, evidence widening,
partial failure, result-reranker reuse, compact output, and JSON behavior are
covered by local integration/full-suite regressions; this evidence does not
claim a provider-backed active answer-quality or result-reranking
certification. The fixed four-corpus provider evaluator remains a separately
governed future modernization.

Rollback remains deployment of the prior schema-v2-reader-compatible legacy
selector build at `16357c629a96e4b309592917ad479a163cec3047`. It is not a
runtime fallback, artifact override, schema/card mutation, or v1-only binary.
