Status: recorded
Created: 2026-08-13
Updated: 2026-08-13
Ticket: .10x/tickets/2026-08-13-implement-automatic-multi-corpus-retrieval.md

# Automatic Multi-Corpus Retrieval Evidence

## Candidate

- Branch: `work/automatic-multi-corpus-retrieval`
- Base: `origin/develop` `51a84a3b265d8ecee380d6792fcc7d8f7f9b7815`
- Live inventory observed read-only before implementation: eight namespaces,
  comprising five content namespaces, two evidence namespaces, and
  `buoy-routing-catalog-v1`.
- Existing catalog observed read-only: three enabled cards for Oscilar,
  Turbopuffer, and the Dagster benchmark namespace.
- Checked-in evaluation candidate:
  `src/buoy_search/data/automatic_multi_corpus_retrieval_evals.json` contains
  the fixed 20 unambiguous, 15 descriptor-free/confusable, 10 multi-corpus,
  and 5 no-answer cases. It inventories five physical content namespaces but
  scores four logical eligible corpora; `site-dagster-io-benchmark-v1` is the
  disabled duplicate and is never an expected route or judgment.
- Two independent reviewers examined the complete 50-case candidate against
  pooled indexed results and official source pages, then the candidate was
  adjudicated consistently across all cases. Judged pages that independently
  answer the same information need share one answer group. On 2026-08-13, the
  repository owner reviewed the fixed answer-key document and explicitly
  stated, "I approve this answer key." The dataset now records
  `human_approved_ground_truth=true` and `review_status=approved`; no question,
  judgment, answer group, or threshold changed during approval.
- `src/buoy_search/multi_corpus_evals.py` validates basket governance and
  implements the exact route, exhaustive-baseline Recall@5, pre/post-rerank
  Recall@5, macro nDCG@5, and all-50-case fanout definitions.
- `scripts/evaluate_multi_corpus_retrieval.py` now provides `collect`,
  `fixture`, and `validate-run`. The live collector has query-only content
  namespace adapters, verifies exact five-physical/four-eligible/one-disabled
  coverage before content retrieval, records logical namespace attempts and
  exact `multi_query` invocations, and strips every observation to a
  namespace/URL identity before serialization. The offline paths recompute
  stored metrics and the verdict and cannot load credentials, providers, or
  models. A candidate dataset always receives a non-passing verdict even when
  every numerical gate passes.

## Validation

- Focused post-review catalog, routing, retrieval, evaluation, apply, CLI, and
  provider-boundary validation passed, including 145 hardened retrieval/catalog
  tests and 83 evaluator-provenance tests.
- The scorer tests prove route-recall truncation at three while fanout uses the
  final route, reject the disabled duplicate, count incorrect high-confidence
  single routes, anchor automatic Recall@5 to exhaustive-available required
  answer groups, award equivalent pages only once, macro-average nDCG@5 across
  all 10 multi-corpus cases against a namespace-interleaved comparison, and
  expose rerank Recall@5 regression.
- Complete post-review locked suites: 626 tests passed on Python 3.11 and 626
  passed on Python 3.13. Tests fail closed on more than
  three automatic namespaces and missing/disabled/incompatible coverage,
  prove derived results are recomputed, assert the exact threshold contract,
  exercise retrieval-quality verdict failures, and patch every live
  provider/model factory to fail if the fixture or `validate-run` path touches
  it.
- The collector integration runs all 50 cases through fake provider/model
  seams while retaining the real routing, bounded retrieval, widening,
  exhaustive-search, deduplication, and reranking orchestration. It proves one
  cached content inference per case, all-four exhaustive attempts, exact
  `multi_query` accounting, zero writes, separate initial-confidence/final-route
  semantics after widening, and different captured pre/post-rerank identity
  orders.
- Release readiness additionally requires `mode=live`; even a human-approved
  perfect fixture remains non-passing. Route observations retain the initial
  high-confidence singleton after widening so a confidently wrong first choice
  cannot be hidden by final recall. When production does not apply reranking,
  the recorded pre-rerank order is the returned final order rather than a
  reconstructed top-eight/deduplicated order.
- Independent adversarial review identified those three collector semantics as
  blockers; each is now covered by a focused regression.
- `uv lock --check`, read-only release-source validation, ranking-contract
  validation, C6 syntax/tokenizer validation, distribution validation, clean
  wheel install/import/help/data smoke, and `git diff --check` all passed.
- A clean-commit provider-backed rerun and final validation after approval
  remain pending. Independent code/security and product/evaluation/governance
  reviews both passed the bounded implementation; human-owner approval is now
  satisfied.

## Live catalog reconciliation

- Three separate zero-write previews each reported `approved=false`, an empty
  `affected_ids`, and `write_requests=0` before mutation authority was used.
- After independent code/security review and a separate bounded product GO,
  exact approved catalog-only writes created the manual schema-1 cards for
  `site-dagster-io-v1` and `site-www-thistle-co-v1`, then disabled (without
  deleting) `site-dagster-io-benchmark-v1`.
- The three strong readbacks each reported one write and one exact affected
  card ID. Final catalog readback reported eight listed namespaces split into
  five content plus three control-plane namespaces; five live cards; four
  enabled/eligible targets (canonical Dagster, Oscilar, Turbopuffer, Thistle);
  one disabled benchmark duplicate; and zero missing, stale, or incompatible
  targets. No content namespace or row was mutated or deleted.

