Status: done
Created: 2026-07-15
Updated: 2026-07-15

# Data Vault Cross-Namespace Concept Graph

## Scope correction — no Data Vault architecture

The user clarified after this research closed that Data Vault was only an analogy for stable concepts and relationships. `.10x/decisions/data-vault-is-analogy-not-architecture.md` governs: Buoy will not build or require hubs, links, satellites, business-key mappings, warehouse authority, or Data Vault loading.

Retain this record's findings on concept cards, entity resolution, reified source-supported assertions, typed relationships, provenance, temporal validity, ACLs, correction/deletion, relational adjacency, graph alternatives, and evals. Replace “approved Hub/Link mapping” in future synthesis with optional mapping to project-governed concept identities; no warehouse identity is assumed.

## Question

What is the smallest provenance-preserving concept/entity layer that could improve retrieval across many Buoy namespaces while keeping formal Data Vault 2.0 hubs, links, business keys, satellites, lineage, and history authoritative?

This investigation compares documented product behavior and open-source implementations, proposes storage-neutral candidate models and evals, and recommends a bounded experiment. It does **not** select a graph store, create a product contract, or authorize inferred entities to become Data Vault authority.

## Sources and methods

Research was performed on 2026-07-15. The work combined complete reading of the governing ticket, parent plan, preliminary research, current relevant Buoy source, active identity/provenance records, official product documentation, current open-source documentation, repository source, and license files. GitHub repository metadata and current default-branch source were also inspected. No live Buoy/Turbopuffer data or service was read or mutated.

The task named `context.md` and `plan.md` at the worktree root, but neither file existed. The executable ticket and its parent plan were present and were treated as the governing records.

### Local authority inspected

- `.10x/tickets/done/2026-07-15-research-data-vault-concept-graph.md`
- `.10x/tickets/done/2026-07-15-semantic-retrieval-research-plan.md`
- `.10x/research/2026-07-15-metadata-tagging-graphs-and-data-vault.md`
- `.10x/specs/explicit-multi-namespace-retrieval.md`
- `.10x/specs/buoy-local-compatibility.md`
- `.10x/decisions/local-document-ingestion-uses-markitdown.md`
- `.10x/decisions/local-pdf-ingestion-uses-markitdown.md`
- `src/buoy_search/chunker.py`
- `src/buoy_search/plan_artifacts.py`
- `src/buoy_search/retriever.py`
- `src/buoy_search/applied_state.py`

### External sources

Chief (`chief.bot`; product documentation, not implementation authority):

- https://help.chief.bot/articles/2999623-how-chief-creates-concepts
- https://help.chief.bot/articles/6258614-concepts-overview
- https://help.chief.bot/articles/7283674-how-to-navigate-concepts-view
- https://help.chief.bot/articles/9528674-how-to-view-concept-details
- https://help.chief.bot/articles/7466380-why-is-my-concept-showing-as-unavailable
- https://help.chief.bot/articles/1047959-data-collections-overview
- https://help.chief.bot/articles/0485181-how-to-manage-scope

Cognee:

- https://docs.cognee.ai/core-concepts/further-concepts/node-sets
- https://docs.cognee.ai/core-concepts/main-operations/cognify
- https://docs.cognee.ai/core-concepts/main-operations/search
- https://github.com/topoteretes/cognee
- https://github.com/topoteretes/cognee/blob/main/LICENSE

Graphiti:

- https://github.com/getzep/graphiti/blob/main/README.md
- https://github.com/getzep/graphiti/blob/main/graphiti_core/nodes.py
- https://github.com/getzep/graphiti/blob/main/graphiti_core/edges.py
- https://github.com/getzep/graphiti/blob/main/graphiti_core/graphiti.py
- https://help.getzep.com/graphiti/core-concepts/communities
- https://github.com/getzep/graphiti/blob/main/LICENSE

Microsoft GraphRAG:

- https://microsoft.github.io/graphrag/index/overview/
- https://github.com/microsoft/graphrag/blob/main/docs/index/default_dataflow.md
- https://github.com/microsoft/graphrag/blob/main/docs/index/outputs.md
- https://github.com/microsoft/graphrag/blob/main/docs/index/methods.md
- https://github.com/microsoft/graphrag/blob/main/docs/query/overview.md
- https://github.com/microsoft/graphrag/blob/main/docs/query/local_search.md
- https://github.com/microsoft/graphrag/blob/main/docs/query/global_search.md
- https://github.com/microsoft/graphrag/blob/main/LICENSE

LlamaIndex property graphs:

- https://developers.llamaindex.ai/python/framework/module_guides/indexing/lpg_index_guide/
- https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/indices/property_graph/base.py
- https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/graph_stores/types.py
- https://github.com/run-llama/llama_index/blob/main/LICENSE

RAGFlow:

- https://ragflow.io/docs/dev/construct_knowledge_graph
- https://github.com/infiniflow/ragflow/blob/main/docs/guides/dataset/advanced/construct_knowledge_graph.md
- https://github.com/infiniflow/ragflow/blob/main/rag/graphrag/general/index.py
- https://github.com/infiniflow/ragflow/blob/main/rag/graphrag/entity_resolution.py
- https://github.com/infiniflow/ragflow/blob/main/LICENSE

Data Vault and graph/relational storage:

