Status: active
Created: 2026-08-13
Updated: 2026-08-13
Depends-On: None
Decision: .10x/decisions/buoy-owns-bounded-multi-corpus-retrieval.md
Specification: .10x/specs/automatic-multi-corpus-retrieval.md

# Implement Automatic Multi-Corpus Retrieval

## Outcome

Restore the existing remote routing-card boundary in focused form so
`buoy retrieve QUERY` can navigate every current content corpus, search at most
three namespaces, and produce a trustworthy locally reranked unified result.

## Scope

- Restore validated schema-v1 remote cards, inventory, management commands,
  apply-driven registration, and deterministic routing from repository history.
- Preserve explicit one-namespace retrieval compatibility while allowing
  repeatable explicit namespaces.
- Add high-confidence one-or-ambiguous-three selection, bounded concurrent
  retrieval, one-time widening, partial-failure reporting, deduplication, and
  pinned MiniLM reranking.
- Add a reviewed 50-query routing/end-to-end evaluation and update retrieval,
  indexing handoff, and Buoy/Kite documentation.
- Reconcile only the existing catalog after code review and validation: create
  missing canonical Dagster and Thistle cards and disable the duplicate Dagster
  benchmark card. Do not delete it or mutate any content row/namespace.

## Acceptance

- Automatic routing refuses incomplete live-card coverage and never routes to
  control-plane, stale, disabled, or incompatible cards.
- One explicit namespace preserves v0.5.1 behavior and output; explicit values
  bypass automatic work.
- Content embedding occurs once, fanout is at most three, single routes never
  load MiniLM, and multi routes rerank no more than 24 deduplicated candidates.
- Model failure, partial namespace failure, empty-first widening, and complete
  provider failure have exact tested behavior.
- Catalog preview/approval and post-apply registration preserve manual fields,
  report partial success, and never change content namespaces.
- The specification's quality gates, complete locked Python 3.11/3.13 suites,
  lock/release validators, distribution smoke, and diff check pass.

## Owned paths

- `src/buoy_search/{catalog,catalog_cli,remote_catalog,routing,retriever,cli,apply}.py`
- focused catalog, routing, retrieval, apply, CLI, and evaluation tests/data
- `README.md`, `docs/retrieval.md`, `docs/indexing.md`, `docs/kite-split.md`
- governing decision/specification and this ticket's evidence/review records

## External effects

Tests and evaluation may make read-only Turbopuffer inventory/catalog/content
queries using the existing `.env` key loaded by the command environment. After
passing independent review, exact approved catalog-only writes may create the
two missing rows and disable the one duplicate benchmark card. No other remote
write, namespace deletion, content mutation, key change, release, or branch
merge is authorized by this ticket.

## Exclusions

LLM/learned/hierarchical routing, multiple prototypes, account ACL design,
Command Center/evidence systems, mega-namespace migration, content reindexing,
source-adapter work, provider deletion, PyPI, and unrelated refactoring.

## Progress

- 2026-08-13: User approved the complete implementation plan. Isolated branch
  `work/automatic-multi-corpus-retrieval` was created from current
  `origin/develop` `51a84a3b265d8ecee380d6792fcc7d8f7f9b7815`.
- 2026-08-13: Added the governed 50-query evaluation candidate, strict loader,
  and reproducible routing/retrieval scorers. The basket remains explicitly
  unapproved pending human owner review; subsequent read-only live collection
  and independent candidate review do not substitute for that approval.
- 2026-08-13: Updated onboarding, retrieval, indexing, catalog, partial-failure,
  and Buoy/Kite boundary documentation for the automatic default and explicit
  repeatable override.
- 2026-08-13: Added the reproducible read-only 50-case collector and release
  gate at `scripts/evaluate_multi_corpus_retrieval.py`. Live collection requires
  an already-sourced process credential, rejects incomplete or incompatible
  five-namespace coverage before content reads, queries all four eligible
  corpora for the exhaustive baseline, and persists only case IDs,
  namespace/URL identities, timing, call accounting, metrics, and the recomputed
  verdict. Offline fixture and `validate-run` modes load no provider or model.
  Eval/release-focused validation passes 40 tests, including a 50-case
  fake-provider/model collector integration.
- 2026-08-13: After independent review, reconciled exactly the existing remote
  routing catalog: created canonical Dagster and Thistle cards and disabled the
  duplicate Dagster benchmark card. Strong readback reports five live cards,
  four eligible, one disabled, and no missing/stale/incompatible target. No
  content namespace or row was changed.
- 2026-08-13: Ran the corrected read-only live basket twice with deterministic
  routes and result identities. All 50 cases completed through a query-only
  adapter that exposed no provider mutation method. Routing, fanout,
  multi-corpus coverage, and reranker-improvement gates passed, but the first
  flat-URL evaluator scored automatic Recall@5 as `27/34 = 0.7941176` versus
  the required `0.95`. Ground truth remains explicitly human-unapproved.
- 2026-08-13: Independent review found that the flat exact-URL evaluation
  contract treated answer-equivalent official pages as misses and that
  cross-encoder-only ordering could erase strong namespace-local evidence.
  The full 50-case basket was independently reviewed twice, equivalent answers
  were grouped without changing any question, and the evaluator was hardened
  with digest-bound live provenance and a fair interleaved comparison order.
  Human owner approval remained deliberately unset during independent review.
- 2026-08-13: Added fixed equal-weight ordinal RRF over MiniLM rank and
  namespace-local rank plus deterministic one-hit-per-nonempty-namespace
  coverage when the requested top-k permits it. The latest collector-produced
  candidate run completed all 50 cases and passed every numerical gate: route
  recall@3 `57/58 = 0.9827586`, complete multi-corpus coverage `10/10`, zero
  incorrect confident routes, average/max fanout `1.98/3`, automatic Recall@5
  `33/34 = 0.9705882`, nDCG@5 improvement `+0.0622558`, and multi-corpus
  Recall@5 `0.9 -> 1.0`. It remains non-release evidence because it was
  collected from a dirty candidate tree.
- 2026-08-13: The repository owner reviewed the fixed 50-question answer-key
  document and explicitly approved it. The checked-in dataset now records
  `human_approved_ground_truth=true` and `review_status=approved`; no question,
  judgment, answer group, or threshold changed during approval.

## Blockers

- After the reviewed candidate is committed, the exact clean commit must rerun
  the read-only collector and all validation so live provenance can pass. The
  questions and approved judgments must remain unchanged for that run.