## Provider-backed quality results

- The first corrected live report used a flat one-URL-per-target evaluator and
  scored automatic Recall@5 as `27/34 = 0.7941176`. Independent adversarial
  review showed that several returned official pages answered the same needs
  under different URLs, while cross-encoder-only ordering removed candidates
  with strong namespace-local ranks. That report remains a useful diagnostic,
  but its evaluator contract is superseded and it is not release evidence.
- The evaluator now binds every collector-produced report to the raw dataset
  digest, evaluator digest, source commit/tree/clean state, catalog snapshot,
  exact routing/content/reranker revisions and configuration, and invocation.
  Only the collector's private immediate evaluation path can establish that
  structural trust after matching those fields to current runtime facts.
  Public/offline evaluation and `validate-run` recompute metrics but always
  mark saved provenance untrusted; they cannot upgrade hand-authored JSON or
  re-establish the original live assertion.
  Required answer groups credit any reviewed equivalent source once. The
  pre-rerank comparison interleaves namespaces by local rank, and the product
  combines MiniLM and namespace-local ordinal ranks with fixed equal-weight
  RRF (`k=60`) while preserving the namespace-local-rank-one hit from each
  nonempty namespace when the requested top-k permits it.
- Latest pre-hardening candidate diagnostic:
  `/private/tmp/buoy-multi-corpus-eval-20260813-05.json`, SHA-256
  `4d4d7b07ef9014ebfcd5a6fe00cfdddb1ba7540b575210101b31ea0b408bde0c`,
  dataset SHA-256
  `6e7f2dfed6622626c4a07cd00582d713ccaa82b0f107225afe4166be3b99f3be`,
  and catalog snapshot
  `ce12e12b1349bfd09ceff84480942dab17b60131e5f71390456e7677000cd93f`.
  It retained only case IDs, namespace/URL identities, timings, logical-call
  counts, provenance, metrics, and verdict; it serialized no question text,
  content, vectors, model input, credential, or raw provider response.
- All 50 cases completed with zero automatic or exhaustive failures through a
  query-only adapter that exposed no provider mutation method. Logical
  accounting recorded 50 routing embeddings, 50 content embeddings, 99
  automatic namespace queries, 200 exhaustive namespace queries, and 28
  MiniLM inferences. These are application-level calls, not provider audit
  telemetry.
- Every numerical gate passed: route recall@3 `57/58 = 0.9827586`; all 10
  multi-corpus routes complete; zero incorrect initial high-confidence routes;
  average/max fanout `1.98/3`; automatic Recall@5
  `33/34 = 0.9705882`; nDCG@5 `0.4817529 -> 0.5440087`
  (`+0.0622558`); and multi-corpus Recall@5 `0.9 -> 1.0`.
- The report is still correctly non-passing. Its source provenance records a
  dirty candidate tree, so `provider_backed_live_run` fails, and the candidate
  answer key was then human-unapproved. It predates the stricter evaluator-v3
  collector-only trust gate and records the superseded best-fused coverage
  policy, so the current evaluator rejects it as invalid historical input. It
  remains diagnostic only; the missing gates were subsequently satisfied by
  the approved clean run below.

## Clean approved result

- After the repository owner approved the fixed answer key, the complete
  implementation and approval state were committed as
  `11b2b05f5fd8d3f86c8c7228ba805e7dc164a568` with tree
  `79b70d64c602da48b3541c3995854bf27a3320be`. The worktree was clean before
  collection.
- The in-process live collector wrote
  `/private/tmp/buoy-multi-corpus-eval-20260813-06.json` (419,404 bytes),
  SHA-256
  `a29eaee6f66590888c82f0e2dbbb66e37cca6a12514ff9ac9a1893e3b1a44444`.
  It bound dataset SHA-256
  `29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`,
  evaluator-v3 SHA-256
  `7ea3e3d10ed5c081cb63a5d06d301470169dd4167a2894f7a85318c0852eb8d7`,
  and catalog snapshot
  `ce12e12b1349bfd09ceff84480942dab17b60131e5f71390456e7677000cd93f`.
- All 50 cases completed with zero automatic or exhaustive failures. Logical
  accounting recorded 50 routing embeddings, 50 content embeddings, 99
  automatic namespace queries, 200 exhaustive namespace queries, and 28 local
  reranker calls. The query-only provider adapter exposed no mutation method.
- Every release-quality gate passed with no failed checks: human approval and
  provider-backed provenance passed; route recall@3 was
  `57/58 = 0.9827586`; all 10 multi-corpus routes were complete; incorrect
  initial high-confidence routes were zero; average/max fanout was `1.98/3`;
  automatic Recall@5 was `33/34 = 0.9705882`; nDCG@5 improved
  `0.4817529 -> 0.5440087` (`+0.0622558`); and multi-corpus Recall@5 improved
  `0.9 -> 1.0`. The collector verdict was `release_ready=true`, `status=pass`.

## External effects

Previews and evaluation performed only namespace-list, metadata, catalog-row,
and bounded content reads. The only provider mutations were the three exact
reviewed routing-card changes above. No content row, content namespace,
credential, stale row, or release state was changed.
