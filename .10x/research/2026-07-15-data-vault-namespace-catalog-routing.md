Status: done
Created: 2026-07-15
Updated: 2026-07-15

# Data Vault Namespace Catalog and Semantic Routing

## Scope correction — no Data Vault architecture

The user clarified after this research closed that Data Vault was only an analogy for stable concepts and relationships. `.10x/decisions/data-vault-is-analogy-not-architecture.md` governs: Buoy will not build or require hubs, links, satellites, business-key governance, warehouse authority, or Data Vault loading.

Retain this record's findings on separate namespace/source/revision identities, relational catalog authority, semantic namespace cards, compatibility, ACL gating, lifecycle, and routing evals. Reinterpret proposed “Hub” or vault mappings as ordinary project-governed catalog/concept identifiers; recommendations requiring an actual Data Vault are withdrawn.

## Question

What is the smallest governed catalog and query-routing layer that can select a bounded, authorized, embedding-compatible set from many Buoy/Turbopuffer namespaces, while using Data Vault 2.0 identity, history, and lineage correctly and without treating a namespace, vector index, or inferred concept as Raw Vault authority?

This record answers a research question only. Labels marked **Documented fact**, **Local observation**, and **Recommendation** deliberately separate external claims, current Buoy behavior, and proposed design. Unresolved product semantics remain blockers rather than acceptance criteria.

## Sources and methods

Research was performed 2026-07-15. Methods were: complete inspection of the owning ticket, parent plan, preliminary research, active local contracts and relevant source; direct reading of official Turbopuffer documentation; comparison with Data Vault authority/lineage material; and inspection of open-source/self-hostable catalog and routing documentation and repositories. No credential was read, no model was loaded, and no Turbopuffer or other live service was queried or mutated.

The requested root `context.md` and `plan.md` were absent from this worktree. Their durable equivalents—the owning ticket and referenced parent plan—were present and inspected. This is a source-availability limit, not a substituted semantic assumption.

### Local authority inspected completely

- `.10x/tickets/done/2026-07-15-research-data-vault-namespace-catalog-routing.md`
- `.10x/tickets/2026-07-15-semantic-retrieval-research-plan.md`
- `.10x/research/2026-07-15-metadata-tagging-graphs-and-data-vault.md`
- `.10x/specs/turbopuffer-namespace-discovery.md`
- `.10x/specs/explicit-multi-namespace-retrieval.md`
- `.10x/specs/compact-duckdb-applied-state.md`
- `.10x/specs/plan-artifact-lifecycle-cleanup.md`
- `.10x/decisions/namespace-ranking-defaults.md`
- `.10x/decisions/duckdb-applied-state-concurrency-and-retention.md`
- `.10x/decisions/plan-artifact-immediate-lifecycle-retention.md`
- `.10x/tickets/done/2026-07-14-add-namespace-discovery-command.md`
- `.10x/tickets/done/2026-07-14-add-explicit-multi-namespace-retrieval.md`
- `src/buoy_search/namespaces.py`
- `src/buoy_search/retriever.py`
- `src/buoy_search/plan_artifacts.py`
- `src/buoy_search/applied_state.py`
- `src/buoy_search/chunker.py`
- `src/buoy_search/config.py`
- `docs/retrieval.md`

### External sources (accessed 2026-07-15)

#### Turbopuffer official documentation

- Concepts and namespace isolation: https://turbopuffer.com/docs/concepts
- Write/namespace creation and document identity: https://turbopuffer.com/docs/write
- Single-namespace queries, filters, multi-query, and aggregation: https://turbopuffer.com/docs/query
- Namespace metadata response: https://turbopuffer.com/docs/metadata
- Document-level permission-filter pattern: https://turbopuffer.com/docs/permissions
- Production limits: https://turbopuffer.com/docs/limits
- Namespace listing: https://turbopuffer.com/docs/namespaces
- Schema and attribute indexing: https://turbopuffer.com/docs/schema
- Atomic write batches and transaction limits: https://turbopuffer.com/docs/guarantees

#### Data Vault 2.0 identity, history, and lineage

