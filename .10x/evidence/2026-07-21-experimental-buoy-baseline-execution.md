Status: recorded
Created: 2026-07-21
Updated: 2026-07-21
Relates-To: .10x/tickets/2026-07-20-source-pin-and-execute-experimental-buoy-baseline.md, .10x/specs/experimental-buoy-baseline-executor.md, .10x/evidence/2026-07-20-experimental-buoy-baseline-approval-a-grant.md, .10x/evidence/.storage/2026-07-21-experimental-buoy-baseline-execution.json

# Experimental Buoy Baseline One-Invocation Evidence

## Outcome

A fresh complete Step 2 preflight passed at exact integrated `develop` commit `0e6b97a0897ac7f7a82d073d851709951e0ea29e`. The public `execute_experimental_baseline` entry point was then invoked exactly once, from `2026-07-21T03:09:58.038837+00:00` through `2026-07-21T03:12:38.841410+00:00`, by the implementation subagent in the local macOS worktree. Approval A is now consumed and MUST NOT be invoked again regardless of this abort.

The invocation constructed and loaded the exact offline model, read the provider credential only inside the public executor, and constructed the locked `turbopuffer==2.4.0` client with `max_retries=0`. It made exactly two provider metadata attempts and then failed closed with `ExperimentalBaselineError: catalog namespace distance_metric is missing or mismatched`.

No content or card write was attempted. No delete, retry, pagination, fallback, cleanup, rollback, resume, Approval B, or C3 request occurred.

Complete secret-free structured preflight, raw schema/distance projections, result/error evidence, all 26 normalized slots, billing/`rows_affected` presence markers, counters, local observations, and effect classifications are preserved at `.10x/evidence/.storage/2026-07-21-experimental-buoy-baseline-execution.json`.

## Exact source, grant, plan, cache, and local preflight

All 19 fresh non-credential/non-model checks passed before invocation:

