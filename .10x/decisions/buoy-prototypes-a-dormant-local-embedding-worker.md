Status: active
Created: 2026-08-27
Updated: 2026-08-27

# Buoy Prototypes a Dormant Local Embedding Worker

## Context

Current traces attribute most retrieval startup latency to repeated Sentence Transformers import/runtime initialization in each short-lived CLI process. Provider-free measurements found 7.63–7.84 seconds for that import boundary, 0.31–0.44 seconds for post-import model construction, and negligible wrapper construction. One ordinary import profile points to broad Transformers machinery and Torch native/runtime initialization.

Changing the model/import stack risks embedding and ranking parity. A resident process can instead amortize initialization while preserving the current model. Research at `.10x/research/2026-08-27-persistent-local-embedding-worker.md` found that a private standard-library Unix-domain socket and Buoy's existing detached-process lifecycle patterns are the smallest viable mechanism.

The owner directed Buoy to try keeping the process alive, selected a five-minute idle lifetime, visible failure, and embedder-only scope, and correctly deferred product activation until the prototype is tested.

## Decision

Build a dormant, provider-free local embedding-worker prototype with no CLI activation path.

- The worker owns only the exact local embedder; provider credentials, provider clients, namespace queries, rerankers, results, and telemetry remain outside it.
- It uses a private POSIX Unix-domain socket under the canonical one-user Buoy home, an exact bounded non-pickle protocol, one request per connection, one elected worker per exact protocol/model/revision/precision identity, and serialized embedding execution.
- The worker exits after five minutes idle.
- Startup, handshake, IPC, identity, or worker failures are visible; the prototype has no silent in-process fallback.
- Production CLI retrieval remains byte-for-byte behaviorally unchanged because no flag, environment switch, default, or dispatch path activates the prototype.
- Activation, default behavior, fallback policy, rollout, and latency gates require separate post-prototype owner decisions.

## Alternatives considered

- Default-on worker: rejected before parity and lifecycle evidence exists.
- Opt-in CLI flag immediately: deferred because even opt-in product activation should follow prototype evidence.
- Full retrieval daemon: rejected because it unnecessarily moves credentials, provider clients, namespace state, and results into the worker.
- Replace Sentence Transformers/import stack: rejected before proving a behavior-preserving lifecycle solution.
- TEI, llama.cpp server, HTTP/gRPC, or a third-party daemon framework: rejected as unnecessary dependencies and deployment surfaces for one local embedder.
- Silent in-process fallback: rejected because it would hide worker defects and reintroduce the measured startup cost during evaluation.

## Consequences

The prototype can prove exact vector parity, process reuse, lifecycle safety, private transport, and second-client improvement without changing retrieval behavior. It adds dormant internal code and tests, plus provider-free validation that may start a temporary local model worker. If results are poor, the prototype can be removed without compatibility obligations. If results pass, a later specification must define activation and user-visible failure/resource behavior.
