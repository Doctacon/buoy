Status: superseded
Created: 2026-07-21
Updated: 2026-07-21

# Label-Driven Develop-to-Main Release Readiness

## Purpose and scope

Make one same-repository `develop -> main` PR the complete release-control surface: one explicit SemVer label, four deterministic checks, merge-commit auto-merge, and no version/changelog preparation.

This specification supersedes `.10x/specs/superseded/develop-to-main-release-readiness-static-version.md` for future releases and restates every retained normative guarantee below.

## PR and label contract

The workflow MUST trigger only for pull requests targeting `main`. The PR MUST be non-draft with exact head `Doctacon/buoy:develop` and base `Doctacon/buoy:main`.

Exactly one label MUST exist from:

- `release:patch`
- `release:minor`
- `release:major`

Missing or multiple release labels fail. Other non-release labels are allowed. Labeled/unlabeled/synchronize/reopen events rerun readiness.

## Version derivation

Let `B` be the highest stable `vMAJOR.MINOR.PATCH` annotated tag whose exact complete GitHub Release/provenance state is valid and whose peeled commit is reachable from current base main. Any higher stable tag that is lightweight, partial, mismatched, or not base-reachable fails closed instead of being ignored.

The target version increments `B` using the exact release label:

- patch: `M.m.(p+1)`
- minor: `M.(m+1).0`
- major: `(M+1).0.0`

Core identifiers MUST have no leading zeros. The target annotated tag and Release MUST both be absent.

## Prospective merge validation

GitHub's exact prospective merge commit MUST be checked out and have ordered parents `[current base main, exact head develop]`. Its tree is the candidate.

Policy MUST verify:

- exact repository/branches/parents;
- exact one-label version plan and base-tag authority;
- dynamic project version metadata uses pinned `hatch-vcs==0.5.0` and no committed static project/module/lock release version;
- `CHANGELOG.md` is frozen history through v0.4.0 with future notes delegated to canonical GitHub Releases;
- canonical repository `Doctacon/buoy`, exact legacy v0.4 exception, no PyPI/Turbopuffer release behavior;
- target tag/Release absence and no partial state.

## Required checks

The workflow MUST emit these exact GitHub Actions check-run job names, each app-bound under ID 15368:

1. `Release readiness / Policy`
2. `Release readiness / Python 3.11`
3. `Release readiness / Python 3.13`
4. `Release readiness / Distribution`

Main protection requires exactly those app-bound contexts with `strict=false`, pull requests, zero fixed approvals, administrator enforcement, deletion denial, retained force-push allowance, and last-push approval disabled. Develop protection remains strict on its ordinary three app-bound checks with force-push/deletion denial. Missing/skipped/cancelled/stale/failed release checks block merge.

Python jobs independently use locked dependencies, validate frozen ranking/C6 contracts, and run the complete suite without secrets, model/provider/live retrieval/apply/eval, or mutation.

Distribution builds once with locked backend/dependencies, `SETUPTOOLS_SCM_PRETEND_VERSION=<target>`, `SOURCE_DATE_EPOCH` equal to prospective merge commit timestamp, `PYTHONHASHSEED=0`, `TZ=UTC`, and `LC_ALL=C`. It verifies exact target-version wheel/sdist names and metadata, clean install, CLI/help/version, bundled tokenizer, inventory, and absence of internal/legacy artifacts.

## Automatic merge controller

The readiness workflow uses per-PR concurrency with `cancel-in-progress: true` and explicitly triggers on opened, reopened, synchronize, ready-for-review, labeled, and unlabeled events. Label changes therefore cancel stale runs and start a fresh complete readiness run.

A final `Automatic merge` job MUST depend on successful completion of all four required jobs. It MUST:

- run only for the exact same-repository non-draft `develop -> main` PR;
- check out and execute no PR/repository code;
- have exact job permissions `contents: write` and `pull-requests: write`, with every other permission absent; validation jobs retain only `contents: read` and `pull-requests: read`;
- authoritatively refetch current PR head/base/repository/draft/mergeability/labels immediately before merging;
- require current head/base to equal the event and validated prospective-merge identities;
- recompute base tag/label/target and require equality with Policy's immutable plan output;
- call native `gh pr merge --merge --match-head-commit <exact-head>` with no admin bypass;
- set deterministic merge subject `Release Buoy <target> (#<pr>)` and body trailers exactly:
  - `Buoy-Release-Label: <release label>`
  - `Buoy-Release-Version: <target>`
  - `Buoy-Release-Base-Tag: <base tag>`
  - `Buoy-Release-PR: <number>`
  - `Buoy-Release-Head: <exact head SHA>`;
- treat the label/plan observed and written by this controller as merge-time immutable release authority; later PR metadata changes cannot alter it;
- make no tag, Release, package, provider, protection, environment, or configuration mutation.

The controller performs the merge only after all required checks pass; no repository `allow_auto_merge` setting or mutable queued auto-merge request is used. Invalid current labels cannot reach this job. A concurrent metadata/head change causes `--match-head-commit` or identity revalidation to fail without merge. Human manual merging is unsupported for release PRs because it would lack the exact trailers; main-push validation fails before mutation.

## Tests and portability

Repository-local executable tests MUST cover event triggers/concurrency, exact job names/permissions/action SHA pins, branch/repository/parent checks, every label/SemVer/tag-authority vector, dynamic metadata/frozen changelog, target absence/partial state, deterministic target build, clean artifact smoke, labeled/unlabeled stale-run behavior, no-checkout final job, metadata reinspection, exact head matching, immutable trailers, and forbidden mutation/provider/registry behavior.

Release-critical calculations and merge-plan construction MUST remain repository-local standard Python/shell. GitHub is the explicit managed-platform exception. Documentation MUST map prospective-merge checks and final merge control to a self-hosted forge/runner using the same scripts, merge commit, labels, and trailers. No GitHub-only format enters package artifacts.

## Acceptance scenarios

- Exact patch label over released v0.4.0 computes 0.4.1; four checks pass; final controller revalidates and merge-commits with exact immutable trailers.
- Minor/major labels reset lower identifiers correctly.
- Missing/multiple labels, draft/cross-repo/wrong branches, ambiguous tag authority, existing/partial target, wrong dynamic metadata, wrong job names, or failed validation block without mutation.
- Adding/removing a release label cancels stale readiness and cannot merge while invalid.
- Automatic merge job runs only after all four checks, never checks out code, uses exact named permissions, and fails on stale head/base/plan.

## Explicit exclusions

Committed release-version bump; pending changelog sections; squash/rebase/manual/admin-bypass release merge; mutable queued auto-merge; `pull_request_target`; tag/Release creation during PR checks; PyPI; Turbopuffer; force push; environment approval; manual workflow dispatch; recurring ancestry bridge; product behavior changes.
