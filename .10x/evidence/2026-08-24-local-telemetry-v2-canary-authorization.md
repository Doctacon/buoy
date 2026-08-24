Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/decisions/superseded/one-time-local-telemetry-v2-canary.md, .10x/tickets/done/2026-08-24-run-local-telemetry-v2-canary.md

# Local Telemetry V2 Canary Authorization

## What was observed

Before any canary mutation, the parent session performed documented read-only
inspection and observed:

- repository `develop`, `origin/develop`, and remote `develop` at
  `d3ae1ba272c9ce8999332dd04058116e8a5dda0f`;
- integrated tree `38174e3d8167bbe4a7bd1afd3e1f16402ad8b7bc`;
- a clean integration worktree;
- user-global executable managed by uv, reporting
  `buoy 0.6.2.dev2+g796f7384e` on Python 3.13.0;
- real telemetry status `disabled` and schema version 1;
- one compatible 3,682,304-byte store snapshot with 12 persisted runs;
- an empty queue, 12 receipts, and zero reported conflicts, publication
  failures, write failures, replays, rejections, or durability degradation;
- an intended repository credential source and a process credential were
  present; no value was printed or persisted; and
- the owner-approved automatic multi-corpus dataset has SHA-256
  `29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`.

The initial process-name probe matched only its own shell command text and is
not evidence of an active writer. The executable ticket requires a precise
fresh process and status preflight before migration.

## User authorization

The user first selected a local canary, then asked for a plain explanation.
After being told that the canary would use a temporary exact-develop build,
leave the global tool unchanged, access and potentially migrate the real
telemetry store, perform normal provider-backed retrievals, and inspect only
content-free timing aggregates, the user explicitly said `go ahead`.

The parent then disclosed the exact schema-v1/12-run store snapshot and the
bounded effects: one exact temporary build, explicit backed migration, four
approved observation modes, at most six content-namespace reads plus catalog
reads, no provider writes, aggregate-only reporting, temporary-environment
removal, and no global-tool change. The user explicitly confirmed that exact
canary.

Finally, the parent made the literal workload user-legible and bound it to:

- preview and explicit-single forms of approved case
  `u01-dagster-purpose`; and
- explicit-multi and automatic forms of approved case
  `m01-dagster-turbopuffer-quality`.

The user explicitly confirmed those exact requests. This evidence intentionally
does not duplicate query text, argument vectors, or namespace values; the
confirmed values remain bound to the immutable approved dataset and case IDs.

## What this supports

This supports the historical semantic and side-effect authority recorded in
`.10x/decisions/superseded/one-time-local-telemetry-v2-canary.md` and removes the ticket's
scope, migration, workload, provider-read, model, credential-source, reporting,
and cleanup ambiguities.

## Limits

This authorization is one-time and forward-only. It does not prove the canary
will pass and does not authorize retries, repairs, global tool replacement,
release or `main` work, provider writes, broader queries, model downloads,
credential changes, catalog/card repair, backup deletion, telemetry retention
changes, or unrelated state mutation.