- https://www.databricks.com/blog/what-is-data-vault
- https://www.postgresql.org/docs/current/queries-with.html
- https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- https://www.postgresql.org/about/licence/
- https://duckdb.org/docs/stable/sql/query_syntax/with.html
- https://github.com/duckdb/duckdb/blob/main/LICENSE
- https://www.sqlite.org/lang_with.html
- https://www.sqlite.org/copyright.html
- https://github.com/apache/age
- https://github.com/apache/age/blob/master/LICENSE
- https://github.com/apache/incubator-hugegraph
- https://github.com/apache/incubator-hugegraph/blob/master/LICENSE
- https://github.com/neo4j/neo4j/blob/dev/LICENSE.txt
- https://github.com/kuzudb/kuzu

## Findings

### 1. Current Buoy identity and provenance are sufficient anchors for an experiment, not a semantic authority

Buoy currently has several distinct identities that must not be collapsed:

| Layer | Current identity/provenance | Local source implication |
| --- | --- | --- |
| Source | `site_id`, normalized `base_url`, source kind, repository/file/PDF source fields | A source coordinate is deterministic and path-private for local files. It is not a Data Vault business key unless separately governed as one. |
| Namespace | explicit Turbopuffer namespace | Cross-namespace identity must include namespace; current retrieval does not infer a catalog, ACL, or per-namespace model contract. |
| Page/document revision | `canonical_url`, `page_hash`/`source_hash`, source metadata | `source_hash` written to a Turbopuffer row is the page hash in the generic-site apply path. |
| Chunk revision | remote `ts_*` row ID, `chunk_hash`, `embedding_text_hash`, section, chunk index | The remote row ID is derived from site, canonical URL, section, content hash, and duplicate ordinal. Intermediate `jf_*` chunk IDs are not the applied generic-site row identity. |
| Indexing run | `plan_id`, `artifact_hash`, embedding model/precision, `applied_at` | These fields can identify the indexed derivation, but they do not identify a semantic extractor or taxonomy version. |
| Applied lifecycle | per-namespace DuckDB ledger, row status (`active`, `retained_stale`, `deleted`), apply summaries | This ledger is an incremental-index record, not a cross-namespace graph or Data Vault warehouse. |

The minimum evidence pointer for derived concept work is therefore a namespace-qualified chunk revision, not a URL or label alone:

```text
(namespace_id, row_id, chunk_hash, page_hash, canonical_url, plan_id)
```

`row_id` preserves the current applied identity; hashes distinguish revisions and support deletion/reprocessing checks. The embedding contract and semantic extraction contract are separate: an extraction run also needs extractor name/version, prompt/schema hash, model identity, taxonomy/ontology version, and extraction time.

Buoy's current `tags` are deterministic structural labels. They must not be treated as extracted entities, controlled taxonomy assignments, graph nodes, or Data Vault hubs without a separately ratified mapping.

### 2. Product and framework behavior

#### Chief Concepts: useful product shape, opaque implementation

Chief documents a first-class concept object rather than a tag array:

- It scans files for recurring entities/themes, uses contextual relevance and proximity, and promotes material over a relevance threshold.
- A concept aggregates source snippets/chunks across files, exposes a title/summary, related concepts, contributing source files, citation count, timestamps, and a citation timeline.
- Concepts can be automatic or user-defined by a description; defined concepts gather relevant chunks.
- Concepts and Collections are project-scoped. Concepts can scope chat and can be explored in a graph.
- Adding content continuously enriches/re-evaluates concepts. Deleting a file removes that file's references. Automatically generated concepts can become unavailable as underlying knowledge changes; manually defined concept identity is durable even though supporting knowledge changes.

This is a strong interaction/provenance reference: concept cards, evidence timelines, explicit scope, and source deletion are more important than graph visualization. Chief is proprietary/hosted, its storage schema, extraction prompts, exact entity resolution, ACL enforcement, thresholds, temporal semantics, and deletion implementation are not documented. It is therefore a behavior comparison only, not a reusable open-source component or authority.

#### Cognee: graph-native memory with lightweight NodeSet scoping

Cognee (Apache-2.0) documents a pipeline that classifies documents, checks dataset write permission, chunks, extracts/deduplicates graph nodes and edges, summarizes chunks, embeds data points, and writes graph/vector stores. Its legacy search surface supports chunk, summary, graph, hybrid, temporal, and Cypher-oriented modes.

NodeSets are the clearest reusable idea: ingest-time tags become first-class `NodeSet` nodes connected to documents, chunks, and extracted entities by `belongs_to_set`; retrieval can filter with AND/OR NodeSet rules. This shows how a structural scope can become explicit graph structure without pretending it is a business entity.

Operationally, Cognee is a multi-store orchestration system with LLM, graph, vector, and relational concerns. Documentation warns that dataset isolation requires backend access-control configuration. That makes its permission behavior configuration-dependent, not proof that arbitrary cross-dataset traversals are safe. The inspected docs did not establish a source-revision retraction algorithm, contradiction model, or exact cascade behavior for deleting one document from a deduplicated entity graph.

#### Graphiti: strongest temporal/provenance reference, but a framework rather than Buoy's model

Graphiti (Apache-2.0) models:

- `EpisodicNode`: raw text/message/JSON/fact input with `group_id`, source description, created time, source-valid/reference time, content, metadata, and referenced entity-edge IDs;
- `EntityNode`: deduplicated entity with evolving summary;
- `EntityEdge`: a fact/relationship with fact text/embedding, contributing episode IDs, `created_at`, `valid_at`, `invalid_at`, `expired_at`, reference time, and attributes;
- `MENTIONS`: episode-to-entity provenance;
- communities with summaries, plus group-scoped search and community construction.

