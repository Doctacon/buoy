Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/2026-08-24-measure-provider-free-retriever-construction.md

# Provider-Free Retriever Construction Probe Failure

## What was observed

Execution began from required clean HEAD
`f43847767513a9e5d1854f928485692e12737e35`. Only the owning ticket was
changed for activation, producing activation commit
`d6bf3c59168877b2db2936fdae67cd0ee3653ad7`, tree
`06fddfa32ba60bfad1b80aee02737e9f1aaada7d`, before any model child started.
The exact execution source remained commit
`dd0e155d26af6b0cfbc9872606c5861e0d3b4306`, tree
`f9edc5cbaa76d342239901d99f75013846c6e278`. `pyproject.toml` SHA-256 was
`f80f4c53b5a6e1fe15e79abf31b40cdf529336a28144cec085ef1c7749861c22` and
`uv.lock` SHA-256 was
`ad7508159bc00271b21fc598bad07b56045329c938ed4fbd37a5a18d71c4c254`.
The bound runtime was CPython 3.13.0 with sentence-transformers 5.6.0,
transformers 5.12.1, torch 2.12.1, and turbopuffer 2.4.0.

The pre-child path accepted the exact cached
`BAAI/bge-small-en-v1.5` revision
`5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, its 12 exact content-hashed
assets, float32, the locked dependency versions, production automatic-device
selection, the owner-private temporary root, offline controls, credential-free
child environment, process sandbox, watchdog, and pre-child cache identity
checks. No retained observation had begun.

The first and only model child was the discarded warm-up. Its start consumed
that authority. It reached a terminal nonzero exit, so the sanitized failure
category is exactly `child_nonzero_exit`. No valid child result was accepted,
no timing was retained, no later child started, and no retry, replacement, or
substitution occurred. There is no complete five-sample result.

## Failure handling and cleanup

Raw stdout/stderr, exception detail, process samples, environment, paths, and
partial timing were neither promoted nor retained. The child was terminal when
the watchdog completed. The external harness, scripts, sandbox profile,
sanitary intermediate result, and owner-private temporary root were deleted;
the root was then verified absent. Repository status was clean at activation
commit `d6bf3c59168877b2db2936fdae67cd0ee3653ad7` immediately after cleanup.

The failed-child path did not retain a post-child full-cache comparison, so
terminal full-cache equality is not established. This uncertainty is a probe
failure and grants no rerun. It is not converted into a timing, optimization
finding, cache-mutation claim, or accepted result.

## What this supports or challenges

This supports only that the one authorized warm-up authority was consumed and
the campaign failed without retry. It challenges completion of every
five-observation acceptance criterion. It does not support any performance,
latency attribution, provider, network-attempt, cache-integrity, telemetry,
retrieval, or optimization conclusion.

## Privacy and limits

This record contains no query, argv, environment value, credential presence or
value, provider/catalog/namespace/content identity, cache/model/executable
path, raw process output, process/thread identifier, host/user name, hardware
serial, private path, stack, traceback, exception text, or partial timing.
Only the permitted exact source/model identities, generic failure category,
sequence outcome, and cleanup result survive.
