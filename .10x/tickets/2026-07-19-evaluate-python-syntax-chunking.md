Status: blocked
Created: 2026-07-19
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/2026-07-19-implement-opt-in-python-syntax-chunking.md

# C6: Evaluate Python Syntax Chunking

## Scope

After C5 has an active ratified spec, passing local implementation/tests, and exact paired plan counts, evaluate only the specified fixed/breadcrumb/syntax arms on Buoy, pytest, and Ruff. Use new namespaces, identical source commits/corpora per comparison, and zero deletes.

## Acceptance criteria

- C5 is complete and exact per-arm namespace names, commits, row counts, storage multipliers, and write counts are reported before approval.
- Every apply targets a new namespace; no stale or namespace delete occurs; baseline namespaces, catalog, defaults, and local applied state outside the new namespaces remain unchanged.
- Live eval after approved applies is retrieval-only.
- Primary metrics match C4. Also report chunk-count multiplier, mean/p95 chunk tokens, symbol-boundary coverage, and fallback rate by language.
- The three-repo no-regression/positive-average/two-improving-repo rule is only an experiment escalation gate. Stop an arm at the pilot if it fails that gate, exceeds an approved chunk/storage bound, or gains only from the already-completed global metadata preamble. Passing permits only a request for separately approved full-basket experimentation; it is not promotion authority.
- Full-basket expansion requires a separate exact ten-repo forecast and approval; only the full-basket keep gate is governed by the active distribution policy.
- Passing means promotion-candidate evidence only; fixed-line behavior remains the default.

## Approval gate

Blocked until C5 local plans can fill this exact checkpoint:

> Approve up to `<rows>/<new namespaces>/<estimated writes and storage multiplier>` for the ratified Buoy/pytest/Ruff syntax arms, with zero deletes and no catalog/default change?

Past namespace approvals do not authorize these writes. Approval covers only the exact planned commits/arms/counts.

## Stop conditions

- Stop before any live operation without exact approval.
- Stop on commit/corpus mismatch, unapproved/exceeded rows or storage, a failed pilot gate, fallback/coverage behavior that violates the active spec, or any need to delete/mutate a baseline namespace.
- Do not add Tree-sitter unless the Python experiment first passes and a later multilingual need is explicitly ratified.
- Stop before full expansion until its exact incremental forecast is separately approved.

## Evidence expectations

Approval provenance; paired plan/apply summaries; exact writes/deletes; per-arm metrics/resources/fallbacks; retrieval-only proof; review; explicit no-promotion conclusion.

## Blockers

- C5 and its governing active spec do not exist in executable/completed form.
- No exact syntax namespace-write approval exists.

## Explicit exclusions

Source implementation; behavior shaping; Tree-sitter; baseline mutation/deletion; catalog/default changes; automatic promotion.

## References

- `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`
- `.10x/tickets/2026-07-19-implement-opt-in-python-syntax-chunking.md`
- `.10x/decisions/repo-ranking-promotion-policy.md`

## Progress and notes

- 2026-07-19: Opened blocked. No namespace names/counts, write budget, live call, or promotion was ratified.
- 2026-07-20: Clarified that the three-repo rule is an experiment escalation gate only, not active promotion policy.
