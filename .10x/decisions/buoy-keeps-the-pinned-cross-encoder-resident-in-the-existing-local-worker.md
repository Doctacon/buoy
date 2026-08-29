Status: active
Created: 2026-08-28
Updated: 2026-08-28

# Buoy Keeps the Pinned Cross-Encoder Resident in the Existing Local Worker

## Context

Default compatible retrieval already keeps `BAAI/bge-small-en-v1.5` resident in a private five-minute local worker. Provider-free fresh-process measurement then isolated the pinned cross-encoder boundaries:

- Sentence Transformers/CrossEncoder import and transitive runtime initialization: 7,460.980291–7,928.117125 ms;
- post-import pinned model construction: 72.913000–88.451625 ms;
- first one-pair score: 24.548709–30.563000 ms;
- warm 24-pair score: 45.996500–53.246459 ms; and
- warm 49-pair score: 88.842917–103.686750 ms.

The import/runtime boundary dominated every retained observation. The existing embedding worker already imports Sentence Transformers and Torch, so a cross-encoder loaded in that process can reuse the resident runtime rather than starting another service or importing the stack again in each CLI process.

Cross-encoder scoring is local and side-effect free, but passages may contain provider-returned content. Moving scoring across the private socket therefore requires explicit cardinality, frame, privacy, fallback, and no-persistence rules. Provider credentials, clients, catalog operations, namespace requests, ranking orchestration, evidence decisions, telemetry storage, and rendering must remain outside the worker.

## Decision

For exact worker-eligible `buoy retrieve` commands, extend the existing private local worker protocol with one bounded cross-encoder score operation.

The worker will:

- continue serving exact embedding requests;
- advertise and validate the exact pinned cross-encoder identity in its handshake;
- lazily construct `cross-encoder/ms-marco-MiniLM-L-6-v2` revision `c5ee24cb16019beea0893ab7796b1df96625c6b8` on the first accepted score request;
- keep that model resident until the existing five-minute accepted-request idle exit;
- score at most 108 query/passage pairs serially—the existing governed maximum of 12 shortlisted cards times one base plus eight evidence passages—using unchanged CPU, max-length, batch-size, safetensors, local-only, and no-remote-code behavior; and
- return only one validated finite score per passage.

Use the same command-wide worker eligibility, opt-out, failure latch, warning, and in-process fallback policy as embedding. `--no-embedding-worker`, custom embedding models, float16, and unsupported platforms keep both embeddings and cross-encoder scoring in-process. A worker scoring failure may be retried in-process because local inference has no provider or durable side effect; it must not repeat catalog or content operations.

Queries, passages, vectors, and scores remain transient memory/IPC data. The worker must not log, persist, cache, or place them in readiness/error state. Provider credentials and clients remain excluded from the child environment and process.

The protocol identity will be versioned so an older embedding-only worker cannot be mistaken for a scoring-capable worker. No compatibility forwarding protocol will be retained.

## Alternatives considered

- **Keep scoring in every CLI process:** rejected because it repeats the measured 7.5–7.9 second dominant boundary.
- **Start a separate reranker worker:** rejected because it adds another lifecycle, socket, lock set, process, and runtime footprint while forfeiting reuse of the existing worker's imported Sentence Transformers/Torch runtime.
- **Eagerly load both models at worker startup:** rejected because embedding-only and single-namespace commands do not need the cross-encoder; lazy construction preserves their current startup boundary.
- **Move routing/retrieval orchestration or provider clients into the worker:** rejected because it expands credentials, side effects, privacy exposure, protocol complexity, and failure semantics without addressing the measured local-inference bottleneck.
- **Change or quantize the reranker:** rejected because model/ranking parity is required and startup, not warmed scoring, is dominant.

## Consequences

Repeated eligible routing, evidence assessment, and multi-namespace reranking can avoid process-cold CrossEncoder imports. The first score in a newly started embedding worker should pay only incremental model construction/inference after the runtime is resident, but this decision sets no latency target or SLA.

The worker protocol and readiness identity become broader and must be strictly versioned. Provider-derived passages will cross one same-user private Unix socket, increasing transient local IPC exposure, but no external boundary or durable storage is introduced. Worker memory can increase after the first score request and remains allocated until idle exit. Commands that never score do not load the cross-encoder.

Worker failure remains visible and recoverable through the established single warning and in-process path. No live campaign, release, deployment, or publication is authorized by this decision.

On 2026-08-28 independent implementation review corrected the earlier 49-pair assumption: source and a named regression test already govern a 108-passage automatic-routing call. The owner explicitly ratified raising the worker request maximum to 108 rather than chunking or accepting fallback. This does not add scoring work; it keeps the existing bounded call resident.
