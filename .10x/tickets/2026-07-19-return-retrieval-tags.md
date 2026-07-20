Status: open
Created: 2026-07-19
Updated: 2026-07-19
Parent: .10x/tickets/done/2026-07-15-reconcile-retrieval-tag-output.md
Depends-On: None

# Return Retrieval Tags

## Scope

Implement `.10x/specs/retrieval-tag-output.md` in the existing retrieval path: request stored chunk tags, carry them through hit/ranking serialization, render the ratified JSON/text output, and extend missing-schema fallback without regressing current `repo_path` portability.

## Acceptance criteria

- Every live JSON hit contains `tags` as a list, including `[]` for empty or unavailable tags.
- Live text prints `Tags: <ordered values>` only for non-empty tags.
- Raw chunk and file/page-grouped results preserve the retrieved representative chunk's stored tag order and values.
- Single-namespace, explicit multi-namespace, and automatically routed multi-namespace hits use the same tag contract while retaining their existing top-level shapes and namespace attribution.
- Initial requests include both `tags` and `repo_path`; missing-attribute fallback handles tags-only, repo-path-only, and successively discovered absence of both without swallowing unrelated errors or issuing unbounded retries.
- Tag output adds no CLI/API filtering, query filter, ranking signal, or interaction change with the existing `doc_kind` filter.
- Retrieval documentation accurately describes the JSON, text, no-filter, and older-schema behavior.
- Focused and full non-live tests, formatting/lint/type checks required by the repository, diff hygiene, evidence, and independent review pass.

## Test expectations

Focused deterministic tests MUST cover:

- present, empty, and missing tags in `SearchHit` serialization and row conversion;
- non-empty versus empty tag text rendering;
- representative-hit tag preservation through file/page grouping;
- single- and multi-namespace JSON/text consistency and namespace attribution;
- successful fallback for missing `tags`, missing `repo_path`, and both attributes discovered in either order;
- no fallback for unrelated provider errors and no partial multi-namespace payload on failure.

No live Turbopuffer call is required.

## Evidence expectations

Record the exact implementation diff, focused/full command outputs, schema-fallback call sequences and included attributes, single/multi output assertions, documentation consistency, no-live-operation boundary, diff hygiene, and independent review.

## Blockers

None. The user ratified the output-only contract on 2026-07-19, and `.10x/specs/retrieval-tag-output.md` records the execution-complete behavior.

## Explicit exclusions

- Tag filtering, filter grammar, tag ranking/boosting, or `doc_kind` semantic changes.
- New tag derivation, taxonomy, ontology, concept/knowledge graphs, or governance.
- Chunking, plan/apply, remote schema, data migration, backfill, namespace mutation, or deterministic-ID changes.
- Live Turbopuffer reads/writes during validation.
- Changes outside retrieval hit transport, output rendering, focused documentation, and tests required by the active specification.

## References

- `.10x/specs/retrieval-tag-output.md`
- `.10x/specs/explicit-multi-namespace-retrieval.md`
- `.10x/tickets/done/2026-07-15-reconcile-retrieval-tag-output.md`
- `src/buoy_search/chunker.py`
- `src/buoy_search/plan_artifacts.py`
- `src/buoy_search/retriever.py`
- `src/buoy_search/cli.py`
- `docs/retrieval.md`
- `tests/test_retriever.py`
- `tests/test_multi_namespace_retrieval.py`

## Progress and notes

- 2026-07-19: Opened as the bounded executable child of the completed retrieval-tag shaping ticket after inspection of current JSON/text conventions, ranking propagation, `repo_path` schema fallback, and the active multi-namespace contract. No source, user documentation, tests, live operation, or external resource changed in this record-only turn.
- 2026-07-19: Ready for independent review and subsequent implementation on a separate `work/*` branch after this record-only change integrates into `develop`.
