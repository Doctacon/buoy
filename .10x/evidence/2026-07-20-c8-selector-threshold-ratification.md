Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/tickets/2026-07-19-reproduce-and-generalize-routed-profile-selection.md, .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md, .10x/reviews/2026-07-20-c8-selector-threshold-preregistration-review.md

# C8 Selector Threshold Ratification

## What was observed

PR #62 commit `b9780495adfbc8ebee37be9a92525cbd4a0e9511` pre-registered one exact C8 contract before a C3 cache or any future selector score existed. It defines:

- the equal-weight 13-repository safe-oracle and held-out-selector comparison;
- aggregate-before-ratio oracle-gap closure with explicit zero-gap handling;
- an inclusive 50% minimum closure threshold;
- per-repository score and Precision@5 no-regression gates;
- the active full-basket distribution policy and zero-false-positive-routing gate;
- leakage, cache/hash, replay, post-freeze-change, incomplete-fold, and formula-reproduction stops; and
- explicit no action on failure and promotion-candidate evidence only on success.

The user explicitly ratified the reviewed PR #62 formula and gates exactly as written on 2026-07-20. The ticket now marks that already committed text as active authority. No formula, threshold, tolerance, boundary, tie rule, fallback, selector-input restriction, gate, or disposition was changed during ratification.

The threshold checkpoint is therefore satisfied and is no longer a C8 blocker. C8 remains `blocked`: C3 is incomplete and has no immutable shared cache/hash, and the complete basket, default replay, action set, selector inputs/rule, folds, seed, fallback, tie-breaking, and leakage prerequisites must still be frozen and validated before selector scoring. C9 remains separately blocked on completed C8 evidence and an explicit product checkpoint.

## Procedure

- Inspected the full C8 ticket and its parent plan on branch `work/shape-selector-thresholds`.
- Reviewed the pre-registration at exact commit `b9780495adfbc8ebee37be9a92525cbd4a0e9511`; findings are recorded in `.10x/reviews/2026-07-20-c8-selector-threshold-preregistration-review.md`.
- Compared the ratification diff with that exact pre-registration and confirmed that only authority/status/provenance prose, blocker state, references, and append-only progress changed. The reviewed comparison definitions, formulas, gates, arithmetic illustration, and disposition remain unchanged.
- Incorporated current `origin/develop` mechanically; it was already an ancestor, so Git reported `Already up to date.`
- Checked diff hygiene and searched active C8/parent text for stale claims that the C8 threshold remains unratified.

## What this supports

This supports treating the exact reviewed C8 threshold contract as ratified authority and removing only its threshold blocker. It also supports keeping C8 blocked without execution and keeping C9 blocked.

## Limits

No C3 cache exists or was read. No formula was executed, selector scored, profile reconstructed, dataset changed, test/source/product code written, model loaded, credential read, provider/retrieval call made, namespace/catalog state inspected or mutated, or default/product behavior changed. This evidence does not establish a passing selector, authorize C8 execution, or authorize C9 productization.
