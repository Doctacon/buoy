Status: active
Created: 2026-07-15
Updated: 2026-07-15

# Metadata, Tagging, Knowledge Graphs, and a Cross-Namespace Data Vault

## Scope correction — Data Vault is analogy only

On 2026-07-15 the user clarified that Data Vault was mentioned only because hubs and links resemble stable concepts and relationships. Buoy will not build or require Data Vault 2.0. The current authority is `.10x/decisions/data-vault-is-analogy-not-architecture.md`.

This record preserves the earlier investigation and its useful findings about identity, relationships, provenance, history, ACLs, and lifecycle. Any recommendation that assumes an actual Raw Vault, Business Vault, hubs, links, satellites, business keys, warehouse authority, or Data Vault loading process is withdrawn. Read “hub-like,” “link-like,” and “satellite-like” only as analogy for concept identity, typed relationships, and versioned/provenance-bearing observations.

## Question

Can Turbopuffer store metadata per indexed chunk, how do products and open-source tools use “tagging,” and how could many Buoy namespaces contribute to a larger data-vault or knowledge-graph layer that improves retrieval for LLMs?

The user confirmed and later corrected the investigation terms:

1. **“Chief AI” means Chief at `chief.bot`**, the knowledge product whose Labels, Collections, Concepts, and concept graph are analyzed below. `chief.ai` is a different model marketplace/platform.
2. **“Data Vault” was an analogy, not the intended architecture.** The initial formal Data Vault 2.0 interpretation motivated comparative research but was superseded before architecture shaping. The intended subject is taxonomy, ontology, concepts, relationships, provenance, and semantic retrieval across namespaces.

## Sources and methods

Research performed 2026-07-15 using current project source/records, official product documentation, open-source project documentation, and primary research abstracts. No live Turbopuffer namespace was queried or mutated.

### Local authority inspected

- `src/buoy_search/chunker.py`
- `src/buoy_search/plan_artifacts.py`
- `src/buoy_search/retriever.py`
- `.10x/specs/turbopuffer-namespace-discovery.md`
- `.10x/specs/explicit-multi-namespace-retrieval.md`
- `.10x/decisions/namespace-ranking-defaults.md`

### External sources

Turbopuffer:

- https://turbopuffer.com/docs/write
- https://turbopuffer.com/docs/query
- https://turbopuffer.com/docs/limits
- https://turbopuffer.com/docs/metadata
- https://turbopuffer.com/docs/permissions
- https://turbopuffer.com/docs/concepts

Chief:

- https://help.chief.bot/articles/2999623-how-chief-creates-concepts
- https://help.chief.bot/articles/6258614-concepts-overview
- https://help.chief.bot/articles/1047959-data-collections-overview
- https://help.chief.bot/articles/0485181-how-to-manage-scope
- https://help.chief.bot/articles/7283674-how-to-navigate-concepts-view

Tagging and graph systems:

- https://ragflow.io/docs/use_tag_sets
- https://ragflow.io/docs/dev/construct_knowledge_graph
- https://docs.cognee.ai/core-concepts/further-concepts/node-sets
- https://getzep-graphiti.mintlify.app/concepts/episodes
- https://getzep-graphiti.mintlify.app/concepts/nodes-and-edges
- https://microsoft.github.io/graphrag/index/overview/
- https://github.com/microsoft/graphrag/blob/main/docs/index/default_dataflow.md
- https://developers.llamaindex.ai/python/framework/module_guides/indexing/lpg_index_guide/

Data Vault and retrieval research:

- https://www.databricks.com/blog/what-is-data-vault
- https://arxiv.org/abs/2401.15391
- https://arxiv.org/abs/2406.13213
- https://www.microsoft.com/en-us/research/publication/from-local-to-global-a-graph-rag-approach-to-query-focused-summarization/

## Findings

### 1. Turbopuffer supports metadata per chunk

Turbopuffer calls metadata **document attributes**. In Buoy, one chunk is written as one Turbopuffer document, so attributes are per chunk.

