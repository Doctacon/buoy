Status: passed
Created: 2026-08-28
Updated: 2026-08-28
Target: .10x/tickets/done/2026-08-28-extend-default-worker-with-cross-encoder-scoring.md
Evidence: .10x/evidence/2026-08-28-default-worker-cross-encoder-scoring.md
Prior-Review: .10x/reviews/2026-08-28-cross-encoder-worker-scoring-implementation-review.md
Verdict: pass

# Cross-Encoder Worker Scoring Final Acceptance Review

## Scope

Fresh independent final review after the owner-ratified 108-passage repair. I read the governing decision/specifications, active ticket, execution evidence, immutable initial concerns review, production and test diff, current routing/cardinality source, documentation, and package state. I independently ran focused and complete dual-runtime suites, exact cached-model provider-free parity, package/build and isolated-wheel checks, validators, compilation, diff hygiene, staged-state, process cleanup, and temporary-artifact checks.

This review changed no production, tests, documentation, decision, specification, evidence, initial review, or ticket. It created only this review record. No live/provider command, download, cache mutation, global install, release, deployment, or publication ran.

## Findings

No blocking findings.

### Initial 49-versus-108 blocker — resolved

Current governed routing remains unchanged: `ROUTING_SHORTLIST_LIMIT = 12`, each card permits eight combined routing examples/source passages, and `_rerank_prototype_shortlist` scores one base plus those eight passages, yielding the existing exact maximum `12 * 9 = 108`. The source-named regression still freezes that bound.

The repaired worker now defines `MAX_SCORE_PASSAGES = 108` and `MAX_FRAME_BYTES = 8_388_608`. Client and server enforce the 1–108 bound, canonical aggregate request size, and strict tagged identity. Tests cover 1, 108, and rejected 109 cardinalities plus inclusive aggregate-frame acceptance/rejection. The source-named CLI integration sends all 108 passages through one worker callback, observes no warning, constructs no in-process fallback, and leaves the command session's worker-failure latch false.

An independently run exact cached-model parity probe used two exact pinned reranker instances and the real private Unix-socket worker transport under credential-free/offline controls. Counts 1, 24, 49, and 108 each returned maximum absolute score delta `0.0`; the reranker cache content manifest remained equal, provider operations were zero, request sentinels were absent from worker files, worker cleanup completed, and no lineage remained.

The repair therefore accommodates existing scoring work without chunking, routing-cardinality changes, accepted fallback, additional provider work, or ranking changes.

### Initial documentation-ordering finding — resolved

`docs/retrieval.md` no longer claims every missing lazy worker model fails before content queries. It now distinguishes prototype routing before content from multi-corpus reranking after namespace results, states that availability is checked at the first score boundary, and states that fallback reuses already retrieved passages without repeating catalog/content operations. It also accurately documents transient same-user passage IPC, lazy memory residency, five-minute idle lifetime, opt-out, and one visible fallback without an SLA.

## Implementation review

### Protocol, identity, and framing

Schema 2 and the distinct `v2-*` identity directory bind worker implementation/package/Python identity, exact embedding identity, and exact MiniLM model/revision/CPU/max-length/batch/local-only/safetensors/no-remote-code identity. Ready/state validation rejects missing, old, or mixed identities before a query or passage is sent.

Encode request/vector semantics remain unchanged apart from schema/path identity and the shared bounded frame ceiling. Score parsing rejects unknown/duplicate fields, wrong identity, invalid/empty/oversized text, invalid cardinality, wrong/non-finite/boolean scores, malformed outcomes, truncation, and timeout. Post-request transport/protocol failures become bounded errors and do not return to the startup/reuse retry branch.

### Residency, integration, and semantics

`_WorkerRuntime` eagerly holds only the existing embedder and lazily constructs one exact reranker on the first valid score. It reuses that object serially. Valid encode and score requests refresh accepted-request idle life; malformed connections do not. The worker state remains content-free.

One command session owns one cached worker-backed reranker adapter and one shared embed/score failure latch. The CLI injects that adapter into all three existing cross-encoder seams:

1. automatic prototype-routing shortlist scoring;
2. calibrated evidence assessment when existing scores are unavailable; and
3. explicit/automatic multi-namespace reranking and widening through the new optional `MultiNamespaceRetriever.from_configs(..., reranker_loader=...)` seam.

The optional retriever argument preserves omitted library behavior. Existing routing passage formatting, candidate counts, score interpretation, thresholds, fusion, namespace coverage, evidence decisions, provider ordering, serialized output, and telemetry semantics are unchanged; complete 1,268-test suites pass on both required Python versions.

### Fallback, privacy, and lifecycle

The first encode or score failure emits the existing redacted warning exactly once, computes the failed local operation in-process, and sends all later local inference in-process. Scoring fallback after content uses the existing formatted query/passages and does not replay provider reads. Worker IPC is not retried after request transmission. Double failure is redacted and retains `model_error` taxonomy rather than provider classification.

Opt-out, custom model, float16, unsupported/incompatible selection, no-score, and non-retrieve paths retain in-process/dormant behavior without an expected-ineligibility warning or worker state.

Queries, passages, vectors, scores, and frames are not included in readiness/error state or durable files. The worker child remains offline, telemetry-disabled, credential-free, same-user/private-socket constrained, serial, and free of provider/catalog/orchestration/telemetry-store behavior. Election, stale cleanup, idle exit, timeout, socket/state cleanup, and zero-survivor checks pass.

## Acceptance-criteria map

