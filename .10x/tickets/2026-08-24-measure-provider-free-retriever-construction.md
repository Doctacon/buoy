Status: blocked
Created: 2026-08-24
Updated: 2026-08-24
Parent: None
Depends-On: .10x/tickets/done/2026-08-24-investigate-retrieve-command-outer-latency.md
Authorization-Evidence: .10x/evidence/2026-08-24-provider-invocation-probe-and-live-canary-authorization.md
Research: .10x/research/2026-08-24-retrieve-command-outer-latency-attribution.md
Review: .10x/reviews/2026-08-24-retrieve-command-outer-latency-attribution-review.md
Activation-Review: .10x/reviews/2026-08-24-provider-invocation-execution-activation-review.md
Execution-Evidence: .10x/evidence/2026-08-24-provider-free-retriever-construction-probe-failure.md

# Measure Provider-Free Retriever Construction

## Outcome

Separate sentence-transformers import, exact local embedding-model construction,
and fake-provider/retriever/configuration construction inside the explicit
`buoy.retrieve.prepare` source boundary. Produce content-free research evidence
without provider, credential, network, telemetry, store, source, or cache
mutation and without treating the result as optimization authority.

## Exact execution identity

Execution MUST use exact source commit
`dd0e155d26af6b0cfbc9872606c5861e0d3b4306`, tree
`f9edc5cbaa76d342239901d99f75013846c6e278`, and the repository's current
locked runtime:

- `pyproject.toml` SHA-256
  `f80f4c53b5a6e1fe15e79abf31b40cdf529336a28144cec085ef1c7749861c22`;
- `uv.lock` SHA-256
  `ad7508159bc00271b21fc598bad07b56045329c938ed4fbd37a5a18d71c4c254`;
- sentence-transformers `5.6.0`, transformers `5.12.1`, torch `2.12.1`, and
  turbopuffer `2.4.0` as resolved by that lock; and
- the source files and hashes bound in the authorization evidence.

