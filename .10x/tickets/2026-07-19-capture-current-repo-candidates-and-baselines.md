Status: blocked
Created: 2026-07-19
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-19-freeze-repo-ranking-experiment-contract.md, .10x/tickets/done/2026-07-20-remove-buoy-internal-ranking-judgment.md

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

- The ratified internal-judgment removal/rehash is complete under `.10x/tickets/done/2026-07-20-remove-buoy-internal-ranking-judgment.md`, and all remaining paths resolve. Buoy remains `insufficient` because the proposed baseline is still `pending_approval` and its contents/model compatibility are unverified.
- The required retrieval-only approval has not been granted.

## Explicit exclusions

Namespace writes/deletes; candidate re-indexing; source/tests implementation before approval; model downloads; duplicate C7/C8 retrieval; labels/defaults/catalog changes; promotion.

## References

- `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`
- `.10x/tickets/done/2026-07-19-freeze-repo-ranking-experiment-contract.md`
- `.10x/tickets/done/2026-07-20-remove-buoy-internal-ranking-judgment.md`
- `.10x/specs/repo-search-eval-autoresearch.md`

## Progress and notes

- 2026-07-19: Opened blocked. No credentials, live calls, cache artifacts, source, or tests were created during decomposition.
- 2026-07-20: Clarified that retrieval and cache identity use all 90 composite `repo_key:case_id` values while preserving dataset-local IDs and labels.
- 2026-07-20: C1 closed with Buoy explicitly insufficient. C3 remains blocked on the separate ratified label-removal/rehash owner, a compatible Buoy baseline, and the exact retrieval-only approval; no call or remote operation was authorized.
- 2026-07-20: The separate judgment-removal/rehash owner closed after independent review at `ac9bb34`; all 369 remaining paths resolve. Buoy still lacks an approved, verified compatible baseline, and the retrieval-only checkpoint remains unapproved, so C3 stays blocked with no call or remote operation.
