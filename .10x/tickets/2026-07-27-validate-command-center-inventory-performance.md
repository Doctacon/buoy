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

## Blockers

Dependencies only.

## Exclusions

Live crawls/clones, BigQuery/Snowflake, turbopuffer, remote refresh/search, approved apply, source/namespace mutation, push/merge/PR/publish/release, and permanent benchmark/browser artifacts.

## References

- `.10x/specs/command-center-summary-inventory-performance.md`
- `.10x/specs/command-center-managed-plan-cache-invalidation.md`
- `.10x/specs/command-center-blocking-route-threading.md`
- `.10x/specs/command-center-packaging-documentation-ci.md`
- `.10x/tickets/done/2026-07-27-baseline-command-center-inventory-performance.md`
