Status: active
Created: 2026-08-13
Updated: 2026-08-15
Decision: .10x/decisions/buoy-owns-bounded-multi-corpus-retrieval.md
Amended-By: .10x/specs/scalable-routing-quality.md

# Automatic Multi-Corpus Retrieval

## Catalog contract

Buoy MUST reuse `buoy-routing-catalog-v1` and its existing schema-v1 card rows.
One card represents one live content namespace and contains validated source,
semantic, embedding, ranking, lineage, enablement, revision, and pinned
384-dimensional BGE routing-vector fields. `buoy-routing-catalog-v1` and
`buoy-evidence-*` are reserved control-plane namespaces and MUST NOT become
content candidates.

The inactive scalable-routing amendment adds new-reader support for exact
schema v1 and exact additive schema v2. Schema v2 adds the four-field prototype
bundle defined by `.10x/specs/scalable-routing-quality.md`:
`routing_examples`, `routing_prototype_hash`, `routing_prototype_vector`, and
`routing_prototype_vector_hash`. It does not authorize a live schema write or
alter current production routing. The exact projection, shortlist, reranker,
calibration, activation, and reader-first migration contract is governed by
that scalable-routing spec.

Automatic routing requires a card for every live content namespace. Disabled
cards count as intentionally covered but are not eligible. Missing, stale,
disabled, and incompatible state MUST be reported; missing or corrupt coverage
MUST fail automatic routing before content queries. Stale cards are never
automatically removed.

Approved apply creates or updates its generated card only after successful
content and local-state commit. Existing manual title, summary, aliases, tags,
vector, and enabled state survive generated updates. A failed post-apply card
write is explicit partial success and is repaired by a fresh reviewed apply or
catalog operation; it MUST NOT roll back content or claim catalog success.

Catalog list/show are read-only. Upsert/enable/disable preview by default and
require `--approve`. No catalog operation deletes or mutates a content
namespace.

## Route selection

Explicit unique repeatable `--namespace` values bypass listing, catalog reads,
and route-model work. A single explicit namespace preserves the current text
and JSON contract. Explicit preview remains credential- and provider-free.

Without `--namespace`, Buoy strongly reads the live inventory and complete
catalog, applies compatibility gates, and scores enabled cards using normalized
title/alias phrase matches plus the pinned
`BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`
semantic projection.

- One unique title/alias match selects that namespace.
- Two or three named cards select those cards in deterministic route order.
- More than three named cards fail with an explicit-selection instruction.
- Otherwise semantic top-1 selects one only when its cosine score is at least
  `0.65` and exceeds top-2 by at least `0.05`.
- Every other route selects the semantic top three, or all eligible cards when
  fewer than three exist.

These score and margin thresholds remain production authority until the
scalable-routing candidate has human-approved canaries, passes its locked
quality gates, and receives an explicit owner-approved packaged activation.
Exact-name behavior and the three-namespace maximum survive that amendment.

Automatic preview performs only inventory/catalog reads and local route
embedding. It MUST report selected cards, scores, confidence/margin, coverage,
and expected fanout, and MUST NOT query content or write state.

## Retrieval and reranking

Live retrieval embeds the content query once and queries at most three selected
namespaces with at most three workers. Each namespace retains existing
ANN+BM25+within-namespace RRF and source-aware file/page ranking. A selected
namespace contributes at most its top eight hits.

A successful one-namespace route returns directly without loading a reranker.
An empty or failed one-namespace route widens exactly once to the next two
route candidates. Multi-namespace retrieval preserves successful namespaces;
failures are redacted, attributed, and mark the response incomplete. If every
selected namespace fails, retrieval fails.

Before global ranking, exact duplicate candidates are collapsed by canonical
citation, section, and content identity. At most 24 candidates are scored by
`cross-encoder/ms-marco-MiniLM-L-6-v2` pinned to revision
`c5ee24cb16019beea0893ab7796b1df96625c6b8`. The model input is query paired
with bounded title, section path, and content text. Raw model scores are
converted to a deterministic one-based cross-encoder ordinal rank; equal raw
scores break by route rank, namespace-local rank, namespace, then stable ID.
The global score is fixed equal-weight ordinal reciprocal-rank fusion with
`k=60`:

`1 / (60 + cross_encoder_rank) + 1 / (60 + namespace_local_rank)`

