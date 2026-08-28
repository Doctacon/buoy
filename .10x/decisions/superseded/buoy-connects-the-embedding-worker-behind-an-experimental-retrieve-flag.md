Status: superseded
Created: 2026-08-27
Updated: 2026-08-27
Superseded-By: .10x/decisions/buoy-defaults-compatible-retrieve-embeddings-to-the-local-worker.md

# Buoy Connects the Embedding Worker Behind an Experimental Retrieve Flag

## Context

The dormant worker prototype proved exact default-model vector parity and cross-process reuse. On its corrected provider-free run, startup cost 9.716 seconds once, a first fresh client request cost 200 milliseconds, a subsequent fresh client request cost 30 milliseconds, and the resident worker used about 492 MB RSS. It remains unconnected to retrieval, so those measurements do not yet establish end-to-end command benefit.

The owner authorized connecting it for an experiment, chose an explicit retrieve flag, selected both automatic-routing and retrieval-query embeddings, and authorized a three-run live A/B using the documented query `How is approximate vector recall evaluated?`. If evidence is favorable, the owner wants a later decision on making the worker the default.

The dormant prototype ticket remains active pending genuinely independent post-correction review. Product activation must not outrun that review.

## Decision

Add `buoy retrieve --experimental-embedding-worker` as the sole activation surface after the dormant worker passes independent review.

When present, the exact same resident pinned model serves:

- automatic semantic-routing query embeddings; and
- final retrieval-query embeddings across selected namespaces.

The flag has no silent fallback. It supports only the current pinned/default model, revision, float32 precision, and supported POSIX worker capability. Unsupported configuration or worker failure is visible and bounded. Without the flag, established retrieval behavior remains unchanged.

Validate with exactly three sequential live automatic-routing commands using the owner-approved documented query:

1. established in-process baseline without the flag;
2. cold worker with the flag; and
3. warm reused worker with the flag.

Telemetry is disabled for the experiment. Existing environment credentials may be read by normal retrieval code but must never be copied into worker state, child environment, logs, records, or retained artifacts. Retain timing, routing/result parity, redacted hashes/counts, worker identity/RSS, and cleanup—not query results or credentials.

No default-on decision is made here. Default activation requires favorable evidence, independent review, and a separate owner-ratified decision.

## Alternatives considered

- Make the worker default immediately: rejected until end-to-end evidence exists.
- Environment-variable activation: rejected because it is easier to inherit accidentally than an explicit command flag.
- Retrieval embedding only: rejected because automatic routing uses the same pinned model and would retain the dominant cold initialization.
- Provider-free integration only: rejected as the final test by owner choice; provider-free evidence remains a precondition and live provider variance must be reported.
- Silent in-process fallback: rejected because it hides reliability and latency defects.

## Consequences

The experiment can measure real command utility while preserving an explicit off switch and unchanged default. It performs three authorized live read-only retrieval commands and may leave the worker resident for up to five minutes before validated idle cleanup. Remote provider/catalog/content timing remains a confounder, so conclusions must separate local preparation/embedding spans from total wall time and must not claim stable percentiles from three observations.
