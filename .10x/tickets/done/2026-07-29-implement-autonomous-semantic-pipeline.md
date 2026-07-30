Status: done
Created: 2026-07-29
Updated: 2026-07-30
Parent: .10x/tickets/done/2026-07-29-autonomous-local-semantics-foundation-plan.md
Depends-On: .10x/tickets/done/2026-07-29-implement-local-semantic-inference.md

# Implement Autonomous Semantic Pipeline

## Scope

Implement `.10x/specs/autonomous-semantic-builds.md`: strict semantic models and formulas, completed-snapshot active evidence streaming/sampling, extraction and deterministic remote resume, normalization/blocking/alias-sense resolution, canonical concepts/mentions, taxonomy proposal/independent verification/structural validation, exact remote schemas/catalog-last lifecycle, build identity, safety budgets/lock/manifest, quality report, fake provider/model fixtures, and 500-row structural coverage.

## Acceptance criteria

Focused semantic model/pipeline/remote tests cover extraction, repair, resume conflicts, active-only evidence, ambiguity/alias/close-match behavior, confidence score/status rules, exact schemas, taxonomy grammar/acyclicity/depth/parents/status, build identity/sampling/budgets, catalog-last/manifest limits, and 500-row measurements. No full corpus or semantic dataset persists locally; no source/evidence branch writes or hosted call path exists.

## Explicit exclusions

CLI estimate/verify/inspect presentation beyond seams needed by core, docs/package finalization, live model/provider smoke, arbitrary assertions/predicates, UI/graph, scheduling, incremental maintenance, deletion/GC, or cross-host lease recovery.

## Evidence expectations

Changed files, formulas/version strings, namespace/schema contracts, structural measurements, call/write batching, local bytes/RSS, focused commands, and residual risks.

## Blockers

None after local inference contract implementation.

## Progress and notes