The model is exactly `BAAI/bge-small-en-v1.5` at revision
`5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, float32. Construction MUST use
the unchanged production `SentenceTransformerEmbedder` path and its production
automatic device selection. The harness MUST NOT force CPU, MPS, CUDA, or any
other device and MUST NOT call `.half()`. Before the first process, the executor
MUST prove that the locally resolved model/ref/assets are that exact revision
and are complete under enforced offline/local-only behavior.

The execution runtime and host MUST be bound before the first child starts:
Python executable bytes or immutable runtime manifest, Python version,
platform/kernel/architecture, dependency manifest, and selected device class.
Retained identities MUST be content-free and MUST exclude user, host name,
serial number, executable/cache path, process ID, and environment values.
Runtime, source, host, model, or device drift stops before another child starts.

## Temporary harness and independent timing method

The executor MAY create one purpose-built harness and raw logs only under an
owner-private temporary directory outside the repository. The harness MUST run
with all real credentials removed, fixed offline/no-download environment,
process-level network denial, telemetry disabled, and a fake/injected provider
object that has no network or provider implementation.

Each child process MUST perform these three non-overlapping timed components in
source order and report each interval independently:

1. import `sentence_transformers` from immediately before import evaluation
   until the import returns;
2. construct exact `SentenceTransformerEmbedder` for the ratified model and
   float32 precision, after the import interval is complete; and
3. construct the source `RuntimeConfig`, fake/injected namespace/provider
   boundary, and `HybridRetriever` around the already-constructed embedder,
   after model construction is complete.

The third component MUST use direct dependency injection and MUST NOT call
`HybridRetriever.from_config`, `build_namespace`, a real SDK client, or any
provider resource. No query, embedding encode, retrieval, catalog read, content
read, model reranker, or other operation follows construction. The research
MUST present the three measured intervals separately and MUST NOT add them,
sum nested spans, derive an end-to-end duration from them, or infer causality
from their relative size.

## Observation sequence and hard process limits

Run exactly six fresh child processes in fixed order:

1. one fresh-process host warm-up whose timing is discarded; then
2. five retained fresh-process observations of the resulting process-cold,
   host-warm condition.

No child may be reused. No observation may be reordered, replaced, or repeated.
Every child has both hard limits:

- elapsed monotonic time MUST remain below 120 seconds; when it reaches
  120.000 seconds, the parent MUST immediately terminate that child and abort
  the campaign; and
- observed child resident set size MUST remain below 4,294,967,296 bytes; when
  it reaches or exceeds that value, the parent MUST immediately terminate that
  child and abort the campaign.

The watchdog MUST apply from child start through terminal exit and measure that
child process's elapsed time and RSS directly. An unexpected descendant process
is itself a failure. Retain only whether a generic elapsed/RSS limit failed. A
limit hit, watchdog uncertainty, inability to terminate, or orphaned descendant
is a failed probe, not a censored observation.

## Cache integrity and prohibited effects

Before the warm-up, after every child, and after the terminal campaign state,
the executor MUST compare:

- the model cache-root identity set;
- exact model ref identity for the ratified revision; and
- a full regular-file/symlink/type/size/content manifest for every bound model
  cache root.

Any added, removed, changed, retargeted, or metadata/type-inconsistent cache
entry is a failure and immediately aborts remaining observations. Retained
records MAY keep only content-free manifest digests, counts, aggregate bytes,
and the exact model/revision; no cache path or unrelated cached model identity
may be retained. The harness MUST NOT clear, evict, repair, touch, rewrite, or
otherwise manipulate OS caches, model caches, refs, assets, or device caches.
Normal read-only host/OS cache warming caused by the six authorized model
constructions is the only approved cache effect.

There MUST be no provider SDK call, provider/catalog/content access, credential
read, network attempt, model download, telemetry activation/publication/store
access, database operation, source/test edit, repository artifact, build,
install, migration, global-tool operation, release, or deployment.

## Failure, no-retry, and cleanup rules

- Any preflight identity, offline, network-denial, credential-removal, cache,
  harness, watchdog, or privacy failure stops before the warm-up.
- Starting a child consumes that observation authority. Nonzero exit, signal,
  interruption, timeout, RSS limit, malformed/missing output, prohibited
  effect, identity drift, or uncertain terminal state fails the entire probe,
  stops all later children, and grants no retry or replacement.
- Warm-up failure produces no retained timing. Failure in one of the five
  retained observations does not permit keeping a shorter successful series as
  an accepted result.
- A failed probe MAY record only sanitized failure category, the identities
  permitted below, cleanup result, and the fact that no complete five-sample
  result exists. It MUST NOT record partial raw output or promote partial
  timings to findings.
- Process interruption MUST trigger best-effort termination of the current
  child and descendants followed by cleanup. Uncertain termination or cleanup
  is a ticket failure and requires owner escalation; it never grants a retry.

After sanitized evidence and review inputs are recorded, delete the external
harness, scripts, raw stdout/stderr, process samples, temporary environment,
intermediate manifests, and every runtime/log artifact. Verify their absence.
The repository worktree and all unrelated local state MUST match their bound
pre-state.

## Privacy and retention

Retain only:

- the three content-free component timings for each of five accepted
  observations, plus units and observation order;
- generic hard-limit/failure and cleanup outcomes;
- exact source/tree/lock/model/revision/precision identities;
- bounded content-free runtime, host class, automatic device class, and cache
  manifest identities; and
- methods, limits, conclusions, and review references.

Do not retain query, argv, environment value, credential presence/value,
provider/catalog/namespace/content identity, model/cache/executable path, raw
process output, process/thread ID, host/user name, hardware serial, private path,
stack, traceback, or raw exception. Component timings are not telemetry and
MUST NOT be written to the telemetry-v2 store.

## Acceptance criteria

- Exact source, lock, runtime, host, model revision, float32 precision,
  production automatic-device behavior, offline network denial, fake provider,
  and pre-cache identity are proven before execution.
- Exactly one discarded warm-up and five retained fresh processes complete in
  order under both hard limits, with no retry or replacement.
- Every process emits three separate non-overlapping component timings and no
  summed/nested-derived total.
- Full cache/ref/root identities are equal before, between, and after processes;
  repository, telemetry store, provider, credential, network, global-tool, and
  unrelated state are unchanged.
- A dated sanitized research record under `.10x/research/` records the bounded
  observations, method, conclusions, and limits without becoming an
  optimization requirement or performance target.
- Temporary harness/raw/runtime artifacts are deleted after sanitized evidence;
  retained content satisfies the privacy contract.
- Independent review verifies the exact evidence commit, timing method,
  identities, hard-limit/no-retry behavior, privacy, cleanup, and no unrelated
  mutation before this ticket can close.

## Evidence expectations

Record the exact activation/execution commit and tree; source/lock/runtime/model/
host/cache identities; six-process start/terminal ledger without PIDs; five
three-component timing rows; limit and network/provider/telemetry/store
invariants; pre/intermediate/post manifest equality; changed-path/diff/status;
and cleanup proof. Evidence MUST state that the warm-up was discarded and that
no total was formed by summing component intervals.

## Explicit exclusions

Source/test/specification change; production instrumentation or telemetry;
query/encode/retrieval/reranking; real provider/client/catalog/content/network/
credential operation; model download/cache clearing/cache repair; forced device;
telemetry/store/database access or mutation; performance target, optimization,
mode comparison, cold-host claim, distribution/percentile claim, live canary,
build/install, global-tool change, release, or deployment.

## Blockers

The first and only child start consumed the discarded warm-up authority and
ended with sanitized category `child_nonzero_exit`. No timing was retained, no
later child started, and no retry, replacement, or substitution is permitted.
The failed-child path also did not retain a post-child full-cache comparison,
so terminal cache equality is not established. The external runtime artifacts
were removed and the repository was clean after cleanup.

There is no complete five-sample result. This ticket cannot resume under its
consumed no-retry authority. The owner later ratified a materially distinct
current-source successor at
`.10x/tickets/done/2026-08-27-measure-current-provider-free-retriever-construction.md`;
this ticket remains the immutable durable owner of the failed attempt and is
not reopened.

## Progress and notes

- 2026-08-24: Opened from independently reviewed outer-latency attribution as
  the durable owner for the unfinished explicit prepare sub-boundary. It was
  blocked pending model/cache and measurement authority; no probe ran.
- 2026-08-24: The owner ratified the exact model/revision/precision/device,
  six-process sequence, independent timing boundaries, hard elapsed/RSS limits,
  offline fake-provider design, cache integrity, privacy, cleanup, validation,
  and review contract. The old blockers are removed. Ticket is now open,
  executable, and inactive; no child process, model, provider, network, store,
  telemetry, build, test, or global-tool operation ran in this records-only
  turn.
- 2026-08-24: Independent activation review passed exact authorization commit
  `21f6a7b21d950f086ac6dfd7ab4f633883d6e066`, tree
  `4d044b44d492757dad80466968809aebdb76f161`, with no findings. The probe is
  activation-ready but remains open/inactive and unrun; this reconciliation
  performed no probe, model, provider, network, telemetry/store, build, test,
  or global-tool operation.
- 2026-08-24: Activated only this ticket for its exact one-discarded-warm-up
  plus five-retained provider-free construction campaign from clean execution
  HEAD `f43847767513a9e5d1854f928485692e12737e35`, bound to source commit
  `dd0e155d26af6b0cfbc9872606c5861e0d3b4306` and tree
  `f9edc5cbaa76d342239901d99f75013846c6e278`. No child/model process had
  started when this activation was recorded; all preflight, no-retry, privacy,
  cleanup, and failure rules remain controlling.
- 2026-08-24: Activation commit
  `d6bf3c59168877b2db2936fdae67cd0ee3653ad7`, tree
  `06fddfa32ba60bfad1b80aee02737e9f1aaada7d`, preceded every model child.
  The first discarded warm-up child consumed its authority and terminated
  nonzero. The campaign stopped immediately: zero retained observations, zero
  retries/replacements, and no five-sample result. Raw detail and partial timing
  were discarded. External harness/runtime artifacts were deleted and verified
  absent; repository status was clean. Sanitized failure evidence is recorded
  at
  `.10x/evidence/2026-08-24-provider-free-retriever-construction-probe-failure.md`.
- 2026-08-27: Trace analysis again identified preparation as the dominant
  retrieval inefficiency. The owner selected current reorganized source and
  authorized a fresh, separately bounded provider-free campaign with a
  pre-consumption harness self-test. New authority belongs exclusively to
  `.10x/tickets/done/2026-08-27-measure-current-provider-free-retriever-construction.md`;
  this consumed ticket remains blocked.