The resulting order breaks exact fused-score ties by cross-encoder rank, route
rank, namespace-local rank, namespace, then stable ID. No raw provider score,
raw route score, or route-score-derived weight enters the fused score. Route
rank is used only as a deterministic tie-breaker. This preserves useful local
retrieval evidence while retaining MiniLM's query-specific relevance signal.
When the requested global `top_k` can represent every nonempty successful
namespace, the final set MUST include that namespace's existing local-rank-one
candidate. If fused top-k omitted a namespace, its local-rank-one candidate
replaces the worst selected candidate from a namespace that still retains more
than one result; returned hits remain ordered by the fixed fused ranking. The
promotion and whether full namespace coverage was possible MUST be reported in
JSON. If `top_k` is smaller than the nonempty namespace count, no hidden
replacement occurs and coverage is reported as impossible.
Model load or inference failure fails the multi-namespace request rather than
emitting a misleading unified order.
The loader MUST use the CPU, local cache only, safetensors only, and disabled
remote code with a fixed inference batch size of eight. It MUST NOT download or
substitute a model during retrieval.

Automatic and explicit-multi JSON include `namespaces`, `routing`, `reranking`,
per-hit `namespace`, per-namespace summaries, `incomplete`, and attributed
failures. Applied multi-namespace reranking reports the fixed method,
components, `k`, and tie-break sequence. Each hit's `score_info` reports route
rank, namespace-local rank, raw cross-encoder score and ordinal rank, both RRF
component scores, and the final fused score. The requested `top_k` is global.

## Evaluation gates

The feature MUST pass a human-reviewed 50-query basket with exactly 20
unambiguous named-source cases, 15 descriptor-free/confusable cases, 10
multi-corpus cases, and 5 no-answer cases. A candidate basket MUST retain
`human_approved_ground_truth=false`; it cannot satisfy the release gate until a
human reviews it against current indexed content.

The repository owner explicitly approved the fixed checked-in 50-query answer
key on 2026-08-13. The approved transition changes only the approval flag,
review status, and approval note; the questions, judgments, answer groups, and
thresholds remain unchanged.

All five current physical content namespaces MUST have cards. Four logical
corpora are enabled and eligible; the duplicate Dagster benchmark card is
disabled, counts as covered, and MUST never appear in an expected route,
relevance judgment, or scored hit.

The gates use these exact definitions:

- Route recall@3 is micro required-namespace recall over the 45 answer-bearing
  cases after truncating each automatic route to its first three namespaces. It
  MUST be at least 0.95.
- Complete multi-corpus route coverage means all expected namespaces occur in
  those first three routes for every one of the 10 multi-corpus cases.
- An initial high-confidence one-namespace route is incorrect unless its
  singleton is exactly the case's required namespace set. That initial
  decision remains scored even when empty/failed retrieval widens the final
  attempted route; the incorrect count MUST be zero.
- Each answer-bearing case defines required answer/facet groups. Judged URLs
  that independently satisfy the same information need share one group;
  complementary facts remain separate required groups. A group is available
  when exhaustive retrieval finds any judged member, and a result recalls the
  group when its top five contains any member. A group receives credit at most
  once, so equivalent pages neither inflate the denominator nor earn duplicate
  gain.
- Automatic Recall@5 is micro recall over exhaustive-available required groups
  across all 45 answer-bearing cases. It MUST be at least 0.95.
- Reranking nDCG@5 is macro-averaged across the 10 multi-corpus cases. The
  first returned member of an available group earns that group's fixed gain;
  later equivalent members earn zero. The pre-rerank comparison interleaves
  namespace-local results by local rank and route rank instead of concatenating
  whole namespaces. Pinned MiniLM plus the fixed ordinal fusion MUST improve
  nDCG@5 by at least 0.03 over that comparison.
- Pre- and post-rerank Recall@5 are micro-averaged over exhaustive-available
  required groups in the multi-corpus cases. Reranking MUST NOT reduce
  Recall@5.
- Average automatic fanout is the final route count averaged over all 50 cases,
  including no-answer cases. It MUST be no greater than 2.0.

Provider-backed evaluation is read-only. No content row, namespace, API key,
stale row, or release state may be changed by validation.

A qualifying live report MUST be produced by the checked-in collector and bind
the canonical dataset digest, clean source commit and tree, catalog snapshot,
model revisions and runtime configuration, evaluator digest, and collector
invocation. Offline validation may recompute a report but cannot establish live
provenance. The collector exposes query-only content adapters and MUST record
that provider mutation methods were structurally unavailable; logical call
counts are not provider audit telemetry.

Live provenance is a structural in-process collector assertion, not a
cryptographic attestation. Only the collector's private immediate evaluation
path may satisfy it, after independently matching the recorded values to the
current clean checkout and the collector's exact runtime facts. Public library
evaluation, fixture mode, and `validate-run` MUST always treat saved live
provenance as untrusted: they may revalidate shape and recompute every metric,
but can never restore `provider_backed_live_run=true` from a JSON file.