Graphiti distinguishes ingestion time from source/reference time and invalidates superseded facts instead of erasing temporal history. It supports incremental episode ingestion and hybrid semantic/keyword/graph retrieval. These are directly relevant patterns for contradictory and changing facts.

Its current source includes `remove_episode`: it deletes the episode, entities mentioned only by that episode, and relationship edges whose first recorded producing episode is the deleted episode. That behavior is useful evidence that cascade deletion is non-trivial; Buoy must test shared-edge support explicitly rather than assume a framework's episode deletion exactly matches retention and multi-support requirements.

Graphiti requires an LLM/embedding provider and a graph backend. Current documented backends include Neo4j, FalkorDB, Neptune, and deprecated Kuzu. Kuzu is explicitly deprecated in Graphiti because upstream is no longer maintained; the Kuzu GitHub repository is archived. Graphiti's `group_id` is a partition/search scope, not a complete per-edge ACL policy or proof against aggregate leakage.

#### Microsoft GraphRAG: best global-query reference, batch-oriented derived tables

GraphRAG (MIT) constructs Documents, TextUnits, Entities, Relationships, optional Claims/Covariates, hierarchical Communities, and Community Reports. TextUnits are linked to documents and are explicitly retained as source references for extracted knowledge. Entities and relationships retain `text_unit_ids`; claims carry source text, text-unit ID, status, and optional start/end dates.

Default entity merging uses equal title and type; relationship merging uses source and target, followed by LLM summarization of collected descriptions. Those rules are convenient indexing mechanics, not safe business entity resolution. Optional claim extraction is off by default and documented as requiring prompt tuning.

Retrieval modes are query-class-specific:

- local search starts from semantically matched entities and gathers related entities, relationships, claims, reports, and text units;
- global search map-reduces community reports for corpus-wide questions and is resource-intensive;
- DRIFT broadens local search with community context;
- basic vector RAG exists as a comparison baseline.

Default storage is Parquet tables plus a configured vector store; a graph database is not required. Standard indexing is LLM-heavy, and the project warns that indexing can be expensive. Current docs estimate graph extraction at roughly 75% of indexing cost; FastGraphRAG trades richer extraction for noun-phrase/co-occurrence graphs and lower cost/noisier structure. Incremental output fields exist, but the inspected docs did not establish a complete source deletion/retraction and ACL propagation contract. Version upgrades may require config regeneration or index migration.

#### LlamaIndex PropertyGraphIndex: flexible orchestration, lifecycle delegated to the application/store

LlamaIndex (MIT) applies one or more graph extractors to each source chunk and attaches nodes/relations as chunk metadata. It supports simple LLM triples, implicit relationships already present on nodes, dynamic open-schema extraction, and strict schema extraction. It adds `triplet_source_id` to extracted nodes and relations, providing a direct source-node pointer.

Retrieval can combine synonym/keyword lookup, vector graph-node retrieval plus path expansion, text-to-Cypher, constrained Cypher templates, and custom retrievers. Source chunk text may be included with matching paths. If the graph store lacks vector search, an additional vector store is required.

This is useful as an orchestration vocabulary, not a finished governance layer. Default entity node identity is name-derived, and relation identity alone is too weak for contradictory, temporal, or multi-evidence assertions unless customized. Graph-store interfaces expose deletion primitives, but the inspected guide/source did not document an end-to-end source-revision cascade across graph, vector store, summaries, aliases, and ACLs. Free-form LLM-generated Cypher also enlarges the security boundary; constrained templates are safer.

#### RAGFlow graphs: integrated retrieval feature with an explicit stale-deletion warning

RAGFlow (Apache-2.0) constructs one unified graph across files in a dataset and stores graph artifacts as chunks in its document engine (Elasticsearch or Infinity), rather than requiring a separate graph database. It offers General (GraphRAG prompts), Light (lower resource use), optional LLM entity resolution, and optional community reports. Graph generation is explicitly documented as memory-, compute-, and token-intensive.

A newly uploaded file automatically updates the graph. Removing a related file does **not** update the graph until the dataset graph is regenerated. The entire generated graph can be deleted, and graph export is not supported. These are decisive lifecycle caveats for Buoy: an index that cannot promptly retract one source is unsafe for ACL revocation and deletion-sensitive provenance, regardless of retrieval quality.

### 3. Comparison summary

