Status: done
Created: 2026-08-28
Updated: 2026-08-28
Parent: .10x/tickets/done/2026-08-28-retrieval-telemetry-v3-plan.md
Depends-On: .10x/tickets/done/2026-08-28-implement-retrieve-inference-observation-v3.md

# Integrate Provider Accounting into Telemetry V3

## Scope

Extend the completed v3 producer/envelope with ordinary effective-command activation and persistence-ready normalization of the existing validated private provider invocation receipt.

This child owns:

- entering one receipt scope only for effective v3 retrieve telemetry;
- sealing after command provider work is terminal;
- mapping validated receipt schema 1 to exact v3 `provider_accounting`;
- complete-versus-unavailable authority;
- canonical producer/writer-side structural validation; and
- provider-free fake coverage for every content/catalog boundary and failure mode.

## Acceptance criteria

- Enabled v3 retrieve commands activate exactly one private scope before any governed automatic catalog/content call; disabled/non-retrieve/direct-v1 paths do not.
- Complete receipts preserve exact content/catalog unit, route-rank attempts, categories, order, counts, bounds, and outcomes.
- Missing/incomplete/invalid/observer-failed receipt records unavailable, never zero.
- Provider SDK arguments/order/call count, pagination, compatibility fallback, routing, result/exception identity, output, and existing private canary receipt remain unchanged.
- Producer and decoder reject impossible source order, count mismatches, overflow, unknown fields, booleans-as-integers, and prohibited data.
- No per-attempt timestamp is invented.
- Privacy sentinels are absent from canonical v3 bytes.
- Focused tests pass on Python 3.11 and 3.13 using local fakes only.

## Evidence expectations

Record focused test commands, exact fake call matrices, canonical round trips, disabled/no-op checks, privacy byte scans, and changed files. No live provider call is authorized by this child.

## Explicit exclusions

DuckDB/queue/writer migration, SDK transport retries, wire/billing claims, provider identifiers/payloads, provider writes, live validation, public receipt API, v1/v2 changes, release, and unrelated cleanup.

## References

- `.10x/specs/retrieve-provider-invocation-telemetry-v3.md`
- `.10x/specs/provider-client-invocation-accounting.md`
- `.10x/specs/provider-client-invocation-receipt.md`
- `.10x/evidence/2026-08-28-retrieval-telemetry-v3-authorization.md`

## Progress and notes

- 2026-08-28: Opened after ratification; waits for the v3 base envelope child.
- 2026-08-28: Activated as the second dependency in the integrated v3 milestone after the repaired sequential provider-free baseline passed on Python 3.13 and 3.11.
- 2026-08-28: Implemented internal effective-v3 receipt-scope activation, post-terminal canonical handoff, complete/unavailable mapping, independent content/catalog/source-order validation, and command/provider agreement. Production command publication remains exact v2; the provider tuple now reaches only the dormant downstream persistence seam.
- 2026-08-28: Added provider-free command lifecycle, complete zero, server/client fallback, minimum catalog, upper-bound, malformed/noncanonical, disabled/v2/v1, nested canary, exception identity, command-family agreement, and privacy tests. Updated the prior source audit only for the newly ratified producer/envelope seam.
- 2026-08-28: Final provider-free validation passed: Python 3.13 focused `479 passed, 546 subtests passed`; isolated Python 3.11 changed-path `264 passed, 252 subtests passed`; full Python 3.13 and isolated Python 3.11 each `1300 passed, 1383 subtests passed` with only 57 pre-existing lxml deprecation warnings. Compileall, `git diff --check`, and empty staged diff passed. Candidate evidence: `.10x/evidence/2026-08-28-retrieve-provider-invocation-telemetry-v3.md`.
- 2026-08-28: No provider/network/model call, provider write, real telemetry-store access, stage/commit/push, or release occurred. Ticket remains active for independent acceptance review.
- 2026-08-28: Applied the parent-accepted P1/P2 review fixes without widening activation: complete provider accounting now reconciles after the command operation/span graph validates, requiring exact content route/final-fanout agreement, zero content without a pipeline, bounded per-route terminal consistency, and actual automatic catalog-span reach. Added explicit-single/multi/automatic contradictions, failed-before/in-catalog cases, partial/post-provider-error preservation, and a callback-driven privacy fake that proves query/response/raw-error/cursor/header/credential/ambient sentinels never reach canonical v3 bytes.
- 2026-08-28: Post-fix focused suites passed identically on Python 3.13 and isolated Python 3.11 (`266 passed, 263 subtests passed` each). Full suites passed on Python 3.13 and isolated Python 3.11 (`1302 passed, 1394 subtests passed` each) with only 57 pre-existing lxml deprecation warnings. No provider/network/model, real-store, downstream queue/store, staging, commit, or release action occurred.
- 2026-08-28: Final independent review confirmed exact lifecycle, structural validation, command/route/catalog reconciliation, callback-driven privacy coverage, v1/v2 compatibility, and downstream activation boundary; no P0/P1/P2 issue remained. Parent reran `git diff --check` and the reconciled v3 provider/inference/receipt matrix: `39 passed, 62 subtests passed`. Review: `.10x/reviews/2026-08-28-retrieve-provider-invocation-telemetry-v3-review.md`.
- 2026-08-28: Closure reconciliation mapped every criterion to recorded evidence. Retrospective found no new reusable lesson beyond the already extracted atomic telemetry-version activation rule at `.10x/knowledge/telemetry-version-activation-is-atomic-with-queue-consumer.md`; no additional follow-up was opened.

## Blockers

None.
