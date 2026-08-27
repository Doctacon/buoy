Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Target: source commit 0b27c4eaa2449493125f4040af3cd1f7c926b531, tree 9017c4a335938faca80cdded54545df8b79c12f8; records commit 327bcf43b73b5941a0c94ab9fb4aa294456ea498, tree 0c187238d8abe09cf0d99aa8fdb53f1a5112900e
Verdict: pass

# Provider Invocation Receipt Integration Review

## Target and provenance

This record durably preserves the complete independent CLI/integration review
lineage and the governing final PASS. The final reviewer inspected exact source
commit `0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`, together with committed validation
records at `327bcf43b73b5941a0c94ab9fb4aa294456ea498`, tree
`0c187238d8abe09cf0d99aa8fdb53f1a5112900e`.

All three reviews were read-only. None reran the recorded validation. Their
source artifacts were outside the repository and are identified here so the
verdict history remains independently refindable:

| Review | External artifact | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Historical staged-CLI FAIL | `/Users/crlough/.pi/agent/sessions/--Users-crlough-Code-personal-turbo-search--/subagent-artifacts/14ba8d2a-6e8b-4046-8e56-9c00edd52c98_reviewer_0_output.md` | 2,041 | `8b65cbe278886822aa526847ebc92d9f2c008dc54090117ccd0b87919e306739` |
| Repaired staged-CLI PASS | `/Users/crlough/.pi/agent/sessions/--Users-crlough-Code-personal-turbo-search--/subagent-artifacts/a4b0451e-5f8b-4f7c-8f52-23d3a4d6ad6e_reviewer_0_output.md` | 1,733 | `6aa365f8b276f661e56a4b30ba8449f762fff6158eed01bff3001650f34b8e13` |
| Governing exact-final PASS | `/Users/crlough/.pi/agent/sessions/--Users-crlough-Code-personal-turbo-search--/subagent-artifacts/cd847ba4-9828-4ae6-bc90-122a48a22cb3_reviewer_0_output.md` | 5,687 | `f52679275f61e4fe615b513c5aee59ae35d26b300f07398090115ec696b6614e` |

## Historical staged-CLI FAIL

The first staged-CLI review correctly accepted these properties:

- automatic retrieval alone obtained and explicitly passed the private catalog
  observer at `src/buoy_search/cli.py:17,1643-1647`;
- `read_remote_catalog` and helpers defaulted the capability to `None` without
  ambient receipt lookup;
- all 14 production/script callers were inspected: apply 2, catalog management
  9, evaluation scripts 2, automatic CLI 1, with only automatic CLI passing the
  private capability;
- default-off/public audits covered package exports, parser flags, environment
  activation, persistence, and telemetry-v2 drift;
- automatic preview/live, explicit live, exception identity, leases,
  concurrency, observer faults, output equivalence, privacy, and family
  separation were covered; and
- the routing artifact correctly remained intentionally stale before the
  final-CLI review gate.

**Historical verdict: FAIL.** The integration ticket required both explicit live
and explicit preview command paths, but the staged tests did not run explicit
`--dry-run`. The exact requested repair was an active-scope explicit
`--namespace ... --dry-run --json` case asserting exit 0, expected preview
output, empty stderr, no retriever/provider construction, null catalog outcome,
zero catalog counters, and zero content operations/invocations. No production
source repair was requested. This finding remains historical and is not erased
by later PASS verdicts.

## Repaired staged-CLI PASS

The repaired review targeted exact staging commit
`bb32b4f81fbb490472a68e7caaf00d0a4dfab379`, tree
`9d42b419c2240ca53566056940d02e5c84d0baad`.

It confirmed that `tests/test_provider_invocation_receipt_integration.py:212-296`
added the exact explicit `--namespace ... --dry-run --json` path and proved exit
0, no stderr, no retriever/provider construction, and exact zero content/catalog
accounting. It reconfirmed automatic retrieve as the sole production observer
caller, default-`None` isolation, and integrated automatic preview/live,
failure, concurrency, observer-fault, privacy, and public-surface coverage.

**Intermediate verdict: PASS with no blocker for the pre-artifact CLI-byte
gate.** The old routing-artifact receipt remained intentionally expected at
that stage, so the review explicitly did not represent final ticket closure.

## Governing exact-final review findings

The final independent review found:

- **Correct:** Exact source candidate `0b27c4eaa2449493125f4040af3cd1f7c926b531`,
  tree `9017c4a335938faca80cdded54545df8b79c12f8`, satisfies the integration
  and parent-plan contracts.
