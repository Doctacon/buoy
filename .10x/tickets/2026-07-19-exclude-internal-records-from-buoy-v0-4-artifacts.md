Status: open
Created: 2026-07-19
Updated: 2026-07-19
Parent: .10x/tickets/2026-07-19-buoy-v0-4-compatibility-removal-plan.md
Depends-On: .10x/evidence/2026-07-19-buoy-v0-4-compatibility-removal-candidate.md

# Exclude Internal Records from Buoy 0.4 Artifacts

## Scope

Implement `.10x/specs/buoy-v0-4-internal-record-artifact-exclusion.md` as one bounded packaging repair on the assembled Buoy 0.4 candidate:

- configure wheel and sdist construction to exclude repository-root `.10x/**` and no other path;
- preserve the repository's `.10x/**` records;
- add only focused packaging validation needed to prove the wheel/sdist inventory and deterministic record-only boundary;
- rerun the aggregate candidate clean install and digest-verified released-0.3.0 same-environment upgrade validation.

The implementation surface is limited to build configuration, focused packaging validation, and `.10x` ticket/evidence/review records. It MUST NOT modify runtime/package code, bundled package data, or user documentation.

## Acceptance criteria

- Repository-root `.10x/**` remains present and tracked in the repository.
- Fresh Buoy 0.4 wheel and sdist inventories contain zero `.10x` entries, with sdist member paths evaluated after stripping the archive's single distribution-root directory.
- The build configuration introduces exactly the `.10x/**` exclusion and no other exclusion.
- With identical controlled inputs outside `.10x/**`, the same interpreter/platform/locked build dependencies and command, fixed `SOURCE_DATE_EPOCH`, and fresh temporary output directories, adding only one `.10x/**` evidence record produces byte-for-byte identical wheel and sdist archives with equal corresponding SHA-256 digests.
- Runtime/package code, bundled package data, tests outside the focused packaging validation, and user documentation are unchanged.
- Aggregate clean candidate-wheel installation passes with `buoy` working and no package-owned `turbo-search` launcher.
- Aggregate same-environment upgrade passes after verifying the released GitHub 0.3.0 wheel SHA-256 `048dba11df692a7efcd7ab7269fc2eec82f6b53e57573a3de113bbd051750bab`; 0.3.0 has both package-owned launchers before upgrade, and candidate 0.4.0 metadata plus complete launcher-directory inspection have only `buoy` after upgrade.
- No package publication, tag, GitHub Release, live Turbopuffer operation, or user state/data mutation occurs.
- Independent bounded review and exact-head hosted checks pass before this child can close.

## Validation and evidence expectations

Record:

- the exact changed-file inventory and build-configuration diff;
- complete wheel and sdist member inventories or durable machine-readable inventories, including explicit zero-`.10x` assertions;
- the controlled build inputs, `SOURCE_DATE_EPOCH`, build commands, artifact names, byte-comparison results, and before/after SHA-256 digests;
- proof that the comparison's only source-tree delta is one `.10x/**` evidence record;
- aggregate clean-install and released-0.3.0 upgrade commands, verified release URL/digest, installed metadata/entry points, launcher-directory inventories, and primary CLI outputs;
- diff checks proving runtime/package code, bundled package data, and user docs are unchanged;
- exact-head hosted check identities and an explicit no-publication/no-tag/no-release/no-state/no-live-product-service attestation; authorized GitHub PR/check delivery operations are allowed.

## Blockers

None. The assembled candidate and aggregate evidence exist. The observed candidate sdist currently contains `.10x/**`, so parent acceptance and aggregate review are blocked until this executable repair is implemented and reviewed.

## Explicit exclusions

Any exclusion other than repository-root `.10x/**`; removal or relocation of repository records; runtime/package code or bundled-data changes; user-documentation changes; unrelated test changes; any additional compatibility removal; state/data migration or deletion; live product-service operations; PyPI publication; Git tag creation; GitHub Release creation; release publication. Authorized GitHub branch, PR, and hosted-check delivery operations are allowed.

## References

- `.10x/tickets/2026-07-19-buoy-v0-4-compatibility-removal-plan.md`
- `.10x/specs/buoy-v0-4-internal-record-artifact-exclusion.md`
- `.10x/specs/buoy-release-validation.md`
- `.10x/evidence/2026-07-19-buoy-v0-4-compatibility-removal-candidate.md`
- `.10x/reviews/2026-07-19-buoy-v0-4-aggregate-packaging-blocker-review.md`

## Progress and notes

- 2026-07-19: User ratified the exact packaging boundary: keep `.10x/**` in the repository, exclude only `.10x/**` from both Buoy 0.4 artifacts, prove deterministic stability across a record-only evidence delta, and rerun aggregate install/upgrade validation without publishing, tagging, or releasing. Ticket opened; no implementation performed.
- 2026-07-19: Implemented only the repository-root Hatch exclusion `exclude = ["/.10x/**"]` plus one focused exact-config assertion. Controlled CPython 3.13 builds with a frozen five-package Hatchling environment and `SOURCE_DATE_EPOCH=1784506710` produced identical 45-member wheels and 95-member sdists before/after adding and staging exactly one `.10x` evidence record: wheel SHA-256 `1a5cdb4a303eb0c4f7e42b335138a43f4b1098a8f8b2189ded2d3d9fc8e00d30`, sdist SHA-256 `bd7d2f80e06e8f6ae2c99a5b81f9ae709d5af5e71c0659cf5333f281e46404b1`, both `cmp`-identical, both inventories with zero `.10x` entries.
- 2026-07-19: Python 3.11/3.13 aggregate suites each passed 422 tests; 75 focused packaging/environment/CLI/autoresearch/release tests passed. Fresh 0.4.0 clean install exposed only `buoy`; the digest-verified released 0.3.0 wheel exposed both launchers before a same-environment candidate upgrade and only `buoy` afterward. Exact installed gate/no-side-effect validation passed. Evidence: `.10x/evidence/2026-07-19-exclude-internal-records-from-buoy-v0-4-artifacts.md`. No publication, tag, release, state/data mutation, or live product-service operation occurred. Ticket remains active pending independent bounded/aggregate review and exact-head hosted checks.
