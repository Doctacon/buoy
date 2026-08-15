Status: active
Created: 2026-08-15
Updated: 2026-08-15
Decision: .10x/decisions/buoy-uses-bounded-prototype-routing.md
Amends: .10x/specs/automatic-multi-corpus-retrieval.md, .10x/specs/namespace-routing-card-contract.md

# Scalable Routing Quality

## Scope and inactive starting state

This contract improves only automatic namespace routing. Explicit namespace
selection, content schemas, content ranking, evidence abstention, cross-corpus
result fusion, and the maximum content fanout of three remain unchanged.

The implementation starts inactive. The packaged routing-confidence artifact
has collect/candidate status, no active thresholds, and no authority to change
ordinary automatic selection. Candidate evaluation may exercise the new path
through a purpose-built route-only boundary. Activation requires the human and
quality gates below plus a separate reviewed artifact revision. No feature
flag, environment variable, or CLI value can bypass that rule.

## Catalog schema and compatibility

The only routing authority remains exact namespace
`buoy-routing-catalog-v1`. One card ID continues to represent one target
content namespace. No prototype row, sentinel row, second namespace, or
content-namespace metadata row is permitted.

New readers accept exactly two normalized remote schemas:

- schema v1 is the existing exact schema and existing card fields;
- schema v2 is schema v1 plus the exact four-field prototype bundle:
  `routing_examples={type:"[]string",filterable:false}`,
  `routing_prototype_hash={type:"string",filterable:false}`,
  `routing_prototype_vector={type:"[]float",filterable:false}`, and
  `routing_prototype_vector_hash={type:"string",filterable:false}`. The
  ordinary prototype vector has no ANN index.

No other missing, extra, renamed, retyped, or reindexed field is compatible.
The version names are Buoy application contracts; no new stored schema-version
attribute is added. A schema-v1 row reconstructs the complete empty-example
bundle from its base projection. A schema-v2 row whose provider-null values
omit all four fields is normalized the same way: examples become `[]`, the
prototype hash becomes `semantic_hash`, the prototype vector becomes `vector`,
and its hash becomes `vector_hash`. Any partial bundle fails closed. Every
newly written schema-v2 row includes all four fields.

`routing_examples` contains zero through eight non-empty strings of at most
512 Unicode code points each. Values use
the existing Unicode NFKC/case-fold/alphanumeric-and-whitespace canonical key
for duplicate detection and deterministic sorting. Examples may equal neither
one another nor an empty canonical value. They do not become aliases or tags
and cannot trigger the exact-name path.

Manual catalog upsert exposes a repeatable `--routing-example` option. A
schema-v1 catalog may preview a non-empty example edit but approval fails with
an explicit reader-first-migration requirement; it MUST NOT add the remote
field incidentally. When schema v1 is observed, ordinary apply/catalog writes
retain the exact v1 schema and require an empty example list. When schema v2 is
observed, writes retain exact v2.

Approved apply treats routing examples as reviewed manual semantic fields.
Generated cards default to an empty example list because verified plan-level
source identity does not establish product capabilities. Existing manual
title, summary, aliases, tags, `routing_examples`, semantic origin, projection,
and enabled state survive a generated refresh. A reviewed manual edit may
replace the complete example list and recompute the projection.

## Exact prototype projection

The base passage and BGE query prefix remain exactly those in the existing
card contract. Canonically sorted examples produce passages in this exact
form, with no trailing newline:

```text
Title: <title>
Summary: <summary>
Routing example: <example>
```

The legacy `semantic_hash`, ANN-indexed `vector`, and `vector_hash` always
remain the exact base-passage representation defined by the existing card
contract, whether or not examples exist. The separate prototype projection's
ordered passage list is the base passage first, followed by example passages
in canonical stored order. Every passage is encoded
separately by
`BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`
with normalized float32 output and no query prefix. The ordinary, non-indexed
`routing_prototype_vector` is:

1. the exact base-passage vector when the example list is empty; or
2. the arithmetic coordinate-wise mean of all passage vectors, normalized to
   unit length, when one or more examples exist.

With no examples, `routing_prototype_hash`, `routing_prototype_vector`, and
`routing_prototype_vector_hash` equal their base counterparts exactly. With
examples, `routing_prototype_hash` is the stable hash of:

```json
{
  "passage_texts": ["<exact base>", "<exact example>", "..."],
  "projection": "separate_prototype_vector_normalized_mean_v1",
  "routing_contract": "<the existing exact routing contract object>"
}
```

`routing_prototype_vector_hash=stable_hash(routing_prototype_vector)`.
Normalization tolerance, immutable model loading, finite-number validation,
and card-revision rules apply to both projections. Changing only an example
recomputes the prototype projection while preserving the exact base semantic
hash, vector, and vector hash.

## Candidate route execution

