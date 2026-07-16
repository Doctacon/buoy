Status: superseded
Created: 2026-07-15
Updated: 2026-07-15

# Offline Semantic Routing Evaluation

## Supersession

Superseded on 2026-07-15 by `.10x/specs/representative-semantic-namespace-routing-experiment.md`. The synthetic five-stage plumbing pilot was replaced by one representative public/project routing experiment. The historical contract remains evidence of the rejected synthetic framework shape, not active behavior.


## Purpose and scope

Define a deterministic offline plumbing pilot comparing exact taxonomy routing, semantic namespace-card routing, and hybrid routing before any production catalog, live Turbopuffer integration, or knowledge graph.

The pilot can establish implementation correctness, safety-gate plumbing, and behavior on its synthetic fixture. It MUST NOT be described as evidence of real semantic-routing quality.

## Assumption provenance

### User-ratified direction

The user approved exact, semantic-card, and hybrid comparison; current multi-namespace RRF as downstream control; local-only execution; ACL/false-exclusion measurement; and no graph before evidence.

### Record/source-backed invariants

- Eligibility gates precede relevance.
- Existing `RRF_K = 60` is reused.
- Namespace-local raw scores are not compared across namespaces.
- Cross-namespace evidence identity includes namespace plus row identity.
- Exact/oracle namespace selection is needed to separate routing loss from downstream cached-retrieval loss.

### Synthetic pilot-only mechanics

Fixture vectors, route limit, acceptable namespace labels, metric formulas, splits, and canonical serialization below exist only for deterministic plumbing evaluation.

### Explicitly unresolved outside the pilot

Real model quality, production ACLs, route limits, promotion thresholds, live latency/cost, public output, learned routing, decomposition, concepts, ontology, and graphs remain blocked.

## Pilot configuration and case inputs

A frozen pilot configuration MUST include:

- `catalog_revision` and `taxonomy_revision`;
- positive integer `route_limit`;
- positive integer `evidence_cutoff`;
- `rrf_k` fixed to `60`;
- deterministic card vectors keyed by card identity;
- case list in stable case-ID order.

Each case MUST contain:

- unique `case_id` and `source_group_id`;
- `split`: `development` or `held_out`;
- query text;
- validated synthetic principal groups;
- the complete compatibility tuple from the catalog spec;
- deterministic query vector;
- disjoint namespace sets: non-empty `required_namespace_ids`, optional `acceptable_namespace_ids`, and optional `forbidden_namespace_ids`;
- ordered `oracle_namespace_ids` containing every required namespace, only required/acceptable namespaces, no duplicates, and length no greater than `route_limit`;
- cached ordered evidence rows per eligible namespace;
- non-empty namespace-qualified `required_evidence_ids` expressed as `(namespace_id, row_id)` pairs.

Required and acceptable namespaces MUST be enabled, authorized for the case, and compatible. Forbidden namespaces MAY be ineligible and exist to test safety. All referenced namespace/evidence IDs MUST exist in the fixture.

## Vector validation

Every query/card vector MUST:

- be a list of exactly `embedding_dimensions` numeric non-boolean values;
- contain only finite values;
- have non-zero Euclidean norm.

Empty, wrong-dimension, NaN, infinite, boolean, and zero-norm vectors are fixture-validation errors before evaluation. Cosine similarity MUST produce a finite score.

## Eligibility first

Authorization, `enabled`, and the complete compatibility tuple MUST gate candidates before every strategy. Ineligible namespaces MUST not be scored.

Internal safety output reports only case ID plus violation category/count. Ordinary route output contains selected authorized namespaces only.

## Routing strategies

Every automatic strategy receives the same eligible candidate set and positive `route_limit`. If fewer candidates exist, return all ranked candidates; zero is invalid.

### Oracle/explicit control

Use the case's `oracle_namespace_ids` exactly in supplied order. This is not an automatic router. It isolates downstream cached-retrieval quality from routing loss.

### Exact taxonomy

- Extract exact term matches under the taxonomy spec.
- Select namespaces assigned at least one matched term.
- Rank by descending number of distinct matched term IDs, then `namespace_id` ascending.
- If no term matches, return no candidates.

### Semantic card

Rank every eligible card by descending cosine similarity, then `namespace_id` ascending.

### Hybrid route RRF

Let exact and semantic ranks be one-based. For each namespace present in either list:

```text
hybrid_score(namespace) =
    sum(1 / (60 + rank_in_strategy))
    for strategy in {exact, semantic}
    where the namespace is present
```

Aggregate contributions by `namespace_id`. Rank by descending hybrid score, then `namespace_id` ascending. A namespace in one list receives one contribution. Apply `route_limit` after fusion.

