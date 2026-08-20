Status: open
Created: 2026-08-20
Updated: 2026-08-20
Parent: .10x/tickets/2026-08-20-correct-retrieve-command-telemetry-latency.md
Depends-On: None
Decision: .10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md
Specification: .10x/specs/local-telemetry-v2-storage-and-migration.md

# Implement Local Telemetry V2 Storage and Migration

## Scope

Implement the version-2 envelope, separate inbox, dual-version writer,
additive exact DuckDB schema/views, read-only upgrade-required status, bounded
flush behavior, and explicit backed-up migration command. Use deterministic
content-free fixture traces; do not instrument production retrieve commands in
this ticket.

Owned modules are telemetry envelope, queue, store, writer, management CLI,
entry-point telemetry dispatch needed for `migrate`, focused tests, and the
minimum user documentation for migration mechanics.

## Required work

- Preserve exact v1 encoder/decoder, inbox, rows, views, and direct-library
  producer compatibility.
- Add canonical independently validated v2 command/retrieval-operation
  envelopes and fixed v2 queue/receipt names.
- Add exact schema-v2 command/operation tables and two canonical v2 views while
  retaining exact v1 view SQL and values.
- Make the writer safely drain v1/v2 under the specification's schema matrix.
- Expose read-only `upgrade_required` and versioned queue facts.
- Add `buoy telemetry migrate [--json]` with exact authority, output,
  backup/scratch, idempotency, atomicity, and no-deletion behavior.
- Keep status free of DuckDB imports/connections and keep all management paths
  provider/model/network inert.

## Acceptance criteria

1. Every envelope shape/value/graph and privacy requirement in the storage spec
   has direct positive and adversarial decoder coverage.
2. Existing v1 stores and envelopes remain accepted with byte/semantic
   equivalence and unchanged v1 view results.
3. Fresh initialization creates exact schema v2; deterministic v2 live,
   preview, and pre-pipeline-error fixtures persist atomically to exact v2
   views.
4. Status/flush cover absent, exact v1, upgrade-required with/without v2
   backlog, exact v2, incompatible, unsafe, busy, and mixed-version queues.
5. Migration covers absent/already-current/success/busy/blocked, v1 backlog,
   preexisting exact/mismatching backup, idempotent retry, and every specified
   crash point without changing an unproven canonical store.
6. Exact-byte privacy scans cover envelope, both queues, receipts, state,
   output, scratch, backup diagnostics, and database values.
7. Audit hooks prove zero socket/DNS/provider/model/catalog/retrieval calls.
8. Focused telemetry suites, existing v1 writer/store/queue suites, full tests,
   compilation, lock, distribution, clean-wheel management lifecycle, and diff
   hygiene pass on the ticket's required runtimes.

## Evidence expectations

Record exact commands, runtime/host identities, focused and full results,
schema/view identities, migration before/after counts, crash-injection matrix,
privacy sentinel result, no-network result, changed paths, and residual risks
in a new evidence record related to this ticket.

## Explicit exclusions

No changes to `cli.py` retrieve behavior, retriever trace nesting, routing,
ranking, evidence, provider calls, live credentials/namespaces, real
`~/.buoy`, automatic migration, backup deletion, release, installed tool,
`main`, or package publication.

## Assumption provenance

- Explicit migration, retained backup, all retrieve modes, and separate
  command/pipeline latency are user-ratified in the 2026-08-20 workstream.
- The exact v1 security/durability behavior is record-backed by
  `.10x/specs/local-telemetry-writer.md` and its evidence/reviews.
- No external service behavior is assumed or required.

## Blockers

None.

## Progress and notes

- 2026-08-20: Opened after user ratification and source/record inspection.
  Implementation intentionally deferred to a later turn under the governing
  spec-first execution gate.
