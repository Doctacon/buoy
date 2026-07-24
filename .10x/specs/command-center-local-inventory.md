Status: active
Created: 2026-07-23
Updated: 2026-07-23

# Command Center Local Inventory and Artifact Review

## Purpose and scope

Buoy MUST provide a web-framework-independent, read-only application-service layer that discovers saved plans, local applied state, source provenance, retrieval settings, and safe artifact previews. This specification governs local inventory only; remote provider activity and search are governed separately.

## Behavior

- Services MUST call current Python domain functions rather than shelling out to `buoy`.
- Plan discovery MUST recursively find `plan.json` beneath a configured artifacts root, avoid following symlinks outside that root, deduplicate by stable plan ID, and sort deterministically with valid newest timestamps first.
- A malformed plan MUST produce an item-level artifact error and MUST NOT break other inventory.
- Namespace summaries MUST combine all available plans and applied state without reducing the product model to a namespace ID.
- Unknown counts MUST be represented as unknown, never invented.
- Supported provenance MUST cover website, public GitHub repository, local document, DuckDB relation, BigQuery relation, and Snowflake relation plans using actual persisted fields.
- Path-private absolute local/database paths and provider connection details MUST NOT be exposed.
- Browser-addressable previews MUST use plan IDs and bounded indexes/pagination, never arbitrary paths.
- Markdown and chunks MUST be returned as bounded plain text.
- Local inventory MUST NOT import source adapters, load embedding models, inspect credentials, contact providers, crawl, clone, query databases, apply, delete, or mutate catalogs.

## Acceptance criteria

1. Typed models represent plan summaries/details, namespace summaries/details, dashboard aggregates, previews, warnings, and safe errors.
2. Tests prove discovery, deduplication, deterministic latest selection, malformed isolation, aggregation, source mapping for every supported source kind, private-path redaction, symlink/traversal rejection, preview bounds, and pagination bounds.
3. Tests prove local inventory does not import BigQuery/Snowflake adapters or make remote calls.
4. Existing plan/state terminology and parsers are reused where compatible.

## Constraints and exclusions

No source reconnection, plan/apply mutation, arbitrary file access, or fabricated counts. Existing active specifications and decisions remain authoritative for plan, state, source, retrieval, and catalog semantics.
