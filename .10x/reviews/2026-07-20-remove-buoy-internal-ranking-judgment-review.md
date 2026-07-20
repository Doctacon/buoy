Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Target: PR #60 head ac9bb34549a0bc172ad01a60f6d94512b48a9052
Verdict: pass

# Remove Ratified Internal Buoy Ranking Judgment Review

## Target

The seven-file semantic change at PR #60 head `ac9bb34549a0bc172ad01a60f6d94512b48a9052`, compared with its `b63dc76` `develop` base. Later integration of `origin/develop` and closure-only record edits are outside the reviewed semantic target and must remain mechanical.

## Findings

- The Buoy dataset removes exactly the user-ratified grade-1 `.10x/specs/repo-search-eval-autoresearch.md` judgment from case `evals-composite-metrics`. No other dataset judgment, case, question, grade, reason, or metadata changes.
- The matching fixture-only ideal hit is removed so the fixture continues to represent only currently judged relevant paths. No runtime retrieval, ranking, provider, namespace, catalog, model, or default behavior changes.
- The inventory consistently changes Buoy from 33 to 32 judgments, the full basket from 370 to 369, and the Buoy/dataset-bundle/inventory hashes. Every remaining path resolves, but Buoy correctly remains `insufficient` because `github-doctacon-buoy-search-v1` remains `pending_approval` and unverified.
- The validator and focused regression test enforce the new total, exact removed path, complete remaining path membership, pending baseline status, and continued insufficiency. Existing contract checks continue to protect the 13 datasets, 90 composite identities, folds, mappings, hashes, and source-path authority.
- Recorded Python 3.11/3.13 focused and full suites, locked CI-equivalent checks, distributions, diff hygiene, semantic comparison, and exact-head hosted checks passed. The evidence explicitly preserves the no-live-operation boundary.

No blockers found.

## Verdict

PASS. The reviewed seven-file change is the smallest complete implementation of the ratified judgment removal and satisfies the ticket acceptance criteria without widening scope.

## Residual risk

- Buoy is not baseline-ready: the proposed 903-row same-source namespace remains approval-gated, unpopulated/uninspected by this work, and model/corpus compatibility remains unverified.
- C3 remains blocked on Buoy baseline approval/compatibility and the separate exact retrieval-only approval. C7/C8 retain their independent user-ratified threshold gates.
- The seed labels remain assistant-drafted calibration/experiment evidence rather than human-approved product ground truth.
- This review does not authorize merge, namespace/catalog changes, provider or retrieval calls, model loading, downloads, writes, deletes, or promotion.
