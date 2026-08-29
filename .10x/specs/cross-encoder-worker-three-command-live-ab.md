Status: active
Created: 2026-08-28
Updated: 2026-08-28
Decision: .10x/decisions/buoy-runs-one-three-command-cross-encoder-worker-live-ab.md
Depends-On: .10x/specs/default-retrieve-cross-encoder-worker-residency.md, .10x/specs/default-retrieve-embedding-worker.md

# Cross-Encoder Worker Three-Command Live A/B

## Purpose and scope

Validate one bounded current end-to-end observation of default schema-v2 embedding plus cross-encoder residency against the complete in-process retrieve path, while preserving output/routing parity, provider read-only behavior, credential privacy, model-cache integrity, and exact three-command authority.

## Fixed command contract

The query MUST be exactly:

```text
How is approximate vector recall evaluated?
```

After all provider-free gates pass and a compatible schema-v2 worker is proven absent, the harness MUST run these commands once each in fixed order under the same current source, Python executable, environment controls, credential name, region/configuration, and working directory:

1. baseline: `buoy retrieve <query> --json --no-embedding-worker`;
2. cold worker: `buoy retrieve <query> --json`; and
3. warm worker: the identical default command again.

Each command MUST execute in a fresh CLI process with a 240-second timeout. The cold and warm commands MUST use one validated worker identity/process; the baseline MUST create no worker state. No command may be retried, replaced, reordered, or run a second time. Any nonzero exit, timeout, malformed output, unexpected warning/error bytes, baseline worker activation, unavailable worker after a default command, identity/reuse mismatch, source/cache mutation, or privacy/cleanup failure MUST stop the remaining sequence. A failed command still consumes its ordinal. No fourth command is authorized.

## Preflight and harness debugging

Before the first live command, the executor MUST:

1. bind exact current source/lock/runtime/package/schema-v2 worker identities and deterministic changed-path manifest, excluding ignored Python bytecode from source identity;
2. bind complete readable exact embedding and cross-encoder cache manifests and verify offline/local-only availability without model construction if possible;
3. verify the provider credential name is present without reading, printing, hashing, or retaining its value;
4. remove unrelated credential keys from child environments where compatible with the single required provider credential;
5. disable Buoy/OpenTelemetry/model telemetry, bytecode writes, and model-network access while preserving authorized provider catalog/content network access;
6. prove no compatible schema-v2 socket/ready state exists, waiting for validated natural idle cleanup for at most 360 seconds if necessary and aborting with zero live calls if it remains;
7. create all harness/output files under one mode-0700 temporary directory outside the repository with mode-0600 files;
8. debug the exact harness parser, redaction, hashing, timeout, cleanup, source/cache comparison, worker-state/RSS observation, and stop logic using provider-free synthetic subprocesses only; and
9. pass focused source/tests, protocol identity, provider-operation-count, fallback, privacy, diff-hygiene, no-staged-files, and harness compile/self-tests.

Harness debugging MUST NOT invoke `buoy retrieve`, a provider client, the live credential, or any external service. Live authority begins only when the baseline subprocess starts.

## Read-only external boundary

The three commands MAY perform established automatic remote catalog reads and namespace content queries. They MUST NOT perform provider writes, upserts, deletes, namespace creation/deletion, apply, index, crawl, plan mutation, catalog mutation, telemetry export/store, or any other external side effect.

Provider/client objects and credentials MUST remain in the CLI process, never the worker or retained evidence. The harness MUST invoke only the public retrieve CLI and MUST NOT instrument, monkeypatch, or bypass provider behavior during live commands.

## Privacy and retained data

Raw stdout/stderr MAY exist only in private temporary files during each command. Immediately after each command, the harness MUST:

- parse the complete JSON only on zero exit;
- reduce it to the allowed redacted fields below;
- release decoded payload/provider-derived objects;
- delete raw stdout/stderr; and
- verify deletion before starting the next command or idle wait.

Durable evidence MAY retain only:

