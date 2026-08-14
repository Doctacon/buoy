Status: pass
Created: 2026-08-13
Updated: 2026-08-13
Ticket: .10x/tickets/2026-08-13-implement-automatic-multi-corpus-retrieval.md
Evidence: .10x/evidence/2026-08-13-automatic-multi-corpus-retrieval.md

# Automatic Multi-Corpus Retrieval Review

## Scope

Independent review covered the complete bounded implementation: remote routing
cards and catalog lifecycle, apply registration, automatic and explicit
selection, concurrency and widening, partial failures, deduplication, pinned
local reranking, namespace coverage, output compatibility, evaluation metrics,
live-collector provenance, credentials and provider-error redaction, public
documentation, and active governance records.

## Findings closed during review

- Coverage replacement now preserves every namespace represented through a
  deduplicated hit and revalidates membership before claiming coverage.
- The namespace-local-rank-one coverage policy is consistent in product JSON,
  documentation, tests, and collector provenance.
- Provider construction, catalog namespace acquisition, pagination,
  descriptors, iterators, normalization, and write-response processing all
  fail through bounded redacted errors without retaining a secret-bearing
  exception chain.
- Apply suggests only safe catalog inspection until the existing card has been
  read, so a recovery command cannot overwrite manual semantics unknowingly.
- Public/offline evaluation and `validate-run` can never manufacture live
  provenance. Only the collector's private immediate path may qualify after
  exact comparison with a clean current commit/tree, dataset, catalog, all
  model identities/configurations, evaluator, and invocation.
- Active Buoy/Kite and command-surface records now describe the bounded
  restoration consistently without reviving removed control-plane features.

## Verdict

The implementation is a bounded code, security, product, evaluation, and
governance PASS. The post-review locked suites pass 626 tests on Python 3.11
and 626 on Python 3.13; focused adversarial tests, dependency lock, release,
ranking, tokenizer, distribution, clean-wheel, and diff-hygiene checks pass.

Release-quality evidence is closed for task handoff. The repository owner
explicitly approved the fixed 50-question answer key on 2026-08-13 without
changing its questions or judgments. Clean commit `11b2b05f5fd8d3f86c8c7228ba805e7dc164a568`
then passed the new in-process live collector with all 50 cases complete, every
quality and provenance gate passing, and no failed checks. Historical
dirty-tree reports remain diagnostics only. This review authorizes no
self-merge, release, content mutation, namespace deletion, or credential
change.
