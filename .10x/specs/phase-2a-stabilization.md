Status: active
Created: 2026-07-24
Updated: 2026-07-24

# Phase 2A Stabilization

## Purpose and scope

Harden the existing Phase 2A managed planning surface without expanding its authority. The read-only Command Center remains available when the platform cannot safely host durable managed jobs; newly appended progress is bounded; source language matches the actual credential-free HTTP(S) contract; shutdown remains non-cancellable; and the React Router advisory is resolved from official scope and actual router use.

This specification supplements `.10x/specs/phase-2a-plan-job-lifecycle.md`, `.10x/specs/phase-2a-plan-job-api-security.md`, `.10x/specs/phase-2a-plan-job-interface.md`, and `.10x/specs/phase-2a-public-source-planning-service.md`.

## Unsupported-platform fallback

A dedicated managed-planning unsupported exception MUST represent only absence of required filesystem primitives (`O_NOFOLLOW`, `O_DIRECTORY`, descriptor-relative operations, and descriptor enumeration). It MUST remain distinguishable from integrity/tamper failures, malformed records, service ownership conflicts, permission or durability failures, and artifact failures.

When and only when that dedicated exception is raised during managed-job service startup:

- the FastAPI application MUST start with the worker absent;
- no job/artifact managed directory, source access, provider, client, or model load may occur;
- Dashboard, local inventory, saved plan review, applied-state inspection, explicit remote refresh, and explicit search MUST remain available;
- capabilities MUST report managed public planning unavailable with the sanitized reason `platform_unsupported` and durable plan-job history unavailable;
- every plan-job collection/detail/events route, including creation, MUST return HTTP 503 with code `managed_planning_unavailable` and the safe managed-planning-unavailable message;
- the frontend MUST show read-only availability, render no usable submission form or managed history request, and MUST NOT fetch a CSRF token or attempt creation;
- startup MUST emit one sanitized warning.

All other startup failures remain fail-closed.

## Durable event bound

`MAX_DURABLE_EVENTS_PER_JOB` is 5,000. Existing schema-v1 records and event logs remain readable even when already above this count; no existing history is rewritten, truncated, compacted, or deleted because of the new bound.

For a running job, ordinary progress may be appended only while the current sequence is below `MAX_DURABLE_EVENTS_PER_JOB - 2`. At the threshold, the store persists exactly one intermediate event with the safe message `Additional progress updates are being coalesced while planning continues.` Subsequent nonterminal callbacks cause no durable record/event mutation, timestamp/sequence change, or observer notification. Exactly one final slot remains for `succeeded`, `failed`, or `interrupted`; persisted sequences remain contiguous and total events do not exceed 5,000.

## Source terminology and network boundary

Managed website planning accepts a **credential-free HTTP(S) website**. Managed GitHub planning accepts a **public GitHub repository root**. Website syntax validation is not a public-routability or SSRF policy.

> Managed website planning validates HTTP(S) syntax and accepts no source credentials, but it is not a public-routability or SSRF firewall. The Command Center must remain loopback-only and under the control of the local operator.

Existing Host, Origin, CSRF, credential, URL-userinfo, and source-form restrictions remain unchanged.

## Shutdown

Phase 2A remains non-cancellable. Graceful server shutdown MUST wait for an active in-process planning job. When shutdown begins with an active future, the server MUST log one sanitized message containing only the safe job ID/state and the fact that cancellation is unsupported. No source URL, exception, credential, or absolute path may be logged. Genuine process interruption retains the existing restart-to-`interrupted` rule.

## React Router advisory guard

GHSA-qwww-vcr4-c8h2 MUST be assessed against official advisory scope, installed dependency versions, and actual frontend imports/mode. If the vulnerable action/RSC path is unreachable in Buoy's declarative Vite SPA, no dependency churn is required; record evidence, close the ticket, and add a narrow guard against framework mode, React Server Components, server actions, or unstable RSC entrypoints. Reevaluate if those modes are adopted or official scope changes. If reachable, use a compatible patched dependency and validate tests/build/assets.

## Exclusions

No Phase 2B behavior: no browser apply/approval, deletion, cancellation, retry endpoint, pause/resume, source definitions, database UI planning, credentials, private GitHub, catalog/namespace mutation, graph behavior, authentication, new queue/database/daemon, or network-routability policy.

## Acceptance criteria

Automated tests prove the dedicated fallback and fail-closed distinctions; inert unsupported startup and structured 503s; frontend unavailable states with no CSRF/POST; event coalescing/terminal retention/legacy compatibility/SSE reconnect; accurate terminology; router-mode guard and advisory evidence; safe active-shutdown log; supported-platform regression behavior; package/static synchronization; and the repository validation basket.
