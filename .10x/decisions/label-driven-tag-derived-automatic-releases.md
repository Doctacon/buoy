Status: superseded
Created: 2026-07-21
Updated: 2026-07-21

# Label-Driven Tag-Derived Automatic Releases

## Context

The static-version release process required coordinated edits to project/module/lock/changelog and exposed configuration mistakes before the first automated release. The user explicitly requested that future operation be only: open one PR, wait for CI, merge, and receive an automatic deployment. The user ratified exact release labels, tag-derived versions through open-source `hatch-vcs`, frozen historical changelog, GitHub-generated future notes, merge commits, and automatic merging.

Research in `.10x/research/2026-07-21-label-driven-tag-derived-release-automation.md` proved the current Hatch/uv project supports dynamic VCS versions and exact release-build override without lock churn, and GitHub can bind a main merge commit back to its exact PR and labels.

## Decision

- Every release uses one same-repository `develop -> main` PR.
- The PR MUST carry exactly one of `release:patch`, `release:minor`, or `release:major`; missing/multiple labels fail closed.
- The next stable version is derived deterministically from the highest valid stable annotated released tag reachable from base main, incremented by the exact label using SemVer core rules.
- Buoy package versions are VCS-derived with pinned open-source `hatch-vcs==0.5.0`; release validation/build uses exact `SETUPTOOLS_SCM_PRETEND_VERSION`.
- `CHANGELOG.md` becomes frozen history through v0.4.0 and points future readers to GitHub Releases. GitHub-generated notes are future release notes.
- After all four checks pass, a final no-checkout least-privilege readiness job refetches exact current metadata and merge-commits with immutable release-plan trailers. It uses no mutable queued auto-merge state.
- Main-push publication recovers the exact merged PR and immutable commit trailers, verifies two-parent `[prior main, exact develop]` topology, recomputes the version, rejects any different stable release already associated with the SHA, and then uses the deterministic immutable-state publication guarantees.
- Ordinary work PRs into develop continue to squash. Release PRs into main use merge commits so develop remains in main ancestry.
- No PyPI or Turbopuffer release behavior is introduced.

This decision supersedes `.10x/decisions/superseded/simple-main-release-governance.md`. Its exact collision, least-privilege, deterministic-build, legacy-v0.4, and no-destructive-repair guarantees remain unless this decision explicitly replaces static version/changelog mechanics.

## Alternatives considered

### Keep static version preparation

Rejected by explicit user direction; it preserves the ceremony being removed.

### Conventional commits choose version

Rejected because commit-message conventions can accidentally change public version semantics. One explicit PR label is simpler and reviewable.

### Bot-edit the protected develop branch

Rejected. Dynamic versions avoid write-token bypass of protected source branches.

### Squash release PRs

Rejected. The accepted v0.4 squash caused historical divergence and conflicts. Merge commits preserve release ancestry.

### Freeze package version at build-script metadata only

Rejected. Standard dynamic project metadata plus generated `__version__` keeps wheels, installed metadata, and CLI identity coherent.

## Consequences

A release operator opens/labels one PR and can walk away. CI's final merge controller handles promotion; main-push automation handles publication. Source checkouts expose a PEP 440 VCS development version, while release artifacts expose exact stable SemVer. The repository must create the three labels; native queued auto-merge need not be enabled. Main publication fails before mutation if immutable trailers, PR association, topology, tag authority, version, duplicate-SHA release state, artifacts, or provenance are ambiguous.
