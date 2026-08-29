Status: completed
Created: 2026-08-28
Updated: 2026-08-28
Ticket: .10x/tickets/done/2026-08-28-extend-default-worker-with-cross-encoder-scoring.md
Review: .10x/reviews/2026-08-28-cross-encoder-worker-scoring-implementation-review.md, .10x/reviews/2026-08-28-cross-encoder-worker-scoring-final-review.md
Specification: .10x/specs/default-retrieve-cross-encoder-worker-residency.md, .10x/specs/default-retrieve-embedding-worker.md
Decision: .10x/decisions/buoy-keeps-the-pinned-cross-encoder-resident-in-the-existing-local-worker.md

# Default Worker Cross-Encoder Scoring Execution Evidence

## Disposition

Implemented the scoring-capable worker transport and integration. After independent review found that the original 49-passage request ceiling did not cover the source-governed 108-passage automatic-routing maximum, the owner ratified one exact 108-passage request and an 8,388,608-byte canonical frame ceiling. The bounded repair, validation, and exact cached-model parity are complete. No live provider command, model download, cache mutation, telemetry migration, global installation, release, deployment, commit, or staging operation ran. Fresh independent final review passed all twelve criteria and the ticket is closed.

## Production changes

- `src/buoy_search/retrieval/embedding_worker.py`
  - Versioned the strict protocol and identity directory from schema 1/v1 to schema 2/v2.
  - Bound the exact embedding and pinned MiniLM model/revision/device/max-length/batch/local-only/safetensors/no-remote-code identities in greeting and durable content-free state.
  - Preserved encode fields/vector semantics while raising the shared canonical frame ceiling to exactly 8,388,608 bytes.
  - Added strict tagged score requests: one nonempty bounded query, 1–108 bounded passages, exact identity, strict fields, duplicate rejection, aggregate frame enforcement, and no replay after request transmission.
  - Added exact finite ordered score responses and bounded `model_unavailable`/`scoring_failure` errors.
  - Added a serial runtime that eagerly retains only the existing embedder and lazily loads/reuses the exact production cross-encoder on first accepted score.
  - Both valid encode and score requests refresh the unchanged five-minute idle clock; malformed connections do not. Query, passage, vector, score, and frame values are not placed in worker state or files.
- `src/buoy_search/cli/main.py`
  - Added one command-cached worker reranker adapter sharing the existing worker failure latch and exact warning text with embeddings.
  - Worker failure switches all later local embedding/scoring in-process; reranker double failure remains `model_error`, redacted, and phase-specific.
  - Injected one worker adapter into automatic prototype routing, evidence assessment without existing scores, explicit/automatic multi-namespace reranking, and widening.
  - Preserved omitted/in-process behavior for opt-out, custom model, float16, unsupported platform, and worker-ineligible configurations.
- `src/buoy_search/retrieval/retriever.py`
  - Added only an optional `reranker_loader` argument to `MultiNamespaceRetriever.from_configs`; omitted behavior is unchanged.
- `docs/retrieval.md`
  - Documented lazy scoring residency, transient same-user provider-derived passage IPC, no persistence, memory lifetime, opt-out, and command-wide visible fallback without an SLA.

## Tests added or updated

- `tests/retrieval/test_embedding_worker.py`
  - schema-v2/reranker greeting and identity path;
  - strict score fields, duplicate/unknown fields, exact 1/108/109 boundaries, inclusive aggregate-frame enforcement, UTF-8/text limits, finite score identity/count checks, and pre-filesystem client rejection;
  - lazy one-time load, same-process reuse, bounded load/inference failures, accepted score idle refresh, serialized serving, no persistence, timeout/truncation, no post-request replay, and cleanup.
- `tests/retrieval/test_multi_namespace_retrieval.py`
  - exact optional reranker-loader propagation from the factory.
- `tests/retrieval/test_automatic_routing.py`
  - active prototype scoring through the worker, including the source-governed exact-108 route with no warning or fallback; one shared adapter for retrieval/evidence; command-wide score-to-embed fallback; one warning on actual failure; and routing double-failure model taxonomy/redaction.
- `tests/cli/test_cli.py`
  - opt-out/custom/float16 multi-namespace in-process behavior; explicit multi worker embed/score; score fallback after one content operation without replay; and reranker double-failure model taxonomy/redaction.

## Provider-free parity

A credential-free, telemetry-disabled, Hugging Face/Transformers-offline Python 3.13 harness used the exact cached production models and a private temporary Buoy home. It compared unchanged in-process scores with schema-v2 worker subprocess scores for fixed synthetic batches of 1, 24, 49, and 108 pairs.

Result: all four counts matched, maximum absolute score delta was `0.0` at every cardinality, the exact embedding/reranker cache manifests were equal before and after, the worker process group terminated, no live lineage remained, and the external script/directory were removed. Provider operation and credential-key counts were zero.

Two earlier harness-debug attempts produced no retained parity result. The first used an overlong private socket path and failed before worker startup; the second encountered a transient socket-validation failure after startup. Both removed their external files/directories and any worker lineage. A subsequent bounded diagnostic established the exact 1/24/49/108 path before the accepted cache-bound observation above.

## Validation

### Focused

- `uv run python -m unittest tests.retrieval.test_embedding_worker tests.retrieval.test_multi_namespace_retrieval tests.retrieval.test_automatic_routing tests.cli.test_cli`
  - PASS: 193 tests after the 108-bound repair.
- Strict 1/108/109 protocol bounds, inclusive canonical-frame validation, exact-108 worker-resident automatic routing, score transport, fallback, and worker lifecycle cases passed.