- Data Vault Alliance, standards-change process (publisher-hosted process authority, not a public normative specification): https://datavaultalliance.com/engineering/how-to-propose-dv-standards/
- Data Vault Alliance, Data Vault 2.0 overview by Daniel Linstedt (publisher-hosted explanatory material, not a normative specification): https://datavaultalliance.com/architecture-data/understanding-data-vault-2-0/
- Scalefree, Data Vault 2.0 modeling overview: https://www.scalefree.com/scalefree-newsletter/data-vault-2-0-modeling-basics/
- Databricks, Data Vault overview and hub/link/satellite explanation: https://www.databricks.com/blog/what-is-data-vault
- dbt Labs, Data Vault technique overview: https://www.getdbt.com/blog/data-vault-with-dbt-cloud
- AutomateDV open-source documentation, hashing and staging conventions: https://automate-dv.readthedocs.io/en/latest/best_practises/hashing/

The Data Vault Alliance process article is authoritative only about how that publisher describes standards evolution; the Alliance overview and the other sources are explanatory/implementation evidence. No accessible public normative Data Vault specification was established by this investigation, and none of these sources substitutes for a ratified enterprise business-key model or the complete proprietary Data Vault 2.0 body of knowledge.

#### Open-source/self-hostable catalog and lineage implementations

- DataHub architecture and metadata model (Apache-2.0): https://docs.datahub.com/docs/architecture/architecture and https://github.com/datahub-project/datahub
- OpenMetadata metadata standard and lineage (Apache-2.0): https://docs.open-metadata.org/latest/main-concepts/metadata-standard and https://github.com/open-metadata/OpenMetadata
- OpenLineage object model (Apache-2.0): https://openlineage.io/docs/spec/object-model/ and https://github.com/OpenLineage/OpenLineage
- Marquez reference metadata/lineage service (Apache-2.0): https://github.com/MarquezProject/marquez

#### Open-source routing implementations

- Aurelio Labs `semantic-router`, route/utterance selection (MIT; repository-root license): https://github.com/aurelio-labs/semantic-router and https://raw.githubusercontent.com/aurelio-labs/semantic-router/HEAD/LICENSE
- LlamaIndex router query engine and selectors (MIT): https://docs.llamaindex.ai/en/stable/module_guides/querying/router/ and https://github.com/run-llama/llama_index
- Haystack conditional router (Apache-2.0): https://docs.haystack.deepset.ai/docs/conditionalrouter and https://github.com/deepset-ai/haystack

Licenses above are repository licenses observed at the named project roots. A production dependency review would still need to verify the exact release, transitive dependencies, deployment features, and trademark/hosted-edition boundaries.

## Evidence-backed findings

### 1. Turbopuffer namespaces are serving isolation, not semantic authority

**Documented fact.** Turbopuffer defines a namespace as an isolated container with its own document/vector/attribute indexes, implicitly created by the first inserted document. Its guidance recommends one namespace per set of documents expected to be returned together and notes that smaller namespaces generally perform better. A query targets one namespace. Multi-query combines search strategies against that same namespace; it is not cross-namespace routing.

**Documented fact.** Namespace listing exposes identifiers. Namespace metadata exposes schema, approximate row/logical-byte counts, creation/write/update timestamps, index status/unindexed bytes, encryption, and optional pinning/branch information. It does not document source business keys, human meaning, embedding-model identity for client-generated vectors, ACL policy ownership, retrieval profiles, or source revision lineage.

**Documented fact.** Namespaces can be numerous (the limits page reports unlimited as the production limit and 250M+ observed), but each query still names a namespace. Mechanical scale therefore does not solve discovery or safe selection.

**Conclusion from facts.** A namespace ID is a physical serving address, not sufficient authority for what the data means or which query may access it. Turbopuffer can host a derived catalog search index, but its namespace APIs do not constitute that catalog.

### 2. Catalog ACLs must precede semantic routing

**Documented fact.** Turbopuffer does not provide built-in row/document RBAC. Its documented pattern stores `user_ids`, `group_ids`/groups, and an explicit `is_public` attribute on each document, then supplies mandatory filters from the application auth layer. The permission guide explicitly warns that an empty permission list should mean no access rather than public access.

**Recommendation.** Authorization MUST narrow catalog candidates before any semantic namespace-card scoring and MUST again constrain each namespace-local retrieval. Catalog-card text, counts, titles, and concept summaries can themselves disclose sensitive corpus existence; unauthorized cards should not merely be selected and then dropped later.

