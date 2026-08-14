Status: done
Created: 2026-08-14
Updated: 2026-08-14
Depends-On: .10x/tickets/2026-08-13-implement-automatic-multi-corpus-retrieval.md
Decision: .10x/decisions/buoy-owns-automatic-retrieval-evidence-abstention.md
Specification: .10x/specs/automatic-retrieval-evidence-abstention.md

# Activate Automatic Retrieval Evidence Abstention

## Outcome

Applied a provisional `-8.0` best-hit relevance cutoff so automatic retrieval
does not present nearest-but-irrelevant evidence as useful results. The owner
knowingly authorized this starting point despite the limited five-no-answer
diagnostic sample; monitoring and broader calibration remain follow-up work.

## Scope

- Reuse the pinned local MiniLM scorer for automatic evidence assessment.
- Preserve explicit namespace retrieval exactly.
- Apply the gate to automatic text and JSON retrieval.
- Add weak-singleton widening and the governed evidence JSON/text contract:
  complete weak results become `no_relevant_evidence`; weak results with a
  namespace failure become `inconclusive`.
- Package `automatic-retrieval-evidence-v1` revision
  `owner-approved-provisional-minus-8-v1` as an owner-approved active artifact
  with a `-8.0` cutoff and no CLI, environment, or runtime override, and retain
  deterministic offline calibration/certification tooling.
- Connect read-only evidence score collection to separately reviewed
  question-level labels without creating or approving those labels here.
- Update retrieval docs, changelog, evidence, and independent review records.

## Acceptance

- Automatic text, JSON, and evaluator retrieval use the same active cutoff and
  content-free diagnostics.
- Weak singleton retrieval widens at most once; complete weak results return no
  hits, while partial weak results are explicitly inconclusive.
- Explicit single/multi retrieval does not load the evidence assessor and keeps
  its existing output contract.
- The packaged active artifact is strict, owner-approved, and model/feature
  bound; malformed or incompatible configuration fails closed.
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
  diagnostics. At that first phase, shadow and active were mechanically
  rejected.
- 2026-08-14: Completed one read-only 50-case diagnostic collection from the
  dirty candidate tree. All 50 observations were `unassessed`, none failed,
  and the report contained no question, query, passage, content, vector,
  credential, token, or API-key field. This is diagnostic evidence only, not a
  trusted release or activation artifact.
- 2026-08-14: Final validation passed on the current `origin/develop`: 186
  focused and 671 full-suite tests on each of Python 3.11 and 3.13, locked
  dependency/source/ranking/tokenizer validators, archive inspection,
  clean-wheel CLI/module/tokenizer/calibration smoke, and diff check.
- 2026-08-14: The owner explicitly approved activating a provisional `-8.0`
  cutoff after being told that the observed category separation included only
  five no-answer questions. Activation work extends the gate to automatic text
  and JSON output; the prior collect-only validation remains historical until
  the active delta is revalidated.
- 2026-08-14: Adversarial review clarified that the threshold separates
  `answer_expected` from `no_answer` question categories, not useful from
  irrelevant returned passages. It accepts the known unrelated
  `d11-vector-recall-debug` result at `-5.8328`; the incomplete judged-URL/group
  signal is TP30, FP15, FN0, TN5 at `-8.0`.
- 2026-08-14: Final active-delta validation passed: `677/677` complete-suite
  tests on both Python 3.11 and 3.13, `43/43` final reviewer-focused tests,
  `56/56` evaluator regression tests, and the lock, source, ranking, C6, and
  diff checks.
- 2026-08-14: The wheel and source archive validated with SHA-256
  `6d662bd0eea974e79ecf741ad57985eb9c10e0d52676355754fabeda427c1661`
  and `992874d71a6b8b5f294211cc2b96d4e7a8682b82f7f82827de15d1133aff4ab5`
  respectively. A clean wheel install passed active-artifact, package-data,
  tokenizer, help, and import smoke.
- 2026-08-14: Read-only live wheel smoke verified complete no-evidence,
  supported automatic, explicit bypass, and plain-text wording paths without
  provider writes. Independent final review passed with the known `d11` false-
  support and incomplete judged-signal limitations retained.

## Follow-up and residual risk

- A materially larger mixed answerable/no-answer key with reviewed useful-
  evidence labels and frozen calibration/certification splits does not yet
  exist.
- The `-8.0` cutoff is provisional and versioned; it is not supported by a
  locked certification report or sufficient source-kind sample. Changing it
  requires a new reviewed packaged revision.
- Monitor false rejections and irrelevant acceptances, expand the reviewed
  sample, then calibrate and certify a stable default. Do not describe the
  historical category separation as passage relevance or a proven error rate.
