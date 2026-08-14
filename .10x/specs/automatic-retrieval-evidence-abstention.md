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

## Provisional active threshold

The packaged `automatic-retrieval-evidence-v1` artifact uses revision
`owner-approved-provisional-minus-8-v1`, `mode=active`,
`owner_approved=true`, and the threshold `-8.0` for the pinned
model and `cross_encoder_top_score_threshold_v1` feature contract. The top
score is a raw model value, not a probability. Scores below the threshold are
weak; scores at or above it are supported. Empty successful retrieval is weak.
The CLI, environment, and runtime MUST NOT provide a threshold override. Any
cutoff change requires a new reviewed packaged revision.

Both ordinary text and JSON automatic retrieval MUST apply the same artifact
and decision. The governed evaluator records the same content-free observation
and decision. Explicit single- and multi-namespace retrieval MUST bypass the
artifact, assessor, widening rule, and suppression behavior.

The project owner explicitly approved this threshold on 2026-08-14 after being
informed that it came from one 50-question diagnostic with only five no-answer
questions. Those five top scores ranged from `-11.2867` through `-9.6270`; the
45 `answer_expected` questions scored `-5.8328` or higher. This is a separation
of dataset question categories, not proof that accepted passages are relevant.
The `d11-vector-recall-debug` counterexample is accepted at `-5.8328` despite
returning unrelated passages for its Turbopuffer recall question. This is a
provisional owner-directed activation, not a probability estimate, locked
certification result, or claim that the small sample establishes future error
rates. Missing, malformed, incompatible, or unapproved active configuration
MUST fail rather than silently bypassing or inventing a threshold.

## Calibration and quality gates

Candidate judgments use query-level evidence labels derived from reviewed hit
grades: `0` unrelated, `1` topically related but not useful, and `2` materially
useful evidence. Only grade `2` is support. Calibration and certification split
by question, never by returned row.

The monitoring and stable-calibration basket MUST materially exceed the five
historical no-answer cases and cover every active source type. It includes
answerable questions,
obvious out-of-domain questions, adjacent-but-absent questions, named-corpus
but absent questions, false premises/entity swaps, static-versus-live requests,
and difficult answerable questions with weak lexical overlap.

Promotion of the provisional cutoff to a formally calibrated stable default
requires all of:

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
an empty or too-small denominator. The provisional `-8.0` activation does not
claim that any of these stringent certification gates passed.

## Effects and failures

Evaluation may make read-only catalog and content queries through the existing
query-only collector boundary. It performs no provider mutation. Cross-encoder
or calibration failure in active mode fails automatic retrieval. Monitoring
must report false rejections, irrelevant acceptances, outcome counts, source
mix, and fanout so the provisional cutoff can be reviewed and changed.
