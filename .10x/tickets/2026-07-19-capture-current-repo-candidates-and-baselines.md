Status: blocked
Created: 2026-07-19
Updated: 2026-07-21
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-19-freeze-repo-ranking-experiment-contract.md, .10x/tickets/done/2026-07-20-remove-buoy-internal-ranking-judgment.md, .10x/tickets/done/2026-07-20-implement-experimental-buoy-baseline-executor.md, .10x/tickets/2026-07-20-source-pin-and-execute-experimental-buoy-baseline.md

# C3: Capture Current Repo Candidates and Baselines

## Scope

After C1 freezes exact datasets, snapshots, mappings, request accounting, and artifact schema, make one approved retrieval-only pass over all 90 unique composite `repo_key:case_id` identities. Preserve each dataset-local `case_id` and all labels. Capture ANN and BM25 candidate lists separately, compute current-default fused/file-ranked baselines, and freeze one immutable hash-addressed cache for both C7 and C8.

## Acceptance criteria

- C1 is complete and the exact 13-repo namespace/source-commit map, expected request count, and any provider cost exposure are reported before approval.
- One and only one live raw-candidate capture occurs per frozen composite identity; ANN and BM25 lists are exported separately rather than only server-side fused results.
- Cache rows contain `repo_key`, unchanged dataset-local `case_id`, derived composite `repo_key:case_id`, C1's namespace-qualified hit identity, path/content/section fields, ANN/BM25/fused ranks and scores, retrieval options, commit/namespace/model compatibility, and redacted request accounting. Cache keys and joins use the composite identity and never assume local `case_id` is globally unique.
- Current default offline replay matches direct current-default evaluation at deterministic equality or C1's declared tolerance.
- The immutable cache hash and storage location are recorded. C7 and C8 consume this exact cache and MUST NOT issue duplicate retrieval calls.
- No content, namespace, local applied state, catalog, source, tests, datasets, defaults, or labels are mutated.

## Approval gate

The ratified Buoy judgment removal and rehash are complete. C3 remains blocked pending verification of a compatible Buoy baseline and this exact checkpoint with filled values:

> Approve one retrieval-only raw-candidate pass for the 90 frozen composite `repo_key:case_id` identities across `<exact namespace/commit map>`, with separate ANN and BM25 lists, `<predicted request count/cost bound>`, zero writes/deletes/catalog changes, and one immutable cache shared by C7/C8?

Past retrieval or namespace approvals do not authorize this pass.

## Stop conditions

- If separate ANN/BM25 lists cannot be captured, stop; do not substitute fused-only output.
- If default replay does not reproduce direct ordering within C1's tolerance, stop C7/C8 and diagnose without recapturing candidates.
- If the live namespace/commit/model contract differs from C1, stop before calls.
- If actual request/cost exposure would exceed the approved bound, stop without widening approval.

## Evidence expectations

Approval provenance; exact request count; proof that the cache/schema contains all 90 composite identities plus preserved local IDs; cache hash; direct-versus-replay comparison; no-write proof; redaction audit; limits.

## Blockers

- The ratified internal-judgment removal/rehash is complete under `.10x/tickets/done/2026-07-20-remove-buoy-internal-ranking-judgment.md`, and all remaining paths resolve. The exact Approval A source pins independently passed review and integrated at `8c7750d84ebaf846ae519ccf164f2c7b72c9ec1c`; the ratified bounded repair independently passed review and integrated at `0e6b97a0897ac7f7a82d073d851709951e0ea29e`.
- Approval A was irrevocably consumed by exactly one aborted public executor invocation after exactly 2 metadata reads and 0 writes because the executor redundantly required a top-level `distance_metric` while raw provider authority returned `schema.vector.ann.distance_metric=cosine_distance`. It performed no content/card write, established no compatible baseline, and authorizes no retry, resume, cleanup, replacement approval, or second invocation.
- `.10x/tickets/2026-07-20-source-pin-and-execute-experimental-buoy-baseline.md` is blocked, not done. Separate open shaping owner `.10x/tickets/2026-07-21-shape-provider-metadata-interpretation.md` owns provider-metadata interpretation and prerequisites for any possible future operation; it grants neither repair nor operation authority. Approval B remains ungranted and explicitly excluded. C3 stays blocked until a future independently reviewed compatible-baseline outcome exists and Approval B is then separately granted.

## Explicit exclusions

Namespace writes/deletes; candidate re-indexing; source/tests implementation before approval; model downloads; duplicate C7/C8 retrieval; labels/defaults/catalog changes; promotion.

## References

