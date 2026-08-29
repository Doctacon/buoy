Status: concerns
Created: 2026-08-28
Updated: 2026-08-28
Target: .10x/tickets/done/2026-08-28-extend-default-worker-with-cross-encoder-scoring.md
Evidence: .10x/evidence/2026-08-28-default-worker-cross-encoder-scoring.md
Verdict: concerns

# Cross-Encoder Worker Scoring Independent Implementation Review

## Scope

Independent adversarial review of the active scoring-worker ticket, governing decision/specifications, implementation and test diff, execution evidence, current source, documentation, package contents, Python 3.11/3.13 suites, and Git state. No live provider call, model download/cache mutation, global installation, production/test edit, or ticket/evidence/spec/decision edit ran. This review created only this review record.

## Findings

### Blocker — the worker's 49-passage ceiling does not cover the governed 108-passage automatic-routing seam

The ticket's assumption provenance says the maximum routing score batch is 49, but current governed source and its existing source-named test establish a maximum of 108:

- `src/buoy_search/retrieval/routing.py:58` sets `ROUTING_SHORTLIST_LIMIT = 12`;
- `src/buoy_search/catalog/local.py:59-60` permits eight routing evidence/example passages per card;
- `src/buoy_search/retrieval/routing.py:503-569` emits one base passage plus up to eight examples/source passages per shortlisted card and accepts `12 * (8 + 1) = 108`; and
- `tests/retrieval/test_automatic_routing.py:833-846` explicitly freezes the exact 108-passage bound.

The new client instead rejects every score call over 49 before IPC at `src/buoy_search/retrieval/embedding_worker.py:62,531-549`. The command session treats that local protocol rejection as worker failure, emits the public fallback warning, and scores all 108 pairs in-process. A read-only reproduction using the production session and exact input validator returned 108 fallback scores with `_worker_failed=True` and exactly the warning `Warning: local embedding worker failed; using in-process embedding for this command.`

Consequences:

- a valid exact-compatible automatic route can repeat the measured process-cold CrossEncoder import that this ticket is meant to remove;
- the command reports a worker failure even though the worker and inputs are valid under the existing routing contract;
- all later local inference in that command switches in-process; and
- acceptance criterion 5's complete automatic prototype-routing integration and the evidence's “maximum 49 routing score pairs” claim are not supported.

This is not safely repairable by silently widening the owner-ratified 49-pair protocol. Resolution needs one explicit contract choice: permit a 108-pair request with a correspondingly safe frame bound, define and parity-test deterministic sequential client chunking of one 108-pair logical score call into bounded requests, or explicitly accept visible in-process fallback and narrow the complete-integration claim. No routing cardinality/ranking change should be made merely to fit the worker.

### Moderate — retrieval documentation retains a now-false missing-model/provider-order claim

`docs/retrieval.md:260-264` says an ambiguous multi-corpus request with a missing exact snapshot fails before content queries. On an eligible worker path, `src/buoy_search/cli/main.py:1902-1910` injects an adapter without loading the reranker; the worker loads it only on the first actual score, after multi-namespace content results exist. The specification explicitly permits scoring fallback after provider reads, and the added CLI test intentionally exercises scoring failure after one content operation. Therefore a worker model-load failure followed by an unavailable in-process fallback can occur after content reads, contrary to the documentation.

This does not duplicate provider operations, and it is consistent with the newly ratified lazy-score design, but criterion 10 is not satisfied until the documentation distinguishes the worker-lazy path from the opt-out/in-process pre-query load path or otherwise states the new ordering truthfully.

## Positive observations

- Schema v2, the distinct `v2-*` identity path, exact ready/state identity, same-user private socket controls, strict tagged fields, duplicate/unknown-field rejection, UTF-8/text/frame bounds, finite score validation, redacted errors, and pre-request greeting validation are implemented coherently.
- `_connect_and_score` maps all post-request transport/protocol failures to bounded public errors, so `_request_from_worker` does not replay after request transmission.
- `_WorkerRuntime` eagerly holds only the existing embedder and lazily loads one cached reranker object. Valid encode/score requests refresh idle life; malformed connections do not. Server execution remains serial.
- The command session shares one reranker adapter, failure latch, exact warning, and in-process fallback. Routing, evidence, explicit/automatic multi-namespace, and widening injection seams are present. Added provider-count and double-failure tests pass.
- Opt-out/ineligible and no-score dormancy behavior is preserved by lazy CLI import/selection and test coverage.
- Worker state/files contain content-free identity only; score/query/passages are local request variables and are not added to state or durable files. The minimal child environment remains credential-free, telemetry-disabled, and offline.
- The optional `MultiNamespaceRetriever.from_configs(..., reranker_loader=...)` seam is narrow and preserves omitted behavior.
- No production/test change outside the ticket's named seams was found. No staged files exist.