| Approach | License / self-hosting | Construction and identity | Retrieval | Updates/deletion | Operational shape | Buoy lesson |
| --- | --- | --- | --- | --- | --- | --- |
| Chief Concepts | Proprietary hosted product; not an open-source candidate | Automatic/defined project-scoped concepts from relevant source chunks; internals opaque | Concept-scoped chat, cards, related-concept graph | Enriches on add; file references removed on delete; dynamic concepts may disappear | Managed/undocumented | Copy the evidence-card and lifecycle expectations, not the implementation. |
| Cognee | Apache-2.0; self-hostable | Documents/chunks/summaries/entities/edges; NodeSets become nodes | Vector, graph, hybrid, temporal, Cypher; dataset/NodeSet scopes | Incremental processing documented; exact shared-entity delete cascade not established in inspected docs | Relational + graph + vector + LLM stack | NodeSets are a useful explicit scope model; ACL configuration remains critical. |
| Graphiti | Apache-2.0; self-hostable with supported backend | Episodes, entities, temporal fact edges, communities; group partition | Hybrid semantic, keyword, traversal, graph distance | Incremental; fact invalidation/history; source includes episode cascade deletion | LLM/embedder plus graph backend; backend-specific behavior | Best temporal/provenance reference; do not inherit group IDs as complete ACLs. |
| Microsoft GraphRAG | MIT; self-hostable | Batch tables for documents/text units/entities/relationships/claims/communities/reports | Local, global, DRIFT, basic vector baseline | Incremental fields/workflows exist; complete source deletion/ACL contract not established | Parquet + vector store + substantial LLM/NLP processing | A graph DB is unnecessary for global-search experiments; entity merge rules are not authority. |
| LlamaIndex PropertyGraphIndex | MIT; self-hostable orchestration | Chunk extractors create nodes/relations with source-node IDs | Vector paths, synonyms, templates, text-to-Cypher, custom | Store primitives exist; lifecycle is application/backend responsibility | Library plus chosen graph/vector/LLM components | Useful extractor/retriever interfaces, insufficient governance by default. |
| RAGFlow | Apache-2.0; self-hostable full application | Unified dataset graph, optional resolution/reports, graph stored as document-engine chunks | Integrated dataset chat/agent graph retrieval | Adds update graph; source removal needs regeneration; whole-graph delete; no export | Large application stack with document engine and supporting services | Its deletion limitation fails a strict source-retraction requirement unless regeneration is acceptable and proven. |

All five open-source systems are derived indexes/orchestration layers. None supplies authority for creating formal Data Vault hubs or links from an LLM guess.

### 4. Data Vault 2.0 must remain upstream authority

The inspected Data Vault explanatory material consistently describes:

- **Hubs**: stable business keys and core business identity;
- **Links**: durable relationships among hub business keys;
- **Satellites**: descriptive/contextual attributes and history, including source/load lineage.

The graph analogy is useful but dangerous. `EntityCandidate` is not a Hub, an extracted `RELATES_TO` is not a Link, and a generated summary is not a Satellite. A safe derived layer may reference approved Data Vault identities, but must never mint or merge them.

Candidate mapping:

| Data Vault authority | Derived concept-layer representation | Permitted direction |
| --- | --- | --- |
| Hub key/hash key | `VaultHubRef` node containing an opaque approved vault identifier and vault model/version | Imported read-only from authoritative warehouse/catalog. No LLM creation. |
| Link key/hash key | `VaultLinkRef` node or approved relationship reference | Imported read-only. Derived assertions may support or contradict a view but cannot change the link. |
| Satellite row/history | `VaultObservationRef` with load/effective/source metadata | Referenced as governed evidence where authorized; not summarized into authority. |
| Raw document/chunk | `EvidenceRevision` | Supports candidate mentions/assertions and remains citeable. |
| LLM entity/concept | `EntityCandidate` / `ConceptCard` | Derived, versioned, retractable, and explicitly non-authoritative. |
| LLM relationship | `RelationshipAssertion` | Derived claim with evidence and temporal fields, never a vault Link. |
| Candidate hub match | `VaultResolutionAssertion(kind=maps_to_hub)` | Remains pending/rejected/approved under a separately ratified human/rule workflow; only approved mapping assertions may be used as a derived projection. |

Even an approved mapping preserves separate identities: approval governs only the derived assertion that one candidate maps to one imported reference. It neither ratifies, creates, merges, nor modifies the Hub, Link, Observation, business key, or warehouse relationship; the derived entity is never rewritten into the Hub. Retraction or deletion of a mapping changes only the derived assertion and its projections. The full Data Vault 2.0 standard was not inspected, so loading patterns, hash-key conventions, effectivity satellites, record-source rules, and business-vault policy require Data Vault specialist review before implementation.

### 5. Candidate storage-neutral node and edge model

The model intentionally reifies assertions instead of placing provenance on a bare entity-to-entity edge. Reification permits contradictory facts, multiple sources, independent ACLs, temporal validity, confidence, review, and retraction.

#### General assertion contract

`DerivedAssertion` is the logical supertype for `MentionAssertion`, `TaxonomyAssignmentAssertion`, `VaultResolutionAssertion`, `RelationshipAssertion`, and `AliasAssertion`. It need not be a separate physical table or graph label, but every subtype has the same identity, provenance, policy, time, and lifecycle contract:

- `assertion_id` is a generated opaque, immutable ID. Endpoint values, names, confidence, or content hashes are not assertion identity and cannot cause two assertions to merge. A correction creates a new assertion ID and links the old assertion with `SUPERSEDED_BY`; it never edits history in place.
- Each assertion has exactly one typed `ASSERTS_SUBJECT` and one typed `ASSERTS_OBJECT`. Subtype endpoint constraints are given below. Every machine-produced assertion has exactly one `DERIVED_FROM_RUN`; governed review records actor/rule, decision time, and `pending`/`approved`/`rejected` state separately.
- `SUPPORTED_BY` links to every exact `EvidenceRevision` used to make or retain the assertion. Machine assertions require at least one support. A separately governed manual assertion would still require a recorded actor/action provenance contract before implementation; this research does not define one.
- Common fields are `assertion_type`, predicate/kind, confidence plus calibration contract where applicable, assertion text or source span, `policy_ref`, `security_partition`, `valid_from`/`valid_to`, `observed_at`, `retracted_at`, review/decision state, lifecycle state (`active`, `retracted`, or `superseded`), retraction reason, and supersession pointer. Nullable event-valid fields mean “not stated by the source,” not “valid forever.” Run timestamps provide index-revision time.
- Assertion authority is always **derived and non-warehouse-authoritative**. Approval may activate a governed projection of that assertion; it does not elevate the assertion, its endpoints, or its evidence into taxonomy or Data Vault authority.

