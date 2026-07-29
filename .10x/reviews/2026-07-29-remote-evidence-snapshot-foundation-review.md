Status: recorded
Created: 2026-07-29
Updated: 2026-07-29
Target: work/remote-evidence-snapshot-foundation diff from 606c168389e28b09105e8eb139f2cde063994a83
Verdict: pass

# Remote Evidence Snapshot Foundation Review

## Target

The Phase 3A implementation, tests, documentation, specification/research/ticket graph, and packaging changes on `work/remote-evidence-snapshot-foundation`.

## Assumptions tested

- Provider import and credentials remain lazy.
- Full source content/vector data is retained only by turbopuffer branches, not locally or in the ledger.
- Local applied rows and remote pages/batches remain bounded.
- Apply locks cover the point-in-time state used for identity and publication.
- Sharding, budgets, collisions, drift, and partial failures fail before a visible completed snapshot or clean only current internal artifacts.
- Catalog completion is last and remote-only verification needs no current state database.
- Internal evidence namespace IDs cannot become ordinary automatic-routing/discovery/Command Center source rows.
- Documentation does not claim graph extraction, taxonomy, ontology, provider-enforced immutability, exact storage, retention, or deletion.

## Findings

### No blocking correctness or safety finding

Inspection of `evidence_snapshot.py:123-343`, `applied_state.py:362-488`, and `evidence_remote.py:323-1266` found deterministic identity, descriptor-bound `fetchmany` state reads, sorted locks, exact branch/ledger/catalog names, strong 10,000-row query pagination, bounded ledger upserts, exact reconciliation, catalog-last finalization, atomic bounded manifest writes, and guarded cleanup. Tests exercise the requested success/failure classes and the 100,000-row structural case.

### Safe contract clarification — zero-row completed state

Turbopuffer 2.4.0 documents schema-only writes only for existing namespaces. An absent zero-row ledger cannot be created without a sentinel that would violate the one-row-per-state-row contract. The implementation therefore rejects zero-row applied state before remote creation and records that limit in the active spec and documentation. This is fail-closed and does not broaden remote mutation.

### Compatibility preserved

`remote_catalog.py:464-467` subtracts `buoy-evidence-` IDs from content-live classification while retaining total listing semantics, so existing public routing-count output remains stable. Namespace CLI and explicit Command Center search also reject internal IDs. The full 839-test suite passes.

### Operational limitations are stated accurately

Branches are not technically immutable; metadata plus complete reconciliation detects external changes. Logical bytes are approximate and potentially billable. Live provider behavior was not exercised. Cleanup refuses deletion when completed catalog state cannot be ruled out.

## Verdict

Pass. The diff implements the bounded Phase 3A contract without graph extraction, local corpus duplication, source mutation, lifecycle deletion commands, or UI scope.

## Residual risk

- No opt-in live smoke was authorized, so fake-client behavior is the acceptance boundary for provider calls.
- Provider strong consistency and metadata timestamp fidelity retain the official operational caveats.
- The scale RSS figure includes fake remote state held in the test process; it proves the bounded code paths structurally, not production client RSS in isolation.
