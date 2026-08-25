Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Target: commit a458aeba95844230271ad50d4364281f4462ad5e, tree 05c720c9e77ee335079114694ec89b04e5d05e84, .10x/specs/provider-client-invocation-accounting.md, .10x/specs/provider-client-invocation-receipt.md, .10x/tickets/2026-08-24-implement-private-provider-invocation-receipts.md
Verdict: fail

# Provider Client Invocation Contract Review

## Target and method

Independent review run `29dbeef6-82a2-43b1-8fd3-b572f0d83f40`
reviewed records-only candidate commit
`a458aeba95844230271ad50d4364281f4462ad5e`, tree
`05c720c9e77ee335079114694ec89b04e5d05e84`, against the ratified owner
contract and exact source boundaries. The review found three significant
execution blockers. This verdict remains historical authority for that exact
candidate; a repaired commit requires fresh independent rereview.

## Findings

### Significant: aggregate catalog validation admitted impossible source orders

The catalog family had only a global total and weak minimums. It did not encode
per-category successful/terminal maxima or enough prerequisite relationships to
validate the source order:

```text
first namespace-list pass -> metadata -> first card pass ->
second card pass -> second namespace-list pass
```

That weakness admitted impossible combinations, including metadata/card calls
without a completed first list, second-list-scale aggregate counts without
metadata/two completed card passes, and success totals that could not be split
across both passes. The validator contract needed an exact aggregate state
machine without retaining pass IDs. In particular, 40,002 all-success terminal
must be exactly 20,001 namespace-list + 1 metadata + 20,000 card calls.

### Significant: interruption precedence was ambiguous

“Cancellation exceptions” did not fix the precedence needed because
`concurrent.futures.CancelledError` is an `Exception`. The contract needed to
classify both `asyncio.CancelledError` and
`concurrent.futures.CancelledError` as `interrupted` before the generic
`Exception` rule; classify all non-`Exception` `BaseException` values,
including `KeyboardInterrupt`, `SystemExit`, and `GeneratorExit`, as
`interrupted`; classify every other `Exception` as `error`; and require
identical exception preservation tests.

### Significant: shared catalog reader could observe non-retrieve callers

`read_remote_catalog` is shared by automatic retrieve, apply, and catalog
management paths. A receipt-global observer lookup inside that shared reader
would count apply/catalog activity whenever a private receipt scope happened to
be active, widening the ratified automatic-retrieve-only family. The contract
needed an explicit private observer/ledger argument defaulting to `None`,
propagated through read helpers, with only automatic-retrieve CLI wiring allowed
to pass the active observer. Because that wiring changes `cli.py`, the final
integration child also needed exact schema-v3 routing CLI-receipt
recertification under the active decision.

## Verdict

**FAIL.** Candidate `a458aeb` was not regeneration-grade for implementation.
The active owner semantics remained valid, but implementation tickets had to
stay open/inactive while the three mechanical blockers were repaired in
records and independently rereviewed.

## Residual scope boundary

The repair grants no new product surface, provider/model/catalog/content
operation, telemetry/store/migration behavior, source/test implementation,
public observer, or live canary. Catalog receipt accounting remains restricted
to automatic retrieve, and routing semantics/artifact fields other than the
final governed CLI source hash remain frozen.