**Failure mode.** A semantically excellent router with post-selection ACL checks leaks metadata through candidate lists, timing, logs, or explanations and can waste calls on inaccessible namespaces. Shared concept cards can also bridge otherwise isolated tenants.

### 3. Vector/schema compatibility is a routing contract, not a name convention

**Documented fact.** Turbopuffer schemas expose vector dimensions/types and query filters; metadata can report the remote schema. Client-generated vector semantics—the embedding model, revision, normalization, input template, and precision used to populate the vector—are not recoverable from dimensions alone.

**Local observation.** Current Buoy embeds once and requires all explicitly selected namespaces to share one region, configured embedding model, and precision. It neither registers nor infers those values per namespace. Website/document and repository namespace prefixes select different local ranking defaults, but prefixes do not prove source meaning or embedding compatibility.

**Recommendation.** Treat an `embedding_contract_id` as an immutable catalog object covering provider/model identifier, model revision or content digest where available, dimensions, vector attribute, normalization, input template/chunk text contract, stored vector type, query precision, distance metric, and contract version. Route only within a compatible cohort before reusing one query vector. Querying multiple model cohorts would require one embedding per cohort and is outside the current Buoy contract.

### 4. Current local artifacts contain useful lineage, but none is a durable catalog

**Local observation.** A plan records `plan_id`, `artifact_hash`, source/site ID and base URL, target and candidate namespace, embedding model/precision, schema version, state path, options, and diff. Its manifest/rows add canonical URL, stable row ID, source/page/chunk/embedding-text hashes, source kind, repository identity/ref/commit/path/language, or local-file/PDF identity and hashes.

**Local observation.** Per-namespace DuckDB state keeps the current applied-row ledger and compact apply-run summaries. It intentionally does not retain full historical row snapshots. Plan directories are intentionally deleted after successful approved apply or supersession. Consequently neither successful plan artifacts nor the current ledger alone can answer full historical questions such as “which source revision and embedding contract produced every prior indexed revision?”

**Recommendation.** A future catalog ingest boundary should consume reviewed plan identity before artifact cleanup and append deployment/revision history only after the remote operation and local-state commit succeed. A pending plan is intent, not an active indexed revision. This is a design implication, not authorization to change apply behavior.

### 5. Data Vault identity must not be inferred from namespace or vector content

**Documented fact.** Data Vault 2.0 separates stable business keys in Hubs, durable relationships in Links, and descriptive/history-bearing context in Satellites, with record source and load time supporting auditability. Hash keys are implementation aids derived from canonicalized business keys; they do not create business meaning.

**Recommendation.** Use four separate identity classes:

1. **Physical namespace address:** `(provider, organization/account boundary, region, namespace_id)`. This is the authoritative remote location. Rename should normally create a new address/deployment relationship, not rewrite history.
2. **Governed source identity:** a registry-issued `source_id` bound to a ratified source business key and canonical locator. Mutable locator/title belong in history, while source-specific immutable revisions (for example Git commit or file digest) identify observations.
3. **Data Vault business concept identity:** the governed Hub business key supplied by domain authority. An LLM label, tag, namespace-card phrase, URL slug, or embedding cluster is not allowed to mint this identity silently.
4. **Indexed revision identity:** an immutable `index_revision_id` generated by the catalog and bound to source revision(s), reviewed plan/artifact identity, row/chunk schema, embedding contract, retrieval profile version, and applied outcome. This is technical deployment lineage, not automatically a business Hub.

**Important boundary.** If an enterprise Raw Vault already governs sources and business concepts, the catalog should reference its Hub/Link keys and project serving metadata. If no such authority exists, a relational technical registry may govern namespace/source/index identities without claiming to be Data Vault 2.0.

### 6. Open-source catalogs solve more than the smallest experiment needs

**Documented fact.** DataHub and OpenMetadata model versioned metadata entities, relationships, ownership, tags/domains, schemas, and lineage with self-hostable services and search. OpenLineage defines job/run/dataset events and facets; Marquez is a self-hostable reference service consuming that lineage model.

**Comparison.** These systems provide useful precedents for stable URNs, aspect/entity versioning, ownership, lineage events, and searchable projections. They also introduce ingestion frameworks, services, APIs, search backends, operational upgrades, and broader metadata semantics. OpenLineage/Marquez are strongest for job-run-dataset lineage and do not by themselves define Buoy's namespace selection or vector compatibility contract.

