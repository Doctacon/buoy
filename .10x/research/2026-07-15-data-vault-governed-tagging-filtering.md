Status: done
Created: 2026-07-15
Updated: 2026-07-15

# Data Vault Governed Tagging and Filtering

## Scope correction — no Data Vault architecture

The user clarified after this research closed that Data Vault was only an analogy for stable concepts and relationships. `.10x/decisions/data-vault-is-analogy-not-architecture.md` governs: Buoy will not build or require hubs, links, satellites, warehouse authority, or Data Vault loading.

Retain this record's findings on structural versus governed versus inferred tags, stable taxonomy IDs, temporal assignment provenance, fail-closed ACLs, Turbopuffer projections, lifecycle reconciliation, and controlled-tag evals. Use an ordinary project-governed relational authority unless a later decision selects something else; recommendations requiring an existing Data Vault are withdrawn.

## Question

How should Buoy classify, govern, project, filter, and optionally boost tags over namespaces, sources, documents, and chunks while preserving Data Vault 2.0 authority and history, source provenance, deletion semantics, and authorization boundaries?

This record is research, not a product contract. In particular, it does **not** decide whether Buoy's public retrieval output should return tags or whether its CLI should accept tag filters. That behavior remains blocked in `.10x/tickets/2026-07-15-reconcile-retrieval-tag-output.md`.

## Sources and methods

Research was performed on 2026-07-15. Official documentation and current local source/records were preferred. Product documentation establishes documented behavior, not independently measured quality. No live Turbopuffer namespace, product data, credential, or external service was queried or mutated.

### Local authority inspected completely

- `.10x/tickets/done/2026-07-15-research-data-vault-governed-tagging-filtering.md`
- `.10x/tickets/2026-07-15-semantic-retrieval-research-plan.md`
- `.10x/tickets/2026-07-15-reconcile-retrieval-tag-output.md`
- `.10x/research/2026-07-15-metadata-tagging-graphs-and-data-vault.md`
- `.10x/specs/explicit-multi-namespace-retrieval.md`
- `.10x/specs/turbopuffer-namespace-discovery.md`
- `.10x/decisions/namespace-ranking-defaults.md`
- `src/buoy_search/chunker.py`
- `src/buoy_search/plan_artifacts.py`
- `src/buoy_search/retriever.py`
- `src/buoy_search/applied_state.py`
- `docs/retrieval.md`
- Targeted repository searches over tests and source for tags, filters, row identity, stale rows, and deletion behavior.

The task-referenced worktree-root `context.md` and `plan.md` did not exist. The executable ticket, parent plan, preliminary research, and worker input artifact contained the available scope and plan context; no missing semantic premise was invented from those absent files.

### External sources inspected

Chief (official help, accessed 2026-07-15):

