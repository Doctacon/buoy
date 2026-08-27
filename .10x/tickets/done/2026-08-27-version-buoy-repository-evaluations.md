Status: done
Created: 2026-08-27
Updated: 2026-08-27
Parent: .10x/tickets/done/2026-08-27-decouple-evidence-from-source-layout-plan.md
Depends-On: None

# Version Buoy repository evaluations

## Scope

Implement the historical/current evaluation split in `.10x/specs/versioned-repository-evaluations-and-promotion-gate.md`: preserve exact v1 evidence, create the reorganized v2 current dataset with explicit lineage and a path-membership manifest, mark it baseline pending and promotion-ineligible, and update fast validators so historical paths are not checked against `HEAD`.

## Acceptance criteria

- Exact v1 dataset/manifest bytes and identities remain preserved as historical evidence.
- V2 carries forward all non-path judgment semantics exactly and declares every path mapping.
- V2 current paths exist in its deterministic path-membership manifest, which makes no corpus/source-snapshot claim.
- V2 is `baseline_status=pending`, is explicitly promotion-ineligible, and makes no score claim.
- Fast validation checks historical internal consistency without requiring historical paths at `HEAD`.
- No retrieval, model, provider, namespace, credential, or live operation occurs.
- Focused ranking-contract/autoresearch and full tests pass for this slice.

## Explicit exclusions

New labels, scores, benchmarks, ranking defaults, promotion logic, provider operations, or non-Buoy dataset changes.

## Evidence expectations

V1 raw hashes, v1-to-v2 semantic comparison, complete path map, v2 manifest/hash reproduction, focused/full test output, external-effect audit, diff summary, and limits.

## Blockers

None.

## Progress and notes

- 2026-08-27: Opened after cancelling the in-place historical corpus rewrite. No evaluation artifact mutation occurred in this record-authoring turn.
- 2026-08-27: Preserved the exact v1 dataset as immutable evidence without changing the historical source bundle/inventory; created active v2 with explicit nine-path lineage, 32 unchanged judgment semantics, a 15-path current membership manifest, and `baseline_status=pending`; updated current dataset/fixture/docs references; and made the standard-library validator resolve historical v1 independently of `HEAD` while validating v2 against current paths.
- 2026-08-27: Added ranking-contract coverage for exact v1 preservation, absent historical paths at `HEAD`, current v2 path validity/pending state, and fail-closed non-path semantic drift. Focused tests passed (`35 passed, 22 subtests`), fixture-only autoresearch passed, full suite passed (`1169 passed, 1232 subtests`, 57 existing lxml warnings), compilation and wheel inventory passed, historical hashes reproduced, diff hygiene passed, and no files were staged. No retrieval/model/provider/credential/live operation occurred. Evidence: `.10x/evidence/2026-08-27-versioned-buoy-repository-evaluations-implementation.md`. Ticket remains active pending independent review.
- 2026-08-27: Aggregate integration passed frozen/current validators, 1176 tests on Python 3.11 and 3.13, wheel/sdist current-data inventory, isolated installation, and no-shim/path audits. Evidence: `.10x/evidence/2026-08-27-buoy-search-subpackage-final-integration.md`. Ticket remains active pending independent review.
- 2026-08-27: Repaired the aggregate review finding under the updated spec. Pending v2 now exposes only `path_membership_manifest_path`/`sha256`, has no corpus-manifest or source-snapshot fields, and is explicitly `promotion_eligible=false`; the file is named `buoy_search_repo_search_v2_path_membership.json`. Registry, dataset, validator summary, tests, and docs use the same discriminated interface. Added a mutation test that rejects adding a corpus identity to pending v2. Historical v1 dataset/source-manifest bytes remain exact. Fresh focused/package results and hashes are recorded in `.10x/evidence/2026-08-27-versioned-buoy-repository-evaluations-implementation.md`.
- 2026-08-27: Promotion repair and aggregate integration are now complete. Ranking validation reproduced pending path membership and `promotion_eligible=false`; promotion mutation coverage rejects pending/path-only versions. Exact Python 3.11/3.13 suites each passed 1186 tests, with package/isolated and workflow integration green.
- 2026-08-27: Integrated the later basket registry: production registry has zero entries because current Buoy v2 is pending/path-only; promotion validation cross-checks any future registered Buoy member against a recorded, promotion-eligible evaluation version. Exact Python 3.11/3.13 validators and 1189-test suites plus package/isolated registry checks passed.
- 2026-08-27: Integrated strict semantic checks for every future registered dataset and corpus: exact dataset identity/cases/judgments, judgment membership in canonical corpus inventory, and exact corpus repository/full-commit/document/content identities. Current pending v2 and empty promotion registry remain unchanged. Exact Python 3.11/3.13 1191-test suites and aggregate package checks passed. Evidence: `.10x/evidence/2026-08-27-buoy-search-subpackage-final-integration.md`.
- 2026-08-27: Fresh independent aggregate review passed with no findings: `.10x/reviews/2026-08-27-evidence-layout-final-review.md`. Closed after acceptance criteria and preserved-history/current-path boundaries were rechecked.

## Closure mapping

Exact v1 bytes remain historical evidence; v2 carries unchanged judgment semantics through explicit mappings, validates current path membership, remains pending and promotion-ineligible, and requires no external operation. Focused/full/package evidence and final review support every criterion.

## Retrospective

Historical benchmark artifacts and current regression data have different lifecycles. Versioning them separately prevents either rewriting history or coupling ordinary refactors to obsolete paths.
