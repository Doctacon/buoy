Status: recorded
Created: 2026-08-15
Updated: 2026-08-15
Ticket: .10x/tickets/2026-08-15-activate-bounded-prototype-routing.md

# Bounded Prototype Routing Activation Authorization

## Owner direction

After the three routing-quality checkpoints completed, the owner was told that
the new router scored `67/67` routes versus the current selector's `63/67`,
that every corpus achieved Recall@3 of `1.0`, that average initial fanout fell
from `2.0338983050847457` to `1.5932203389830508`, and that the candidate was
deliberately not active. The owner then directed: “yes activate.”

This records implementation authority for the bounded activation contract. It
does not claim that activation has been implemented, reviewed, integrated,
released, deployed, or observed in ordinary retrieval.

## Independently audited authorization report

The exact read-only report is
`/private/tmp/buoy-routing-v2-live.tLAkaC/routing-quality-65.16357c62.json`,
SHA-256
`d9369f82d47d17fd0a7388246348c258d97b12f956ca9796e3afaa5442255a9d`.
It records:

- schema version `1`, mode `live`, a clean checkout at commit
  `16357c629a96e4b309592917ad479a163cec3047` and tree
  `c002897fc3224faae9c8670f785e906884100890`;
- approved suite
  `0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5`;
- exact eligible-card projection
  `e559a8aac5a4f7fb808f137b1c6a3710b6cd5b6764fc84f7f06120e33307ef7c`;
- calibration score/margin floors `-10.167728424072266` /
  `1.0735645294189453` over six cases whose ordered ID digest is
  `23a863f53b44ec741185bf27f903824931dd9d84bd08e907c8f2b94e1f70ce1f`,
  with six correct and zero incorrect high-confidence singletons;
- 59 locked certification cases whose ordered ID digest is
  `536a6417f0882ac073d7f4cedda30c05594b5ae9447a998e62d264677ca69149`;
- a complete passing quality verdict whose stable compact JSON digest is
  `cb26318f93e61ed7874bfe4db5139f2f3eb2bdc52d1d3908c278ce9e2f8aca4d`;
- candidate route and shortlist recall `67/67 = 1.0`, exact per-corpus
  Recall@3/shortlist Recall@12 `1.0`, `23/23` named cases, `10/10` complete
  multi-corpus cases, zero regressed passing cases/corpora, zero
  incorrect/no-answer high-confidence singletons, average initial fanout
  `1.5932203389830508`, and maximum initial/fallback fanout `3`; and
- the same-snapshot legacy route at `63/67 = 0.9402985074626866` with average
  initial fanout `2.0338983050847457`.

Call accounting was 65 routing-query inferences and 65 bounded reranker calls,
with two namespace-list pages, one metadata request, two catalog-query pages,
zero shortlist/per-card provider queries, zero content queries, zero provider
writes, and zero model downloads. No content namespace resource was acquired
and provider mutation methods were not exposed.

The report itself remained `collect_only`: its packaged v1 artifact was
`mode=collect`, owner-unapproved, null-threshold, and unbound. Its two failed
activation checks were exactly the absence of an approved active artifact and
its suite/catalog bindings. The route-quality, owner-approved canary,
clean-source, and read-only checks passed. No ordinary production route changed.

## Approved packaged ground truth

The independent activation audit required removing the dormant run's scratch-
directory dependency without broadening its ground truth. The only approved
packaged canary inputs are the exact current packs:

- RentPTR, SHA-256
  `5a39c38d302cbc5c6d758b1e48d4456456a4357248f559a6cf56e0234742f4f5`;
- Salesforce, SHA-256
  `32106e02d877788e676cdb3db3f7a3567f57f96fa009a7a558b82ca1d407d13d`;
  and
- WhiteboxGeo, SHA-256
  `5558a4e8a786f0a5553ba0237ebf8248a5d576bd1937ffd69cf9af66a8ac0916`.

They are adopted without byte or label changes at
`src/buoy_search/data/routing_canaries/{rentptr,salesforce,whiteboxgeo}.json`.
With the unchanged legacy dataset they retain exact suite SHA-256
`0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5`.
The four disabled synthetic FleetDeck, FleetShield, OrbitStock, and OrbitWatch
packs remain external and outside the active suite, source/distribution
inventory, and ordinary routing.

Final implementation evidence must prove the source tree, wheel, source
distribution, and clean installed package contain exactly those three routing
canary files, reproduce each raw hash and the suite digest, and contain no
synthetic fixture pack. Packaging these reviewed evaluation questions does not
load them during ordinary routing and authorizes no live-card enablement or
provider operation.

