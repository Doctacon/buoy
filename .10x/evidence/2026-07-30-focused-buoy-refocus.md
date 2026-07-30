Status: recorded
Created: 2026-07-30
Updated: 2026-07-30
Relates-To: .10x/tickets/done/2026-07-30-refocus-buoy-for-kite-split.md, .10x/specs/focused-buoy-boundary.md

# Focused Buoy Refocus

## Branch and history boundary

The refocus was implemented on `work/refocus-buoy` from fetched
`origin/develop` commit `7d359f344348289fef75e8a53c9bfc258c5d9c17`.
History and existing tags were preserved. A historical audit found `d9ca6db` as
the last commit whose product surface matched Buoy's original narrow purpose,
but that tree predates later database source adapters. The implementation
therefore removes the expanded surfaces in one forward commit instead of
resetting or rewriting history.

The immutable final commit is the draft pull request head containing this
record. The draft pull request records its exact SHA; a commit cannot include
its own final SHA without changing it.

## Observed product boundary

The resulting public CLI exposes exactly `crawl`, `plan`, `apply`, `retrieve`,
and `evals`.

Retained:

- website, repository, local file, PDF, DuckDB, BigQuery, and Snowflake
  relation inputs;
- source planning, compact plan artifacts, approved apply, local DuckDB applied
  state, retrieval ranking, evaluation, and the bundled tokenizer;
- exact applied-state schema validation, load/save, locking, and apply-run
  summaries;
- dynamic Hatch VCS package versioning.

Removed:

- remote routing catalogs, automatic namespace discovery, multi-namespace
  retrieval, and semantic-routing experiments;
- remote evidence snapshot commands and storage;
- Command Center APIs, jobs, static assets, local servers, and the separate web
  application;
- the experimental baseline executor and its representative routing fixture;
- orphaned cross-source applied-state summary and row-stream APIs.

Retrieval and evaluation require one explicit content namespace. Repeated or
empty namespace values, the former routing-catalog namespace, and
`buoy-evidence-*` namespaces fail closed. `TURBOPUFFER_NAMESPACE` is not a
fallback. Plan and apply enforce the same reserved-namespace boundary,
including apply-time manifest fallback. A successful approved JSON apply emits
a schema-v1 receipt with source identity, apply identity, content-apply proof,
vector dimensions, and state-commit proof for Kite to consume later.

Release publication is paused while the split settles. Release validation
keeps dynamic Hatch VCS as the version authority, requires read-only workflow
permissions, rejects upload/publish behavior, validates exact distribution
inventory, and exercises a clean installed wheel.

## Validation

All validation was local and provider-free:

- Python 3.13 unittest discovery: 462 tests passed in 45.825 seconds.
- Python 3.11 unittest discovery: 462 tests passed in 74.357 seconds.
- focused applied-state suite: 18 tests passed.
- final source release validator: pass; dynamic versioning present,
  publication paused, and all three workflows read-only.
- ranking contract: 13 datasets, 369 judgments, bundle SHA-256
  `5a79f58aaca87a2d4f7cbec68fdcfbbf041131821587f8aba74a86daca99d9`.
- C6 syntax forecast: pass, forecast SHA-256
  `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
- `uv lock --check`, `git diff --check`, and local Markdown-link audit: pass.
- final archive validation: one wheel and one sdist, matching version metadata,
  required focused modules and assets present, and removed product surfaces
  absent.
- wheel:
  `buoy_search-0.4.1.dev130+g7d359f344.d20260730-py3-none-any.whl`,
  53 files, SHA-256
  `4a91c916df062df09f01e5a3647c9e8343d2d7dc8dd3ec8dd82333e3cad0f9f4`.
- sdist:
  `buoy_search-0.4.1.dev130+g7d359f344.d20260730.tar.gz`,
  106 files, SHA-256
  `bc38516db5a2db1d17e8fe534f6c610044ac12e1173e03d767572a6430e99344`.
- clean installed-wheel smoke: version, help, module entry point, exact
  five-command boundary, imports, and tokenizer behavior passed.

## Side-effect boundary

No Turbopuffer, database, warehouse, object store, or other data-provider call
was made. No namespace was listed, read, repaired, migrated, or deleted. The
known incomplete remote evidence snapshot remains untouched and is documented
for a separately approved exact-ID recovery. No protected branch, tag, release,
or deployment is changed by this work; the only intended remote writes are the
task branch and its draft pull request.
