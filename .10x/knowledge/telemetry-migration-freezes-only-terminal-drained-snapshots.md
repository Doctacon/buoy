Status: active
Created: 2026-08-29
Updated: 2026-08-29

# Telemetry Migration Freezes Only Terminally Drained Snapshots

Before freezing a telemetry store as a migration source, processing a compatible queue item is insufficient. The migration must prove the fixed drain snapshot reached terminal queue state:

- no receipt publication or acknowledgement failure;
- a bounded safe and complete queue rescan;
- no remaining claim from the snapshot; and
- every committed item either acknowledged by a validated receipt or recoverable for exact replay.

A store commit can succeed while receipt publication or claim acknowledgement fails. Freezing/migrating immediately afterward can publish a new schema while recoverable old-version work remains claimed, making status and retry semantics false.

This rule is distinct from retry after a final migration backup was already published. In that branch, the backup fixes the exact source history; migration must complete canonical publication from that proven source before draining work published later.

Immutable backups of earlier schema history are exact validated subsets of later append-only history unless the governing migration explicitly freezes a complete final source. Equality against all later history would reject valid post-migration appends.
