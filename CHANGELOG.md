# Changelog

Notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

## [Unreleased]

## 0.2.1 (pending GitHub release)

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

- The `turbo-search` command and `TURBO_SEARCH_*` configuration aliases remain available during 0.2 and are scheduled for removal in 0.3.

## 0.2.0 (not released)

- The annotated `v0.2.0` tag was preserved without a GitHub Release after its hosted validation failed before artifact construction or publication.
