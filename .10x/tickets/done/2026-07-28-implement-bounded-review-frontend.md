Status: done
Created: 2026-07-28
Updated: 2026-07-28
Parent: .10x/tickets/done/2026-07-28-command-center-bounded-review-performance-plan.md
Depends-On: .10x/tickets/done/2026-07-28-implement-bounded-review-backend.md

# Implement Bounded Review Frontend

## Scope

Implement the React/API-client portions of `.10x/specs/command-center-bounded-inventory-transport.md` and `.10x/specs/command-center-coalesced-plan-review.md` against the completed backend contracts.

## Acceptance criteria

- Plans and Namespaces initially request/render only one 50-row page; page/filter actions issue exactly one request, filters reset offset, URL parameters preserve practical navigation, and stale responses cannot overwrite newer results.
- No normal-screen helper loops over all local pages and no unbounded show-all action exists.
- Current local namespace rows receive matching explicit-remote enrichment; only `local_present=false` entries appear in a separate independently paginated remote-only section. Labels accurately scope filters.
- Namespace detail consumes bounded history and links to `/plans?namespace=...` when truncated.
- Plan review initial load issues only combined review. Chunk/stale pagination invokes only its focused endpoint, preserves detail/unaffected section, exposes section-level loading/errors/retry where practical, ignores stale races, and resets on plan ID.
- Tests prove exact request behavior, rendered bounds, independent pagination, errors/races, no mutation controls, and no 1,000-row DOM behavior.
- Packaged static assets are rebuilt and synchronized after tests/build.

## Evidence expectations

Focused Vitest/RTL request-count and race tests plus build/static synchronization results.

## Explicit exclusions

Heavy frontend data libraries, automatic remote work, global misleading remote filter, mutation controls, graph work, schema/API redesign, and unrelated UI refactors.

## Progress and notes

- 2026-07-28: Opened after ratification; depends on backend contract.
- 2026-07-28: Resumed the prior worker's extensive partial edits after its transport-level `fetch failed`; inspected and preserved sound bounded inventory, remote-only, combined-review, focused-pagination, and static-asset work. Initial validation exposed 2 failing RTL tests, 1 unhandled stale namespace-detail fixture, and a widened TypeScript test fixture. Repaired those incomplete edges rather than reverting the partial implementation.
- 2026-07-28: Completed URL-backed 50-row Plans/Namespaces with exact request and stale-race behavior; accurate current-local enrichment and independently paginated/scoped remote-only rows; bounded namespace history and filtered-plan link; one combined initial review; isolated focused chunk/stale loading, error, retry, race, and plan-ID reset behavior. Expanded RTL to exact request arrays, reverse-order inventory/section races, 1,000-record rendered bounds, remote-only independence, history truncation, initial/focused retries, plan reset, and no mutation controls.
- 2026-07-28: Final `npm test -- --run` passed 44 tests; `npm run build` passed and synchronized packaged `index-CTBZ4tnQ.js` plus `index-0ugYq-Qa.css` while removing both legacy assets. Four focused API/release/static tests passed. Static-reference/orphan checks, temporary-version/bytecode/build-output hygiene, no-staged-file check, and `git diff --check` passed. Evidence is recorded at `.10x/evidence/2026-07-28-implement-bounded-review-frontend.md`. `web/node_modules` remains intentionally available for immediate independent review. No docs, full package/suite, benchmark, commit, or closure work was performed.
- 2026-07-28: Repaired only frontend rereview findings: incremental Plans/Namespaces text filters now replace their current history entry while select and pagination transitions still push; explicit RTL back/forward coverage proves text coalescing and restoration across meaningful select/page entries. Inventory pagination now exposes named navigation landmarks, including distinct local/remote-only context, and the mutation-control regression rejects prohibited action terms within longer accessible labels. All 45 frontend tests, TypeScript/Vite build, and the focused packaged-static route test passed. Rebuilt packaged assets now reference `index-DAM_87xf.js` and retained `index-0ugYq-Qa.css`. Reviewer artifacts and temporary validation files were removed; `web/node_modules` remained only for required rereview.
- 2026-07-28: Independent rereview passed navigation, bounded requests, remote-only presentation, plan-review isolation/races, accessibility/security, and byte-for-byte static synchronization at `.10x/reviews/2026-07-28-command-center-bounded-review-frontend-review.md`. This child is closed and integrated validation is unblocked.

## Blockers

None.