- command ordinal and role;
- exit code;
- wall milliseconds;
- stdout/stderr byte counts and SHA-256 hashes;
- SHA-256 of canonical complete payload, ordered route identity, and structural shape;
- hit count and namespace count;
- parity booleans;
- content-free worker schema/implementation identity match, process reuse boolean, bounded RSS observation, and validated cleanup duration/outcome;
- source/lock/runtime/package and embedding/reranker cache manifest digests/equality; and
- generic bounded failure/stop category.

Durable evidence MUST NOT retain query-result content, snippets, titles, URLs, namespace or route values, raw output/error, provider responses, billing objects beyond content-free aggregate presence/count already exposed by the established payload shape, credentials or credential hashes, environment values, PIDs, socket/cache/private paths, stack traces, or decoded result objects.

## Parity and observation contract

Within the new campaign, baseline/cold/warm MUST be compared for:

- exit status;
- complete stdout hash and byte length;
- canonical payload hash;
- ordered route hash;
- structural shape hash;
- hit count;
- namespace count; and
- stderr hash/length.

Every mismatch MUST be retained as a boolean plus bounded category; it MUST NOT be normalized away. Historical hashes from the embedding-only campaign MAY be compared only as explicitly non-authoritative context because source, protocol, worker behavior, and remote state may differ.

Record wall time for each command and simple observed differences/percent changes only. Do not claim a distribution, percentile, SLA, causal provider-adjusted saving, cold-host measurement, release gate, or statistical significance.

After the warm command's raw/decoded data is destroyed, wait without signaling for the validated worker's natural five-minute idle cleanup. Record content-free reuse, one bounded post-command RSS observation, cleanup outcome, and cleanup observation duration. Do not retain PID or socket path.

## Acceptance criteria

1. Provider-free preflight/harness self-tests pass before live authority and no compatible worker is active.
2. Exactly three commands run once each in baseline/cold/warm order; no retry, replacement, reorder, or fourth call occurs.
3. Baseline uses complete in-process embedding/reranking and creates no worker; cold/warm use one schema-v2 worker identity and warm reuses it.
4. All three commands exit zero with empty stderr and equal complete payload/stdout/route/shape/count identities, or every mismatch/failure is truthfully retained and remaining calls stop as required.
5. Only authorized provider catalog/content reads occur; no provider write or duplicate operation caused by worker fallback occurs.
6. Raw files and decoded provider-derived objects are removed at each boundary before the next command/idle wait; durable evidence contains only allowed redacted fields.
7. Source, lock, runtime, package, embedding cache, and reranker cache identities remain equal before/after; no download, cache repair, source mutation, staging, install, or telemetry effect occurs.
8. Worker reuse, bounded RSS, natural idle cleanup, and zero surviving compatible worker state/process are validated without retaining sensitive identity.
9. Evidence states timing/parity findings and all limits without optimization, SLA, release, or causality overclaim.
10. Independent review passes command accounting, privacy, external effects, identities, cleanup, evidence accuracy, diff hygiene, and no-staged-files checks before closure.

## Verification

- Harness compile and provider-free synthetic self-test.
- Focused schema-v2 worker, retrieve CLI, provider-operation-count, fallback, privacy, and historical-harness dormancy tests.
- Exact pre/post source/cache/runtime/package manifest comparison.
- Three-entry immutable command ledger and no-fourth-call assertion.
- Raw-file deletion and decoded-object release checks after each command.
- Worker state/reuse/RSS/idle-cleanup checks with value-redacted retention.
- `git diff --check`, no staged files, and independent review.

## Explicit exclusions

More or fewer than the exact authorized sequence after live authority begins; retry/replacement/reordering; new query; explicit namespace mode; telemetry stage attribution; provider writes or management operations; content retention; packet tracing; production instrumentation; protocol/model/ranking/routing/evidence/output changes; performance target/SLA/release gate; global install; release; deployment; publication; automatic follow-up campaign.
