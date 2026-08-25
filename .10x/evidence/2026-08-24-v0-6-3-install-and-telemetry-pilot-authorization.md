Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/2026-08-24-install-v0-6-3-and-run-telemetry-pilot.md, .10x/decisions/one-time-v0-6-3-global-install-and-telemetry-pilot.md

# V0.6.3 Install and Telemetry Pilot Authorization

## Owner direction

After merging the canary records to `develop`, merging `develop` to `main`, and
publishing GitHub Release `v0.6.3`, the owner asked whether the project could
start collecting testing data. The parent verified exact branches, tag,
release, tree continuity, CI, and the still-old global installation.

The owner then explicitly directed: install the new Buoy, run a few
production-style commands to collect telemetry data, and return with findings.
The parent proposed one exact bounded campaign after installation:

- one live explicit-single retrieval;
- one live explicit-multi retrieval; and
- one live automatic retrieval;

using the previously approved `u01-dagster-purpose` and
`m01-dagster-turbopuffer-quality` cases, with at most six logical namespace
operations, no retry, no provider write, one final flush, and sanitized
findings. The owner selected **3-run pilot (Recommended)**.

## Authorized effects

This authorizes, once:

1. replacement of only the uv-managed user-global `buoy-search` tool with a
   locally built and verified artifact from exact lightweight tag `v0.6.3`;
2. pre/post read-only inspection of package, Git, telemetry, model-cache, and
   process state needed for safe execution and evidence;
3. exactly the three live read-only retrieval commands listed above, each begun
   at most once, using the approved case values privately at runtime;
4. at most six logical namespace operations in total plus the automatic route's
   established bounded catalog reads;
5. local cached embedding/reranking inference under enforced offline model
   settings;
6. local telemetry-v2 envelope/database writes for those commands, one bounded
   final flush, terminal-writer wait, sanitized read-only analysis, and retained
   content-free test observations in the real local telemetry store; and
7. owner-private temporary build, validation, command-output, and rollback
   artifacts removed after accepted installation and evidence capture.

The intended repository credential source may be loaded only within each
retrieval subshell after removing any inherited provider key. No credential
value or private credential metadata may be printed, copied, or persisted.

## Limits

No installation retry, retrieval retry, query/case substitution, provider or
catalog write, namespace/content mutation, model download, credential change,
telemetry migration/purge, backup deletion, release/tag/ref/GitHub mutation,
other-tool change, or unrelated cleanup is authorized. Physical transport
attempt count remains outside this pilot's logical-operation budget and must not
be inferred from logical spans.

A known-good old-tool rollback may run at most once only if the replacement
returns a known terminal result and immediate exact-candidate acceptance fails
while the rollback artifact remains verified. Successful candidate acceptance
expires rollback authority. Retrieval failure stops later retrievals, still
permits the single bounded telemetry flush/readback, and does not by itself
roll back an otherwise accepted installation.
