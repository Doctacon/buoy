Status: active
Created: 2026-07-30
Updated: 2026-07-30

# Focused Buoy Boundary

## Product contract

Buoy converts one supported source into one reviewed, incremental turbopuffer
search index and searches that explicitly selected index.

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

`retrieve` and `evals` require one singular `--namespace`. Buoy performs no
namespace-list or catalog read to choose a target, and
`TURBOPUFFER_NAMESPACE` is not an implicit routing authority.

`apply --dry-run` remains provider- and credential-free. Approved apply writes
the verified content delta to the plan's one namespace and commits local state.
It performs no catalog registration or account-wide discovery.

## Removed product surfaces

The Buoy package and distributions exclude:

- namespace discovery;
- semantic routing and routing catalogs;
- multi-namespace retrieval;
- the Command Center server, API, durable jobs, frontend, and static bundle;
- remote evidence snapshots;
- account-wide experimental baseline executors and semantic-routing fixtures.

## Compatibility

Existing source plans and applied-state databases remain valid when they satisfy
the active compact schema-v2 contract. Existing turbopuffer content namespaces
are not mutated by this refocus. Existing routing catalog and evidence
namespaces are left untouched, but Buoy no longer reads or writes them.

The apply summary retains the explicit retrieval handoff commands introduced
after v0.2.1. Those commands name exactly one namespace and require no catalog.
Successful approved apply also emits `receipt_schema_version=1` with its source,
plan/apply identities, artifact hash, embedding contract, ranking contract, and
vector dimensions/write counts. That summary is the versioned integration event
Kite consumes; Buoy never imports or calls Kite.

## Release safety

Version authority remains Git tags through Hatch VCS. Publication is paused:
source validation checks the dynamic configuration without choosing a target
version, and every release-related workflow is read-only. Legacy static-version
publication commands fail cleanly.

No release, merge to `develop`, merge to `main`, tag, or provider mutation is
part of the implementation ticket. The handoff ends with a validated work
branch and draft pull request.

## Acceptance criteria

1. CLI help exposes only the five focused commands.
2. Website, repository, local-document, DuckDB, BigQuery, and Snowflake planning
   tests pass.
3. Apply dry run and approval tests prove no catalog dependency remains.
4. Retrieval accepts one explicit target and rejects repeated namespaces.
5. Removed product modules, frontend assets, documentation, and package
   artifacts are absent.
6. Full focused tests, lock checks, distribution builds, import/help checks,
   release validation tests, and `git diff --check` pass.
7. No live turbopuffer call, remote mutation, release, or branch merge occurs.
