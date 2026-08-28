Status: active
Created: 2026-08-27
Updated: 2026-08-27
Decision: .10x/decisions/buoy-defaults-compatible-retrieve-embeddings-to-the-local-worker.md
Supersedes: .10x/specs/superseded/experimental-retrieve-embedding-worker.md
Depends-On: .10x/specs/dormant-local-embedding-worker-prototype.md

# Default Retrieve Embedding Worker

## Purpose and scope

Make the reviewed local embedding worker the default backend for compatible `buoy retrieve` routing and retrieval embeddings, preserve in-process behavior for custom/unsupported configurations, provide an explicit opt-out, and visibly fall back in-process if an eligible worker attempt fails.

## CLI contract

`buoy retrieve` MUST expose:

```text
--no-embedding-worker
```

The flag MUST exist only on `retrieve` and MUST force the complete established in-process routing/retrieval embedding path. It MUST create no inference-worker directory, file, socket, process, import, or IPC connection.

The superseded `--experimental-embedding-worker` flag MUST be removed rather than retained as an alias. It was explicitly experimental and not a compatibility promise. Help and retrieval documentation MUST describe default eligibility, five-minute idle memory lifetime, opt-out, custom/unsupported behavior, and visible fallback.

## Default eligibility

The worker MUST be selected automatically only when all are true:

- no `--no-embedding-worker` flag;
- POSIX capability required by the reviewed worker is available;
- configured model is exactly `BAAI/bge-small-en-v1.5`;
- configured precision is exactly `float32`; and
- installed worker protocol/revision/dimensions match the active worker specification.

Custom model, float16, or unsupported-platform retrieval MUST use the established in-process backend directly. This expected selection MUST NOT emit a fallback warning or create worker state.

Eligibility selection MUST occur without reading credential values or performing provider/catalog/content operations. Worker imports remain lazy: ordinary non-retrieve commands, retrieve opt-out, and ineligible configurations MUST NOT import the worker module.

## Routing and retrieval behavior

An eligible automatic retrieval command MUST use one worker-backed adapter for semantic routing and final retrieval-query embedding. All prefixes, cards, calibration, reranking, thresholds, tie-breaking, fanout, provider calls, evidence assessment, ranking, output, and telemetry semantics remain unchanged.

An eligible explicit live namespace command MUST use the worker exactly once for the retrieval-query embedding.

Automatic dry-run may use the default worker for semantic routing but performs no content retrieval. Explicit dry-run performs no embedding and MUST NOT start the worker. Opted-out dry-runs preserve the established in-process behavior.

Retriever factories retain optional injection seams and unchanged omitted-argument behavior.

## Visible fallback

If an eligible worker operation fails during startup, model loading, handshake, IPC, protocol validation, timeout, or encoding, the command MUST:

1. emit exactly one bounded warning to stderr for that command stating that local worker embedding failed and in-process embedding is being used;
2. discard raw worker detail;
3. use the established in-process embedder for the failed and all later embedding operations in that command;
4. perform each provider catalog/content operation no more times than the established path; and
5. preserve successful routing, retrieval, ranking, and output semantics if in-process embedding succeeds.

The warning MUST NOT include query text, model-cache path, socket path, PID, frame, environment value, credential, raw exception, traceback, or allowlisted internal category. If in-process embedding also fails, the established phase-correct bounded CLI error governs.

Embedding fallback is allowed even after uncertain worker request completion because local embedding has no provider or durable side effect. Fallback MUST occur before any dependent provider content request, so it cannot duplicate content retrieval. Automatic routing catalog reads already completed before routing embedding MAY remain single-occurrence and MUST NOT be repeated.

Only one warning may be emitted even if routing fallback causes later retrieval to use in-process embedding. Worker failure MUST be represented by a bounded low-cardinality local telemetry attribute/event only if the active telemetry schema already permits it; otherwise no telemetry schema expansion occurs in this ticket.

## Worker lifecycle and privacy

All reviewed worker protocol, identity, permission, election, no-persistence, credential-free child environment, no-provider import, cleanup, and five-minute accepted-request idle semantics remain unchanged.

The worker receives only bounded embedding text and returns vectors. Provider credentials/clients, namespace queries, results, reranking, telemetry storage, and output remain in the CLI process.

## Acceptance scenarios

### Eligible default automatic retrieval

Given default model/float32 on a supported POSIX host without opt-out, when automatic retrieval runs, then one resident worker adapter serves routing and retrieval embeddings, no CLI-process Sentence Transformers model is constructed unless fallback occurs, and established output/provider behavior is preserved.

### Eligible default explicit retrieval

Given one or more explicit namespaces under eligible defaults, when live retrieval runs, then the worker embeds exactly once before established provider content requests.

### Opt-out

Given `--no-embedding-worker`, when any retrieve mode runs, then worker code/state/process/IPC is absent and the established in-process path is used.

### Custom or unsupported

Given a custom model, float16, or unsupported worker capability without opt-out, when retrieval runs, then the established in-process backend is selected directly with no worker side effect and no fallback warning.

### Worker failure

Given an eligible worker failure before any dependent content query, when the in-process backend succeeds, then exactly one bounded warning is emitted and the command succeeds with established output and no duplicated provider operation. When the in-process backend also fails, then the established phase-correct error is returned after the single fallback warning.

### Dry-run

Given eligible automatic dry-run, semantic routing may use or fall back from the worker but no content query occurs. Given explicit dry-run, no worker or embedding operation occurs regardless of eligibility. Given opt-out, dry-run preserves established in-process behavior.

### Non-retrieve dormancy

Given help/version or any non-retrieve command, worker code/state/process/IPC remains absent.

## Verification

- Parser/help/docs tests for remove-opt-in/add-opt-out behavior and command locality.
- Focused matrix tests for eligible, opt-out, custom model, float16, unsupported capability, automatic/explicit live, and automatic/explicit dry-run.
- Failure tests for every worker error phase, exactly-one redacted warning, command-wide in-process switch, no provider duplication, fallback-success parity, and fallback failure taxonomy.
- No-worker import/files/process tests for opt-out, ineligible configs, non-retrieve commands, and isolated install.
- Existing worker, routing, retrieval, telemetry, output, and full Python 3.11/3.13 suites pass.
- Provider-free exact-vector/ranking parity remains passing.
- A live campaign is not required to implement the already owner-ratified default; no additional live provider call is authorized by this specification.
- Independent post-change review passes before closure.

## Explicit exclusions

Worker support for custom models, float16, Windows, pools, batching, cross-encoder residency, provider clients/credentials in worker, apply/index/evals integration, telemetry schema redesign, additional live A/B, percentile/SLA/release gate, global installation, release, deployment, or publication.
