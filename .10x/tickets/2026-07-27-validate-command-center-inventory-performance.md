Status: open
Created: 2026-07-27
Updated: 2026-07-27
Parent: .10x/tickets/2026-07-27-command-center-inventory-performance-plan.md
Depends-On: .10x/tickets/done/2026-07-27-integrate-managed-plan-cache-invalidation.md, .10x/tickets/done/2026-07-27-move-blocking-command-center-routes-off-event-loop.md

# Validate Command Center Inventory Performance

## Scope

Integrate and validate the complete workstream: rerun the exact baseline fixture, update `docs/command-center.md` accurately, run required Python/frontend/package/install/import validation, inspect generated-asset synchronization, record before/after evidence, and obtain independent adversarial review.

## Acceptance criteria

- Exact pre-change fixture/method is rerun after implementation; cold and at least five warm medians are recorded separately for summary and selected full-verification routes with host/version/count/RSS context.
- Observational result reaches warm Dashboard/Plans/Namespaces below 250 ms or at least 5× baseline improvement, or a concrete evidence-backed blocker prevents closure.
- Docs state traversal boundaries, aggregate state summaries, bounded process cache/TTL/external visibility, managed invalidation, non-authorizing/nonpersistent cache, and continued complete selected verification without claiming universal constant/subsecond behavior.
- Run and record: `git diff --check`; `uv sync --locked`; `uv lock --check`; ranking and C6 validators; full Python discovery; UI-extra sync and focused basket; frontend `npm ci`, tests, and build; static synchronization; `uv build`; wheel/sdist inventory; installed-wheel health/local summaries; ordinary core import isolation; final core-environment restoration/lock check.
- Wheel contains synchronized frontend assets; sdist includes intended frontend source; no `node_modules` or benchmark/private artifacts are committed.
- Independent review checks safety/integrity, performance proof, test strength, docs claims, and scope. Findings are repaired or durably accepted before closure.
- Evidence names any defect, deviation, and residual selected-plan linear cost honestly.

## Evidence expectations

Create `.10x/evidence/2026-07-27-command-center-inventory-performance.md` and an independent review record. Include base/branch/final commits, files, exact commands/results, timing tables, RSS, limits, and no-external-side-effect attestation.

## Progress and notes

- 2026-07-27: Opened; dependencies not yet executed.
- 2026-07-27: Final integration validation completed without closing the ticket. The exact clean-commit default benchmark recorded warm summary p50 of 0.018–0.141 ms versus baseline 671.639–688.501 ms (Dashboard/Plans/Namespaces improved 4,844.9×/38,250.1×/6,532.5×); selected complete verification remained intentionally linear at 2,899.825–2,937.950 ms warm p50. Structural tracing recorded one plan/state scan, five state connections, no applied-row objects or legacy descendant traversal, and zero delta opens.
- 2026-07-27: Updated `docs/command-center.md` with traversal, aggregate summary, 1.0-second process-local cache/invalidation/external visibility, non-authority/nonpersistence, forced miss refresh, and continued complete selected-verification boundaries. The first full-suite run exposed a pre-existing latest-main package/public-surface defect: `images/buoy.svg` had been removed while active package/CI/tests still required it. Restored only a byte-identical copy of the packaged SVG; the complete rerun passed 791 tests with 35 skips.
- 2026-07-27: Ranking/C6, locked core/UI sync, 169 focused applied-state/local/API/jobs/planning/release tests, 37 frontend tests/build/static synchronization, 69-entry wheel/159-entry sdist inventory with zero `node_modules`, installed-wheel health/dashboard/plans/namespaces/static smoke, final core restoration/import isolation, lock/diff/staged/generated-artifact checks all passed. Safari WebDriver was present but could not create a real session because the operator-level remote-automation setting is disabled; it was not changed. Aggregate evidence: `.10x/evidence/2026-07-27-command-center-inventory-performance.md`. Independent final review and closure remain parent-owned.
- 2026-07-27: Repaired final integration commit `4cb793bf` after two independent reviews without moving this ticket. Applied-state summaries now explicitly require no-follow, directory-descriptor, and `dir_fd` support and translate unavailable/`NotImplementedError` primitives into isolated `AppliedStateError` items; service and real API regressions prove dashboard/namespaces/plans remain HTTP-available. Cache expiry now uses captured rebuild-start monotonic time; a deterministic exact-TTL rebuild test proves an external plan appearing after the scan is immediately discovered on the next call. The benchmark tracer now mirrors/restores `os.supports_dir_fd` while wrapping `os.open`.
- 2026-07-27: Repair validation passed 87 focused tests, the rerun full 795-test suite with 36 core skips, exact benchmark thresholds/structure, ranking/C6, frontend 37 tests/build/static hashes, 69-entry wheel/159-entry sdist inventory, installed-wheel five-route smoke, Safari readiness/platform-setting probe, core import isolation, and final 876-path artifact inventory. The first full repair run exposed only the bounded benchmark-tracer capability-advertisement mismatch and passed after repair. Evidence now contains exact replayable commands and exact results for every final artifact gate and correctly treats hardcoded benchmark zero operations as procedure-attested inventory rather than counters. Independent rereview and closure remain parent-owned.
- 2026-07-27: Applied the remaining final-review repairs without moving this ticket: forced direct misses no longer reuse a concurrently rebuilt snapshot after its rebuild-start expiry; initial summary-descriptor `fstat` failure closes the descriptor; and the one observed frontend test race now waits for `FakeEventSource` construction. Deterministic regressions passed, including the exact concurrent slow-rebuild/external-plan/direct-miss schedule with three total scans and one forced retry. Final validation passed 89 focused core tests, 797-test full core and UI-enabled runs, 175 focused UI-Python tests, ranking/C6, the exact benchmark and structural contract, 20 repeated frontend full runs plus 30 focused and 10 further full runs, two builds/static synchronization, 69/159 package inventory, installed-wheel five-route smoke, core import isolation, and lock/diff checks. Generated targets were removed using an explicit walk that excluded only `.git` and `.venv`; all enumerated targets and tracked overlap were empty across 876 tracked paths. Aggregate evidence appends exact results, harness deviations, and the bounded inventory claim. Independent rereview and closure remain parent-owned.

## Blockers

None. Independent review and closure are intentionally parent-owned.

## Exclusions

Live crawls/clones, BigQuery/Snowflake, turbopuffer, remote refresh/search, approved apply, source/namespace mutation, push/merge/PR/publish/release, and permanent benchmark/browser artifacts.

## References

- `.10x/specs/command-center-summary-inventory-performance.md`
- `.10x/specs/command-center-managed-plan-cache-invalidation.md`
- `.10x/specs/command-center-blocking-route-threading.md`
- `.10x/specs/command-center-packaging-documentation-ci.md`
- `.10x/tickets/done/2026-07-27-baseline-command-center-inventory-performance.md`