- `HEAD`, local `develop`, and `origin/develop` were the pinned integrated commit `0e6b97a0897ac7f7a82d073d851709951e0ea29e`; tracked source was clean.
- `src/buoy_search/experimental_baseline.py` was exactly 69,834 bytes, Git blob `bce9daf1f7b07b50e5c6bfb34f5e834ff13554d4`, SHA-256 `044c5362618ae07a93ad832a1f7425174faed273d2907f17110210319cbcd450`, and byte-identical to `HEAD`.
- The immutable grant remained exactly 2,627 bytes with SHA-256 `46a44e9440425ef73c66e69d64d7e83a7c098ce0fa3f85f2caf7f8d7685cc5ec`; its 2,206-byte text hash and exact three-field provenance matched the integrated source pins.
- Retained `plan.json`, `manifest.json`, and `chunks.jsonl` bytes/hashes matched the prior authority. Validation reproduced plan `plan_b6c5d128295f442f`, artifact `b6c5d128295f442fcae21472c9bcb037ecb44101ca648115e8f666ba59a6f0ce`, source `Doctacon/buoy-search@fcb7abbe1652d2eab4ee23816b6d992d893603ac`, namespace `github-doctacon-buoy-search-v1`, and exactly 903 unique intended IDs with an empty first-apply/no-stale diff.
- The real cache ref was exact revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`. Its 12 resolved files totaled 267,599,430 bytes and exactly matched the checked-in canonical authority; both canonical authority and production serialization reproduced manifest SHA-256 `5f783ebce23b6ac957d2741399b46e19502b1751acfd3c744b8c41103b138f35`. README SHA-256 was `ddb964361a55c6e5dfca6361615854b260c9c960205d04c7520151aaa1d75837`, with `license: mit` and the pinned Markdown-linked MIT statement recognized.
- `/tmp/buoy-c1-state` was absent, with no pending record, DuckDB state, or lock; local verification was a compatible empty first apply.
- The locked SDK/version, exact region, target/catalog namespace, generated card ID `bc_0a4ee01f946cb0779399000a43d0c146601e87c07740819d0ca83e41149a7`, cosine contract, offline controls, no-delete/no-retry enforcement, exact 26-slot ledger, and complete evidence capacity all passed.

No preflight read the credential, imported or loaded the model, constructed a provider client, made a provider request, or mutated retained local/domain state.

## Complete fixed-slot accounting

- Physical attempts: `2 / 26`.
- Read attempts: `2 / 10`.
- Write attempts: `0 / 16`.
- Attempted write-row positions: `0 / 904`.
- Returned-row positions: `0 / 1,817`.
- Delete attempts: `0`.
- Runtime SDK: `turbopuffer==2.4.0`; `max_retries=0`; provider attestation true.
- Dollar cost: unknown. No dollar price is inferred.

Attempted slots:

1. Slot 1, `target_preflight_metadata`, `github-doctacon-buoy-search-v1`: succeeded. It returned the SDK's unambiguous namespace-absent projection. Returned rows `0`; `rows_affected_present=false`, value `null`; `billing_present=false`, value `null`; metrics/request identity/affected IDs absent; no error.
2. Slot 3, `catalog_preflight_metadata`, `buoy-routing-catalog-v1`: the physical metadata request succeeded and returned schema, but semantic validation aborted because the response had no top-level `distance_metric`. Returned rows `0`; `rows_affected_present=false`, value `null`; `billing_present=false`, value `null`; metrics/request identity/affected IDs absent; no transport/response-shape error.

Unused slots are exactly 2 and 4–26. Each is explicitly represented as `unused` in the structured record with its immutable resource, operation number, kind, requested rows or `top_k`, returned-row ceiling, `rows_affected_present=false`/`null`, `billing_present=false`/`null`, returned rows `0`, absent metrics/request identity/affected IDs/error, and zero unused-slot cumulative counters. Unused capacity was not reassigned.

The raw catalog projection proves that the returned schema's vector `ann.distance_metric` was `cosine_distance`, but the required top-level `distance_metric` marker was absent. The exact sanitized projection hashes are:

- target preflight: `2f41ab62d15091aea29f841802917ff829aa273da15b0db8c5c073b30f1f36ab`;
- catalog preflight: `5073fd4dcbf9fce0c9337d8c2fb34722cfb7731bfe33b93823108435b07d8ccc`.

No target-row or card-row projection exists because the corresponding fixed slots were unused.

## Known and indeterminate effects

- Target namespace: slot 1 observed it unambiguously absent at that time; slot 2 was correctly unused; no target write or delete was attempted.
- Catalog namespace/card: slot 3 observed the catalog schema and missing top-level distance marker. The exact generated card itself was not read because slots 4 and 5 were not reached. Slot 24 was unused, so no card mutation was attempted; slots 25 and 26 were unused.
- Pending: known absent after invocation. No pending record was created.
- DuckDB applied state: known absent after invocation. No local applied-state commit was attempted and no applied-state hash exists.
- Lock/state root: lock acquisition created the exact local state-root/lock-file path. The executor's lock context exited; the persistent `apply.lock` file remains. Lock ownership was not retested and the file was not deleted because cleanup is forbidden.
- Remote mutation: none attributable to this invocation because there were zero write and zero delete attempts. Provider state after the two metadata observations was not re-read, as extra evidence requests are forbidden.
- Local/remote cleanup, rollback, retry, resume, second invocation, and another namespace/card operation: none.

## Procedure

1. Ran repository-required status/worktree checks and provisioned the exact locked Python 3.11 environment without model or credential activity.
2. Ran the complete 19-check preflight using standard-library/project validators and read-only retained inputs. The preflight passed with no stop reason.
3. Reconfirmed the clean exact source/develop pins.
4. Invoked the public live entry point exactly once with only the immutable Approval A record, retained plan, real immutable cache, and exact local state-root paths.
5. Caught the fail-closed error and immediately persisted its attached executor evidence, complete 26-slot accounting, and local-only pending/DuckDB observations. No extra provider request was made.
6. Performed record-only secret scanning, accounting validation, and diff validation. The live entry point was not and will not be invoked again under Approval A.

## What this supports

This supports that Approval A was consumed by exactly one bounded invocation and that the executor failed closed after two metadata reads with no remote or durable applied-state mutation. It supports the exact catalog metadata compatibility blocker and complete bounded accounting for independent review.

It does not establish a compatible Buoy baseline, grant Approval B, authorize another baseline attempt, or unblock C3.

## Limits

Provider/account dollar pricing remains unknown. The exact generated card and target rows were not observed because their fixed slots were unused. No post-abort provider observation is available or permitted. Independent review remains required; the owning ticket stays active and C3 remains blocked.
