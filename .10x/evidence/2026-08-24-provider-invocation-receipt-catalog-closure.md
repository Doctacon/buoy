Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/done/2026-08-24-instrument-catalog-provider-invocations.md, .10x/specs/provider-client-invocation-accounting.md, .10x/specs/provider-client-invocation-receipt.md, .10x/reviews/2026-08-24-provider-invocation-receipt-catalog-review.md

# Provider Invocation Receipt Catalog Closure Evidence

## What was observed

The independently reviewed source target is exact commit
`d9399e86e121e00f403f5f3a1d674f70c2d75aa4`, tree
`1359284ad942224c6873ca810f7de93fd188ad9c`.

Relative to the separately committed catalog activation state
`62b1d3c2f8e33a6de21a53c05aadcee9856fe567`, tree
`47b12dbd637df8e98224f9cdce5f677f77754687`, the reviewed candidate changes
exactly four paths:

- 32 insertions and 7 deletions of append-only progress/blocker state in the
  owning catalog ticket, now
  `.10x/tickets/done/2026-08-24-instrument-catalog-provider-invocations.md`;
- 7 insertions and 3 deletions in
  `src/buoy_search/_provider_invocation_receipt.py` for the authorized
  transformed-cancellation classification repair;
- 203 insertions and 46 deletions in `src/buoy_search/remote_catalog.py` for the
  explicit private operation capability and exact SDK-expression observation;
  and
- the new 868-line, 12-test
  `tests/test_provider_invocation_receipt_catalog.py`.

The focused implementation diff is 1,110 insertions and 56 deletions. It does
not change `src/buoy_search/__init__.py`, `src/buoy_search/cli.py`,
`src/buoy_search/apply.py`, `src/buoy_search/catalog_cli.py`, `pyproject.toml`,
or `uv.lock`. At the reviewed target, relevant Git blobs and SHA-256 values are:

| Path | Git blob | SHA-256 |
| --- | --- | --- |
| `src/buoy_search/_provider_invocation_receipt.py` | `f8ccd188717ab6194f19e1a85ac0fef6165d77c9` | `c9eef051f6f35ac5e839d3066b6b6f1acdee7753105b4a1938d0c42846dfa09f` |
| `src/buoy_search/remote_catalog.py` | `8ec5b5e528407b00d37aab8a4c7e6636b392f9f4` | `3d859a21c257f7edaf113593aa486defdc78d1c89d45367811d0ac9ce991399d` |
| `tests/test_provider_invocation_receipt_catalog.py` | `333925b126a91df4433be8638a7527ee32b135f2` | `6468d107d2774741d1d16e49971d5ad86ad1527d5598d4d2a53cf176227fbe8c` |
| `tests/test_provider_invocation_receipt_core.py` | `73b8a10340479044c3b7479f76a8c2a85a4674ce` | `8645265455da03423286fa3e77cf18757e3cd80d195b2f88aa2e37ee367c15bc` |
| `tests/test_provider_invocation_receipt_content.py` | `fc304b4d56e51ae5d7b755b7ed0d2e614d11d3d8` | `98bddbcf973ebc06bec427c34f9e6797efb16165ca118215f776c9bffc968e6a` |
| `src/buoy_search/__init__.py` | `017662a5839d76632901e60a6f9b1fc68a3f17e1` | `2e73f77e75d1e9bb0f9be953e9c9846f3d4eac9ede3294573df0348b1630c3e6` |
| `src/buoy_search/cli.py` | `d20e16fecd731af8fbfe2ce4b3e0a36a7703b820` | `90e7b2ddf7bbde2daaf0ccd78aa2a779d9e61946a8b7f7ae8f3512dec431ebf9` |

This closure changes records only and preserves all reviewed source/test blobs.

## Attested implementation validation

The owning ticket's append-only implementation notes attest the following
credential-removed, telemetry-independent, strict-offline results:

