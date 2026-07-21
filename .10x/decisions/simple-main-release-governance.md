Status: active
Created: 2026-07-21
Updated: 2026-07-21

# Simple Main Release Governance

## Context

The prior release process required strict main freshness, ancestry-sync PRs, manual tag creation, release-environment approval, and post-hoc conversational verification. During v0.4.0 this created repeated process friction and still allowed a human squash merge that violated the intended topology. The user explicitly rejected that ceremony and selected required develop-to-main readiness checks plus fully automatic main-push publication.

Independent review proved strict main freshness/main-ancestor enforcement is the source of recurring ancestry-sync mechanics. The user ratified dropping those requirements and last-push approval on main, while retaining the previously selected main force-push allowance and prohibiting workflows/agents from using it.

The first real release PR later proved the already-accepted v0.4 squash topology was itself unmergeable before GitHub could construct a prospective merge ref. The user therefore ratified the exact non-repeatable migration bridge in `.10x/decisions/one-time-v0-4-squash-topology-bridge.md`; it repairs inherited history once and does not restore recurring sync ceremony.

## Decision

- `develop` remains the protected integration branch with strict ordinary Python 3.11, Python 3.13, and Build distributions checks.
- `main` remains PR-only/release-only with administrator enforcement and deletion denial, but uses `strict=false` and `require_last_push_approval=false`.
- Main requires the four checks in `.10x/specs/develop-to-main-release-readiness.md`; they validate GitHub's prospective merge commit and exact develop head rather than requiring recurring ancestry sync. The sole pinned v0.4 migration bridge is governed separately and expires after execution.
- Every successful new-version main push follows `.10x/specs/main-push-automatic-github-release.md`: serialized validation, deterministic build once, annotated tag, provenance, and GitHub Release without manual approval.
- Existing exact complete state is an idempotent no-op; every partial/mismatched state permanently fails without automated repair or destructive cleanup.
- Stable SemVer only; each future main release requires an explicit version bump and pending changelog.
- The unused release environment is deleted after zero references/deployments are proved.
- Main force pushes remain hosted-enabled by prior user choice but are not authorized for any agent/workflow/release path.

## Alternatives considered

### Retain strict main freshness

Rejected because it necessarily retains ancestry incorporation between releases.

### Keep manual tag or environment approval

Rejected by explicit user choice; deterministic checks and fail-closed immutable state replace conversational gates.

### Release every main commit under commit tags

Rejected. Stable project SemVer remains the public identity; unchanged versions fail readiness.

### Move or overwrite existing version tags

Rejected as destructive and incompatible with immutable release evidence.

### Publish to PyPI

Rejected. Releases remain GitHub-only.

## Consequences

Release safety moves from manual sequencing to required merge-result checks and a deterministic main-push state machine. After the exact inherited v0.4 topology is repaired once, main can diverge historically from develop without recurring sync ceremony because GitHub's prospective merge result is the validated unit. A partial publication permanently blocks that version until separately handled. Future releases require version/changelog preparation in develop. GitHub remains a user-required managed-host exception with repository-local portable logic and a documented self-hosted migration path.

This decision supersedes `.10x/decisions/superseded/protected-development-and-github-release-governance-v2.md` for branch/release governance. Historical decisions/evidence remain preserved.
