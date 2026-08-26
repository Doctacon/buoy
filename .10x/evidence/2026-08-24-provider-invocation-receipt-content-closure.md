Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/done/2026-08-24-instrument-content-provider-invocations.md, .10x/specs/provider-client-invocation-accounting.md, .10x/specs/provider-client-invocation-receipt.md, .10x/reviews/2026-08-24-provider-invocation-receipt-content-review.md

# Provider Invocation Receipt Content Closure Evidence

## What was observed

The independently reviewed source target is exact commit
`e72841d2c4553c66f99be9f57efc1cd137fd543d`, tree
`8fea9db249214a6d633a7d34d2c014fbcd6e816b`.

Relative to the separately committed content activation state
`86a0d71a3972a95af6fbd4ba6969e09ea417fb94`, the reviewed candidate changes
exactly four paths:

- 27 append-only lines in the owning content ticket, now
  `.10x/tickets/done/2026-08-24-instrument-content-provider-invocations.md`;
- 4 insertions and 1 deletion in
  `src/buoy_search/_provider_invocation_receipt.py` for the authorized
  transformed-cancellation classification repair;
- 83 insertions and 15 deletions in `src/buoy_search/retriever.py`; and
- the new 850-line, 23-test
  `tests/test_provider_invocation_receipt_content.py`.

The focused implementation diff is 964 insertions and 16 deletions. It does not
change `src/buoy_search/__init__.py`, `src/buoy_search/cli.py`, `pyproject.toml`,
or `uv.lock`. At the reviewed target, the relevant Git blobs and SHA-256 values
are:

| Path | Git blob | SHA-256 |
| --- | --- | --- |
| `src/buoy_search/_provider_invocation_receipt.py` | `a2f888dc8db1409d514a15298d31fd9a8847bcf7` | `56a7f29f0c5c78c4b8ff4f3adbc3b8b2b0d6e28daf2849b900f0deb2534848c1` |
| `src/buoy_search/retriever.py` | `d87530fb4db81029744273ef27d7f1e0e4ca302c` | `89aeb5db61a1997f127db2ebe651beb9f184d4358e0e0cd3d98921713c9b613d` |
| `tests/test_provider_invocation_receipt_content.py` | `fc304b4d56e51ae5d7b755b7ed0d2e614d11d3d8` | `98bddbcf973ebc06bec427c34f9e6797efb16165ca118215f776c9bffc968e6a` |
| `tests/test_provider_invocation_receipt_core.py` | `73b8a10340479044c3b7479f76a8c2a85a4674ce` | `8645265455da03423286fa3e77cf18757e3cd80d195b2f88aa2e37ee367c15bc` |
| `src/buoy_search/__init__.py` | `017662a5839d76632901e60a6f9b1fc68a3f17e1` | `2e73f77e75d1e9bb0f9be953e9c9846f3d4eac9ede3294573df0348b1630c3e6` |

This closure changes records only and preserves those reviewed source/test
blobs.

## Attested implementation validation

The owning ticket's append-only implementation notes attest the following
credential-removed, telemetry-disabled, strict-offline results:

- 45 core plus 23 content tests passed, 68/68, on Python 3.11;
- the same 68/68 tests passed on Python 3.13;
- 57/57 retriever and multi-namespace tests passed;
- 15/15 local retrieval telemetry tests passed;
- both frozen-contract validators passed;
- AST inspection of exact call boundaries and the prohibition on ambient
  context copying passed;
- `git diff --check` passed; and
- generated-version cleanup left the candidate clean.

The count is internally consistent with 45 focused core test methods and 23
focused content test methods present at the reviewed target. Tests used local
fakes only. No provider, network, credential, model, content store, telemetry
store, database, persistence, canary, catalog, routing/ranking, release, or
global-tool operation ran.

The exact historical shell strings and raw console output were not retained in
the implementation commit. The independent PASS review inspected the source,
the focused tests, and the internally consistent attestation but did not rerun
them. This records-only closure likewise did not rerun tests, as directed.

## Acceptance-criterion mapping

1. **Server/client invocation accounting — supported.**
   `_invoke_content_expression` registers immediately before evaluating each
   exact SDK expression at `src/buoy_search/retriever.py:1855-1909`. Server RRF
   retains `rerank_by=("RRF",)`, client fallback omits it, and both subqueries
   remain one invocation. Focused tests at
   `tests/test_provider_invocation_receipt_content.py:279-299,356-390` prove a
   successful server call is one attempt and local signature rejection plus
   client fallback is two attempts, including the pre-method-entry attempt.
2. **Exact optional-schema grammar and retry bound — supported.** Trigger
   threading at `src/buoy_search/retriever.py:760-792` applies only to the two
   governed optional attributes. Tests at lines 190-278 cover every sequence
   length 1..6 and one/two removals with and without client fallback; lines
   300-341 prove an unrelated error adds no retry.
