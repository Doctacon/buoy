Status: recorded
Created: 2026-08-23
Updated: 2026-08-23
Target: cb56b0afa38883fb22b0227c9e17e3a39c770814
Verdict: fail

# Retrieve Command Telemetry Source-Reachability Rereview

## Target and method

A fresh read-only reviewer inspected exact candidate
`cb56b0afa38883fb22b0227c9e17e3a39c770814`, including implementation repairs
`814a2d3a` and `cb56b0af`, against the prior source-reachability review, active
specifications, CLI/retriever/envelope/writer source, and focused tests. The
review attempted both accepted-but-source-impossible and
rejected-but-source-truthful graphs. Package and dual-runtime attestation were
intentionally deferred until this source-only gate passed.

## Finding

### High — a final automatic assessment may still precede reranking

`src/buoy_search/telemetry_envelope.py:2313-2326` allows an evidence span before
rerank after the initial namespace set has completed. The phase-specific
constraints at `src/buoy_search/telemetry_envelope.py:2356-2379` distinguish
only weak-top-one widening.

Starting from `_automatic_partial_v2_object()`, moving its sole evidence span
after both namespaces but before rerank produces an accepted graph. Production
cannot emit that order when initial fanout exceeds one: the optional initial
assessment occurs only for `requested_fanout == 1` with more than one selected
target, while otherwise the sole final assessment occurs after rerank. The same
gap permits pre-rerank final evidence for `empty_top1` and `failed_top1`
widening, whose only assessment is post-rerank.

The bounded repair must distinguish the one truthful non-weak initial-
assessment shape from final assessment:

- weak-top-one first evidence remains after initial namespaces and before added
  namespaces; its second evidence remains after rerank;
- a non-weak pre-rerank assessment is valid only for the initial one-target
  attempt that did not widen, while a later reached rerank may still fail;
- successful/partial automatic paths with larger initial fanout and
  empty/failed widening require their sole assessment after successful rerank;
- automatic error paths retain zero or source-reached evidence, initialized
  summaries, and terminal-error behavior; and
- successful evidence remains `UNSET` or `OK`.

Add positive non-weak initial-assessment coverage and adversarial decoder plus
writer-before-database coverage for a final assessment moved before rerank.

## Previously reviewed findings

The reviewer accepted the following as closed at this target:

- automatic success/partial requires exactly one evidence span, or exactly two
  for weak-top-one widening;
- successful catalog cannot stop before the second routing-model stage;
- successful second routing model cannot stop before selection;
- evidence cannot overlap its consumed initial namespace result;
- weak evidence cannot overlap the added namespace batch, including truthful
  weak-widening error prefixes; and
- early zero-routing errors, reached-evidence errors, evidence `UNSET`/`OK`,
  initialized error summaries, command/render behavior, and writer-before-
  database rejection remain preserved.

Parent focused validation at `cb56b0af` observed 66 passed tests and 182 passed
subtests, plus lock, compilation, Ruff `F,E9`, ranking, and diff success. Those
results do not override the adversarial ordering finding.

## Verdict

FAIL. Repair only the final-versus-initial evidence phase distinction, then run
a fresh source-only review before dual-runtime and exact-package acceptance.

## Residual risk

This review was static and local. It made no provider, catalog, content,
credential, model, collector, real telemetry-home, installed-tool, remote,
integration, release, or publication operation.
