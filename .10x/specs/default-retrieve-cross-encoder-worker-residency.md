Status: active
Created: 2026-08-28
Updated: 2026-08-28
Decision: .10x/decisions/buoy-keeps-the-pinned-cross-encoder-resident-in-the-existing-local-worker.md
Depends-On: .10x/specs/default-retrieve-embedding-worker.md
Evidence: .10x/evidence/2026-08-28-provider-free-cross-encoder-boundaries.md

# Default Retrieve Cross-Encoder Worker Residency

## Purpose and scope

Extend the existing default-compatible retrieve embedding worker with one private, bounded scoring operation so routing, evidence assessment, and multi-namespace reranking reuse the worker's resident Sentence Transformers/Torch runtime and lazily resident pinned MiniLM cross-encoder.

This specification governs cross-encoder residency only. `.10x/specs/default-retrieve-embedding-worker.md` continues to govern embedding selection, CLI exposure, worker lifecycle, and the base fallback contract. Where that earlier spec describes an embedding-only worker or excludes cross-encoder residency, this focused extension governs the added score operation.

## Eligibility and CLI contract

Cross-encoder worker scoring MUST be available only through the same command session selected by the existing embedding-worker eligibility contract:

- no `--no-embedding-worker` flag;
- supported POSIX capability;
- configured embedding model exactly `BAAI/bge-small-en-v1.5`;
- configured embedding precision exactly `float32`; and
- exact current worker protocol and complete embedding/reranker identity.

`--no-embedding-worker` MUST force both embeddings and cross-encoder scoring through their established in-process implementations. It MUST create no worker state, process, import, or IPC connection.

Custom embedding models, float16, unsupported platforms, and incompatible worker identity MUST keep cross-encoder scoring in-process with no worker warning or worker side effect. No new CLI flag is introduced, and the existing flag name and help compatibility remain unchanged.

## Protocol identity and lifecycle

The scoring-capable worker MUST use a new protocol/schema identity and a distinct identity directory from the embedding-only protocol. No protocol forwarding, alias, downgrade, or mixed-version request is allowed.

The ready handshake and durable content-free state MUST bind:

- worker schema and implementation identity;
- package and Python identity;
- embedding model, revision, precision, and dimensions; and
- cross-encoder model, revision, CPU device, max length 512, batch size 8, local-only loading, safetensors requirement, and remote-code-disabled behavior.

An older worker MUST fail compatibility validation before any query or passage crosses IPC. Existing same-user path, permission, socket, lock, election, stale-cleanup, timeout, and peer-verification controls remain mandatory.

The embedding model MAY remain eagerly loaded as today. The cross-encoder MUST be constructed lazily on the first accepted score request and reused for later accepted score requests until the existing five-minute idle exit. A valid encode or score request MUST refresh the accepted-request idle timer; invalid connections or malformed requests MUST NOT.

The worker MUST remain serial. Pools, request batching across clients, parallel model inference, and additional services are excluded.

## Score request contract

A score request MUST contain exactly:

- the current schema version;
- operation `score`;
- the exact cross-encoder model and revision;
- one non-empty UTF-8 query of at most 65,536 bytes; and
- between 1 and 108 non-empty UTF-8 passages, each at most 65,536 bytes.

The 108-passage maximum is the existing governed automatic-routing bound: 12 shortlisted cards times one base passage plus up to eight routing evidence/example passages. The complete canonical framed request MUST be at most 8,388,608 bytes. Duplicate JSON fields, unknown fields, non-canonical identity, invalid UTF-8, booleans where numbers are expected, empty/out-of-range collections, and oversized values MUST be rejected with the bounded protocol vocabulary.

The worker MUST invoke the unchanged pinned production scoring behavior:

- `cross-encoder/ms-marco-MiniLM-L-6-v2`;
- revision `c5ee24cb16019beea0893ab7796b1df96625c6b8`;
- CPU;
- max length 512;
- batch size 8;
- local files only;
- safetensors; and
- no remote code.

A successful score response MUST contain exactly the schema version, success outcome, cross-encoder identity, and one finite numeric score per input passage in input order. It MUST contain no query, passage, token, vector, model path, timing, PID, or raw exception.

Wrong score count, non-numeric/boolean score, non-finite score, model-load failure, inference failure, timeout, transport failure, and malformed response MUST become bounded value-redacted worker errors. Raw model/cache paths, inputs, scores, frames, environment values, credentials, exceptions, and tracebacks MUST NOT cross the public error boundary.

Existing encode request/vector semantics MUST remain byte-for-byte and numerically unchanged except for the required new protocol identity and framing ceiling.

## Retrieve integration

One command-scoped worker-backed reranker adapter MUST be shared across every production cross-encoder seam used by an eligible retrieve command:

1. automatic prototype-routing shortlist scoring;
2. automatic evidence assessment when existing reranker scores are unavailable; and
3. bounded multi-namespace result reranking, including widening.

The adapter MUST implement the existing `CrossEncoderReranker.score(query, passages)` seam. Routing prototype generation, passage formatting, candidate cardinality, deduplication, model score interpretation, thresholds, margins, RRF fusion, namespace coverage, evidence logic, provider ordering, output, and telemetry semantics MUST remain unchanged.

