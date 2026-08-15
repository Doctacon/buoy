Status: active
Created: 2026-08-15
Updated: 2026-08-15
Decision: .10x/decisions/buoy-uses-bounded-prototype-routing.md
Specification: .10x/specs/scalable-routing-quality.md

# Implement Scalable Routing Quality

## Outcome

Improve descriptor-free routing as the catalog grows to dozens of corpora,
without changing Buoy's explicit-namespace bypass or its maximum of three
content namespaces. Keep one card per corpus in the existing
`buoy-routing-catalog-v1`, add bounded reviewed operator-authored routing
examples, take an exact top-twelve vector shortlist from the cards already
returned by the strong catalog read, and rerank that shortlist locally with
the already pinned MiniLM model.

## Scope

- Add reader compatibility for the exact current remote schema (schema v1)
  and exact schema v2 containing the four-field routing prototype bundle.
- Add zero-to-eight routing examples to one card row and a deterministic,
  separate non-ANN normalized-mean BGE prototype vector while preserving the
  exact legacy base projection.
- Preserve exact title/alias routing behavior and the three-namespace bound.
- Add an exact in-memory vector shortlist of at most twelve cards and a bounded local
  MiniLM rerank over each shortlisted card's base passage and examples.
- Add manual `--routing-example` input, apply preservation, projection
  diagnostics, and route-only canary tooling. Automatic apply does not invent
  capability examples from generic source identity.
- Package a versioned collect-only confidence-calibration artifact. Ordinary
  automatic retrieval MUST retain the current route selector until human-
  approved canaries and every activation gate pass.
- Document but do not perform the reader-first remote schema migration.

## Acceptance

- A new reader accepts only exact schema v1 or exact schema v2, reconstructs
  the complete four-field prototype bundle only when all provider values are
  absent, rejects partial state, and rejects every other schema or row shape.
- Existing schema-v1 rows retain their exact semantic hash, vector, vector
  hash, card revision, and routing behavior when examples are empty.
- Schema-v2 rows contain at most eight canonical examples plus the prototype
  hash, ordinary non-ANN `[]float` vector, and vector hash in the same card
  row; no prototype documents, second catalog namespace, second vector index,
  hosted embedding, or provider reranker is introduced.
- A descriptor-free candidate route scores the separate prototype vectors from
  the existing strong catalog snapshot exactly in memory, retains at most
  twelve eligible cards, and adds no provider query or per-card request. Stale, disabled,
  missing, and incompatible cards remain unable to enter the route.
- The pinned local MiniLM scores the base passage and each example separately;
  each corpus receives its maximum finite score with deterministic ties.
- Complete title/alias matching behaves exactly as before. At most three
  content namespaces are selected or queried on every path.
- Confidence comes only from an exact packaged, owner-approved calibration
  revision. No CLI or environment override exists, and collect/unapproved,
  missing, malformed, or incompatible activation state cannot silently enable
  the candidate selector.
- Human-approved per-corpus canaries are disjoint from stored routing examples.
  shortlist recall, final routing, high-confidence safety, fanout, call accounting,
  and existing end-to-end gates all satisfy the specification before any
  activation record can be approved.
- Python 3.11 and 3.13 focused/full suites, locked dependency validation,
  source-release validation, distribution smoke, and diff checks pass.

## Owned paths

- `src/buoy_search/{catalog,remote_catalog,routing,catalog_cli,apply,cli,cross_encoder}.py`
- focused catalog, apply, CLI, routing, migration, and evaluation tests/data
- `scripts/evaluate_multi_corpus_retrieval.py` or one focused route-only
  evaluator if separation keeps the gate clearer
- `scripts/release_automation.py` and focused distribution-inventory tests for
  the packaged routing-quality module, artifact, and source-only evaluator
- routing/indexing/migration documentation and this ticket's decision,
  specification, evidence, and review records

## External effects

The owner explicitly authorized creating dedicated corpora to test this
feature. The four reviewed test plans were applied through the current
schema-v1-compatible public workflow, immediately disabled, then given manual
schema-v1 cards. The standard apply path briefly created each generated card
as eligible before the immediate disable; final strong readback proves all
four are now excluded from ordinary automatic routing. This creates real
provider-backed test content without adding prototype fields. No existing
production content corpus may be mutated or deleted.

Code validation and the route-only collector perform no provider mutation.
The separately authorized test-corpus setup is the only provider mutation in
this phase. It changes no shared schema and adds no prototype field, so the
currently installed exact-schema reader remains compatible. A schema-v2 write
still waits for reader-first integration.

Adding the four prototype fields to the shared live routing schema remains a
reader-first operation after integration. The user authorization covers the
new routing-test corpora; the shared-schema mutation and any existing-card
backfill still require an exact drift-checked preview because they affect the
catalog read by every automatic request.

## Exclusions

LLM routing, learned online routing, hierarchical routing, more than eight
examples, more than twelve shortlist rows, more than three content namespaces,
prototype rows, late-interaction or multi-vector provider indexes, a second
catalog namespace, a new provider shortlist query, content reindexing,
ACL/taxonomy work and automatic threshold tuning in production.

## Progress

- 2026-08-15: Isolation review replaced the one-vector draft with an exact
  four-field v2 bundle and separate non-ANN prototype vector so legacy routing
  remains byte-for-byte bound to the base card projection.
- 2026-08-15: Prepared four tiny routing-test corpus plans and twenty candidate
  canaries under `/private/tmp` for two deliberately confusable pairs. Planning
  generated sixteen chunks with zero provider calls.
- 2026-08-15: Applied the four plans through Buoy's ordinary approved path,
  immediately disabled each generated card, then installed a complete manual
  schema-v1 card. Strong readback found all four targets live and disabled,
  with no missing, stale, or incompatible catalog state; four explicit
  retrieval smokes each returned a hit from its intended test namespace.
- 2026-08-15: Completed strict candidate five-case packs for RentPTR,
  WhiteboxGeo, and Salesforce. Together with the approved legacy-50 projection
  they form a collectible 65-case suite over every currently eligible card;
  adding the four disabled fixture packs produces the later 85-case experiment
  suite. All seven packs remain owner-unapproved candidates.

## Blockers

- The complete modular route-canary answer key now exists, but every new pack
  requires explicit human approval before it can support activation.
- No active confidence thresholds exist. They must be selected on calibration
  data, pass a locked certification split, and receive explicit owner approval.
- Schema-v2 migration and prototype examples wait on the mechanical
  reader-first integration boundary and their exact drift-checked previews.
