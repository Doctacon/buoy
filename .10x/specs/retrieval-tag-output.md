Status: active
Created: 2026-07-19
Updated: 2026-07-19

# Retrieval Tag Output

## Purpose and scope

Expose the automatic structural tags already stored on indexed chunks as retrieval-result metadata. This contract applies to live single- and multi-namespace retrieval output without adding tag filtering, tag-based ranking, or new tag derivation.

## Tag meaning and retrieval behavior

- Retrieval MUST request the existing `tags: []string` chunk attribute alongside the current retrieval attributes.
- Tags MUST preserve the stored list values and order. Retrieval MUST NOT derive, expand, filter, boost, or otherwise reinterpret them.
- Tag values MUST NOT affect query construction, `doc_kind` filtering, within-namespace ranking, cross-namespace fusion, grouping, or result limits.
- File/page grouping MUST preserve the selected representative chunk's tags just as it preserves that chunk's other citation metadata.
- Single-namespace and multi-namespace results, including automatically routed multi-namespace results, MUST use the same per-hit tag contract.

## JSON output

Every live retrieval hit in JSON MUST contain a `tags` field whose value is a list of strings. The field MUST be present even when the stored tag list is empty or the namespace schema does not provide tags; in those cases its value is `[]`.

This per-hit field is additive. Existing single-namespace fields, multi-namespace fields, namespace attribution, ordering, and score metadata MUST remain compatible.

## Text output

A live retrieval hit with one or more tags MUST include a `Tags: ` line containing the stored tags in order, separated by `, `. A hit with no tags MUST omit the line. Single-namespace and multi-namespace text MUST render tags identically; existing namespace citations and other hit lines remain unchanged.

## Missing-schema portability

- Initial live queries MUST request both `repo_path` and `tags`.
- A missing-attribute error naming `tags` or `repo_path` MUST trigger a bounded retry that omits the missing optional attribute while preserving the other optional attribute until the provider proves that it too is absent.
- A namespace missing either optional attribute, or both attributes discovered across successive attempts, MUST remain queryable. At most the necessary variants—both present, one absent, then both absent—may be attempted.
- When `tags` is unavailable, every returned hit MUST use `tags: []`. When `repo_path` is unavailable, the existing empty-`repo_path` behavior MUST remain intact.
- Missing-attribute fallback MUST apply consistently to every ANN/BM25 subquery in an attempt and independently within each selected namespace.
- Errors not identified as a missing `tags` or `repo_path` attribute MUST fail under the existing retrieval error and no-partial-results contracts. The fallback MUST NOT hide transport, authentication, malformed-row, or unrelated schema failures.

## Acceptance scenarios

### Tagged JSON and text

**Given** a retrieved chunk with stored tags `['library', 'guide']`
**When** JSON and text output are rendered
**Then** JSON contains `"tags": ["library", "guide"]` and text contains `Tags: library, guide`.

### Empty tags

**Given** a retrieved chunk with no stored tags
**When** JSON and text output are rendered
**Then** JSON contains `"tags": []` and text contains no `Tags:` line.

### Single/multi consistency

**Given** the same tagged hit contract in one selected namespace and across multiple explicitly or automatically selected namespaces
**When** results are serialized
**Then** every hit uses the same JSON/list and conditional text-line rules while multi-namespace hits retain source namespace attribution.

### Older schema

**Given** a live namespace whose schema lacks `tags`, `repo_path`, or both
**When** retrieval receives the corresponding missing-attribute error
**Then** it retries only without the unavailable optional attribute or attributes, returns successful hits with empty values for unavailable metadata, and preserves all existing query and ranking behavior.

### No filtering

**Given** tags on indexed chunks
**When** a user configures retrieval
**Then** no tag filter or tag-based ranking control exists, and only the existing `doc_kind` filter affects metadata filtering.

## Constraints and explicit exclusions

- No tag CLI/API filter, AND/OR grammar, interaction rule with `doc_kind`, tag boost, or ranking signal.
- No semantic tag extraction, taxonomy, ontology, concept graph, knowledge graph, or tag governance change.
- No chunking, plan, apply, remote schema, row, namespace, or deterministic-ID change.
- No live Turbopuffer write, migration, backfill, or namespace recreation.
- Dry-run plans contain no hits and require no tag-specific output change.
