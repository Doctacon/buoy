Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: commit `3809a62`; `.10x/specs/superseded/controlled-taxonomy-pilot.md`; `.10x/specs/superseded/semantic-namespace-catalog-pilot.md`; `.10x/specs/superseded/offline-semantic-routing-evaluation.md`; `.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md`; its four child tickets
Verdict: fail

# Semantic Routing Offline Pilot Shaping Review

## Target and authority inspected

This review adversarially checked shaping commit `3809a62` against:

- the user-approved direction preserved at `.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md:26-36` and `.10x/tickets/done/2026-07-15-semantic-retrieval-research-plan.md:81-82`;
- `.10x/decisions/data-vault-is-analogy-not-architecture.md`;
- `.10x/decisions/namespace-ranking-defaults.md`;
- `.10x/specs/explicit-multi-namespace-retrieval.md`;
- `.10x/research/2026-07-15-metadata-tagging-graphs-and-data-vault.md`;
- `.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md`;
- `.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md`;
- `.10x/research/2026-07-15-data-vault-concept-graph.md`;
- `.10x/research/2026-07-15-data-vault-multi-hop-global-retrieval.md`;
- current namespace-qualified RRF implementation and tests at `src/buoy_search/retriever.py:504-524` and `tests/test_multi_namespace_retrieval.py:71-112`.

## Correct

- **Focused top-level boundaries are mostly sound.** Catalog authority/projection, controlled taxonomy, and routing evaluation are separate coherent surfaces. The parent is explicitly non-executable (`.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md:9-14`) and implementation is delegated to bounded children.
- **No Data Vault, graph, or production implementation creep was found.** The plan and specs repeatedly exclude Data Vault machinery, ontology/concept extraction, graph construction/traversal, live Turbopuffer, production persistence, and architecture promotion (`.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md:47-66`; `.10x/specs/superseded/semantic-namespace-catalog-pilot.md:105-112`; `.10x/specs/superseded/offline-semantic-routing-evaluation.md:131-138`). This matches `.10x/decisions/data-vault-is-analogy-not-architecture.md:15-35`.
- **Offline and fail-before-score intent is strong.** Deterministic fixture vectors, no model initialization/download, authorization/eligibility/compatibility before scoring, no live retrieval/write, and no unauthorized route metadata are explicit (`.10x/specs/superseded/offline-semantic-routing-evaluation.md:13-28,123-129`; `.10x/specs/superseded/semantic-namespace-catalog-pilot.md:35-53,98-104`).
- **Governed and derived semantics are separated.** Semantic similarity cannot create taxonomy assignments, and topical tags cannot grant access (`.10x/specs/superseded/controlled-taxonomy-pilot.md:28-34,74-80`).
- **The worktree topology is directionally correct.** Each child names its own `work/*` branch/worktree; downstream children wait for dependencies to integrate into `develop` (`.10x/tickets/cancelled/2026-07-15-build-offline-semantic-router-evaluator.md:5,13`; `.10x/tickets/cancelled/2026-07-15-run-offline-semantic-routing-pilot.md:5,13`).

## Findings

### Critical — The records declare execution ready while material semantics are neither provenance-classified nor complete

The durable user approval establishes the phase and five broad outcomes, not every detailed semantic choice (`.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md:26-36`). Nevertheless, all four children say they arise from a “user-ratified ... specification set” and claim either `Blockers: None` or only mechanical dependencies (`.10x/tickets/cancelled/2026-07-15-build-controlled-taxonomy-fixture.md:39-45`; `.10x/tickets/cancelled/2026-07-15-build-offline-namespace-catalog-fixture.md:41-47`; `.10x/tickets/cancelled/2026-07-15-build-offline-semantic-router-evaluator.md:42-48`; `.10x/tickets/cancelled/2026-07-15-run-offline-semantic-routing-pilot.md:42-48`). No spec or ticket classifies detailed behavior as user-ratified, research-backed, current-source-compatible, synthetic pilot-only, or still blocked.

