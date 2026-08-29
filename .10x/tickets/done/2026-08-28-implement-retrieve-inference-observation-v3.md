Status: done
Created: 2026-08-28
Updated: 2026-08-28
Parent: .10x/tickets/done/2026-08-28-retrieval-telemetry-v3-plan.md
Depends-On: None

# Implement Retrieve Inference Observation V3

## Scope

Implement the schema-v3 command producer/envelope and command-scoped inference request instrumentation governed by `.10x/specs/retrieve-inference-telemetry-v3.md`.

This child owns:

- private worker lifecycle diagnostics needed to distinguish spawned/reused/unknown without filesystem/process probing;
- inference request spans around actual worker and in-process encode/score calls;
- command inference-policy derivation;
- v3 graph/attribute/envelope canonical validation for command, operation, spans, and events; and
- focused fake-clock/backend/privacy/failure-isolation tests.

## Acceptance criteria

- An explicit internal schema-v3 command session produces canonical v3 observations while preserving v2 command/pipeline timing semantics; production activation is transferred to the dependent store/queue integration ticket so no v3 payload enters inbox-v2.
- Each actual encode/score backend call creates exactly one governed inference span; established fallback creates failed worker primary plus in-process fallback spans.
- Automatic route embedding/prototype score spans are children of route selection; query/result/evidence calls have exact governed parents.
- Spawn/reuse is reported from bounded worker-client lifecycle state, never inferred post hoc.
- Policy is exactly worker-preferred, forced-in-process, or compatibility-in-process.
- Disabled telemetry installs no callback/context and adds no side effect.
- Callback/telemetry faults preserve exact call count, fallback, warning, result/exception identity, output, and worker lifecycle.
- V3 canonical decoder independently rejects bad graph, attributes, values, counts, and prohibited sentinels.
- Existing v1/v2 envelope tests remain unchanged and passing.
- Focused tests pass on Python 3.11 and 3.13 without provider/network/model download.

## Evidence expectations

Record changed files, focused commands, deterministic lifecycle/fallback fixtures, exact privacy inspection, and residual risks. No live provider call is authorized by this child.

## Explicit exclusions

Provider-accounting persistence, queue/store/migration, live provider use, model/ranking changes, worker protocol/model/lifetime changes, output changes, default enablement, release, and unrelated refactoring.

## References

- `.10x/specs/retrieve-inference-telemetry-v3.md`
- `.10x/specs/retrieve-command-telemetry.md`
- `.10x/specs/default-retrieve-embedding-worker.md`
- `.10x/specs/default-retrieve-cross-encoder-worker-residency.md`
- `.10x/research/2026-08-28-retrieval-telemetry-current-state-and-gaps.md`

## Progress and notes

- 2026-08-28: Opened after ratification. No source implementation in the record-authoring turn.
- 2026-08-28: Activated for the integrated v3 milestone. The first dual-runtime baseline attempt incorrectly ran two `uv run` processes concurrently against one `.venv`; both exited 2 after racing to recreate it and reported `pytest` missing. Stopped and escalated before source edits. Owner authorized rebuilding and rerunning sequentially.
- 2026-08-28: Repaired with `uv sync --python 3.13 --all-groups`. Sequential provider-free baselines then passed on both runtimes: Python 3.13 and 3.11 each reported 353 tests plus 496 subtests passed for telemetry, provider-receipt, and embedding-worker suites.
- 2026-08-28: Source inspection found that safely activating production v3 required the separately owned inbox-v3 and complete provider-accounting seams. Supervisor directed this child to remain in-memory/test-only: no v3-through-v2 publication, trace suppression, or queue widening. Added an explicit internal schema-v3 session and an unavailable-provider fixture only for canonical tests; production command creation/publication remains exact v2 until downstream activation.
- 2026-08-28: Implemented v3 inference policy/spans/validators, worker spawned/reused/unknown lifecycle callback, command-wide worker/fallback sibling observations, and v3-only in-process wrappers. Added deterministic privacy, graph, policy, failure-isolation, and worker lifecycle tests. Candidate evidence: `.10x/evidence/2026-08-28-retrieve-inference-observation-v3.md`.
- 2026-08-28: Provider-free validation passed: focused Python 3.13 `351 passed, 362 subtests passed`; focused Python 3.11 `209 passed, 258 subtests passed`; full Python 3.13 and isolated Python 3.11 each `1278 passed, 1350 subtests passed` with only 57 pre-existing lxml deprecation warnings. `git diff --check` and compileall passed; no provider call, real telemetry-store access, staging, or commit occurred.
- 2026-08-28: Applied parent-accepted P1 review repairs without activating v3 publication: lifecycle state now changes only at compatible greeting contact; fallback factories sit outside request timing; the decoder requires the exact immediate failed-worker/fallback sibling pair while accepting later latched fallbacks; late identity/capability rejection downgrades policy; disabled paths remain direct; and fresh in-process evidence scoring uses the instrumented command reranker under evidence assessment.
- 2026-08-28: Expanded deterministic coverage for contact/pre-contact lifecycle failures, post-contact errors, fake-clock call boundaries, automatic routing/query/rerank/evidence parents, evidence score reuse, double failure, malformed fallback pairs, late policy downgrade, side-effect-free preview/disabled paths, telemetry-fault isolation, item bounds, and the complete prohibited-sentinel matrix. Production v2 in-process evidence loading remains on its original direct path; only explicit v3 sessions inject the instrumented command reranker.
- 2026-08-28: Review-fix validation passed provider-free: focused Python 3.13 `387 passed, 403 subtests passed`; focused isolated Python 3.11 `246 passed, 299 subtests passed`; full Python 3.13 and isolated Python 3.11 each `1290 passed, 1369 subtests passed` with only 57 pre-existing lxml deprecation warnings. Candidate evidence was updated; no provider/network/model call, real telemetry-store access, staging, or commit occurred. Ticket remains active for required independent review.
- 2026-08-28: Applied the two accepted follow-up test repairs only. Added an enabled-versus-fault-injected matrix through `_CommandEmbeddingWorkerSession` covering worker success, fallback success, and exact double-failure identity with backend/factory counts, lifecycle, selection, warning/output, and return/exception assertions. Rebuilt malformed-pair fixtures as a valid automatic graph and added independently decodable witnesses so parent, operation, item-count, and immediacy failures reach the intended sibling-pair grammar rather than generic graph rejection. No production bug was exposed and no production source changed in this follow-up.
- 2026-08-28: Final follow-up focused suites passed provider-free on Python 3.13 and isolated Python 3.11: each `163 passed, 94 subtests passed`. Production v2 deferral and all downstream exclusions remain unchanged; no provider/network/model use, real store access, staging, or commit occurred.
- 2026-08-28: Final independent review found no P0/P1/P2 issue and returned pass after two repair rounds. Parent reran `git diff --check` and the reconciled Python 3.13 acceptance matrix: `163 passed, 94 subtests passed`. Review: `.10x/reviews/2026-08-28-retrieve-inference-observation-v3-review.md`.
- 2026-08-28: Closure reconciliation mapped every bounded criterion to recorded evidence. The production switch remains explicitly owned by `.10x/tickets/done/2026-08-28-implement-local-telemetry-v3-store-and-migration.md` and `.10x/tickets/done/2026-08-28-validate-retrieval-telemetry-v3-integration.md`; this is dependency sequencing, not residual scope in this milestone.
- 2026-08-28: Retrospective extracted the atomic version-activation rule into `.10x/knowledge/telemetry-version-activation-is-atomic-with-queue-consumer.md`. No additional defect or follow-up was found.

## Blockers

None.