- remote-catalog plus core/content/catalog receipt tests passed 130/130 on
  Python 3.13;
- the same 130/130 tests passed on Python 3.11;
- exact AST/default/caller/source-order static checks passed;
- both frozen-contract validators passed;
- `git diff --check` passed; and
- generated-version and isolated-environment artifacts were removed.

The count is internally consistent with 45 core, 23 content, and 12 catalog
test methods plus the included remote-catalog tests. The supplied independent
PASS review inspected the implementation, focused tests, static containment,
and this attestation but did not rerun validation. Exact historical shell
strings and raw console output were not retained in the implementation commit,
so this evidence does not reconstruct or overstate them.

Tests used local fakes. No provider, network, credential, model, catalog/content
operation, store, telemetry, database, persistence, canary, CLI wiring, routing,
release, or global-tool operation ran. This records-only closure did not rerun
tests, as directed.

## Acceptance-criterion mapping

1. **Minimum complete read — supported.** `read_remote_catalog` carries the
   explicit operation observer through exact L1, metadata, C1, C2, and L2 order
   at `src/buoy_search/remote_catalog.py:683-737`. The focused test at
   `tests/test_provider_invocation_receipt_catalog.py:322-366` proves five
   successful invocations: two namespace-list pages, one metadata call, and two
   card-query pages. It also proves the exact SDK arguments, strong consistency,
   source order, resource-acquisition exclusion, and resulting read metrics.
2. **Multipage aggregate-only accounting — supported.** The multipage test at
   lines 368-405 proves exact list/card totals across both passes, continuation
   observation, pass order, card filters, and unchanged output. Helpers default
   to `None`, and initial `namespaces`, each reached `get_next_page`, metadata,
   and each reached card query are wrapped at source lines 1056-1180. The model
   retains only fixed category/outcome totals, not pass or response detail.
3. **Category bounds and ordered aggregate impossibilities — supported.**
   Source validation at
   `src/buoy_search/_provider_invocation_receipt.py:951-1058` enforces successful
   and terminal category maxima, terminal prerequisites, mixed/later-stage
   rejection, and local terminal stages. Catalog table tests at lines 407-463
   cover adjacent overflow, missing prerequisites, terminal evidence, and
   impossible pass decompositions.
4. **40,001/40,002 total boundaries — supported.** The focused catalog test at
   lines 465-495 proves a successful 40,001 aggregate, exact all-success 40,002
   terminal composition, successful-40,002 rejection, every other represented
   40,002 composition rejection, and higher-bound rejection. Reviewed core
   tests at `tests/test_provider_invocation_receipt_core.py:695-824` additionally
   cover exact terminal L2 invocation and all-success terminal forms.
5. **SDK/local terminal outcomes and transformed cancellation — supported.**
   Exact SDK expressions count once and stop; post-return processing and page-
   bound failures change only the operation outcome. Tests at catalog lines
   497-699 cover both cancellation classes, named/custom control flow, ordinary
   errors, metadata termination, post-return failures, and list/card page
   bounds. The bounded repair at
   `src/buoy_search/_provider_invocation_receipt.py:683-695` prefers an already
   recorded interrupted catalog invocation only for exceptional operation
   completion. The regression at catalog lines 497-602 proves unchanged
   caller-visible `RemoteCatalogError` type/message for transformed
   `concurrent.futures.CancelledError`, authoritative interrupted receipt, one
   invocation, and ordinary-error preservation. This is the separately approved
   core defect allowed by the ticket's exclusion boundary; no broader outer-
   exception classification changed.
6. **Excluded calls count zero — supported.** Production observation wraps only
   initial/continuation namespace listing, metadata, and card query expressions.
   Client construction, `client.namespace(...)`, normalization, eligibility,
   management, and mutation remain outside the wrappers. The minimum and error
   tests prove resource acquisition and post-return work do not fabricate
   invocation counts.
