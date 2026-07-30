Status: active
Created: 2026-07-30
Updated: 2026-07-30

# Buoy Is a Focused Indexer

## Context

Buoy achieved its original purpose: turn one website, public GitHub repository,
local document, or already-shaped database relation into a reviewed,
incremental turbopuffer search index. Later work added namespace discovery,
multi-namespace retrieval, semantic routing, a remote catalog, a cross-plan
Command Center, and remote evidence snapshots. Those capabilities now form the
beginning of a separate context-layer product named Kite.

The last historical commit with the original single-corpus product shape is
`d9ca6dbc47f26ca03d424c2a997636d6c963a54d`. Database-relation ingestion,
important safety fixes, compact schema-v2 plans, and improved chunking arrived
later and remain consistent with the original purpose.

On 2026-07-30 the user ratified the split with these defaults:

- preserve Buoy history and release tags;
- refocus through the protected `work/* -> develop -> main` flow;
- retain website, repository, document, and database-relation indexing;
- move multi-namespace retrieval and the Command Center to Kite;
- create Kite as a public repository with clean history;
- stop at draft pull requests;
- leave incomplete turbopuffer snapshot resources untouched.

## Decision

Buoy owns one explicit indexing target at a time:

1. acquire one supported source;
2. normalize and deterministically chunk it;
3. create a local, reviewable, baseline-bound plan;
4. apply the approved delta to one explicitly selected turbopuffer namespace;
5. retrieve and evaluate within that one namespace.

Buoy retains:

- website, public GitHub repository, local document, DuckDB, BigQuery, and
  Snowflake relation sources;
- local planning, compact delta artifacts, review, confirmation, incremental
  apply, applied-state safety, stale-row handling, retrieval, and evaluation;
- source-aware ranking, syntax-aware chunking, tokenizer-aware subdivision,
  citations, result tags, and provider-free dry runs.

Buoy does not own:

- account-wide namespace discovery;
- multi-namespace retrieval or cross-namespace result fusion;
- automatic semantic routing;
- local or remote routing catalogs;
- evidence snapshots, concepts, mentions, assertions, taxonomy, ontology, or
  Data Vault mapping guidance;
- a cross-plan, cross-namespace, or graph-oriented Command Center.

Those capabilities belong to Kite. Buoy may expose stable library functions
that Kite can call, but it does not orchestrate Kite's account-wide context
layer.

This decision supersedes the following records as active Buoy product
authority. They remain in history only as implementation provenance for Kite:

- `production-routing-remote-catalog.md`;
- the remote catalog, catalog CLI, namespace discovery, default routing, and
  explicit multi-namespace retrieval specifications;
- the approved-apply catalog-registration and database-catalog specifications;
- the Command Center and Phase 2A planning-job specifications;
- the remote evidence-snapshot specification;
- the representative semantic-routing and account-wide baseline specifications;
- `data-vault-is-analogy-not-architecture.md` for Buoy (Kite must make its own
  architecture decision).

## Consequences

The refocus is a forward change. Published history, tags, and release records
remain intact; `main` is never force-reset to the historical boundary.

Retrieval and evaluation require exactly one target namespace supplied by
`--namespace`; ambient namespace selection is not routing authority. Applying a
plan writes only content and local applied state; it no longer creates or
updates a routing card.

The Command Center, catalog, routing, evidence-snapshot, and experimental
account-wide modules leave the Buoy distribution. Historical `.10x` records
remain available as provenance unless they would actively misstate current
authority, in which case they are marked superseded.

The incomplete live evidence-snapshot attempt remains an external recovery
concern for Kite. This decision authorizes no provider deletion or mutation.
