Status: recorded
Created: 2026-07-21
Updated: 2026-07-21
Relates-To: .10x/specs/deterministic-repository-prose-token-budget-compatibility.md, .10x/tickets/done/2026-07-20-shape-prose-token-budget-compatibility.md, .10x/tickets/2026-07-19-evaluate-python-syntax-chunking.md, .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md, .10x/reviews/2026-07-21-prose-token-budget-compatibility-contract-review.md

# Repository-Prose Token-Budget Option A Ratification

## What was observed

PR #78 pre-ratification head `02adbd1cd9fc33dd7f5d52e6c9ef33770f155f74` contains the reviewed focused repository-prose options contract. Independent review recorded PASS with no blocker to selecting exact Option A in `.10x/reviews/2026-07-21-prose-token-budget-compatibility-contract-review.md`.

On 2026-07-21 the user explicitly ratified exact Option A: preserve prose byte-for-byte across ordinary no-arm, explicit `current-default`, `fixed-80-python-breadcrumbs`, and `python-ast`; retain the exact 366 incompatible treatment occurrences as 183 unique parents across 57 paths; perform no split, truncation, omission, compatibility relabeling, or identity/order/count/artifact change; and keep C6 blocked.

The user also explicitly granted no implementation, regeneration, live-operation, namespace-write, or write-approval authority. Options B, C, and D were not selected and remain non-authoritative comparison material.

## Procedure

1. Recorded the independent PASS against PR #78 pre-ratification head `02adbd1cd9fc33dd7f5d52e6c9ef33770f155f74`.
2. Changed `.10x/specs/deterministic-repository-prose-token-budget-compatibility.md` from `draft` to `active` and made selected Option A versus rejected B/C/D authority explicit without changing Option A behavior.
3. Closed and moved the shaping ticket to `.10x/tickets/done/2026-07-20-shape-prose-token-budget-compatibility.md` with acceptance mapping and retrospective.
4. Opened no implementation ticket because exact Option A requires and authorizes no implementation.
5. Reconciled C6 and its parent to the terminal shaping path while preserving C6's blocked status and the exact fail-closed incompatibility counts.

## What this supports

This supports treating exact no-action Option A as active prose authority and treating the shaping work as complete. It supports no tokenizer-readiness or C6-readiness claim.

## Safety observation

This ratification turn changed records only. It did not change source or tests, add dependencies, regenerate or mutate any plan, forecast, manifest, chunks JSONL, compact authority, tokenizer report, validator, count, identity, or namespace; construct or run a tokenizer/model; access credentials or providers; retrieve; evaluate; promote; perform a live operation; grant write approval; or write/delete domain state.

## Limits and residual risk

All 366 preserved incompatible treatment occurrences remain fail-closed. C6 remains blocked on those rows and its other existing gates. Any future change from no action would require explicit supersession of the active specification and separately reviewed authority; this ratification carries none forward.
