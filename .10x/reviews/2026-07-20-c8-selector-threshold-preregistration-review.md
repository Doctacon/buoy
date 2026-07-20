Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Target: PR #62 pre-registration commit b9780495adfbc8ebee37be9a92525cbd4a0e9511
Verdict: pass

# C8 Selector Threshold Pre-registration Review

## Target

The C8 oracle-gap comparison definitions, aggregate formula, denominator and boundary handling, materially-closed and stop gates, and disposition pre-registered in `.10x/tickets/2026-07-19-reproduce-and-generalize-routed-profile-selection.md` at PR #62 commit `b9780495adfbc8ebee37be9a92525cbd4a0e9511`.

This review concerns only the pre-registered contract. It does not review a C3 cache, selector implementation, score, result, or product surface because none exists in this change.

## Findings

- The authority uses an equal-weight 13-repository macro comparison and aggregates gains before taking the oracle-gap ratio. It does not silently drop zero-gain repositories, substitute a per-repository ratio, or case-weight the result.
- The safe oracle and selector use the same finite action set, include the current default as the no-op action, preserve score and Precision@5 no-regression bounds, and define deterministic tolerance and tie behavior.
- `oracle_gap_closure = G_selector / G_oracle = 1 - G_remaining / G_oracle` follows from the defined repository gains. The `G_oracle <= 1e-12` branch is explicitly undefined/no-action rather than treating `0/0` as success, and the ratio is not clipped.
- The exact inclusive minimum is 50%: `G_selector + 1e-12 >= 0.50 * G_oracle`. It is conjunctive with per-repository score/Precision@5 safety, the active full-basket distribution policy, zero false-positive routing, and protocol-integrity gates.
- Held-out labels are limited to the post-hoc oracle upper bound. Repository/namespace identity, held-out cases or labels, candidates, derived aggregates, and fold-local outcome information are forbidden selector inputs. The historical static portfolio is not represented as held-out generalization.
- Passing produces experiment-only promotion-candidate evidence. Failure produces explicit no action. Neither result authorizes scoring before C3, a benchmark lookup table, source/default/catalog/namespace mutation, a product selector, or C9 productization.

No blockers were found in the pre-registered formula or gates.

## Verdict

PASS. The proposal is precise enough for explicit ratification without changing its formula, thresholds, boundaries, stop gates, or disposition. Ratification may remove only C8's threshold blocker; it cannot make C8 executable while C3/cache and pre-scoring protocol prerequisites remain unsatisfied.

## Residual risk

- C3 is blocked and no immutable shared cache/hash is available, so none of the threshold contract has been scored or empirically validated.
- Buoy baseline compatibility, complete-basket sufficiency, current-default replay, reconstructed action-set identity, selector inputs/rule, folds, seed, fallback, tie-breaking, and leakage checks remain prerequisites.
- The review does not authorize C8 execution, retrieval, source/tests implementation, live operations, writes, default/catalog changes, or C9 productization.
