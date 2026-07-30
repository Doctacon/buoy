Status: superseded
Created: 2026-07-28
Updated: 2026-07-28

# Command Center Coalesced Plan Review

## Purpose and scope

Reduce selected-plan request multiplication while preserving complete per-request schema-v2 verification, identity binding, tamper/replacement protections, and read-only authority. This narrows `.10x/specs/compact-delta-plan-artifacts.md`, `.10x/specs/command-center-local-inventory.md`, `.10x/specs/command-center-local-api-and-server.md`, and `.10x/specs/command-center-operator-interface.md` without changing their artifact or authority contracts.

## Combined service and API

`LocalInventoryService` MUST expose one combined review operation accepting plan ID plus independently bounded changed-chunk and stale-row windows. It MUST:

1. validate offsets, limits, and preview characters with current rules;
2. resolve the selected summary record once;
3. perform pre-verification plan-directory, `plan.json`, and `delta.duckdb` identity checks once;
4. invoke the existing complete verifier exactly once with `materialize=False`, both requested windows, and no cache;
5. reconstruct verified detail and both bounded windows from that verifier result;
6. perform post-verification identity/replacement checks once; and
7. preserve complete schema, logical hash, source authority, row identity, embedding hash, plan identity, artifact hash, baseline, privacy, descriptor/no-follow, and A→B→A protections.

Add synchronous `GET /api/v1/plans/{plan_id}/review` with defaults: chunk offset 0, chunk limit 10, preview 2,000 characters, stale offset 0, stale limit 10. Existing maximums apply: bounded offsets, limits no greater than 100, and current preview maximum. The response contains verified detail, chunks, and stale rows. The route MUST be synchronous so Starlette runs it in its bounded worker pool.

Existing detail, chunks, and stale-row routes remain additive compatibility/focused-pagination operations and each MUST continue one complete verification per request. No verification result, token, rows, or apply authority may persist between requests.

## Frontend behavior

Initial `/plans/:planId` load MUST issue exactly one combined-review request and retain its three response sections. Chunk pagination MUST request only the chunks route and replace only chunk state; stale pagination MUST request only the stale route and replace only stale state. Detail and unaffected data remain visible with section-level loading/errors. Retry SHOULD repeat only the failed section where possible.

Plan-ID changes reset offsets/state and invalidate prior requests. Slower earlier combined, chunk, or stale responses MUST NOT replace newer plan/window state, using aborts, sequences, or an equivalent deterministic mechanism. No heavy frontend data library is introduced.

## Acceptance criteria

- Instrumented tests prove one verifier call for combined service/API review and one each for standalone detail/chunks/stale.
- Combined output detail and windows derive from the same verification.
- Replacement before/during verification, A→B→A, corrupt deltas, and invalid windows fail safely.
- Tests prove no provider, source adapter, model, or credential loading.
- Frontend tests prove exact initial and pagination request shapes, isolated loading/errors, preserved unaffected sections, race safety, plan-ID reset, and absence of mutation controls.
- Benchmark evidence records verifier counts before/after (initial 3→1, chunk pagination 3→1, stale pagination 3→1), wall time, peak RSS where practical, worker-thread behavior, complete-verification duration, and materialized response counts for about 100 changed and 100,000 stale rows.

## Operational truth

Every response containing delta-derived data performs a new complete linear verification. The optimization coalesces three initial windows into one verification and narrows later browser pagination to one endpoint; it does not make review constant-time or universally subsecond. Large selected deltas may take several seconds for each payload request.

## Exclusions

No persistent or process-local verification cache, verified-plan token, verifier bypass, cached delta rows, schema change, apply/approval/deletion/catalog authority, cancellation/retry workflow, remote persistence, graph/taxonomy/ontology work, provider call, or turbopuffer write.