**Recommendation.** Do not adopt a full catalog platform for the first routing experiment. Keep a portable relational model and event/export boundary that can later map to DataHub/OpenMetadata/OpenLineage if enterprise integration becomes a named requirement. This follows the project's open-source-first rule without spending platform complexity prematurely.

### 7. Semantic routing implementations converge on descriptions plus deterministic gates

**Documented fact.** `semantic-router` represents routes with example utterances and selects a route through encoder similarity/thresholds. LlamaIndex routers select among query engines/tools described by metadata, using LLM- or embedding-based selectors. Haystack's `ConditionalRouter` executes explicit conditions over pipeline inputs.

**Finding.** These are routing mechanisms, not catalog authority or authorization systems. Their useful common shape is a small candidate description, a selection score/condition, and a downstream target. None makes generated descriptions, thresholds, or model decisions authoritative by itself.

**Recommendation.** Combine deterministic gates (authorization, status, source kind, embedding/schema cohort, requested scope) with semantic scoring over versioned namespace cards. Never ask a semantic classifier to override an exact deny, incompatible vector contract, or tombstoned deployment.

## Competing architectures

### Architecture A — canonical relational catalog plus derived searchable namespace cards (recommended candidate)

**Authority boundary.** A self-hosted PostgreSQL database—or SQLite/DuckDB for a single-process experiment—is canonical for source, namespace address, indexed revision, contracts, policies, and history. A dedicated derived Turbopuffer namespace stores one card per routable namespace revision for semantic candidate ranking. Raw Vault business identities are referenced, not recreated.

**Write/read path.** Approved lifecycle events append catalog revisions transactionally in the relational store. An outbox/version cursor updates the derived card index idempotently. Queries authorize and deterministically filter canonical candidates, semantically score only eligible card IDs, revalidate returned card versions, then retrieve from a bounded namespace set.

**Strengths.** Explicit constraints and foreign keys; auditable temporal history; easy exact ACL/compatibility queries; portable/open-source authority; semantic index is rebuildable and disposable.

**Failure modes.** Catalog/card lag, dual-write bugs, stale cards, relational service operations, and policy mistakes. Mitigate with revision IDs on cards, outbox checkpoints, deny-on-missing/stale card versions, and rebuild tests.

**Migration path.** Start with fixture-backed SQLite/DuckDB tables and an in-memory card scorer; move canonical tables to PostgreSQL if multi-writer/service needs arise; export entity/lineage events to DataHub, OpenMetadata, or OpenLineage later. A Turbopuffer card index can be added only after offline routing shows value.

### Architecture B — Turbopuffer namespace-card registry as canonical catalog

**Authority boundary.** One registry namespace contains typed card documents. Exact attributes hold status/contracts/policy references; text/vector fields support semantic routing. History is represented by immutable revision documents plus a current pointer/status convention.

**Strengths.** Smallest number of new runtime components; native filters plus semantic/BM25 search; straightforward scale and rebuild of route candidates if another source exists.

**Failure modes.** Circular dependency (the service being routed is also the only routing authority); no relational constraints or general-purpose read/write transactions; user-level ACL filters remain application-enforced; hard-to-prove temporal uniqueness/currentness; accidental card overwrite can erase history; service outage blocks both discovery and retrieval. Turbopuffer documents that all writes in one upsert are applied atomically and that conditional writes provide limited atomic read/write semantics. Those guarantees do not provide foreign keys/uniqueness constraints or one transaction spanning the registry namespace, routed-data namespaces, and application lineage state, so cross-namespace and multi-system consistency remains application-managed. Turbopuffer metadata does not provide business lineage, so application records still have to supply it.

**Migration path.** Export immutable cards/events into a relational catalog, then demote this namespace to a derived index. If no independent event source exists, migration cannot reconstruct overwritten or omitted history.

**Assessment.** Viable only for a disposable experiment whose cards are generated from versioned files. Not recommended as production canonical authority.

### Architecture C — enterprise Data Vault as authority plus catalog serving projection

**Authority boundary.** Governed Raw Vault Hubs/Links/Satellites own business source/concept identity and historical observations. Technical indexed-deployment satellites/links record namespace/revision lineage. A relational/search projection serves routing cards.

**Strengths.** Strongest enterprise audit and lineage alignment; preserves source-system observations and business-key governance; corrections are historized rather than silently overwritten.

