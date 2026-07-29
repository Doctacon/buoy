Status: active
Created: 2026-07-29
Updated: 2026-07-29

# Command Center Artifact-Error Diagnostics

## Purpose and scope

Bound isolated local artifact-error transport on ordinary Command Center inventory screens while preserving complete, deterministic, read-only discovery through a dedicated paginated diagnostics surface. This narrows `.10x/specs/command-center-local-inventory.md`, `.10x/specs/command-center-local-api-and-server.md`, `.10x/specs/command-center-operator-interface.md`, and `.10x/specs/command-center-bounded-inventory-transport.md` without changing artifact authority, sanitization, summary caching, or verification.

## Service and API contract

- Dashboard, PlanInventory, and NamespaceInventory MUST retain their existing error arrays but include no more than 20 errors in the snapshot's existing stable order.
- Dashboard `artifact_error_count` remains the total global isolated-error count and `artifact_errors_truncated` MUST equal `artifact_error_count > len(artifact_errors)`.
- PlanInventory and NamespaceInventory MUST add `error_total` and `errors_truncated`; `error_total` is the total global isolated-error count and `errors_truncated` MUST equal `error_total > len(errors)`.
- `GET /api/v1/artifact-errors` MUST return `items`, filtered `total`, `offset`, and `limit` from the existing cached local summary snapshot. Defaults are offset 0 and limit 50; limit MUST be between 1 and 100 under current bounded-offset rules.
- Optional `q` MUST be at most 256 characters and apply case-insensitive substring matching across error code, sanitized message, and safe artifact ID before pagination.
- Ordering MUST remain deterministic and use the snapshot's existing stable error order. Existing sanitization MUST remain unchanged.
- Invalid bounds or query values MUST use the normal structured error response and preserve the established validation codes (including `invalid_offset` and `invalid_limit`) rather than collapsing every validation failure into one code.
- This surface MUST NOT perform delta verification, source access, provider/model/credential loading, mutation, repair, or deletion.

## Frontend contract

- `/artifact-errors` MUST request and render only the current 50-item page and expose search, Previous, Next, current range, code, sanitized message, and safe artifact ID. Changing `q` resets offset to zero; stale responses MUST NOT replace newer results.
- Dashboard, Plans, and Namespaces MUST link to diagnostics whenever their total error count is positive.
- Ordinary screens MAY render their embedded sample but MUST render no more than 20 errors. Truncated samples MUST state the shown and total counts.
- No show-all or mutation control exists.

## Acceptance criteria

Synthetic 10,000-error service/API tests prove bounded ordinary responses, exact totals/truncation, deterministic samples, filters-before-pagination, invalid-input handling, and inertness. Frontend tests prove bounded ordinary rendering, one current diagnostics page, exact page requests, query reset, stale-response protection, and read-only presentation.

## Exclusions

No artifact/schema redesign, persistent index/cache, verification authority, provider/source/model work, repair/deletion controls, graph extraction, or turbopuffer operation.
