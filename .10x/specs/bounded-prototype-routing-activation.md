Status: active
Created: 2026-08-15
Updated: 2026-08-15
Decision: .10x/decisions/buoy-activates-certified-bounded-prototype-routing.md
Amends: .10x/specs/scalable-routing-quality.md

# Bounded Prototype Routing Activation

## Frozen authorization envelope

The activation is authorized only for the candidate represented by this exact
independently audited report:

- report SHA-256:
  `d9369f82d47d17fd0a7388246348c258d97b12f956ca9796e3afaa5442255a9d`;
- certified candidate source commit/tree:
  `16357c629a96e4b309592917ad479a163cec3047` /
  `c002897fc3224faae9c8670f785e906884100890`;
- canary suite SHA-256:
  `0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5`;
- eligible-card semantic projection SHA-256:
  `e559a8aac5a4f7fb808f137b1c6a3710b6cd5b6764fc84f7f06120e33307ef7c`;
- score floor `-10.167728424072266` and margin floor
  `1.0735645294189453`;
- calibration count/digest `6` /
  `23a863f53b44ec741185bf27f903824931dd9d84bd08e907c8f2b94e1f70ce1f`,
  with zero incorrect high-confidence singletons;
- certification count/case-ID digest `59` /
  `536a6417f0882ac073d7f4cedda30c05594b5ae9447a998e62d264677ca69149`;
  and
- passing quality-verdict digest
  `cb26318f93e61ed7874bfe4db5139f2f3eb2bdc52d1d3908c278ce9e2f8aca4d`.

The verdict digest is SHA-256 over the stable compact JSON encoding of the
complete `quality_verdict` object. The candidate found `67/67` required routes,
achieved exact per-corpus Recall@3 and shortlist Recall@12 of `1.0`, produced
zero incorrect/no-answer high-confidence singletons, averaged
`1.5932203389830508` initial corpora, and never exceeded three. The same-snapshot
legacy selector found `63/67` and averaged `2.0338983050847457`.

These values are an approval envelope, not permission to substitute a nearby
threshold, suite, projection, model, report, or source revision.

## Packaged ground-truth input

The exact approved extension to the legacy 50-case projection is packaged at
these paths with these raw-byte SHA-256 identities:

- `src/buoy_search/data/routing_canaries/rentptr.json`:
  `5a39c38d302cbc5c6d758b1e48d4456456a4357248f559a6cf56e0234742f4f5`;
- `src/buoy_search/data/routing_canaries/salesforce.json`:
  `32106e02d877788e676cdb3db3f7a3567f57f96fa009a7a558b82ca1d407d13d`;
  and
- `src/buoy_search/data/routing_canaries/whiteboxgeo.json`:
  `5558a4e8a786f0a5553ba0237ebf8248a5d576bd1937ffd69cf9af66a8ac0916`.

The bytes must be identical to the three owner-approved current external
packs; activation does not authorize relabeling, rewriting, regenerating, or
normalizing them. The existing suite construction over those three files and
the unchanged approved legacy dataset MUST reproduce
`0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5`.
The dormant certification uses this packaged default directory, not a
`/private/tmp` canary dependency.

The four disabled FleetDeck, FleetShield, OrbitStock, and OrbitWatch synthetic
fixture packs remain external. They do not enter the current 65-case suite,
the active artifact, the package, or ordinary routing, and their disabled cards
remain untouched.

The source tree, wheel, and source distribution contain exactly these three
JSON members under `buoy_search/data/routing_canaries/`, with no synthetic
fixture pack or additional canary file. Source/distribution inventory and
clean-install tests hash each member and reconstruct the exact suite digest.
Runtime automatic routing does not read question text from these packs; they
are packaged solely as the reproducible governed evaluation input.

## Ordered activation state machine

### 1. Dormant wiring

Implement strict loader and production routing wiring while retaining the
existing packaged v1 collect artifact byte-for-byte. Commit that bounded source
and test change on the task branch. With a valid collect artifact, ordinary
automatic retrieval MUST continue to call the legacy hybrid route and emit its
current strategy, selections, confidence behavior, and call accounting.

The dormant commit must be clean before collection. No active artifact may be
written in the same uncommitted state as the wiring, and no commit or tree
identity may be predicted.

### 2. Dormant-source certification

Run the same source-only `scripts/evaluate_routing_quality.py collect` flow
against the packaged default exact 65-case suite and live catalog from the
clean dormant commit. The run is read-only and MUST report:

- the three exact packaged canary hashes, the same suite, catalog projection,
  thresholds, calibration receipt, certification count/digest, and
  quality-verdict digest frozen above;
- every quality check passing and no regression from the same-snapshot legacy
  baseline;
