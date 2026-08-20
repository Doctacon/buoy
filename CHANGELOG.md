# Changelog

Notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semantic Versioning](https://semver.org/). Release packages are published
as GitHub Release assets rather than to PyPI.

## Unreleased

## [0.6.0] - 2026-08-20

### Added

- Added opt-in, local-only retrieval tracing with OpenTelemetry and a private
  DuckDB history at `~/.buoy/telemetry/telemetry.duckdb`. Sanitized traces now
  cross a private durable inbox into one bounded-idle Buoy writer, avoiding
  per-command DuckDB startup and concurrent-writer loss. `buoy telemetry
  status` and `buoy telemetry flush` expose content-free local health and
  bounded draining. The schema still records allowlisted operational metadata
  only; it does not record queries, content, source identifiers, paths,
  credentials, or raw errors, and it does not configure a Collector or remote
  export.
- Added schema-v3/delta-v2 plans with deterministic bounded source-derived
  routing passages, exact `plan.json` plus `delta.duckdb` output, remote catalog
  schema v3 support, and retained-plan `catalog repair-apply` inspection plus
  absence/revision-bound repair.
- Added the preview-first, reader-first `catalog migrate-routing-v3` operator.

- Added the staged activation contract for bounded prototype routing. Routing
  cards may carry up to eight reviewed example questions, and the router can
  rerank an exact local top-twelve card shortlist with the pinned MiniLM model
  without extra provider searches. The clean dormant checkpoint retains the
  packaged collect artifact and legacy selector; only an independently audited
  exact 65-case result can authorize the artifact-only active checkpoint that
  is the intended final state of this Unreleased package. An active task tree
  remains separate from integration, publication, and deployment.
- Packaged the exact owner-approved RentPTR, Salesforce, and WhiteboxGeo route-
  canary packs as reproducible evaluation ground truth. Source, wheel, source-
  distribution, and clean-install checks bind their raw hashes and reconstructed
  suite identity, while ordinary routing never reads their question text.
- Added preview-first `catalog migrate-routing-v2` and
  `catalog set-routing-examples` operators. The schema migration is bound to
  the exact catalog snapshot and vector-inclusive projection; each reviewed
  example update is bound to one exact card revision and one deterministic
  row. Both operations report bounded request accounting and leave content and
  production routing untouched.
- Restored the fixed `buoy-routing-catalog-v1` card lifecycle and bounded
  `catalog list/show/upsert/enable/disable` commands. Mutations preview by
  default and require explicit approval.
- Added namespace-free retrieval that selects one confident corpus or searches
  at most three ambiguous corpora concurrently, then deduplicates and locally
  reranks multi-corpus results with an exact pinned MiniLM model.
- Added an automatic-only post-retrieval relevance gate. Automatic text and
  JSON retrieval use the best final pinned-MiniLM score and a provisional
  packaged cutoff of `-8.0`; weak results widen once, then return either no
  relevant evidence or an inconclusive result when a namespace failed. There
  is no command-line, environment, or runtime threshold override.
- Added `buoy retrieve --explain` for the established detailed live text
  diagnostics. It is presentation-only and cannot be combined with `--json`.

### Changed

- Implicit Buoy-owned local storage is now user-global instead of
  current-directory-relative: applied state lives under `~/.buoy/state/`, and
  default crawl/plan artifacts live under
  `~/.buoy/artifacts/site-crawls/`. An `apply` without `--plan` proceeds only
  when exactly one supported pending plan exists there. Existing project-local
  `.buoy`, `.turbo-search`, and `artifacts/site-crawls` paths remain available
  through explicit options but are not implicitly discovered, migrated,
  backfilled, or deleted; explicitly selected plans retain their normal
  verified success-only cleanup lifecycle. Default plans now use a distinct `-plan` directory
  leaf for every source kind, including database relations. Package-manager
  and model caches remain outside this Buoy home. The active routing receipt
  keeps the exact CLI module bytes pinned, so its legacy default-path option
  descriptions remain temporarily stale pending a separate routing
  recertification; the runtime behavior and documentation use the new paths.
- Remote catalog reads now normalize empty routing-prototype float arrays at
  the same float32 boundary as base vectors, accepting harmless provider
  decimal round trips while retaining stale adjacent-bucket rejection.
- Schema-v3 registration now requires an existing exact-v3 remote catalog.
  First and ordinary apply never provision or migrate it; when the prerequisite
  is absent or catalog state cannot be safely read after content/state commit,
  apply reports nonzero partial success, performs no catalog schema/card write,
  and retains the plan. Its read-only `repair-apply --inspect-current` recovery
  establishes a safe card binding before any approved repair.
- Generic `catalog upsert` can no longer set or clear system-owned routing
  passages and preserves an existing passage bank. Approved apply,
  retained-plan repair, and separately governed migration/backfill remain the
  passage-mutation authorities.
- Local plan compatibility is a forward-only schema-v3/delta-v2 cutover;
  schema-v1/v2 plans remain preserved but inert. Plan cleanup now occurs only
  after content, state, and catalog registration all succeed.
- Valid certified-catalog drift now routes provisionally across the best three
  compatible cards, while exact title/alias anchors retain singleton authority.

- Ordinary apply registration now preserves operator-reviewed routing examples
  on both manual and generated cards while continuing to refresh verified
  source, retrieval, plan, and apply-lineage fields.
- `--namespace` is now a repeatable deterministic retrieval override; one
  explicit namespace retains the v0.5.1 result contract.
- Successful approved applies register their routing card after content and
  local state commit, with truthful partial-success reporting if catalog
  registration fails.
- Automatic text, JSON, and governed evaluation now apply the relevance gate.
  Explicit `--namespace` retrieval remains an unchanged deterministic bypass.
  The `-8.0` cutoff is a raw model score rather than a probability; it was
  approved as a provisional starting point from the observed 50-question run
  and remains subject to monitoring against a broader reviewed sample.
- Live `buoy retrieve` text now defaults to compact citation-first passages
  with whitespace-collapsed excerpts capped at 320 characters. Routing,
  ranking, per-corpus coverage promotion, evidence behavior, JSON, and provider
  calls are unchanged; partial-failure and `assessment_failed` warnings remain
  visible.

### Security

- Schema-v3 routing cards persist bounded, verbatim-derived source excerpts.
  Buoy redacts passages and vectors from normal output, but credentials allowed
  to query raw catalog provider rows can read the excerpts; catalog read access
  must be scoped as source-content access.

## [0.5.1] - 2026-08-13

### Added

- Added a versioned GitHub-wheel installation path and a compact first GitHub
  repository `plan -> dry-run apply -> approved apply -> retrieve` walkthrough.

### Security

- Confined GitHub repository content acquisition to tracked regular files.
  Link, submodule, and special entries are skipped even when explicitly
  included, and regular/oversize-card reads are bounded before indexing.

## [0.5.0] - 2026-08-01

The existing v0.5.0 history uses a lightweight tag and a GitHub Release with no
downloadable package assets.

### Changed

- Refocused Buoy on one source to one reviewed Turbopuffer namespace while
  retaining website, repository, document, DuckDB, BigQuery, and Snowflake
  relation ingestion.
- `retrieve` and `evals` now require one explicit singular `--namespace`;
  ambient `TURBOPUFFER_NAMESPACE` is no longer target authority.
- Successful approved apply emits `receipt_schema_version=1` as the supported
  Kite integration event and no longer reads or writes a routing catalog.
- Moved account-wide namespace discovery, routing, multi-namespace fusion,
  evidence snapshots, experimental baselines, and the Command Center out of
  the Buoy package and into the Kite product boundary.
- Removed Command Center frontend/package dependencies and assets.
- Paused further GitHub publication after v0.5.0 while retaining tag-derived
  Hatch-VCS development versions and read-only release readiness checks.

### Migration

- Existing content namespaces, compact schema-v2 plans, local DuckDB applied
  state, routing/evidence namespaces, and incomplete evidence resources are
  left untouched. See `docs/kite-split.md`.

## [0.4.0] - 2026-07-21

### Added

- Retrieval results now return the automatic tags already stored on indexed chunks.
- GitHub repository planning supports explicit `fixed-80-python-breadcrumbs` and `python-ast` experiment arms with exact line citations, deterministic fallback, and fail-closed 512-token source subdivision.

### Changed

- Plain interactive apply now shows complete local preflight and prompts `Apply this plan? [y/N]`; `--dry-run` is explicit prompt-free preflight, `--approve` remains prompt-free automation, and plain non-interactive apply is rejected before plan work.
- Plain automatic and explicit retrieval now execute live; `--dry-run`/`--plan` request preview, while `--live` remains an accepted compatibility no-op that conflicts with preview flags.
- Retrieval without CLI `--namespace` defaults to authenticated live-namespace discovery intersected with fixed remote `buoy-routing-catalog-v1`; repeatable CLI `--namespace` is the sole bypass, `TURBOPUFFER_NAMESPACE` is ignored, and `--auto-route` remains a compatibility no-op.
- Catalog lifecycle, approved-apply registration, and recovery now use conditional remote cards with explicit permissions, stable reads, preview-first removal, safe rebase, and operator-approved exact-revision acceptance.
- Local catalog path options and `BUOY_CATALOG_PATH` were removed. `catalog migrate-local` imports a validated legacy schema-v1 file without modifying it; the bound local cutover catalog is deleted only after post-integration verification.
- Applied-state authority is DuckDB-only; obsolete JSON state is ignored without migration or deletion.

### Fixed

- Website crawling stays on the exact requested hostname and bounds sitemap/robots reads, redirects, gzip expansion, and malformed compressed responses before parsing.
- MarkItDown ingestion again removes C0 and C1 control characters while preserving tabs, line feeds, and carriage returns.

### Removed

- The deprecated package-owned `turbo-search` console entry point. Replace only the executable name with `buoy`; command arguments and behavior are unchanged, and Buoy does not delete user-created shell aliases, copied launchers, wrappers, or caches.
- Buoy 0.4.0 removes the `TURBO_SEARCH_EMBEDDING_MODEL` and `TURBO_SEARCH_EMBEDDING_PRECISION` fallbacks. Rename them to `BUOY_EMBEDDING_MODEL` and `BUOY_EMBEDDING_PRECISION`; actual commands reject either old name with exit 2, empty stdout, and a value-redacted stderr mapping before any state, data, credential, model, artifact, DuckDB, or remote effect. Help/version remain available.


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

[0.6.0]: https://github.com/Doctacon/buoy/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/Doctacon/buoy/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/Doctacon/buoy/releases/tag/v0.5.0
[0.4.0]: https://github.com/Doctacon/buoy/releases/tag/v0.4.0
[0.3.0]: https://github.com/Doctacon/buoy/releases/tag/v0.3.0
[0.2.1]: https://github.com/Doctacon/buoy/releases/tag/v0.2.1
