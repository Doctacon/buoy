Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/done/2026-08-24-implement-private-provider-invocation-receipt-core.md, .10x/specs/provider-client-invocation-accounting.md, .10x/specs/provider-client-invocation-receipt.md, .10x/reviews/2026-08-24-provider-invocation-receipt-core-review.md

# Provider Invocation Receipt Core Closure Evidence

## What was observed

The independently reviewed source target is exact commit
`8953e9336354f2a2e0604a54be9cd882a97a7985`, tree
`66fb2d0dcca5d397132f60eb0be6d22a5b69479b`.

The reviewed implementation lineage is:

1. `cd964738dbd16eb729245fd678d94055c7b43729` implemented the private core;
2. `08af92e943b6e5d52f3446a3d5dc407d379538dc` repaired observer fault isolation;
3. `8953e9336354f2a2e0604a54be9cd882a97a7985` repaired exact no-op observer keyword-signature parity.

Relative to the separately committed activation state
`94e41fa30291017958f38f1963da26851a19c880`, that lineage adds only:

- `src/buoy_search/_provider_invocation_receipt.py`;
- `tests/test_provider_invocation_receipt_core.py`; and
- append-only progress in the owning core ticket.

The implementation-lineage diff is 2,268 insertions across those three paths:
1,192 lines in the private module, 1,039 lines in its focused tests, and 37
progress lines. No package initializer, CLI, dependency, lockfile, telemetry,
store, provider call site, routing artifact, or other production path changed.

At the reviewed target, the relevant Git blobs and SHA-256 values are:

| Path | Git blob | SHA-256 |
| --- | --- | --- |
| `src/buoy_search/_provider_invocation_receipt.py` | `e5fa2eb6b028347d9f816ffd4c0775a0cf7b9191` | `ba7fb4aaf4a8437b3755052ed117a089215998355d4ca8d5a2b1fdd1691029c6` |
| `tests/test_provider_invocation_receipt_core.py` | `73b8a10340479044c3b7479f76a8c2a85a4674ce` | `8645265455da03423286fa3e77cf18757e3cd80d195b2f88aa2e37ee367c15bc` |
| `src/buoy_search/__init__.py` | `017662a5839d76632901e60a6f9b1fc68a3f17e1` | `2e73f77e75d1e9bb0f9be953e9c9846f3d4eac9ede3294573df0348b1630c3e6` |

The private module and focused test bytes are the reviewed source/test bytes.
This closure changes records only and preserves those blobs.

## Attested implementation validation

The owning ticket's append-only implementation notes attest the following
credential-removed, telemetry-disabled, offline validation:

- initial candidate: all 40 focused tests passed on Python 3.11 and Python 3.13;
- fault-isolation repair: all 45 focused tests passed on Python 3.11 and Python
  3.13, with 44 private definitions, standard-library-only imports, unchanged
  package/CLI/telemetry boundaries, and current-`develop` ancestry;
- final signature repair: the two constructor-fault regressions passed, all 45
  focused tests passed on Python 3.11, all 45 passed on Python 3.13, exact
  signature/private-module static inspection passed, and both frozen-contract
  validators passed.

The final implementation handoff characterized this as an eight-command
validation suite. The exact shell strings and raw console transcript were not
embedded in the implementation commits, so this evidence does not reconstruct
or overstate them. The independent PASS review inspected all 45 test methods
and accepted the reported results while explicitly recording that it did not
rerun the suite.

No provider, model, network, credential, content, catalog, store, telemetry,
persistence, routing, canary, or provider-free latency-probe operation ran in
that validation. This records-only closure did not rerun tests, as directed.

## Core acceptance-criterion mapping

1. **Default-off and activation faults — supported.** Source lines 471-537
   isolate scope/handle construction and active-ledger lookup faults with
   disabled/null behavior. Focused tests at lines 106-116 and 325-404 cover
   default-off behavior, activation/context faults, governed lookup faults,
   nested read-fault isolation, and handle construction while preserving body
   result and exception identity.
2. **Empty, post-exit, nested lifecycle — supported.** Tests at lines 118-166
   prove pre-exit null, repeatable canonical zero receipt after exit, nested
   null with outer authority, body-exception identity, and independent
   contexts. Source sealing at lines 398-434 rejects unhealthy, in-flight,
   leased, or incomplete state before immutable model validation.