- zero content queries, shortlist/per-card provider queries, provider writes,
  and model downloads; and
- clean source identity plus exact runner, scorer, collect-artifact,
  `src/buoy_search/routing.py`, `src/buoy_search/cli.py`, and
  `src/buoy_search/evidence.py` hashes.

The report provenance uses SHA-256 over the exact raw bytes of those three
files from the clean dormant checkout and names them `routing_module_sha256`,
`cli_module_sha256`, and `evidence_module_sha256`. Missing fields or a value
that does not reproduce from the dormant checkout stops activation.

Any changed frozen value, dirty source, projection drift, failed check,
unexpected request class, or mutation stops activation. It requires diagnosis
and, for any changed result or authority, new owner approval. The dormant
report receives an independent exact-artifact audit before the packaged
artifact changes.

### 3. Artifact-only activation

After that audit, change the packaged confidence JSON from collect to active.
Apart from final governance/evidence updates, no production behavior source may
change after the certified dormant commit. If a source repair is required,
return to step 1 and produce a new clean dormant report.

The active artifact is strict JSON with duplicate-key rejection and exact
schema version `2`. It has exactly these top-level fields and no others:

```text
schema_version
calibration_id
calibration_revision
mode
owner_approved
score_floor
margin_floor
bindings
calibration
certification
receipts
```

The exact scalar values are:

```text
schema_version = 2
calibration_id = automatic-routing-confidence-v2
calibration_revision = active-16357c62-e559a8aa-v1
mode = active
owner_approved = true
score_floor = -10.167728424072266
margin_floor = 1.0735645294189453
```

`bindings` has exactly these fields and values:

```text
routing_model = BAAI/bge-small-en-v1.5
routing_model_revision = 5c38ec7c405ec4b44b94cc5a9bb96e735b38267a
routing_reranker_model = cross-encoder/ms-marco-MiniLM-L-6-v2
routing_reranker_revision = c5ee24cb16019beea0893ab7796b1df96625c6b8
schema_contract = remote-routing-card-schema-v1-v2
projection = separate_prototype_vector_normalized_mean_v1
shortlist_limit = 12
max_examples = 8
feature_contract = max_prototype_score_and_margin_v1
score_field = reranker_score
margin_field = reranker_margin
canary_suite_sha256 = 0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5
catalog_projection_sha256 = e559a8aac5a4f7fb808f137b1c6a3710b6cd5b6764fc84f7f06120e33307ef7c
```

`calibration` has exactly:

```text
case_count = 6
case_ids_sha256 = 23a863f53b44ec741185bf27f903824931dd9d84bd08e907c8f2b94e1f70ce1f
incorrect_high_confidence_singletons = 0
```

`certification` has exactly:

```text
passed = true
case_count = 59
case_ids_sha256 = 536a6417f0882ac073d7f4cedda30c05594b5ae9447a998e62d264677ca69149
verdict_sha256 = cb26318f93e61ed7874bfe4db5139f2f3eb2bdc52d1d3908c278ce9e2f8aca4d
```

`receipts` has exactly these fields:

```text
authorization_report_sha256
authorization_source_commit
authorization_source_tree
certified_dormant_report_sha256
certified_dormant_source_commit
certified_dormant_source_tree
certified_dormant_working_tree_clean
evaluator_runner_sha256
evaluator_scorer_sha256
collect_artifact_sha256
routing_module_sha256
cli_module_sha256
evidence_module_sha256
```

The first three values are the frozen report/commit/tree above. The dormant
working-tree value is exactly `true`. Every other dormant value is copied from
the independently audited clean dormant report; each digest is 64 lowercase
hex and each commit/tree is the exact full Git object ID observed after the
dormant commit. A placeholder, guessed identity, missing receipt, or receipt
from a different report fails review and loading. The active artifact's own
SHA-256 is recorded externally in final evidence because self-hashing would be
circular.

The active loader hashes the exact installed raw bytes of
`buoy_search/routing.py`, `buoy_search/cli.py`, and
`buoy_search/evidence.py` and requires equality with the three corresponding
receipt fields before returning an active calibration. It does not trust Git
metadata or an editable-worktree path as a substitute. Build and installed-
distribution tests extract/read the packaged module bytes and require the same
three hashes, so squash integration cannot erase the durable source identity.
The exact v1 collect loader does not claim or require active source receipts.

The existing exact v1 collect shape remains the sole supported inactive shape:
`mode=collect`, `owner_approved=false`, null thresholds/binding digests, and a
non-passing zero-case certification. A schema-v1 active artifact, schema-v2
collect artifact, or any other mixture is invalid.

## Runtime selection and fail-closed boundary

