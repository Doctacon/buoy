# Buoy and Kite

Buoy owns a bounded source-to-search loop:

- acquire one source and produce one reviewable plan;
- apply one approved delta to one content namespace;
- register or refresh that namespace's validated routing card;
- inspect and explicitly manage routing-card enablement;
- choose at most three compatible content namespaces for one question; and
- retrieve, deduplicate, and locally rerank anchored results.

This is enough for `buoy retrieve QUERY` to navigate the indexes Buoy created
without requiring the caller to know their namespace IDs. It is not a general
knowledge-control plane.

[Kite](https://github.com/Doctacon/kite) retains the broader capabilities:

- cross-plan orchestration, durable jobs, and operator workflows;
- evidence snapshots and governed evidence lifecycles;
- concepts, mentions, assertions, taxonomy, ontology, and graph modeling;
- tenant/account policy, ACL-aware routing, and wider context assembly; and
- learned, hierarchical, decomposed, or unbounded routing beyond Buoy's fixed
  one-to-three-corpus search.

## Integration boundary

Successful approved apply emits `receipt_schema_version=1`. The JSON summary
binds source, namespace, region, plan/apply IDs, artifact hash, embedding and
ranking contracts, write counts, retrieval commands, and routing-card
registration status. Kite may consume that receipt; Buoy does not import Kite
or write Kite evidence, ontology, policy, or job state.

Buoy's automatic router is deliberately small: it reads exact schema-v1, v2,
or v3 cards from `buoy-routing-catalog-v1` and chooses no more than three
compatible enabled cards. Missing cards for unrelated live namespaces are
diagnostics, not a global availability stop. A caller that already has
policy-approved targets can repeat explicit `--namespace` and bypass inventory,
catalog, and routing-model reads.

Existing content namespaces and local applied-state databases remain valid.
Current local planning and apply accept only schema-v3/delta-v2 artifacts;
historical schema-v1/v2 plans are preserved but inert.

## Legacy control-plane state

The existing `buoy-routing-catalog-v1` namespace is reused as Buoy's routing
authority. Buoy reads it for automatic retrieval and writes one reviewed card
through approved apply or an approved `catalog` mutation. Those operations
never mutate the card's target content namespace.

Schema-v3 plan registration requires that catalog to exist at exact remote
schema v3. Deploy compatible readers first, then provision a missing catalog or
migrate v1/v2 through separately reviewed operations. Ordinary apply never
creates or migrates it. If the prerequisite is absent after content and local
state commit, apply returns partial success, makes no catalog schema/card write,
and retains the exact plan for its emitted
`catalog repair-apply --inspect-current` command. After prerequisite recovery,
that read-only command revalidates committed authority under the namespace lock,
strongly reads exact-v3 state, and emits an absence- or revision-bound repair.
The same fallback applies when catalog state could not be read safely. Inspection
writes nothing and retains the plan; only after successful bound repair may
exact plan cleanup run.

Schema-v3 cards carry bounded, verbatim-derived source excerpts. Buoy redacts
them from normal output, but Kite or any other principal with credentials that
can query raw catalog provider rows can read them. The catalog credential and
ACL boundary must therefore be governed as source-content access rather than
metadata-only access.

The feature does not delete or repurpose:

- `buoy-evidence-*` namespaces;
- old local catalog-pending files;
- Command Center job history;
- historical plans or repository records.

Buoy does not read or write the evidence namespaces. Old local pending files do
not become remote routing authority and are not an automatic repair queue.
Stale remote cards are reported rather than removed; disabling a duplicate card
keeps its history while excluding it from automatic routes.

An incomplete evidence-snapshot attempt recorded in unmerged commit `61f4d84`
wrote 1,000 ledger rows before stopping. It is not treated as complete, and
automatic retrieval performs no repair or cleanup. Recovery still requires a
separately approved exact-ID provider inventory; prefix deletion and inferred
ownership remain forbidden.