## Why a second clean report is required

The report source implements and measures the candidate scorer but not the
later production activation wiring. The active JSON also cannot bind the Git
commit that contains itself without a circular identity. The execution gate
therefore requires a clean dormant-wiring commit while the package remains
collect-only, followed by the same read-only collection and an independent
exact-result audit. The final artifact binds both this authorization report and
that later dormant-source report. Because later squash integration does not
preserve task commit ancestry as the deployed source identity, the dormant
report must additionally emit exact raw-byte SHA-256 receipts named
`routing_module_sha256`, `cli_module_sha256`, and
`evidence_module_sha256` for the three production modules that select routing,
enforce the CLI boundary, and assess automatic evidence.

No dormant commit, report SHA, tree, runner/scorer digest, collect-artifact
digest, or routing/CLI/evidence module digest has been invented in this record.
They are mandatory measured receipts for later evidence. The active loader and
build/installed-distribution tests must reproduce the three module hashes from
packaged bytes; Git metadata alone is insufficient.

## Authorization and effect boundary

The owner direction authorizes bounded task-branch implementation and the exact
active artifact only if the dormant gate reproduces the frozen envelope. It
also authorizes local/read-only validation, independent review, push, and PR
creation under the repository workflow.

It does not authorize a provider/schema/card/content mutation, catalog repair,
credential change, deletion, self-merge, merge of an unknown future PR head,
`main` promotion, deployment, tag, release, or publication. The prior build at
`16357c629a96e4b309592917ad479a163cec3047` is the rollback target; rollback
means deploying that build, not rewriting the live catalog.

## Governance validation

This authorization record, the executable ticket, active specification, and
decision were created before production source or packaged behavior changed in
the activation worktree. Scoped diff, whitespace, changed-path, and exact-hash
results are recorded by the governance handoff and do not claim later
implementation validation.

The records-before-source handoff preserved the last four scoped record hashes
before implementation began: decision
`d9edc7f0a4f63ee3b022e3164f3bed84f4a72a3a7c7c0bdfdb5a724ee47624f6`,
specification
`9fea0fb0d515fc08c6a09117c37e52a1ebe14dd21b5e45833fd946c85ef056d3`,
ticket
`ff14b2691f18cce934616a0f08685b19217d9c07b30d23ac46cd199fb1989b4e`,
and this authorization record
`bc53ad37d9b12470f40e7af450b14c3195d846ada2e035bf1f8bd28942cd084c`.
Those hashes are chronology receipts, not the final record identities.

## Dormant implementation validation before commit

The frozen implementation tree still packages the exact collect-only artifact,
SHA-256
`23fb14c49263933a2adb2299a9c04089888fb2ec734b790d9eadda2df295cbed`.
It therefore cannot activate prototype routing. The source implements strict
schema-v2 authority parsing, active prototype dispatch, exact catalog binding,
redacted pre-content failures, and phase-independent tests while collect mode
continues to call the prior hybrid selector.

Validation before the clean dormant commit recorded:

- `152/152` focused activation, routing-quality, evidence, and packaging tests
  under both Python 3.11 and Python 3.13;
- `805/805` full repository tests under both Python 3.11 and Python 3.13;
- source-release, frozen-ranking, C6, compilation, and diff-hygiene checks;
- a diagnostic current-tree wheel/source-distribution pair whose wheel and
  source bytes match frozen `routing_quality.py`, `routing.py`, `cli.py`, and
  `evidence.py`; distribution validation reproduced the exact three-canary
  inventory and suite, and an installed-wheel loader returned collect mode;
  and
- an independent dormant audit with no remaining P1/P2 finding, including
  `167` focused Python 3.13 tests and `72` routing tests with the packaged
  default simulated as a valid active artifact.

The diagnostic wheel SHA-256 was
`700093391034046f4874b89c65a3f0be195877f41c7161faf47ba3f667dcb981`
with 69 files. The diagnostic source-distribution SHA-256 was
`dd0b21a25ce58d66526e9b9cbc79fcc12b0455941d9037999fc73033ea12b85f`
with 140 files. Because those diagnostic archives were built before the
dormant Git commit existed, exact clean-commit archives remain a required
post-commit check and are not claimed here.

No provider or model was called by these tests, builds, or audits. The upcoming
65-case run is a live, read-only route-selection certification. Downstream
retrieval, evidence widening, partial failure, and reranker reuse are locally
regression-tested; this task does not claim a provider-backed active
answer-quality or result-reranking certification.
