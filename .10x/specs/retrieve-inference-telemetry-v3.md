Status: active
Created: 2026-08-28
Updated: 2026-08-28
Decision: .10x/decisions/buoy-records-worker-and-provider-attempt-retrieval-telemetry-v3.md
Amends: .10x/specs/retrieve-command-telemetry.md
Storage: .10x/specs/local-telemetry-v3-storage-and-migration.md

# Retrieve Inference Telemetry V3

## Purpose and scope

This specification upgrades successfully dispatched `buoy retrieve` command observations from schema v2 to v3 and makes command-scoped embedding and cross-encoder work attributable after resident-worker activation.

It preserves retrieval/routing/ranking/evidence/output/provider semantics, v2 command and pipeline timing meanings, v1 direct-library behavior, strict privacy, opt-in local-only enablement, and disabled zero-side-effect behavior.

## V3 command graph

Every newly observed retrieve command uses observation schema exactly 3. The command root remains `buoy.retrieve.command`; the retained stage names and relationships from v2 remain valid. V3 adds one name:

```text
buoy.inference.request
```

One inference-request span MUST surround each actual command-scoped embedding or cross-encoder call, whether worker or in-process. It MUST begin immediately before the selected backend call and end immediately after return or raise. It measures caller-observed backend wait, including worker IPC and any startup/model initialization reached by that call; it does not claim worker-internal CPU time.

An inference request MUST be a child of the stage that requires it:

- routing embedding or prototype scoring: `buoy.routing.select`;
- retrieval query embedding: `buoy.query.embed`;
- result reranking: `buoy.rerank`;
- fresh evidence scoring: `buoy.evidence.assess`.

Reused existing evidence scores create no synthetic request. Factory/adapter construction remains under existing preparation/routing-model spans. An inference span MUST NOT cause eager model loading, extra calls, changed batching, retries, or backend selection.

A worker failure followed by established in-process fallback creates two sibling inference-request spans for one logical operation: failed `worker/primary`, then `in_process/fallback`. A worker request that succeeds creates no fallback span. Compatibility-required or explicitly forced in-process execution creates one `in_process/primary` span.

## Command inference policy

The command root adds exactly one required attribute:

```text
buoy.inference.policy = worker_preferred |
                        forced_in_process |
                        compatibility_in_process
```

- `worker_preferred` means exact platform/model/precision compatibility selected the established default worker path. It does not claim every request succeeded in the worker; request spans own fallback truth.
- `forced_in_process` means the retrieve-only opt-out explicitly disabled the worker.
- `compatibility_in_process` means established platform, custom-model, precision, or other compatibility rules required the unchanged in-process path.

Preview commands use the policy that their established configuration would use. Explicit preview may have no inference spans. The policy MUST NOT retain the specific custom model, platform, path, or incompatibility detail.

## Inference-request attributes

Every `buoy.inference.request` span has exactly these attributes:

| Attribute | Contract |
| --- | --- |
| `buoy.inference.operation` | `encode` or `score` |
| `buoy.inference.backend` | `worker` or `in_process` |
| `buoy.inference.role` | `primary` or `fallback` |
| `buoy.inference.item_count` | integer 1..108; encode MUST be <=16 |
| `buoy.inference.worker_state` | `spawned`, `reused`, `unknown`, or null; non-null only for worker |
| `buoy.inference.outcome` | `success` or `error` |
| `buoy.inference.error_type` | null on success; governed category on error |

Worker error categories are exactly:

```text
protocol_error
incompatible_worker
model_unavailable
encoding_failure
scoring_failure
busy_timeout
internal_worker_failure
```

In-process error categories are exactly `encoding_failure` or `scoring_failure`. The span status is `OK` for success and `ERROR` for error. The original return value or exception remains unchanged.

`spawned` means this call elected and launched the worker instance it then contacted. `reused` means it contacted a compatible instance without launching it. `unknown` is allowed only when a worker request fails before the lifecycle fact can be established. Competing-process details, PID, identity hash, socket data, retries, or elapsed substeps MUST NOT be retained.

The item count is the number of texts for `encode` or passages for `score`. It reveals neither lengths nor values. No zero-item inference span is valid because established worker/in-process APIs reject or avoid such calls.

## Instrumentation and failure isolation

Backend lifecycle facts MUST come from a private bounded callback/result owned by the worker client; they MUST NOT be inferred by probing process or filesystem state after the request. The callback accepts only the governed fields above. Callback or telemetry failure MUST be swallowed and MUST NOT alter spawn/connect behavior, IPC frames, timeout behavior, fallback, warning emission, model loading, output, or exception identity.

When telemetry is disabled, command policy derivation and inference observation MUST add no worker callback, context, filesystem, process, output, network, or model side effect. Existing plain backend calls remain direct.

## Summary and stable query behavior

The v3 command analytical view exposes `inference_policy` and content-free aggregate request counts:

```text
worker_encode_requests
worker_score_requests
in_process_encode_requests
in_process_score_requests
worker_spawned_requests
worker_reused_requests
worker_error_requests
fallback_requests
```

Each is a nonnegative integer derived from validated request rows. The dedicated inference view exposes one row per request with command mode, stage parent, timing, and governed attributes. Consumers MUST NOT sum nested request spans with their parent stage durations.

## Privacy

The complete v2 prohibited-data contract remains active. Inference telemetry additionally prohibits text/passages, vectors/scores, model inputs/outputs, worker PID/socket/implementation identity, process command/environment, request frame bytes, custom model value, and raw worker error. Model/revision labels remain only in the existing bounded retrieval-operation summary.

## Acceptance scenarios

1. Compatible explicit live retrieval with a new worker records one spawned worker encode request; later scoring records worker state reused.
2. A second compatible command against the resident worker records reused requests and no spawned request.
3. Automatic routing records routing encode/score requests under route selection and later retrieval requests under their established pipeline stages.
4. A worker encoding or scoring failure records one bounded error request followed by the established in-process fallback request; output/provider operations remain unchanged and the existing one-warning rule holds.
5. Worker plus fallback double failure retains existing `model_error` command taxonomy and exact exception/output behavior while recording only bounded request errors.
6. `--no-embedding-worker`, custom model/precision, and unsupported platform use exact in-process behavior with correct policy and no worker request.
7. Evidence score reuse creates no score request; fresh evidence scoring creates one under evidence assessment.
8. Preview behavior is unchanged and contains only inference requests established routing actually performs.
9. Disabled telemetry is byte/side-effect compatible and does not register lifecycle callbacks.
10. Sentinel tests prove prohibited query, passage, vector, score, PID, path, model override, credential, provider, raw exception, ambient context, and worker frame data are absent from every artifact.
11. Python 3.11 and 3.13 focused/full suites, package builds, and isolated installed-wheel telemetry lifecycle pass without model download or provider access.

## Explicit exclusions

Worker-side telemetry persistence/export, model input/output retention, per-substep worker timing, RSS sampling, process identifiers, query/corpus fingerprints, changed worker lifetime, changed fallback behavior, model/ranking changes, physical provider accounting, default-on telemetry, provider writes, release, and publication are excluded.
