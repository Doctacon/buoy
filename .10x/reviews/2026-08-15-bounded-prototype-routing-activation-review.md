Status: pass
Created: 2026-08-15
Updated: 2026-08-15
Ticket: .10x/tickets/2026-08-15-activate-bounded-prototype-routing.md
Specification: .10x/specs/bounded-prototype-routing-activation.md
Decision: .10x/decisions/buoy-activates-certified-bounded-prototype-routing.md
Evidence: .10x/evidence/2026-08-15-bounded-prototype-routing-activation.md

# Bounded Prototype Routing Activation Review

## Scope and exact path boundary

This independent final review examined the complete artifact-phase delta after
the final clean dormant commit
`d171cd887f615158a196dbeef8fa93830818ea64`, tree
`184c7cd83ad5d93591d05bb1d286d07941c360b1`. Before this review record was
created, the exact post-dormant path boundary was:

```text
.10x/evidence/2026-08-15-bounded-prototype-routing-activation.md
.10x/tickets/2026-08-15-activate-bounded-prototype-routing.md
src/buoy_search/data/automatic_routing_confidence_calibration.json
```

This review record is the sole additional path created by the reviewer. No
production source, evaluator, test, workflow, user documentation, packaged
canary, specification, or decision changed after `d171cd8`. The final evidence
reviewed here had exact raw SHA-256
`11257bc756a2d268c8d463f3d0c0ad3136c0e36090523a5b99e729ec3f9a3b46`.

## Dormant certification and active authority

The active artifact is exactly
`src/buoy_search/data/automatic_routing_confidence_calibration.json`, 2671
bytes, raw SHA-256
`3412bdb20f928de226e159344cac04ec52587da4134d6c079e9fc53a6aa75d9d`.
Strict no-argument loading returns schema version `2`, calibration ID/revision
`automatic-routing-confidence-v2` / `active-16357c62-e559a8aa-v1`,
`mode=active`, `owner_approved=true`, and a passing certification. The loader
rejects alternate-path active authority and recomputes the bound package
module bytes before returning active state.

The artifact preserves the original authorization report at SHA-256
`d9369f82d47d17fd0a7388246348c258d97b12f956ca9796e3afaa5442255a9d`,
source commit `16357c629a96e4b309592917ad479a163cec3047`, and tree
`c002897fc3224faae9c8670f785e906884100890`. Its operative dormant receipt is
the superseding clean report at raw SHA-256
`6b02379f20147d004ff03cd2d90cdb6bd820e8f008be42d218578981f6db5977`,
bound to exact commit/tree
`d171cd887f615158a196dbeef8fa93830818ea64` /
`184c7cd83ad5d93591d05bb1d286d07941c360b1` with
`certified_dormant_working_tree_clean=true`. The earlier `a8190f3` report is
superseded history and is not used as active authority.

Independent parsed-object comparison established that the superseding report
reproduces the original report's complete catalog, threshold calibration, all
65 candidate observations, all 65 legacy observations, candidate and legacy
metrics, quality verdict, call accounting, and read-only boundary. The frozen
authority receipts are:

- canary suite:
  `0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5`;
- eligible catalog projection:
  `e559a8aac5a4f7fb808f137b1c6a3710b6cd5b6764fc84f7f06120e33307ef7c`;
- score floor / margin floor: `-10.167728424072266` /
  `1.0735645294189453`;
- calibration count / ordered-ID digest: `6` /
  `23a863f53b44ec741185bf27f903824931dd9d84bd08e907c8f2b94e1f70ce1f`,
  with zero incorrect high-confidence singletons;
- certification count / ordered-ID digest: `59` /
  `536a6417f0882ac073d7f4cedda30c05594b5ae9447a998e62d264677ca69149`;
  and
- passing quality-verdict digest:
  `cb26318f93e61ed7874bfe4db5139f2f3eb2bdc52d1d3908c278ce9e2f8aca4d`.

The exact packaged canary raw-byte receipts are:

- RentPTR:
  `5a39c38d302cbc5c6d758b1e48d4456456a4357248f559a6cf56e0234742f4f5`;