Source correction or deletion retracts the affected `SUPPORTED_BY` links and creates an explicit lifecycle event. An assertion with no remaining permitted support is retracted; one whose text, span, confidence, endpoints, or policy changes is superseded by a new assertion. Retraction propagates to retrieval, summaries, embeddings, adjacency projections, and caches, while the minimum permitted audit tombstone retains assertion identity and lineage.

#### Nodes

| Node | Authority class | Minimum candidate fields and endpoint contract |
| --- | --- | --- |
| `NamespaceRef` | current indexed-structure reference | `namespace_id`, source/catalog reference, embedding contract reference, policy reference, indexed revision/status |
| `SourceRef` | source/provenance reference | `site_id`/source ID, source kind, canonical base identity, policy reference |
| `DocumentRevision` | source-derived evidence coordinate | namespace, canonical URL/synthetic file URI, page hash, source metadata, observed/applied time, retraction state |
| `EvidenceRevision` | source-derived evidence coordinate | `(namespace_id,row_id,chunk_hash)`, page hash, section/chunk metadata, plan ID, content locator, extraction eligibility, policy reference |
| `EntityCandidate` | derived | generated opaque ID, normalized display name, candidate type, security partition, resolution cluster version, created/updated/retracted state |
| `ConceptCard` | derived | opaque ID, definition/description, automatic vs defined, security partition, summarizer contract, created/updated/retracted state |
| `DerivedAssertion` | derived logical supertype | Common immutable identity, provenance, temporal, ACL/policy, review, and lifecycle fields defined above. |
| `MentionAssertion` | derived assertion | Subject: exact `EvidenceRevision`; object: one `EntityCandidate`. Type-specific fields: original span offsets/text, mention type, normalization version. Its subject evidence is also mandatory `SUPPORTED_BY`; deletion of that revision retracts the mention. |
| `TaxonomyAssignmentAssertion` | derived assertion | Subject: one `EvidenceRevision`, `EntityCandidate`, or `ConceptCard`; object: one imported `TaxonomyTermRef`. Type-specific fields: taxonomy/version, assignment method, score/calibration. Approval governs only the assignment, never the term; taxonomy migration creates new assertions and supersedes old assignments. |
| `VaultResolutionAssertion` | derived assertion | Subject/object pairs are constrained by `kind`: `maps_to_hub` is `EntityCandidate` → imported `VaultHubRef`; `maps_to_link` is `RelationshipAssertion` → imported `VaultLinkRef`; `maps_to_observation` is `EvidenceRevision` or `RelationshipAssertion` → imported `VaultObservationRef`. Type-specific fields: resolver contract, candidate score, decision state. Approval activates only the mapping projection and never creates, ratifies, merges, or mutates a warehouse Hub, Link, Observation, key, or relationship. |
| `RelationshipAssertion` | derived assertion | Subject: one `EntityCandidate`; object: one `EntityCandidate` or typed literal value; type-specific fields: predicate ID, assertion text, direction, confidence/calibration. |
| `AliasAssertion` | derived assertion | Subject/object: candidate pair or candidate/name value; type-specific fields: alias kind, score, resolver contract, decision state. It supports reversible resolution and never destructively coalesces candidates. |
| `TaxonomyTermRef` | governed only if imported from approved taxonomy | taxonomy/version/term ID, label, status; inferred assignment remains a separate `TaxonomyAssignmentAssertion` |
| `VaultHubRef` / `VaultLinkRef` / `VaultObservationRef` | warehouse-authoritative reference | opaque identifiers imported from an approved warehouse/catalog plus model/version; no generated business key and no derived write path |
| `CommunitySummary` | derived aggregate | member-set hash, summarizer contract, source policy domain, evidence closure, generated/retracted time |
| `ExtractionRun` | derivation metadata | extractor/model/prompt/schema/taxonomy versions, code revision, start/end, parameters, cost/token counters |

#### Edges

| Edge | Meaning and required controls |
| --- | --- |
| `NAMESPACE_CONTAINS` | Namespace to document/evidence revision; deterministic structural relation. |
| `REVISION_OF` / `SUPERSEDES` | Revision chain; never overwrite prior evidence silently. |
| `ASSERTS_SUBJECT` / `ASSERTS_OBJECT` | Mandatory typed endpoints for every `DerivedAssertion`; subtype constraints above are normative and keep contradictory assertions independent. |
| `SUPPORTED_BY` | Assertion/concept/summary to exact evidence revision; many-to-many and mandatory for machine-produced or retrieved derived facts. Visibility is the intersection of the assertion policy and its currently valid support. |
| `DERIVED_FROM_RUN` | Candidate/assertion/summary to the exact extraction/resolution/assignment run; mandatory for every machine-produced assertion. |
| `MENTION_ASSERTION` | Optional physical convenience from evidence to its `MentionAssertion`; it must mirror that assertion's `ASSERTS_SUBJECT` and conveys no authority without the reified node. |
| `ASSIGNED_TERM` | Optional physical convenience from `TaxonomyAssignmentAssertion` to its term; it must mirror `ASSERTS_OBJECT` and cannot change term authority. |
| `MAPS_TO_VAULT_REF` | Optional physical convenience from `VaultResolutionAssertion` to its imported Vault object; it must mirror `ASSERTS_OBJECT`. Its state belongs to the assertion, and even `approved` cannot ratify or mutate the referenced warehouse object. |
| `ABOUT_ENTITY` | Concept to candidate entity; derived and versioned. |
| `ALIAS_CANDIDATE` | Optional projection of an `AliasAssertion`, not a destructive merge or authority edge. |
| `MEMBER_OF_COMMUNITY` | Derived clustering output scoped to an extraction/community version. |
| `RETRACTED_BY` / `SUPERSEDED_BY` | Explicit lifecycle lineage for correction, source deletion, model/taxonomy change, or review. These operations invalidate convenience edges and downstream projections, not authoritative endpoint objects. |

