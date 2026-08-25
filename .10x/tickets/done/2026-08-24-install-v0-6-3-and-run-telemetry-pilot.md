Status: done
Created: 2026-08-24
Updated: 2026-08-24
Parent: None
Depends-On: .10x/tickets/done/2026-08-24-run-local-telemetry-v2-canary.md
Decision: .10x/decisions/one-time-v0-6-3-global-install-and-telemetry-pilot.md
Authorization-Evidence: .10x/evidence/2026-08-24-v0-6-3-install-and-telemetry-pilot-authorization.md
Preflight-Evidence: .10x/evidence/2026-08-24-buoy-v0-6-3-release-and-install-preflight.md, .10x/evidence/2026-08-24-v0-6-3-install-and-pilot-preparation.md
Execution-Evidence: .10x/evidence/2026-08-24-v0-6-3-installed-telemetry-pilot.md
Specifications: .10x/specs/retrieve-command-telemetry.md, .10x/specs/local-telemetry-v2-storage-and-migration.md, .10x/specs/local-telemetry-writer.md
Knowledge: .10x/knowledge/provider-budgets-distinguish-logical-operations-and-transport-attempts.md
Review: .10x/reviews/2026-08-24-v0-6-3-installed-telemetry-pilot-review.md
Follow-Ups: .10x/tickets/done/2026-08-24-investigate-retrieve-command-outer-latency.md, .10x/tickets/2026-08-24-define-physical-provider-attempt-accounting.md

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
- 2026-08-24: Preparation PASS. Exact release/tag/tree/CI were revalidated; an
  exact `0.6.3` candidate and exact old-version rollback wheel were built and
  accepted offline; locked dependencies, sole entry point, source identities,
  isolated status/help, global baseline, non-Buoy tools, approved dataset,
  credential-source presence, and 159-entry model-cache manifest were bound.
  Private forward and rollback commands both passed isolated uv-tool rehearsal.
  Sanitized evidence is at
  `.10x/evidence/2026-08-24-v0-6-3-install-and-pilot-preparation.md`. No global
  replacement, real-home telemetry inspection, provider/model operation,
  retrieval, or flush began; all one-time authorities remain unconsumed pending
  independent install gate.
- 2026-08-24: Independent review issued `INSTALL-GO`. Fresh immutable bindings,
  real compatible-v2/empty-queue/idle-writer state, old global identity,
  rollback smoke, model cache, dataset, credential presence, refs, clean
  worktrees, and process absence all passed immediately before replacement.
- 2026-08-24: The sole global replacement exited zero and installed exact
  uv-managed `buoy-search 0.6.3` on Python 3.13.0 with accepted source,
  entry-point, dependency, help, status, and non-Buoy-tool identities. Immediate
  acceptance passed, so no rollback ran.
- 2026-08-24: All three authorized live commands began once, in order, and
  exited zero with valid JSON-object results. Three new successful command-v2
  rows recorded truthful enclosed command/pipeline timing, five logical
  namespace spans, five hits each, zero failures, automatic fanout two,
  supported automatic evidence, and no widening. The sole flush returned
  `empty` because detached writers had already committed all rows.
- 2026-08-24: Final schema-v2 snapshot/receipt count is 19 with empty queues,
  idle/terminated writer, 12 preserved v1 runs, and byte-identical immutable
  backup. Privacy scanning covered 87 private literals, five changed telemetry
  artifacts, 5,781,571 bytes, and 488 exact new-trace string/JSON scalars with
  zero matches. Model cache, refs, source, GitHub/release state, and non-Buoy
  tools remained unchanged. Sanitized execution evidence is at
  `.10x/evidence/2026-08-24-v0-6-3-installed-telemetry-pilot.md`.
- 2026-08-24: Global-install, all three retrieval, and sole flush authorities
  are consumed. Temporary private artifacts are pending removal after record
  commit; the accepted global installation and three telemetry rows remain.
- 2026-08-24: Two independent reviewers returned PASS on exact execution commit
  `084664c1c4c34400e768c840ff5c5bd8733ea5db`. Every criterion mapped to
  evidence; both confirmed exact installed release identity, three once-only
  successful commands, truthful telemetry, healthy persistence, privacy,
  logical-operation bounds, side-effect invariants, and cleanup. Review is
  recorded at
  `.10x/reviews/2026-08-24-v0-6-3-installed-telemetry-pilot-review.md`.
- 2026-08-24: Worker and parent workflow temporary roots/artifacts were removed.
  Parent readback observed uv-managed `buoy-search v0.6.3`, exact clean task/root
  Git state, and unchanged release refs without rerunning telemetry, retrieval,
  flush, provider/model, credential, or database operations.

## Blockers

None. Exact release installation and the three-command production telemetry
pilot satisfy every acceptance criterion. Further collection or performance
work requires separate authority.

## Retrospective

- Building and rehearsing exact tagged candidate/rollback wheels before the one
  global replacement gave a bounded, reversible install without relying on an
  attached GitHub release asset.
- Command-level telemetry worked as designed and exposed the important result:
  88.6%–96.7% of observed command latency was outside the nested pipeline. The
  finding is owned by
  `.10x/tickets/done/2026-08-24-investigate-retrieve-command-outer-latency.md` and is
  not yet a latency distribution or optimization mandate.
- Logical namespace spans remain distinct from physical provider attempts;
  future transport accounting remains owned by
  `.10x/tickets/2026-08-24-define-physical-provider-attempt-accounting.md`.
- No instruction, specification, source, test, release, or rollback repair was
  required. The installed release, three content-free rows, and immutable
  backup are the intentional retained outcomes.