- Salesforce:
  `32106e02d877788e676cdb3db3f7a3567f57f96fa009a7a558b82ca1d407d13d`;
  and
- WhiteboxGeo:
  `5558a4e8a786f0a5553ba0237ebf8248a5d576bd1937ffd69cf9af66a8ac0916`.

The artifact's source and prior-authority receipts reproduce the raw bytes of
the final dormant commit:

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

## Validation and distribution review

Parent-observed final validation recorded `152/152` focused
activation/routing/evidence/package tests and `805/805` full repository tests
under both ticket-required interpreters, Python 3.11 and Python 3.13. It also
recorded passing frozen-ranking and C6 forecast validation, compilation, diff
hygiene, and source-release validation. The reviewer independently reran the
strict source and distribution validators against the exact active delta;
both passed with the artifact, module, runner, canary, suite, and inventory
receipts above.

The reviewed diagnostic distributions are a 69-file wheel at SHA-256
`d617e9065b62ec1dcb5925da0015e474893fc06c0d9638438b8c59f73feee9d4`
and a 140-file source distribution at SHA-256
`e9309364a03f2ed244939eaf47d9faca27a1378a9284f0172dba7a44782d70ec`.
They agree with source on the active artifact, four package-module receipts,
the exact three-canary inventory, and the 65-case suite; the source
distribution additionally reproduces the evaluator-runner receipt.

A stricter installed-wheel rerun used isolated/no-bytecode interpreter mode,
removed the editable source entry, inserted the wheel's isolated installation
site, and supplied the complete locked Python 3.11 dependency runtime. It
proved that every loaded `buoy_search` module resolved from that installed
site. The no-argument loader returned `mode=active`, `owner_approved=true`,
revision `active-16357c62-e559a8aa-v1`, dormant source commit
`d171cd887f615158a196dbeef8fa93830818ea64`, and artifact SHA-256
`3412bdb20f928de226e159344cac04ec52587da4134d6c079e9fc53a6aa75d9d`.
This wording does not claim that the retained no-dependencies installation
venv alone contains the project's runtime dependency set.

## Privacy and external effects

The final live certification made 65 routing-query inferences and 65 local
reranker calls over 3185 passages, with at most 49 passages in one call. Its
provider accounting records two namespace-list pages, one metadata request,
two catalog-query pages, zero shortlist/per-card queries, zero content
queries, zero writes, zero content-resource acquisitions, and zero model
downloads. Provider mutation methods were not exposed. Independent scanning
found none of the 65 governed questions and no routing example, passage,
vector contents, payload, credential, or environment secret in the report.

No schema, namespace, card, example, content row, credential, or provider
state was written or deleted. No package was published, and no tag, GitHub
Release, registry object, deployment, integration, push, or pull request was
created by this activation review. The reviewer made no provider or model
call and did not commit, merge, deploy, release, or publish.

This evidence certifies live route selection only. Downstream retrieval,
evidence widening, partial failure, result-reranker reuse, compact output, and
JSON behavior are local regression claims, not provider-backed active answer-
quality or result-reranking certification. A valid schema-v1 collect artifact
preserves the legacy selector; invalid or failing active authority never
silently falls back to it.

## Verdict and remaining gates

GO for the exact artifact, ticket, final evidence, and this review record
bounded above. No P1 or P2 finding remains. The task branch is ready for its
final commit and handoff validation; this GO is not integration, publication,
deployment, or release authorization.

The exact final commit does not yet exist. After committing only the bounded
four-path artifact-phase delta, the task owner must build and validate the
wheel and source distribution from that exact commit, repeat the installed-
wheel no-argument authority smoke under the complete locked dependency
runtime without the source checkout on the import path, and record the final
commit/tree and archive hashes. The branch must still incorporate current
`develop` if it advanced, rerun every ticket-required check affected by that
incorporation, push the exact reviewed head, open the pull request to
`develop`, and confirm required checks. The task session must not merge its
own pull request.

Any source, evaluator, test, workflow, documentation, canary, specification,
decision, artifact-authority, receipt, or behavior change after this review is
a STOP and requires renewed review. Any production-source or authority change
that invalidates the dormant report boundary requires returning to the
dormant certification stage rather than repairing forward from the active
artifact.
