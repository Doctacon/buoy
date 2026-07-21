Status: active
Created: 2026-07-21
Updated: 2026-07-21

# One-Time v0.4 Squash Topology Bridge

## Context

The user accepted v0.4.0 promotion as squash commit `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d` because its tree exactly matched the reviewed release candidate. Develop subsequently continued on its original lineage. The branches still share merge base `820b8abba4308481eace728203d98f3365154956`, but both histories independently changed release/version files.

The first automated release PR, #93 (`develop -> main` for 0.4.1), is therefore `CONFLICTING`. GitHub cannot create the prospective merge ref, so the four required readiness checks cannot run. No release state changed.

## Decision

Authorize exactly one protected, content-neutral ancestry bridge before retrying PR #93:

- bridge only exact main `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d` into the then-current protected develop head;
- create the bridge on an isolated `work/*` branch from that exact develop head;
- the bridge commit MUST have exact main as an ancestor and MUST have a tree byte-identical to its develop parent;
- expose the bridge through a protected pull request to develop and integrate it with merge-commit ancestry preservation, never squash, rebase, direct push, force push, or protection weakening;
- verify before and after integration that develop's tree is unchanged and that exact main is now an ancestor of develop;
- make no version, changelog, workflow, product, tag, Release, asset, registry, provider, or configuration change;
- then allow exact `develop -> main` PR #93 to refresh and execute the normal four-check/automatic-release process;
- never generalize or repeat this exception after the inherited v0.4 topology is repaired.

The user explicitly ratified this exact one-time bridge on 2026-07-21 after the blocker and non-mutation boundary were explained.

## Alternatives considered

- **Stop v0.4.1:** safe but does not test or deliver the requested process.
- **Redesign readiness around a synthetic release branch:** larger and weakens the exact-develop source invariant without solving repository history.
- **Force/rebase develop:** rewrites protected shared history and is prohibited.
- **Resolve PR #93 manually in main:** bypasses the required prospective-merge source contract and risks choosing main-side stale release files.

## Consequences

One legacy-style ancestry operation remains necessary as migration cleanup because the prior squash topology predates the new process. It is protected, reviewable, content-neutral, and pinned. Afterward, ordinary release promotion remains exactly `develop -> main` with no recurring sync ceremony.
