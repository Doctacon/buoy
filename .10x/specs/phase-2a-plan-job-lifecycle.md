Status: active
Created: 2026-07-23
Updated: 2026-07-23

# Phase 2A Durable Plan-Job Lifecycle

## Purpose and scope

Define the local audit record, state machine, single-worker execution, restart behavior, event stream, and failure semantics for ephemeral public-source plan requests.

## State machine

States are exactly `queued`, `running`, `succeeded`, `failed`, and `interrupted`. Allowed transitions are `queued → running`, `queued → failed`, `running → succeeded`, `running → failed`, and `running → interrupted`. Terminal states are immutable. Invalid transitions fail closed. Retry always creates a new job ID; there is no cancellation, pause, resume, or automatic retry.

Only one command-center job may be active (`queued` or `running`). A second start is rejected without starting or queuing work and identifies the active job. This rule does not affect the CLI. Execution uses one in-process worker/executor with concurrency one; no external queue or daemon.

## Durability and restart

Store atomically written safe records and append-only JSONL events under `<state-root>/command-center/jobs/`, keyed by an unguessable safe job ID. On service startup, persisted `queued` or `running` jobs transition to `interrupted`, preserving artifacts/events; nothing resumes or retries automatically.

A record contains schema version, job ID, operation, `local-operator`, state, source kind/URL, namespace when known, root-relative artifact path, plan ID only after verified success, timestamps, latest progress, safe error code/message, and sanitized request summary. It MUST NOT contain secrets, headers, cookies, CSRF tokens, IP addresses, environment values, raw exceptions, or avoidable absolute paths.

## Progress and SSE

Events contain monotonically increasing `sequence`, timestamp, bounded stage, bounded escaped message, and optional safe counts. Stages cover queued, validation, source acquisition/discovery/crawl/clone/processing, chunk/artifact/diff/write phases, and terminal outcomes by mapping existing callbacks into sanitized events.

SSE replays persisted events after the requested sequence/`Last-Event-ID`, then streams new events without starting work, emits stable event IDs, and closes after terminal state. Polling job detail is a supported fallback. Event-log appends are durable and never expose raw provider/source output.

## Failure semantics

Failure preserves the job record/events and incomplete managed directory when safe, records a sanitized code/message, produces no plan ID unless complete normal artifacts passed integrity verification, and performs no applied-state, turbopuffer, namespace, or catalog mutation.

## Acceptance criteria

Tests cover every allowed transition, invalid transition rejection, success/failure/interruption, restart recovery, one-active conflict, new-ID retry, atomic records, durable replay/reconnect/live completion/terminal closure, sanitization, and no duplicate execution.
