# Buoy and Kite

Buoy has returned to its original focused contract: one source, one reviewed
plan, one Turbopuffer namespace, one search target.

[Kite](https://github.com/Doctacon/kite) owns the capabilities that appeared
after that contract was proven:

- account-wide namespace inventory and source-index catalog;
- automatic semantic routing and multi-namespace retrieval;
- cross-namespace evidence snapshots;
- concepts, mentions, assertions, taxonomy, ontology, and Data Vault guidance;
- the cross-plan operator console and durable jobs.

## Integration boundary

Successful approved apply emits `receipt_schema_version=1`. The JSON summary
binds the source, namespace, region, plan/apply IDs, artifact hash, embedding
contract, ranking contract, and write counts. Kite consumes that receipt; Buoy
does not import Kite or write Kite control-plane state.

Existing schema-v2 plans, content namespaces, and local applied-state databases
remain valid.

## Legacy control-plane state

The refocus does not delete or mutate:

- `buoy-routing-catalog-v1`;
- `buoy-evidence-*` namespaces;
- old local catalog-pending files;
- Command Center job history;
- historical plans or repository records.

Buoy simply stops reading and writing the catalog/evidence/operator surfaces.
Kite may later import validated legacy cards or evidence through an explicit
migration.

An incomplete evidence-snapshot attempt recorded in unmerged commit `61f4d84`
wrote 1,000 ledger rows before stopping. It is not treated as complete and this
split performs no repair or cleanup. Recovery requires a separately approved,
exact-ID provider inventory; prefix deletion and inferred ownership are
forbidden.