- `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`
- `.10x/tickets/done/2026-07-19-freeze-repo-ranking-experiment-contract.md`
- `.10x/tickets/done/2026-07-20-remove-buoy-internal-ranking-judgment.md`
- `.10x/specs/repo-search-eval-autoresearch.md`
- `.10x/evidence/2026-07-20-c3-buoy-baseline-approval-checkpoint.md`
- `.10x/specs/experimental-buoy-baseline-executor.md`
- `.10x/tickets/done/2026-07-20-implement-experimental-buoy-baseline-executor.md`
- `.10x/evidence/2026-07-20-experimental-buoy-baseline-executor-ratification.md`
- `.10x/reviews/2026-07-20-experimental-buoy-baseline-executor-spec-review.md`
- `.10x/evidence/2026-07-20-experimental-buoy-baseline-approval-a-grant.md`
- `.10x/evidence/.storage/2026-07-20-experimental-buoy-baseline-approval-a.json`
- `.10x/tickets/2026-07-20-source-pin-and-execute-experimental-buoy-baseline.md`
- `.10x/evidence/2026-07-21-experimental-buoy-baseline-execution.md`
- `.10x/evidence/.storage/2026-07-21-experimental-buoy-baseline-execution.json`
- `.10x/reviews/2026-07-21-experimental-buoy-baseline-execution-review.md`
- `.10x/tickets/2026-07-21-shape-provider-metadata-interpretation.md`

## Progress and notes

- 2026-07-19: Opened blocked. No credentials, live calls, cache artifacts, source, or tests were created during decomposition.
- 2026-07-20: Clarified that retrieval and cache identity use all 90 composite `repo_key:case_id` values while preserving dataset-local IDs and labels.
- 2026-07-20: C1 closed with Buoy explicitly insufficient. C3 remains blocked on the separate ratified label-removal/rehash owner, a compatible Buoy baseline, and the exact retrieval-only approval; no call or remote operation was authorized.
- 2026-07-20: The separate judgment-removal/rehash owner closed after independent review at `ac9bb34`; all 369 remaining paths resolve. Buoy still lacks an approved, verified compatible baseline, and the retrieval-only checkpoint remains unapproved, so C3 stays blocked with no call or remote operation.
- 2026-07-20: Prepared the non-mutating split approval package in `.10x/evidence/2026-07-20-c3-buoy-baseline-approval-checkpoint.md`. Read-only cache/source inspection pins the proposed current-default model revision/bytes/contract and observed resource envelope; retained C1 artifacts reproduce `plan_b6c5d128295f442f`, 903 first-apply rows, and the exact namespace/source pin. The record inventories unavoidable apply catalog/local-state effects and bounds C3 at 90 physical two-subquery requests, 180 subqueries, and at most 36,000 candidate-list positions with zero retries; account dollar pricing is not source-derivable. Neither approval was granted, no live/model/domain operation occurred, and C3 remains blocked/non-executable.
- 2026-07-20: Repaired the approval package record-only. The immutable default model/revision is now bound to MIT by its hashed cached README. Draft `.10x/specs/experimental-buoy-baseline-executor.md` fail-closes on an absent/verified-empty target, `max_retries=0`, per-response rows/billing/request accounting, bounded post-write reads, a 26-attempt/904-write-position/1,817-read-position ceiling, zero deletes, and no state/card success on mismatch. Approval B now freezes exact region/model/license/vector/BM25/filter/RRF/default/billing/request values. The draft is unratified with no executable source ticket; neither approval is granted and C3 remains blocked.
- 2026-07-20: The user ratified the independently reviewed executor specification exactly as reviewed. It is now active, and `.10x/tickets/done/2026-07-20-implement-experimental-buoy-baseline-executor.md` was the one executable source/test owner. No implementation or live/model/domain operation occurred in that ratification turn. Approval A and Approval B remained ungranted, Buoy compatibility unverified, and C3 blocked/non-executable.
- 2026-07-20: The bounded executor implementation independently passed review at PR #70 head `f6cd38dba1bc7cf8fbcb542133ca264e6cb3d61c` and its ticket closed. This satisfies only C3's implementation/review prerequisite. Approval A and Approval B remain ungranted, the source-pinned Approval A grant constants remain `None`, no baseline/model/provider/domain-state operation occurred, Buoy compatibility remains unverified, and C3 remains blocked/non-executable.
- 2026-07-20: The user granted the checkpoint's exact Approval A text via `Approve baseline write (Recommended)`. `.10x/evidence/2026-07-20-experimental-buoy-baseline-approval-a-grant.md` records the exact text, actor/timestamp/provenance, immutable JSON bytes, and source-pin hashes. The new bounded sequential owner `.10x/tickets/2026-07-20-source-pin-and-execute-experimental-buoy-baseline.md` must first pin/review/integrate the exact grant and only then invoke live once from reviewed integrated source with complete slot/accounting/partial-state evidence. Current grant constants remain `None`; no credential/model/provider/domain-state operation occurred. Approval B remains ungranted, Buoy compatibility remains unverified, and C3 remains blocked.
- 2026-07-21: Reconciled C3 after PR #77 independent review. The exact source pins and ratified bounded repair are integrated. Approval A was irrevocably consumed by exactly one invocation that aborted after exactly 2 metadata reads and 0 writes; no compatible baseline was established. The execution owner is blocked, separate provider-metadata shaping owner `.10x/tickets/2026-07-21-shape-provider-metadata-interpretation.md` grants neither repair nor operation authority, Approval B remains ungranted, and C3 remains blocked. No implementation, evidence JSON, live operation, or cleanup changed in this reconciliation.
