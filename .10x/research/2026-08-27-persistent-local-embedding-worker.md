Status: active
Created: 2026-08-27
Updated: 2026-08-27

# Persistent Local Embedding Worker

## Question

What is the smallest behavior-preserving way to keep Buoy's embedding runtime alive across short-lived retrieval CLI invocations, given current latency evidence, privacy constraints, platform support, and existing process-lifecycle machinery?

## Sources and methods

### Project authority and source

Inspected:

- `.10x/research/2026-08-24-retrieve-command-outer-latency-attribution.md`;
- `.10x/research/2026-08-27-current-provider-free-retriever-construction-findings.md`;
- `.10x/research/2026-08-27-ordinary-sentence-transformers-import-diagnostic.md`;
- `.10x/decisions/buoy-uses-a-private-local-telemetry-writer.md`;
- `.10x/decisions/buoy-defaults-local-assets-to-one-user-home.md`;
- `.10x/knowledge/isolated-tests-own-lazy-model-dependencies.md`;
- current embedding and retrieval seams in `src/buoy_search/indexing/chunker.py`, `src/buoy_search/retrieval/retriever.py`, `src/buoy_search/retrieval/routing.py`, `src/buoy_search/catalog/local.py`, and `src/buoy_search/cli/main.py`; and
- detached-process election, heartbeat, lease, idle-exit, and spawn mechanics in `src/buoy_search/telemetry/queue.py` and `src/buoy_search/telemetry/writer.py`.

### External open-source references

- Python standard-library socket documentation: https://docs.python.org/3/library/socket.html
- Hugging Face Text Embeddings Inference: https://github.com/huggingface/text-embeddings-inference
- llama.cpp server: https://github.com/ggml-org/llama.cpp/tree/master/tools/server
- vgi-rpc Unix socket launcher: https://vgi-rpc-typescript.query.farm/guides/launcher/

The two inference servers demonstrate the established model-serving pattern—load once, accept repeated bounded requests—but are far broader than Buoy needs. The Unix-socket launcher demonstrates spawn-or-reuse, deterministic worker identity, readiness/version handshake, duplicate-start prevention, and idle lifecycle patterns. Python's standard library provides Unix-domain sockets without a new dependency.

## Findings

### The reusable object should be the embedder, not the retriever

The dominant process-cold/host-warm boundary is the Sentence Transformers import/runtime initialization at 7.63–7.84 seconds. Post-import model construction measured 0.31–0.44 seconds, and fake retriever/configuration wrapping remained below one millisecond.

`HybridRetriever` and `MultiNamespaceRetriever` combine a local embedder with provider namespace clients and environment-only credentials. Keeping complete retrievers alive would force provider credentials, clients, query transport, provider lifecycle, and potentially stale namespace configuration into the daemon. That is unnecessary and expands the trust boundary.

A smaller worker owns only the local `SentenceTransformer` embedder. The CLI retains provider credentials and provider queries. It sends one or more texts plus an exact model/precision identity to the worker and receives normalized vectors. Query text necessarily crosses local IPC but is never written to disk.

### Routing and retrieval currently use the same default model

The default retrieval model and pinned routing model are both `BAAI/bge-small-en-v1.5`; routing additionally binds revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` and local-only loading. Automatic retrieval therefore can reuse one resident model for both routing-query and retrieval-query embeddings when model, revision, and precision contracts match. The initial version should not cache provider clients or cross-encoder rerankers.

### Existing writer mechanics are reusable, but its queue is not

Buoy already has tested POSIX detached-process patterns: start lease, lifetime election, heartbeat, stale-state handling, minimal child environment, `start_new_session=True`, and bounded idle exit. Those mechanics are useful.

The telemetry writer's durable filesystem queue is wrong for embedding requests because query text and vectors must not be persisted. Embedding IPC should be transient request/response over a private Unix-domain socket. A crash fails the request; it does not leave a recoverable sensitive payload.

### A Unix socket is the minimum viable transport

A private socket under the canonical one-user `~/.buoy` home avoids TCP ports, network exposure, and new dependencies. The owning directory should be mode `0700` and the socket mode `0600`; path, ownership, file type, and peer identity should be validated where the platform exposes peer credentials. One request per connection keeps framing and cleanup simple.

Socket permissions protect against other users, not arbitrary same-UID processes. The worker therefore must accept only a tiny exact protocol, bounded text/count/payload sizes, exact model identity, and no file paths, provider configuration, credentials, arbitrary method names, pickle, or code-loading input.

### Stale worker identity must fail explicitly

The client and worker need an exact protocol version plus package/runtime/model identity handshake. A stale or incompatible worker must not silently serve. The client may start a compatible replacement only after proving the old socket is stale and safely removing its own stale socket object; it must never signal or delete an unverified process.

### First-request latency remains; later requests are the target

The first request still pays worker spawn, import, and model construction. The gain applies to subsequent retrieval commands during the worker's lifetime. Existing evidence does not authorize a latency target. A prototype should prove exact vector parity and a parent-observed second-request improvement rather than claim a percentile or release gate.

## Recommended architecture

Build an opt-in experimental embedding worker, not a full retrieval daemon:

1. POSIX-only Unix-domain socket under `~/.buoy/inference/`.
2. One elected detached worker per exact model/revision/precision/protocol identity.
3. Worker loads the exact pinned local model once under offline/local-only behavior.
4. Exact bounded JSON request/response protocol; no pickle and no durable queue.
5. Requests contain only protocol identity, model identity, precision, and bounded text array; responses contain normalized finite vectors or a small allowlisted error category.
6. Provider credentials and clients remain entirely in the CLI process.
7. One request per connection, serialized model execution initially; no speculative batching or pool.
8. Explicit readiness handshake, bounded startup/request timeouts, heartbeat/state, and idle exit.
9. On worker failure, the experimental path fails visibly rather than silently falling back and hiding lifecycle defects. Existing in-process behavior remains available when the experiment is disabled.
10. First acceptance is provider-free: exact vector parity with current in-process embedding, concurrent spawn coalescing, crash/stale-socket recovery, privacy/path hardening, and proof that a second process avoids Sentence Transformers import/model construction.

This is smaller than adopting TEI, llama.cpp server, HTTP, gRPC, FastAPI, Redis, a generic job queue, or a third-party daemon framework. Those add deployment and protocol obligations without satisfying a requirement the standard library cannot meet.

## Trade-offs

### Benefits

- Amortizes the observed dominant import/runtime cost across retrieval commands.
- Preserves current embedding model and ranking semantics.
- Keeps provider credentials and provider clients out of the worker.
- Reuses established process-election/lifecycle concepts.
- Adds no dependency or listening network port.

### Costs and risks

- Adds a local background process, IPC protocol, stale-worker/version lifecycle, private query transport, and approximately 0.5 GB observed resident memory while warm.
- First request remains slow.
- Same-user processes can potentially access a same-user socket unless stronger peer/application authentication is added.
- MPS/process crashes, client interruption, upgrade races, and idle shutdown need explicit behavior.
- A long idle timeout improves reuse but retains memory longer.

## Execution-critical decisions still requiring owner ratification

1. Activation: opt-in experiment or immediate default.
2. Idle lifetime/resource posture.
3. Failure behavior: visible failure or in-process fallback.
4. Platform boundary: POSIX-only initial implementation and behavior elsewhere.
5. Scope: embedding only, or routing/retrieval/provider/reranker expansion. This research recommends embedding only.

## Limits

No worker prototype, socket, model process, provider operation, benchmark, source change, or external state change was created during this research. External examples establish patterns, not direct compatibility or performance guarantees for Buoy.
