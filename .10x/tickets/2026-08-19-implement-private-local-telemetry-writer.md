Status: active
Created: 2026-08-19
Updated: 2026-08-19
Decision: .10x/decisions/buoy-uses-a-private-local-telemetry-writer.md
Specification: .10x/specs/local-telemetry-writer.md
Depends-On: .10x/tickets/done/2026-08-18-implement-local-retrieval-telemetry.md
Diagnostic-Evidence: .10x/evidence/2026-08-19-local-telemetry-100-scenario-findings.md
Evidence: .10x/evidence/2026-08-19-local-telemetry-writer.md
Prior-Review: .10x/reviews/2026-08-19-local-telemetry-writer-review.md
Review: pending exact repaired-head review

# Implement Private Local Telemetry Writer

## Outcome

Move enabled retrieval telemetry's DuckDB work off the short-lived retrieval
process by atomically publishing sanitized private envelopes and draining them
through one bounded Buoy-owned local writer. Preserve the existing database,
privacy contract, retrieval behavior, and local-only ownership while removing
fresh-process DuckDB latency and contention loss.

## Owned scope

- Amend the prior local-telemetry decision/specification with the approved
  private-writer architecture.
- Add exact envelope serialization/revalidation and a bounded private inbox.
- Add one lock-elected, bounded-idle and bounded-work-admission detached local
  writer with crash-safe idempotent replay into the unchanged DuckDB v1
  schema; do not claim cancellation of an in-flight DuckDB filesystem call.
- Change retrieval telemetry completion from synchronous DuckDB append to
  atomic envelope publication plus best-effort writer start.
- Add read-only `buoy telemetry status` and bounded `buoy telemetry flush`.
- Add focused envelope, filesystem, privacy, concurrency, crash, replay,
  lifecycle, CLI, and performance tests.
- Update local telemetry documentation, README/changelog, evidence, and review.

## Required implementation properties

- No generic OpenTelemetry Collector, OTLP, listener, socket, remote backend,
  cloud destination, or unsanitized handoff exists.
- Disabled telemetry remains a zero-side-effect no-op.
- Retrieval never opens DuckDB or waits for database persistence.
- Only independently revalidated `trace-envelope/v1` values may reach the
  unchanged DuckDB v1 store.
- Successfully published envelopes survive writer absence, contention, and
  supported crash boundaries until committed or explicitly classified.
- Concurrent publishers do not share output filenames and do not lose traces
  merely because another writer is active.
- Queue/storage/process/accounting resources are bounded and private.
- Status is read-only; flush is explicitly bounded; both are local and
  content-free.
- Every telemetry failure preserves the original retrieval result/error and
  stdout/stderr behavior.

## Validation

- focused telemetry writer/envelope/status/flush and established retrieval
  suites;
- 100-process publication/flush and graph-integrity challenge;
- crash points through publication, claim, transaction, commit, and ack;
- forged-envelope and exact-byte privacy scans across every durable artifact;
- symlink/hardlink/FIFO/socket/permission/ownership/path-race challenges;
- fresh-process paired latency and warm-writer visibility measurements;
- no-DuckDB-binding-in-producer and zero-network/credential-child probes;
- full unittest discovery on Python 3.11 and 3.13;
- lock/source/ranking/C6/compile/diff checks; and
- distribution inspection plus clean-wheel installed-console lifecycle smoke.

## External-effects boundary

Authorized durable effects are the isolated
`work/local-telemetry-writer` branch/worktree, the bounded records/source/
tests/docs changes and bounded governance/implementation commits. Validation
may create only isolated temporary homes, inboxes, databases, processes,
environments, and distribution artifacts. Evidence and independent review
records are the closure outputs. Branch push, pull request, and integration
require a later explicit handoff authority.

No real `~/.buoy` asset, installed tool, provider, model, credential,
namespace, catalog/content state, `main`, release, tag, package, GitHub Release,
or branch-protection setting may be read or changed. No remote telemetry or
listener is authorized.

## Exclusions

Standard Collector/OTLP support, permanent service installation, remote
backend integration, database migration, retention/purge, analytics UI,
additional signals/instrumentation, query fingerprints, feedback capture,
raw/dead-letter payload archives, and release/installed-tool work.

## Progress

- 2026-08-19: The owner directed execution of the previously recommended
  local writer. Work paused when the owner challenged whether the Adobe,
  Mastodon, or Skyscanner reference deployments matched it. Review confirmed
  that none uses a filesystem spool or DuckDB; Mastodon supports only the
  single-owner principle. The owner then approved the accurately named Buoy
  local writer recommendation. Renamed the clean isolated branch/worktree to
  `work/local-telemetry-writer` at exact `develop`
  `3787e0eabd2720732fb5c68ca168f926342ae454` before implementation.
- 2026-08-19: The first synchronized 100-process implementation run exposed a
  real publication-contention blocker: the initial 250-ms producer lock bound
  persisted 93 of 100 instrumented publications in the confirming run. The
  exact same harness persisted 100 of 100 at 500 ms with 259.7-ms maximum
  producer time; 1,000 ms also persisted all traces but was slower. The
  governing specification now assigns 500 ms only to producer publication and
  retains 250 ms for writer/management locks pending the final campaign.
- 2026-08-19: The first exact-source warm-visibility campaign exposed a second
  real contention blocker. Separate read-only validation and read-write append
  connections yielded p95 421.4 ms and p99 660.8 ms while a consumer polled
  DuckDB. One verified transaction connection reduced the tail but the 100-ms
  retry cadence still yielded p95 320.1 ms and p99 511.8 ms. Controlled
  100-trace comparisons on that one-connection design passed with fixed 10-ms
  retry (p95 72.8 ms, p99 82.6 ms, max 91.3 ms), fixed 5-ms retry (p95 112.2
  ms, p99 140.1 ms, max 201.1 ms), and bounded exponential retry (p95 82.0 ms,
  p99 139.7 ms, max 240.5 ms). Fixed 10 ms also required the fewest failed
  opens, so the governing specification now selects it. Validation remains
  per trace and shares the exact transaction connection; no lifecycle cache
  or persistent DuckDB session is introduced.
- 2026-08-19: Final frozen-source acceptance passed 100/100 synchronized
  publications with 100 complete graphs and no loss, 100/100 paired retrieval
  equivalence checks, p99 3.147-ms added producer latency, p99 90.827-ms warm
  visibility, three cold-home visibility checks below 500 ms, a zero-DuckDB
  producer guard, and natural exit for every observed writer. The 38-case
  adversarial campaign and 144-test focused suite passed without a blocker.
- 2026-08-19: Exact implementation commit
  `55f41fd9e2f98fed83fd0619c29a9a5549ae4052`, tree
  `08b1679963b9b88d73601458e7a9890696591e68`, passed all 1,027 tests on
  Python 3.11 and Python 3.13, including a second complete Python 3.13 run with
  local telemetry enabled. Source/lock/ranking/C6/compile/diff, distribution,
  clean-wheel lifecycle, privacy, filesystem, and independent exact-commit
  review gates passed. The task is ready for a separately authorized
  integration handoff; this implementation session does not push or merge it.
- 2026-08-19: Installation preflight found that the built wheel correctly
  exposed the new lightweight `buoy_search.entrypoint:main`, but the release
  validator and active package-identity specification still required the old
  direct `buoy_search.cli:main` mapping. PR #134's Python 3.11 and 3.13 jobs
  passed and its Build distributions job failed on that exact mismatch. The
  PR was returned to draft before merge, no tool replacement occurred, the
  prior review was superseded, and this ticket was reopened for a bounded
  validator/spec/test/evidence repair and full revalidation.
