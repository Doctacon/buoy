Status: superseded
Created: 2026-08-27
Updated: 2026-08-27
Superseded-By: .10x/specs/default-retrieve-embedding-worker.md
Decision: .10x/decisions/superseded/buoy-connects-the-embedding-worker-behind-an-experimental-retrieve-flag.md
Depends-On: .10x/specs/dormant-local-embedding-worker-prototype.md

# Experimental Retrieve Embedding Worker

## Purpose and scope

Connect the reviewed local embedding worker to `buoy retrieve` behind one explicit experimental flag, then run a bounded live A/B to determine whether cross-process reuse materially reduces real repeated-command latency without changing routing, embeddings, retrieval, ranking, output, errors outside the selected backend, or credential boundaries.

## CLI contract

`buoy retrieve` MUST accept:

```text
--experimental-embedding-worker
```

The flag MUST NOT exist on other commands. Help MUST describe it as a POSIX experimental path that reuses the exact pinned local embedding model for automatic routing and retrieval. Omitting it MUST preserve established behavior exactly and MUST create no inference-worker path, file, socket, process, import, or connection.

The flag is not a compatibility promise. No environment alias or configuration-file activation is added.

## Supported configuration

The enabled path supports exactly the worker identity governed by `.10x/specs/dormant-local-embedding-worker-prototype.md`:

- model `BAAI/bge-small-en-v1.5`;
- revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`;
- precision `float32`;
- 384 normalized dimensions; and
- supported POSIX worker capability.

If the flag is combined with another embedding model or precision, or capability is unavailable, the command MUST fail with a bounded user-facing configuration/model error before model load, query IPC, remote catalog/content requests, or credential value handling. Float16 and arbitrary model identities remain unsupported by the worker experiment.

## Routing and retrieval behavior

For automatic routing, the worker-backed embedder MUST replace only the local routing embedder. All routing prefixes, cards, vectors, calibration, thresholds, reranking, tie-breaking, fanout, catalog reads, error behavior, and selected-card order remain unchanged.

For live retrieval, the same worker-backed embedder instance contract MUST replace only `SentenceTransformerEmbedder`. Provider client construction, credentials, namespaces, ANN/BM25 requests, RRF, cross-encoder reranking, evidence assessment, widening, failure handling, ranking, citations, output, and telemetry semantics remain unchanged.

Explicit namespace retrieval uses the worker only for the retrieval-query embedding. Automatic dry-run may use it for semantic routing but performs no content retrieval. Explicit dry-run performs no embedding and MUST NOT start the worker merely because the flag is present.

The retrieval factories MAY gain an optional injected embedder seam. Existing callers and calls without an injected embedder MUST retain current construction and behavior.

The worker path MUST NOT silently fall back in-process. A worker failure after request transmission MUST NOT replay the embedding request.

## Error behavior

Worker configuration/capability/startup/model/IPC/protocol errors MUST be converted to bounded existing CLI-facing configuration, model, routing, or retrieval errors according to the phase where they occur. They MUST NOT be mislabeled as provider failures, expose raw exceptions, query text, paths, environment values, credentials, PIDs, frames, or stack traces, or change no-flag errors.

## Telemetry and output

The experimental backend MUST retain current span ordering and model/precision identity. No query text, vector, credential, socket path, PID, or raw worker error is added to telemetry. If a backend marker is necessary for A/B attribution, it MUST be a bounded low-cardinality value on an existing governed local span and covered by the active telemetry specification; otherwise the A/B harness records backend identity outside command telemetry.

Successful text and JSON output MUST be equivalent between baseline and worker runs for equivalent provider responses. The flag itself MUST NOT appear in retrieval result payloads.

## Live A/B procedure

After unit/provider-free validation and independent review of the dormant worker, run exactly three sequential automatic live retrieval commands from the same source/runtime/environment:

1. baseline without the flag;
2. cold worker with the flag, starting from no live compatible worker; and
3. warm worker with the flag while the same worker remains ready.

Fixed query:

```text
How is approximate vector recall evaluated?
```

Controls:

- existing `TURBOPUFFER_API_KEY` and region may be read only by established CLI/provider code;
- `BUOY_TELEMETRY=off`, OpenTelemetry disabled, model telemetry disabled, and no credential output;
- exact model cache is present and offline/local-only worker controls remain active;
- JSON command output and stderr go only to restrictive temporary files outside the repository and are deleted after redacted comparison;
- retain no hit text, URLs, namespace identifiers, catalog content, query output, credential value, or raw provider response in `.10x/`;
- retain wall time, governed span timings if available without enabling telemetry, exit status, result/hit counts, redacted deterministic hashes, selected-route equality boolean, worker PID-reuse boolean, RSS, source/cache manifests, and idle cleanup;
- perform no catalog/content writes, indexing, apply, release, deployment, installation, or publication; and
- wait for or otherwise safely observe the fixed five-minute idle exit and validated cleanup without signaling an unverified process.

Because provider/catalog state and network timing can vary, exact output mismatch MUST be investigated rather than automatically attributed to the worker. Three runs establish a bounded local decision artifact, not a percentile, SLA, release gate, or benchmark certification.

## Acceptance scenarios

### Default unchanged

Given any established retrieve invocation without the flag, when it runs or fails, then worker code is not imported/activated and behavior, output, provider calls, telemetry, and errors match the pre-change path.

### Automatic worker reuse

Given the flag and compatible default configuration, when automatic retrieval runs, then routing and retrieval embeddings use the same resident worker identity and no in-process Sentence Transformers model is constructed in the CLI process.

### Explicit worker reuse

Given the flag and one or more explicit namespaces, when live retrieval runs, then the query is embedded exactly once through the worker and established namespace/provider behavior follows.

### Dry-run boundaries

Given automatic dry-run plus the flag, semantic routing may use the worker but no content query occurs. Given explicit dry-run plus the flag, no worker starts and no embedding/provider operation occurs.

### Failure visibility

Given incompatible config, unsupported capability, worker startup/model/IPC/protocol failure, or idle race, then the command returns a bounded phase-correct user-facing error, sends no credential to the worker, performs no hidden in-process fallback, and performs no post-request replay.

### Live parity and latency evidence

Given the fixed three-run procedure, then retained evidence reports baseline/cold/warm wall and available local phase timings separately, compares redacted route/result shape, proves cold/warm worker identity behavior, and states provider/network confounding and all mismatches.

## Verification

- Focused CLI parser/dispatch tests for flag locality, no-flag dormancy, supported config, dry-run behavior, routing and retrieval injection, exact call counts, errors, output, and telemetry privacy.
- Retriever factory tests proving optional injection and unchanged default construction.
- Existing worker tests remain passing on Python 3.11 and 3.13.
- Full Python 3.11 and 3.13 suites, validators, package builds, isolated install/help/import smoke, diff hygiene, and no-staged-files checks pass.
- Independent post-change review passes before any default-on recommendation.
- Live A/B follows the exact bounded procedure and produces a redacted evidence record.

## Explicit exclusions

Default-on activation; environment activation; fallback; worker support for custom model/precision; cross-encoder residency; provider client or credentials in the worker; worker pools/batching; apply/indexing/evals activation; Windows; release gate; installation into the user's global tool; release; deployment; publication; automatic promotion based only on three runs.
