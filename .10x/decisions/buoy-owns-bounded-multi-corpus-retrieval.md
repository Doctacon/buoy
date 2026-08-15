Status: active
Created: 2026-08-13
Updated: 2026-08-15
Amends: .10x/decisions/buoy-is-a-focused-indexer.md
Amended-By: .10x/decisions/buoy-uses-bounded-prototype-routing.md

# Buoy Owns Bounded Multi-Corpus Retrieval

## Context

The focused-indexer split moved account-wide discovery, routing catalogs, and
multi-namespace retrieval to Kite. The user has now explicitly returned the
small, retrieval-facing subset to Buoy: one existing remote routing catalog,
automatic selection of at most three content namespaces, and one unified
retrieval result. Buoy's current Turbopuffer account already retains
`buoy-routing-catalog-v1` and three compatible card rows.

## Decision

Buoy owns the following bounded context-navigation behavior:

- list the authenticated account's namespace IDs and intersect them with
  validated rows in the fixed `buoy-routing-catalog-v1` namespace;
- maintain one routing card per content namespace from approved apply or an
  explicit approved catalog command;
- select one high-confidence namespace or at most three ambiguous namespaces;
- embed one retrieval query once, query those namespaces concurrently, and
  locally rerank a bounded multi-namespace candidate set using fixed
  equal-weight ordinal reciprocal-rank fusion (`k=60`) of the pinned MiniLM
  rank and each candidate's namespace-local rank;
- expose route, namespace, reranker, and partial-failure provenance.

Cross-namespace fusion uses no raw provider score and no routing score. Exact
fused-score ties resolve by cross-encoder rank, route rank, namespace-local
rank, namespace, and stable row ID. This keeps incomparable provider scores out
of the global order while preventing the cross-encoder from silently erasing
all namespace-local ranking evidence.

Explicit `--namespace` remains the deterministic bypass. One explicit
namespace retains the focused v0.5.1 retrieval contract.

Kite continues to own cross-plan orchestration, evidence snapshots, concepts,
taxonomy, ontology, graphs, ACL administration, and general-purpose context
management. This decision does not restore the Command Center or any evidence
system.

## Consequences

The focused Buoy boundary and Kite split are amended only for namespace
inventory, routing cards, bounded routing, multi-namespace querying, and result
reranking. The historical catalog namespace is reused without content-namespace
migration or a second catalog.

Catalog mutations remain explicit and reviewed. Automatic retrieval is
read-only. Missing or incompatible live cards fail automatic routing in the
safe direction. Disabled and stale cards are reported and excluded. No read
path creates, repairs, deletes, or enables state.

Multi-corpus ordering combines only ordinal MiniLM and namespace-local ranks.
When the result limit permits, one local-rank-one result from every nonempty
selected corpus survives into the final set; this prevents one corpus from
silently occupying every global slot after the router deliberately selected
several. The result reports any such promotion and does not compare raw
provider scores across namespaces.