1. **Protocol identity — PASS.** Schema 2/v2 and complete embedding/reranker identity are strict; old/malformed/mixed identities fail before content IPC; encode suites remain passing.
2. **Strict score framing — PASS.** Exact 1–108 cardinality, rejected 109, 65,536-byte value bound, inclusive 8,388,608-byte canonical frame ceiling, finite ordered response, timeout/truncation, and no-post-request retry are implemented and tested.
3. **Lazy residency — PASS.** Encode-only construction count remains zero; first score loads once; later scores reuse; accepted idle refresh and malformed-request non-refresh pass.
4. **Parity — PASS.** Independent exact cached-model score delta is `0.0` for 1/24/49/108; complete semantic suites pass. Exact-108 automatic routing remains worker-resident without warning/fallback.
5. **Complete integration — PASS.** Routing, evidence fallback scoring, result reranking, and widening share one adapter; no-score/named paths preserve no-score behavior.
6. **Opt-out/ineligibility — PASS.** Opt-out/custom/float16/unsupported/incompatible paths retain established in-process behavior without worker injection/state/warning.
7. **Fallback — PASS.** One warning, shared latch, in-process continuation, no IPC replay, no provider duplication, redacted phase-correct double-failure behavior all pass focused/full suites.
8. **Privacy/security — PASS.** Strict transient payloads, content-free files/state, credential-free/offline child, existing same-user private IPC, and prohibited-module boundaries are supported by source, tests, parity inspection, and cleanup checks.
9. **Lifecycle — PASS.** Election, serialization, stale cleanup, five-minute accepted-request semantics, timeout, idle exit, and complete cleanup pass under encode/score paths.
10. **Documentation — PASS.** The initial provider-ordering defect is corrected; scoring extension, IPC/privacy, lazy memory, opt-out, and fallback are accurate with no SLA promise.
11. **Validation — PASS.** Independent focused and complete Python 3.11/3.13 suites, build/package inspection, isolated-wheel dormancy/activation, validators, compile, diff check, zero staged files, and this review pass.
12. **No live effects — PASS.** Review and retained execution evidence show no live/provider command, download/cache mutation, global installation, telemetry migration, release, deployment, publication, commit, or staging.

## Commands and checks

- `uv run --python 3.11 python -m unittest tests.retrieval.test_embedding_worker tests.retrieval.test_multi_namespace_retrieval tests.retrieval.test_automatic_routing tests.cli.test_cli` — PASS, 193 tests in 27.878 seconds.
- `uv run --python 3.13 python -m unittest tests.retrieval.test_embedding_worker tests.retrieval.test_multi_namespace_retrieval tests.retrieval.test_automatic_routing tests.cli.test_cli` — PASS, 193 tests in 27.505 seconds.
- `uv run --python 3.11 python -m unittest discover -s tests -t .` — PASS, 1,268 tests in 123.501 seconds.
- `uv run --python 3.13 python -m unittest discover -s tests -t .` — PASS, 1,268 tests in 114.664 seconds.
- Credential-free/offline exact cached-model worker parity probe — PASS, counts 1/24/49/108, maximum absolute deltas all `0.0`, cache manifest equal, no provider operation, content-free state/files, complete cleanup.
- `UV_OFFLINE=1 uv build --out-dir <private-temp>` and wheel/sdist inspection — PASS, 94 wheel entries and 193 sdist entries; worker/cross-encoder modules present, `.10x` absent, output removed.
- Offline private Python 3.13 wheel install — PASS: CLI import dormant with neither worker nor Sentence Transformers imported; fake-model encode plus 108/1 scoring used schema 2, exact bounds, one lazy reranker load, content-free state, idle cleanup; temporary venv/home/dist removed.
- `scripts/validate_ranking_contract.py` — PASS.
- `scripts/validate_ranking_promotion.py --base-ref HEAD --comparison-mode exact` — PASS, ranking authority unchanged and promotion basket empty.
- `scripts/c6_syntax_forecast.py validate` — PASS.
- `python -m compileall -q src/buoy_search`, `git diff --check`, staged-file check, temporary-directory check, and worker-process check — PASS; zero staged files, zero review temp directories, zero worker processes.

Two review-harness-only corrections preceded accepted package checks: one inspection wrapper used unavailable bare `python` after a successful build, and one isolated activation omitted creation of its test home parent. Corrected commands above passed; neither failure exercised product behavior or left artifacts.

## Changed-file and scope assessment

Production/documentation/specification changes are limited to:

- `.10x/specs/default-retrieve-embedding-worker.md`;
- `docs/retrieval.md`;
- `src/buoy_search/cli/main.py`;
- `src/buoy_search/retrieval/embedding_worker.py`; and
- `src/buoy_search/retrieval/retriever.py`.

Tests are limited to:

- `tests/cli/test_cli.py`;
- `tests/retrieval/test_automatic_routing.py`;
- `tests/retrieval/test_embedding_worker.py`; and
- `tests/retrieval/test_multi_namespace_retrieval.py`.

The diff adds the named protocol, command-session, injection, documentation, and test seams without model/ranking/provider/output/telemetry changes. No unrelated production or test file changed. Current broader untracked `.10x` records belong to the already documented migration/measurement work; no file is staged.

## Verdict

**PASS. Merge/closure verdict: OK.**

All twelve ticket criteria are supported. The initial 49-passage and documentation concerns are resolved under the owner-ratified 108-passage/8,388,608-byte contract.

## Residual risks

- Combined resident RSS after both exact models load remains host/dependency dependent and was not promoted to an SLA or release limit.
- Provider-derived formatted passages cross a private same-user Unix socket transiently; source/tests found no persistence, but this is a larger transient local IPC surface than embedding-only operation.
- The 8 MiB frame increases bounded same-user memory exposure; strict per-value/cardinality checks, serial serving, private peer/path controls, and timeouts bound it.
- Worker eligibility remains intentionally POSIX/default-model/float32 only.
- No live end-to-end latency A/B ran under this ticket; correctness and parity do not establish a production latency distribution.