Route RRF is distinct from downstream evidence RRF, which preserves namespace-qualified hits instead of aggregating equal row IDs.

## Route output

Selected route rows MUST include namespace/revision IDs, route rank, strategy, matched term IDs and normalized phrases when applicable, semantic rank/score when applicable, hybrid score when applicable, and the full compatibility tuple.

Top-level output includes catalog/taxonomy revisions, route limit, evidence cutoff, and RRF constant. Unauthorized metadata is excluded.

## Downstream cached retrieval

Routed namespace order is the explicit downstream namespace-selection order.

The evaluator MUST directly reuse `cross_namespace_rrf` where practical or reproduce exactly:

```text
score = 1 / (60 + one_based_source_rank)
```

Each cached hit remains distinct. Sort by:

1. descending score;
2. routed namespace index ascending;
3. source rank ascending;
4. row ID ascending.

Return the first `evidence_cutoff` hits. Equal row IDs in different namespaces remain distinct via `(namespace_id, row_id)`.

No chunk/evidence tag filter or boost exists in this pilot.

## Metrics

For one case, let `S` be selected namespaces, `R` required, `A` acceptable, and `E` returned namespace-qualified evidence at `evidence_cutoff`.

- `required_namespace_recall = |S ∩ R| / |R|` (`R` is non-empty);
- `selected_namespace_precision = |S ∩ (R ∪ A)| / |S|`, defined as `0.0` when `S` is empty;
- `over_selection_count = |S - (R ∪ A)|`;
- `fan_out = |S|`;
- `forbidden_selection_count = |S ∩ forbidden|`;
- `ineligible_selection_count`: selected namespaces that fail enabled/ACL/compatibility, expected zero;
- `required_evidence_recall = |E ∩ required_evidence| / |required_evidence|` (required evidence is non-empty).

Report every metric per case and macro arithmetic mean per strategy/split. Counts for forbidden/ineligible selection are also summed across cases and MUST remain visible; averages cannot hide them. No micro aggregate is used.

Report oracle, exact, semantic, and hybrid in that fixed strategy order. Exact is the cheapest automatic control; oracle is the downstream ceiling/control.

## Auditable freeze and held-out discipline

A separate fixture-freeze ticket MUST commit and independently review before execution:

- source-grouped development/held-out assignment;
- all fixture files and canonical card text;
- vectors and cached evidence;
- required/acceptable/forbidden namespace and evidence labels;
- route/evidence limits and metric definitions;
- SHA-256 manifest of every frozen input;
- implementation commit expected for execution.

The execution ticket MUST run the frozen commit without editing inputs or parameters. Any edit invalidates the freeze and requires a new manifest/review before another held-out run.

Because fixtures and labels are synthetic and repository-visible, results are **deterministic plumbing evidence**, not held-out real-world quality evidence.

## Canonical serialization

Results MUST:

- preserve cases by `case_id` ascending;
- preserve strategy order `oracle`, `exact`, `semantic`, `hybrid`;
- preserve selected/evidence rank order;
- serialize JSON with UTF-8, sorted object keys, separators `(',', ':')`, `ensure_ascii=False`, and exactly one trailing newline;
- contain only finite numeric values.

Repeated execution of the same frozen commit MUST produce identical bytes and SHA-256 digest.

## Acceptance scenarios

- Unauthorized highest-scoring/exact-matching canary is never exposed.
- Any compatibility mismatch excludes before scoring.
- Exact miss returns no exact route while other strategies remain measurable.
- Hybrid aggregates same namespace across lists with the formula above.
- Invalid vectors/config/case labels fail before evaluation.
- Oracle uses fixed explicit order and isolates downstream evidence recall.
- Downstream ties follow current namespace-qualified RRF ordering; duplicate row IDs survive across namespaces.
- Repeated frozen runs produce byte-identical canonical JSON.

## Acceptance criteria

- All contracts, formulas, validation, outputs, metrics, and freeze rules are test-covered.
- Fixture covers public/private, overlapping groups, invalid group cases, disabled/incompatible namespaces, exact/synonym/semantic-only cases, false exclusions, forbidden canaries, tie cases, and duplicate row IDs.
- Test sentinels fail on socket/network, credential access, model construction/download, Turbopuffer SDK construction, live retrieval/write, and persistence outside temporary paths.
- No architecture promotion occurs.

## Explicit exclusions

Answer generation, LLM judging, live services, real ACLs, public APIs, learned routing, decomposition, chunk tag filtering/boosts, concepts, ontology, graphs, production storage, and numeric promotion thresholds.