### Complete suites

- `uv run --python 3.11 python -m unittest discover -s tests -t .`
  - PASS: 1,268 tests in 124.540 seconds.
- `uv run --python 3.13 python -m unittest discover -s tests -t .`
  - PASS: 1,268 tests in 115.736 seconds.

### Packaging and isolated install

- `UV_OFFLINE=1 uv build --out-dir <private-temp>`
  - PASS: one wheel (94 entries) and one sdist (193 entries); both contain the worker/cross-encoder modules; neither contains `.10x` records; temporary outputs removed.
- Offline isolated Python 3.13 wheel install under a private temporary directory:
  - PASS dormancy: importing CLI loaded neither the worker backend nor Sentence Transformers and created no Buoy home.
  - PASS activation: fake provider-free installed-package encode plus 108- and 1-passage score calls used schema 2, exact bound 108, exact frame bound 8,388,608, loaded one lazy reranker exactly once, returned expected vectors/scores, persisted no request/response fields, and cleaned socket/state after idle exit.
  - Temporary venv/home/dist were removed; this was not a global installation.

### Validators and hygiene

- `scripts/validate_ranking_contract.py`: PASS.
- The first promotion-validator invocation intentionally supplied CI-style environment without a comparison ref and failed closed with the expected missing-base diagnostic. The corrected local command `scripts/validate_ranking_promotion.py --base-ref HEAD --comparison-mode exact` passed and classified ranking authority unchanged with an empty promotion basket.
- `scripts/c6_syntax_forecast.py validate`: PASS.
- `git diff --check`: PASS throughout implementation.
- Full suites, parity, build, and isolated install used no provider credential/client/catalog/content operation and no live command.

## Acceptance mapping

1. New strict protocol/identity and old-worker separation: implemented and adversarially tested.
2. Strict 1–108 score framing with exact 1/108/109 boundaries, finite responses, timeout/truncation, inclusive 8,388,608-byte ceiling, and no replay: implemented and tested.
3. Lazy one-time reranker construction/reuse and accepted idle refresh: implemented and tested.
4. Exact score and downstream semantic parity: direct 1/24/49/108 delta `0.0`; existing routing/ranking/evidence/output/telemetry suites pass.
5. All retrieve seams use the shared adapter. The exact source-governed 108-passage automatic route remains worker-resident with no warning, fallback, routing-cardinality change, or chunking.
6. Opt-out/ineligibility: existing and added matrix tests pass with omitted worker loaders/state/warnings.
7. Shared fallback: one warning, command-wide latch, no provider replay, redacted phase-correct double failure tested.
8. Privacy/security: strict transient frames, content-free state, no request persistence, minimal child environment, and private existing IPC controls pass.
9. Lifecycle: election, serialization, stale cleanup, idle behavior, timeout, and terminal cleanup suites pass.
10. Documentation was corrected after review to describe lazy worker model-load ordering truthfully, without changing help compatibility or promising a target.
11. Both required runtime suites, package, isolated install, validators, compile, hygiene, and no-staged checks passed after repair; fresh independent final review passed.
12. No prohibited live/release/deploy/global/staging effect occurred.

## Independent review history and resolution

The initial review at `.10x/reviews/2026-08-28-cross-encoder-worker-scoring-implementation-review.md` passed protocol, lifecycle, fallback, privacy, opt-out, and no-live-effect behavior but correctly blocked closure because current source permits 108 routing score pairs while the first implementation accepted 49. It separately found stale model-load ordering documentation, which was corrected without runtime change.

The owner then explicitly selected one 108-passage worker request with an exact 8,388,608-byte canonical frame ceiling. The repair changes no logical scoring work: current routing already produces at most 12 times (one base plus eight evidence) passages. It does not chunk, change routing cardinality, accept fallback, change scores, or alter ranking/provider/output/telemetry semantics. The initial concerns review remains historical evidence. Fresh final review at `.10x/reviews/2026-08-28-cross-encoder-worker-scoring-final-review.md` independently confirmed both findings resolved and passed all twelve criteria.

## Final repair validation

- Focused protocol/integration/fallback suites: PASS, 193 tests.
- Sequential full Python 3.11 and 3.13 suites: PASS, 1,268 tests each.
- Provider-free exact cached-model parity: PASS for 1/24/49/108, maximum absolute delta `0.0` for every count, equal pre/post cache identities, zero provider/credential operations, complete worker-lineage and external-artifact cleanup.
- Offline build and package-content inspection: PASS; wheel/sdist contain required modules and exclude `.10x`.
- Offline isolated-wheel dormancy and fake-model activation: PASS at exact 108/8,388,608 bounds with one lazy reranker load and complete cleanup.
- `scripts/validate_ranking_contract.py`, `scripts/validate_ranking_promotion.py --base-ref HEAD --comparison-mode exact`, and `scripts/c6_syntax_forecast.py validate`: PASS.
- `python -m compileall -q src/buoy_search`, `git diff --check`, and no-staged-files check: PASS.

No live/provider operation, model download/cache mutation, global install, release, deployment, publication, commit, or staging ran.

## Residual risks

- The initial independent review remains immutable history; its cardinality blocker is repaired under the later owner-ratified 108-passage/8,388,608-byte contract and the fresh final review passed.
- Combined resident memory after lazy MiniLM load remains host/model dependent and is not an SLA.
- Worker support remains limited to the existing exact default POSIX/float32 eligibility.
- Provider-derived passages now cross a private same-user local socket transiently; they are not persisted or logged.
- No live end-to-end A/B was authorized or run by this implementation ticket.
