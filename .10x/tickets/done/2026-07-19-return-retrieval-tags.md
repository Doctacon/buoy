Status: done
Created: 2026-07-19
Updated: 2026-07-20
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
- 2026-07-19: Implemented the active retrieval-tag contract on `work/return-retrieval-tags`: requested stored tags, added always-list `SearchHit` JSON, conditional ordered text output, representative-group preservation, and bounded missing-`tags`/`repo_path` fallback in either successive order. Added focused single/grouped/explicit/routed multi and failure-atomicity tests and updated `docs/retrieval.md`. Fake-backed focused suites passed 74 tests on Python 3.11 and 3.13; full suites passed 431 tests on each; the Python 3.13 package build and `git diff --check` passed. No live Turbopuffer read/write, filter, ranking, default, schema, or migration operation occurred. Evidence: `.10x/evidence/2026-07-19-return-retrieval-tags-implementation.md`. Ticket remains active pending the required independent review.
- 2026-07-19: Incorporated current `origin/develop` (no divergence), committed implementation as `bd06042`, pushed `work/return-retrieval-tags`, and opened PR #57 (`https://github.com/Doctacon/buoy-search/pull/57`) against `develop`. No merge or closure was performed; independent review remains required.
- 2026-07-19: Repaired the PR #57 review blocker without widening scope at code/test commit `8aa2ced`: missing-schema fallback now parses exactly one known quoted `attribute "<name>" not found in schema` diagnostic and removes only its exact captured still-requested optional attribute. Added regressions proving `repo_tags` propagates and requested-attribute-list context cannot remove the other available optional attribute, with successive absence in both orders. Rebased onto current `origin/develop` at `0ce5f37`; focused 75-test and full 441-test suites passed on Python 3.11 and 3.13, the Python 3.13 CI distribution build and diff hygiene passed, and no live Turbopuffer operation occurred. Hosted PR #57 CI run `29720376822` passed Python 3.11, Python 3.13, and distribution build checks at pushed head `5c5202e`. Evidence: `.10x/evidence/2026-07-19-return-retrieval-tags-implementation.md`. Ticket remained active for independent re-review; no merge or closure was performed in that repair step.
- 2026-07-20: Independent final review passed PR #57 at exact head `b54e9f2681974ac368160ce27fe982ed37efdb94`; hosted CI run `29720445368` passed Python 3.11, Python 3.13, and distribution jobs at that reviewed head. The review mapped every acceptance criterion, confirmed the fallback blocker was repaired without scope expansion, and retained the fake-provider limitation as residual risk. Review: `.10x/reviews/2026-07-20-return-retrieval-tags-review.md`.

## Closure mapping

- Always-present ordered JSON tags and absent/empty normalization: reviewed `SearchHit` and row-conversion implementation plus focused serialization assertions.
- Conditional ordered text output: focused single- and multi-namespace CLI assertions and independent review.
- Representative raw/grouped tag preservation: focused ranking/grouping assertions and reviewed ranking reconstruction.
- Single, explicit multi, and automatically routed multi consistency with namespace attribution: focused serializer/routing assertions and independent review.
- Initial `tags` plus `repo_path` requests, bounded successive fallback in either order, unrelated-error propagation, and no partial results: exact fake-provider request sequences and failure regressions recorded in implementation evidence and independently reviewed after repair.
- No filter, ranking, `doc_kind`, schema, migration, or live-operation expansion: bounded diff inspection, documentation inspection, and independent review.
- Documentation and supported-version validation: retrieval guide inspection; focused/full Python 3.11/3.13 suites, Python 3.13 distribution build, diff hygiene, and exact reviewed-head hosted CI.

## Retrospective

Optional-attribute portability must associate fallback with the provider's exact missing-schema diagnostic, not search the whole error message for known field names. Provider messages may echo the complete requested attribute list, so message-wide substring matching can remove an available attribute and conceal unrelated failures. Parsing one exact diagnostic, requiring that its name is both optional and still requested, and testing requested-list context preserves independent fallback while mechanically bounding retries. The durable behavioral rule remains in `.10x/specs/retrieval-tag-output.md`; the focused regressions preserve the implementation lesson, so no separate knowledge record or follow-up ticket is needed.