**Failure modes.** Greatest modeling/load complexity and latency; teams may incorrectly elevate inferred concepts to Hubs; serving queries directly from Raw Vault structures can be cumbersome; building it before business keys/load rules are ratified launders assumptions into warehouse authority.

**Migration path.** Architecture A's source/index identities can later map to governed Hub/Link keys and become a serving projection. Keep technical deployment IDs separate to avoid destructive remapping.

**Assessment.** Appropriate only if a current Data Vault authority, loading standards, and operational owner already exist. Those are not established in inspected Buoy records.

## Candidate catalog model

The following is a candidate for evaluation, not a ratified schema.

| Entity | Required fields | Authority / Data Vault mapping |
|---|---|---|
| `source` | `source_id`, `source_kind`, governed business key, canonical locator, owner, lifecycle status, valid/observed times | Reference `Hub_Source` when it exists; locator/title history in source Satellite |
| `source_revision` | `source_revision_id`, `source_id`, immutable revision/digest, observed/load time, record source, crawl/extraction contract | Source observation Satellite; do not pretend a crawl timestamp is business effective time |
| `business_concept_ref` | external Hub key, vocabulary/version, display label, authority | Reference only; inferred terms remain separate candidates |
| `source_revision_concept_ref` | source revision ID, concept key/version, assignment authority, record source, asserted/load time, effective-from/to, withdrawal/status | Governed relationship assertion; connects concepts to source observations without allowing inferred terms to mint or silently attach Hub identity |
| `namespace_address` | `namespace_address_id`, provider, organization/account boundary, region, namespace ID, created/retired times | Technical registry identity; not automatically a business Hub |
| `index_revision` | immutable ID, namespace address, `plan_id`, artifact hash, row/chunk/schema contract IDs, embedding contract ID, retrieval profile ID/version, applied/status times, supersedes ID | Technical historical Satellite/Link projection; each successful deployment is append-only |
| `index_revision_source_revision` | index revision ID, source revision ID, relationship role, record source, load time | Explicit many-to-many deployment provenance; replaces an opaque source-revision set and supports multi-source indexes |
| `embedding_contract` | ID/version, model/revision, dimensions, vector attribute/type, normalization, input template, precision, distance metric | Technical reference data |
| `schema_contract` | ID/version, attribute names/types, required retrieval fields, ACL fields, compatibility fingerprint | Technical reference data; remote schema may verify only part |
| `retrieval_profile` | ID/version, source class, candidate limits, within-namespace ranking/fusion settings | Serving policy, not source truth |
| `access_policy_ref` | policy ID/version, tenant/security boundary, policy engine/owner, default-deny marker | Reference to authoritative authorization system; do not duplicate memberships as truth |
| `index_revision_access_policy` | index revision ID, policy ID/version, assignment authority, record source, load time, effective-from/to, revoked/status | Versioned effective relationship used to determine the policy governing a routable revision; policy meaning remains in the authoritative authorization system |
| `namespace_card_revision` | card ID/version, index revision, title/description, controlled tags, example queries, embedding contract for card vector, generation provenance, status | Derived serving projection; rebuildable; policy, source, and governed-concept eligibility resolve through its index revision, not card text |
| `catalog_event` | event ID, entity/revision, event type, actor/process, record source, load time, payload digest | Audit/outbox lineage |

### Required lifecycle representation

- **Rename:** preserve old `namespace_address`; create/associate a new address and index revision. A display-title change is a card/source Satellite revision, not a physical rename.
- **Reindex:** append `index_revision` tied to the same source revision when only chunk/schema/embedding contracts change; never overwrite prior deployment lineage.
- **Stale source:** record observed freshness separately from policy evaluation. Do not infer the allowed staleness threshold.
- **Deletion:** mark routing eligibility false immediately in canonical state, tombstone/delete derived cards, and record remote deletion separately. Catalog history retention and source-data erasure are distinct policies.
- **Model migration:** create a new embedding contract and index revision; old and new deployments may coexist but are different compatibility cohorts.
- **Access-policy change:** append a new effective `index_revision_access_policy` relationship (and close/revoke the prior assignment according to the authoritative policy event), invalidate routing caches/cards, and default deny until both catalog selection and namespace-local enforcement resolve the same current policy version.

