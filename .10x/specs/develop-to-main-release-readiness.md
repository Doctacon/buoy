Status: active
Created: 2026-07-21
Updated: 2026-07-21

# Develop-to-Main Release Readiness

## Purpose and authority

Replace release ancestry syncs and conversational preflights with four mechanically required GitHub checks on every pull request targeting `main`. The user ratified this repaired contract after independent review.

The only supported release PR source is branch `develop` in `Doctacon/buoy-search`. Main does **not** require strict base freshness or main-as-ancestor; the checks validate GitHub's exact prospective merge commit. Develop retains its existing strict ordinary CI protection.

## Required workflow and checks

`.github/workflows/release-readiness.yml` MUST trigger only for pull requests targeting `main` and expose exactly:

1. `Release readiness / Policy`
2. `Release readiness / Python 3.11`
3. `Release readiness / Python 3.13`
4. `Release readiness / Distribution`

Main protection MUST require exactly these app-bound release checks, PRs, zero fixed approvals, administrator enforcement, deletion denial, `strict=false`, and `require_last_push_approval=false`. The user's previously retained main force-push allowance remains unchanged; repository workflows and agents MUST NOT use it. Develop keeps strict `Python 3.11`, `Python 3.13`, and `Build distributions` checks, force-push denial, and no last-push approval.

## Prospective merge-result validation

GitHub's pull-request merge ref MUST be checked out. Policy MUST verify:

- head repository and branch are exactly `Doctacon/buoy-search:develop`;
- checkout is GitHub's prospective merge commit with exact current base-main and head-develop parents;
- project, module, and lock agree on stable `MAJOR.MINOR.PATCH` only—no prerelease/build suffix;
- `CHANGELOG.md` has empty `Unreleased`, exactly current `## [X.Y.Z] - pending`, and every older released section has an ISO date;
- authoritative remote annotated tag and GitHub Release `vX.Y.Z` are both absent;
- repository policy contains no PyPI/Turbopuffer release behavior.

A previously released unchanged version fails. Every main merge intended to publish therefore includes an explicit version bump and pending changelog section.

## Python checks

Python 3.11 and 3.13 independently use locked dependencies, validate the frozen ranking contract, validate the intentionally blocked C6 forecast without claiming readiness, and run the complete tests/docs. They use read-only permissions, no secrets, and perform no model download/inference, provider call, live retrieval/apply/eval, namespace operation, or mutation.

## Distribution check

After Python passes, Distribution MUST build once from the prospective merge result with deterministic inputs:

- `SOURCE_DATE_EPOCH` equal to the prospective merge commit timestamp;
- `PYTHONHASHSEED=0`, `TZ=UTC`, and `LC_ALL=C`;
- locked build backend/dependencies.

It MUST verify exact versioned wheel/sdist names and metadata; absence of `.10x/**`, `turbo-search`, and `legacy_main`; exact `buoy` entry point; required data; normal fresh wheel install; `buoy --version`, both help paths; and mandatory loading/smoke-counting of the current exact bundled tokenizer.

It publishes nothing and retains artifacts only within the workflow run for diagnostics.

## Protection transition

Implementation order is mandatory:

1. land repository workflow/scripts/tests/docs on `develop` through ordinary protected CI;
2. verify workflow syntax and deterministic dry harness locally/hosted;
3. update main protection to the exact four checks, `strict=false`, and last-push approval false;
4. leave develop protection unchanged;
5. record API readback.

No passing release-readiness run is expected until a future version-bump `develop -> main` PR. Protection may name the four contexts before that first release PR; that PR is the first end-to-end proof.

## One-time v0.4 squash-topology transition

The accepted v0.4.0 squash promotion left exact main `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d` outside develop ancestry. PR #93 proved GitHub cannot construct the first prospective merge ref because both lineages independently changed release files.

Before PR #93 may proceed, the repository MUST perform the sole exception defined by `.10x/decisions/one-time-v0-4-squash-topology-bridge.md`: one protected merge-commit-preserving bridge of that exact main commit into then-current develop whose tree is byte-identical to its develop parent. It MUST make no source/version/changelog/workflow/product/release/provider/configuration change, use no direct/force push or protection weakening, and prove exact tree identity plus main ancestry after integration.

This is migration cleanup for the already-accepted v0.4 topology, not release ceremony. It MUST NOT be repeated or generalized. After the bridge, PR #93 and all future releases follow the normal exact `develop -> main` readiness flow.

## Failure behavior

Any missing/skipped/cancelled/stale/failed check blocks merge. Failure is diagnostic-only and never modifies tag, Release, branch, protection, environment, registry, Turbopuffer, or user state.

## Portability

GitHub Actions is the explicit user-required managed-platform exception. Release-critical logic MUST live in repository-local standard Python/shell with deterministic tests. Full-SHA-pinned open-source actions are used where possible. A documented migration path MUST map each check to local commands and a self-hosted Git forge/runner: invoke the same scripts on a prospective merge commit, enforce their statuses, then publish standard wheel/sdist/tag/release objects. No proprietary package registry or GitHub-only data format enters artifacts.

## Acceptance scenarios

- New stable version, pending changelog, exact develop head, passing merge result: four checks pass.
- Non-develop head, existing version, prerelease, stale/malformed changelog, incompatible clean install, or failed test: relevant check fails without mutation.
- Main does not contain develop ancestry: prospective merge result is validated without ancestry-sync ceremony.

## Explicit exclusions

Choosing/bumping the next version; merging main; creating a tag/Release; PyPI; Turbopuffer; force push; release environment; recurring ancestry-sync mechanics beyond the exact one-time v0.4 transition above; product changes.
