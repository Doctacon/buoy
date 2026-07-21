Status: recorded
Created: 2026-07-21
Updated: 2026-07-21
Target: PR #77 at `ec5dbbb19ec705c66e674b51bf86e8b84c0b3f89`
Verdict: concerns

# Experimental Buoy Baseline Execution Evidence Review

## Target

Independent adversarial review of PR #77's record-only invocation evidence at exact reviewed head `ec5dbbb19ec705c66e674b51bf86e8b84c0b3f89`, governed by `.10x/specs/experimental-buoy-baseline-executor.md` and `.10x/tickets/2026-07-20-source-pin-and-execute-experimental-buoy-baseline.md`.

## Findings

### PASS — raw observation, accounting, effects, and consumed authority are preserved

The structured artifact `.10x/evidence/.storage/2026-07-21-experimental-buoy-baseline-execution.json` has SHA-256 `cf2cba77bfe1b6f854569887ddcd3d4d07335541088a5a554588d6d2e10ccdcd` and preserves:

- exactly two attempted metadata reads, zero writes, zero deletes, zero returned-row positions, and zero attempted write-row positions;
- slots 1 and 3 as succeeded and slots 2 and 4–26 as unused, with no reassignment;
- no pending record or DuckDB applied-state commit;
- creation of the exact persistent state-root/lock-file path, exit from the lock context, and no cleanup;
- the one public invocation, which irrevocably consumed Approval A;
- the catalog raw projection with `schema.vector.ann.distance_metric=cosine_distance`, `distance_metric_present=false`, and top-level `distance_metric=null`.

The evidence therefore supports the bounded stop and absence of operation-attributable remote mutation. It does not support completion of a compatible baseline.

### Significant — the original wording misattributes an executor metadata-shape assumption to provider compatibility

The raw provider authority proves the catalog vector schema uses `cosine_distance`. The executor separately checks `metadata.get("distance_metric")` after validating the schema and raises when that redundant top-level field is absent. PR #77's original evidence/ticket wording treats that missing top-level marker as a catalog compatibility blocker without identifying the executor's redundant response-shape assumption.

The failure must be characterized as an executor/provider-metadata interpretation failure, not provider cosine incompatibility. The raw JSON, slots, effects, and lock observations must remain unchanged while the prose is corrected.

### Significant — no retry or repair follows from the corrected interpretation

Approval A was consumed by the one invocation regardless of why execution stopped. No compatible baseline exists because card reads, content writes, verification, and local applied-state commit never occurred. Correcting the record does not authorize an executor repair, retry, resume, cleanup, second invocation, replacement approval, Approval B, or C3. Provider-metadata interpretation and any possible future new operation require a separate open shaping owner; opening that owner grants neither repair authority nor a new approval.

## Procedure

1. Compared the checked-in raw projection, slot ledger, counters, invocation error, and local/effect observations with the Markdown evidence and owning ticket.
2. Inspected the executor's checked-in metadata capture and catalog validation paths without editing or invoking them.
3. Confirmed PR #77 hosted Python 3.11, Python 3.13, and Build distributions checks passed at the reviewed head.
4. Made no credential, model, provider, retained-state, lock, cleanup, retry, resume, Approval B, or C3 operation.

## Verdict

CONCERNS. The raw evidence and bounded accounting are usable, but the provider-compatibility characterization requires record-only correction. The owning ticket must be `blocked`, not `done`; Approval A remains irrevocably consumed; no compatible baseline exists; and no operational follow-on is authorized.

## Residual risk

The correct durable interpretation of the provider's metadata shape versus executor expectations is not yet specified. No post-abort provider observation is available or authorized. A separate shaping ticket must own that interpretation and the gates for any possible future operation without implying repair or approval.