7. **Default-off, caller containment, and observer-fault equivalence —
   supported.** `read_remote_catalog`, `_list_namespaces`, and `_read_card_pass`
   all default their private observer to `None`. Tests at catalog lines 701-836
   prove an active scope without the argument remains unobserved; apply,
   catalog-management, CLI, and direct/default callers omit the argument; and
   observer enter/invoke/exit faults preserve exact-once evaluation, result or
   exception identity, full read completion, metrics, and null authority.
   `remote_catalog.py` contains neither `_active_ledger` nor `ContextVar`; the
   only production `_catalog_observer` definition remains private in
   `_provider_invocation_receipt.py`.
8. **Local fakes and exact-byte privacy — supported.** All focused tests use
   local fake clients/resources/pages. Catalog test lines 838-864 assert the
   exact fixed catalog keys and exclude credential, namespace, card, cursor,
   response, billing, provider, error, and path sentinels from canonical bytes.
   No pass, stage, identifier, payload, billing, URL, error, or timing detail is
   stored.
9. **Scope and exclusions — supported.** Exact changed-path and caller
   inspection proves no package-public export, automatic CLI/env activation,
   telemetry, persistence, routing, pagination semantics, provider/model/store,
   catalog-management, dependency, or lockfile widening. Automatic-retrieve CLI
   wiring remains owned by the integration ticket.

## Active-spec coherence

The behavioral bodies of
`.10x/specs/provider-client-invocation-accounting.md` and
`.10x/specs/provider-client-invocation-receipt.md` are unchanged from the
independently accepted contract at
`cb4a76b97f68fcdfc2816c49c33b5b23e9b5f899`. The only later spec diff adds
`Prior-Review` and updates `Review` metadata so the historical contract FAIL and
governing PASS both remain visible.

The exact explicit observer boundary, L1 -> metadata -> C1 -> C2 -> L2 order,
per-category and total aggregate validation, interruption precedence, private
default-off lifecycle, privacy, and observer-failure isolation in both active
specifications match the reviewed source and tests. The transformed-
cancellation repair implements the accounting rule that an interrupted SDK
invocation makes catalog operation accounting interrupted while preserving the
lifecycle specification's external exception-isolation requirement. No active
scenario is narrowed or contradicted.

## Procedure

Closure inspection used read-only Git/status/log/diff/tree/blob/hash/search and
file-reading commands. It confirmed:

- a clean reviewed worktree before closure mutation;
- exact reviewed HEAD and tree;
- current `develop` is an ancestor of the reviewed candidate;
- the exact activation-to-candidate changed paths and statistics;
- 12 catalog, 45 core, and 23 content focused test methods at the target;
- unchanged package initializer, CLI, apply, catalog-management, dependency,
  and lockfile boundaries;
- no ambient catalog observer discovery;
- spec behavior drift is limited to review-metadata preservation; and
- all active `.10x` references affected by the catalog ticket move are repaired
  by this closure.

No test, provider, model, network, store, credential, canary, telemetry,
database, persistence, catalog/content, routing, release, or installed-tool
operation ran during closure.

## What this supports

This evidence supports closing only catalog provider invocation instrumentation
at exact independently reviewed source commit/tree
`d9399e86e121e00f403f5f3a1d674f70c2d75aa4` /
`1359284ad942224c6873ca810f7de93fd188ad9c`.

It does not satisfy integrated automatic-retrieve CLI wiring, final repository
validation, live canary behavior, physical wire count, provider billing, cost,
or rate-limit claims.

## Limits

Tests were not rerun during records-only closure. Test evidence is the exact
candidate's internally consistent attestation and the supplied independent PASS
review, which also did not rerun validation. Exact historical command strings
and raw output are unavailable. Local fakes prove Buoy's application-boundary
instrumentation and compatibility behavior, not live SDK/provider behavior,
SDK-internal retries, physical wire sends, billing, cost, or rate-limit use.
Integration and live-canary work remain separately owned and gated.