Document attributes can be typed strings, numbers, arrays, dates, vectors, and other supported schema types. Attributes are filterable/indexed by default unless configured otherwise. Queries can combine attribute filters with ANN, exact filtered kNN, BM25/full-text search, ordering, aggregation, and multi-query RRF. Array attributes support membership filters and grouped aggregation; the Turbopuffer documentation uses a `tags` array as an example.

Relevant current limits include 1,024 attribute names per namespace, 128-byte attribute names, 8 MiB attribute values, 4 KiB filterable values, 64 MiB documents, 128-byte namespace names, and up to 500M documents/2TB per namespace. Turbopuffer documents unlimited namespace count as the service posture, with 250M+ observed. Those limits make many namespaces mechanically possible but do not provide semantic namespace discovery.

Turbopuffer recommends a namespace per isolated document space when possible. A query targets one namespace. Cross-namespace routing, catalog semantics, graph traversal, and model-contract discovery remain application responsibilities.

Turbopuffer does not provide row-level RBAC as a separate abstraction; its documented pattern stores fields such as `groups`, `user_ids`, and `is_public` on each document and enforces access with mandatory query filters.

### 2. Buoy already writes tags and substantial chunk metadata

Current Buoy schema in `src/buoy_search/chunker.py` includes:

- `tags: []string`
- `doc_kind`
- title, URL, path, section, and chunk index
- vector and searchable content
- source hash

`src/buoy_search/plan_artifacts.py` adds source and lifecycle attributes including site/source identifiers, repository owner/name/ref/commit/path/language, file/PDF identifiers and hashes, plan ID, apply time, page hash, chunk hash, and embedding-text hash.

Current tags are not semantic concepts. `derive_doc_kind_and_tags()` deterministically derives them from document kind and the first URL/path segments. They are useful structural labels, not entity extraction or an ontology.

Current retrieval filters only on `doc_kind`. `RETRIEVAL_ATTRIBUTES` does not request `tags`, and `SearchHit` has no tag field, even though `docs/retrieval.md` says live results include tags. This source/documentation drift is separately owned by `.10x/tickets/2026-07-15-reconcile-retrieval-tag-output.md`.

### 3. “Tagging” describes at least four materially different layers

#### A. Structural metadata and access labels

Examples: source type, tenant, project, file type, language, timestamps, ACL groups, and deterministic URL/path labels.

Purpose: exact filtering, isolation, governance, routing, and ranking boosts. This is Turbopuffer’s native strength and Buoy’s current layer.

#### B. Controlled taxonomy tags

RAGFlow’s tag sets are closed, user-defined vocabularies. Each chunk is compared with tag descriptions; matching tags are applied by vector similarity. At query time, corresponding query tags increase the chance of retrieving tagged chunks. Updating a tag set requires reprocessing affected documents.

Chief’s Labels and Collections show a similar product pattern at asset scope: labels classify files; saved Collections combine label rules with include/exclude and all/any logic; chat scope can be narrowed to a label, collection, file, or concept.

Controlled tags are inspectable and governable. They work well for domain, product, customer, lifecycle, sensitivity, or project classification. They do not by themselves encode arbitrary relationships.

#### C. Open-set concepts and entities

Chief automatically detects recurring entities/themes across files, evaluates contextual relevance and proximity, and creates Concepts containing a title, summary, source snippets, and links to original documents. Concepts continuously enrich as files are added and remove references when a source file is deleted. Users may also define a concept description and let Chief gather matching source chunks.

This is more than tagging: a Concept is a first-class aggregate object with provenance and a retrieval scope. Chief exposes related concepts as a graph for navigation.

#### D. First-class graph nodes and edges

Cognee demonstrates the smallest bridge from tags to graphs: NodeSet tags become `NodeSet` nodes, documents/chunks and extracted entities connect through `belongs_to_set` edges, and retrieval can be scoped to a NodeSet.

Graphiti treats ingested items as episodic nodes, extracts/deduplicates entities and relationships, links episodes to entities with `MENTIONS`, stores source and temporal fields, and tracks validity/invalidation of relationship facts. It embeds entity names and edge facts for semantic retrieval while retaining graph traversal and provenance.

Microsoft GraphRAG builds Documents, TextUnits, Entities, Relationships, optional Claims, Communities, and Community Reports. TextUnits remain provenance anchors. Hierarchical community detection and summaries target corpus-wide “global” questions rather than only nearest-chunk lookup.

