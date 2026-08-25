Status: superseded
Created: 2026-08-24
Updated: 2026-08-24

# One-Time V0.6.3 Global Install and Telemetry Pilot

## Disposition and consumed authority

The sole global replacement, all three retrievals, and the sole flush began and
completed under this decision. Exact `buoy-search 0.6.3` installed successfully;
immediate acceptance passed; no rollback ran. All three commands exited zero
and retained three private command-v2 observations. Independent review passed.

Every execution authority is consumed, and unused rollback authority expired
at successful candidate acceptance. This decision is superseded by consumption
with no successor operational authority. It grants no reinstall, rollback,
additional collection, provider/model access, telemetry operation, global-tool
change, release action, or retry.

## Context

Exact telemetry runtime and records are now on `develop`, `main`, and public
lightweight tag/GitHub Release `v0.6.3`. Exact branch push CI passed on Python
3.11, Python 3.13, and distribution build. The released runtime is byte-identical
on package-relevant paths to the integrated and real-store-canary-tested
runtime.

The user-global uv-managed tool remains the older
`0.6.2.dev2+g796f7384e` installation. The real local telemetry store has already
been explicitly migrated to schema v2 and contains four canary command rows.
The owner now wants the released global tool installed and a small
production-style read-only campaign retained as testing data.

## Decision

Authorize `.10x/tickets/done/2026-08-24-install-v0-6-3-and-run-telemetry-pilot.md`
to perform one exact release installation followed by one three-command pilot.

### Exact installation

- Build the candidate only from exact tagged commit
  `4c0a04a443ddf792db9089242bca4d1e141db03d` in an owner-private temporary
  source tree. Verify tag, commit, tree, package version, entry point, wheel
  safety, dependencies, accepted telemetry/routing source identities, and an
  isolated provider-free smoke before global mutation.
- Bind the existing uv-managed global package/runtime/source baseline and stage
  one exact old-version rollback artifact before replacement.
- Invoke one `uv tool install --force` replacement using the verified local
  candidate artifact. Invocation start consumes forward authority; no retry is
  granted.
- Accept only exact version `0.6.3`, the expected entry point and package source,
  compatible dependencies, unchanged non-Buoy tools, and successful help plus
  read-only real-home telemetry-v2 status.
- A rollback may run once only after a known-terminal forward result installs a
  non-accepted candidate and independent parent audit confirms the exact
  rollback predicate. Successful candidate acceptance expires rollback.

### Three-command production-style pilot

After installation acceptance and a fresh compatible-v2/idle-writer/safe-queue
gate, run exactly once and in order:

1. live explicit-single using approved case `u01-dagster-purpose`;
2. live explicit-multi using approved case
   `m01-dagster-turbopuffer-quality`; and
3. live automatic using that same approved multi-corpus case.

The approved dataset must retain SHA-256
`29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`.
Private case values are loaded at runtime and never enter records. The campaign
permits at most six logical namespace operations plus established bounded
automatic catalog reads. Each command begins at most once; failure stops later
commands without retry or substitution.

Telemetry is enabled only in each command subshell. Existing pinned local model
assets run under offline settings. The intended credential source is loaded
only inside the subshell after inherited provider credentials are removed. No
provider/catalog/namespace/content write, model download, credential mutation,
or remote telemetry export is permitted.

After the commands begun under this authority finish, invoke exactly one bounded
flush, wait for terminal writer state, and inspect only sanitized command/pipeline
rows, governed stages, fanout/hit/failure/widening outcomes, queue health, and
content-free privacy invariants. Retain accepted rows in the real schema-v2
store as the requested testing data. Remove temporary build, rollback, raw
output, and analysis artifacts after durable sanitized evidence is complete.

## Failure and consumption boundaries

Global-install authority is consumed when the sole replacement starts. Each
retrieval authority is consumed when its command starts. Flush authority is
consumed when the one flush starts. Failure, interruption, ambiguity, or review
gaps grant no retry.

An install failure stops before provider access. A retrieval failure preserves
truthful telemetry, stops later retrievals, and proceeds only to the one flush
and sanitized readback. Telemetry failure must not change retrieval behavior.

## Alternatives considered

### Keep using an isolated candidate

Rejected. The owner explicitly requested installation of the released Buoy,
and exact release/runtime continuity plus passing CI make the temporary-canary
constraint unnecessary.

### Install from an unversioned branch or package index

Rejected. The exact public tag is available while the GitHub Release has no
attached wheel. A locally built tagged artifact gives exact source identity
without trusting an unrelated mutable package candidate.

### Run a larger campaign

Rejected for the first installed-release sample. Three live modes provide the
smallest balanced production-style dataset and bound provider effects while
confirming the released global path.

## Consequences

On success the user-global command remains exact `v0.6.3`, the real telemetry
store gains three content-free command observations, and findings can compare
near-shell command duration with nested pipeline duration across all live modes.
The store remains opt-in and local-only; ordinary commands without
`BUOY_TELEMETRY=local` produce no observation.

This one-time decision authorizes no future recurring campaign, release work,
provider write, automatic telemetry enablement, or physical-attempt claim. Any
additional collection requires a new explicit workload and effect boundary.