A property graph may represent each assertion as a node with role edges, while a relational model uses a common assertion table plus subtype constraints and evidence joins. A bare convenience edge is never the logical assertion. The identity, endpoint, support, run, policy, temporal, authority, review, and lifecycle contract remains the same so storage is replaceable.

### 6. Identity resolution, aliases, and contradictions

#### Entity resolution

Resolution must be staged and reversible:

1. extract mention candidates per evidence revision;
2. normalize only mechanically (Unicode/case/punctuation) while retaining original spans;
3. generate candidate pairs within the same approved security partition and compatible entity type;
4. score with deterministic features and/or a versioned model;
5. store `AliasAssertion` decisions rather than destructively coalescing nodes;
6. require governed approval before mapping to a Data Vault Hub;
7. permit split/undo by superseding the resolution assertion and rebuilding projections.

Names are not stable keys. GraphRAG's title/type merge and LlamaIndex's default name-derived entity ID are useful prototypes but unsafe for business identity. Cross-namespace co-reference can also leak that a hidden namespace contains the same entity; resolution itself must be policy-scoped.

#### Contradictory facts

Contradictions must coexist as separate `RelationshipAssertion` records. Each assertion retains exact support, extraction contract, confidence, event-valid interval (when source-backed), system-observed interval, and review/retraction state. A generated “current fact” is a query-time or materialized projection with a named conflict policy; it must not erase earlier assertions or turn an LLM adjudication into warehouse history.

Confidence is not authority. It must be calibrated per extractor/query class and never used as the sole basis for hub/link creation, access bypass, deletion, or irreversible merge.

### 7. Temporal, migration, and deletion model

At least three clocks are required:

- **source/event validity**: when the source says a fact was true (`valid_from`, `valid_to`), nullable unless explicit;
- **system knowledge time**: when Buoy observed/extracted/retracted it (`observed_at`, `retracted_at`);
- **index revision time**: plan/apply/extraction-run identity and timestamps.

Graphiti's separate episode `created_at` and `valid_at`, plus fact `valid_at`/`invalid_at`/`expired_at`, is the strongest inspected reference. Data Vault history remains authoritative wherever it exists; derived times describe the index and assertions, not warehouse loads.

Model, prompt, schema, resolver, or taxonomy changes must produce a new `ExtractionRun`/versioned projection. Do not update old assertions in place. Migration can be shadow-built, compared, and then activated by a reversible pointer; old projection retention follows an explicit policy.

Source deletion/correction requires a deterministic dependency walk:

1. mark the exact evidence revision retracted (or hard-delete content where policy requires);
2. retract affected `MentionAssertion`, `TaxonomyAssignmentAssertion`, and assertion-support links; supersede rather than overwrite corrected assertions;
3. recompute each assertion's remaining support and visibility, including `VaultResolutionAssertion` projections;
4. retract an assertion when no valid support remains, or regenerate it if its endpoints, text, span, confidence, policy, or summary depended on removed evidence; retraction of Vault resolution changes only the derived mapping and never the referenced Hub/Link/Observation;
5. recompute entity summaries, concept cards, communities, embeddings, counts, and retrieval materializations;
6. delete orphan candidate entities only when policy permits and no retained evidence/history/reference requires them;
7. verify graph, vector, caches, exports, and eval artifacts contain no forbidden payload;
8. retain only the minimum audit tombstone/hashes permitted by retention policy.

Chief documents reference removal and dynamic concept disappearance; RAGFlow explicitly requires graph regeneration after file removal; Graphiti implements a shared graph cascade. Their differences show why deletion must be a Buoy-owned, tested contract rather than inferred from a framework.

### 8. ACL and cross-namespace leakage analysis

A shared node is itself a disclosure. Its name, existence, type, degree, aliases, neighbor count, timestamps, summary, community membership, retrieval score, and latency can reveal inaccessible sources even if final chunks are filtered.

Required invariants for any future design:

- authorization happens **before** routing, candidate resolution, graph expansion, aggregation, ranking, and answer generation;
- every evidence revision, assertion, assignment, and aggregate carries a policy/security-partition reference;
- a traversal may expand only through items visible to the principal; hidden nodes/edges cannot affect degree, centrality, community summaries, counts, or ranking;
- a mixed-ACL summary cannot be made safe by filtering citations after generation; summaries/community reports need policy-homogeneous materialization or must be regenerated solely from authorized evidence;
- revocation and source deletion invalidate graph, vector, summary, community, cache, and alias projections within a measured SLA;
- no cross-namespace entity merge runs across policy partitions unless a separately governed policy explicitly allows it;
- citations returned to a user must themselves be readable and sufficient to support the displayed claim.

The safest experiment is policy-homogeneous: use synthetic namespaces with explicit principals and duplicate projected entity candidates across security partitions. Cross-partition federation should remain blocked until zero-leakage tests cover content and side channels. Graphiti group IDs, Chief project scope, Cognee datasets/NodeSets, and RAGFlow datasets are useful isolation shapes, but none by itself proves Buoy's desired ACL semantics.