For routing, the required joins are explicit: a card identifies one `index_revision`; policy eligibility resolves through `index_revision_access_policy`; governed source provenance resolves through `index_revision_source_revision`; and governed concept narrowing resolves from those source revisions through `source_revision_concept_ref`. Effective-time and status predicates come from the relationship records and their named authorities, not namespace/card text. The exact temporal-overlap, cardinality, and policy-conflict rules remain blocked semantics rather than implied schema defaults.

### Provenance minimum

Every routed result should be traceable through:

```text
query decision
  -> namespace_card_revision and routing score/reason
  -> index_revision and namespace_address
  -> source_revision and reviewed plan/artifact identity
  -> (namespace_id, row_id, source/page/chunk hashes)
  -> governed source and optional Data Vault Hub/Link references
```

An LLM-generated description, example query, tag, or concept must also retain generation method/model version, input revision, timestamp, confidence where meaningful, and human-review state.

## Candidate routing and fallback design

### Routing flow

1. **Resolve principal and requested scope.** Obtain tenant/security context and explicit user constraints from the authoritative auth/application layer.
2. **Default-deny eligibility query.** Select only current routable index revisions whose policy permits the principal. Exclude pending, tombstoned, failed, superseded-only, or unverified records.
3. **Compatibility partition.** Enforce region/API boundary, embedding contract, vector/schema contract, required ACL attributes, and retrieval-profile support. Under current Buoy behavior, retain only one shared model/precision cohort.
4. **Exact narrowing.** Apply explicit namespace IDs, governed source/concept keys, source kind, controlled tags, and caller scope. Exact user selection should remain inspectable and should not be silently broadened.
5. **Semantic card scoring.** Search versioned cards only within eligible IDs. Use title/description plus governed tags and human-reviewed example queries; preserve scores and reasons. Do not include sensitive card text in unauthorized logs/output.
6. **Bounded selection.** Select at most `K` namespaces and optionally require per-route confidence/margin. `K` and thresholds are experiment parameters, not product defaults.
7. **Revalidate.** Before retrieval, confirm card revision and policy/contract versions still match canonical catalog state.
8. **Execute and fuse.** Reuse current sequential per-namespace retrieval and namespace-qualified RRF for a compatible cohort. Preserve all-or-nothing failure as the current contract unless separately superseded.
9. **Audit.** Record candidate counts, selected revision IDs, deterministic exclusions, scorer/version, latency, calls, and ACL-safe outcome without logging sensitive query/card content unnecessarily.

### Conservative fallback

- If explicit authorized namespaces are supplied, use those after compatibility checks.
- If semantic routing is unavailable or below confidence, fall back to an authorized exact taxonomy/source match only when it is unambiguous.
- Otherwise return a no-safe-route/clarification result. **Do not fan out to all visible namespaces.**
- Empty eligibility, missing policy, stale card version, or contract mismatch fails closed.
- Whether users may override freshness warnings, and whether partial namespace success is acceptable, remain unresolved semantics.

### Explicit non-goals

- Making Turbopuffer, a vector index, namespace naming convention, inferred tag, or LLM-generated concept the Raw Vault authority.
- Automatic all-namespace fan-out.
- Cross-tenant concept aggregation or ACL inference.
- Live mutation, schema migration, catalog/UI/CLI implementation, or selection of a managed proprietary catalog.
- Replacing namespace-local ANN/BM25/ranking or current explicit selection before eval evidence.
- Defining business keys, deletion retention, freshness SLOs, or authorization policy by convention.

## Offline evaluation design

### Dataset

Build a versioned, human-reviewed fixture with:

- queries labeled with **required**, **acceptable**, and **must-not-select** namespace/index revision IDs;
- actor/tenant/group context and authoritative eligibility result;
- query class (exact source, domain taxonomy, ambiguous, semantic paraphrase, multi-source, stale-only, no-match);
- compatibility cohorts (model/dimension/schema/profile);
- lifecycle cases (renamed, superseded, reindexed, deleted/tombstoned, stale, policy changed);
- adversarial cards whose text is highly similar but unauthorized or incompatible;
- final evidence relevance/citation labels for selected namespaces where available.

Labels must name the governing source/business authority. Assistant-generated labels can exercise plumbing but cannot serve as final quality ground truth.

### Baselines and candidates