- 2026-07-29: Implemented provider-injected core pipeline and remote lifecycle in `src/buoy_search/semantics_pipeline.py` and `src/buoy_search/semantics_remote.py`, with focused tests in `tests/test_semantics_pipeline.py` and `tests/test_semantics_remote.py`.
- 2026-07-29: Deterministic contracts use `semantic-confidence-v1`, `semantic-taxonomy-structure-v1`, `unicode-case-whitespace-punctuation-v1`, `type-first-token-bounded-v1`, `cluster-hash-v1`, and `namespace-proportional-stable-sha256-v1`. Explicit no-verifier mode is recorded as `explicit_lexical_only_v1`.
- 2026-07-29: Focused semantic/model tests passed (20 tests); evidence snapshot regressions passed (37 tests); full repository discovery passed (903 tests, 39 skipped).
- 2026-07-29: The 500-row fake structural run measured 3,000 candidates, 3,000 concepts, 3,000 mentions, 0 taxonomy rows, 500 sequential model calls (maximum concurrency 1), 500 exact branch content queries, 19 remote write calls (five 100-row extraction batches, six 500-row concept batches, six 500-row mention batches, one empty taxonomy schema write, and one catalog-last write), 32,500 evidence UTF-8 bytes, 6,912,000 derived bytes, 846 manifest bytes, observed max RSS 90,226,688, and catalog-last completion. Semantic logical hash: `5b4f5106dc7e1f78dfe7efb8df02c48f56967830c988873e3c93ca7136429e2f`.
- 2026-07-29: Ticket remains active pending independent required review; CLI/docs/live-provider work remains explicitly excluded.
- 2026-07-29: Repaired all supported findings from two independent fail reviews. Normal builds now run separate production local-model merge, taxonomy-proposal, and taxonomy-verification prompts; strict repair carries only a bounded private invalid output into the next in-memory prompt; exact candidate support is revalidated on resume; generic filler is rejected; SSO/customer-process aliases merge only after verifier judgment; ambiguous deployment senses remain distinct; confidence uses actual verifier scores and cannot accept raw extraction confidence alone; alias/canonical collisions receive close-match disposition; taxonomy alternatives re-canonicalize/re-deduplicate; and global hierarchy depth, parent, cycle, status, and representative-mention bounds fail closed.
- 2026-07-29: Hardened remote lifecycle with active exact evidence attributes/provenance, byte checks before model calls, per-call/stage wall guards, bounded staging materialization, content/input hash and exact excerpt resume checks, conditional first writes for every final row, exact final namespace schema/hash/count scans immediately before catalog-last finalization, and completed-build reuse hash/count validation. No source/evidence-branch write path or local corpus persistence was introduced.
- 2026-07-29: Added targeted regressions for private repair payloads, generic nouns, SSO aliases, customer implementation/onboarding, ambiguous deployment senses, actual confidence breakdown/statuses, taxonomy alternatives/duplicates/overlong mention bases, resume content drift, pre-model row/byte limits, explicit sampling, conditional-write races, and post-write mutation detection.
- 2026-07-29: Post-repair validation passed 49 semantic core tests, 127 focused semantic/evidence/catalog tests, and full discovery on rerun (909 tests, 39 skipped). The first full run had one transient existing 100,000-row applied-state identity race; the isolated test and immediate full rerun passed. Current 500-row measurement: 3,000 candidates, 2,999 concepts, 3,000 mentions, 75 provisional taxonomy rows, one accepted alias merge, 651 sequential local fake-model calls (maximum concurrency 1), 6,575 remote rows, approximately 7,562,942 remote JSON bytes, 7,560,137 derived bytes, 32,497 evidence bytes, 19 remote write calls, 847 local persistent bytes, 97,320,960 observed max RSS, 0.683170s fake wall time, and semantic hash `ca1d98be9570f83a0aa23e96cf063b2ad0d4b7b5ab346017a346fe1712403823`.
- 2026-07-29: Follow-up acceptance repair now requires accepted-threshold independent confidence before unioning same-concept candidates; medium same-concept judgments retain distinct concepts and carry a provisional close-match ceiling. Taxonomy verification is a direct publication gate, so medium judgments stay provisional and low judgments are rejected regardless of composite score. Rejected alternative edges no longer reserve a final deduplication key.
- 2026-07-29: Final concepts, mentions, and taxonomy rows now store hashes recomputed from their complete canonical persisted contents. Completion revalidates the evidence snapshot before exact final semantic scans, with only the hard deadline check between the last scan and conditional catalog write. Completed-build reuse exact-scans schemas/counts, recomputes every row hash and the global hash, and rejects content mutation even when a stale stored hash is left unchanged.
- 2026-07-29: Resume discovery now scans IDs only to reject extras, fetches each selected staging row by bounded exact-ID query, and charges the full canonical staging row against the derived-byte cap before retaining it. A hostile oversized scalar regression fails closed. The strengthened 500-row fixture observed 3,000 candidates, 2,900 concepts, 3,000 active-evidence mentions, four taxonomy rows covering accepted `broader`, `related`, and `close_match` plus a provisional relation, 1,325 sequential accounted model calls (maximum concurrency one), 19 bounded remote writes, 32,600 evidence bytes, 7,424,226 derived bytes, 846 local persistent manifest bytes, 97,386,496 observed max RSS, 0.794561s fake wall time, and semantic hash `75abe1ae9c4199aafe95ece0ce70539dc4fd997acf438fefd5fcc30122ce640f`.
- 2026-07-29: Acceptance-repair validation passed 62 focused semantic tests, 43 evidence snapshot regressions, `git diff --check`, and full discovery with 916 tests passing and 39 skipped. No network, live model, hosted inference, turbopuffer credential, source/evidence-branch write, or local corpus artifact was used.

- 2026-07-30: Fresh independent acceptance review passed the repaired semantic core with no blocker or significant finding; ticket closed after parent-observed focused/full validation and retrospective review.