## Acceptance-criteria map

1. **Protocol identity — PASS.** Schema v2 and the complete greeting/state identity reject old/mixed workers before query/passage IPC; encode validation remains unchanged apart from protocol/frame identity.
2. **Strict score framing — PASS for the ratified 1–49 protocol.** Focused tests and source inspection cover fields, duplicate/unknown input, 1/49/50, UTF-8/value/frame bounds, response identity/count/finiteness, timeout/truncation, and no post-request replay.
3. **Lazy residency — PASS.** Encode-only leaves reranker loads at zero; first score loads once; reuse and idle semantics are tested.
4. **Parity — PARTIAL.** Retained provider-free evidence reports exact delta 0.0 for 1/24/49 and all semantic suites pass, but the governed 108-pair routing case is not worker-scored and has no worker-versus-in-process parity result.
5. **Complete integration — FAIL/BLOCKED.** The automatic route seam can legitimately produce 108 passages and therefore falls back visibly under the 49-passage worker limit.
6. **Opt-out/ineligibility — PASS.** Matrix tests pass without worker reranker injection/warning for expected ineligibility.
7. **Fallback — PASS within tested cardinalities.** One warning, shared latch, no IPC replay, no provider duplication, and phase-correct redacted double failures are covered.
8. **Privacy/security — PASS.** Strict transient frames, content-free state, minimal child environment, existing private IPC controls, and no-persistence inspections are present.
9. **Lifecycle — PASS.** Election, stale cleanup, serial serving, valid-request idle refresh, invalid-request non-refresh, timeout, and cleanup tests pass.
10. **Documentation — FAIL.** The missing-snapshot-before-content statement is false for eligible lazy worker scoring.
11. **Validation — PARTIAL.** Sequential independent Python 3.11 and 3.13 suites each pass 1,265 tests; focused tests, build contents, compile, diff hygiene, and no-staged checks pass. Independent review has unresolved concerns.
12. **No live effects — PASS.** No live/provider/model-download/global/release operation ran in review; execution evidence records the same boundary.

## Commands and validation

- `uv run python -m unittest tests.retrieval.test_embedding_worker tests.retrieval.test_multi_namespace_retrieval tests.retrieval.test_automatic_routing tests.cli.test_cli` — PASS, 191 tests.
- `uv run --python 3.11 python -m unittest discover -s tests -t .` — PASS, 1,265 tests in 119.401 seconds.
- `uv run --python 3.13 python -m unittest discover -s tests -t .` — PASS, 1,265 tests in 110.346 seconds.
- `UV_OFFLINE=1 uv build --out-dir <private-temp>` plus wheel/sdist inspection — PASS; worker and cross-encoder modules present, `.10x` absent, temporary output removed.
- `uv run python -m compileall -q src/buoy_search`, `git diff --check`, and staged-file check — PASS.
- Static cardinality inspection plus production-session reproduction of a 108-passage call — reproduced visible protocol fallback exactly.
- Scope/status inspection — PASS: production/tests/docs changes are limited to ticket seams; no staged files.

One earlier parallel dual-runtime review probe was discarded because simultaneous `uv --python` commands contend for the shared `.venv`; the sequential commands above are the accepted independent results.

## Verdict

**CONCERNS — NOT READY TO CLOSE.**

The core v2 transport, lazy residency, privacy, fallback, and 1/24/49 implementation is sound, but a current source-backed 108-passage routing contract defeats worker scoring on a valid eligible automatic route. The stale documentation claim is separately repairable after the owner resolves/ratifies the cardinality handling. Re-review is required after repair.

## Residual risks

- Combined resident memory after both models load remains host-dependent and was not independently remeasured here.
- Provider-derived passages cross the same-user local socket transiently; no persistence was found.
- POSIX/default-float32-only eligibility remains intentional.
- Direct model parity relies on the retained provider-free execution evidence; review reran semantic/full suites but did not rerun cached-model inference.
