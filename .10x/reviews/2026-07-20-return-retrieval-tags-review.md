Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Target: PR #57 at commit `b54e9f2681974ac368160ce27fe982ed37efdb94`
Verdict: pass

# Return Retrieval Tags Review

## Target and method

Independent adversarial review of PR #57 at head `b54e9f2681974ac368160ce27fe982ed37efdb94` against `.10x/specs/retrieval-tag-output.md`, `.10x/specs/explicit-multi-namespace-retrieval.md`, `.10x/tickets/done/2026-07-19-return-retrieval-tags.md`, the source and documentation diff, focused assertions, full-suite evidence, and exact-head hosted checks.

The review also rechecked the earlier fallback-association blocker. The original message-wide substring matching could remove the wrong optional attribute when a provider error mentioned `tags` or `repo_path` outside the actual missing-schema diagnostic. Commit `8aa2ced` replaced it with exact parsing of one quoted `attribute "<name>" not found in schema` diagnostic and added regressions for near names and requested-attribute-list context.

## Criteria mapping

- **JSON tag contract:** pass. `SearchHit.to_dict()` always emits a copied list. Row conversion preserves present ordered string values and maps empty, absent, or unavailable tags to `[]`; malformed non-list or non-string values fail rather than being silently reinterpreted.
- **Text tag contract:** pass. Single- and multi-namespace text render `Tags: <ordered values>` only for a non-empty list and retain existing output lines.
- **Grouping and ranking transport:** pass. Ranking reconstruction copies the representative hit's tags without using them in scoring, so raw and file/page-grouped results preserve the selected representative chunk's stored values and order.
- **Single-, explicit-multi-, and automatic-multi-namespace consistency:** pass. The shared per-hit serializer carries tags through all three result shapes while multi-namespace hits retain namespace attribution and routed output retains routing metadata.
- **Older-schema portability:** pass. Every initial ANN/BM25 request includes both `repo_path` and `tags`. Fallback removes only one exactly diagnosed, still-requested optional attribute, rebuilds both subqueries with the same attribute list, and terminates after at most the necessary three variants. Tests cover each attribute alone, both successive orders, requested-list context, a near-name, an unrelated missing attribute, malformed tags, and no partial multi-namespace output.
- **No filtering or ranking expansion:** pass. The bounded diff adds no CLI/API tag option, filter expression, ranking input, derivation, schema mutation, migration, or `doc_kind` behavior change.
- **Documentation and validation:** pass. `docs/retrieval.md` accurately describes JSON, conditional text, grouping, namespace consistency, output-only semantics, and older-schema fallback. Fake-backed focused and full suites passed on Python 3.11 and 3.13, distribution build and diff hygiene passed, and exact reviewed-head GitHub Actions run `29720445368` passed Python 3.11, Python 3.13, and distribution jobs.

## Findings

No blockers remain. The fallback repair is narrow, bounded, and covered by failure-path regressions. The implementation satisfies the active specifications and the ticket's acceptance criteria without widening scope.

## Verdict

Pass. The implementation ticket may close.

## Residual risk

Provider interaction is fake-backed. The tests prove request construction, exact mocked missing-schema diagnostics, bounded retry sequences, row conversion, serialization, rendering, and failure atomicity, but they do not prove that every live Turbopuffer SDK/version formats missing-attribute errors or row values identically. No live query was required or performed; provider availability, credentials, and account-specific schema state remain outside this review.