The command MUST NOT send provider credentials, client objects, namespace handles, catalog objects, complete result objects, routing decisions, evidence decisions, or telemetry objects to the worker. Only the already formatted bounded query/passages needed for the exact score call may cross IPC.

Single-namespace retrieval, named routes, dry-runs, or other paths that do not invoke production cross-encoder scoring MUST NOT issue a score request or lazily load the cross-encoder. Existing embedding behavior for those paths remains unchanged.

## Privacy and no persistence

Queries, passages, vectors, and scores MUST exist only in transient process memory and private socket frames. They MUST NOT be written to readiness/error state, lock files, logs, telemetry, caches, temporary files, durable queues, crash artifacts created by Buoy, or worker directory names.

The worker child environment MUST remain credential-free, telemetry-disabled, and offline. It MUST import no provider client, catalog service, retrieval orchestration, telemetry store/writer, or rendering module as a consequence of scoring.

The worker MUST retain only model/runtime objects between requests. It MUST NOT retain the most recent query, passage list, score list, or request frame after the response is completed.

## Command-wide fallback

Embedding and scoring MUST share one command-wide worker failure latch and exactly-one-warning policy.

On the first worker encode or score failure, the command MUST:

1. emit the existing bounded embedding-worker fallback warning exactly once;
2. discard raw worker detail;
3. perform the failed local operation through the unchanged in-process implementation;
4. use in-process implementations for every later embedding or scoring operation in that command; and
5. preserve established phase-correct errors if the in-process fallback also fails.

A score fallback MAY occur after provider content reads because local scoring has no provider or durable side effect. It MUST reuse the already formatted query/passages and MUST NOT repeat any catalog, namespace, or content operation. A lost worker response MAY be recomputed in-process; no worker score request may be retried over IPC after its first request byte is sent.

If embedding fails first, later reranker loads/scores MUST go directly in-process without another worker attempt or warning. If scoring fails first, later embedding operations MUST go directly in-process. Expected ineligible configurations MUST NOT emit the fallback warning.

## Acceptance scenarios

### Automatic prototype route

Given an eligible automatic query requiring prototype reranking, when routing scores its shortlist, then the worker lazily loads the exact cross-encoder, returns parity scores, and the CLI process does not import or construct CrossEncoder.

### Reuse across one command

Given automatic routing followed by multi-namespace retrieval/evidence scoring, when more than one score seam is invoked, then one command adapter and one resident worker model serve all calls without changing scores, ordering, thresholds, evidence, provider operations, or output.

### Warm reuse across commands

Given a prior accepted score request less than five minutes ago, when another eligible command scores, then the same worker/model may be reused and the accepted request refreshes idle lifetime.

### No-score path

Given an eligible command whose route/retrieval requires no cross-encoder score, when it completes, then embedding may use the worker but the cross-encoder is never constructed.

### Opt-out or ineligible configuration

Given opt-out, custom embedding model, float16, unsupported platform, or incompatible protocol identity, when scoring is needed, then the established in-process reranker is used without worker scoring state or warning.

### Worker scoring failure

Given a worker score failure before or after provider reads, when in-process scoring succeeds, then exactly one existing warning is emitted, ranking/output match the established path, and no provider operation repeats. If in-process scoring also fails, the established bounded phase error is returned.

### Privacy

Given routing, evidence, or result passages, when worker scoring completes or fails, then no query, passage, score, result, credential, path, or raw exception remains in worker files/state/logs or public diagnostics.

## Verification

- Strict protocol tests for new identity, encode/score tagged schemas, duplicate/unknown fields, 1/108/109 cardinalities, per-value and aggregate frame limits, finite score validation, timeout, truncation, lost responses, and bounded errors.
- Worker tests proving lazy one-time reranker construction, same-process reuse, idle refresh only after valid accepted requests, serial behavior, no retained request data, and complete cleanup.
- Exact provider-free score parity for 1, 24, 49, and 108 pairs against the unchanged in-process reranker; exact downstream route/ranking/evidence/output parity, including the source-governed 108-passage automatic-routing case.
- CLI tests for eligible/ineligible/opt-out and automatic/explicit/dry-run/single/multi/widening paths.
- Failure matrix proving one warning, shared command failure latch, in-process fallback, no IPC retry after request start, no duplicated catalog/content operation, and phase-correct double-failure taxonomy.
- Import/process/filesystem tests proving no CLI-process CrossEncoder import on successful eligible scoring, no lazy worker reranker on no-score paths, and complete worker dormancy for opt-out/ineligible/non-retrieve paths.
- Credential/module/no-persistence inspections and private socket/path permission tests.
- Existing embedding-worker, routing, retrieval, evidence, telemetry, output, packaging, isolated-install, and full Python 3.11/3.13 suites pass.
- Provider-free validation only; no live provider command is required or authorized.
- Independent review passes before closure.

## Explicit exclusions

Changing cross-encoder model/revision/device/precision/max length/batch size; changing routing, candidate, ranking, evidence, threshold, fusion, coverage, provider, output, warning text, telemetry schema, or five-minute idle semantics; custom-model/float16/Windows worker support; separate reranker service; eager reranker loading; worker pools/concurrency; provider credentials/clients or orchestration in worker; durable request/result cache; apply/index/evals activation; live A/B; percentile/SLA/release gate; global installation; release; deployment; publication.