- **Correct:** The private lifecycle is default-off, nested-scope-safe,
  lease-aware, thread-safe, canonical, and null-on-incomplete/fault at
  `src/buoy_search/_provider_invocation_receipt.py:471,619,765,963,1162,1208`.
- **Correct:** Content observation surrounds the exact route and SDK-expression
  boundaries without changing fallback behavior at
  `src/buoy_search/retriever.py:718,1323,1855,1881`.
- **Correct:** Catalog observation is capability-explicit.
  `read_remote_catalog` defaults to `None`; only automatic retrieval passes
  `_active_catalog_observer()` at `src/buoy_search/remote_catalog.py:683-690`
  and `src/buoy_search/cli.py:17,1643-1647`. Exhaustive search found the other
  13 callers argument-free.
- **Correct:** Integration assertions at
  `tests/test_provider_invocation_receipt_integration.py:173-694` cover explicit
  preview/live, automatic preview/live, catalog-only preview, separated live
  families, pre-call/partial/all failure, nested/concurrent scopes, worker
  propagation, exception classes, observer failure, privacy, public-surface
  containment, and telemetry-v2 nonextension.
- **Correct:** Core/content/catalog tests inspect exact grammar, identities,
  conditional aggregate matrices, 40,001/40,002 boundaries, canonical bytes,
  privacy, and failure equivalence rather than relying only on counts.
- **Blocker:** None.
- **Fixed:** None required by the final review.

## Integration criterion mapping

1. **Explicit/automatic live and preview — pass.** Tests `173-336` prove
   explicit preview zero-call, explicit-live null catalog, automatic-preview
   catalog-only, and separated automatic-live families.
2. **Caller isolation — pass.** Tests `607-639` and exhaustive source search
   prove 14 callers and exactly one private-capability caller.
3. **Terminal authority/unknown handling — pass.** Pre-exit, incomplete-worker,
   observer-fault, invalid-model, and terminal exception cases are covered.
4. **Lifecycle, concurrency, workers, cancellation and identity — pass.** Both
   cancellation classes, named/custom control-flow values, ordinary exceptions,
   nested/independent contexts, leases, never-run workers, and restoration are
   asserted.
5. **Aggregate matrices — pass.** Source `963-1058` and core/catalog tables
   enforce prerequisites, per-category bounds, ambiguous-state rejection, exact
   40,002 composition, and overflow.
6. **Privacy — pass.** Models retain route rank or fixed aggregate categories
   only; exact bytes and generic diagnostics exclude every governed sentinel.
7. **Private/default-off/nonpersistent/nontelemetry — pass.** Package exports
   only version; parser/source audits reject CLI/env/public/persistence and
   telemetry-v2 widening.
8. **Provider/model/store-free validation — pass by recorded evidence.** Exact
   91/91 and 535/535 dual-runtime suites and 1,167/1,167 full-repository suites
   are preserved in the closure evidence.
9. **CLI receipt/package reproduction — pass.** The schema-v3 artifact has the
   exact CLI hash at line 57; only `/receipts/cli_module_sha256` changed; source,
   wheel, sdist, and isolated install reproduced and strictly enforced it.
10. **Independent exact-candidate review — pass.** This final review supplies
    the required gate.

## Parent-plan and active-spec drift gate

All five aggregate parent criteria pass:

1. core, content, and catalog children have exact reviewed commits, focused
   closure evidence, and PASS reviews; integration maps above;
2. fake-only tests cover governed boundaries, strict models, privacy,
   concurrency, caller isolation, and observer faults;
3. reviewed scope adds no public/env/persistence/telemetry-v2 or unrelated
   production surface;
4. recorded focused, broad, full-repository, artifact, build, and isolated-
   install validation passes on both required runtimes; and
5. the exact-final review passes the source and records candidates against both
   active specifications.

No active-spec narrowing or contradiction was found. Content/catalog source
boundaries, source-order validation, cancellation precedence, terminal
authority, canonicalization, privacy, worker lifecycle, and default-off
activation remain regeneration-grade.

## Verdict

**PASS.** Exact source commit
`0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`, with validation records commit
`327bcf43b73b5941a0c94ab9fb4aa294456ea498`, tree
`0c187238d8abe09cf0d99aa8fdb53f1a5112900e`, satisfies every integration-child
and aggregate parent-plan criterion. Blockers: none. Required source repair:
none.

## Residual risk and limits

The reviews inspected, but did not rerun, recorded validation. Fake-only
validation does not prove live provider behavior, SDK-internal retries, physical
wire sends, billing, cost, or rate-limit use. These are not unresolved closure
findings: they remain expressly excluded here and durably owned by
`.10x/tickets/2026-08-24-run-one-time-live-provider-invocation-receipt-canary.md`.