3. **Routes, fanout, deterministic order, and maximum — supported.** Explicit
   route 1 begins only around the content operation at source lines 718-725;
   workers begin ranked operations at lines 1322-1329. Tests at lines 488-551
   cover explicit single, CLI two/three-route fanout, concurrent deterministic
   route order, and the exact three-route/eighteen-attempt maximum.
4. **Terminal outcomes and the authorized transformed-cancellation defect —
   supported.** Tests at lines 553-690 cover top-1 stopping, empty/failed
   widening without route repetition, missing reranker before first/later calls,
   partial/all failure, post-response failure, and zero-attempt failure. The
   bounded core repair at
   `src/buoy_search/_provider_invocation_receipt.py:624-632` overrides outer
   exception classification only when the already-recorded final attempt is
   `interrupted`. The regression at test lines 449-484 proves unchanged
   sanitized external `ProviderCallError` type, message, cause/context, and
   one-call count while both authoritative attempt and operation are
   `interrupted`. Ordinary errors remain `error` at lines 300-341, 591-638, and
   673-690. This is the separately authorized core defect allowed by the
   ticket's exclusion boundary; no broader core behavior changed.
5. **Missing operation registration — supported.** Source lines 1855-1878 and
   tests at lines 342-390 prove a governed expression without a registered
   logical operation executes exactly once and invalidates only receipt
   authority.
6. **Disabled and observer/propagation fault equivalence — supported.** Receipt
   worker binding is composed with the existing telemetry callable at source
   lines 1277-1284 rather than replacing it. Tests at lines 700-846 cover
   disabled mode, ledger and observer access faults, submission failure, lease
   registration/claim/release faults, worker bind/reset faults, no copying of
   unrelated context, identical worker interruption propagation, and unchanged
   call/result/exception behavior.
7. **Local-fake privacy and bounded scope — supported.** Receipt-byte sentinels
   at test lines 392-414 exclude query, namespace, content, path, provider
   detail, raw error, schema attribute, and SDK keyword data. Candidate-path
   inspection shows no catalog, CLI activation, environment, package-public API,
   persistence, telemetry schema, provider/model/store, routing, or ranking
   widening.

## Active-spec coherence

The behavioral bodies of
`.10x/specs/provider-client-invocation-accounting.md` and
`.10x/specs/provider-client-invocation-receipt.md` are unchanged from the
independently accepted contract at
`cb4a76b97f68fcdfc2816c49c33b5b23e9b5f899`. The only later spec diff adds
`Prior-Review` and updates `Review` metadata so the historical contract FAIL and
governing PASS both remain visible.

The exact content boundaries, route/attempt grammar, terminal outcome rules,
worker leases, default-off/private lifecycle, privacy contract, and
observer-failure isolation in both active specs match the reviewed source and
tests. In particular, the transformed-cancellation repair implements the
accounting rule that a final interrupted invocation makes the operation
interrupted while preserving the lifecycle spec's external behavior and
exception-isolation requirements. No active scenario is narrowed or
contradicted.

## Procedure

Closure inspection used read-only Git/status/log/diff/tree/blob/hash/search and
file-reading commands. It confirmed:

- a clean reviewed worktree before closure mutation;
- exact reviewed HEAD and tree;
- current `develop` is an ancestor of the reviewed candidate;
- the exact activation-to-candidate changed-path/stat boundary;
- 23 content and 45 core focused test methods at the reviewed target;
- unchanged package initializer, CLI, dependency, and lockfile boundaries;
- spec behavior drift is limited to review-metadata preservation; and
- all active `.10x` references affected by the ticket move are repaired by this
  closure.

No test, provider, model, network, store, credential, canary, telemetry,
database, persistence, catalog, routing/ranking, release, or installed-tool
operation ran during closure.

## What this supports

This evidence supports closing only content provider invocation instrumentation
at exact independently reviewed source commit/tree
`e72841d2c4553c66f99be9f57efc1cd137fd543d` /
`8fea9db249214a6d633a7d34d2c014fbcd6e816b`.

It does not satisfy catalog instrumentation, integrated automatic-retrieve CLI
wiring, final repository validation, live canary behavior, physical wire-count,
provider billing, cost, or rate-limit claims.

## Limits

Tests were not rerun during records-only closure. Test evidence is the exact
candidate's internally consistent attestation and the supplied independent PASS
review, which also did not rerun the suite. Exact historical command strings and
raw output are unavailable. Local fakes prove Buoy's application-boundary
instrumentation and compatibility behavior, not live SDK/provider behavior,
SDK-internal retries, wire sends, billing, cost, or rate-limit use. Catalog,
integration, and live-canary work remain separately owned and gated.
