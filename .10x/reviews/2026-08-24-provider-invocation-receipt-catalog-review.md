Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Target: commit d9399e86e121e00f403f5f3a1d674f70c2d75aa4, tree 1359284ad942224c6873ca810f7de93fd188ad9c, src/buoy_search/_provider_invocation_receipt.py, src/buoy_search/remote_catalog.py, tests/test_provider_invocation_receipt_catalog.py, tests/test_provider_invocation_receipt_core.py
Verdict: pass

# Provider Invocation Receipt Catalog Review

## Target and provenance

This durable record preserves the supplied independent PASS review of exact
source commit `d9399e86e121e00f403f5f3a1d674f70c2d75aa4`, tree
`1359284ad942224c6873ca810f7de93fd188ad9c`.

The review inspected exact branch/reflog identity, catalog instrumentation, the
bounded core transformed-cancellation repair, focused catalog and relevant core
tests, active provider-invocation specifications, caller/privacy/public/scope
boundaries, and attested validation. It was read-only and did not rerun tests.

## Historical review lineage

This PASS applies only to the final exact target and does not rewrite prior
verdicts or defect history:

- the historical contract FAIL remains at
  `.10x/reviews/2026-08-24-provider-client-invocation-contract-review.md` for
  exact records candidate `a458aeba95844230271ad50d4364281f4462ad5e`;
- the governing repaired-contract PASS remains separately recorded at
  `.10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md` for
  exact contract commit `cb4a76b97f68fcdfc2816c49c33b5b23e9b5f899`;
- the independently reviewed core and content predecessors remain separately
  closed at their exact reviewed commits/trees; and
- execution's discovery and approved repair of transformed catalog cancellation
  remains in the owning catalog ticket's append-only progress. It is not
  retroactively folded into or erased from the predecessor core review.

No earlier catalog-candidate review artifact exists in the record graph, so this
record does not invent or overwrite one.

## Findings

### Explicit capability and exact expression boundaries

- `read_remote_catalog` has an explicit private observer default of `None` and
  passes only its operation capability through L1, metadata, C1, C2, and L2 at
  `src/buoy_search/remote_catalog.py:683-737`.
- Helpers also default to `None`; initial `namespaces`, each reached
  `get_next_page`, and each card query are wrapped at source lines 1056-1180.
- There is no ambient discovery: `remote_catalog.py` contains neither
  `_active_ledger` nor `ContextVar`. The only production `_catalog_observer`
  definition remains private at
  `src/buoy_search/_provider_invocation_receipt.py:454-464`.
- Minimum and multipage tests at
  `tests/test_provider_invocation_receipt_catalog.py:322-405` verify five calls,
  exact category totals, SDK arguments, strong consistency, continuation
  observation, and exact source order.

### Aggregate validation and source order

- Aggregate validation at
  `src/buoy_search/_provider_invocation_receipt.py:951-1058` enforces category
  maxima, terminal prerequisites, mixed/later-stage rejection, local terminal
  stages, a successful 40,001 maximum, and terminal 40,002 bounds.
- Catalog tables at test lines 407-495 cover conditional bounds, ordered
  impossibilities, adjacent overflow, and 40,001/40,002 compositions. Reviewed
  core tests at `tests/test_provider_invocation_receipt_core.py:695-824`
  additionally cover the valid 40,002 L2-terminal-invocation form and exact all-
  success terminal composition.

### Outcomes and transformed cancellation

- The approved `concurrent.futures.CancelledError` repair is narrowly catalog-
  specific: an already recorded interrupted invocation overrides transformed
  outer `RemoteCatalogError` only for operation accounting at
  `src/buoy_search/_provider_invocation_receipt.py:683-695`.
- Tests at catalog lines 497-602 prove baseline-equivalent caller type/message,
  authoritative interrupted receipt, one invocation, and ordinary-error
  preservation.
- SDK interruption/error identity, metadata termination, post-return failures,
  and page-bound failures are covered at catalog lines 497-699. Observer faults
  preserve exactly-once evaluation, result/exception identity, full read
  completion, and null authority at lines 729-836.

### Privacy and containment

- Privacy remains aggregate-only. Exact receipt keys and sentinel exclusion are
  asserted at catalog test lines 838-864; no pass, cursor, identifier, payload,
  billing, or error detail enters the ledger.
- Apply, catalog-management, automatic CLI, evaluation scripts, and
  direct/default callers omit `_invocation_observer`, including
  `src/buoy_search/apply.py:917,997`,
  `src/buoy_search/catalog_cli.py:264,894,1169,1222,1396,1453,1619,1706,1883`,
  `src/buoy_search/cli.py:1642`, and both evaluation scripts. Containment tests
  are at catalog lines 701-727.
- Inspection found no package-public export, automatic CLI wiring, environment
  activation, telemetry, persistence, routing, pagination, provider/model/store,
  or catalog-management widening.

### Acceptance and spec coherence

All nine owning-ticket acceptance criteria map to exact source and focused tests
in `.10x/evidence/2026-08-24-provider-invocation-receipt-catalog-closure.md`,
including the separately approved transformed-cancellation core defect.

Both active provider-invocation specifications match the reviewed
implementation. The explicit shared-reader capability, exact catalog source
order, aggregate validator, interruption precedence, private/default-off
lifecycle, privacy contract, and observer-failure isolation are neither narrowed
nor contradicted.

## Verdict

**PASS.** Exact commit `d9399e86e121e00f403f5f3a1d674f70c2d75aa4`,
tree `1359284ad942224c6873ca810f7de93fd188ad9c`, satisfies every catalog-ticket
acceptance criterion. Blocker: none. Exact repairs required: none.

## Residual risk and limits

Validation is attested in the owning ticket: remote-catalog plus
core/content/catalog receipt tests passed 130/130 on Python 3.11 and 130/130 on
Python 3.13, alongside exact static checks, both frozen-contract validators, and
`git diff --check`. This independent review inspected that attestation rather
than rerunning it; exact historical shell strings and raw output were not
retained.

The PASS is fake-only and application-boundary-only. It does not prove live SDK
or provider behavior, SDK-internal retries, physical wire sends, billing, cost,
or rate-limit use. Integrated automatic-retrieve CLI wiring/final validation and
the separately authorized live canary remain outside this ticket and under
their own gates.