The complete live-inventory, card-coverage, schema, compatibility, enabled,
and stable-read gates run before relevance work exactly as today. The local
BGE query embedding is computed once.

The vector-shortlist operation uses only the complete eligible cards already
returned and validated by the existing two strong catalog passes. For every
eligible card, Buoy computes the exact dot product of its normalized
`routing_prototype_vector` and the normalized query vector. A non-finite score
fails routing. The current semantic/hybrid router continues to use only the
legacy base `vector`.
Cards sort by descending score and then namespace; the first
`min(12, eligible_count)` form the shortlist.

The result therefore contains no more than twelve unique eligible cards and
cannot introduce an identity or revision outside the authoritative snapshot.
The exact cosine value is reported as `shortlist_cosine_score`; it is not a
confidence probability. Shortlisting adds zero provider calls and never makes
one query per card. Existing paginated inventory, metadata, and strong catalog
reads remain fully accounted rather than being mislabeled as one request.

Exact-name behavior has priority:

- one complete normalized title/alias match remains route rank one; shortlist order
  supplies only its bounded fallback candidates;
- two or three named cards select exactly those cards;
- more than three named cards fails with explicit-selection guidance.

For uniform route-only observations, the evaluator's bounded diagnostic
shortlist prepends those already-validated exact-name cards and fills the
remaining positions from exact vector order, still capped at twelve. It may
score that diagnostic list but MUST derive the route from the exact-name rule;
the additional local score cannot change named production selection.

For a descriptor-free route, the pinned local
`cross-encoder/ms-marco-MiniLM-L-6-v2` revision
`c5ee24cb16019beea0893ab7796b1df96625c6b8` scores the question paired with
the base and example passages of every shortlisted card. Inference retains the
existing CPU-only, local-files-only, safetensors-only, no-remote-code, batch-
size-eight contract. At most twelve cards and at most nine passages per card
are scored.

Each card receives its maximum finite raw passage score. Equal passage scores
choose the base before examples and then the lowest example index. Cards sort
by descending maximum score, shortlist rank, then namespace. Routine route output
MUST NOT expose example text or vectors; it reports shortlist rank/score,
reranker rank/score, winning prototype kind/index/hash, model/calibration
identity, score margin, selection reason, and expected fanout.

When activated, a descriptor-free top card begins with fanout one only if its
raw maximum score and top-one/top-two score margin meet the exact packaged
thresholds. Otherwise the route begins with the first three reranked cards, or
all cards when fewer than three are eligible. The selected/fallback list never
contains more than three content namespaces. Model failure fails before any
content query.

## Confidence artifact and activation

The packaged artifact is named `automatic-routing-confidence-v2` and binds:

- artifact schema, revision, mode, and owner-approval state;
- exact BGE and MiniLM identities;
- schema-v1/v2 normalization contract;
- projection `separate_prototype_vector_normalized_mean_v1`;
- shortlist limit twelve and max examples eight;
- feature contract `max_prototype_score_and_margin_v1`, with
  `score_field=reranker_score` and `margin_field=reranker_margin`;
- canonical canary/calibration/certification digests and a semantic catalog
  digest over only namespace, enablement, title, summary, aliases, tags,
  routing examples, base and prototype vectors/hashes, and routing-model revisions;
- finite score and margin thresholds when active;
- the complete gate verdict and source commit.

The initial artifact has `mode=collect`, `owner_approved=false`, null
thresholds, and no activation authority. Calibration considers only observed
score and margin breakpoints plus an exact disable-singletons sentinel. It
chooses a pair with zero false confident singletons that maximizes correct
singleton count and then minimizes fanout; ties choose the higher score floor
and then the higher margin floor. A question cannot occur in both calibration
and certification. Certification is evaluated once on the gate split plus the
approved legacy 50-case projection and cannot tune the same revision.

The evaluator mechanically projects certification metrics to `split=gate`
and binds the separate calibration case IDs, count, thresholds, and zero-false-
singleton receipt. A `contrast_other` calibration case must include its
expected other corpus in the fallback three and must not rank the subject
corpus first; otherwise calibration fails before certification.

A descriptor-free singleton decision requires both an observed top score and
an observed finite top-one/top-two margin to meet their floors. A catalog with
only one eligible corpus has no margin and therefore remains on the bounded
fallback path unless the query names that corpus exactly.

An active artifact requires `mode=active`, `owner_approved=true`, compatible
exact contracts, finite thresholds, a clean bound source commit, an approved
canary digest, and a passing locked certification verdict. Missing, malformed,
incompatible, unapproved, or falsely active configuration fails closed; it
cannot silently select thresholds or fall back from an advertised active
strategy. Changing any bound input requires a new candidate and review.

## Per-corpus canaries and quality gates

Each onboarded corpus owns an exact five-case route-only canary pack:

- `named_self` on the gate split: one exact title or alias question;
- two `capability_self` questions, one on calibration and one on the gate
  split;