This matters because the detailed choices include synthetic authorization semantics, the compatibility tuple, normalization boundaries, precision/source-kind domains, vector validity, route-limit behavior, metric formulas, hybrid fusion semantics, and held-out controls. Several are underdefined or conflict with governing research below. An implementer would have to ratify them by coding them.

**Required repair:** add compact assumption-provenance sections to the three specs and affected children. Distinguish (a) the user-ratified pilot direction, (b) record/source-backed invariants, (c) deliberately synthetic pilot-only mechanics that do not claim production meaning, and (d) unresolved items. Do not describe the entire detailed spec set as user-ratified unless exact semantics were actually confirmed. Mark implementation children blocked until the significant findings below are repaired.

### Significant — Taxonomy identity and matching are internally contradictory

The taxonomy rejects duplicate labels, duplicate cross-term synonyms, and a synonym equal to its own label, but does not reject a synonym equal to another term's label (`.10x/specs/superseded/controlled-taxonomy-pilot.md:17-24`). That permits one normalized phrase to map to two term IDs, contradicting the requirement that every matched label/synonym map to exactly one term ID (`:36-46`).

“Unicode-normalize,” “complete normalized phrase,” and “after normalization” also leave the Unicode normalization form, whitespace treatment, punctuation/word-boundary behavior, and match-evidence representation undefined (`:24,36-46`). These choices change matches and acceptance results.

**Required repair:** define one canonical normalization algorithm and phrase-boundary rule, with punctuation/whitespace and Unicode examples. Validate uniqueness across the union of every normalized label and synonym, not only within label and synonym subsets. Define deterministic ordering and exact matched-phrase output when phrases overlap or repeat in a query.

### Significant — Catalog/taxonomy revision coherence and compatibility gates are incomplete

Catalog cards render taxonomy labels and claim determinism for identical catalog and taxonomy revisions (`.10x/specs/superseded/semantic-namespace-catalog-pilot.md:55-66`), but catalog records/cards do not carry `taxonomy_revision`; cards retain only catalog, namespace, and revision references. “taxonomy labels in tag-id order” does not say whether this is fixture order or canonical sorting. Cached evidence tags likewise have no explicit revision binding beyond prose (`.10x/specs/superseded/controlled-taxonomy-pilot.md:48-54`). A changed taxonomy label can therefore change card bytes without changing the retained card identity.

The catalog requires `schema_version` and `ranking_profile` (`.10x/specs/superseded/semantic-namespace-catalog-pilot.md:26-29`) but eligibility compares only embedding model, dimensions, and precision (`:46-53`). Evaluation cases similarly provide only an “embedding contract” (`.10x/specs/superseded/offline-semantic-routing-evaluation.md:15-22`). Governing research requires compatibility cohorts to cover model/dimension/schema/profile and describes schema/retrieval-profile support as pre-score gates (`.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md:237-249,268-280`). Current live multi-namespace compatibility also includes region (`src/buoy_search/retriever.py:439-447`). Fields that are required but ignored invite false compatibility.

The loader must reject “unsupported embedding precision,” but the supported set is not named or referenced (`.10x/specs/superseded/semantic-namespace-catalog-pilot.md:31-34`). `source_kind` is similarly examples rather than a closed or explicitly open domain (`:17-24`).

**Required repair:** bind every card and tagged cached-evidence fixture to an explicit taxonomy revision and define canonical tag ordering. Define the complete pilot query/namespace compatibility tuple and gate all fields that materially affect cached retrieval (at minimum disposition of region, schema version, ranking profile, model, dimensions, and precision); alternatively remove non-gating fields and document why. Name source-backed allowed precision/profile/source-kind domains or explicitly specify open-string behavior.

### Significant — The exact/semantic/hybrid algorithms are not regeneration-grade

Cosine routing has no validation or behavior for dimension mismatch, empty vectors, zero-norm vectors, NaN, or infinity (`.10x/specs/superseded/offline-semantic-routing-evaluation.md:41-45`). The route limit is required to be shared but is absent from the enumerated case inputs and has no validation or zero/oversized behavior (`:13-22,30-32`).

