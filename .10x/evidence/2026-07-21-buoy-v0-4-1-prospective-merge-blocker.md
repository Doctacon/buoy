Status: recorded
Created: 2026-07-21
Updated: 2026-07-21
Relates-To: .10x/tickets/2026-07-21-release-buoy-v0-4-1-through-main-automation.md

# Buoy v0.4.1 Prospective-Merge Blocker

## Observation

PR #93 (`Doctacon/buoy-search:develop -> main`) is open at exact develop `8694afc94984e6993730acd205af3bdca93c5c8b`, but GitHub reports `mergeable=CONFLICTING` and `mergeStateStatus=DIRTY`. Only ordinary CI ran. The four `Release readiness / ...` checks did not start because GitHub could not construct the prospective merge ref required by `.10x/specs/develop-to-main-release-readiness.md`.

Main remains `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`; no v0.4.1 tag or Release was created.

## Procedure

- Queried PR #93 metadata and check rollup with `gh pr view`.
- Fetched exact remote main/develop.
- Computed merge base `820b8abba4308481eace728203d98f3365154956`.
- Ran read-only `git merge-tree --write-tree --messages origin/main origin/develop`.

## Cause

The user-approved v0.4.0 squash promotion made main's `c49dc05` tree equal the then-reviewed develop tree without making develop an ancestor of main. Later protected develop work independently changed files also changed on main since merge base `820b8ab`. Git therefore reports add/add or content conflicts in release records, release workflow/docs, changelog, version authorities, release tests, and lock data.

This is inherited topology from the v0.4 transition. It is not a v0.4.1 source, test, version, or readiness-policy failure.

## What this supports

The new readiness workflow is fail-closed: it cannot run without a GitHub prospective merge commit, and protection blocks promotion. The current active ticket excludes ancestry sync, so execution cannot repair this topology without explicit user ratification of a narrow exception or a separately ratified process redesign.

The smallest bounded recovery is one protected, content-neutral ancestry bridge making exact main `c49dc05` a parent of exact develop `8694afc`, preserving the develop tree. After protected integration and revalidation, PR #93 can be refreshed or recreated from exact develop and the new process can run normally. This bridge is a one-time migration exception, not recurring release ceremony.

## Ratification

After the conflict and recovery boundary were explained, the user explicitly authorized the recommended one-time protected ancestry bridge on 2026-07-21. The exact non-repeatable contract is recorded in `.10x/decisions/one-time-v0-4-squash-topology-bridge.md` and `.10x/specs/develop-to-main-release-readiness.md`.

## Limits

No branch, source, protection, tag, Release, asset, registry, provider, or user state was mutated during diagnosis or ratification. No merge, retry, repair, or cleanup was attempted.
