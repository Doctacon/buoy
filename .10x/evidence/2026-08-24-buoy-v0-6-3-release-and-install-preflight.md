Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/done/2026-08-24-install-v0-6-3-and-run-telemetry-pilot.md, .10x/decisions/one-time-v0-6-3-global-install-and-telemetry-pilot.md, .10x/tickets/done/2026-08-24-run-local-telemetry-v2-canary.md

# Buoy V0.6.3 Release and Install Preflight

## Observed release state

Read-only local and GitHub inspection established:

- remote `develop` is exact
  `4171555a81376b66cf5bf8cb51b1835bbf19129f`, tree
  `5c0da1521f4f82fb65dad12b262e2daa868242bc`;
- remote `main` is exact
  `4c0a04a443ddf792db9089242bca4d1e141db03d`, the same tree;
- `v0.6.3` is a lightweight tag resolving directly to exact `main@4c0a04a`;
- the public, non-draft, non-prerelease GitHub Release is
  `https://github.com/Doctacon/buoy/releases/tag/v0.6.3`, published
  2026-08-24T23:35:25Z with target `main`;
- the release has no attached wheel or source-distribution assets beyond
  GitHub's normal generated source archives.

The `develop` merge has ordered parents
`[d3ae1ba272c9ce8999332dd04058116e8a5dda0f,
410ab5a87bd198bdd0c8db05db9f4f9968f4f439]`. The `main` merge has ordered
parents
`[796f7384e2c86f6fb9e10f9099dbec589f8e47e6,
4171555a81376b66cf5bf8cb51b1835bbf19129f]`. Both preserve exact reviewed
canary-records tree `5c0da1521f4f82fb65dad12b262e2daa868242bc`.

No package, source, test, dependency, lock, workflow, documentation, README, or
changelog path differs between exact telemetry integration commit
`d3ae1ba272c9ce8999332dd04058116e8a5dda0f` and release commit `4c0a04a`.
The release therefore contains the exact canary-tested runtime plus records
only.

## Exact push CI

Exact `develop@4171555a` push CI run
`https://github.com/Doctacon/buoy/actions/runs/32789880349` passed:

- Python 3.11 job `97629169435`;
- Python 3.13 job `97629169232`; and
- Build distributions job `97629808003`.

Exact `main@4c0a04a` push CI run
`https://github.com/Doctacon/buoy/actions/runs/32789892473` passed:

- Python 3.11 job `97629203470`;
- Python 3.13 job `97629203558`; and
- Build distributions job `97629850718`.

The CI workflow retained no uploaded distribution artifact, so global install
must use a locally built artifact cryptographically bound to exact tagged
source rather than an unbound package-index candidate.

## Current local baseline

The repository root and canary records worktree were clean. Local and remote
`develop` and `main` matched the exact values above. The uv-managed user-global
installation still reported `buoy-search 0.6.2.dev2+g796f7384e` with sole
`buoy` executable. It is not the released candidate and must not produce the
new pilot observations.

The completed local canary previously established a compatible schema-v2 real
telemetry store with 16 persisted snapshots, four command-v2 rows, empty queues,
an idle writer, and retained immutable v1 backup. Fresh execution preflight
must revalidate compatible v2 state before retrieval; this record does not
assert that temporal state remains unchanged.

## What this supports

The exact tagged release is suitable as the sole source for a locally built
candidate. Exact source continuity and passing push CI support isolated artifact
validation before one authorized global uv-tool replacement. They do not by
themselves authorize installation, retrieval, provider access, or telemetry
mutation; those effects are governed separately.
