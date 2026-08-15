Status: provisional
Created: 2026-08-15
Updated: 2026-08-15
Ticket: .10x/tickets/2026-08-15-migrate-routing-catalog-v2-and-examples.md

# Routing Catalog V2 Migration Evidence

## Initial state

- Checkpoint-one compatible reader integrated into `develop` at
  `9fd3f01a05392a08401296d3fdc99d0dd70ed5a1` after PR #108 and passing
  hosted Python 3.11, Python 3.13, and distribution validation.
- PR #109 promoted that exact reviewed tree to `main` at
  `b6319dfaca0920248be4d870c0aeb7aeed0d0d26`; fresh main Python 3.11,
  Python 3.13, build/install, and read-only publication-paused validation all
  passed.
- The global Buoy installation now reports
  `0.5.2.dev9+gb6319dfac` and contains the exact v1/v2-compatible reader.
- The last independently verified live catalog snapshot remained exact schema
  v1 (`793f6844d7141959b43a5f03c33dbbd7b657d4ff186c622ac0ee1635be9217f7`).
  No prototype fields, routing examples, shared-schema change, or active
  candidate route exists, and no migration attempt has occurred.
- No executable schema-v2 migration operator existed before this ticket.

## Required evidence

Record source and independent review commits, full validation, exact installed
reader version, read-only v1 preview, schema/card projections, request budgets,
approved migration result and v2 readback, every example preview/write/readback,
canary/example disjointness, generated-card apply persistence, unchanged
production-route smoke, and every external effect. Any failed or partial
attempt remains recorded.

## Checkpoint-two source implementation validation

- Implementation worktree: `work/routing-catalog-v2-migration`, based on
  `develop` commit `9fd3f01a05392a08401296d3fdc99d0dd70ed5a1`.
- Focused remote primitive, catalog operator, and apply-persistence suite:
  61 tests passed under both Python 3.11.5 and Python 3.13.0.
- Full source suite, split only to prevent the generated worktree version path
  from leaking into the packaging tests' deliberately isolated child
  environments: 750 non-packaging tests and three packaging tests passed under
  each of Python 3.11.5 and Python 3.13.0.
- `scripts/release_automation.py validate-source` passed.
- A diagnostic `0.5.2.dev999` wheel and source distribution built from the
  worktree, passed `validate-distribution`, installed into an isolated target,
  reported the exact version, and exposed help for both new catalog commands.
  Publication remained paused and no artifact was published.
- Python compilation and `git diff --check` passed for the bounded source and
  test changes.
- Validation made no provider calls and performed no live catalog, content
  namespace, activation, deletion, credential, commit, push, or merge action.

## Frozen reviewed questions and examples

- The owner authorized all three routing checkpoints and approved execution of
  the reviewed canary/example process in this task on 2026-08-15. Independent
  source review confirmed all 35 canary expected-namespace labels and replaced
  five weak-but-correct calibration/confusion formulations before approval.
- The three enabled-corpus extension packs are byte-identical between the
  current and expanded external suites: RentPTR
  `5a39c38d302cbc5c6d758b1e48d4456456a4357248f559a6cf56e0234742f4f5`,
  Salesforce
  `32106e02d877788e676cdb3db3f7a3567f57f96fa009a7a558b82ca1d407d13d`,
  and WhiteboxGeo
  `5558a4e8a786f0a5553ba0237ebf8248a5d576bd1937ffd69cf9af66a8ac0916`.
  Their approved 65-case suite identity is
  `0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5`.
- The four approved disabled-fixture packs are FleetDeck
  `abe183b98b3750c28faf68aa1ebfce2031399c7ddb329bc1980884edef3bd004`,
  FleetShield
  `b5f0406557c0221f00bc14f6819c141397cadd3abc99f4683798bd9ea56e79f7`,
  OrbitStock
  `7ab0bb876828f2e04634ecfed194871b61e08cbd394178837b519b638e16cf0d`,
  and OrbitWatch
  `721c8dba7d09bdfa6fbb6a030ca2cdadd5d9bb0e4ff481eba5e4bcacd78b889b`.
  Together with the enabled extension they produce the approved 85-case suite
  identity
  `a5f84328ce8fda284b6b887d38ed4981e73a2abf416882a6c7576247a8655357`.
- The external reviewed-example manifest
  `/private/tmp/buoy-routing-test-corpora/routing-examples-approved-v1.json`
  has SHA-256
  `3d6c93b091a2adad57799746931fb10c443a675bb814991edbe08c0ec523bf2f`,
  binds 62 examples across 11 cards, and is exact-normalized disjoint from all
  35 held-out canary questions. These scratch review artifacts are not packaged
  and are not a second catalog or runtime overlay.