The hybrid says to use RRF but does not state the score aggregation formula. Route fusion must sum `1 / (60 + rank)` by the same `namespace_id` across exact and semantic lists. Reusing the downstream cross-namespace helper would be wrong because current `cross_namespace_rrf` intentionally preserves each namespace-qualified hit as distinct rather than aggregating equal row IDs (`src/buoy_search/retriever.py:504-524`).

The taxonomy spec also introduces optional evidence hard filtering or a bounded tag boost (`.10x/specs/superseded/controlled-taxonomy-pilot.md:48-54`) without defining either an evaluation arm or boost/filter algorithm in the evaluator spec. The parent promises false-exclusion evaluation (`.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md:30-34`), while the evaluator ticket implements only namespace routing and cached RRF (`.10x/tickets/cancelled/2026-07-15-build-offline-semantic-router-evaluator.md:9-25`). This crosses the taxonomy/evaluator boundary without executable semantics.

**Required repair:** specify vector validation and deterministic invalid/zero-vector outcomes; locate and validate the route limit; define hybrid RRF mathematically, including one-list membership and rank origin. Either remove cached-evidence tag filtering/boost from this pilot and define false exclusion purely as missed required namespace/evidence, or add a separately named, fully specified evidence-filter/boost arm with its own metrics. Do not leave a `MAY` behavior that changes measured retrieval.

### Significant — Namespace-qualified downstream RRF compatibility is asserted but not fully specified

The evaluator says to use “existing namespace-qualified RRF semantics” (`.10x/specs/superseded/offline-semantic-routing-evaluation.md:67-71`), but the acceptance contract names only identity preservation. Current behavior uses `1 / (RRF_K + source_rank)` and resolves ties by namespace selection order, then source rank, then row ID (`src/buoy_search/retriever.py:512-524`; `.10x/specs/explicit-multi-namespace-retrieval.md:28-35`). The pilot route order is not explicitly declared to be downstream namespace selection order. A fresh evaluator implementation could use a different tie rule and still appear compliant.

**Required repair:** require direct reuse of `cross_namespace_rrf` where its data shape permits, or reproduce its exact formula and tie order in the spec. State that routed namespace order is the explicit downstream selection order, and test equal local ranks plus duplicate row IDs across namespaces.

### Significant — Metrics and the explicit/oracle downstream control are underdefined

The case schema has expected and forbidden namespaces but no “acceptable” set (`.10x/specs/superseded/offline-semantic-routing-evaluation.md:15-22`), while governing research defines required, acceptable, and must-not-select labels and uses acceptable-or-required in precision (`.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md:268-305`). The spec does not define metric formulas, empty-denominator behavior, macro versus micro aggregate, over-selection, evidence identity labels, or the configured evidence cutoff (`.10x/specs/superseded/offline-semantic-routing-evaluation.md:73-88`). “Byte-for-byte” reproducibility also needs canonical case/result ordering and serialization (`:119-121`).

The spec calls current explicit selection/RRF the downstream baseline (`:90-96`) but runs downstream fusion only for the three predicted routing strategies. Governing multi-hop research requires an oracle/gold namespace-selection run first so routing failure can be separated from retrieval failure (`.10x/research/2026-07-15-data-vault-multi-hop-global-retrieval.md:162-178,392-394`). Without it, a downstream evidence miss cannot be attributed to routing versus cached retrieval.

**Required repair:** define required/acceptable/forbidden namespace sets and validate their disjointness and eligibility expectations; give formulas and edge-case behavior for every metric and aggregation; define namespace-qualified required-evidence labels/cutoff and canonical serialization order. Add an explicit/oracle namespace-selection + existing RRF downstream control using the same cached lists, while keeping exact-only as the cheapest automatic-routing control.

### Significant — The held-out protocol is not protected by the ticket graph

