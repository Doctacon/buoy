Status: recorded
Created: 2026-08-19
Updated: 2026-08-19
Ticket: .10x/tickets/done/2026-08-19-implement-private-local-telemetry-writer.md
Decision: .10x/decisions/buoy-uses-a-private-local-telemetry-writer.md
Specification: .10x/specs/local-telemetry-writer.md
Review: .10x/reviews/2026-08-19-local-telemetry-writer-review.md

# Private Local Telemetry Writer Evidence

## Outcome and exact identity

Buoy now moves enabled retrieval telemetry's DuckDB work out of the
short-lived retrieval process. The completed local-only path is:

```text
private in-process OpenTelemetry spans
  -> sink-side governed rows
  -> canonical trace-envelope/v1
  -> private atomic filesystem inbox
  -> one lock-elected Buoy local writer
  -> existing telemetry DuckDB v1
```

There is no OpenTelemetry Collector, OTLP exporter/receiver, listener,
socket, remote backend, or cloud destination. Retrieval returns after local
envelope publication and never waits for DuckDB acknowledgement.

The task began from exact
`develop@3787e0eabd2720732fb5c68ca168f926342ae454` in isolated worktree
`/private/tmp/buoy-local-telemetry-writer` on
`work/local-telemetry-writer`. Governance commit
`2846b9e24b8355492b098fe9c4bd562db14b7ff2`, tree
`c296d9d97e7976421c23871756dcf501944a2d64`, is a direct child of that
base. The reviewed implementation is exact commit
`55f41fd9e2f98fed83fd0619c29a9a5549ae4052`, tree
`08b1679963b9b88d73601458e7a9890696591e68`, and direct child of the
governance commit.

The complete base-to-implementation range changes 24 owned paths with 11,937
insertions and 1,464 deletions. It adds the governing records, strict envelope,
bounded private queue, writer/store split, lightweight telemetry CLI routing,
documentation, and focused tests. It leaves `cli.py`, `test_cli.py`, evidence,
routing, and routing-quality behavior byte-identical to the base.

## Delivery, recovery, privacy, and compatibility proof

The producer canonicalizes only governed typed run/span/event values, writes
one private bounded envelope, fsyncs it, and atomically renames it into the
ready inbox. The writer independently parses and revalidates exact JSON types,
sizes, allowlists, timestamps, trace graph, summaries, and identifiers before
any database call. One elected writer claims work, validates the unchanged
DuckDB-v1 schema inside the same short-lived read-write transaction used for
the append, commits, publishes a content-free terminal receipt, and only then
acknowledges the claim.

Crash tests cover pre-publication, ready, claimed, partial transaction/WAL,
first-store scratch publication, post-commit/pre-receipt, and
post-receipt/pre-ack boundaries. Exact replay is idempotent; conflicting data
never overwrites an existing trace; malformed envelopes are content-free
rejections; incompatible/unsafe stores retain recoverable work. FIFO,
symlink, hardlink, socket, permission, unknown-entry, malformed-state,
start-lease, initialization-scratch, and catalog/view attacks fail closed.

Exact-byte scans across envelopes, state, receipts, and DuckDB prove absence
of query/content text, namespace/source/document identifiers, URLs, paths,
credentials, arbitrary environment values, command arguments, vectors,
provider payloads, raw exceptions, stack traces, ambient resources, and
unrelated `ContextVar` values. The detached writer receives an empty
environment and imports no provider, model, credential, retriever, or network
client. Ambient OpenTelemetry context and outbound propagation remain
isolated. Every telemetry failure preserves the retrieval result/error and
normal stdout/stderr behavior.

The DuckDB schema, metadata row, typed tables, analytical views, and database
path remain v1-compatible. Disabled telemetry remains a zero-side-effect
no-op. Enabled persistence is intentionally eventual; `buoy telemetry status`
is read-only and `buoy telemetry flush` is explicitly bounded. The strong
writer guarantee is POSIX-only and the bounded queue drops only the newest
observation at capacity while reporting content-free lower-bound accounting.

## Exact acceptance campaigns

The final frozen-source campaign matched the implementation commit's seven
governed module hashes through completion and passed:

- 100/100 synchronized producers with zero publication failures, exactly 100
  complete database graphs, one elected writer, and no trace loss;
- 100/100 paired disabled/enabled retrieval outcomes or errors exactly equal;
- paired added producer latency p50 2.414 ms, p95 3.039 ms, p99 3.147 ms,
  and maximum 4.700 ms;
- synchronized producer completion p50 113.334 ms, p95 215.128 ms, p99
  236.273 ms, and maximum 236.979 ms;
- warm-writer database visibility p50 62.421 ms, p95 82.581 ms, p99
  90.827 ms, and maximum 92.483 ms;
- three cold homes with retrieval maximum 5.044 ms, writer startup 57.332 ms,
  and visibility maximum 418.596 ms;
