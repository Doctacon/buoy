Status: done
Created: 2026-08-28
Updated: 2026-08-28

# Retrieval Telemetry Current State and Gaps

## Question

What retrieval telemetry does Buoy currently produce and persist, what useful answers does it support, and where does it fall short after default embedding plus cross-encoder worker residency?

## Sources and methods

This read-only audit inspected:

- `.10x/specs/retrieve-command-telemetry.md`;
- `.10x/specs/local-telemetry-writer.md` and the superseded v1 retrieval contract;
- `.10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md`;
- `.10x/research/2026-08-24-physical-provider-attempt-accounting-options.md`;
- `.10x/research/2026-08-28-post-worker-retrieval-latency-residuals.md`;
- current `src/buoy_search/cli/entrypoint.py`, `cli/main.py`, `retrieval/retriever.py`, `retrieval/_provider_invocation_receipt.py`, and `telemetry/{producer,envelope,queue,store,writer}.py`;
- `buoy telemetry status --json`; and
- content-free aggregate read-only SQL over `retrieval_runs_v1`, `retrieval_stage_latency_v1`, `retrieval_command_runs_v2`, and `retrieval_stage_latency_v2` in the canonical local DuckDB.

The database was opened read-only. Queries selected only versions, modes, outcomes, counts, timestamps, stage names/status, and aggregate durations. No trace/span ID, attributes JSON, query, argument, namespace, route value, content, URL, path, credential, provider response, or raw error was emitted or retained. No telemetry flush/writer/migration, retrieval, provider, model, cache, or external mutation ran.

## What exists today

### Strong command and broad-stage coverage

For opted-in `buoy retrieve`, schema v2 records:

- near-shell Buoy command duration from the lightweight entry point through rendering;
- live inner-pipeline duration separately;
- execution mode (`live|preview`) and retrieval mode (`explicit_single|explicit_multi|automatic`);
- command outcome, exit code, and bounded error category;
- bootstrap, prepare, automatic catalog/model/select, pipeline, embed, namespace, rerank, evidence, and render spans when those stages occur;
- content-free counts for hits, namespaces, fanout, failures, rerank candidates/deduplication, and evidence candidates;
- routing selection reason and finite semantic score/margin;
- widening reason/event, evidence mode/status/scores, model/precision labels, and route-rank-only namespace status/hit count.

This is enough to distinguish total command latency from inner retrieval latency, compare broad modes/stages, observe widening/partial results/evidence outcomes, and locate whether time is broadly in bootstrap, preparation/routing, embedding, provider namespace operations, reranking, evidence, or rendering.

### Strong privacy and failure isolation

The exact envelope allowlists prohibit query text/hash, argv, namespace/source/document identifiers, content, URL, path, vectors, credentials, provider responses, raw errors, trace propagation, and ambient context. Disabled telemetry is a zero-side-effect no-op. Enabled persistence is private, local, eventual, and best-effort; failures cannot change retrieval behavior.

Current status is healthy but disabled:

- enablement: `disabled` / `not_requested`;
- schema: 2, compatible;
- queue: empty, zero ready/claimed/temporary entries;
- accounting: zero recorded conflicts, replays, rejects, queue-full events, publication failures, write failures, or producer-drop lower bound;
- persisted run snapshot: 20 total;
- store size: 5,517,312 bytes;
- migration backup present.

## What data is actually present

The store contains 20 retrieval observations:

- 12 schema-v1 pipeline-only rows from 2026-08-20, all version `0.6.2.dev2+g796f7384e`;
- 8 schema-v2 command rows from 2026-08-24 through 2026-08-27;
- 7 v2 live pipelines and one explicit-single preview;
- all 8 v2 commands succeeded; and
- latest persisted version is `0.6.4.dev71+g88c829e70`.

There is no telemetry from the current schema-v2 inference-worker implementation/version or either post-worker live A/B because those campaigns deliberately disabled telemetry. Current ordinary telemetry is also not enabled.

The eight v2 rows break down as:

