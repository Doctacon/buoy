Status: done
Created: 2026-07-20
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-19-freeze-repo-ranking-experiment-contract.md

# Remove Ratified Internal Buoy Ranking Judgment

## Ratified outcome

The user explicitly ratified removal of only this grade-1 judgment from `src/buoy_search/data/buoy_search_repo_search_seed_evals.json`, case `evals-composite-metrics`:

- `repo_path`: `.10x/specs/repo-search-eval-autoresearch.md`
- `grade`: `1`
- reason: `Specifies the intended metric contract and config-only autoresearch scope, but is not runtime implementation.`

The rationale is that the public Buoy corpus intentionally excludes internal `.10x` records. No other case, judgment, grade, reason, or dataset behavior is ratified for change.

## Scope

In a separate implementation change, remove exactly the ratified judgment and regenerate every contract-v1-derived dataset count/hash, inventory payload/hash, evidence statement/table, validator expectation, and focused test expectation affected by that one deletion. Preserve all other dataset content and the frozen source/corpus mapping.

## Acceptance criteria

- Exactly the named grade-1 judgment is removed; all other dataset-local case IDs, questions, judgments, grades, reasons, and metadata remain unchanged.
- Buoy judgment count changes from 33 to 32 and the all-repository total changes from 370 to 369; all dataset, bundle, inventory payload, and whole-file hashes are regenerated consistently rather than hand-waved.
- Path validation resolves every remaining judgment, while Buoy remains explicitly `insufficient` because `github-doctacon-buoy-search-v1` is still `pending_approval` and its remote contents/model compatibility are unverified.
- C3 and dependent comparison work remain blocked until the exact retrieval approval gate and Buoy baseline compatibility requirements are independently satisfied.
- Focused validator tests, full Python 3.11/3.13 suites, CI-equivalent checks, diff hygiene, and independent review pass.
- No namespace, catalog, model, credential, provider, retrieval, or remote state is read or mutated.

## Evidence expectations

A semantic before/after proving only the named judgment changed; regenerated count/hash output; validator and full-suite output on Python 3.11 and 3.13; independent review; explicit confirmation that Buoy remains insufficient and no namespace operation occurred.

## Blockers

None for closure. Buoy baseline approval/compatibility and C3 retrieval approval remain downstream blockers, not unfinished scope in this ticket.

## Explicit exclusions

Any other label edit or review; treating assistant-drafted labels as human ground truth; creating/populating/verifying `github-doctacon-buoy-search-v1`; retrieval or provider calls; namespace/catalog/default changes; unblocking or executing C3+; altering C7/C8 threshold gates.

## References

- `.10x/tickets/done/2026-07-19-freeze-repo-ranking-experiment-contract.md`
- `.10x/evidence/2026-07-20-repo-ranking-experiment-contract-freeze.md`
- `.10x/reviews/2026-07-20-repo-ranking-experiment-contract-freeze-review.md`
- `.10x/specs/repo-search-eval-autoresearch.md`
- `.10x/evidence/2026-07-20-remove-buoy-internal-ranking-judgment.md`
- `.10x/reviews/2026-07-20-remove-buoy-internal-ranking-judgment-review.md`

## Progress and notes

- 2026-07-20: Opened as the separate owner for the user's exact post-review ratification. C1 closure did not edit the dataset, change 370-count/hash artifacts, or imply Buoy sufficiency.
- 2026-07-20: Removed exactly the ratified grade-1 judgment and its stale ideal-fixture hit. Mechanically regenerated the Buoy count/hash (32), all-repository count (369), dataset bundle hash, inventory payload/whole-file hashes, path-membership fields, validator expectation, and focused regression coverage. Semantic comparison proved the revised Buoy JSON equals the prior JSON after only that exact object is removed, while all 12 other datasets remain byte-identical. Every remaining path resolves, but Buoy remains `insufficient` and `pending_approval`; C3+ stays blocked. Python 3.11/3.13 validators, 5 focused tests, 446 full tests, CI-equivalent locked environments, distribution builds, and diff hygiene passed. No namespace, catalog, model, credential, provider, retrieval, or remote domain state was read or mutated. Ticket remains active pending independent review; do not merge or close.
- 2026-07-20: Pushed `work/remove-buoy-ranking-judgment` and opened PR #60 against `develop` for the required independent review. The branch incorporated current `origin/develop` before handoff. Ticket remains active; PR must not be merged before review.
- 2026-07-20: PR #60 hosted Python 3.11, Python 3.13, and distribution-build checks passed. Independent review remains the only ticket gate; no merge or closure occurred.
- 2026-07-20: Independent review passed the seven-file semantic change at PR #60 head `ac9bb34549a0bc172ad01a60f6d94512b48a9052` with no blockers. Incorporated current `origin/develop` `72d1344` and limited reconciliation to record ownership/status/reference updates, preserving completed C2 and dynamic-dimension shaping ownership. Closed this ticket without merging PR #60 or unblocking C3.

## Closure mapping

- Exact removal: the semantic before/after comparison proves only the ratified grade-1 judgment was removed; all 12 other datasets are byte-identical, and the matching fixture-only ideal hit is the only fixture change.
- Counts and hashes: the validator independently reproduces 13 datasets, 90 composite identities, 369 judgments, the regenerated Buoy/dataset-bundle/inventory hashes, and the unchanged source-path bundle hash.
- Path and baseline state: all 369 remaining paths resolve, while Buoy remains `insufficient` and `pending_approval`; no baseline contents or model compatibility were inferred.
- Downstream isolation: C3 remains blocked on Buoy baseline approval/compatibility and exact retrieval-only approval; C7/C8 keep their independent threshold gates; C2 and dynamic-dimension shaping ownership remain unchanged.
- Verification and review: focused/full Python 3.11/3.13 validation, CI-equivalent checks, distribution builds, exact-head hosted CI, diff hygiene, and the independent PASS review support closure.
- Safety: evidence records that no namespace, catalog, model, credential, provider, retrieval, or remote domain operation occurred.

## Retrospective

A ratified label correction must be treated as a contract revision, not as evidence that its source corpus or baseline is usable. Mechanically regenerating every derived hash and retaining an explicit insufficiency state prevents path completeness from silently laundering an unapproved baseline into experiment eligibility. A focused regression asserting both the removed path and continued `pending_approval` state makes that boundary durable.

## Residual

- Buoy remains insufficient until the proposed 903-row same-source baseline is separately approved, populated, and verified for source/model compatibility.
- C3 remains blocked on that baseline and the exact retrieval-only approval; C7/C8 retain separate user-ratified threshold gates.
- The remaining seed labels are assistant-drafted experiment evidence, not human-approved product ground truth.
- PR #60 remains open and must not be merged by this task.
