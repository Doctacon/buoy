Status: active
Created: 2026-07-30
Updated: 2026-08-13
Amended-By: .10x/decisions/buoy-owns-bounded-multi-corpus-retrieval.md

# Buoy Is a Focused Indexer

The bounded catalog, automatic routing, and multi-corpus retrieval exclusions
below are amended by
`.10x/decisions/buoy-owns-bounded-multi-corpus-retrieval.md`. All other focused
indexer boundaries remain active.

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

Buoy owns one explicit indexing target at a time and one bounded retrieval
route at a time:

1. acquire one supported source;
2. normalize and deterministically chunk it;
3. create a local, reviewable, baseline-bound plan;
4. apply the approved delta to one explicitly selected turbopuffer namespace;
5. retrieve within one explicit namespace or an automatically selected set of
   at most three compatible namespaces.

Buoy retains:

- website, public GitHub repository, local document, DuckDB, BigQuery, and
  Snowflake relation sources;
- local planning, compact delta artifacts, review, confirmation, incremental
  apply, applied-state safety, stale-row handling, retrieval, and evaluation;
- source-aware ranking, syntax-aware chunking, tokenizer-aware subdivision,
  citations, result tags, and provider-free dry runs.
- the fixed routing catalog, account inventory needed to validate it, bounded
  automatic routing, and bounded multi-corpus reranking.

Buoy does not own:

- evidence snapshots, concepts, mentions, assertions, taxonomy, ontology, or
  Data Vault mapping guidance;
- a cross-plan, cross-namespace, or graph-oriented Command Center.
- unbounded orchestration, general-purpose context management, or ACL
  administration across an account.

Those broader capabilities belong to Kite. Buoy does not orchestrate Kite's
account-wide context layer.

This decision supersedes the following records as active Buoy product
authority. They remain in history only as implementation provenance for Kite:

- `production-routing-remote-catalog.md`;
- the Command Center and Phase 2A planning-job specifications;
- the remote evidence-snapshot specification;
- the representative semantic-routing and account-wide baseline specifications;
- `data-vault-is-analogy-not-architecture.md` for Buoy (Kite must make its own
  architecture decision).

## Consequences

The refocus is a forward change. Published history, tags, and release records
remain intact; `main` is never force-reset to the historical boundary.

Retrieval accepts an explicit namespace override or uses the validated remote
catalog to select at most three targets. Ambient environment values remain
non-authoritative. Successful approved apply registers its routing card only
after content and local state commit; registration failure is explicit partial
success and never rolls content back.

The catalog and bounded routing modules return to the Buoy distribution. The
Command Center, evidence-snapshot, and experimental account-wide modules remain
excluded. Historical `.10x` records remain provenance; only the new bounded
decision and specification are current authority for restored behavior.

The incomplete live evidence-snapshot attempt remains an external recovery
concern for Kite. This decision authorizes no provider deletion or mutation.