LlamaIndex’s PropertyGraphIndex illustrates graph-plus-vector retrieval: chunk extractors attach entity/relation metadata, retrievers can combine vector node retrieval, synonyms, graph path expansion, and constrained or unconstrained Cypher. It explicitly warns that arbitrary LLM-generated Cypher requires production safety controls.

### 4. Tags can become graph nodes, but that is a modeling choice

A tag array on a chunk is not automatically a knowledge graph. Promotion occurs when the system assigns stable tag/concept identity and materializes relationships such as:

```text
Namespace --CONTAINS--> Chunk
Chunk --TAGGED_AS--> TaxonomyTerm
Chunk --MENTIONS--> Entity
Entity --RELATED_TO--> Entity
Concept --SUPPORTED_BY--> Chunk
Namespace --COVERS--> Concept
```

The critical addition is not the word “graph”; it is stable identity, typed relations, provenance back to chunks, lifecycle/version handling, and entity resolution. Without these, a graph can be a noisy visualization of duplicated labels.

### 5. A large namespace fleet needs a catalog before it needs a knowledge graph

Turbopuffer namespace listing exposes identifiers, not semantic descriptions or per-namespace embedding contracts. Buoy’s active namespace-discovery spec intentionally supports ID substring search only. Multi-namespace retrieval requires explicit selection and one shared embedding model/precision; it does not infer per-namespace model metadata or fan out over every namespace.

Therefore the smallest useful cross-namespace layer is a **namespace catalog/control plane**, not a graph database. A catalog entry should minimally describe:

- stable namespace ID and source identity
- source kind and canonical source location
- human title/description
- controlled domain/project/customer/security tags
- embedding model, dimensions, precision, and schema version
- indexed content revision, freshness, time range, and status
- chunk/document counts
- access policy reference
- supported retrieval/ranking profile
- optional concept/entity coverage summaries

A query router can search/classify against catalog entries, select a small compatible namespace set, apply authorization, execute namespace-local retrieval, and fuse results. This removes the need to query every namespace and makes model/schema incompatibility explicit.

A catalog could be implemented as a separate Turbopuffer namespace containing one “namespace card” per namespace, but that is only one option. It would provide semantic catalog search and filters, not graph traversal or transactional authority. The canonical catalog could instead live in a small open-source relational store with a derived Turbopuffer search index.

### 6. A concept graph should be a derived semantic index, not the source of truth

A practical second layer can derive concepts/entities and relationships from cataloged chunks while preserving source coordinates:

```text
catalog namespace record
    -> selected source namespaces
        -> chunk IDs and source hashes
            -> concept/entity assignments
                -> typed relationships and summaries
```

Every concept/edge should retain supporting `(namespace_id, chunk_id, source_hash)` references plus extraction method, model/rule version, confidence, and observed time. This permits retraction when a source disappears, reprocessing after taxonomy/model changes, and citation back to original material.

The chunk index remains optimized for evidence retrieval. The graph is optimized for routing, aggregation, multi-hop traversal, and concept navigation. Neither should silently replace the other.

### 7. Knowledge graphs help specific query classes, not all search

Evidence supports three useful cases:

1. **Multi-hop questions** requiring several pieces of evidence. MultiHop-RAG reports unsatisfactory performance from existing RAG methods on its multi-document benchmark. Multi-Meta-RAG reports substantial benchmark improvement from domain-specific metadata filtering, showing that better metadata can solve some multi-hop selection problems without a full graph.
2. **Entity-centric consolidation**, such as collecting all evidence about a customer, project, product, person, or risk across sources.
3. **Global/corpus questions**, such as themes across a collection. Microsoft’s GraphRAG research reports improved comprehensiveness and diversity versus conventional RAG for global sensemaking questions over roughly million-token corpora using entity graphs and community summaries.

A graph is not established as a universal relevance improvement for ordinary factual nearest-neighbor search. Costs and failure modes include LLM extraction expense, entity duplication, bad relation typing, stale edges, unsupported inferred claims, graph fan-out, ACL leakage through shared entities, and additional deletion/reconciliation work. RAGFlow and GraphRAG both warn that graph construction consumes substantial tokens/compute; RAGFlow also requires explicit regeneration for some deletion updates.

