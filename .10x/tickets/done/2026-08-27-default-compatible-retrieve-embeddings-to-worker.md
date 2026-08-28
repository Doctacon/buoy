Status: done
Created: 2026-08-27
Updated: 2026-08-27
Parent: None
Depends-On: .10x/tickets/done/2026-08-27-connect-embedding-worker-to-retrieve-experiment.md
Decision: .10x/decisions/buoy-defaults-compatible-retrieve-embeddings-to-the-local-worker.md
Specification: .10x/specs/default-retrieve-embedding-worker.md
Evidence: .10x/evidence/2026-08-27-default-retrieve-embedding-worker.md
Prior-Evidence: .10x/evidence/2026-08-27-experimental-retrieve-embedding-worker-ab.md

# Default Compatible Retrieve Embeddings to the Worker

## Cold-start context

The reviewed explicit experiment produced byte-identical baseline/cold/warm live outputs and observed 10.523s, 8.789s, and 5.880s wall times respectively. The owner selected default worker activation with an explicit opt-out and visible in-process fallback. Custom/unsupported configurations retain the established in-process path.

## Scope

- Replace retrieve-only `--experimental-embedding-worker` with `--no-embedding-worker`.
- Select the worker by default only for exact compatible POSIX default configuration.
- Keep worker import and state absent for opt-out, custom model, float16, unsupported capability, explicit dry-run, non-retrieve, help, and version paths where no embedding is required.
- Implement command-wide, exactly-once, value-redacted visible fallback to the established in-process routing/retrieval embedders on eligible worker failure.
- Preserve provider call counts, routing/ranking/output semantics, credential boundaries, worker lifecycle/privacy, and optional retriever injection defaults.
- Update focused tests and retrieval documentation.
- Validate provider-free only; no additional live provider command is authorized.

## Explicit exclusions

Custom-model/float16/Windows worker support; silent fallback; provider credentials/clients in worker; pools/batching; cross-encoder residency; apply/index/evals activation; telemetry schema redesign; additional live A/B; global installation; release/deploy/publication.

## Acceptance criteria

1. Implementation exactly satisfies `.10x/specs/default-retrieve-embedding-worker.md`.
2. Eligible compatible retrieve commands default to one worker adapter for automatic routing plus retrieval, or one retrieval embedding for explicit namespaces.
3. `--no-embedding-worker` exists only on retrieve, creates no worker import/state/process/IPC, and uses the established in-process path.
4. The experimental opt-in flag is removed without an alias.
5. Custom model, float16, and unsupported capability select in-process directly with no worker side effect or warning.
6. Every eligible worker failure emits one bounded warning, switches the whole command to in-process embedding, duplicates no provider operation, preserves success semantics when fallback succeeds, and retains phase-correct failure if fallback also fails.
7. Automatic/explicit live and dry-run boundaries, no-flag default, opt-out, help/version, and non-retrieve dormancy are fully tested.
8. Existing worker, routing, retrieval, output, telemetry, and dual-runtime full suites pass; provider-free exact vector/ranking parity remains passing.
9. Validators, compilation, wheel/sdist, isolated install/help/opt-out/custom/dormancy smoke, diff hygiene, and no-staged-files checks pass.
10. Independent review passes with no unresolved significant finding.
11. No live provider, global install, release, deploy, or publication operation occurs.

## Evidence expectations

- Exact changed paths and default/fallback control-flow map.
- Focused matrix and failure/provider-call-count coverage.
- Full Python 3.11/3.13 outputs and test counts.
- Provider-free parity, process/dormancy, package/isolated-install evidence.
- Independent review, residual risks, diff/no-staged state, and retrospective.

## Blockers

None. Independent rereview passed at `.10x/reviews/2026-08-27-default-retrieve-embedding-worker-review.md` with no unresolved finding.

## Progress and notes

- 2026-08-27: Owner selected default worker activation with visible in-process fallback, explicit opt-out, and automatic in-process handling for custom/unsupported configurations. Activated the focused decision/spec and opened this executable ticket. No implementation occurred in this specification/ticket-authoring turn.
- 2026-08-27: Owner explicitly authorized execution. Ticket moved to active and assigned to an implementation subagent with the governing decision, specification, prior experiment evidence, and closed dependency.
- 2026-08-27: Implemented compatible default selection, retrieve-only `--no-embedding-worker`, removal of the experimental flag, lazy opt-out/custom/float16/unsupported/explicit-dry-run dormancy, and a shared command fallback session with phase-specific established in-process factories. First worker failure emits one bounded warning; later command embeddings bypass the worker; automatic catalog/content and explicit provider construction are not replayed. Retired the historical live harness before credentials/subprocesses; no live command ran.
- 2026-08-27: Initial final full suites passed 1,238 tests on each Python 3.11 and 3.13. Provider-free exact-model validation retained vector delta 0.0/equal ranking/same-PID reuse, measured 8,959.374 ms startup and 33.883 ms warm client, observed 524,812,288-byte RSS, and left source/cache unchanged with zero provider/network/telemetry operations and complete cleanup. Compile, ranking/promotion/C6 validators, wheel/sdist, isolated install/help/opt-out/custom/unsupported dormancy, diff hygiene, and no-staged-files checks passed.
- 2026-08-27: Independent review returned one P1: lazy fallback construction/encoding double failure could be mislabeled as `provider_call_error` or `routing_error`. Added a typed, redacted fallback-failure boundary; explicit live handling now replaces generic pipeline taxonomy with `model_error`, and automatic routing replaces the routing-stage category with `model_error` when the command session records fallback failure. Added explicit fallback-construction and automatic fallback-encoding regressions proving one warning, bounded phase-specific messages, no secret leakage, one permitted provider/catalog construction, and zero content operations/replay. Focused CLI/routing/telemetry suites passed 133 tests on both runtimes; final full suites passed 1,243 tests on Python 3.13 and 3.11. No live provider operation ran.
- 2026-08-27: Independent rereview passed with no unresolved finding at `.10x/reviews/2026-08-27-default-retrieve-embedding-worker-review.md`. Parent observed 133 focused Python 3.13 tests passing, diff hygiene, and no staged files. All acceptance criteria map to `.10x/evidence/2026-08-27-default-retrieve-embedding-worker.md`.
- 2026-08-27: Retrospective: a default optimization needs an availability path whose failures retain the semantic phase of the original backend, not the nearest generic catch block. Command-wide fallback state, exactly-once bounded warning, provider-operation-count assertions, and double-failure tests now preserve that invariant. No new generalized skill is needed beyond the active specification and regression suite.
