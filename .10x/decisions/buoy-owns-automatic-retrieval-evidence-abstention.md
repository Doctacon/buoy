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

Raw cross-encoder logits and routing scores are not probabilities, and a cutoff
is not portable across models. The first governed 50-question diagnostic
observed a category gap: its five `no_answer` questions had top scores from
`-11.2867` through `-9.6270`, while its 45 `answer_expected` questions scored
`-5.8328` or higher. Those categories describe whether the dataset expects an
answer somewhere in the corpora; they do not establish that an accepted
passage is relevant.

On 2026-08-14, after being told that only five no-answer examples supported
that gap, the project owner explicitly authorized `-8.0` as a provisional
active cutoff. The earlier collect-only pause is lifted narrowly for this
owner-directed starting point. The versioned cutoff is bound to the exact
pinned reranker and feature contract. It has no CLI, environment, or runtime
override and may change only through a new reviewed packaged revision. A score
below `-8.0` is weak; a score at or above it is supported.

This authorization is not locked calibration or certification, and the
historical run MUST NOT be represented as proving an error rate. A broader
reviewed basket containing answerable, adjacent-but-absent, named-corpus-but-
absent, false-premise, static-versus-live, and out-of-domain questions remains
required to measure false rejections and irrelevant acceptances. The threshold
must be monitored and revised if that evidence shows regressions.

The known residual risk is material. `d11-vector-recall-debug` scored `-5.8328`
and is accepted by `-8.0`, but returned unrelated Dagster, Oscilar, and Thistle
passages for a Turbopuffer exact-versus-ANN recall question. The incomplete
judged-URL/group signal yields TP30, FP15, FN0, and TN5 at this cutoff, so it
flags 15 of 45 accepted questions while possibly counting useful unjudged
alternates as false positives. Neither the category gap nor that incomplete
signal may be described as passage-level certification.

## Consequences

Automatic text and JSON retrieval now load or reuse the pinned cross-encoder
and apply the provisional evidence rule. A weak high-confidence singleton
widens once before the final decision. A complete weak search returns no hits;
a weak search with any namespace failure is inconclusive. Explicit retrieval
retains its existing lightweight compatibility path and bypasses the gate.

`no_relevant_evidence` means only that Buoy did not find sufficiently relevant
evidence in the successfully searched indexed corpora. It MUST NOT be phrased
as proof that an answer does not exist. Provider failures, incomplete catalog
coverage, model failure, or corrupt calibration state fail in the safe
direction and never become a false no-answer claim.
