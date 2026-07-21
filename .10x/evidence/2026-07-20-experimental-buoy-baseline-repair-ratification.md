Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/tickets/2026-07-20-source-pin-and-execute-experimental-buoy-baseline.md, .10x/evidence/2026-07-20-experimental-buoy-baseline-step-2-preflight.md, .10x/reviews/2026-07-20-experimental-buoy-baseline-step-2-preflight-review.md, .10x/evidence/2026-07-20-experimental-buoy-baseline-approval-a-grant.md, .10x/specs/experimental-buoy-baseline-executor.md

# Experimental Buoy Baseline Narrow Repair Ratification

## What was ratified

After the mandatory Step 2 preflight stop, the user explicitly directed the record-only finalization of PR #74 and ratified only the narrow implementation repair for the exact three independently reviewed defects in `.10x/reviews/2026-07-20-experimental-buoy-baseline-step-2-preflight-review.md`:

1. make cache validation reproduce the already-approved canonical 12-file manifest pin `5f783ebce23b6ac957d2741399b46e19502b1751acfd3c744b8c41103b138f35` from the unchanged exact cache bytes, without replacing the pin or rewriting/normalizing cache bytes;
2. recognize the MIT statement as it actually appears with a Markdown link in the exact immutable README while still requiring its existing SHA-256 `ddb964361a55c6e5dfca6361615854b260c9c960205d04c7520151aaa1d75837` and `license: mit` front matter;
3. retain in the executor's secret-free public success/error evidence the immutable returned target/card row projections, observed target/catalog schema and distance, and local applied-state hash already established within the fixed executor operation, without adding a provider request, pagination, retry, fallback, or reassigned slot.

The repair may add or update only deterministic no-live tests and the records needed to prove those three corrections. It must independently pass review and CI and integrate through the protected development workflow before a fresh Step 2 preflight. This ratification does not authorize repairing source in PR #74 itself.

## Approval A remains exact, unchanged, and unspent

This is repair ratification, not a new live-operation grant. The existing Approval A at `.10x/evidence/2026-07-20-experimental-buoy-baseline-approval-a-grant.md` remains the sole live authority and remains byte-for-byte unchanged:

- grant record: 2,627 UTF-8 bytes, SHA-256 `46a44e9440425ef73c66e69d64d7e83a7c098ce0fa3f85f2caf7f8d7685cc5ec`;
- Approval A text: 2,206 UTF-8 bytes, SHA-256 `bafc2500292bc8fcfc4aa806873782d43689330c704620f8981684a3796bfa10`;
- source provenance: `{"source_system":"pi","conversation_id":"runtime-id-not-exposed","message_id":"sha256:4b066f19c3331b0074d4548b691b293072a50406df6f0557fcdba8e3d3f25d74"}`.

PR #74 does not change `APPROVAL_A_TEXT`, either Approval A source pin, `CACHE_MANIFEST_HASH`, `README_HASH`, model/revision/region/plan/artifact/source/namespace/card identities, SDK version, `max_retries=0`, the 26-slot/10-read/16-write/904-write-row/1,817-returned-row ceilings, zero-delete rule, commit order, or any ordinary default. Because `execute_experimental_baseline` was not invoked, the existing one-invocation authority remains unspent. The ratified repair must preserve those constants and that authority unchanged; it neither refreshes nor duplicates the grant.

## Procedure and boundary

1. Independently reviewed the checked-in preflight artifacts and current source, producing a PASS for the mandatory stop and three exact defects.
2. Recorded the user's explicit narrow repair ratification and the unchanged/unspent Approval A boundary.
3. Updated only record evidence, review, and active-ticket progress in PR #74.

No source or test was repaired. No constant, grant JSON, dependency, lockfile, plan, cache, credential, model, provider resource, namespace, card, catalog, pending record, or DuckDB applied state was read or changed by this record turn. The executor was not invoked, no provider client was constructed, and no provider request occurred.

## What this supports

This supports a later bounded source/test repair of only the three defects above while preserving the original Approval A. It also supports keeping the owning ticket active rather than closing or invoking it. After protected integration of an independently passing repair, the ticket still requires a fresh complete preflight; any mismatch still stops before invocation.

## Limits

This record does not prove a repair, grant a new or second invocation, authorize immediate execution, establish cache/model/provider/remote compatibility, grant Approval B, perform C3 retrieval, or change a constant. The existing Approval A can be spent only by the one live entry-point invocation already defined by the active ticket after every gate passes.