- automatic live: 3;
- explicit-multi live: 2;
- explicit-single live: 2;
- explicit-single preview: 1;
- command errors: 0;
- widened/partial automatic observations: 0.

Selected pre-worker v2 medians are descriptive only because the sample is tiny:

| Mode/stage | Rows | Median ms |
| --- | ---: | ---: |
| automatic command | 3 | 12,762.722 |
| automatic pipeline | 3 | 1,176.982 |
| automatic catalog | 3 | 2,130.466 |
| automatic prepare | 3 | 11,046.451 |
| explicit-multi command | 2 | 11,229.549 |
| explicit-multi pipeline | 2 | 2,192.767 |
| namespace query, all v2 | 11 spans | 894.182 |
| query embed, all v2 | 7 spans | 149.997 |
| rerank, all v2 | 5 spans | 310.187 |
| bootstrap, all v2 | 8 spans | 309.100 |
| render, all v2 | 8 spans | 0.380 |

Nested durations must not be summed. `buoy.retrieve.prepare` contains automatic catalog/model/select spans, and concurrent namespace spans overlap.

## Where telemetry falls short

### 1. The data is stale relative to the system we now care about — critical

The dominant gap is not a missing chart; it is missing current observations. The store has no row from the current default worker that serves both embeddings and cross-encoder scores. The most recent live A/B observed 16.102 s in-process, 6.752 s cold worker, and 2.854 s warm worker, but telemetry was disabled, so none has a stage graph.

Consequences:

- no evidence of current real-world stage distributions;
- no way to explain the current warm 2.854-second command from persisted telemetry;
- no current failure/fallback/lifecycle rate; and
- historical medians describe pre-worker boundaries that moved materially.

### 2. The schema cannot identify worker versus in-process inference — critical

No v2 attribute can record:

- worker selected/eligible versus in-process;
- cold start versus resident reuse;
- schema/implementation compatibility outcome;
- embedding or reranker worker request count/cardinality;
- worker startup/handshake/model-load wait;
- worker fallback occurrence or whether embedding versus reranking failed; or
- bounded worker RSS/lifecycle outcome.

The visible warning is not telemetry. Expected ineligibility, successful worker use, and silent absence of any attempted worker all look the same in persisted rows.

This omission makes comparisons across the worker activation boundary ambiguous even if collection is re-enabled. Adding fields is not a compatible v2 tweak: the producer, strict envelope, writer, views, and migration contract reject unknown attributes, so durable worker dimensions require a focused schema/version decision.

### 3. Current stage names no longer align cleanly with model work — significant

The worker intentionally emits no telemetry. Client spans measure waits around existing operations, but automatic routing now shifts work:

- `buoy.routing.model` mostly covers calibration/factory/adapter construction;
- actual routing query embedding and prototype cross-encoder scoring occur inside `buoy.routing.select`;
- a cold worker's Sentence Transformers/Torch startup can therefore appear as route-selection time rather than model-loading time;
- result-query embedding appears in `buoy.query.embed`;
- result reranking appears in `buoy.rerank`; and
- evidence-triggered scoring may appear inside `buoy.evidence.assess`.

Multiple semantically different `buoy.routing.model` spans share one name and allow only an error attribute. There is no role/subtype for calibration, embedder preparation, reranker preparation, routing embedding, or prototype scoring. A current automatic trace could therefore say “routing select is slow” without telling whether the cause is worker cold start, embedding, cross-encoder scoring, or routing logic.

### 4. Provider telemetry is logical and too coarse for cost/network diagnosis — significant

`buoy.namespace.query` records one logical route-rank operation. One such operation can execute 1–6 Buoy SDK call expressions because of server-RRF compatibility fallback and optional-schema compatibility. The telemetry does not persist those invocation counts, request forms, triggers, or outcomes.

`buoy.routing.catalog` is one broad span. Current automatic catalog code knows content-free successful read metrics, but command-stage attributes allow only an error category, so telemetry does not retain namespace-list page, metadata, or card-query invocation counts.

