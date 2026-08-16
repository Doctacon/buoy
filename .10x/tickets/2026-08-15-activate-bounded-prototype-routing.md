Status: done
Created: 2026-08-15
Updated: 2026-08-15
Decision: .10x/decisions/buoy-activates-certified-bounded-prototype-routing.md
Specification: .10x/specs/bounded-prototype-routing-activation.md

# Activate Bounded Prototype Routing

## Outcome

Activate the already certified bounded prototype router for automatic
retrieval through one strict, packaged, owner-approved artifact. Keep explicit
namespace retrieval unchanged, preserve the three-corpus bound, and stop
before content access on invalid authority or certified catalog-projection
drift.

## Execution order

1. Implement the exact v1-collect/v2-active loader and production wiring while
   the packaged artifact remains collect-only.
2. Commit and validate that clean dormant state; prove collect mode still uses
   the legacy selector.
3. Run and independently audit a new read-only 65-case report from that exact
   dormant commit. Require exact equality with every frozen value in the
   specification and exact raw-byte SHA-256 receipts for dormant `routing.py`,
   `cli.py`, and `evidence.py`.
4. Change only the packaged artifact plus final governance/evidence records to
   the exact active revision. A source repair restarts at step 1.
5. Run focused/full/distribution/installed validation and independent review,
   incorporate current `develop`, rerun required checks, and prepare a PR
   handoff without self-merging or releasing.

## Scope and owned paths

- The strict confidence artifact schema/loader in
  `src/buoy_search/routing_quality.py` and the packaged
  `src/buoy_search/data/automatic_routing_confidence_calibration.json`.
- The exact approved RentPTR, Salesforce, and WhiteboxGeo JSON packs under
  `src/buoy_search/data/routing_canaries/`, with no other packaged canary pack.
- The minimum production route/CLI wiring in
  `src/buoy_search/routing.py` and `src/buoy_search/cli.py`.
- Focused tests and only the evaluator/release-inventory changes required to
  validate and package the exact active artifact and receipts.
- Public routing documentation that currently describes the candidate as
  inactive, plus this ticket's decision, specification, evidence, and review
  records.

## Acceptance

- The original owner-approved report remains bound by exact hash, candidate
  source commit/tree, suite, projection, thresholds, split receipts, and
  verdict digest.
- The packaged RentPTR, Salesforce, and WhiteboxGeo packs are byte-identical to
  the approved external inputs at SHA-256
  `5a39c38d302cbc5c6d758b1e48d4456456a4357248f559a6cf56e0234742f4f5`,
  `32106e02d877788e676cdb3db3f7a3567f57f96fa009a7a558b82ca1d407d13d`,
  and `5558a4e8a786f0a5553ba0237ebf8248a5d576bd1937ffd69cf9af66a8ac0916`;
  they reconstruct suite
  `0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5`.
- A separately committed dormant wiring state is cleanly recollected and
  independently audited before active JSON exists; every frozen value matches
  exactly and read-only accounting stays at zero content queries, zero
  shortlist/per-card provider queries, zero provider writes, and zero model
  downloads.
- The final active JSON is exact schema v2 with no extra/missing fields, the
  exact certified values, complete original/dormant receipts, and an externally
  recorded artifact SHA-256.
- Dormant report provenance emits `routing_module_sha256`,
  `cli_module_sha256`, and `evidence_module_sha256`; the artifact loader
  verifies all three against installed packaged bytes before returning active
  state, and build/wheel/sdist/install tests reproduce them exactly.
- Production accepts a complete validated artifact object, never loose
  thresholds. No CLI/environment/config/path override can alter the artifact,
  thresholds, mode, or strategy.
- Valid collect mode preserves current legacy routing. Valid active mode uses
  prototype shortlisting/reranking and creates a confident singleton only when
  both exact finite floors pass; exact names and maximum fanout three remain
  unchanged.
- Explicit namespaces bypass all automatic artifact/catalog/model work.
- Missing/malformed/incompatible/unapproved state, wrong receipts, catalog
  projection drift, non-finite values, stale prototype state, or model failure
  stops before content resource construction or query and cannot silently
  fall back from active to legacy.
- Routine output remains redacted and identifies the active artifact revision,
  strategy, thresholds, score/margin, and selection reason.
- Rollback is documented and tested operationally as deployment of prior
  compatible-reader legacy build `16357c629a96e4b309592917ad479a163cec3047`;
  it never mutates schema, cards, examples, content, or runtime configuration.
- Focused and full Python 3.11/3.13 suites, locked/source/distribution checks,
  clean wheel install, privacy/redaction, diff hygiene, changed-path audit,
  dormant live collection, and independent final review all pass.
