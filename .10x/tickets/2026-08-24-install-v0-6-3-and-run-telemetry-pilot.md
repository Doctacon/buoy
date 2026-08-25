Status: active
Created: 2026-08-24
Updated: 2026-08-24
Parent: None
Depends-On: .10x/tickets/done/2026-08-24-run-local-telemetry-v2-canary.md
Decision: .10x/decisions/one-time-v0-6-3-global-install-and-telemetry-pilot.md
Authorization-Evidence: .10x/evidence/2026-08-24-v0-6-3-install-and-telemetry-pilot-authorization.md
Preflight-Evidence: .10x/evidence/2026-08-24-buoy-v0-6-3-release-and-install-preflight.md
Specifications: .10x/specs/retrieve-command-telemetry.md, .10x/specs/local-telemetry-v2-storage-and-migration.md, .10x/specs/local-telemetry-writer.md
Knowledge: .10x/knowledge/provider-budgets-distinguish-logical-operations-and-transport-attempts.md

# Install V0.6.3 and Run Telemetry Pilot

## Outcome

Replace the old uv-managed global Buoy with exact released `v0.6.3`, then run
one bounded three-mode production-style read-only retrieval campaign that adds
sanitized testing observations to the compatible real telemetry-v2 store and
reports findings without changing provider, catalog, content, model, credential,
release, or unrelated state.

## Scope

1. Revalidate exact local/remote `develop`, `main`, tag, release, tree, CI,
   package-relevant source continuity, clean task/root worktrees, approved
   dataset digest, intended credential-source presence, and local model-cache
   baseline.
2. Record the complete content-free global uv-tool baseline and prepare an
   owner-private exact rollback artifact.
3. Build exact tagged `v0.6.3` in an owner-private temporary source tree; verify
   artifact metadata/safety/content, accepted source identities, dependencies,
   entry point, version, and isolated-home provider-free smoke.
4. Replace only the global uv-managed `buoy-search` tool once and verify exact
   installed release identity, non-Buoy inventory invariance, help behavior,
   and compatible real-home telemetry status.
5. Require compatible schema v2, empty queues, retained backup, idle writer,
   and no active independent install/writer/migration process before provider
   access.
6. Privately extract the approved case values from the exact dataset and run
   exactly one live explicit-single, one live explicit-multi, and one live
   automatic retrieval in that order. Enable telemetry and offline model mode
   only in each command subshell; load the intended credential source there
   after removing inherited provider credentials. Never persist raw arguments
   or retrieval output.
7. Stop later retrievals after any command failure. Invoke the one final bounded
   flush, wait for terminal writer state, inspect the exact new telemetry window
   read-only, and run a complete private-literal scan without recording literal
   values.
8. Record sanitized evidence, obtain independent review, remove temporary
   artifacts, retain the accepted telemetry rows and immutable v1 backup, and
   reconcile the ticket and governing decision honestly.

## Acceptance criteria

- Exact `develop`, `main`, `v0.6.3`, GitHub Release, tree, and successful push
  CI identities match the governing evidence before installation.
- Candidate wheel is built from exact tagged commit/tree, reports version
  `0.6.3`, has safe regular contents and sole
  `buoy=buoy_search.entrypoint:main` entry point, passes dependency and isolated
  provider-free smoke checks, and reproduces accepted production source
  identities.
- The pre-install uv-managed global baseline and exact old-version rollback
  artifact are bound before replacement; only `buoy-search` changes.
- Exactly one forward global replacement exits zero and the installed package,
  version, entry point, source identities, dependencies, and uv provenance match
  the candidate. Immediate acceptance passes, so rollback does not run.
- Fresh real-home status is compatible schema v2 with retained backup, safe
  empty queues, idle writer, no durability degradation, and no active
  installation/writer/migration process before retrieval.
- The approved dataset digest is exact. Exactly three commands begin at most
  once and in order: live explicit-single `u01`, live explicit-multi `m01`, and
  live automatic `m01`. All exit zero and produce valid result shape.
- The exact new telemetry window contains three successful live command rows in
  those three modes with nonnegative command and pipeline durations,
  command-enclosed pipeline intervals, source-reachable governed stage graphs,
  truthful counts/outcomes, automatic fanout at most three, zero failures, and
  at most six total logical namespace spans.
- Exactly one final flush reaches empty terminal queue/writer state with no
  conflicts, rejections, replays, write failures, or durability degradation.
- New telemetry artifacts contain no query, argv, namespace, credential,
  content, URL, provider response, raw error, stack trace, document/source
  identifier, or private path value.
- Provider/catalog access is read-only; no namespace/content/catalog write,
  model download/cache change, credential change, release/ref/GitHub mutation,
  other-tool mutation, migration, purge, backup change, or unrelated effect
  occurs.
- Temporary build, rollback, command-output, and analysis artifacts are removed
  after evidence. The global tool remains exact `v0.6.3`; the three sanitized
  telemetry observations and immutable v1 backup remain.
- Independent review returns PASS or all findings are resolved. Every criterion
  maps to reproducible evidence with limits; physical transport attempts remain
  explicitly unknown.

## Evidence expectations

Record exact refs/tree/release/CI; candidate and rollback artifact identities;
pre/post global package/runtime/entry-point/source/dependency and other-tool
inventories; sanitized pre/post telemetry status; three mode/outcome/timing/
fanout/failure/stage summaries; logical namespace-span count; flush/terminal
health; model-cache equality; private-literal scan verdict; cleanup; and all
limits. Never record credentials, private input values, argv, output content,
URLs, provider responses, raw errors, stack traces, or private path components.

## Explicit exclusions

Installation retry; retrieval retry or substitution; more than three retrieval
commands; provider/catalog/namespace/content write; model download; credential
retrieval/change; telemetry migration/purge/retention change; backup deletion or
replacement; release/tag/ref/GitHub/workflow change; other-tool mutation;
physical-attempt inference; recurring telemetry enablement; unrelated cleanup.

## Progress and notes

- 2026-08-24: Owner selected the recommended three-run production-style pilot
  after explicitly directing exact release installation and telemetry data
  collection. Read-only release preflight bound exact branches, tag, release,
  CI, source continuity, and the old global-tool baseline. No installation,
  real-home inspection, credential/model access, retrieval, telemetry write, or
  provider operation has begun.
- 2026-08-24: Activated at records commit
  `aa13d6a69494eceaf2a22abb243d6f3dbce1443b` on clean
  `work/v0-6-3-telemetry-pilot`, based on exact `develop@4171555a`. Execution
  must use exact tagged release source, not this records commit. Forward install,
  each retrieval, and flush remain individually unconsumed.

## Blockers

None. Scope, effects, workload identities, logical-operation budget, failure
behavior, privacy, retention, installation target, and acceptance evidence are
explicitly user-ratified or record-backed.
