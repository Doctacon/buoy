Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/specs/experimental-buoy-baseline-executor.md, .10x/reviews/2026-07-20-experimental-buoy-baseline-executor-spec-review.md, .10x/tickets/2026-07-20-implement-experimental-buoy-baseline-executor.md, .10x/tickets/2026-07-19-capture-current-repo-candidates-and-baselines.md

# Experimental Buoy Baseline Executor Ratification

## What was observed

On 2026-07-20 the user explicitly ratified the exact fail-closed baseline executor contract prepared in PR #65 and directed that the reviewed draft be activated unchanged. Independent review passed the draft at commit `539f32c236a6c1179cdcfed958f33e19c75a2579`; the reviewed file SHA-256 was `2511b6908727d0e3f5a2f6dfc28885beacd9b0af9abbcc4a0f1d9075634364d6`. Findings are recorded in `.10x/reviews/2026-07-20-experimental-buoy-baseline-executor-spec-review.md`.

Ratification activates `.10x/specs/experimental-buoy-baseline-executor.md` without changing its region, plan/artifact/source/model/cache/license identities; 903-row/15-batch write shape; `max_retries=0`; preflight absence/emptiness/card checks; 26-attempt, 904-write-row-position, and 1,817-returned-row-position ceilings; exact response/accounting requirements; two target and two card post-write verification reads; commit order; zero-delete rule; failure behavior; or evidence contract. Only obsolete draft/authority prose changed to record active status and point to the separately bounded implementation owner.

One executable source/test ticket now owns implementation at `.10x/tickets/2026-07-20-implement-experimental-buoy-baseline-executor.md`. This record turn does not implement or exercise it.

## Approval boundary

Specification ratification and ticket creation grant neither live-operation approval:

- **Approval A — Buoy baseline write:** ungranted. No credential read, model import/load/inference, provider call, namespace/card/catalog/local applied-state mutation, or baseline execution is authorized.
- **Approval B — C3 retrieval capture:** ungranted and remains ineligible until Approval A is separately granted, the independently reviewed executor is run within that approval, and compatible-baseline evidence passes.

C3 remains `blocked`. Implementation completion cannot itself grant Approval A, and baseline success cannot itself grant Approval B.

## Procedure

1. Inspected PR #65's exact draft, C3 ticket, checkpoint evidence, governing C1 records, and current source boundaries.
2. Independently reviewed the draft contract and verified its exact request/write/read arithmetic and fail-closed ordering.
3. Incorporated current `origin/develop` after PR #62 before final record changes.
4. Activated only the reviewed specification authority/status prose; preserved its behavioral contract.
5. Opened one bounded implementation ticket, repaired current C3/parent references, and kept all execution approvals and C3 blocked state explicit.
6. Performed record/reference/diff validation without source/test/model/provider/domain-state activity.

## What this supports

This supports treating the exact PR #65 executor contract as active behavioral authority and beginning only the bounded source/test implementation ticket. It does not support executing the baseline, accessing a credential or model, contacting the provider, mutating any namespace/card/catalog/local applied state, or beginning C3 retrieval.

## Limits and residual risk

No implementation or implementation review exists yet. No provider/account state, response, billing, target/card state, dollar price, or model runtime was observed. The retained `/tmp` plan and local immutable cache remain ephemeral inputs that a later approved executor must revalidate exactly. Approval A and Approval B remain separate explicit user checkpoints.
