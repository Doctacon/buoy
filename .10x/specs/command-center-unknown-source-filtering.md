Status: superseded
Created: 2026-07-29
Updated: 2026-07-29

# Command Center Unknown-Source Filtering

## Purpose and scope

Make the existing `unknown` namespace source-kind filter include source-less local namespace summaries, especially malformed applied-state/error summaries, without fabricating provenance or changing other source-kind mappings.

## Behavior

- Namespace filtering MUST derive effective source kind as `summary.source.kind` when source exists and `unknown` otherwise.
- `source_kind=unknown` MUST include source-less namespaces.
- A namespace attributable from malformed applied state MAY have `local_status=error` and `source=None`; it MUST remain visible under `source_kind=unknown` and under the combined `local_status=error&source_kind=unknown` filter.
- Website, GitHub repository, document, and database filters MUST continue to exclude source-less summaries.
- No synthetic provenance object is created. Presentation MAY continue to say `Unknown source`.

## Acceptance criteria

Service and API tests prove malformed-state attribution, source-less error status, unknown and combined filtering, and exclusion from every other source kind. Frontend tests prove the unknown filter requests the matching API contract and renders the source-less row as `Unknown source`.

## Exclusions

No source definition, provenance synthesis, identity change, applied-state schema change, remote refresh, provider access, or mutation.
