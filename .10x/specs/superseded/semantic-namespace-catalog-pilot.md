Status: superseded
Created: 2026-07-15
Updated: 2026-07-15

# Semantic Namespace Catalog Pilot

## Supersession

Superseded on 2026-07-15 by `.10x/specs/representative-semantic-namespace-routing-experiment.md`. Representative semantic routing will use reviewed experiment-local namespace cards instead of a production-shaped catalog model. The historical contract remains evidence of the rejected synthetic framework shape, not active behavior.


## Purpose and scope

Define the local synthetic namespace catalog used to evaluate routing without contacting Turbopuffer or selecting production infrastructure.

The catalog is pilot authority only. It MUST NOT be presented as a production catalog, Data Vault, ontology, graph, or remote namespace registry.

## Assumption provenance

### User-ratified direction

The user approved namespace cards carrying source, tags, compatibility, freshness/eligibility, and access metadata; local fixtures; and evaluation before production or graph work.

### Record/source-backed invariants

- Namespace listing alone does not provide semantic catalog authority.
- Authorization, eligibility, and compatibility gate candidates before relevance scoring.
- Current multi-namespace execution requires one shared region/model/precision contract and namespace-aware ranking behavior.
- Unauthorized metadata must not leak.

### Synthetic pilot-only mechanics

The JSON schema, fixed source-kind/profile domains, lowercase synthetic groups, `enabled` field, and access rule below are deterministic test mechanics only. They do not ratify production policy.

### Explicitly unresolved outside the pilot

Production authority/store, freshness states, source ownership, real ACLs, synchronization, revision retention, public diagnostics, and operational ownership remain blocked.

## Canonical fixture

The pilot MUST use version-controlled JSON containing:

- non-empty `catalog_revision`;
- non-empty `taxonomy_revision` matching the loaded taxonomy exactly;
- non-empty `namespaces` list.

Each namespace record MUST contain:

- `namespace_id`: unique identifier matching Turbopuffer namespace syntax `[A-Za-z0-9-_.]{1,128}`;
- `revision_id`: unique immutable fixture revision ID;
- `source_id`: stable source ID independent of namespace name;
- `source_kind`: exactly one of `website`, `github_repo`, `pdf`, `local_file`;
- `title` and `description`: non-empty human-readable fixture text;
- `tag_ids`: unique IDs existing in the matching taxonomy revision;
- compatibility fields: `region`, `embedding_model`, `embedding_dimensions`, `embedding_precision`, `schema_version`, `ranking_profile`;
- `enabled`: eligibility flag;
- synthetic authorization fields: `is_public`, `allowed_groups`.

Domains:

- `region` and `embedding_model` are non-empty strings compared exactly;
- `embedding_dimensions` is a positive integer;
- `embedding_precision` is exactly `float32` or `float16`, matching current `EMBEDDING_PRECISIONS`;
- `schema_version` is a positive integer;
- `ranking_profile` is exactly `none` or `repo_code`, matching current `RANKING_PROFILES`;
- `tag_ids` are stored and rendered in lexicographic term-ID order.

The loader MUST reject duplicate namespace/revision IDs, unknown tags, taxonomy revision mismatch, empty required strings, invalid domains, duplicate tags/groups, and authorization contradictions.

It MUST NOT infer source identity, compatibility, authorization, ranking profile, or meaning from namespace prefixes.

## Synthetic group validation and access

A group ID MUST match `[a-z0-9][a-z0-9_-]{0,63}` and is case-sensitive canonical lowercase.

Catalog and principal group lists use set semantics but duplicate input is invalid. An empty principal group list is valid.

Catalog authorization invariants:

- if `is_public` is true, `allowed_groups` MUST be empty;
- if `is_public` is false, `allowed_groups` MUST be non-empty.

A namespace is authorized when it is public or the principal's validated group set overlaps `allowed_groups` exactly.

A private namespace without overlap MUST be excluded before scoring. Its ID, revision, title, description, tags, vectors, scores, and exclusion reason MUST NOT appear in route output or ordinary diagnostics.

Internal evaluator safety accounting MAY report only the case ID and violation category/count, never unauthorized namespace metadata.

## Complete compatibility tuple

The query and namespace compatibility tuple is:

```text
(region, embedding_model, embedding_dimensions, embedding_precision, schema_version, ranking_profile)
```

Every field is compared exactly before scoring. A mismatch excludes the namespace. The pilot MUST NOT infer compatibility from related names or prefixes.

`enabled: false` also excludes the namespace before scoring.

## Deterministic namespace cards

The pilot MUST derive one card per eligible namespace revision:

```text
Title: <title>
Description: <description>
Tags: <taxonomy labels ordered by tag_id ascending>
Source kind: <source_kind>
```

The card identity MUST retain:

- `catalog_revision`;
- `taxonomy_revision`;
- `namespace_id`;
- `revision_id`.

Identical catalog and taxonomy revisions MUST produce byte-identical card text and identity. A taxonomy descriptor change requires a new taxonomy revision and therefore a different card identity context.

Cards are disposable projections.

## Local representation

Implementation MAY use Python structures or in-memory DuckDB. It MUST NOT persist a database outside a test/pilot temporary directory or add a dependency.

## Acceptance scenarios

- Authorized, enabled, fully compatible namespace becomes eligible.
- Unauthorized namespace is absent from candidates/results/ordinary diagnostics.
- Any compatibility-field mismatch excludes before scoring.
- Disabled namespace excludes before scoring.
- Unknown tag or taxonomy-revision mismatch fails fixture loading.
- Invalid/duplicate group input and public-with-groups fail validation.
- Same revisions generate byte-identical cards; changed taxonomy revision changes card identity context.
- An adversarial unauthorized canary with unique ID/title/tag and highest relevance leaves none of those values in serialized route output.

## Acceptance criteria

- Fixture/loader/card behavior satisfies every field, validation, and leakage rule.
- Cross-taxonomy validation uses the integrated taxonomy model rather than a duplicate interface.
- Tests install fail-fast sentinels for socket/network access, credential loading, sentence-transformer/model construction, Turbopuffer SDK construction, live retrieval, and persistent writes outside temporary paths.
- No external mutation occurs.

## Explicit exclusions

- Production persistence/synchronization.
- Real namespace discovery or mutation.
- Real ACL policy or public diagnostics.
- Data Vault, ontology, concepts, graph behavior, or freshness policy beyond `enabled`.