### 8. Data Vault 2.0 is adjacent to, but not the same as, a knowledge graph

Formal Data Vault modeling uses:

- **Hubs** for stable core business keys/concepts
- **Links** for relationships between hubs
- **Satellites** for descriptive and historical attributes of hubs/links

That structure resembles graph primitives, but Data Vault is primarily a historical enterprise warehouse modeling pattern. It emphasizes auditable ingestion, stable business keys, source lineage, and change history. It is not automatically a semantic ontology, vector index, LLM retrieval system, or knowledge graph.

A governed mapping is plausible:

```text
Hub       -> canonical business entity identity
Link      -> durable business relationship identity
Satellite -> time-varying descriptions and source observations
Chunk     -> unstructured evidence supporting a hub/link/satellite assertion
```

If “data vault” instead means a product-level knowledge vault, the more useful definition is: a governed catalog of source namespaces plus provenance-preserving concept/entity views over their chunks. That should not be called Data Vault 2.0 unless it actually implements the warehouse method’s keys, history, and loading semantics.

## Conclusions

### Answer to the immediate question

Yes: Turbopuffer supports per-chunk metadata because every Buoy chunk is a Turbopuffer document with typed attributes. Buoy already writes `tags` plus source, structure, hash, and lifecycle metadata. The current tags are deterministic structural path labels, not a semantic layer.

### Recommended architecture sequence

Do not begin with a general knowledge graph. The smallest evidence-backed sequence is:

1. **Namespace catalog** — register each namespace’s source, meaning, tags, access boundary, embedding contract, freshness, and retrieval profile.
2. **Controlled tagging** — define a small governed taxonomy; materialize filterable chunk tags while storing assignment provenance/version separately.
3. **Router and evals** — use catalog/tags to choose compatible namespaces, then measure routing recall and end-answer quality against current explicit multi-namespace RRF.
4. **Concept layer** — add first-class concepts that aggregate cited chunks across namespaces, similar to Chief, only after the catalog and deletion/provenance contracts are stable.
5. **Graph selectively** — materialize typed entities/edges for named multi-hop, entity-centric, temporal, or global-query use cases; retain vector/BM25 retrieval for ordinary evidence lookup.

This sequence is cheaper, reversible, and testable. It also distinguishes exact metadata filtering from probabilistic semantic extraction.

## Ratified research direction

On 2026-07-15 the user confirmed Chief at `chief.bot` and that all four capability families matter independently. The user subsequently clarified that Data Vault was only an analogy; `.10x/decisions/data-vault-is-analogy-not-architecture.md` supersedes the earlier formal Data Vault interpretation:

1. namespace catalog and routing;
2. governed tag filtering;
3. cross-namespace concept graphs;
4. multi-hop and global retrieval.

Each capability will receive a focused investigation in its own `work/*` branch and worktree based on current `develop`. The governing parent plan is `.10x/tickets/2026-07-15-semantic-retrieval-research-plan.md`. Research remains non-implementing until the focused findings are synthesized and the user ratifies a behavioral architecture.

## Unresolved decisions

- How stable concept identity, typed relationships, provenance, temporal observations, and correction/deletion should be modeled without importing Data Vault schemas or warehouse authority.
- Whether tags are human-authored, rule-derived, closed-set similarity assignments, LLM-extracted open-set terms, or a combination with explicit provenance.
- The authority, ACL, history, correction, and deletion model for concepts/entities that span namespaces.
- Which measured evals are sufficient to justify each layer over the current explicit multi-namespace RRF baseline.

## Limits

- Product documentation describes intended behavior, not independently benchmarked quality.
- Chief’s internal storage and extraction algorithms are not public in the inspected docs.
- Data Vault sources inspected were explanatory material rather than the full Data Vault 2.0 standard.
- GraphRAG and metadata-RAG findings are task/dataset-specific and do not establish universal superiority.
- No live Buoy/Turbopuffer corpus was inspected, so this record does not measure current tag distributions, routing recall, or graph extraction quality.