Production automatic retrieval MUST load only the installed package resource;
the CLI, environment, runtime configuration, and public retrieval surface have
no artifact-path, mode, threshold, or strategy override. Internal fixture/path
injection may exist only below the production boundary for tests and the
source-only evaluator.

Explicit repeated `--namespace` values are resolved before automatic state and
continue to bypass the catalog, confidence artifact, route embedder, and route
reranker exactly as today.

For automatic retrieval:

1. load and strictly validate the packaged artifact;
2. perform and validate the existing complete, stable catalog read;
3. for active mode, compute the semantic projection over exactly the eligible
   cards and require equality with the artifact's
   `e559a8aac5a4f7fb808f137b1c6a3710b6cd5b6764fc84f7f06120e33307ef7c`;
   collect mode has no projection authority and continues to the legacy route;
4. only then construct routing models and select a route; and
5. only after selection may the CLI construct content configurations/resources
   or issue a content query.

A valid collect artifact calls the unchanged legacy hybrid route. A valid
active artifact passes the complete validated artifact object into the bounded
prototype route; loose score/margin parameters are forbidden. Missing package
data, I/O failure, duplicate/extra/missing fields, wrong types or identities,
non-finite thresholds, false approval/certification, receipt mismatch,
catalog-projection mismatch, prototype/reranker failure, or malformed card
state produces one redacted automatic-routing error before content access. An
advertised active strategy never silently falls back to legacy routing.

With a valid active artifact, exact title/alias selection remains authoritative.
For descriptor-free routing, the top corpus receives initial fanout one only
when its finite maximum prototype reranker score is at least the score floor
and its finite top-one/top-two margin is at least the margin floor. Otherwise
the first three reranked corpora, or all eligible corpora when fewer than
three, form the initial fallback. A single eligible corpus has no margin and
does not receive semantic singleton confidence. Selected and fallback lists
remain unique and capped at three.

Routine JSON/text output exposes artifact ID/revision, strategy, thresholds,
score/margin, selection reason, and bounded hashes/ranks already allowed by the
scalable-routing contract. It never exposes questions, routing-example text,
vectors, credentials, provider payloads, or raw exceptions.

## Rollback

The rollback unit is the deployed build. The prior known legacy-router build is
source commit `16357c629a96e4b309592917ad479a163cec3047`, tree
`c002897fc3224faae9c8670f785e906884100890`. It contains the compatible schema-v2
reader and collect-only artifact while production still calls the legacy
hybrid route.

Rollback deploys that prior build. It MUST NOT delete schema-v2 fields, clear
routing examples, rewrite or disable cards, alter content, or add a runtime
legacy escape hatch. Rollback deployment and any `main` change remain separate
release operations with exact authorization.

## Validation and integration gates

Before task handoff:

- preserve and record the dormant commit/tree/report boundary;
- run focused loader, artifact, routing, CLI, explicit-bypass, call-order,
  projection-drift, output-redaction, evaluator, package-inventory, and
  distribution tests on Python 3.11 and 3.13;
- prove dormant report provenance emits the exact routing/CLI/evidence module
  hashes, the active loader rejects each independent module-hash mismatch, and
  wheel/sdist/installed bytes reproduce every module receipt;
- prove source, wheel, sdist, and installed inventory contain exactly the
  RentPTR, Salesforce, and WhiteboxGeo pack paths above, reproduce each raw
  hash and suite digest, and contain none of the four synthetic fixture packs;
- prove all malformed/collect/active state combinations, non-finite numbers,
  alternate-path attempts, catalog drift, and model failures stop before any
  content resource/query;
- prove dormant collect behavior is selection-compatible with current legacy
  routing and active behavior matches the certified threshold semantics;
- run the full Python 3.11 and 3.13 suites, locked-dependency validation,
  source-release validation, compilation, wheel/sdist validation, and clean
  installed-wheel smokes;
- run `git diff --check`, a trailing-whitespace audit, secret/privacy checks,
  and a scoped changed-path audit;
- perform no provider/schema/card/content mutation and no tag/package/release
  publication; and
- obtain independent review of the exact final commit, active artifact,
  dormant report and production-module bindings, tests, and complete branch
  diff.

The task branch incorporates current `develop`, reruns required validation,
commits only bounded owned paths, and may open a passing PR to `develop`.
The task session does not merge itself. Exact PR-to-`develop` integration and
later `develop`-to-`main` release promotion are distinct actions requiring
current-head evidence and explicit authorization; activation is not deployed
merely because the task branch contains an active artifact.

## External-effect boundary

Implementation, artifact packaging, tests, dormant collection, and review make
no provider mutation. They do not write schemas, routing cards, content rows,
namespaces, credentials, tags, releases, or packages. The dormant collector
also makes zero content queries. This specification does not authorize any
catalog repair if projection drift occurs.