The run child gives one executor ownership of catalog cards, taxonomy/synonyms, vectors, development cases, held-out cases, execution, and synthesis (`.10x/tickets/cancelled/2026-07-15-run-offline-semantic-routing-pilot.md:9-24`). Saying held-out cases are identified “before execution” is weaker than the governing research requirement to split before generating/tuning cards, keep test labels unavailable to card authors/parameter tuning, group near-duplicate sources/concepts, freeze all artifacts and parameters, and perform one final held-out run (`.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md:307-311`). The current ticket permits a nominal held-out set assembled alongside the vectors designed to satisfy it.

The same research says assistant-generated labels can exercise plumbing but are not final quality ground truth (`:272-282`). The run ticket requires synthetic fixtures but does not bound resulting claims accordingly.

**Required repair:** create an auditable pre-run freeze boundary. Prefer separate dataset/freeze and execution tickets or, minimally, require a reviewed committed preregistration artifact before vector/card tuning that records source-grouped split assignment, hidden/frozen labels, fixture and parameter digests, route limits, metric definitions, and no post-freeze edits. If all labels/vectors remain synthetic and visible to one author, call the result deterministic plumbing evidence, not held-out quality evidence or routing-value evidence.

### Significant — The two “independent” fixture children have a real integration dependency

The parent says catalog and taxonomy children are independent and may run in parallel (`.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md:38-45`). Yet catalog validation must reject unknown taxonomy terms and card generation must resolve taxonomy labels (`.10x/specs/superseded/semantic-namespace-catalog-pilot.md:31-34,55-66`). The catalog child accepts both duties while excluding taxonomy matching and declaring no dependency (`.10x/tickets/cancelled/2026-07-15-build-offline-namespace-catalog-fixture.md:15-29,41-43`). In separate worktrees, it must invent or duplicate the taxonomy interface before the taxonomy child integrates.

Responsibility is also reversed in the taxonomy child: it must “prove taxonomy terms grant no access” despite authorization belonging to the catalog/evaluator boundary (`.10x/tickets/cancelled/2026-07-15-build-controlled-taxonomy-fixture.md:15-22`).

**Required repair:** either make catalog depend on integrated taxonomy, or define a small exact shared fixture/interface owned before both children and move cross-fixture reference/card tests to the evaluator integration child. Keep taxonomy tests limited to taxonomy behavior; prove “tags never grant access” where catalog authorization and taxonomy assignments meet. Clarify that early child fixtures are loader/test fixtures and the fixed pilot dataset is owned only by the run/freeze child.

### Minor — Synthetic ACL inputs need explicit validation and leakage-test scope

The namespace rule itself is clear and safely synthetic (`.10x/specs/superseded/semantic-namespace-catalog-pilot.md:35-45`), but principal-group validation, empty/duplicate group handling, `is_public=true` with groups, and overlap normalization are unspecified. “Unauthorized metadata cannot leak through diagnostics” is not testable until ordinary diagnostics are distinguished from internal evaluator safety records. Tests are required to prove no network/credential/SDK construction, but no test boundary is named.

**Required repair:** define group ID normalization/validation and set semantics; distinguish internal redacted safety accounting from route/user diagnostics; require adversarial canaries for ID/title/tag/score/exclusion leakage and a test harness that fails on socket/network, credential lookup, model construction/download, SDK construction, persistent writes, and live retrieval calls.

## Verdict

**Fail.** The approved direction and scope boundaries are good, and no production/Data Vault/graph creep was introduced. However, the active specs and executable children are not yet cold-start executable without inventing semantics. The critical provenance problem plus taxonomy collision, compatibility, algorithm, metrics/oracle, held-out, RRF, and dependency gaps must be repaired before implementation begins.

## Residual risk

After the required repairs, a fully synthetic deterministic pilot can establish implementation correctness, ACL-gate plumbing, rank-fusion compatibility, and whether the fixture behaves as designed. It still cannot establish production ACL policy, live Turbopuffer behavior, real semantic-routing quality, model quality, latency/cost, production catalog authority, taxonomy stewardship, or a promotion threshold. Those remain explicitly outside this plan and require later evidence and user ratification.
