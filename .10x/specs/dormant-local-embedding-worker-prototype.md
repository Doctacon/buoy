Status: active
Created: 2026-08-27
Updated: 2026-08-27
Decision: .10x/decisions/buoy-prototypes-a-dormant-local-embedding-worker.md
Research: .10x/research/2026-08-27-persistent-local-embedding-worker.md

# Dormant Local Embedding Worker Prototype

## Purpose and scope

Implement and validate a dormant internal POSIX worker that loads Buoy's exact default embedding model once and serves repeated normalized query embeddings over private local IPC. The prototype MUST prove behavior and lifecycle properties without adding a CLI flag, environment activation, default, provider integration, or production retrieval dispatch.

## Fixed prototype identity

The prototype supports exactly:

- protocol schema `1`;
- model `BAAI/bge-small-en-v1.5`;
- revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`;
- precision `float32`;
- current 384-dimensional normalized vectors; and
- POSIX platforms with required filesystem locking and Unix-domain sockets.

Other models, revisions, precisions, dimensions, Windows, TCP, and remote workers are unsupported and MUST fail before spawning or sending text.

## Dormancy contract

No existing CLI, retrieval, routing, apply, catalog, telemetry, configuration, environment variable, or public import path may activate the worker. Existing `SentenceTransformerEmbedder`, `HybridRetriever.from_config`, `MultiNamespaceRetriever.from_configs`, and routing factories retain their current behavior.

The prototype client/worker may be invoked only by focused tests and an explicit provider-free validation harness. No compatibility forwarding module or public API guarantee is created.

## Local paths and permissions

Worker state lives beneath `~/.buoy/inference/` only when the internal prototype is explicitly invoked. The root and identity directory MUST be current-effective-user-owned real directories, mode `0700`, with no symlink traversal. The identity leaf is deterministic from protocol/model/revision/precision and contains no query or credential value.

Lock/state files MUST be regular, one-link, current-user-owned mode-`0600` files. The socket MUST be a Unix socket owned by the current effective user and mode `0600`. Existing nonconforming, replaced, linked, or wrong-type paths fail closed. The implementation MUST never signal a process or remove a socket unless it has validated Buoy ownership and stale-state authority.

## Process lifecycle

1. A client first validates the fixed request identity and private path boundary.
2. It probes an existing socket and requires a compatible readiness handshake.
3. If none is usable, one start lock/lease elects a spawner. Concurrent clients coalesce behind the same worker identity.
4. The detached worker starts from the current absolute Python executable with isolated arguments, closed descriptors, no stdio, a new session, telemetry disabled, offline/local-only model controls, and an exact minimal environment containing no provider credentials.
5. The worker acquires the lifetime lock, validates/creates its private socket, loads the exact local model/revision without download, and publishes readiness only after model construction succeeds.
6. Startup and each request have bounded timeouts. Failure returns one small allowlisted category; raw exception, path, environment, credential, query, stack, and provider detail never crosses IPC or enters state.
7. Requests are processed serially in the first version.
8. The worker exits after 300 seconds with no accepted request. It closes and safely removes only its validated socket/state objects.
9. Crash, client disconnect, stale socket, concurrent spawn, upgrade/protocol mismatch, and interrupted shutdown MUST leave no unverified deletion, orphan authority, or silent fallback.

## IPC protocol

Transport is one request per Unix-domain connection using canonical UTF-8 JSON with an unsigned 32-bit big-endian length prefix. Pickle, eval, arbitrary method names, filesystem paths, provider configuration, credentials, and extension fields are prohibited.

### Request

Exact fields:

```json
{
  "schema_version": 1,
  "operation": "encode",
  "model": "BAAI/bge-small-en-v1.5",
  "revision": "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
  "precision": "float32",
  "texts": ["..."]
}
```

Bounds:

- complete frame at most 1 MiB;
- one through 16 texts;
- every text is a nonempty UTF-8 string of at most 65,536 encoded bytes; and
- no unknown or duplicate JSON fields.

### Success response

Exact fields:

```json
{
  "schema_version": 1,
  "outcome": "success",
  "dimensions": 384,
  "vectors": [[0.0]]
}
```

There MUST be one vector per input text. Every vector has exactly 384 finite numbers and is normalized under the same established Sentence Transformers behavior as `SentenceTransformerEmbedder.encode`.

### Error response

Exact fields:

```json
{
  "schema_version": 1,
  "outcome": "error",
  "error_type": "allowlisted_category"
}
```

Allowlisted categories are limited to protocol error, incompatible worker, model unavailable, encoding failure, busy/timeout, and internal worker failure. Responses contain no raw message.

The client independently validates framing, exact fields, bounds, dimensions, finite values, vector count, and normalization before returning.

## Security and privacy

- Query text and vectors exist only in process memory and transient socket buffers; they MUST NOT be written to state, logs, telemetry, files, argv, environment, or error output.
- Worker children receive no provider credentials and import no provider client intentionally.
- Model loading is exact-revision, offline, and local-only; cache mutation or download fails validation.
- Socket peer effective-user identity MUST be verified where the platform exposes a standard peer-credential API. Where unavailable, the worker relies on validated `0700` directory and `0600` socket ownership; this limit must be documented.
- Malformed or oversized frames are rejected before model invocation.
- Client cancellation or disconnect does not persist or replay a request.

## Acceptance scenarios

### Exact parity

Given the exact cached model, when the same bounded texts are encoded once in-process and once by the worker, then vectors MUST have identical shape and values within the existing numerical parity tolerance, and ordered similarity/ranking checks MUST match.

### Process reuse

Given one worker serves a completed request, when a fresh second client process requests another embedding before five minutes idle, then the same worker identity serves it without another Sentence Transformers import or model construction.

### Startup coalescing

Given multiple clients arrive with no worker, then exactly one compatible worker becomes ready and every accepted client receives a valid response or bounded visible error; duplicate workers do not persist.

### Visible failure

Given startup, handshake, socket, worker, model, timeout, or response failure, then the prototype returns a bounded visible failure and performs no in-process embedding fallback.

### Stale and hostile paths

Given stale, replaced, symlink, hardlink, FIFO, regular-file-as-socket, wrong-owner, wrong-mode, incompatible-protocol, or malformed state, then the prototype fails closed without signaling an unverified process, deleting an unverified object, loading a model, or sending query text.

### Idle exit

Given a ready worker receives no request for 300 seconds under a fake clock or bounded integration observation, then it exits and removes only validated owned runtime objects. A request racing the idle boundary is either accepted completely or receives a bounded visible error.

### Dormancy

Given every established CLI mode and test suite, then no worker path, socket, state, model load, subprocess, or behavior occurs unless the internal prototype API is explicitly invoked.

## Verification

- Unit tests MUST use fake embedder/process/socket/clock boundaries for protocol, paths, lifecycle, concurrency, faults, privacy, and 300-second idle semantics.
- Provider-free integration MUST use the exact cached local model, offline controls, no provider credentials, temporary private home, and bounded process/RSS limits.
- Validation MUST compare exact in-process/worker vectors and ranking behavior, prove fresh-process reuse, and report first versus second client timing separately without creating a release threshold.
- Full Python 3.11 and 3.13 suites, package build, isolated install, CLI/help smoke, ranking/routing validators, and no-worker dormancy audit MUST pass.
- No live provider, catalog, namespace, content, credential, telemetry-store, model-download, global-install, release, publication, or deployment operation is authorized.

## Explicit exclusions

CLI activation or flag; default-on behavior; fallback policy for product retrieval; provider clients or credentials in the worker; full retrieval/routing/reranking service; cross-encoder residency; apply/indexing activation; persistent request queue; batching; worker pools; TCP/HTTP/gRPC; third-party server framework; Windows support; configurable idle timeout; multiple model identities; model download; benchmark/release gate; release or deployment.
