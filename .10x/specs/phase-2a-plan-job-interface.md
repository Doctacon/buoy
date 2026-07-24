Status: active
Created: 2026-07-23
Updated: 2026-07-24

# Phase 2A Plan-Job Operator Interface

## Purpose and scope

Add one managed public-source plan workflow to the existing local command center while retaining all Phase 1 read-only review/search/remote behavior.

## Routes

- `/plans/new`: a `Start plan` form for a required credential-free HTTP(S) website or public GitHub repository-root URL and optional max pages/files, max chunks, namespace, and low-risk include/exclude paths when cleanly supported. It states: `This creates a local reviewed plan only. It does not embed content, call turbopuffer, or modify a namespace.` It obtains and submits the server-issued CSRF token, reports validation/409 errors, and navigates to the new job.
- `/plan-jobs`: recent bounded job history with job ID, safe source, source type, state, created time, current stage, plan ID, and progress/review links.
- `/plan-jobs/:jobId`: state, source, namespace, durable progress timeline/counts, sanitized error, and plan-review link after success. It consumes persisted-plus-live SSE with polling fallback and reconnect sequence. Failed/interrupted jobs may link to `/plans/new` as `Start a new plan`; they never replay automatically.

Navigation adds `Start plan` and `Plan jobs`. Existing plan detail displays originating job ID when the managed job record can establish it. When capabilities report managed planning unavailable, managed routes show an explanatory read-only fallback without rendering the form, fetching history/CSRF, opening SSE, or attempting submission; saved plans and all Phase 1 routes remain available.

## UX and safety

Use existing layout, badges, accessible forms/status regions/tables, escaped text, loading/empty/error states, and responsive CSS. No cancellation, plan-job execution/replay (`Retry plan job`, replay, resume), apply, approval, delete, catalog, source-management, or namespace-management button/link is present. The shared `Retry` action MAY remain on read-error states because it only repeats an idempotent GET to reload the current view; it MUST NOT submit, execute, resume, or replay a plan job. Credential-free HTTP(S)/public-GitHub classification and server validation remain authoritative; client validation is advisory and includes the API's 16 KiB UTF-8 serialized JSON request limit before CSRF retrieval.

## Acceptance criteria

Vitest/RTL covers website and GitHub submission, CSRF token use, field validation, active conflict, timeline/history, SSE success, polling/error fallback, success review link, failed/interrupted new-plan link, escaped progress/errors, durable originating-job metadata on plan review, navigation, and route-wide absence of prohibited controls. Managed-route read-error and terminal variants prove that any shared GET reload remains distinct from, and exposes no control for, plan-job execution/replay.

## Exclusions

No saved source definitions, local files, database sources, credentials, private repositories, cancellation/retry/resume, apply, deletion, catalog/namespace management, graph functionality, WebSockets, or browser secret storage.