- Source, wheel, source distribution, and installed package inventories contain
  exactly the three approved current canary files under
  `buoy_search/data/routing_canaries/`; the four disabled synthetic fixture
  packs remain external and absent.

## External effects

The owner explicitly authorized this bounded activation implementation by
replying “yes activate” after the passing quality result and inactive-state
disclosure. That covers task-branch implementation, the exact active artifact,
read-only validation, independent review, push, and opening a PR to `develop`.

This ticket authorizes no provider mutation: no schema/card/content/namespace
write or delete, no credential change, and no catalog repair. It authorizes no
self-merge, `develop` integration of an unknown PR head, `main` promotion,
deployment, tag, GitHub Release, or package publication. Those later actions
must use exact reviewed commits and their normal separately explicit
integration/release authority.

## Exclusions

Pure-global result reranking, more than twelve routing candidates, more than
three content corpora, online threshold learning, automatic threshold tuning,
runtime flags, environment overrides, alternate artifact paths, LLM routing,
card/example generation, canary relabeling, packaging or activating the four
disabled synthetic fixture packs, catalog/schema migration, provider mutation,
content reindexing, second catalogs, overlays, and deletion of the disabled
test corpora.

## Stop conditions

Stop without activating on any report/value mismatch, dirty dormant source,
catalog projection drift, failed or incomplete gate, unexpected call class,
provider mutation, source change after dormant certification, artifact
placeholder, independent review finding, required-check failure, or target
branch advance not yet incorporated and revalidated.

## Evidence required for closure

Record the exact dormant and final commits/trees, original and dormant report
hashes, runner/scorer/collect/active artifact hashes, dormant and packaged
`routing.py`/`cli.py`/`evidence.py` hashes, active JSON projection,
the three packaged canary hashes and exact source/wheel/sdist/install
inventories, reconstructed suite digest, focused/full/build/install commands
and results, content-before-failure receipts, explicit bypass proof, call
accounting, privacy scan, complete diff, independent review, PR
identity/head/base/checks, compatibility risks, and external-side-effect
attestation. Protected integration and deployment remain future evidence, not
claims of this task branch.

## Progress

- 2026-08-15: Owner authorized activation after the exact passing report was
  disclosed as not yet active. Governance froze the authorization envelope and
  required dormant-wiring-first certification before source implementation.
- 2026-08-15: Dormant wiring, exact packaged canaries, strict artifact and
  distribution checks, phase-independent tests, and downstream local
  regression coverage completed while the packaged artifact remained the
  byte-identical collect-only revision. Focused `152/152` and full `805/805`
  suites passed on both supported Python versions; the independent dormant
  audit found no P1/P2 blocker. The clean dormant commit and its exact read-only
  65-case report remain the next gates; activation has not occurred.
- 2026-08-15: The first artifact-phase simulation exposed three test-only
  packaged-default assumptions. The artifact was restored to the exact
  collect bytes; an independently reviewed three-file fixture repair was
  committed at `d171cd887f615158a196dbeef8fa93830818ea64`, fully revalidated,
  and recollected from that exact clean commit.
- 2026-08-15: The superseding read-only report at SHA-256
  `6b02379f20147d004ff03cd2d90cdb6bd820e8f008be42d218578981f6db5977`
  independently reproduced the frozen 65-case result, call accounting,
  privacy boundary, and source receipts. The exact active artifact at SHA-256
  `3412bdb20f928de226e159344cac04ec52587da4134d6c079e9fc53a6aa75d9d`
  is now present on the task branch. Focused and full dual-Python suites plus
  source/distribution/installed-package checks pass. Independent final review,
  exact post-commit build, push, and PR handoff remain; no integration,
  publication, deployment, or provider mutation has occurred.
- 2026-08-15: The reviewed active checkpoint was committed as
  `e85b62ed8e27565e1ca371e113ffba77ffb3dd3c`, tree
  `b19d7c336fd695730db3e084eaba81dd55f86e69`, with exactly the approved
  four-path artifact-phase delta. Its exact 69-file wheel and 140-file source
  distribution passed receipt and inventory validation at SHA-256
  `346c623edb3dfccd8ec1fa9cb7e006d60326d3df3e8efbd95c68e7fdecbc559e`
  and `800e8c7b5523b48906605742d8cd127ded0fce1631aa5fae78d47be5044d17f0`.
  The installed-wheel authority smoke passed with source checkout bytes
  excluded from imports.
- 2026-08-15: Draft PR #114 opened from the exact reviewed branch into
  unchanged `develop` at `94b06ac58c86e96ddd012aae0a4a019dcc548cef`.
  Fresh CI run `31925850905` passed Python 3.11, Python 3.13, and distribution
  build jobs on active commit `e85b62e`. The task implementation and handoff
  are complete; integration, publication, deployment, release, and every
  provider mutation remain outside this ticket.
