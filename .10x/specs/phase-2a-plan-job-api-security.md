Status: active
Created: 2026-07-23
Updated: 2026-07-23

# Phase 2A Plan-Job API and Security

## Purpose and scope

Expose the durable public-source job service through the loopback Command Center without granting apply, deletion, catalog, namespace, credential, local-file, or database authority.

## API

Versioned resources MUST provide CSRF token issuance, create/list/detail plan jobs, and SSE events. Creation uses a bounded JSON body and returns the durable job identity. A concurrent active job returns HTTP 409 with a safe error and active job ID. Unknown jobs return structured 404 errors. Lists and event replay are bounded.

Plan-job lists MUST order records by record filesystem `mtime_ns` descending, tie-broken by `job_id` descending. `created_at` MUST remain displayed audit data and MUST NOT determine list order. API and store list offsets MUST be between 0 and 1,000 inclusive. Listing MUST count matching records without decoding every record, retain at most `offset + limit` metadata candidates, decode and reconcile only the selected window, and fail closed unless candidate metadata and selected decode both prove a no-follow, permission-private, regular, single-link file with the selected device/inode identity.

## Request authority and protection

A loopback process may start a local public website/GitHub planning job. Creation MUST retain Host validation, require same-origin semantics, reject conflicting/cross-origin `Origin`, require JSON, reject oversized bodies before parsing, validate bounded HTTP(S) URLs, and require a server-issued CSRF token tied to the local server process. The token is never persisted or logged. Existing guarded read-only POST protections remain.

The browser obtains the token from the local API and submits it in a non-simple header. No permissive CORS. Non-HTTP(S), userinfo-bearing, overlength, local-document, database, and unsupported source forms fail before worker submission. Website crawl containment remains unchanged.

## Startup and operation

Startup loads local job records and marks active persisted jobs interrupted but performs no crawl, clone, retry, remote call, model load, or source-adapter import. The SSE endpoint only observes one existing job. Provider/source exceptions are logged safely and returned as bounded structured errors without raw exception representations.

## Acceptance criteria

FastAPI tests cover token issuance; valid same-origin creation; missing/invalid token; cross-origin, hostile Host, wrong content type, oversized body, invalid schemes/source types; 409 conflict; list/detail/404/pagination, including the 1,000 offset cap and deterministic metadata order; historical replay, Last-Event-ID, live completion, terminal closure; startup interruption; and no mutation endpoints beyond bounded job creation. Store tests cover many-record bounded decoding/reconciliation and record-metadata/selected-identity tamper rejection.

## Exclusions

No authentication/RBAC, remote hosting, uploads, filesystem paths, database configuration, credentials, cancellation, retry endpoint, apply, delete, catalog mutation, or namespace mutation.