1. Current explicit human-selected namespaces (quality oracle/operational baseline, not automatic routing).
2. Namespace-ID substring/exact source lookup.
3. Exact controlled taxonomy and source-kind filtering.
4. Semantic namespace-card top-K.
5. Hybrid exact gates plus semantic cards.
6. Optional learned classifier only after enough reviewed labels; compare it against the simpler hybrid.

### Metrics

- **Namespace-selection recall@K:** fraction of required namespaces selected; also report all-required success rate.
- **Selection precision / over-selection:** selected acceptable-or-required divided by selected; excess namespaces per query and fan-out distribution.
- **ACL safety:** unauthorized selection/retrieval count and rate; target must be exactly zero. Report metadata-card exposure separately.
- **Compatibility safety:** incompatible revision selections; target zero.
- **Lifecycle safety:** tombstoned/superseded/stale selections, reported by policy-defined category rather than one invented threshold.
- **Latency:** router p50/p95/p99, end-to-end p50/p95, cold/warm where measurable, and per-namespace tail contribution.
- **Cost/load:** card-search calls, namespace queries, query embeddings per cohort, candidates read, bytes/tokens, and estimated/self-hosted compute cost.
- **Final retrieval/answer quality:** existing Buoy Precision@5, Recall@10, NDCG@10, MRR@10/composite where applicable, plus answer correctness, citation support/coverage, and unauthorized evidence count. Routing recall alone is insufficient.
- **Calibration/stability:** confidence vs success, no-route rate, and selection churn across card/model revisions.

Promote no router on average-only gains. Require zero ACL/compatibility violations, no named critical corpus regression, bounded fan-out, and a predeclared quality/latency/cost improvement gate.

### Held-out evaluation protocol

Before generating or tuning cards, split reviewed queries into development and held-out test sets, stratified by query/lifecycle class and grouped by source or governed concept where possible so near-duplicates cannot cross the boundary. Freeze the test labels and keep them unavailable to card authors and parameter tuning. Use development data only to choose card wording, scorer/model, `K`, confidence thresholds, and promotion gates; then freeze the card corpus, catalog fixture revision, embedding/scorer version, code revision, seeds, and all parameters before one final held-out evaluation. If the fixture is too small for a credible single split, use grouped cross-validation for development and still reserve an untouched final test slice rather than reporting development folds as promotion evidence.

Report per-query results and bootstrap confidence intervals for recall, precision/over-selection, latency, and final-quality deltas. Safety outcomes remain exact counts with zero allowed rather than averages hidden by intervals. Repeat nondeterministic scoring/answer stages under predeclared seeds and report each run plus aggregate uncertainty; deterministic stages need one reproducible run. Compare every candidate with exact-only routing on the identical held-out queries and compatibility/ACL fixture. Any post-test card, threshold, model, or label change starts a new version and requires a new untouched test set; the prior held-out result becomes development evidence only.

### What can be tested without live Turbopuffer access

- Candidate relational constraints, temporal/lifecycle transitions, append-only revision behavior, and Data Vault key mappings using fixtures.
- Default-deny ACL and compatibility predicates, exact routing, fallback, cache invalidation, and adversarial leak cases.
- Namespace-card construction/versioning and deterministic in-memory/local embedding scorer comparisons.
- Router metrics and end-to-end fusion using cached/fake namespace result lists.
- Current Buoy contract compatibility: one embedding cohort, sequential calls, failure attribution, namespace-qualified RRF.
- Rebuild/idempotency behavior between canonical fixture records and derived card documents without sending them.

Without live access, this study cannot establish Turbopuffer cold/warm latency, account-specific namespace metadata behavior, filter performance, service cost, remote schema drift, semantic card quality on a real corpus, or end-answer gains from live selected namespaces.

## Local implications

1. `buoy namespaces` remains identifier discovery only. A catalog router should be additive and must not reinterpret listing as semantic registration.
2. Current multi-namespace retrieval is a useful execution baseline after selection: one embedding, sequential namespace-local retrieval, whole-command failure, and deterministic namespace-qualified RRF.
3. The catalog cannot infer model semantics from Turbopuffer schema or the current namespace prefix. Current plans have model/precision but successful plan artifacts are ephemeral, so durable registration would need a separately ratified lifecycle integration.
4. Current applied state is scoped by `(site_id, namespace)` and stores current rows plus compact successful-run summaries. It is not a global catalog and deliberately lacks full revision history.
5. Current remote rows carry strong chunk/source hashes and repository/file/PDF provenance. They do not carry a catalog/index revision ID, access policy, governed business key, or immutable embedding-contract ID.
6. Current ranking defaults depend on namespace prefix. A future catalog can make source class/profile explicit, but must preserve active defaults unless a separate spec changes them.
7. The docs claim returned tags, while inspected retrieval attributes/result shape do not request/expose tags; this known drift has a separate owner and is not widened into this research ticket.

