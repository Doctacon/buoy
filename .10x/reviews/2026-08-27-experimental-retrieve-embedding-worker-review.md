Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Target: src/buoy_search/cli/main.py; src/buoy_search/retrieval/retriever.py; tests/fixtures/experimental_retrieve_worker_ab.py; .10x/evidence/2026-08-27-experimental-retrieve-embedding-worker-ab.md; .10x/tickets/done/2026-08-27-connect-embedding-worker-to-retrieve-experiment.md
Verdict: pass

# Experimental Retrieve Embedding Worker Review

## Target

Retrieve-only worker activation, retriever injection seams, focused tests/documentation, bounded live A/B harness, and retained redacted evidence under `.10x/specs/superseded/experimental-retrieve-embedding-worker.md`.

## Findings

No unresolved significant finding.

The independent reviewer verified:

- activation exists only as `buoy retrieve --experimental-embedding-worker`;
- worker import is lazy and the no-flag path preserves established factory calls and behavior;
- exact model/precision/POSIX validation occurs before credential reads or provider construction;
- automatic mode uses the same adapter for semantic routing and final retrieval embedding;
- explicit live retrieval embeds once, explicit dry-run starts no worker, and automatic dry-run performs routing but no content retrieval;
- optional retriever-factory injection preserves former default construction when omitted;
- worker errors remain bounded, redacted, phase-correct, no-fallback, and no-replay;
- no backend marker, query, vector, credential, PID, socket path, or raw error was added to output or telemetry;
- the harness performed exactly three ordered live commands, deleted restrictive raw files, retained only hashes/counts/timings, and waited without signaling for validated idle cleanup; and
- evidence makes only a bounded three-observation claim and preserves provider/network confounding and inconclusive source-manifest equality.

### Minor harness privacy finding — resolved

Initial post-change review found that the post-campaign harness still held decoded result references during the five-minute idle wait. The completed campaign had retained no raw artifact, so this was not a significant closure blocker, but future use required correction.

The harness now decodes within `_run_one`, returns only redacted hashes/counts/lengths/status/timing, and deletes raw files in `finally`; decoded provider objects become unreachable before idle waiting. A focused sentinel test proves returned data and raw files contain no result content. Parent observed 32 focused tests passing, `py_compile`, diff hygiene, and no staged files. Targeted independent rereview passed with no issue. No fourth live command ran.

## Verdict

Pass. No unresolved significant or minor finding remains. The experimental retrieve worker ticket is suitable to close. This review does not authorize default-on activation.

## Residual risk

- Three sequential Darwin arm64 observations do not isolate provider/network variance or establish a latency distribution.
- RSS is one post-command sample rather than peak memory.
- Executed-campaign source equality remains inconclusive because its original manifest included ignored bytecode and retained no constituent entries.
- Same-effective-user processes remain within the documented Unix-socket boundary.
- Worker network isolation is procedural/source-controlled rather than packet-traced.
