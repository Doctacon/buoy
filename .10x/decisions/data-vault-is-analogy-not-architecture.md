Status: active
Created: 2026-07-15
Updated: 2026-07-15

# Data Vault Is an Analogy, Not the Semantic Architecture

## Context

The metadata/tagging/knowledge-graph investigation initially interpreted the user's reference to Data Vault as interest in formal Data Vault 2.0 architecture. That interpretation caused the preliminary and focused research records to analyze hubs, links, satellites, business keys, historical loading, and warehouse authority as possible integration constraints.

The user clarified that Data Vault was mentioned only because its hub/link shape resembles concepts and relationships. The intended problem is semantic organization and retrieval across many Turbopuffer namespaces: taxonomies, ontologies, stable concepts, typed relationships, provenance, and graph-assisted retrieval. There is no requirement to create a Raw Vault, Business Vault, hubs, links, satellites, Data Vault loading processes, or a warehouse.

Leaving the earlier interpretation active would invite unnecessary warehouse machinery and could incorrectly turn an analogy into product scope.

## Decision

Buoy MUST NOT build or require Data Vault 2.0 for the semantic retrieval workstream.

The target vocabulary is:

- **semantic catalog** for namespace/source identity, compatibility, access, freshness, and routing metadata;
- **taxonomy** for governed categories, terms, synonyms, and hierarchy;
- **ontology** for concept and relationship types plus constraints;
- **knowledge graph or relational assertion layer** for observed concepts, typed relationships, provenance, temporal state, and source citations;
- **Turbopuffer attributes and retrieval** for chunk-level metadata filtering and semantic/lexical evidence search.

Data Vault concepts may remain as comparative analogies only:

- a hub is analogous to stable concept identity;
- a link is analogous to a typed relationship;
- a satellite is analogous to versioned description, provenance, or historical observations.

Those analogies MUST NOT imply Data Vault schemas, business-key governance, loading semantics, warehouse authority, or a technology dependency. Earlier 2026-07-15 research remains useful for its findings about stable identity, reified relationships, provenance, history, ACLs, correction, and deletion, but any recommendation requiring an actual Data Vault is withdrawn.

No taxonomy, ontology, graph schema, storage engine, extraction method, ACL policy, or implementation threshold is selected by this decision.

## Alternatives considered

### Build formal Data Vault 2.0 first

Rejected because the user did not request a warehouse or Data Vault loading model. It would add unrelated schemas, operational processes, and governance before semantic retrieval value is established.

### Keep “Data Vault” as the product architecture name

Rejected because it would remain ambiguous and encourage future agents to treat hubs, links, and satellites as requirements rather than analogy.

### Discard all Data Vault-related research

Rejected because the investigations produced reusable findings about identity, relationship reification, provenance, history, ACLs, and lifecycle safety. Those findings remain valid when restated without Data Vault authority.

## Consequences

The active parent workstream becomes semantic catalog, taxonomy, ontology, concepts, relationships, and retrieval research. Future specifications and tickets must use those terms and must not introduce Data Vault components without a new user-ratified decision.

The four focused research records remain historical investigations. Each receives a scope correction making clear that Data Vault-specific architecture is not current authority. Their metadata/vector/graph comparisons, experiments, and safety constraints remain candidate evidence for later synthesis.

This correction reduces scope: experiments can use ordinary local fixtures for concepts, relationships, provenance, history, and ACLs without pretending to model a Data Vault warehouse.