- [Data Collections: Overview](https://help.chief.bot/articles/1047959-data-collections-overview)
- [How to manage scope](https://help.chief.bot/articles/0485181-how-to-manage-scope)
- [Concepts overview](https://help.chief.bot/articles/6258614-concepts-overview)
- [How Chief creates Concepts](https://help.chief.bot/articles/2999623-how-chief-creates-concepts)
- [How to navigate Concepts View](https://help.chief.bot/articles/7283674-how-to-navigate-concepts-view)

RAGFlow and Cognee (official docs plus bounded open-source spot checks, accessed 2026-07-15):

- [RAGFlow: Use tag set](https://ragflow.io/docs/use_tag_sets) (displayed version 0.26.4)
- RAGFlow source snapshot `df5c8e73fc37d575c7d4074392447b747384161a`: [ingestion-time chunk tagging](https://github.com/infiniflow/ragflow/blob/df5c8e73fc37d575c7d4074392447b747384161a/rag/svr/task_executor.py#L559-L624) and [content/query tag feature calculation](https://github.com/infiniflow/ragflow/blob/df5c8e73fc37d575c7d4074392447b747384161a/rag/nlp/search.py#L813-L837)
- [Cognee: NodeSets](https://docs.cognee.ai/core-concepts/further-concepts/node-sets)
- Cognee source snapshot `252f2c3efb184533a0955e31e83a28ea7db9813d`: [NodeSet construction on documents](https://github.com/topoteretes/cognee/blob/252f2c3efb184533a0955e31e83a28ea7db9813d/cognee/tasks/documents/classify_documents.py#L64-L99), [document-to-chunk propagation](https://github.com/topoteretes/cognee/blob/252f2c3efb184533a0955e31e83a28ea7db9813d/cognee/tasks/documents/extract_chunks_from_documents.py#L44-L59), and [OR/AND adapter tests](https://github.com/topoteretes/cognee/blob/252f2c3efb184533a0955e31e83a28ea7db9813d/cognee/tests/test_pgvector.py#L92-L206)

Turbopuffer (official docs, accessed 2026-07-15):

- [Write](https://turbopuffer.com/docs/write)
- [Query](https://turbopuffer.com/docs/query)
- [Limits](https://turbopuffer.com/docs/limits)
- [Permissions](https://turbopuffer.com/docs/permissions)
- [Metadata](https://turbopuffer.com/docs/metadata)

Data Vault and comparable open standards/systems used as boundary comparisons:

- [Databricks: What is a Data Vault?](https://www.databricks.com/blog/what-is-data-vault), a vendor-authored explanatory comparison, **not** primary Data Vault methodology evidence
- [W3C SKOS Reference](https://www.w3.org/TR/skos-reference/), a primary open standard for concepts, labels, semantic relations, and concept schemes
- DataHub's specific [Tags API tutorial](https://docs.datahub.com/docs/api/tutorials/tags) and [Terms API tutorial](https://docs.datahub.com/docs/api/tutorials/terms), official open-source catalog documentation that directly describes tags as informal/loosely controlled and glossary terms as standardized shared concepts
- [OpenMetadata classification and glossary concepts](https://docs.open-metadata.org/latest/how-to-guides/data-governance), official open-source metadata-governance documentation

These are boundary comparisons, not deployment evaluations. Their exact current UI behavior, scale, and production quality were not independently exercised. No public primary Data Vault 2.0 methodology text was inspected, so the Databricks explanation supplies vocabulary only and cannot substantiate normative loading, effectivity, retention, or erasure semantics.

## Evidence quality and terminology

| Claim family | Evidence class | Evidence | Confidence / limit |
|---|---|---|---|
| Buoy's current schema, tag derivation, row projection, filters, output, and stale-row lifecycle | Primary local implementation evidence | Current branch source, active records, and tests | High for inspected commit `f7eeb012d3a7147009e5c822914bf9da16699b69` |
| Turbopuffer types, filters, writes, consistency, limits, and permission pattern | Official vendor documentation | Current API/guides | High for documented behavior only; no live performance measurement |
| Chief Labels/Collections/Concepts | Official vendor documentation | Product help | High for documented product behavior; storage and algorithms are private/undocumented |
| RAGFlow tag sets | Official project docs plus narrow open-source source spot check | Versioned guide; fixed source permalinks for ingestion-time and query-time tag feature wiring | High for described mechanics at the cited snapshots; no end-to-end execution, dependency audit, or production-quality inference |
| Cognee NodeSets | Official project docs plus narrow open-source source/test spot check | Fixed source permalinks for document construction, chunk propagation, and OR/AND adapter tests | High for those cited paths at the snapshot; unsupported-search-type statement remains documentation-only; no end-to-end execution or production-quality inference |
| Data Vault vocabulary used here | Non-primary explanatory evidence | Databricks vendor explainer; no licensed/primary methodology text inspected | Low-to-medium and vocabulary-only; not evidence for normative loading, effectivity, retention, erasure, or physical design |
| SKOS identity/label/hierarchy vocabulary | Primary standards evidence | W3C Recommendation | High for the standard's stated model; not an assignment workflow, ACL, or retrieval design |
| DataHub/OpenMetadata label-versus-glossary comparison | Official project documentation | Specific DataHub tag/term tutorials and OpenMetadata governance guide | High for documented conceptual distinction; no deployment or scale evaluation |
| Proposed authority, projection, query, and eval designs | Architectural synthesis | Recommendations derived below | Recommendation, not fact or ratified behavior |

Terms in this record:

- **Term**: a stable controlled-taxonomy identity, independent of its display label.
- **Assignment**: an assertion that a term applies to a target for an effective interval.
- **Projection**: query-optimized attributes copied into Turbopuffer; never the sole authority.
- **Structural tag**: deterministic source/path/type metadata, not business authority.
- **Derived tag**: a rule-, similarity-, or model-produced hint with explicit provenance.
- **ACL attribute**: authorization input. It is not a topical tag and cannot be weakened by relevance logic.

## Findings

### 1. Current Buoy tags are deterministic structural labels

**Observed fact.** `derive_doc_kind_and_tags()` chooses `doc_kind` from known URL/path segments and creates `tags` from that kind plus at most the first four slugified segments. `chunk_document()` copies the same list onto every chunk of the page. `TURBOPUFFER_SCHEMA` declares `tags` as filterable `[]string`.

**Observed fact.** Plan artifacts preserve those tags, and `build_generic_site_row()` writes them on every chunk row together with page/chunk hashes, plan/apply identifiers, source kind, and source-specific metadata. Tags do not participate in the row ID or embedding-text hash. Therefore changing only a future external tag assignment would not, under current diff identity, necessarily cause a row to be selected for upsert.

**Observed fact.** Retrieval currently filters only by one `doc_kind`. It neither requests `tags` nor places tags on `SearchHit`, despite `docs/retrieval.md` saying live results include them. The blocked drift ticket correctly prevents this research from treating either side as intended public behavior.

**Implication.** Existing `tags` should not be relabeled as governed business taxonomy without migration and compatibility decisions. Their proven semantics are structural and deterministic.

### 2. “Tag” covers distinct authority classes

The following taxonomy separates facts about production method from recommendations about authority:

| Mode | Example | Assignment producer | Determinism | Candidate authority | Required treatment |
|---|---|---|---|---|---|
| Structural | `doc_kind`, source kind, path segment, language | Ingestion code | Deterministic for a source revision | Authority only for its narrow structural fact | Record algorithm/version; recompute with ingestion |
| Human-governed controlled | Approved domain, product, retention class | Authorized steward | Human decision | Yes, within named governance scope | Stable term ID, reviewer, effective history |
| Source-authoritative | Classification imported from a system of record | Source connector | Depends on source | Yes for that source's declared field, not globally | Source record/version and precedence policy |
| Rule-derived closed set | Path or metadata rule maps to approved term | Versioned rule | Reproducible | Derived business view, not raw authority | Rule/version, input hashes, reprocessing |
| Similarity-derived closed set | RAGFlow-style match to tag descriptions | Embedding model and threshold | Probabilistic | No; retrieval hint until reviewed | Model, taxonomy version, score/threshold, run ID |
| LLM-extracted open set | Auto-keyword/theme | Model/prompt | Probabilistic and vocabulary-expanding | No | Keep separate from controlled IDs; review/promotion flow |
| First-class concept/entity | Chief Concept | Extraction/aggregation pipeline | Probabilistic aggregate | No by default | Separate identity, citations, lifecycle; not a tag array shortcut |
| Authorization | group/user/public access | Auth/policy system | Policy-controlled | Yes for access decisions | Separate fields and mandatory fail-closed filters |

**Recommendation.** Never collapse these modes into one untyped `tags` array. A string collision between an ACL label, an approved term, and an LLM phrase would erase the provenance needed to decide what the value means.

### 3. Chief separates asset labels, reusable collection logic, and concepts

**Documented fact.** Chief defines a Collection as a saved scope using Labels as file-filter rules. Collections provide two operator layers: inside a group, `include all of`, `include any of`, `exclude if all`, or `exclude if any`; between groups, include-all or include-any. Evaluation is against labeled files in the current project. Labels, Collections, Assets, and Concepts are project-scoped.

**Documented fact.** Chat scope can contain files, labels, collections, and concepts. Manual scope and `@` mentions are merged, and users can inspect the resulting scope. This makes scope an explicit retrieval control rather than merely display metadata.

**Documented fact.** Chief Concepts are automatically or manually defined aggregates over relevant source chunks, with citations to files. Automatic concepts are re-evaluated as content arrives; deleting a file removes its references from concepts. Chief documents concept relationships and a graph, but not the internal thresholds, schemas, consistency window, ACL implementation, or scoring formula.

**Local implication.** Chief supports three useful separations for Buoy research: controlled labels classify assets; saved Boolean scopes compose labels; concepts remain citation-bearing semantic objects. Chief does not establish that inferred Concepts are warehouse authority or that its private implementation should be copied.

### 4. RAGFlow distinguishes closed-set similarity tags from open-set keywords

**Officially documented fact.** A RAGFlow tag set is a closed, user-defined vocabulary supplied as description/tag table entries. Every chunk is compared with entries, and tags are assigned by similarity. A query is also tagged; corresponding chunk tags increase retrieval likelihood. The tag-set dataset itself is not a retrieval dataset.

**Officially documented fact.** Updating or deleting tags requires affected documents to be re-parsed for assignments to change. Adding entries leaves re-parsing to the operator. Multiple tag sets are supported, with guidance that they should be independent. RAGFlow explicitly contrasts vector-similarity auto-tags (closed set) with LLM auto-keywords (open set and token-consuming).

**Source spot check, not an execution result.** At source snapshot `df5c8e7`, the ingestion executor invokes tag calculation for chunks and records applied tags, while retrieval code computes content and query tag features from `tag_kwd`. This corroborates that the documented feature has ingestion- and query-path implementation wiring. It does not independently establish exact end-to-end scoring effects, reparse completeness, dependency behavior, scale, or production quality.

**Implication.** Closed vocabulary does not imply authoritative assignment. RAGFlow's assignment is still probabilistic. Its documented reprocessing requirement is evidence that taxonomy changes need a lifecycle contract, not an in-place label rename alone.

### 5. Cognee demonstrates tags promoted to graph anchors

**Officially documented fact.** Cognee accepts NodeSet names when data is remembered, propagates them to documents/chunks, materializes first-class `NodeSet` nodes and `belongs_to_set` edges, and links extracted entities back to those sets.

**Officially documented fact.** Recall can filter supported graph-completion search types by NodeSet using OR (default) or AND. The docs state the filter has no effect on some search types (`SUMMARIES`, `CYPHER`, and `NATURAL_LANGUAGE`).

**Source spot check, not an execution result.** At source snapshot `252f2c3`, document classification constructs stable `NodeSet` objects from ingestion metadata, chunk extraction copies `belongs_to_set`, and repository adapter tests exercise OR/AND behavior. This corroborates document-to-chunk propagation and tested filter wiring in the cited paths. The source spot check did not execute those tests, inspect every retriever, or independently verify the documentation's unsupported-search-type list, entity-linking behavior, scale, or production quality.

**Implication.** First-class identity and edges enable traversal, but filter support must be verified per query path. A control exposed on only some retrievers is unsafe as an ACL. NodeSets are a useful topology pattern for topical grouping, not evidence of authorization enforcement or Data Vault authority.

### 6. Turbopuffer is a capable projection/filter plane, not the governance ledger

**Documented facts.** Turbopuffer documents are typed attribute maps. Attributes are filterable by default unless `filterable: false`; arrays support membership filtering. Filters can use Boolean composition and combine with ANN, exact filtered kNN, BM25, ordering, aggregation, and multi-query/RRF. A query addresses one namespace.

The API supports whole-document upsert/delete, attribute patches, patch-by-filter, delete-by-filter, and conditional operations. Whole upsert overwrites the document; patches do not create missing documents and cannot patch vector fields. Adding a schema attribute yields null for existing documents; changing an existing attribute's type is an error.

Relevant documented limits include 1,024 attribute names per namespace, 128-byte names, 8 MiB attribute values, 4 KiB filterable values, 64 MiB documents, 16 subqueries per multi-query, 50,000 rows per patch-by-filter operation, and 5 million per delete-by-filter operation. Query docs warn that eventual reads can be stale after significant writes; strong consistency searches unindexed writes.

**Documented authorization boundary.** Turbopuffer has no built-in row/document RBAC. Its permission guide recommends putting user/group IDs and an explicit `is_public` Boolean on every document and applying filters at every query. It explicitly says an empty permission array should mean no access, not public access.

**Recommendation.** Use Turbopuffer as a denormalized projection for active filter/ranking inputs. Keep taxonomy, assignment history, reviews, and provenance in an authoritative open store. Projection loss must be repairable from that store.

### 7. Data Vault authority and semantic inference must remain separate

**Working vocabulary from non-primary evidence.** The inspected Databricks explainer describes Hubs around business keys, Links around relationships, Satellites around descriptive context/history, and Raw Vault versus Business Vault separation. This is sufficient to explain the candidate mapping below, but it is not primary methodology authority. Accordingly, this research makes no normative claim about Data Vault 2.0 loading, effectivity, retention, physical erasure, or physical modeling rules. Those semantics require validation against the enterprise's actual licensed methodology, standards, and owners before implementation.

**Recommended mapping, not a claim that the standard mandates these objects:**

```text
Hub_Term             stable governed term business key
Hub_Target           stable namespace/source/document business key
Link_TermAssignment  relationship identity between term and target
Sat_TermDefinition   label, description, scheme/version, hierarchy status
Sat_AssignmentSource source record, method, confidence, reviewer, effective interval
Sat_AssignmentState  proposed/approved/rejected/retired history
Business projection currently effective approved and derived assignments
```

A similarity or LLM run can load a source observation or derived satellite, but MUST NOT overwrite or masquerade as a steward-approved assignment. Promotion to authority is a separate reviewed event retaining both the proposed observation and approval provenance.

This mapping is justified only if Buoy is integrated with a real Data Vault program. Building Hubs/Links/Satellites solely to store a small tag table would add ceremony without authority benefit; a temporal relational schema can preserve the same local invariants more simply.

### 8. Comparable open taxonomy systems reinforce identity and separation

**Standards comparison.** SKOS distinguishes concept identity from preferred, alternate, and hidden labels; organizes concepts into schemes; and provides broader/narrower/related relations. This is a better model for controlled term identity, synonyms, and hierarchy than using display strings as keys. SKOS does not define assignment workflow, ACLs, or vector-retrieval scoring.

**Catalog comparison.** DataHub's specific official tutorials call tags “informal, loosely controlled labels” and describe glossary terms as a standardized shared vocabulary associated with physical assets. OpenMetadata's governance guide similarly documents classifications and glossaries as distinct concepts. This directly supports the narrow vocabulary distinction used here: lightweight labels and curated business terms serve different purposes. It does not prove equivalent workflows, governance rigor, scale, or fitness for Buoy. Both projects are open-source/self-hostable candidates for an enterprise metadata control plane, but adopting either is substantially larger than Buoy's smallest experiment and was not selected here.

**Recommendation.** Start with stable opaque term IDs, a scheme/version, labels/synonyms, and optional parent relationships. Do not require RDF, a graph database, or a full catalog for the first experiment.

## Candidate assignment and provenance model

The following is a candidate logical model, not an approved schema:

### Taxonomy term

```text
term_id                  stable opaque identity; never derived from mutable label
scheme_id                taxonomy/scheme identity
taxonomy_version         immutable published version
preferred_label          display value
alternate_labels[]       synonyms; not assignment duplicates
parent_term_ids[]        optional governed hierarchy
status                   draft | active | deprecated
replacement_term_ids[]   explicit migration guidance
valid_from / valid_to    definition effectiveness
created_by / approved_by stewardship provenance
```

### Tag assignment

```text
assignment_id
target_type              namespace | source | document | chunk
target_business_key      stable key, not only a volatile chunk row ID
term_id
assignment_method        human | source | rule | closed_set_similarity | llm_open_set
assignment_source_id     user/source/rule/run identity
source_record_ref        traceable source coordinate
rule_or_model_version
prompt_version           only when applicable
taxonomy_version
confidence               nullable; never fabricate for deterministic/human assignments
review_state             proposed | approved | rejected | retired
reviewer_id / reviewed_at
effective_from / effective_to
observed_at
input_revision           source hash/page hash/chunk hash as applicable
supersedes_assignment_id optional correction lineage
```

### Projection state

```text
projection_target        namespace + chunk row ID
assignment_snapshot_id   immutable build/run identity
projected_at
projection_version
source_revision
acl_policy_revision      separate authorization projection revision
```

**Recommendations.** Use append-only assignment events or effective-dated rows; derive current state rather than overwriting history. Enforce uniqueness only for the intended identity interval, not across history. Store confidence as evidence about a method, never as an authorization control. Store hierarchy/synonyms once on terms, not repeatedly on every chunk.

## Candidate architectures

### Architecture A — authoritative temporal relational registry plus Turbopuffer projection

An open relational database (PostgreSQL or DuckDB for a local experiment) stores term definitions, versions, assignments, reviews, ACL policy references, and projection runs. A deterministic projector resolves effective assignments and writes minimal arrays onto each active chunk.

**Update.** Publish a new taxonomy version or append assignment/correction events, calculate affected target keys, and patch/upsert their projected attributes. Rename changes labels without changing stable term IDs. Hierarchy changes do not rewrite chunks unless ancestor closure is deliberately materialized.

**Deletion.** Ending an assignment's effective interval removes it from the next projection. Source deletion retracts active source-derived assignments through source coordinates. Chunk replacement reprojects from stable document/source assignments. Projection reconciliation compares desired snapshot with active remote rows.

**Reprocessing.** Rule/model runs write a complete versioned candidate set. A new run supersedes the prior run only after completeness checks, allowing rollback and stale-assignment removal.

**Advantages.** Small, open-source, auditable, easy Boolean queries, transactional review/history, and independently repairable projection.

**Costs/risks.** Requires a projector and reconciliation path. Buoy's current row diff does not include external assignment state, so an implementation must deliberately trigger metadata-only updates rather than assuming current content diff will do it.

### Architecture B — enterprise Data Vault authority plus business projection

Existing enterprise Hubs/Links/Satellites own controlled business terms, targets, source observations, and effective history. A business-vault rule resolves precedence and approval into a current assignment view. Buoy consumes that view and projects it into each namespace.

**Update/deletion/reprocessing.** New source or rule observations append satellites; corrections and expiration append new effective state. Business rules recompute the current view, then projection reconciliation updates affected chunks. Source erasure requirements require a separately governed physical-deletion/anonymization process because ordinary vault history retention is intentionally durable.

**Advantages.** Strong lineage and enterprise reconciliation when a Data Vault already exists; inferred observations cannot silently replace source records.

**Costs/risks.** Highest modeling and operational cost, eventual propagation, business-key governance, and tension between immutable history and privacy erasure. It is unjustified for a standalone Buoy experiment without an existing Data Vault authority.

### Architecture C — index-only controlled arrays (smallest metadata baseline)

Store a manually prepared controlled term-ID array directly in each plan/chunk artifact and upsert it with content. Keep the taxonomy file under version control but no independent assignment ledger.

**Update/deletion/reprocessing.** Regenerate all affected plans/chunks and upsert; deletion follows current Buoy stale-row behavior.

**Advantages.** Fewest components and a valid experimental baseline.

**Costs/risks.** Weak assignment history/review, expensive broad reprocessing, difficult corrections, and projection becomes de facto authority. It cannot satisfy enterprise Data Vault lineage. It is acceptable only for a disposable, non-authoritative experiment with explicit versioned fixtures.

### Recommendation

Use Architecture A for the smallest governed design. Compare it against C in an offline experiment. Use B only when an existing Data Vault is named as the authoritative upstream and its business keys, retention, and stewardship are ratified.

## Minimal materialized Turbopuffer attributes

This is a candidate future projection, not a source/schema change:

| Attribute | Type | Purpose | Notes |
|---|---|---|---|
| `governed_tag_ids` | `[]string` | Exact filtering on currently effective approved/source-authoritative controlled terms | Stable IDs, not labels |
| `derived_tag_ids` | `[]string` | Optional boosts/analysis for current rule/similarity candidates | Never an authority or ACL input |
| `tag_projection_version` | `string` | Detect/reconcile stale projections | Snapshot/build identity, not full provenance |
| `acl_group_ids` | preferably `[]uuid` | Mandatory group authorization | Separate from topical tags |
| `acl_user_ids` | preferably `[]uuid` | Mandatory user authorization | Separate from topical tags |
| `is_public` | `bool` | Explicit public authorization | Empty arrays still mean no access |
| `acl_policy_revision` | `string` | Fail closed on stale/mismatched policy projection where required | Policy semantics remain upstream |

Keep current structural `tags` and `doc_kind` semantically separate until the blocked public/output and migration contracts are ratified. Do not project confidence, reviewer, synonyms, descriptions, entire hierarchy, or assignment history onto every chunk unless a measured query needs them. The authoritative store can return those after retrieval by assignment/term ID if a future interface requires explanation.

Namespace-level classification belongs in a namespace catalog and routing gate. Document/source assignments that must filter chunks need to be inherited and materialized onto every active chunk because Turbopuffer queries filter documents, and a Buoy document is a chunk.

## Candidate filter and boost semantics

These semantics are recommendations for later ratification, not changes to current CLI/API behavior.

### Target resolution

1. Authorize namespaces before routing/querying.
2. Resolve requested stable terms against one explicit taxonomy version; reject unknown, deprecated-without-replacement, or ambiguous labels.
3. Expand synonyms to the same term ID. Expand descendants/ancestors only when the query explicitly requests hierarchical expansion.
4. Resolve namespace/source/document assignments into the effective per-chunk projection.
5. Conjoin the ACL predicate with every ANN, BM25, fallback, and reranking candidate path.

### Boolean topical filters

- **ANY / OR**: retain a chunk if `governed_tag_ids` contains at least one selected term.
- **ALL / AND**: retain only if it contains every selected term; compile as an AND of membership predicates.
- **EXCLUDE ANY**: reject if it contains any excluded term.
- **EXCLUDE ALL**: reject only when all excluded terms co-occur.
- Positive missing/null controlled-tag attributes mean “no matching tag,” not “unclassified therefore included.”
- Exclusion alone should not accidentally admit unauthorized or taxonomy-version-incompatible chunks.
- Namespace-level and chunk-level clauses should remain visible in the query plan rather than silently changing one another.

Chief's two-layer Collection logic demonstrates the usability of explicit group and global operators. Cognee demonstrates AND/OR NodeSet filtering but also shows why every execution mode must be covered: unsupported retrievers must not silently ignore a filter.

### Filter versus boost

- **Filter** only for explicit user scope, authoritative business constraints, or required corpus partitioning where false exclusion is accepted and measured.
- **Boost** for query-inferred topical affinity, similarity-derived tags, and optional preferences. A derived tag should not remove otherwise relevant evidence.
- Preserve an unboosted hybrid baseline candidate stream, retrieve a controlled-tag-match stream, and fuse them with a fixed, inspectable policy such as weighted RRF. This is safer to evaluate than comparing incomparable raw scores or embedding an opaque multiplier.
- Cap the boost so tag agreement cannot overwhelm strong lexical/vector evidence. Do not permit boosts to affect ACL decisions.
- For multi-namespace retrieval, apply the same declared tag policy within each compatible namespace before existing equal-weight cross-namespace RRF, or treat tag-scoped routing as a separately measured stage. Never infer that identical strings in two namespaces use the same taxonomy/version.

Turbopuffer's documented filters and multi-query/RRF make these experiments mechanically plausible. They do not establish which semantics or weight are correct for Buoy.

## Lifecycle, correction, deletion, and ACL analysis

### Taxonomy lifecycle

- Publish immutable taxonomy versions; do not mutate history in place.
- A label rename retains `term_id`; split/merge/deprecation creates explicit replacement mappings and requires reassignment review.
- Version rule/model inputs separately from taxonomy definitions.
- Measure unknown/unassigned coverage before making a tag a hard filter.

### Assignment lifecycle

- Human/source-authoritative and derived assignments remain in separate provenance classes even if they currently select the same term.
- Reviewer approval appends a new state; it does not erase the proposal.
- Retraction ends effectiveness and triggers projection reconciliation.
- Reprocessing must identify the complete run, affected target population, failures, and superseded run so missing outputs can be distinguished from negative assignments.

### Buoy-specific deletion risk

Current Buoy row IDs bind site, canonical URL, section, and chunk content hash. Applied state tracks current, retained-stale, and deleted rows. Stale remote rows may be intentionally retained unless an approved apply uses deletion. Therefore:

- deleting or changing source content does not prove old remote chunks disappeared;
- removing a tag from only current chunks does not prevent an old retained-stale chunk from matching or being retrieved;
- a governed tag implementation needs reconciliation across active and retained-stale remote rows, with explicit policy for whether retained stale data remains searchable;
- source deletion must retract assignment projections and evidence references using namespace + row/source identity, not label strings.

These are implementation blockers, not changes authorized by this research.

### ACL invariants

1. ACL attributes and topical tags use distinct schemas, producers, stores, and review policy.
2. Authorization is evaluated before or as a mandatory conjunct in every retrieval branch; never after top-k, because unauthorized candidates can consume the pool or leak through metadata/scores.
3. Empty ACL arrays mean no access. Public access requires explicit `is_public=true`.
4. A shared concept, taxonomy term, collection, ancestor expansion, boost, or cross-namespace fusion cannot confer access to underlying chunks.
5. Aggregations, tag clouds, counts, error messages, and routing traces must be authorization-filtered to prevent existence leaks.
6. ACL projection lag has a named fail-closed policy and measurable revocation SLO. Strong query consistency may be required after revocation; eventual consistency is not assumed safe.
7. Multi-namespace retrieval must fail without partial output under the active spec, and every selected namespace must apply an equivalent ACL contract.

## Evaluation design

All evals should compare against current explicit namespace-local hybrid retrieval plus existing equal-weight multi-namespace RRF. No claim of improvement is valid without a fixed corpus revision, taxonomy version, projection version, and query set.

### Assignment quality

- Per-term and macro/micro precision, recall, and F1 against steward-reviewed chunk/document gold labels.
- Coverage and abstention rate; confusion matrix for sibling terms.
- Calibration/reliability for similarity/model confidence; precision at promotion threshold.
- Inter-reviewer agreement and adjudication rate for ambiguous terms.
- Propagation correctness from namespace/source/document to chunks.

### Retrieval and routing quality

- Recall@k, nDCG@k, MRR, existing project score/P@5, and answer evidence recall.
- Separate explicit-filter queries from boost queries; measure false-exclusion rate, especially for untagged relevant chunks.
- Controlled ablations: no tags; structural only; approved controlled filters; derived boosts; hierarchy expansion.
- Single-namespace and compatible multi-namespace cases with stable RRF tie/order checks.
- Hard negatives sharing vocabulary but not controlled meaning.

### ACL safety

- Zero unauthorized row, citation, title, score, count, tag-cloud, or routing-trace exposure across ANN, BM25, server/client RRF, schema fallback, aggregation, and error paths.
- Revocation test from policy update through authoritative store and projection to strong/eventual query visibility.
- Empty ACL, public, user-only, group-only, conflicting topical/ACL labels, shared concept, and cross-namespace cases.
- Property test that adding topical filters/boosts can never broaden the ACL-authorized set.

### Taxonomy drift and lifecycle

- Rename preserves identity; split/merge/deprecation produces expected migration queues.
- Old taxonomy/model run is fully replaced with no orphan active projection.
- Source/chunk deletion, retained-stale row, and reactivation scenarios.
- Projection reconciliation detects missing, extra, wrong-version, and partially patched attributes.
- Drift dashboard: unassigned fraction, deprecated-term usage, label collision, term-frequency shift, review backlog, projection lag.

### Operating cost

- Tagging CPU/model tokens per 1,000 chunks and per changed source.
- Reprocessing write count, bytes, time, and cost for taxonomy edits.
- Added filterable storage and write amplification per chunk.
- p50/p95 query latency and recall under ANY/ALL/exclusion cardinalities and ACL conjunctions.
- Steward minutes per accepted assignment and correction.
- Break-even versus index-only arrays and versus no tag layer.

### Promotion gates

A controlled-tag experiment should not become a hard-filter feature unless it demonstrates:

- agreed minimum relevant-evidence recall and bounded false exclusion;
- zero ACL violations in adversarial tests;
- complete correction/deletion/reprocessing behavior;
- stable cost/latency within an approved budget;
- explainable effective taxonomy/assignment version for every filtered result;
- improvement over the metadata/vector-only baseline on named query classes.

Threshold values are intentionally unratified here.

## Smallest controlled-tag experiment

**Recommendation, not implementation:**

1. Choose one non-sensitive namespace and one cohesive, steward-owned taxonomy of roughly 10–30 stable terms.
2. Build an offline reviewed gold set at document and chunk level. Keep current structural tags unchanged.
3. Compare manual/source-approved assignments, a deterministic rule baseline, and RAGFlow-style closed-set similarity candidates. Do not use open-set LLM tags as authority.
4. Represent effective controlled IDs in an offline fixture/projection; do not change public retrieval output or run live writes.
5. Evaluate explicit ANY/ALL filters and a capped tag-match RRF boost against current hybrid retrieval, including untagged relevant evidence.
6. Exercise rename, removal, source deletion, chunk churn, taxonomy version change, failed/partial reprocessing, and ACL-negative scenarios.
7. Stop if the controlled layer does not beat structural metadata/no-tags on the named query class or cannot meet false-exclusion and lifecycle gates.

This experiment is smaller than deploying DataHub/OpenMetadata, a graph, or a Data Vault. It produces evidence needed to decide whether a durable authority service is justified.

## Recommendations

1. Preserve three distinct planes: authoritative term/assignment history, derived candidate observations, and query-optimized Turbopuffer projections.
2. Use stable term IDs and immutable taxonomy versions; labels and synonyms are mutable descriptors, not identity.
3. Prefer Architecture A (open temporal relational authority plus projection) if the experiment justifies implementation. Integrate Architecture B only with an existing governed Data Vault.
4. Keep structural `tags`, governed topical IDs, derived IDs, and ACL attributes separate.
5. Materialize only active term IDs and projection revision needed by measured queries; retain full provenance externally.
6. Use explicit controlled tags as filters only after false-exclusion evaluation. Use probabilistic tags as bounded boosts, never authority.
7. Compile authorization as a mandatory, fail-closed predicate in every query path and filter every aggregate/trace.
8. Treat correction, taxonomy version changes, retained-stale rows, and deletion as first-class reconciliation scenarios.
9. Do not resolve public tag return/filter CLI behavior from this research. Ratify it through the blocked drift ticket and governing retrieval specification.

## Open decisions and blockers

Research can proceed without blockers, but implementation remains blocked on:

- the authoritative steward/system and precedence among human, source, and rule assignments;
- controlled taxonomy scope, initial terms, hierarchy behavior, and version/publishing workflow;
- target granularity and inheritance rules for namespace/source/document/chunk assignments;
- exact filter grammar, boost policy/weight, and missing-schema behavior;
- public retrieval output and filter compatibility owned by `.10x/tickets/2026-07-15-reconcile-retrieval-tag-output.md`;
- ACL source of truth, public/empty semantics ratification, revocation SLO, and multi-namespace policy compatibility;
- whether retained-stale remote rows are searchable and how tag/ACL corrections reach them;
- quantitative promotion thresholds and operating budget;
- whether an enterprise Data Vault already exists and, if so, its business keys, retention/erasure policy, and ownership.

## Limits

- No live corpus or Turbopuffer namespace was inspected, so tag distribution, latency, costs, and current remote stale rows are unknown.
- Chief documents product behavior but not storage, thresholds, scoring, consistency, ACL enforcement, or source code.
- RAGFlow and Cognee mechanics were taken from current official docs and corroborated only by the fixed, narrow source/test paths cited above. No end-to-end execution, full implementation or dependency/license audit, production failure analysis, or quality assessment was performed.
- No primary Data Vault 2.0 methodology text was inspected. The Databricks explainer is non-primary and vocabulary-only; the proposed mapping is architectural synthesis, not normative Data Vault guidance. Loading, effectivity, retention, erasure, and physical-design semantics require revalidation against the enterprise authority.
- DataHub, OpenMetadata, and SKOS were boundary comparisons, not deployment evaluations.
- Turbopuffer documentation establishes supported mechanics and limits, not Buoy-specific performance or correctness.
- The absent task-referenced `context.md` and `plan.md` limited inspection to the executable ticket graph and worker input artifact.
- No recommendation in this record ratifies user-visible behavior, semantic thresholds, taxonomy content, ACL policy, or a technology selection.
