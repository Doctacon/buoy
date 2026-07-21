Status: open
Created: 2026-07-20
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-20-shape-deterministic-token-budget-subdivision.md

# Implement Deterministic Token-Budget Source Subdivision

## Outcome

Implement and validate only the active source-range subdivision behavior in `.10x/specs/deterministic-treatment-token-budget-subdivision.md` for `fixed-80-python-breadcrumbs` and `python-ast`. This ticket is executable for source and tests, but not for prose behavior, C6 forecast/artifact regeneration, model inference, live operations, namespace writes, or promotion.

## Scope

- Add the smallest post-`SourceRange`, pre-final-`MarkdownChunk` compatibility pass required by the active specification.
- Use only the exact pinned offline BGE tokenizer identity/options and count the complete production-rendered candidate embedding payload.
- Exhaustively choose the farthest feasible physical-line prefix from each cursor without crossing an existing parent range.
- Preserve exact parent breadcrumbs, AST/fallback ownership, LF coverage, payload-accurate citations, metadata, ordering, and semantic row identity rules.
- Fail the complete repository/arm plan on an individually over-limit rendered source line, tokenizer/lock/identity drift, or any invariant failure, with only the specified sanitized diagnostic.
- Preserve byte-for-byte common header, prose, `current-default`, ordinary no-arm, metadata/card, and generic split/overlap behavior.
- Add focused and full tests for the active specification’s downstream implementation/validation requirements on CPython 3.11 and 3.13.

## Acceptance criteria

- Exact tokenizer revision, file-set identity, implementation/package lock, maximum 512, special-token, no-truncation, no-padding, offline, no-model, and mismatch-failure behavior are enforced and tested.
- Every feasibility decision tokenizes the complete final production-rendered Title/Section/breadcrumb/fence/language/source payload with its exact changing `Lines S-E` citation.
- Exhaustive farthest-feasible selection is tested, including a non-monotone feasibility seam; binary search and first-failure assumptions are absent.
- Every emitted source payload is at most 512 exact tokens; children are nonempty, adjacent, non-overlapping, remain inside one parent, and reconstruct every LF physical line exactly once with exact citations.
- Children copy parent breadcrumb tuples and retain AST owner/nesting or fallback category; no ownership/breadcrumb recomputation or generic split/overlap occurs.
- A 513-token complete one-line payload fails the complete repository/arm plan with sanitized identity and no partial artifact, omission, fallback, truncation, or source/token disclosure. Incompatible header or prose rows remain independent failures.
- Identical pinned inputs regenerate deterministic boundaries, semantic identities, consecutive indexes, and stable file/header/source/prose order; compatible source rows remain unchanged.
- Ordinary no-arm, `current-default`, common headers, prose, metadata/cards, dependencies outside the already locked path, and defaults are unchanged.
- Focused and complete suites pass on CPython 3.11 and 3.13 with identical subdivision boundaries, counts, citations, and identities.
- No plan/forecast/token-report mutation, model construction/inference, network fallback, credential/provider access, namespace/catalog/applied-state/default operation, retrieval, delete, evaluation, or promotion occurs.

## Stop conditions

- Stop and return to shaping if implementation exposes any semantic choice not settled by the active source contract.
- Stop rather than infer prose subdivision, intra-line coordinates, truncation, fallback, omission, breadcrumb recomputation, parent crossing, or alternate tokenizer behavior.
- Do not regenerate C6 plans or artifacts from this ticket. A separate task remains required after implementation review, and C6 stays blocked until source and prose readiness both pass.

## Blockers

None. The exact source-only contract passed independent review and was user-ratified unchanged. The completed Option A prose owner resolves prose semantics as no action; its 366 preserved incompatibilities and the blocked C6 checkpoint do not prevent local source/test implementation, but they prohibit widening this ticket or claiming C6 readiness.

## Explicit exclusions

Prose subdivision or other prose behavior; intra-line splitting; control/header/default changes; dependency/lockfile changes unless the active exact package-lock contract cannot be used as-is and shaping is reopened; plan/forecast/token-report/namespace regeneration; model construction/inference/download; credentials/provider access; namespace/catalog/applied-state/default operations; retrieval; deletes; evaluation; promotion; write approval.

## Evidence expectations

Focused and full CPython 3.11/3.13 results; exact golden tokenizer/payload/boundary/coverage/citation/breadcrumb/failure/identity/isolation assertions; changed-file and diff review; proof that preserved C6 artifacts and validator hashes remain unchanged; no-live-operation attestation; and independent implementation review at the exact implementation head.

## References

- `.10x/specs/deterministic-treatment-token-budget-subdivision.md`
- `.10x/specs/repo-python-syntax-chunking-experiment.md`
- `.10x/evidence/2026-07-20-deterministic-token-budget-subdivision-contract-ratification.md`
- `.10x/evidence/2026-07-20-deterministic-token-budget-subdivision-shaping.md`
- `.10x/reviews/2026-07-20-deterministic-token-budget-subdivision-contract-review.md`
- `.10x/tickets/done/2026-07-20-shape-deterministic-token-budget-subdivision.md`
- `.10x/tickets/done/2026-07-20-shape-prose-token-budget-compatibility.md`
- `.10x/tickets/2026-07-19-evaluate-python-syntax-chunking.md`
- `src/buoy_search/repo_syntax_chunking.py`
- `src/buoy_search/github_repo.py`
- `src/buoy_search/chunker.py`
- `src/buoy_search/plan_artifacts.py`

## Progress and notes

- 2026-07-20: Opened after independent PASS and exact user ratification activated the source-only contract. This ticket owns only the bounded local source/test implementation. The 366 incompatible prose plan rows were assigned a separate shaping owner; that owner later resolved semantics as byte-preserving Option A while retaining the incompatibilities, so C6 remains blocked. No source/test implementation, artifact regeneration, model/live operation, or write occurred in the ratification turn.
