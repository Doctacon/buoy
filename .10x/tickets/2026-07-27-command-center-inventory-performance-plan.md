Status: open
Created: 2026-07-27
Updated: 2026-07-27
Parent: None
Depends-On: None

# Command Center Local-Inventory Performance Plan

## Aggregate scope

Deliver the user-ratified bounded Command Center navigation-performance work from latest hosted `main` commit `01f2d19432c4bc77e9d6bd7ab8a657b5f4583521` on `work/command-center-inventory-performance` without changing schema-v2 compact-delta architecture, state schema, product authority, or selected-plan full verification.

## Child sequence and dependencies

1. `.10x/tickets/done/2026-07-27-baseline-command-center-inventory-performance.md` freezes the repeatable pre-change fixture/method/results from the untouched `main` source.
2. `.10x/tickets/done/2026-07-27-implement-summary-inventory-performance.md` implements plan-boundary pruning, aggregate applied-state summaries, and the locked 1.0-second cache after baseline evidence exists.
3. In parallel after child 2:
   - `.10x/tickets/2026-07-27-integrate-managed-plan-cache-invalidation.md` wires successful managed publication invalidation.
   - `.10x/tickets/2026-07-27-move-blocking-command-center-routes-off-event-loop.md` converts compatible blocking handlers and proves responsiveness.
4. `.10x/tickets/2026-07-27-validate-command-center-inventory-performance.md` reruns the exact benchmark, updates docs, performs complete Python/frontend/package validation, records before/after evidence, obtains independent review, and closes the graph when coherent.

One child writer operates in the task worktree at a time. Children 3 and 4 may be investigated/reviewed in parallel but MUST NOT write concurrently in the same worktree.

## Aggregate acceptance criteria

- Every directory containing `plan.json` is an inventory traversal boundary; current plan handling and sibling discovery preserve existing policy and safety.
- Applied-state inventory uses one read-only connection and aggregate SQL per database without `load_applied_state`, ordered full-row queries, or row-object materialization.
- One service-local locked 1.0-second summary cache prevents repeated/stampeded scans, refreshes on expiry/invalidation, and direct misses force one retry.
- Verified successful managed publication invalidates immediately without coupling jobs to FastAPI or turning callback failure into job failure.
- Compatible blocking API routes run through Starlette's sync-route thread pool; bounded body and SSE behavior remain intact and responsive.
- Selected plan detail/chunk/stale access retains complete exact verification and bounded page materialization on every call.
- Structural tests and exact before/after measurements separate summary latency from selected-plan verification and show material host-observed improvement.
- Documentation, full Python, focused UI-extra Python, frontend, generated assets, distribution inventory, installed-wheel smoke, import isolation, lock restoration, and diff checks pass.
- No prohibited provider/source/apply/remote mutation, push, merge, PR, publish, or release occurs.

## Progress and notes

- 2026-07-27: User supplied and ratified the complete performance, safety, measurement, documentation, validation, and non-goal contract. Fished active/terminal records and inspected latest hosted `main` source across local inventory, applied state, API routes, managed jobs, prior compact-delta performance evidence, and active specifications. Created three focused active specifications and this bounded execution graph. No benchmark or implementation started in that shaping turn.
- 2026-07-27: Baseline child completed after initial review-driven harness repair and passing rereview. The repeatable full fixture records warm summary p50 671.639–688.501 ms and selected full-verification p50 3,323.781–3,374.436 ms, with repeated scans, 303,093 row objects, legacy descendant traversal, and zero delta opens. Summary-core implementation is unblocked.

## Blockers

None after the execution gate turn boundary. Child 1 is the first executable unit.

## Exclusions

All user-stated non-goals, especially schema redesign/migration/deletion, persistent or external cache/index infrastructure, selected-verification bypass, new authority, graph/taxonomy work, source/provider operations, apply, remote mutation, push/merge/PR/release.

## References

- `.10x/specs/command-center-summary-inventory-performance.md`
- `.10x/specs/command-center-managed-plan-cache-invalidation.md`
- `.10x/specs/command-center-blocking-route-threading.md`
- `.10x/specs/command-center-local-inventory.md`
- `.10x/specs/command-center-local-api-and-server.md`
- `.10x/specs/compact-delta-plan-artifacts.md`
- `.10x/specs/compact-duckdb-applied-state.md`
- `.10x/specs/phase-2a-plan-job-lifecycle.md`
- `.10x/specs/phase-2a-public-source-planning-service.md`
