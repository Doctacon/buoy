Status: active
Created: 2026-07-30
Updated: 2026-08-13
Amended-By: .10x/specs/automatic-multi-corpus-retrieval.md

# Focused Buoy Boundary

The catalog, namespace discovery, automatic routing, and bounded
multi-namespace retrieval exclusions below are amended by
`.10x/specs/automatic-multi-corpus-retrieval.md`. All other product and release
boundaries remain active.

## Product contract

Buoy converts one supported source into one reviewed, incremental turbopuffer
search index and searches one explicit index or an automatically selected set
of at most three compatible indexes.

Supported sources are one HTTP(S) website, one public GitHub repository, one
local document, or one already-shaped DuckDB, BigQuery, or Snowflake relation.
Database commands read one final document-shaped relation; upstream extraction,
transformation, and orchestration remain outside Buoy.

## Required commands

The public CLI contains:

- `crawl`
- `plan`
- `apply`
- `retrieve`
- `evals`
- `catalog`

`retrieve` without `--namespace` validates account inventory against
`buoy-routing-catalog-v1` and routes automatically. One to three repeated
explicit `--namespace` values bypass that work. `evals` remains explicitly
targeted, and `TURBOPUFFER_NAMESPACE` is not implicit routing authority.

`apply --dry-run` remains provider- and credential-free. Approved apply writes
the verified content delta to the plan's one namespace and commits local state.
Only after that commit it conditionally registers the namespace card. Catalog
failure is reported as partial success and does not roll back content/state.

## Removed product surfaces

The Buoy package and distributions exclude:

- the Command Center server, API, durable jobs, frontend, and static bundle;
- remote evidence snapshots;
- account-wide experimental baseline executors and semantic-routing fixtures.

## Compatibility

Existing source plans and applied-state databases remain valid when they satisfy
the active compact schema-v2 contract. Existing turbopuffer content namespaces
are not mutated by this bounded restoration. Existing routing-catalog rows
remain compatible and evidence namespaces remain untouched. Buoy reads and
conditionally updates only the fixed routing catalog; it does not read or write
evidence namespaces.

The apply summary retains the explicit retrieval handoff commands introduced
after v0.2.1. Those commands name exactly one namespace and require no catalog.
Successful approved apply also emits `receipt_schema_version=1` with its source,
plan/apply identities, artifact hash, embedding contract, ranking contract, and
vector dimensions/write counts. That summary remains a versioned integration
event; Buoy never imports or calls Kite.

## Release safety

Version authority remains Git tags through Hatch VCS. Publication is paused:
source validation checks the dynamic configuration without choosing a target
version, and every release-related workflow is read-only. Legacy static-version
publication commands fail cleanly.

No release, merge to `develop`, merge to `main`, or tag is part of the
implementation ticket. Its separately reviewed exact catalog-card writes are
the only provider mutation it authorizes. The handoff ends with a validated
work branch and draft pull request.

## Acceptance criteria

1. CLI help exposes the five indexing/retrieval commands plus bounded `catalog`.
2. Website, repository, local-document, DuckDB, BigQuery, and Snowflake planning
   tests pass.
3. Apply dry run remains catalog-free; approved apply registers only after
   content/state success and reports catalog partial success truthfully.
4. Retrieval accepts one to three explicit targets or a complete-catalog
   automatic route, while preserving one-explicit compatibility.
5. Catalog/routing modules are packaged; Command Center, evidence, and
   experimental account-wide surfaces remain absent.
6. Full focused tests, lock checks, distribution builds, import/help checks,
   release validation tests, and `git diff --check` pass.
7. Validation makes only read calls; reviewed catalog-card writes are the sole
   provider mutation allowed by the implementation ticket.