### 9. Storage options: relational first is credible, but no store is selected

A graph database is not required to represent or evaluate a concept graph. Nodes, assertions, evidence links, aliases, and adjacency are ordinary relational tables; bounded one- and two-hop traversal can use joins or recursive CTEs.

| Candidate family | License / self-hosting | Strengths | Costs/caveats | Appropriate evidence threshold |
| --- | --- | --- | --- | --- |
| PostgreSQL adjacency tables | PostgreSQL License; self-hostable | Transactions, constraints, indexes, recursive CTEs, mature backup/ops, row-level security | Application must implement graph ergonomics/path controls; RLS must be designed/tested for recursive queries and aggregates | Default comparison for governed multi-user relational control planes, not a decision here. |
| DuckDB relational tables | MIT; embedded/self-hostable | Already a Buoy dependency, simple local analytical joins/CTEs, Parquet interoperability, low experiment overhead | Not a networked multi-user policy service; current Buoy DB is a per-namespace applied-state ledger and must not be silently repurposed | Offline fixture/eval feasibility only; not production authority. |
| SQLite relational tables | Public domain; embedded/self-hostable | Minimal deployment, constraints, recursive CTEs, portable fixture | Limited concurrent/service and policy features; ACL enforcement remains application-owned | Small single-process prototype/fixture comparison. |
| Apache AGE on PostgreSQL | Apache-2.0 extension; self-hostable | Cypher/property graph alongside PostgreSQL data | Extension/version/operational surface; policy interaction and portability need testing | Only if Cypher/path workload materially outgrows clear relational queries. |
| Apache HugeGraph | Apache-2.0; self-hostable | Distributed property graph/TinkerPop-oriented system | JVM/distributed backend and operational complexity far beyond a small experiment | Only after scale/query evidence justifies a dedicated distributed graph. |
| Neo4j Community | GPL-licensed community source/self-hostable; enterprise features have separate terms | Mature Cypher ecosystem and Graphiti compatibility | New service, license/feature-boundary review, backup/HA/ACL operations; not uniformly permissive for every deployment | Comparison candidate only after concrete traversal workload and legal/ops review. |
| Kuzu | MIT source, but repository archived; Graphiti marks backend deprecated | Formerly attractive embedded property graph | Upstream maintenance ended/archived; current Graphiti warns against new use | Exclude from new selection absent renewed maintenance evidence. |

FalkorDB appears in Graphiti's supported/self-hosted path, but its licensing must receive an explicit OSI/open-source and project-policy review before candidacy; “source available” or self-hostable is not automatically equivalent to this project's open-source-first requirement.

A production choice depends on scale, concurrency, recursive query shape, ACL enforcement, backup/recovery, change-data capture, operational ownership, and measured latency. This record deliberately makes no selection.

### 10. Smaller alternatives to a full graph

#### Concept cards

A `ConceptCard` contains a stable derived ID, governed/defined description, cited evidence revisions, summary version, scope, and lifecycle. Retrieval searches cards, then fetches authorized chunks. This reproduces the most useful Chief behavior without arbitrary entity-to-entity traversal.

Advantages: explainable, low fan-out, straightforward deletion, and easy comparison with chunk retrieval. Limit: no explicit multi-hop relations.

#### Inverted entity assignments

Store `(entity_candidate, evidence_revision, assignment provenance)` and search entity names/aliases to gather chunks across authorized namespaces. This supports entity-centric consolidation without summaries or a graph database.

Advantages: smallest entity layer; aliases remain reversible. Limit: relation questions still rely on source chunks.

#### Relational assertion/adjacency tables

Add reified relationship assertions and evidence joins. One- or two-hop queries use bounded joins/recursive CTEs, with policy filters in every step.

Advantages: full provenance/temporal model and constraints before graph-store operations. Limit: advanced path algorithms and graph tooling are less convenient.

#### Community summaries without a graph database

GraphRAG demonstrates that edge lists, Parquet outputs, community detection, and reports can be batch artifacts. This may help global questions without a serving graph database. It remains costly and ACL/deletion-sensitive.

A full graph is justified only if a named query set needs typed paths or community structure and beats these alternatives plus current explicit multi-namespace RRF.

### 11. Evaluation design

#### Dataset

Create a future, synthetic, no-live fixture of roughly 100–300 chunks across at least three namespace-shaped partitions:

- approved stable Vault Hub/Link/observation references supplied as read-only fixtures;
- 20–40 gold entities with aliases, same-name different entities, abbreviations, and cross-document mentions;
- 30–60 gold relationship assertions with single/multiple support, negative examples, and contradictory facts;
- event-time changes and late-arriving observations;
- source corrections, source deletion, model/taxonomy migration, and ACL revocation;
- at least three principals with disjoint and overlapping namespace access;
- canary entities/facts existing only in forbidden partitions.

Human-authored gold data must distinguish `same entity`, `related but distinct`, `unknown`, assertion support/entailment, temporal validity, and permitted visibility. Data Vault fixture keys are provided, never generated.

#### Compared arms

1. current explicit multi-namespace hybrid retrieval + RRF baseline;
2. concept cards only;
3. inverted entity assignments;
4. relational reified assertions with bounded one-/two-hop retrieval;
5. only if prior arms justify it, equivalent logical model through a temporary graph implementation.

Each arm uses the same authorized source set and query suite. Visualization is not an outcome metric.

