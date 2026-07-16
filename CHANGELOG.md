# Changelog

Notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.0] - 2026-07-16

### Added

- Opt-in float16 corpus and query embedding inference on supported accelerators, with precision bound into plans and outputs while float32 remains the default.
- Read-only `buoy namespaces` discovery with deterministic identifier filtering.
- Explicit repeatable `--namespace` retrieval that embeds once, queries namespaces sequentially, and merges namespace-qualified results with deterministic reciprocal-rank fusion instead of using a demo fallback.
- A canonical local namespace-card catalog with atomic persistence, manual lifecycle commands, validated retrieval contracts, and persisted normalized routing vectors.
- Explicit `buoy retrieve --auto-route` selection with eligibility-first filtering, deterministic lexical and semantic ranking, hybrid reciprocal-rank fusion, a default top-three route, and local-only dry previews.
- Approved-apply catalog registration with precomputed pending state, namespace locking, reconciliation, and explicitly approved abandonment for unconfirmed recovery state.

### Changed

- Planning performs one extraction/chunk pass and reports stage timings without loading embeddings or contacting Turbopuffer.
- Approved apply overlaps coordinator-thread embedding with one ordered background upsert at bounded depth one while preserving failure and commit ordering.
- Plan/apply preflight and success output expose decision-complete source, region, model, precision, and stale-row intent plus shell-safe preview/live retrieval commands.
- Routed live retrieval now hands selected cards to the existing multi-namespace retriever and downstream cross-namespace fusion while explicit `--namespace` retrieval remains authoritative and unchanged.
- Apply preserves manual card semantics and every existing enabled state while refreshing verified source, model, precision, schema, ranking, and apply-lineage fields.
- New local state continues to default to `.buoy`; legacy `.turbo-search` state-root fallback remains explicit and non-migrating.

### Fixed

- Apply reports catalog-commit and cleanup partial success truthfully and revalidates recovery artifacts before deletion.
- Generated source metadata supports verified GitHub, website, local-file, and opaque `pdf://` document identities without treating opaque IDs as filenames.

### Deprecated

- The `turbo-search` command and `TURBO_SEARCH_*` configuration aliases remain available through 0.3 and are scheduled for removal in 0.4.

## [0.2.1] - 2026-07-14

### Added

- GitHub-only CI and approval-gated release automation with artifact provenance.
- Website, public GitHub repository, and local-document indexing through a reviewable plan/apply workflow.
- Incremental DuckDB state, apply progress/timing, hybrid retrieval, and retrieval evaluation.

### Changed

- Renamed the project to Buoy, the distribution to `buoy-search`, the Python package to `buoy_search`, and the primary command to `buoy`.
- Adopted Apache-2.0 licensing and a details-on-demand documentation structure.

### Fixed

- Validate annotated release tags from authoritative GitHub remote metadata rather than checkout's dereferenced local ref.

### Deprecated

- The `turbo-search` command and `TURBO_SEARCH_*` configuration aliases remain available during 0.2 with deprecation warnings.

## 0.2.0 (not released)

- The annotated `v0.2.0` tag was preserved without a GitHub Release after its hosted validation failed before artifact construction or publication.

[Unreleased]: https://github.com/Doctacon/buoy-search/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/Doctacon/buoy-search/releases/tag/v0.3.0
[0.2.1]: https://github.com/Doctacon/buoy-search/releases/tag/v0.2.1