- `confusable_self` on the gate split, with confusing corpus IDs in
  `confusable_with`; and
- `contrast_other` on calibration, whose expected route is elsewhere and
  whose `confusable_with` includes the corpus under test.

Each case contains `id`, `role`, `split`, `question`,
`expected_namespaces`, and `confusable_with`. Pack metadata contains
`schema_version`, `corpus_id`, `namespace`, `review_status`,
`human_approved`, `route_contract_revision`, and
`canaries_disjoint_from_routing_examples`. Exact normalized duplicates of
stored routing examples are rejected mechanically; approval also records the
reviewer's assertion that semantic paraphrases were excluded. Candidate labels remain
`human_approved_ground_truth=false` until the repository owner reviews them
against the indexed corpora. A structurally complete candidate pack may be
collected and scored before approval, but an unapproved or empty category
cannot pass or supply activation authority.

Each case observation contains `case_id`, `corpus_scores`,
`reranker_margin`, ranked `fallback_namespaces` capped at three,
`initial_namespaces`, `selection_reason`, `high_confidence`, and
`initial_fanout`. Each corpus item contains `namespace`, `shortlist_rank`,
`shortlist_cosine_score`, `reranker_rank`, `reranker_score`,
`exact_name_match`, and winning prototype kind/index/hash. Raw example text,
vectors, credentials, and provider payloads are forbidden.

Activation requires all of:

- exact shortlist Recall@12 equals `1.0` overall and for every corpus on all
  answer-bearing certification canaries;
- every positive self case includes its expected namespace in the first three
  fallback namespaces, for per-corpus positive Recall@3 of `1.0`;
- aggregate final route Recall@3 is at least `0.95`;
- every `named_self` case ranks its corpus first with selection reason
  `unique_title_or_alias`;
- every `contrast_other` includes its expected other namespace in the first
  three and does not rank the subject corpus first;
- every multi-corpus certification question has complete required-namespace
  coverage in the first three routes;
- incorrect high-confidence singleton count is zero, including negatives and
  no-answer, contrast, and confusing-neighbor questions;
- maximum initial/final content fanout is three and average automatic initial
  fanout is no greater than `2.0`;
- no previously passing canary or per-corpus Recall@3 regresses, and every
  enabled eligible corpus is covered by an approved pack or an explicit
  approved legacy-50 projection;
- the approved automatic multi-corpus route Recall@3, complete multi-corpus
  coverage, incorrect-confident-route, automatic Recall@5, reranking nDCG,
  reranking Recall@5, and fanout gates do not regress;
- route-only call accounting proves one query embedding, zero shortlist or
  per-card provider queries beyond the existing catalog read, zero content queries,
  zero provider writes, and zero model downloads per case; and
- all supported-Python tests, packaging, locked dependency, source-release,
  privacy, provenance, and independent review gates pass.

Reports include exact numerators/denominators, per-corpus/category breakdowns,
shortlist and final ranks, confidence confusion counts, fanout, local model
calls, provider request classes, latency distribution, artifact identities,
and canonical digests. Percentages never hide an empty denominator.

Regression checks require a complete same-catalog legacy-router baseline over
the identical certification cases. A missing or case-mismatched baseline fails
the candidate verdict; it is never treated as an empty set of regressions.

## Reader-first migration

The compatible-reader implementation, route-only collector, and quality
scoring do not write the live provider. Owner-authorized schema-v1 test-corpus
onboarding may use the existing apply/catalog workflows and is recorded as a
separate operational effect; it does not authorize prototype fields or a
shared-schema change. Migration is a separate task and requires explicit
approval after the reader-compatible release is integrated and deployed. It
may occur before candidate quality evidence because the authoritative catalog
must contain the reviewed examples/prototype projection that the no-overlay
collector evaluates. Production routing remains on the legacy base vector
through migration, collection, calibration, and certification; activation is
the later, separately reviewed step.

The migration plan must:

1. prove the live namespace is exact schema v1 and bind its stable card
   snapshot, row count, revisions, and live inventory;
2. prove all supported production readers accept both exact versions;
3. add only the exact four-field non-filterable prototype bundle, with
   `routing_prototype_vector` stored as ordinary `[]float` without ANN;
4. conditionally backfill reviewed cards and recomputed projections against
   their exact observed card revisions;
5. perform two strong complete readbacks proving exact schema v2, one card per
   target, unchanged enabled/source/retrieval/lineage ownership, expected
   semantics/vectors/revisions, and no extra row; and
6. record request/billing counts and the absence of every content-namespace
   mutation.

Any drift, partial affected-ID set, unexpected schema, unknown row, collision,
or failed verification stops the migration. It never deletes or rewrites a
content row/namespace. Because legacy binaries reject additive schema, the
migration approval must explicitly accept that old unsupported readers will
fail closed after cutover. There is no automatic rollback or dual authority.
