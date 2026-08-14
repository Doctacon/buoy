Status: active
Created: 2026-08-14
Updated: 2026-08-14
Depends-On: .10x/tickets/2026-08-13-implement-automatic-multi-corpus-retrieval.md
Decision: .10x/decisions/buoy-owns-automatic-retrieval-evidence-abstention.md
Specification: .10x/specs/automatic-retrieval-evidence-abstention.md

# Instrument Automatic Retrieval Evidence Abstention

## Outcome

Establish the safe collect-only instrumentation and deterministic calibration
machinery needed to prevent automatic retrieval from returning
nearest-but-irrelevant evidence. This ticket does not activate suppression.

## Scope

- Reuse the pinned local MiniLM scorer for automatic evidence assessment.
- Preserve explicit namespace retrieval exactly.
- Add weak-singleton widening and the governed evidence JSON/text contract.
- Add a versioned collect-only artifact and deterministic offline
  calibration/certification tooling. Shadow and active artifacts remain
  mechanically rejected.
- Connect read-only evidence score collection to separately reviewed
  question-level labels without creating or approving those labels here.
- Update retrieval docs, changelog, evidence, and independent review records.

## Acceptance

- Automatic JSON/evaluator collection records content-free observations while
  preserving existing hits and ranking; ordinary text retrieval avoids the
  collect-only model cost.
- The dormant state-transition seam is tested for bounded weak singleton
  widening and honest no-relevant/inconclusive outcomes, but no packaged
  artifact can activate it.
- Explicit single/multi retrieval does not load the evidence assessor and keeps
  its existing output contract.
- Packaged loading rejects shadow/active artifacts pending a separately reviewed
  runtime-binding and certification-report implementation.
- Calibration/certification metrics use question-level splits without changing
  labels after threshold selection.
- Python 3.11/3.13 focused and full suites, lock/release validators,
  distribution smoke, and diff check pass.

## Owned paths

- `src/buoy_search/{cross_encoder,retriever,routing,cli,multi_corpus_evals,evidence,evidence_evals}.py`
- versioned packaged evidence-calibration data and its loader
- `scripts/evaluate_multi_corpus_retrieval.py` and bounded calibration tooling
- `scripts/release_automation.py` package-boundary validation
- focused retrieval, CLI, calibration, evaluator, and compatibility tests
- `README.md`, `docs/retrieval.md`, `docs/releasing.md`, `CHANGELOG.md`
- this ticket's decision, specification, evidence, and review records

## External effects

Tests are local. Governed evaluation may use the existing process environment
credential for read-only Turbopuffer inventory, catalog, and content queries.
No content/catalog row, namespace, API key, release, branch protection, or
other provider state may be changed. No remote model download is allowed.

## Exclusions

LLM or remote evidence judges, learned/hierarchical routing, routing-card
mutation, new namespace/card formats, content reindexing, source-adapter work,
answer generation, provider deletion, release publication, and unrelated
ranking changes.

## Progress

- 2026-08-14: User explicitly authorized implementation after reviewing the
  proposed post-retrieval evidence-gate design. Created isolated branch
  `work/automatic-retrieval-abstention` from merged `origin/develop`
  `9cd80752953e4f48ade343832de8d1e8cfd65f9f`.
- 2026-08-14: Implemented the collect-only automatic evidence observation,
  dormant state-transition seam, strict artifact loader, offline calibration
  math, evaluator integration, explicit-retrieval isolation, and public
  diagnostics. Shadow and active remain mechanically rejected.
- 2026-08-14: Completed one read-only 50-case diagnostic collection from the
  dirty candidate tree. All 50 observations were `unassessed`, none failed,
  and the report contained no question, query, passage, content, vector,
  credential, token, or API-key field. This is diagnostic evidence only, not a
  trusted release or activation artifact.
- 2026-08-14: Final validation passed on the current `origin/develop`: 186
  focused and 671 full-suite tests on each of Python 3.11 and 3.13, locked
  dependency/source/ranking/tokenizer validators, archive inspection,
  clean-wheel CLI/module/tokenizer/calibration smoke, and diff check.

## Blockers

- A materially larger mixed answerable/no-answer key with reviewed useful-
  evidence labels and frozen calibration/certification splits does not yet
  exist.
- No candidate threshold, locked certification report, source-kind sample
  sufficiency result, or runtime binding verifier exists.
- Future shadow/active CLI wiring must assess ordinary automatic text output;
  the current collect-only assessor is intentionally attached only to JSON and
  the governed evaluator so discarded observations do not add user latency.
- A later ticket and code review must authorize shadow; owner review/approval of
  the exact passing certification artifact is additionally required for active.
