Status: active
Created: 2026-08-14
Updated: 2026-08-14
Amends: .10x/decisions/buoy-owns-bounded-multi-corpus-retrieval.md

# Buoy Owns Automatic Retrieval Evidence Abstention

## Context

Bounded multi-corpus routing reliably chooses likely content namespaces, but a
nearest-neighbor query always returns the closest rows even when none is useful
evidence. The approved live basket demonstrated this failure mode: every
reviewed no-answer query returned unrelated hits. Route confidence answers
which corpus is closest; it cannot establish that the indexed content supports
the question.

## Decision

Buoy owns one bounded post-retrieval evidence decision for automatic retrieval.
It reuses the exact pinned local MiniLM cross-encoder already required for
multi-corpus reranking and does not add an LLM, remote judge, provider write, or
new namespace.

Automatic retrieval may produce exactly these evidence outcomes:

- `supported`: at least one returned hit satisfies the approved calibrated
  evidence contract, so normal ranked hits are returned;
- `no_relevant_evidence`: every required content query succeeded but no
  returned hit satisfies that contract, so no hits are returned; or
- `inconclusive`: evidence is weak and at least one required content query
  failed, so Buoy cannot safely claim that the searched corpus set lacks
  evidence.

A weak high-confidence single-corpus result widens once to the next two routed
candidates before the final evidence decision. Empty and failed single-corpus
widening remains intact. Fanout stays bounded at three.

Explicit `--namespace` retrieval remains the deterministic raw-search bypass
and does not suppress results through this automatic evidence gate.

## Calibration and activation

Raw cross-encoder logits and routing scores are not probabilities. No guessed
constant may activate abstention. The evidence decision MUST be calibrated on
an owner-reviewed basket containing answerable, adjacent-but-absent, named-
corpus-but-absent, false-premise, static-versus-live, and out-of-domain
questions. Calibration and certification questions are separated by question,
and the immutable calibration artifact is bound to the exact reranker,
retrieval, source-mix, dataset, and evaluator revisions.

Before a candidate threshold exists, governed JSON/evaluation collection records
bounded score observations without making a decision. Production remains
collect-only: the packaged loader and calibrated assessor reject every shadow or
active artifact. Enabling shadow requires a later reviewed code change that
verifies exact runtime, dataset, evaluator, source-mix, and certification-report
bindings. Active additionally requires owner approval and passing locked gates.
Approval of this decision authorizes collect instrumentation and read-only
evaluation, not self-approval of ground truth or activation of an unvalidated
threshold.

## Consequences

Automatic single-corpus JSON/evaluator collection may now load the pinned
cross-encoder to observe the hits it would return. This adds bounded local
latency to build calibration evidence while preserving every hit; ordinary
text retrieval skips the collect-only work. Avoiding nearest-but-irrelevant
evidence is a later active-mode benefit, not behavior authorized by this
collect-only change. Explicit retrieval retains its existing lightweight
compatibility path.

`no_relevant_evidence` means only that Buoy did not find sufficiently relevant
evidence in the successfully searched indexed corpora. It MUST NOT be phrased
as proof that an answer does not exist. Provider failures, incomplete catalog
coverage, model failure, or corrupt calibration state fail in the safe
direction and never become a false no-answer claim.
