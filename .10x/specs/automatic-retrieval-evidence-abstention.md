Status: active
Created: 2026-08-14
Updated: 2026-08-14
Decision: .10x/decisions/buoy-owns-automatic-retrieval-evidence-abstention.md

# Automatic Retrieval Evidence Abstention

## Scope and compatibility

This contract extends only automatic retrieval after namespace routing and
content retrieval. Explicit single- and multi-namespace retrieval, catalog
selection, content schemas, provider state, and the three-namespace maximum are
unchanged. Automatic preview remains content-query-free and MUST report that an
evidence decision cannot occur until live retrieval.

## Evidence observation

The assessor scores the first up to five hits from the exact final ranking that
automatic retrieval would otherwise return, never beyond the requested global
`top_k`, using the pinned
`cross-encoder/ms-marco-MiniLM-L-6-v2` revision
`c5ee24cb16019beea0893ab7796b1df96625c6b8`. Multi-corpus retrieval reuses the
scores already produced for ranking. Automatic single-corpus retrieval scores
its returned hits without changing their order. Explicit retrieval never loads
the model for this purpose.

An evidence observation records at least the finite top score, second score
when present, score gap when present, candidates scored, route selection reason,
route semantic score and margin, namespace failure count, model identity, and
calibration identity. Empty successful retrieval is an exact weak observation.
Provider/model errors are redacted and MUST NOT leak credentials, response
content, or exception chains.

## State transition

For an initial automatic fanout of one:

1. strong evidence returns the existing single-namespace result;
2. weak evidence widens once to the remaining routed candidates, using fallback
   reason `weak_top1`;
3. empty or failed retrieval retains `empty_top1` or `failed_top1` widening.

After the final attempted route:

- strong evidence produces `supported` and returns normal hits;
- weak evidence with no namespace failure produces `no_relevant_evidence`, an
  empty hit list, and a successful command result;
- weak evidence with any namespace failure produces `inconclusive`, an empty
  hit list, `incomplete=true`, and the existing attributed failure summaries;
- every namespace failing remains a retrieval error rather than an evidence
  outcome.

The public text is “No sufficiently relevant evidence was found in the indexed
corpora.” It MUST NOT claim that no answer exists. JSON adds an `evidence`
object with `mode`, `status`, `reason`, model/revision, calibration ID/revision,
threshold, observed score features, candidates scored, and whether widening
was triggered by weak evidence. Raw content is never added to diagnostics.

## Collection and shadow boundary

The packaged artifact is initially collect-only. Live automatic JSON and the
governed evaluator record the bounded score features needed to select a
threshold, preserve existing hits, and report `unassessed`; ordinary text
retrieval does not pay for a discarded collect-only observation. The loader and
calibrated assessor MUST reject shadow and active artifacts until a later
reviewed change implements exact runtime and certification-report binding.

After that separate gate exists, shadow may compute the full decision while
preserving hits and reporting `would_support`, `would_abstain`, or
`would_be_inconclusive`. Active additionally requires exact owner approval and
passing bound quality gates. Missing, malformed, incompatible, stale, or
unapproved active calibration state MUST fail rather than inventing or applying
a threshold.

## Calibration and quality gates

Candidate judgments use query-level evidence labels derived from reviewed hit
grades: `0` unrelated, `1` topically related but not useful, and `2` materially
useful evidence. Only grade `2` is support. Calibration and certification split
by question, never by returned row.

The governed basket MUST materially exceed the five historical no-answer
cases and cover every active source type. It includes answerable questions,
obvious out-of-domain questions, adjacent-but-absent questions, named-corpus
but absent questions, false premises/entity swaps, static-versus-live requests,
and difficult answerable questions with weak lexical overlap.

An active artifact requires all of:

- false-evidence risk among accepted certification queries at most `0.05`;
- at least `0.95` of the pre-gate answer-bearing Recall@5 retained;
- at least `0.90` of reviewed no-answer certification queries abstained;
- no source kind has false-evidence risk or retained-recall regression more
  than `0.05` worse than the aggregate when its sample is large enough to
  report;
- automatic fanout remains at most three and all existing multi-corpus gates
  remain passing.

Threshold selection maximizes answerable coverage subject to the false-evidence
risk gate on calibration data. The locked certification split is evaluated
once after selection and cannot tune the same artifact. The report includes a
risk-coverage curve and exact confusion counts; no passing percentage may hide
an empty or too-small denominator.

## Effects and failures

Evaluation may make read-only catalog and content queries through the existing
query-only collector boundary. It performs no provider mutation. Cross-encoder
or calibration failure in active mode fails automatic retrieval. Shadow-mode
assessment failure is surfaced in diagnostics but preserves the pre-gate
result, so shadow evaluation cannot silently become production authority.