#### Metrics

| Risk/capability | Measures |
| --- | --- |
| Entity resolution | Pairwise precision/recall/F1, B-cubed cluster scores, false-merge rate, false-split rate, Hub mapping approval accuracy; report same-name false merges separately. |
| Edge/assertion quality | Predicate precision/recall/F1, endpoint accuracy, direction accuracy, evidence entailment judged against gold, unsupported assertion rate, contradiction preservation. |
| Provenance | Percentage of derived items with valid namespace-qualified evidence, extraction contract, and resolvable citation; dangling reference count; citation sufficiency. |
| Temporal | Valid interval accuracy, late-arrival handling, current-state accuracy, history preservation, contradiction overlap accuracy. |
| Deletion/correction | Stale retrievals after deletion, dangling supports, orphan summaries/embeddings, full dependency cascade correctness, measured revocation SLA. |
| ACL | Forbidden canary content/name/count/degree/community leakage, unauthorized traversal paths, cross-principal differential tests, policy-change invalidation. Safety target is zero observed leakage. |
| Retrieval usefulness | Recall@k/nDCG/MRR for evidence retrieval, exact/gold path recall, answer correctness, citation precision/recall, multi-hop completion, global-theme coverage/diversity, abstention quality. |
| Performance/cost | Index wall time, tokens and model cost per 1,000 chunks, incremental reprocess amplification, storage bytes per chunk/assertion, query p50/p95, LLM calls/query, deletion latency. |
| Operations | Number of services/stores, backup/restore test, migration/rebuild duration, observability, deterministic replay rate. |

Candidate safety gates for later ratification: 100% resolvable provenance for every returned derived assertion, zero forbidden-canary leakage, zero stale forbidden payload after the accepted revocation window, and no Data Vault identity mutation. Quality/cost thresholds require user ratification after baseline measurement.

## Conclusions and recommendation

### Strongest findings

1. **Reified, source-supported assertions are the key model choice.** A bare entity edge cannot safely carry multiple evidence sources, contradictions, validity intervals, ACLs, extraction versions, review, and retraction.
2. **A graph database is not required for the first useful test.** Chief-like concept cards, inverted assignments, and relational assertion tables can validate value and lifecycle before a graph-store obligation.
3. **Temporal and deletion behavior vary materially across tools.** Graphiti provides the richest temporal model; Chief documents source-reference removal; RAGFlow requires regeneration after source removal; GraphRAG/LlamaIndex leave important lifecycle work to the application. Buoy must own and test this contract.
4. **Cross-namespace entity resolution is an ACL operation, not only an NLP operation.** Shared entity existence, summaries, communities, and centrality can leak hidden data even when citations are filtered.
5. **Data Vault references must flow one way into the derived layer.** LLM candidates may point to approved Hub/Link/observation references through separately governed resolution; they never mint, merge, or rewrite warehouse authority.

### Bounded experiment recommendation

After user review and semantic/ACL ratification, open a separate executable ticket for an **offline, synthetic, storage-neutral experiment**:

1. build concept cards and inverted assignments over the fixed fixture;
2. add reified relationship/evidence tables and only bounded one-/two-hop queries;
3. compare both with current explicit multi-namespace RRF using the same queries;
4. exercise contradiction, deletion, model migration, and three-principal ACL canaries before measuring relevance;
5. record tokens, latency, storage, and reprocessing amplification;
6. stop unless a named entity-centric/multi-hop/global query class improves enough to justify added lifecycle and operational cost.

The experiment should use temporary local artifacts only, must not mutate Turbopuffer or a Data Vault, and must not select a production graph store. Store selection, if ever needed, follows measured query/scale/ACL/operations evidence and a separate architecture decision.

## Blockers and unresolved decisions

Research is complete, but implementation remains blocked on synthesis of all four research tracks and user ratification of:

- first target query class and gold dataset;
- authoritative source/catalog and exact namespace/ACL policy semantics;
- entity/concept types and allowed relation vocabulary;
- approval workflow for aliases and Data Vault reference mappings;
- valid-time, retention, hard-delete, and audit-tombstone policy;
- acceptable deletion/revocation SLA and aggregate side-channel model;
- quality/cost gates and operational owner;
- only later, storage selection.

## Limits

- Chief documentation describes observable/intended product behavior; its implementation, license terms for deployment, thresholds, storage, and ACL internals are not public in the inspected material.
- Open-source documentation and current default-branch source can change. No framework was installed or benchmarked.
- Graphiti deletion was source-inspected but not executed against every backend; backend-specific behavior needs tests.
- Cognee's exact document deletion cascade and production permission topology were not established by the inspected pages.
- GraphRAG's inspected docs describe incremental fields/workflows but did not establish a complete per-source delete/ACL propagation contract.
- LlamaIndex exposes store deletion primitives but its guide does not establish application-wide graph/vector/summary cascade semantics.
- RAGFlow's documentation explicitly says removed files require graph regeneration; no claim is made about undocumented internals beyond that contract.
- Storage license notes are screening-level, not legal advice. Feature-specific/community-versus-enterprise terms require review at selection time.
- Data Vault sources inspected were explanatory material rather than the full Data Vault 2.0 standard. A qualified Data Vault practitioner must review any future warehouse mapping/loading design.
- No real Buoy corpus, ACL distribution, extraction quality, query latency, token spend, or graph utility was measured.
- The missing root `context.md` and `plan.md` could not be read; governing `.10x` records were available and no scope assumption was substituted.