3. **Context, worker, lease, late-use, no-wait, and synchronization behavior —
   supported.** Tests at lines 154-324 and 406-444 cover isolated contexts,
   explicit worker binding/restoration, in-flight and never-run leases,
   unpropagated workers, late capability use, worker/lock/serialization faults,
   and no-wait null-on-incomplete behavior.
4. **Exact model and canonical validation — supported.** Tests at lines
   594-692 and 927-1017 cover content grammar, route/attempt order and bounds,
   immutable exact-key models, strict duplicate rejection, UTF-8, non-finite
   values, canonical key order/encoding, byte limit, round-trip identity,
   generic non-echoing errors, and privacy sentinels. Source lines 1142-1192
   perform strict encode/decode/revalidate/re-encode handling.
5. **Exhaustive catalog boundaries and source order — supported.** Tests at
   lines 695-824 cover successful and terminal per-category boundaries,
   adjacent overflow, all source-order prerequisites, local terminal stages,
   ambiguous L1 10,001 rejection, exact 40,002 terminal composition, and total
   overflow. Source lines 927-1051 enforce those aggregate invariants.
6. **Cancellation/control-flow precedence and identity — supported.** Source
   lines 791-806 checks both cancellation classes before generic `Exception`,
   then treats every other non-`Exception` `BaseException` as interrupted.
   Tests at lines 534-589 cover both cancellation classes,
   `KeyboardInterrupt`, `SystemExit`, `GeneratorExit`, a custom
   non-`Exception` `BaseException`, representative remaining exceptions, exact
   sanitized outcomes, and identical-object re-raise.
7. **Private live catalog capability and fault isolation — supported.** Tests
   at lines 312-324 and 825-924 prove the capability is available only from a
   live handle, explicit-use-only, unusable after sealing, and null on catalog
   callback/constructor faults while preserving callback execution exactly once,
   return identity, and exception identity. Content fallback parity and the
   same constructor-fault guarantees are covered at lines 447-499. Source
   signatures at lines 543-573 and 647-712 match normal and no-op observers,
   including `request_form`, `trigger`, `category`, and `callback`.
8. **No widened integration or side effects — supported.** The module is
   underscore-private, declares empty `__all__`, and imports only the Python
   standard library. `src/buoy_search/__init__.py` is unchanged. Test lines
   1019-1035 inspect package export, trigger, dependency, and persistence
   boundaries. The exact implementation-lineage diff contains no CLI,
   environment, filesystem, database, provider, network, telemetry, package-
   public, dependency, or lockfile change.

## Active-spec coherence

The behavior bodies of
`.10x/specs/provider-client-invocation-accounting.md` and
`.10x/specs/provider-client-invocation-receipt.md` are unchanged from the
independently accepted contract. The only later spec diff adds `Prior-Review`
and updates `Review` metadata to preserve the historical FAIL and governing
PASS contract reviews.

The final independent source review compared the exact reviewed source/tree to
both active specifications and found the implementation consistent: lifecycle,
content grammar, catalog aggregate state machine, canonicalization, privacy,
fault isolation, and private/default-off integration boundaries match. No spec
scenario is narrowed or contradicted by the reviewed core.

## Procedure

Closure inspection used only read-only Git/status/diff/tree/hash/search
commands. It confirmed:

- clean reviewed worktree before closure mutation;
- exact HEAD and tree;
- exact implementation lineage and changed paths;
- `develop@dd0e155d26af6b0cfbc9872606c5861e0d3b4306` is an ancestor;
- 45 focused test methods are present;
- no implementation-lineage diff in `src/buoy_search/__init__.py`,
  `src/buoy_search/cli.py`, `pyproject.toml`, or `uv.lock`; and
- spec behavior has no drift from the accepted contract.

## What this supports

This evidence supports closing only the private provider invocation receipt core
at the exact independently reviewed source commit/tree. It satisfies no content
or catalog call-site instrumentation, integrated CLI wiring, live canary,
physical wire-count, provider billing, cost, or rate-limit claim.

## Limits

Tests were not rerun during records-only closure. The evidence relies on the
committed implementation attestations and the supplied independent PASS review
of exact commit `8953e933...`, which inspected all 45 test methods but likewise
did not rerun the attested suite. Exact historical command strings/raw output
were not retained in the implementation commits. Downstream content, catalog,
integration, and live-canary work remain separately owned and gated.
