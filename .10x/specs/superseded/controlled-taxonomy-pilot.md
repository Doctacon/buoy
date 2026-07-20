Status: superseded
Created: 2026-07-15
Updated: 2026-07-19

# Controlled Taxonomy Pilot

## Supersession

Superseded on 2026-07-15 by `.10x/specs/representative-semantic-namespace-routing-experiment.md`. Representative semantic routing will use simple experiment-local lexical descriptors instead of a reusable taxonomy subsystem. The historical contract remains evidence of the rejected synthetic framework shape, not active behavior.


## Purpose and scope

Define a small, flat, local taxonomy and deterministic phrase matcher for a synthetic namespace-routing pilot. This contract does not ratify production taxonomy content, public tag behavior, hierarchy, ontology, or automatic tagging.

The existing retrieval-tag output drift remains owned by `.10x/tickets/done/2026-07-15-reconcile-retrieval-tag-output.md`.

## Assumption provenance

### User-ratified direction

The user approved a small controlled taxonomy, exact-tag routing, comparison with semantic/hybrid routing, local-only execution, and evidence before graph work.

### Record/source-backed invariants

- Governed tags, derived scores, and ACL attributes remain separate.
- Probabilistic similarity MUST NOT become authoritative assignment.
- No public tag behavior changes under this pilot.
- No Data Vault or graph behavior is introduced.

### Synthetic pilot-only mechanics

The fixture fields, normalization algorithm, flat vocabulary, uniqueness rules, and exact matcher below exist only to make the pilot deterministic. They do not claim production semantics.

### Explicitly unresolved outside the pilot

Production taxonomy ownership, term content, hierarchy, ontology constraints, assignment review, version publication, public filters/output, and promotion thresholds remain blocked.

## Taxonomy fixture

The pilot MUST use version-controlled JSON with a non-empty `taxonomy_revision` and a non-empty `terms` list.

Each term MUST contain:

- `term_id`: stable unique identifier matching `[a-z][a-z0-9_-]{0,63}`;
- `label`: human-readable canonical phrase;
- `description`: synthetic fixture meaning;
- `synonyms`: zero or more alternative phrases.

Term ID is identity. Label, description, and synonyms are descriptors.

## Canonical phrase normalization

For every query, label, and synonym, normalization MUST:

1. apply Unicode NFKC normalization;
2. apply Unicode `casefold()`;
3. replace every maximal run of non-alphanumeric Unicode characters with one ASCII space;
4. collapse whitespace runs to one ASCII space;
5. trim leading/trailing space.

A normalized descriptor MUST contain at least one alphanumeric token.

Examples:

- `"Machine-Learning"` → `"machine learning"`;
- `"  Customer Risk "` (including non-breaking space) → `"customer risk"`;
- `"Café"` and its canonically equivalent Unicode spelling normalize identically;
- `"art"` MUST NOT match the token `"cart"`.

## Global uniqueness validation

The loader MUST build one global map across every normalized label and synonym. Every normalized phrase MUST map to exactly one term ID.

It MUST reject:

- duplicate term IDs;
- empty required fields;
- two labels normalizing to the same phrase;
- any synonym normalizing to any label or synonym belonging to another term;
- a synonym normalizing to its own label;
- duplicate synonyms after normalization.

The taxonomy is flat. Parent/child relations are not accepted.

## Exact query matching

A descriptor matches only when its normalized token sequence occurs as a contiguous complete token sequence in the normalized query.

The matcher MUST:

- find every complete-phrase occurrence;
- return each term once;
- include every distinct normalized matched phrase for that term;
- order matched phrases lexicographically;
- order term matches by `term_id` ascending.

Overlapping descriptors for the same term are allowed, but global uniqueness prevents one phrase from mapping to multiple terms. Repeated query occurrences do not duplicate output.

Exact matching MUST NOT infer related terms, expand hierarchy, persist assignments, or call an LLM.

## Assignment semantics

Namespace `tag_ids` in the catalog fixture are governed synthetic assignments and MAY participate in exact namespace routing.

Semantic query/card similarity is a derived score. It MUST NOT create, modify, or persist taxonomy terms or namespace assignments.

ACL group IDs are not taxonomy terms and MUST NOT be accepted as authorization evidence.

The first pilot has no chunk/evidence tag filter or boost arm. False exclusion is measured as missed required namespaces and missed namespace-qualified cached evidence. No pilot tag field changes public `SearchHit`, CLI, Turbopuffer schema, or live retrieval.

## Acceptance scenarios

### Canonical label

Given a query containing a normalized complete label phrase, exact matching returns its term once.

### Unique synonym

Given a query containing a synonym, exact matching returns its canonical term ID and normalized matched phrase.

### Punctuation and Unicode

Given punctuation, compatibility characters, or repeated whitespace, matching follows the canonical normalization examples above.

### Substring

Given `art` only inside `cart`, the `art` term does not match.

### Global collision

Given a synonym that normalizes to another term's label or synonym, fixture loading fails.

### Repeated/overlapping match

Given repeated descriptors for one term, output contains one term with unique lexicographically ordered matched phrases.

### ACL separation

Given a taxonomy descriptor equal to a synthetic group ID, the match creates no authorization.

## Acceptance criteria

- Fixture validation and matching satisfy every rule above.
- Matching output is deterministic and explainable.
- Governed assignments, derived scores, and ACL groups remain structurally separate.
- No network, credential, model, Turbopuffer, persistent database, or external mutation occurs.

## Explicit exclusions

- Production taxonomy governance or terminology.
- Hierarchy, ontology, entities, concepts, relationships, or graph traversal.
- Automatic/open-set/LLM tagging.
- Chunk/evidence filtering or boosts.
- Public CLI/API tags or live writes.
