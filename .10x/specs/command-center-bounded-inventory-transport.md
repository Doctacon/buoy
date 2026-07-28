Status: active
Created: 2026-07-28
Updated: 2026-07-28

# Command Center Bounded Inventory Transport

## Purpose and scope

Keep Plans, local Namespaces, and namespace plan history bounded across API and browser transport without changing schema-v2 artifacts, summary-cache semantics, product authority, or explicit remote-refresh boundaries. This narrows `.10x/specs/command-center-local-inventory.md`, `.10x/specs/command-center-local-api-and-server.md`, `.10x/specs/command-center-operator-interface.md`, and `.10x/specs/command-center-summary-inventory-performance.md`.

## Plans inventory

`GET /api/v1/plans` MUST retain bounded `offset`/`limit` pagination and add optional filters applied to the cached summary snapshot before pagination:

- `q`: case-insensitive substring over plan ID, namespace, safe source title, or safe source URI; maximum 256 characters;
- `namespace`: exact namespace ID validated by the current namespace contract;
- `source_kind`: one of `website`, `github_repo`, `document`, `database`, or `unknown`, derived from current source metadata.

`total` MUST be the filtered pre-pagination count. Ordering MUST remain deterministic newest-first. Invalid filters MUST use the structured `invalid_request` response. Filter changes MUST NOT rebuild the summary snapshot solely because the filter changed.

The `/plans` UI MUST request and render only one current page, default limit 50. It MUST expose search, namespace, source-kind, Previous/Next, and a current range. Filters and offset SHOULD use URL search parameters; filter changes reset offset to zero. Browser back/forward SHOULD restore them. No helper or hidden loop may fetch all pages. Stale responses MUST NOT replace newer results.

## Namespaces inventory

`GET /api/v1/namespaces` MUST retain bounded `offset`/`limit` and add filters applied before pagination:

- `q`: case-insensitive namespace substring, maximum 256 characters;
- `source_kind`: the same high-level values and mapping as Plans;
- `local_status`: `planned`, `applied`, `pending_changes`, `conflict`, or `error`.

`total` MUST be filtered pre-pagination count and ordering MUST remain deterministic. Invalid filters use `invalid_request`.

The `/namespaces` UI MUST request and render only one local page, default limit 50, with local search/source/status controls, Previous/Next, and range. Each current local row MAY be enriched from the explicitly refreshed bounded remote snapshot. A remote entry with `local_present=true` MUST NOT become a remote-only row merely because its local record is outside the current page. After explicit refresh, only entries with `local_present=false` appear in a separately labeled `Remote namespaces without a local snapshot` section, paginated client-side independently with page size 50. Remote/catalog filters, if retained, MUST be scoped and labeled for that section; they MUST NOT imply global filtering of the server-paginated local inventory. Remote refresh/search remain explicit.

## Namespace plan history

Namespace detail MUST accept `plan_offset` and `plan_limit`, defaulting to 0 and 20, with limit 1 through 100 and current bounded-offset rules. After deterministic matching-plan ordering, the response MUST include only the selected plan window plus `plan_total`, `plan_offset`, `plan_limit`, and `plans_truncated`. The UI MUST link to `/plans?namespace=<namespace>` whenever truncated and MUST NOT receive an unbounded history.

## Acceptance criteria

- Service/API tests with at least 1,000 fixture plans prove filters-before-pagination, filtered totals, ordering, bounds, invalid requests, namespace-history defaults/max/offset/truncation, summary-cache reuse, and provider/model/source-adapter inertness.
- Frontend tests prove one initial local request per screen, one request per page transition, offset reset on filters, current-page rendering only, race safety, accurate local/remote enrichment, independent local/remote-only pages, no all-pages loop, and the truncated-history link.
- Inventory evidence records before/after requests, records, approximate JSON bytes, and rendered row count.

## Exclusions

No new summary cache, unbounded show-all, automatic remote refresh/search, persistent index, schema migration/change, mutation control, source definition, provider call, graph extraction, or turbopuffer operation.