A private provider-invocation ledger already instruments these application call-expression boundaries, but it is default-off and used only by explicitly scoped canaries. It is not connected to ordinary telemetry. It also cannot see SDK-internal HTTP retries or prove physical wire sends, billing, DNS/TLS, or provider-internal latency.

Consequences:

- cannot tell whether server-RRF fallback is recurring;
- cannot separate one logical namespace span from multiple SDK invocations;
- cannot explain catalog cost by read family;
- cannot estimate application-issued request volume accurately from production telemetry; and
- cannot distinguish provider/network wait from local response parsing/ranking inside a namespace span.

### 5. Failure and fallback observability is mostly theoretical — significant

The schema supports coarse command/pipeline errors, namespace failures, partial outcomes, widening, and evidence states, but the v2 store has eight successes, no command errors, no partials, and no widening. It contains no worker fallback observation at all.

The current error taxonomy is intentionally bounded but coarse. It cannot answer whether a `model_error` came from worker startup, handshake, embed, score, or the in-process fallback. Best-effort persistence also means process death before publication can remove precisely the failure observation of interest; current queue accounting is healthy but does not eliminate that design limit.

### 6. The privacy contract prevents query- and corpus-level product analysis — deliberate tradeoff

There is no query fingerprint, namespace/corpus identity, result identity, click/usefulness signal, or user feedback. That is a strong privacy property, but it means telemetry cannot answer:

- which query classes are slow;
- whether repeated queries improve with worker reuse;
- which corpus/provider path dominates;
- whether retrieved results were useful; or
- whether latency improvements correlate with quality.

Trace IDs permit joining internal operational rows only; they do not provide product context. Any query grouping or feedback feature requires an explicit privacy/retention decision, not a casual attribute addition.

### 7. Sampling and retention are not yet an operational program — moderate

Twenty total observations, only eight command-level rows, are insufficient for percentiles, regression baselines, or version comparisons. Collection is opt-in and currently disabled. There is no automatic retention/purge policy, no dashboard, no alerting, and no release gate. The queue/writer is healthy, but collection continuity and analytical use are manual.

## Priority assessment

1. **Freshness first:** until current ordinary retrieval telemetry is intentionally collected, every instrumentation design discussion is extrapolating from pre-worker traces.
2. **Worker-aware stage semantics next:** current broad spans cannot distinguish backend/coldness/fallback and misattribute automatic cold-start model work to route selection.
3. **Provider invocation accounting next:** persist content-free application-level catalog/content invocation counts separately from logical spans; continue to label them SDK call attempts, not wire requests.
4. **Failure/fallback coverage:** add bounded worker phase/backend/fallback outcomes and ensure hard-failure loss limits are explicit.
5. **Quality/context only by explicit privacy choice:** operational telemetry should not silently acquire query fingerprints, corpus IDs, or feedback.
6. **Retention/analysis later:** percentiles, dashboards, and regression gates are premature until collection is current and dimensions are trustworthy.

## Conclusion

Buoy's retrieval telemetry has a strong privacy model, sound command-versus-pipeline boundary, useful broad stage graph, and currently healthy local persistence. It is good at answering “how long did the command and broad retrieval stages take?” for the small historical sample.

It is currently poor at answering the questions made important by the new architecture: “did this command use a cold or warm worker?”, “which local model operation consumed time?”, “did fallback occur?”, and “how many provider SDK attempts happened beneath each logical catalog/namespace operation?” Most importantly, it is not presently collecting current-worker observations at all.

The immediate deficiency is therefore stale/disabled collection; the primary schema deficiency is missing worker-aware inference and provider-attempt dimensions. The current strict v2 contract means repairing those durable fields should be treated as a focused telemetry-version design, not an ad hoc attribute patch.

## Limits

- The audit is source- and local-store-based on one developer machine.
- Aggregate row counts and medians are descriptive, not representative statistics.
- No current telemetry-enabled retrieval was run, so no store mutation or new observation occurred.
- No attribute JSON or identifier was emitted during the database audit.
- Physical SDK transport retries and provider-internal behavior remain unobserved.
