Status: active
Created: 2026-08-27
Updated: 2026-08-27
Supersedes: .10x/decisions/superseded/buoy-connects-the-embedding-worker-behind-an-experimental-retrieve-flag.md

# Buoy Defaults Compatible Retrieve Embeddings to the Local Worker

## Context

The explicit retrieve experiment completed exactly three owner-authorized live commands with byte-identical outputs:

- established baseline: 10,522.682 ms;
- cold worker: 8,789.305 ms, 16.47% below baseline; and
- warm worker: 5,880.203 ms, 44.12% below baseline and 33.10% below cold.

Cold and warm commands reused one worker, output/route/shape hashes matched exactly, five hits across three namespaces matched, model cache remained equal, and idle cleanup completed. Provider/network timing remains a confounder and three observations are not a distribution, but the evidence establishes useful repeated-command behavior on the observed Darwin arm64 host.

The owner previously wanted default activation if the experiment worked and, after reviewing the evidence, selected default activation with an explicit opt-out and visible in-process fallback. Custom/unsupported configurations must preserve their established in-process path.

## Decision

For `buoy retrieve`, use the local embedding worker by default only when all exact worker conditions hold:

- supported POSIX capability;
- model `BAAI/bge-small-en-v1.5`;
- precision `float32`; and
- current pinned routing/worker identity.

Replace the experimental opt-in flag with `--no-embedding-worker`. The opt-out uses the established in-process routing and retrieval embedders and creates no worker state.

Custom model/precision and unsupported-platform invocations continue in-process automatically without a warning because they are expected supported configurations, not failures.

If an eligible default worker attempt fails during the command, retry that local embedding in-process, emit one bounded value-redacted warning to stderr for the command, and continue. The fallback must occur before any content retrieval request, must not repeat provider content operations, and must preserve established embedding/routing/ranking/output behavior. No raw worker error, query, path, PID, frame, credential, or stack detail is emitted.

The five-minute idle lifetime remains unchanged. Provider credentials and clients remain outside the worker.

## Alternatives considered

- Keep experimental: rejected after exact live parity and favorable cold/warm observations.
- Default fail-closed: rejected because a local optimization should not make retrieval unavailable when the established in-process backend remains usable.
- Silent fallback: rejected because hidden worker failure would erase operational visibility.
- Worker for custom models/float16/unsupported platforms: rejected because the worker prototype does not implement those identities and existing in-process support must remain available.
- Retain both opt-in and opt-out flags: rejected as contradictory surface area; the experimental flag was explicitly not a compatibility promise.

## Consequences

Repeated compatible retrieval commands should avoid repeated Sentence Transformers/Torch initialization, while one-off commands may still pay cold worker startup. Compatible commands now create a private background process and retain roughly 185–516 MB observed RSS for up to five minutes. An actual worker failure may make one command slower because it pays worker failure plus in-process initialization, but should remain functionally available with a bounded warning.

This decision supersedes experimental opt-in activation. It does not establish a percentile, SLA, release gate, Windows worker support, or worker support for custom embedding identities.