## Recommendations

1. **Choose Architecture A only as the smallest experiment hypothesis:** fixture-backed relational canonical records plus a rebuildable card projection. Do not select a production platform yet.
2. **Start offline:** model 20–50 representative namespace revisions and a reviewed routing dataset; compare exact taxonomy with semantic-card and hybrid routing. No live write is needed.
3. **Make authority explicit:** physical namespace, governed source, Data Vault business concept, and indexed revision get separate IDs. Never derive a business Hub key from namespace text or semantic similarity.
4. **Gate before score:** authorization, lifecycle status, and compatibility are deterministic fail-closed predicates. Semantic routing only orders eligible candidates.
5. **Keep the card index disposable:** canonical revision/version fields must allow exact rebuild and stale-card rejection. Turbopuffer may later host cards, but must not be the only history source.
6. **Adopt a full open-source catalog only against a named integration need:** DataHub/OpenMetadata for broad metadata governance, or OpenLineage/Marquez for job-run-dataset lineage. None is required to prove routing value.
7. **Require eval evidence before implementation architecture ratification:** zero ACL/compatibility errors, high required-namespace recall, bounded over-selection, and non-regressing final answer quality at acceptable latency/cost.

## Smallest proposed experiment

Create no service and perform no live operation. In a later separately authorized ticket:

- represent candidate catalog rows in a temporary/local SQLite or DuckDB fixture;
- generate one versioned namespace card per fixture index revision;
- implement only an offline evaluator for exact, semantic-card, and hybrid selection;
- use a local open-source embedding model already compatible with project policy, or deterministic precomputed vectors;
- mock namespace retrieval with cached/fake ranked lists to measure downstream fusion and answer-retrieval metrics;
- stop unless the hybrid beats exact-only routing under predeclared recall, ACL, fan-out, latency, and quality gates.

This experiment tests the routing hypothesis without choosing PostgreSQL, Turbopuffer cards, DataHub, OpenMetadata, or a Data Vault loading architecture.

## Blockers and unresolved semantics

Research is not blocked, but architecture selection and implementation are blocked on user/authority ratification of:

- the governed source business key for each source type and whether an existing Raw Vault owns it;
- the authoritative organization/account/tenant boundary for a physical namespace address;
- principal, group, public-access, policy-reference, and cross-namespace ACL semantics, including metadata-card visibility;
- which business concepts already have governed Hub keys and how inferred candidate concepts are reviewed/promoted;
- freshness SLOs, stale-routing behavior, and who may override a warning;
- rename versus replacement semantics and whether remote namespace IDs are ever reused;
- deletion, tombstone, audit-history, privacy-erasure, and catalog/card retention rules;
- whether whole-command failure remains correct after automatic selection;
- production authority/store and operational owner;
- reviewed route/evidence labels and quantitative promotion thresholds.

No recommendation above ratifies these values.

## Limits and confidence

- **High confidence:** Turbopuffer queries are namespace-local; namespace metadata lacks application business/embedding/ACL semantics; current Buoy explicitly selects compatible namespaces and lacks a catalog; deterministic authorization/compatibility must precede semantic scoring.
- **Medium confidence:** Architecture A is the smallest production-shaped authority boundary. It still needs an offline experiment and operational review.
- **Low/unmeasured confidence:** semantic namespace cards improve Buoy's final answer quality or cost on its actual fleet; no live corpus or human-labeled route set was available.
- Data Vault public material is incomplete relative to the full Data Vault 2.0 body of knowledge, and local records do not establish an enterprise Raw Vault, business-key steward, or loading standard.
- Open-source project documentation describes supported models, not independent operational benchmarks. Exact release compatibility, scale, security posture, and transitive licensing were not validated.
- Turbopuffer documentation is vendor documentation and current limits/features may change. No live account behavior was measured.
- The missing requested root `context.md` and `plan.md` could contain non-durable context not recoverable here; no absent semantics were inferred from them.
