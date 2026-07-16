Status: blocked
Created: 2026-07-15
Updated: 2026-07-15
Parent: None
Depends-On: None

# Reconcile Retrieval Tag Output

## Scope

Resolve the observed drift between indexed chunk attributes and documented retrieval output:

- `src/buoy_search/chunker.py` defines a filterable `tags: []string` Turbopuffer attribute.
- `src/buoy_search/plan_artifacts.py` writes each chunk's `tags` into its Turbopuffer row.
- `docs/retrieval.md` says live results include tags.
- `src/buoy_search/retriever.py` does not request `tags` in `RETRIEVAL_ATTRIBUTES`, `SearchHit` has no tags field, and no retrieval test asserts tag output.

This ticket currently owns shaping only. It MUST NOT decide whether the correct behavior is to expose tags, filter by tags, or narrow the documentation until intended product behavior is ratified.

## Acceptance criteria

Before becoming executable:

- Ratify whether retrieval must return tags, support tag filters, both, or neither.
- If output changes, define single- and multi-namespace text/JSON compatibility and missing-schema fallback behavior.
- If filtering changes, define CLI/API filter semantics for one versus multiple tags and their interaction with `doc_kind`.
- Update the governing retrieval specification or record an explicit no-behavior-change documentation correction.
- Create a bounded executable ticket with tests appropriate to the ratified contract.

## Explicit exclusions

- Semantic tag extraction, taxonomies, namespace catalogs, concept graphs, or knowledge graphs.
- Live Turbopuffer writes or queries.
- Guessing that the documentation or current implementation is authoritative.

## References

- `.10x/research/2026-07-15-metadata-tagging-graphs-and-data-vault.md`
- `.10x/specs/explicit-multi-namespace-retrieval.md`
- `src/buoy_search/chunker.py`
- `src/buoy_search/plan_artifacts.py`
- `src/buoy_search/retriever.py`
- `docs/retrieval.md`

## Evidence expectations

Record the ratified behavior, focused unit tests, single- and multi-namespace output checks where applicable, schema-fallback behavior, and documentation consistency. No live retrieval is required unless separately authorized.

## Blockers

The intended public behavior is unclear. Current source proves tags are stored but not returned; documentation claims they are returned; the active retrieval specification does not settle tag output or filtering.

## Progress and notes

- 2026-07-15: Drift discovered during metadata/tagging/knowledge-graph research. Repository search found no existing active or terminal ticket owning retrieval tag output/filtering. No implementation or live operation occurred.
