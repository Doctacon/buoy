Status: recorded
Created: 2026-08-28
Updated: 2026-08-28
Target: .10x/tickets/done/2026-08-28-implement-retrieve-inference-observation-v3.md
Verdict: pass

# Retrieve Inference Observation V3 Review

## Target

The in-memory/test-only schema-v3 inference observation milestone implemented under `.10x/specs/retrieve-inference-telemetry-v3.md`. Production command creation/publication intentionally remains v2 until the provider and queue/store children can activate v3 atomically.

## Findings

Initial independent review found concrete P1 gaps in worker lifecycle truth, fallback call timing, fallback-pair graph validation, late policy correction, fresh in-process evidence scoring, fault-isolation coverage, and malformed-pair test specificity. The implementation worker repaired each accepted finding and expanded deterministic tests.

Final fresh-context review inspected the complete diff and found:

- worker `spawned|reused|unknown` changes only at the compatible greeting/contact boundary;
- inference timing wraps actual backend encode/score calls rather than fallback construction;
- immediate fallback pairs must match parent, operation, and item count while later command-latched fallbacks remain valid;
- late worker incompatibility downgrades policy to compatibility in-process;
- fresh in-process evidence scoring is instrumented under evidence assessment and score reuse creates no synthetic request;
- disabled telemetry remains direct and callback-free;
- enabled-versus-faulted worker success/fallback/double-failure matrices preserve calls, warning/output, lifecycle, result identity, and exception identity;
- canonical validation enforces parents, counts, state/outcome, policy, exact attributes, fallback grammar, and the complete prohibited-sentinel matrix; and
- production publication remains v2 as explicitly deferred.

No P0, P1, or P2 issue remained. Final reviewer verdict: pass.

## Parent-observed validation

The parent reran on the reconciled worktree:

```text
git diff --check
uv run --python 3.13 --with pytest pytest -q \
  tests/telemetry/test_retrieve_inference_telemetry_v3.py \
  tests/retrieval/test_embedding_worker.py \
  tests/retrieval/test_automatic_routing.py \
  tests/retrieval/test_multi_namespace_retrieval.py \
  tests/retrieval/test_retrieval_evidence.py
```

Result: `163 passed, 94 subtests passed`; diff check passed.

Candidate evidence also records full Python 3.11 and 3.13 results of `1290 passed, 1369 subtests passed` after the production fixes, followed by identical focused acceptance matrices on both runtimes.

## Verdict

Pass for this bounded milestone. The original broad command-activation criterion is transferred to the dependent store/queue and integration tickets; publishing v3 before a distinct inbox consumer exists would poison inbox-v2 or drop enabled telemetry.

## Residual risk

Provider accounting, inbox-v3, writer/store migration, stable analytical views, and production activation remain owned by the existing downstream tickets. No provider call or real telemetry-store mutation occurred in this milestone.
