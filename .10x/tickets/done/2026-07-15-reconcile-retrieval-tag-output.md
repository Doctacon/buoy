Status: done
Created: 2026-07-15
Updated: 2026-07-19
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

None. On 2026-07-19 the user ratified output-only behavior: existing automatic chunk tags are returned in JSON and conditionally shown in text, no tag filtering is added, single/multi output is consistent, and missing-tag schema fallback preserves existing `repo_path` portability.

## Progress and notes

- 2026-07-15: Drift discovered during metadata/tagging/knowledge-graph research. Repository search found no existing active or terminal ticket owning retrieval tag output/filtering. No implementation or live operation occurred.
- 2026-07-19: User ratified the exact output decision: every live JSON hit has ordered `tags` as a list (empty when absent/unavailable); text shows only non-empty tags; no tag filter or ranking behavior is added; single/multi namespace hits are consistent; and bounded missing-attribute fallback supports old schemas without weakening `repo_path` portability.
- 2026-07-19: Inspected current `SearchHit` serialization, text rendering, raw/grouped hit construction, single/multi result shapes, existing missing-`repo_path` retry, active multi-namespace specification, focused tests, and documentation drift.
- 2026-07-19: Activated `.10x/specs/retrieval-tag-output.md` and opened bounded executable child `.10x/tickets/2026-07-19-return-retrieval-tags.md`. The child is review-ready with focused test/evidence expectations and no unresolved semantic blocker. No source, user documentation, tests, live operation, remote resource, or product behavior changed in this shaping turn.

## Closure mapping

- Ratified behavior and single/multi compatibility: `.10x/specs/retrieval-tag-output.md`.
- Bounded implementation, test, documentation, evidence, and review owner: `.10x/tickets/2026-07-19-return-retrieval-tags.md`.
- Historical drift and original blocker remain preserved above.

## Retrospective

Separating tag output from filtering avoids inventing filter grammar or ranking semantics. Treating `tags` and `repo_path` as independently optional retrieval attributes makes the old-schema compatibility requirement explicit without allowing unrelated provider failures to fall through.
