# Migrating to focused Buoy

Buoy's indexing contract remains one source to one reviewed Turbopuffer
namespace. Retrieval may search one explicit namespace or an automatically
selected set of at most three compatible namespaces.
The change is forward-only: repository history, release tags, existing content
namespaces, historical plans, and local DuckDB applied state are preserved.

## CLI changes

The public commands are:

```text
crawl
plan
apply
retrieve
evals
catalog
```

`serve`, `namespaces`, `evidence`, `--auto-route`, `--route-top-k`, and
retrieval's no-op `--live` option remain outside Buoy. The bounded `catalog`
surface and automatic multi-corpus retrieval have returned; the Command Center,
evidence lifecycle, and general account orchestration remain in Kite.

Omit `--namespace` to route automatically, or repeat it up to three times for a
deterministic override:

```bash
buoy retrieve "question"
buoy retrieve "question" --namespace site-example-docs-v1
buoy retrieve "comparison" \
  --namespace site-example-docs-v1 \
  --namespace site-another-corpus-v1
buoy evals --namespace site-example-docs-v1 --dry-run
```

`TURBOPUFFER_NAMESPACE` no longer supplies a default. Region, embedding model,
and embedding precision environment settings remain supported.

After content and local state commit, approved apply conditionally registers or
refreshes the namespace's routing card and reports the outcome in its
`receipt_schema_version=1` summary. A catalog failure is explicit partial
success and includes a reviewed repair command; it never rolls content back.
The exact remote catalog schema v3 is a one-time reader-first prerequisite.
Provision a missing catalog or migrate v1/v2 to v3 as a separately reviewed
operation before applying schema-v3 plans. Ordinary apply, including the first
apply in a clean account, does not create or migrate the catalog.

If the catalog is missing or not exact v3 after content and local state commit,
apply performs no catalog schema or card write, returns nonzero partial success,
and retains the exact plan as repair authority. Complete the prerequisite and
run the emitted retained-plan `catalog repair-apply --inspect-current` command.
That read-only step revalidates the committed plan/apply authority under the
namespace lock, strongly reads exact-v3 state, and emits a repair command bound
to observed card absence or its exact revision. It performs no model work or
write and retains the plan. Review and run the bound command; only a fully
successful registration makes the namespace immediately eligible for automatic
top-three routing without generated questions or a separate card edit.
An unreadable catalog emits the same inspection command for use after the read
failure is resolved.

Schema-v3 cards persist bounded, verbatim-derived source excerpts as routing
passages. Normal Buoy output redacts them and their vectors, but credentials
authorized to query raw catalog provider rows can read the excerpts. Treat
catalog read access as source-content access during rollout.

## User-global local defaults

An installed `buoy` command now uses one implicit home no matter which working
directory invokes it:

```text
~/.buoy/state/<source-id>/<namespace>/state.duckdb
~/.buoy/artifacts/site-crawls/
```

The first path holds applied-state databases. The second holds default crawl
output and pending plan directories. An `apply` without `--plan` searches only
that user-global artifact root and proceeds only when exactly one supported
pending plan exists; zero or multiple candidates require an explicit
`--plan`.

This default change is prospective. Buoy does not implicitly discover, copy,
move, merge, backfill, archive, or delete a noncanonical current-directory
`.buoy`, `.turbo-search`, or `artifacts/site-crawls`. Supported existing state
and plans remain available through explicit paths:

```bash
buoy apply \
  --plan /path/to/project/artifacts/site-crawls/example-plan/plan.json \
  --state-root /path/to/project/.buoy \
  --dry-run
```

Use the same explicit old state root when creating the next plan if its
incremental baseline must continue. Without it, the new user-global ledger is
absent and planning uses normal first-apply semantics; Buoy does not reconstruct
that baseline from remote rows. Explicit selection opts the old assets into
their normal lifecycle: state writes use the selected root, and a fully
successful apply may consume its exact verified plan directory.

The Buoy home covers Buoy-owned state and crawl/plan artifacts. It does not
relocate `uv` tool/download caches or Hugging Face and Sentence Transformers
model caches.

## Existing project-local state and artifacts

The old project-local state layout was:

```text
.buoy/state/<source-id>/<namespace>/state.duckdb
```

Existing `.buoy` and `.turbo-search` DuckDB state remains in place and usable
with explicit `--state-root`. It is byte-inert unless explicitly selected;
selected state receives the requested normal writes. There is no longer an
implicit current-directory or `.turbo-search` fallback. Obsolete JSON state is
ignored and left unchanged.

The split leaves these legacy artifacts untouched:

- local catalog and catalog-pending files;
- old local catalog files and pending-recovery artifacts;
- `buoy-evidence-*` namespaces;
- Command Center job/event history;
- historical plans and `.10x` records.

`buoy-routing-catalog-v1` is again active, bounded Buoy routing authority. The
other artifacts remain historical or Kite-owned and are not automatically
repaired or deleted. See [Buoy and Kite](kite-split.md) before proposing any
cleanup.

## Package changes

The Buoy distribution includes the small routing-card, catalog, bounded
retrieval, and automatic relevance-assessment modules. It still excludes
FastAPI/Uvicorn UI dependencies, Command Center assets/source, the broader
evidence lifecycle/control plane, and evidence-management CLI commands.

Website, repository, local-document, DuckDB, BigQuery, and Snowflake relation
support remains. BigQuery and Snowflake continue as optional dependencies.

## Removed turbo-search aliases

The earlier `turbo-search` executable and
`TURBO_SEARCH_EMBEDDING_MODEL`/`TURBO_SEARCH_EMBEDDING_PRECISION` variables
remain unsupported. Use `buoy`, `BUOY_EMBEDDING_MODEL`, and
`BUOY_EMBEDDING_PRECISION`.
