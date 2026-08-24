Status: superseded
Created: 2026-08-24
Updated: 2026-08-24

# One-Time Local Telemetry V2 Canary

## Context

Retrieve command telemetry v2 is integrated on exact
`develop@d3ae1ba272c9ce8999332dd04058116e8a5dda0f`, tree
`38174e3d8167bbe4a7bd1afd3e1f16402ad8b7bc`. Hosted exact-final-commit CI
passed on that commit, but the user-global `buoy` remains the previously
installed `main@796f7384e2c86f6fb9e10f9099dbec589f8e47e6` build and reports
`0.6.2.dev2+g796f7384e`.

The two branches diverge at the v0.6.1 release boundary. The exact integrated
candidate reports a lower-looking Hatch-VCS development version, and every
prior global-tool replacement authority is consumed. Replacing the global tool
would therefore add unnecessary identity, rollback, and user-environment risk
to a canary whose purpose is only to observe telemetry v2 on the owner's real
local workload.

A documented read-only status inspection of the real telemetry home reported a
compatible schema-v1 store with 12 persisted runs, 3,682,304 bytes, an empty
queue, 12 receipts, disabled collection, and no write or durability failure.
The user then explicitly authorized the bounded canary and separately confirmed
its literal approved workload cases. The exact workload authority is bound by
case IDs rather than copied query or namespace values so the canary records do
not duplicate those values.

## Decision

Authorize one forward-only local canary under
`.10x/tickets/2026-08-24-run-local-telemetry-v2-canary.md` with these exact
bounds:

1. Build and install the exact integrated commit only in an owner-private
   temporary environment. Verify its commit, tree, artifact digest, installed
   entry point, dependencies, source identities, and expected dynamic version
   before real-home access. Do not replace, modify, or uninstall the global
   `buoy-search` tool.
2. Reinspect the real telemetry status immediately before mutation. Require the
   ratified schema-v1, 12-run, empty-queue snapshot and no active writer or
   migration process. Any drift stops without migration or provider access.
3. Invoke the exact public `buoy telemetry migrate --json` contract once through
   the verified candidate. The migration must retain the byte-identical
   immutable v1 backup required by the active specification, preserve the 12
   v1 rows/views, and prove a compatible schema-v2 store. A nonzero, uncertain,
   or drifted result stops; this authority grants no repair, force, backup
   replacement, backup deletion, or migration retry.
4. Run exactly four observations from the owner-approved
   `automatic-multi-corpus-retrieval-v1` dataset at SHA-256
   `29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`:
   the preview and explicit-single forms of case `u01-dagster-purpose`, then the
   explicit-multi and automatic forms of case
   `m01-dagster-turbopuffer-quality`. Each form runs at most once. The explicit
   values are those the user confirmed in the current workstream and those
   exact case records; no substitution is permitted.
5. Permit at most six content-namespace query calls in total across the live
   observations, plus the automatic route's established bounded catalog reads.
   Permit exact local embedding/reranking inference only from already available
   pinned model assets under enforced offline model settings. No model download,
   provider write, catalog mutation, content mutation, credential operation,
   or retry is authorized.
6. Load the repository's intended credential source only inside each command
   subshell so an inherited key cannot silently override it. Never print, copy,
   log, or persist any credential value or private credential metadata.
7. Enable telemetry only for the four canary commands, flush the accepted
   envelopes through the candidate, and inspect only sanitized v1/v2 counts,
   modes, outcomes, durations, fanout, and failure categories. Raw retrieval
   output may exist only in owner-private temporary files long enough to check
   exit status and shape; remove it before closure.
8. Verify that query text, argument vectors, namespace values, credentials,
   content, raw errors, stack traces, and private paths are absent from every
   new telemetry artifact. Records may contain only approved case IDs and
   content-free aggregate observations.
9. Remove the temporary executable environment and raw command artifacts after
   observation. Retain the immutable v1 database backup indefinitely as the
   required migration result. Leave the global tool, repository source, `main`,
   tags, Releases, workflows, installed models, and unrelated local or hosted
   state unchanged.

Beginning the migration consumes this one-time forward authority. The four
workload authorities are consumed individually when their corresponding
commands begin. Failure or uncertainty does not grant a retry. Provider access
cannot begin unless migration and its immediate readback pass.

## Supersession and consumed authority

The one migration and all four workload forms began under this authority, so
all forward authority granted here is consumed. Both independent reviews
ultimately found that retained telemetry proves five logical namespace spans
but not the physical provider-call count: one span may
contain a second request through the compatibility fallback. Because temporary
output/runtime artifacts were deleted as required and no independent call
receipt was retained, the at-most-six-call criterion is unsupported and the
canary ticket is blocked.

This decision is superseded by consumption, with no successor execution
authority. It remains historical provenance only. It grants no retry,
replacement canary, migration, flush, provider/model access, repair, or other
external operation. Any further operation requires separately shaped and
ratified authority.

## Alternatives considered

### Replace the global tool

Rejected. It would present an apparent version downgrade, require a new exact
rollback bundle and installation authority, and expose the normal command to a
candidate needed only for one bounded observation.

### Use only a temporary home

Rejected for this canary. Isolated migration and telemetry behavior already
passed extensive deterministic validation; the remaining question is whether
the exact integrated build behaves correctly with the owner's existing local
v1 store and normal read-only retrieval workload.

### Release before observing

Rejected. Release and `main` promotion are separate scopes, and the repository's
prior release automation was intentionally removed. Neither is needed for this
local observation.

## Consequences

The real telemetry database will advance from schema v1 to schema v2 if every
precondition passes. Its immutable v1 backup remains as durable local history.
The canary may incur the bounded read cost of up to six content-namespace
queries and bounded catalog reads, but cannot mutate provider state. The global
command remains unchanged, so normal use continues to report its prior version
after the temporary candidate is removed.

The canary establishes only this host, this store snapshot, these four approved
forms, and the observed provider/model conditions. It does not authorize a
release, recurring canary, global installation, broader workload collection,
provider repair, routing-card repair, retention change, or deletion.
