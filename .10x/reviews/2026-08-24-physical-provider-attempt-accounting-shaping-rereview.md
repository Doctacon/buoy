Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Target: .10x/research/2026-08-24-physical-provider-attempt-accounting-options.md, .10x/tickets/2026-08-24-define-physical-provider-attempt-accounting.md, commit 0ed20c4d2d68a4a823f689b372095e777a48d459
Verdict: pass

# Physical Provider Attempt Accounting Shaping Rereview

## Target and method

Independent rereview `e91d4f44-e594-4d62-a282-d63236cd0581` inspected repaired
records-only commit `0ed20c4d2d68a4a823f689b372095e777a48d459`, tree
`e0862c2bb2c4b67a234068ad090d2e1f06be03e3`, the source-attribution research,
blocked shaping ticket, parent plan, and exact cited source boundaries. The
review assessed source completeness, cardinality, terminology, privacy,
compatibility, and the owner checkpoint. It performed no implementation or
external operation.

Prior independent review `f17899d7-59f5-43c0-b8f9-66e68f844887` remains a
truthful historical **FAIL** for its reviewed candidate. This rereview does not
rewrite or supersede that verdict; it verifies the four findings were repaired
in `0ed20c4d`.

## Prior FAIL resolution

1. **Catalog bound — repaired.** The records now distinguish maximum successful
   complete read 40,001 from terminal bounded failure 40,002. The extra call is
   the second namespace-list continuation fetched after processing page 10,000
   and before the next-loop bound recheck. Error/interrupted receipt bounds admit
   40,002.
2. **Fanout context — repaired.** CLI `explicit_multi` is 2..3 logical
   namespaces and 2..18 SDK call attempts. Generic `MultiNamespaceRetriever`
   and automatic contexts may be 1..3 and 1..18.
3. **Counting boundary — repaired.** `provider_client_invocation` increments
   immediately before Buoy evaluates each governed SDK call expression, not at
   SDK method-body entry. A local signature `TypeError` counts even when Python
   argument binding prevents method-body entry.
4. **Unit claim — repaired.** The unit is explicitly a Buoy SDK call attempt. It
   does not prove physical wire sends, provider cost, or rate-limit usage;
   actual wire accounting remains unresolved and requires separate transport-
   boundary research.

## Acceptance mapping

- **Source-complete call inventory — PASS.** Content compatibility/schema
  fallback, explicit and automatic routing fanout, catalog strong-read calls,
  cancellation/interruption, and absence of generic content retry are bounded
  without inventing SDK-internal behavior.
- **Privacy-safe candidate — PASS.** The proposed receipt retains bounded route-
  rank/form/trigger/outcome categories and aggregate catalog counts while
  excluding query, argv, namespace, credentials, URLs, payloads, raw errors,
  stacks, paths, and provider responses.
- **Compatibility truthfulness — PASS.** Active telemetry v2 is exact and non-
  extensible. Recurring production telemetry is only an alternative under a
  separately specified compatible schema; no v2 extension is authorized.
- **Shaping gate — PASS.** The child remains blocked on exactly five owner
  decisions. No active specification or executable implementation ticket was
  created.

## Minor reconciliation correction

The child ticket's candidate-surface wording must say “recurring production
telemetry under a separately specified compatible schema,” not “production
telemetry v2.” Closure reconciliation applies that wording because active v2
rejects unknown attributes and cannot be treated as extensible.

## Verdict

**PASS.** Repaired commit `0ed20c4d` is sufficient as a source-complete,
privacy-safe shaping checkpoint after the minor ticket wording correction. The
research recommendation remains unratified, the child remains blocked, and the
parent remains active.

## Exact owner checkpoint

The owner must confirm or correct exactly five decisions:

1. application-boundary `provider_client_invocation` versus separately
   authorized transport-boundary research for wire/cost/rate-limit claims;
2. canary-only terminal receipt versus recurring production telemetry under a
   separately specified compatible schema;
3. content-only versus separately categorized content and automatic-catalog
   families;
4. bounded detail/failure semantics, including 40,001 successful and 40,002
   terminal-failure catalog limits, increment-before-call-expression,
   `success|error|interrupted`, and incomplete receipt meaning unknown; and
5. indefinite sanitized canary-receipt retention, raw-artifact deletion, and no
   recurring production retention/purge change.

After ratification, a focused specification and bounded executable ticket are
still required. This review grants no specification activation, implementation,
schema change, source/test operation, store/provider/model/network/credential/
telemetry/global-tool operation, or canary execution.

## Residual risk

Actual physical wire sends, provider billing, and rate-limit accounting remain
unobserved. The canary-only receipt is a recommendation, not authority.
