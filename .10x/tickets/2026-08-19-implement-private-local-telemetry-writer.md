Status: active
Created: 2026-08-19
Updated: 2026-08-19
Decision: .10x/decisions/buoy-uses-a-private-local-telemetry-writer.md
Specification: .10x/specs/local-telemetry-writer.md
Depends-On: .10x/tickets/done/2026-08-18-implement-local-retrieval-telemetry.md
Diagnostic-Evidence: .10x/evidence/2026-08-19-local-telemetry-100-scenario-findings.md

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
  tests/docs changes and one bounded task commit. Validation may create only
  isolated temporary homes, inboxes, databases, processes, environments, and
  distribution artifacts. Evidence and independent review records are planned
  closure outputs. Branch push, pull request, and integration require a later
  explicit handoff authority.

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
