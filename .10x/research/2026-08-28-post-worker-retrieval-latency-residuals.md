Status: done
Created: 2026-08-28
Updated: 2026-08-28

# Post-Worker Retrieval Latency Residuals

## Question

After defaulting compatible retrieval embeddings to the persistent local worker, what do available retained traces and the bounded live A/B identify as the largest remaining latency costs?

## Sources and methods

Inspected:

- `.10x/research/2026-08-24-retrieve-command-outer-latency-attribution.md`;
- `.10x/evidence/2026-08-24-local-telemetry-v2-canary.md`;
- `.10x/evidence/2026-08-24-v0-6-3-installed-telemetry-pilot.md`;
- `.10x/evidence/2026-08-27-experimental-retrieve-embedding-worker-ab.md`;
- `.10x/evidence/2026-08-27-default-retrieve-embedding-worker.md`;
- `.10x/research/2026-08-24-physical-provider-attempt-accounting-options.md`; and
- current `src/buoy_search/retrieval/cross_encoder.py` and CLI/retrieval source.

The canonical local DuckDB was opened read-only. Queries selected only execution/retrieval mode, content-free stage name, duration, and command/pipeline duration from `retrieval_command_runs_v2` and `retrieval_stage_latency_v2`. No trace IDs, attributes, query, namespace, result, URL, credential, error, path, or provider response was emitted or retained. No telemetry writer/management, provider, model, live retrieval, migration, export, or mutation ran.

## Findings

### Evidence boundary

The retained governed traces predate default worker activation. The three-run worker A/B disabled telemetry deliberately, so its warm 5,880.203 ms total has no governed stage breakdown. Old component timings identify durable network/process boundaries but cannot prove their exact post-worker shares. The default implementation itself ran no new live command.

### First compatible command still has a large cold-start tax

Provider-free worker validation observed worker startup between roughly 8.35 and 8.96 seconds in later accepted runs. The live cold-worker command was 8,789.305 ms. The worker amortizes this cost but does not remove it for a one-off command or after five-minute idle exit.

### Automatic catalog reading is the largest repeatedly measured pre-pipeline residual

Three retained automatic traces spent 2,087.009–2,284.867 ms in `buoy.routing.catalog` (median 2,130.466 ms). Current strong-read semantics perform two namespace-list passes, one metadata request, and two card-query passes: at least five catalog SDK call attempts for a complete one-page read. Every automatic command repeats this boundary. Explicit namespace retrieval bypasses it.

### Provider namespace queries dominate the measured retrieval pipeline

Eleven retained `buoy.namespace.query` spans ranged from 457.761 to 2,644.916 ms (median 894.182 ms). Whole live pipeline intervals ranged:

- automatic: 874.174–1,367.358 ms;
- explicit multi: 1,130.154–3,255.380 ms; and
- explicit single: 1,572.189–2,402.982 ms.

Namespace spans can overlap, so their durations must not be summed. Buoy first requests server-side fusion and may make a compatibility fallback request inside the same logical span. Retained telemetry does not expose physical SDK/wire attempts, leaving avoidable compatibility/network work unresolved.

### Cross-encoder startup is now a high-priority unmeasured candidate

Old rerank spans were 294.993–397.010 ms in ordinary multi-namespace cases, but those processes had already imported Sentence Transformers/Torch while constructing the query embedder. With embeddings moved to another process, the CLI's lazy `CrossEncoder` import/model load in `retrieval/cross_encoder.py` may become process-cold again. The old 0.3–0.4 second rerank measurements therefore do not establish current load-plus-score cost. The warm worker A/B's unexplained 5.88-second total is compatible with—but does not prove—this candidate.

### Fixed process startup is now material

Retained command bootstrap was 290.857–454.724 ms (median 309.100 ms). Installed parent-observed wall minus command root was 751.686–788.310 ms. Together these establish roughly one second of fixed process/harness/pre-entry overhead in those observations. This was negligible beside 8–46 second model preparation but is material against a 5.88-second warm command.

### Lower priorities

- Routing selection: 182.512–422.982 ms (median 184.423 ms).
- Rerank after a warmed import stack: median 310.187 ms, but current cold-load attribution is unknown.
- Query embedding in old warmed processes: median 149.997 ms; current warm worker clients measured roughly 16–34 ms and are no longer a leading target.
- Evidence assessment: median 0.150 ms, with one 249.363 ms observation.
- Output rendering: 0.128–0.585 ms.
- In-root uncovered time in the accepted six-row attribution was 22.064–48.295 ms.

## Ranked conclusion

For a cold compatible command, worker/model startup remains the dominant cost.

For repeated warm automatic commands, the strongest measured residuals are:

1. repeated strong remote catalog read (~2.1–2.3 s);
2. provider namespace-query/pipeline latency (~0.9 s median per logical namespace span, up to 2.6 s; ~0.9–3.3 s whole pipeline depending mode);
3. potentially process-cold cross-encoder import/model loading, currently not separately measured post-worker; and
4. roughly one second of process/bootstrap/near-shell overhead in retained installed observations.

Routing selection and warmed rerank scoring are secondary. Rendering, evidence bookkeeping in ordinary cases, wrapper construction, and warm embedding IPC are not worthwhile first targets.

## Recommended next investigation order

1. Add provider-free, fresh-client timing around cross-encoder import, model construction, and score separately now that query embedding is remote. Do not infer this from old rerank spans.
2. Attribute the remote catalog's five minimum strong-read call families and evaluate a semantically safe validated snapshot/revision reuse policy before changing consistency.
3. Instrument physical provider attempts beneath logical namespace spans to learn whether server-fusion compatibility fallback is occurring and what network critical path remains.
4. Only after those boundaries, consider reducing CLI/bootstrap imports or keeping more of the local inference stack resident.

No optimization implementation, new live campaign, catalog cache policy, provider-attempt policy, or cross-encoder worker expansion is authorized by this research.

## Limits

- Retained governed traces are pre-worker and from one Darwin arm64 host.
- The post-worker A/B contains only three ordered live observations and telemetry was disabled.
- Provider/network timing is confounded; no percentile, causal decomposition, SLA, or release threshold is established.
- Namespace span duration is logical-operation latency, not wire-attempt count.
- No CPU/device utilization, packet trace, peak RSS, or post-worker cross-encoder subspan exists.
