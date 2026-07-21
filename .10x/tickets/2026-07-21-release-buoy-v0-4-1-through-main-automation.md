Status: blocked
Created: 2026-07-21
Updated: 2026-07-21
Parent: None
Depends-On: .10x/tickets/done/2026-07-21-simple-main-release-automation-plan.md

# Release Buoy v0.4.1 Through Main Automation

## Outcome

Exercise the ratified simple release process end to end by preparing stable Buoy 0.4.1 on `develop`, promoting it through a `develop -> main` pull request, and verifying the automatic main-push GitHub Release without manual tag, Release, environment, PyPI, or Turbopuffer operations.

## Ratified release identity

- Version: `0.4.1` (explicitly selected by the user on 2026-07-21).
- Changelog section: `## [0.4.1] - pending` below an empty `## [Unreleased]`.
- Changelog meaning: the release replaces manual tag/environment ceremony with four prospective-merge readiness checks and deterministic automatic GitHub publication on successful `main` pushes.
- Version class: patch; no new product behavior is claimed.

## Scope

1. In an isolated `work/*` worktree from current `develop`, update project/module/lock version authorities to exactly 0.4.1 and add the exact pending changelog section/link required by the active readiness spec.
2. Run repository release-policy checks, complete Python 3.11/3.13 validation, deterministic double-build comparison, artifact inspection, and clean-wheel CLI/tokenizer smoke.
3. Obtain independent review and integrate only the preparation change to protected `develop` through a passing pull request.
4. Open one pull request whose head is exact repository branch `develop` and base is `main`. If the inherited v0.4 squash topology prevents prospective-merge construction, execute only `.10x/tickets/2026-07-21-bridge-v0-4-squash-topology-once.md`, then resume the exact develop-to-main PR.
5. Require all four exact `Release readiness / ...` checks to pass on GitHub's prospective merge result, obtain independent promotion review, then merge through branch protection using the repository-required release merge commit.
6. Observe the automatic `main` push workflow to terminal state and verify the new annotated `v0.4.1` tag, GitHub Release `Buoy v0.4.1`, exact two assets/digests, and provenance source ref `refs/heads/main` and exact source commit.
7. Record raw hosted evidence, independent final review, and coherent closure.

## Acceptance criteria

- Project, module, and lock agree on stable `0.4.1`.
- `CHANGELOG.md` has empty Unreleased, exactly current pending 0.4.1, real dates on older sections, and correct comparison links.
- Preparation validation passes on Python 3.11 and 3.13; deterministic builds and clean-wheel/tokenizer smoke pass.
- Preparation reaches `develop` only through protected passing CI and independent review.
- The main PR source is exactly `Doctacon/buoy-search:develop`; all four exact readiness checks pass on the prospective merge commit.
- Main promotion occurs through the protected PR only; no force push or recurring ancestry-sync ceremony is used. The sole exact v0.4 migration bridge, if required, satisfies its focused child ticket first.
- Automatic release run succeeds from the resulting exact main commit.
- `v0.4.1` is annotated and peels to that commit; Release identity is non-draft/non-prerelease and contains exactly the expected wheel/sdist with recorded SHA-256 digests.
- `gh attestation verify` passes for both assets with repository `Doctacon/buoy-search`, workflow `release.yml`, source ref `refs/heads/main`, and exact source commit.
- PyPI remains absent for 0.4.1; no Turbopuffer operation occurs.
- Every unexpected partial/mismatch state stops without automated repair, overwrite, move, deletion, retry, or cleanup.

## Explicit exclusions

Product behavior changes; version other than 0.4.1; prerelease/build metadata; manual tag/Release creation; workflow dispatch; release environment recreation; PyPI; Turbopuffer; force push; ancestry sync other than the exact non-repeatable child bridge; mutation of existing releases/tags/assets/provenance; retry or repair after a partial/mismatched release state.

## References

- `.10x/specs/develop-to-main-release-readiness.md`
- `.10x/specs/main-push-automatic-github-release.md`
- `.10x/specs/protected-github-branches.md`
- `.10x/decisions/simple-main-release-governance.md`
- `.10x/evidence/2026-07-21-simple-main-release-governance-configuration.md`
- `.10x/reviews/2026-07-21-simple-main-release-governance-configuration-review.md`

## Evidence expectations

Exact source/destination commits; changed version/changelog paths; local commands/results; preparation PR/checks/review/integration; main PR exact head/base and four readiness contexts; merge identity; main-push run; tag object and peel; Release/API assets and downloaded digests; provenance verification; PyPI absence; no-live-provider attestation; independent final review.

## Blockers

PR #93 is conflicting before GitHub can construct the prospective merge ref, so the four release-readiness checks cannot run. The user-ratified bridge is owned by `.10x/tickets/2026-07-21-bridge-v0-4-squash-topology-once.md`; both parent and child remain blocked until PR #94's governing records pass review and integrate. Evidence: `.10x/evidence/2026-07-21-buoy-v0-4-1-prospective-merge-blocker.md`.

## Progress and notes

- 2026-07-21: User explicitly requested exercising the new process by moving current develop changes to main and selected stable version 0.4.1. Read-only inspection found main `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`, develop `3d5f700ed87feedfae76eeeb226d03a9bff12b18`, project version 0.4.0, empty Unreleased, no pending newer section, and a release-automation/governance-only main delta. No version, branch, tag, Release, asset, provider, or hosted configuration state changed during shaping.
- 2026-07-21: Preparation began from exact current develop `99f7685469571cec6f3a23f95801dcb649924059` in isolated branch/worktree `work/prepare-v0-4-1`. Scope is limited to the ratified 0.4.1 version authorities, pending changelog, local validation evidence, and a protected pull request to develop; no main, release, registry, provider, or hosted-configuration mutation is authorized.
- 2026-07-21: Project/module/lock now agree on stable 0.4.1; the changelog has empty Unreleased, the exact current pending section and ratified Changed meaning, and corrected comparison links. The initial complete 3.11 suite exposed two stale 0.4.0 static assertions; those were narrowly updated to the ratified current version/changelog while preserving verified 0.4.0 history. Release policy/version/changelog checks, lock check, complete locked 3.11 and 3.13 suites (534 tests each), deterministic byte-identical double build, repository artifact inspection, and clean-wheel CLI/help/exact-tokenizer smoke all pass. Evidence: `.10x/evidence/2026-07-21-buoy-v0-4-1-preparation.md`.
- 2026-07-21: PR #92 exact-head CI `29870237282` passed all protected develop checks. Independent review passed exact head `2b008edd2618286bb56f7693ca9204959ed81edf` with no blockers. Review: `.10x/reviews/2026-07-21-buoy-v0-4-1-preparation-review.md`. No main/tag/Release/PyPI/Turbopuffer/configuration mutation occurred.
- 2026-07-21: PR #92 squash-integrated to develop as `8694afc94984e6993730acd205af3bdca93c5c8b`. Exact `develop -> main` PR #93 was opened, but GitHub reports it conflicting before prospective-merge construction; only ordinary CI ran. Read-only merge-tree diagnosis attributes the conflict to the accepted v0.4 squash topology. Ticket blocked without merge/release mutation. Evidence: `.10x/evidence/2026-07-21-buoy-v0-4-1-prospective-merge-blocker.md`.
- 2026-07-21: User explicitly ratified the recommended one-time protected, content-neutral ancestry bridge after the inherited conflict was explained. The exception is pinned to exact main `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`, requires develop-tree identity and merge-commit ancestry preservation, and cannot recur. Decision: `.10x/decisions/one-time-v0-4-squash-topology-bridge.md`.
