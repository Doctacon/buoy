Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/tickets/2026-07-20-source-pin-and-execute-experimental-buoy-baseline.md, .10x/specs/experimental-buoy-baseline-executor.md, .10x/evidence/2026-07-20-experimental-buoy-baseline-approval-a-grant.md, .10x/evidence/.storage/2026-07-20-experimental-buoy-baseline-step-2-preflight.json

# Experimental Buoy Baseline Step 2 Stopped Preflight

## What was observed

The complete non-credential/non-model Step 2 preflight ran in the fresh `work/execute-baseline-approval-a` worktree at exact integrated `develop` commit `8c7750d84ebaf846ae519ccf164f2c7b72c9ec1c`. It found two mandatory stop-condition mismatches. The public `execute_experimental_baseline` entry point was **not invoked**. No credential was read, no model was imported, constructed, loaded, or downloaded, no provider client was constructed, and no provider request or local domain-state mutation occurred. Approval B/C3 was not retrieved or exercised.

Complete structured preflight output is preserved at `.10x/evidence/.storage/2026-07-20-experimental-buoy-baseline-step-2-preflight.json`. It maps all 26 fixed slots as unused with zero physical/read/write/delete attempts, zero write-row and returned-row positions, absent `rows_affected` and billing for every unused slot, and no slot error. Because no client was constructed, runtime `max_retries` is recorded as `not_constructed`; static enforceability of literal zero retries passed.

## Passing pins and preconditions

- The tracked worktree was clean before preflight. `HEAD`, local `develop`, and `origin/develop` were all `8c7750d84ebaf846ae519ccf164f2c7b72c9ec1c`.
- `src/buoy_search/experimental_baseline.py` exactly matched that commit: 64,892 bytes, SHA-256 `aba10de48c31a4dd4c1d39b3210274f073adecc3aceef66eed5d543826463b96`, Git blob `22c9610d19ea4aebb718aaab89f7117d2f5a1325`.
- The grant was exactly 2,627 bytes with SHA-256 `46a44e9440425ef73c66e69d64d7e83a7c098ce0fa3f85f2caf7f8d7685cc5ec`; its 2,206-byte text hash and exact three-field source provenance matched the integrated source pins.
- Retained `/tmp/buoy-c1-current-plan/{plan.json,manifest.json,chunks.jsonl}` byte counts and SHA-256 values matched the checkpoint. Local verification reproduced plan `plan_b6c5d128295f442f`, artifact `b6c5d128295f442fcae21472c9bcb037ecb44101ca648115e8f666ba59a6f0ce`, source `Doctacon/buoy-search@fcb7abbe1652d2eab4ee23816b6d992d893603ac`, exactly 903 unique IDs, and the exact 903-row first-apply/no-stale diff.
- `/tmp/buoy-c1-state` remained absent: no pending record, DuckDB state, or lock existed; verified local state was an empty compatible first apply.
- The locked environment contained `turbopuffer==2.4.0`. Static inspection confirmed literal `max_retries=0`, exact region `gcp-us-central1`, only target `github-doctacon-buoy-search-v1` and catalog `buoy-routing-catalog-v1`, generated card ID `bc_0a4ee01f946cb0779399000a43d0c146601e87c07740819d0ca83e41149a7`, cosine distance, offline controls before preparation, local-only revision loading, no executor delete call, and no retry-loop marker.
- The fixed ledger mapped exactly 26 slots, 10 reads, 16 writes, 15 content batches (`14 × 64 + 1 × 7`), 904 maximum write-row positions, and 1,817 maximum returned-row positions without resource reassignment.
- The planned `.10x/evidence/` and `.10x/evidence/.storage/` destinations existed and were writable.

## Mandatory mismatches and stop

### Immutable cache attestation mismatch

The cache ref still named revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`; 12 resolved files still totaled 267,599,430 bytes; README SHA-256 remained `ddb964361a55c6e5dfca6361615854b260c9c960205d04c7520151aaa1d75837`; and front matter still declared `license: mit`. However:

- the executor's canonical manifest algorithm observed SHA-256 `af97aa621263b66d6740dc188958660addfa533dc1b289deceed9c3edf8d81f5`, not pinned `5f783ebce23b6ac957d2741399b46e19502b1751acfd3c744b8c41103b138f35`;
- the source requires the literal text `FlagEmbedding is licensed under the MIT License`, while the exact pinned README contains `FlagEmbedding is licensed under the [MIT License](...)`, so `license_statement_present` is false under the executor's check.

A direct call to the non-model `validate_model_cache` preflight raised `ExperimentalBaselineError: full model cache manifest hash mismatch`. The ticket requires stopping before invocation on either mismatch; no cache bytes were changed or normalized.

### Complete evidence is not enforceable from the public result

Static inspection found that each fixed-slot `Attempt` retains only `returned_rows` count, not provider-returned target/card row bodies or an immutable returned-row projection. The live success result records aggregate `content_rows_verified` and `card_revision`, but not the required local applied-state hash or observed target/catalog schema and distance. Because the contract prohibits extra provider requests after the executor ledger and the public entry point accepts only the four durable paths, a caller cannot persist the specification's reproducible exact returned-row/schema/distance evidence from this exact reviewed integrated source without widening or modifying the reviewed executor. No such modification or caller injection was attempted.

## Procedure

1. Ran repository-required `git status --short --branch` and `git worktree list`; verified the fresh task branch and exact integrated commit.
2. Provisioned the locked Python 3.11 environment with `uv sync --locked --python 3.11`; this installed `turbopuffer==2.4.0` and did not load a model or read a credential.
3. Computed source, grant, and retained-plan byte counts/hashes and compared worktree source with `git show` at the integrated commit.
4. Used `validate_approval_a_record`, `load_verified_apply_plan`, and `validate_immutable_plan` for non-credential/non-model validation.
5. Hashed the exact cache ref/snapshot/README bytes without importing or loading the model. The direct cache validator failed on the manifest mismatch; a second read-only pass captured all remaining preflight observations rather than invoking live.
6. Inspected local pending/DuckDB/lock paths without creating them, inspected the installed SDK constructor and executor source, mapped all fixed slots, and audited the public evidence shape.
7. Persisted the structured preflight and this record, then stopped.

## What this supports

This supports that Step 2 obeyed its pre-invocation stop conditions and that invocation count remains exactly zero. The Approval A one-invocation authority was not consumed. It also provides the exact blockers that must be independently reviewed and explicitly resolved under a separately authorized source/spec/cache repair path before any future live invocation can be considered.

## Limits

No remote target, catalog schema/card, billing, rows, or account state was observed. Remote state therefore remains unknown, while local pending/DuckDB/card-success effects are known absent because the live entry point was never invoked and `/tmp/buoy-c1-state` remained absent. This evidence does not establish baseline compatibility, grant Approval B, unblock C3, or authorize a later invocation by itself.