- zero producer DuckDB connect/execute/bind-like operations and no store
  module import; and
- all five observed writers exiting naturally at the governed idle boundary,
  with no signal or leaked process.

The separate adversarial harness passed 38/38 crash, replay, conflict,
rejection, status/flush, hostile-filesystem, child-privacy, and zero-network
scenarios. The focused envelope/producer/queue/store/writer/CLI/retrieval
suite passed 144/144. Both ran on the same final frozen source under isolated
Python 3.13 with `ResourceWarning` promoted to failure.

The first synchronized campaign had exposed a real 250-ms publication-lock
loss; the final contract's producer-only 500-ms bound admitted all 100
publishers. The first visibility campaign had also exposed read-only/read-write
DuckDB lock churn. One verified transaction connection plus the selected
10-ms retry cadence reduced the final p99 to 90.827 ms without validation
caching or a persistent DuckDB session.

Artifact identities are:

- final acceptance manifest SHA-256
  `c5b9948d06dcbaf0f0920185931f60137ac78732144ee6050a40736d6aab2bba`;
- final acceptance report SHA-256
  `72e29c3447c5b288817ee81a84b38ae35739ef51f41faae766b076e03f0671ca`;
- raw final campaign SHA-256
  `d48372f46ecb12959ece4b3940ce7c854a73613d630f62b3465d6ff236f7b583`;
- raw concurrency evidence SHA-256
  `b8b652f03ec50492c6d3661c1c6d358743ee5a56cc50a3e45e0cbe6fef6e1707`;
  and
- adversarial/focused verification manifest SHA-256
  `5fa05253c75609f8b99a00a4e5cdbc928e605f2b8eb7acf02c349b1825f5da94`.

These hashes establish identity; the `/private/tmp` artifacts are not claimed
as permanent repository assets.

## Repository, runtime, and distribution validation

- Python 3.11.5 passed all 1,027 discovered tests in 61.203 seconds.
- Python 3.13.0 passed all 1,027 discovered tests with telemetry explicitly
  unset in 75.957 seconds and again with `BUOY_TELEMETRY=local` in 84.642
  seconds. The established enabled retriever/multi/evidence/automatic basket
  passed 116/116 and persisted 55 traces, 239 spans, and 5 events with an empty
  final queue. The disabled run created no telemetry path.
- All full runs treated `ResourceWarning` as an error and used isolated homes.
- Source validation passed with both active receipt flags true. Ranking
  validation passed 13 datasets, 369 judgments, and 90 identities. C6 passed
  at digest
  `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`
  with its expected readiness-false state.
- The 157-package offline lock check, in-memory compilation of 104 Python
  files, exact certified-source receipts, worktree/commit diff checks, and
  `git diff --check` passed.
- The validated wheel
  `buoy_search-0.5.2.dev37+g55f41fd9e-py3-none-any.whl` is 697,997 bytes with
  SHA-256
  `dd1fea749ce52ca76d0dbbed552dda228d1514a2b1e9db8a1b3524e749cfe703`.
  The 1,222,128-byte sdist has SHA-256
  `f07100d9a6a42bfac36a6e3d794aa502181a078ebd1d63393ca91d1df598273a`.
- Distribution inspection confirmed the lightweight console entry point and
  exact telemetry module bytes. A clean Python 3.11 wheel install kept absent
  status read-only, reported a controlled backlog, flushed it in 283 ms,
  produced one complete run/root span, reported healthy, enforced `0700`/
  `0600` permissions, excluded hostile sentinels, and failed closed without
  touching a symlink target.

The unchanged certified SHA-256 receipts are CLI
`92c49e943ed5918df7fe65294ff89717e2654a8e9d76317979b63198f1b98ee9`,
test CLI
`7d29b7d450ffe4ba3e780ff51f4dece392488fb75f1704e973ea65b62cd2855b`,
evidence
`78b792098ee0c49bedc7c135dffc33f4096f7d92222bc437f5d8438f1e015c7b`,
routing
`e0711bc40a90c364ca52c7a9884d29342be21e3df43950ec26033a70c2b6e9fd`,
and routing quality
`5d53624613bf5a80ad80e6d103d07cb0fab2d2a6ae2a1456e6c2709147d67aa7`.

## External effects and handoff

Validation effects were limited to isolated `/private/tmp` homes, queues,
DuckDB stores, local writer processes, caches, build artifacts, and virtual
environments. Dependency/package network access was used only for isolated
build/runtime setup. No real `~/.buoy`, credential, provider, model,
namespace, catalog/content state, remote telemetry destination, installed
tool, `develop`, `main`, release, tag, publication, or branch protection was
read or changed.

The durable effects at evidence time are the isolated task branch/worktree,
its governance and implementation commits, and these bounded closure records.
Branch publication, pull request, exact-head CI, and integration require a
later authorized integration workflow; this implementation session performs
none of them.
