Status: active
Created: 2026-08-19
Updated: 2026-08-19
Decision: .10x/decisions/buoy-uses-a-private-local-telemetry-writer.md
Supersedes: .10x/specs/local-retrieval-telemetry.md

# Private Local Telemetry Writer

## Scope, precedence, and compatibility

This specification is the complete governing contract for Buoy retrieval
telemetry. It supersedes the direct-write contract in
`.10x/specs/local-retrieval-telemetry.md` while preserving that slice's trace,
privacy, DuckDB-v1, failure-isolation, and retrieval-equivalence behavior.

The following older requirements are replaced:

| Older requirement | Governing replacement |
| --- | --- |
| retrieval synchronously appends DuckDB | retrieval atomically publishes one sanitized envelope |
| database lock acquisition is nonblocking and may drop | a bounded queue lock linearizes publication; DuckDB retry belongs to the writer |
| `src/buoy_search/cli.py` is byte-identical | routing, evidence, and routing-quality receipts remain byte-identical; CLI may add only `telemetry status` and `telemetry flush` |

`BUOY_TELEMETRY=local` and `OTEL_SDK_DISABLED` retain their existing exact
semantics. Span names, instrumentation attributes/events, observation schema
version 1, DuckDB schema version 1, analytical views, database path, retrieval
behavior, result objects, exception wording/types, provider/model calls,
routing, ranking, evidence decisions, and normal retrieval output remain
compatible.

Enabled retrieval changes only the persistence boundary:

```text
private in-memory OpenTelemetry spans
  -> sink-side governed rows
  -> canonical trace-envelope/v1
  -> private atomic inbox publication
  -> one bounded Buoy local writer
  -> existing telemetry DuckDB v1
```

The retrieval process MAY import the installed `duckdb` package transitively
through existing CLI modules, but telemetry completion MUST NOT call
`duckdb.connect`, execute a DuckDB statement, bind a DuckDB parameter, acquire
the database-write lock, or wait for database acknowledgement. Telemetry
failure MUST remain silent and MUST NOT change retrieval behavior or output.

The distribution's sole console script is
`buoy = buoy_search.entrypoint:main`. The lightweight entry point dispatches
only top-level `telemetry` commands without importing `buoy_search.cli`; all
other arguments are forwarded unchanged to `buoy_search.cli:main`. Source and
distribution validation MUST enforce that exact sole mapping, require the
entry point and all governed telemetry runtime modules in the wheel, and
reject the former direct `cli:main` mapping or any additional console script.

## Enablement and zero-side-effect behavior

Telemetry is enabled only when the stripped, case-insensitive value of
`BUOY_TELEMETRY` is `local` and the stripped, case-insensitive value of
`OTEL_SDK_DISABLED` is not `true`. Every other state is disabled.

Disabled retrieval and dry-run/plan paths create no telemetry directory,
queue, temporary file, lock, state, receipt, database, or child process.
`telemetry status` is always available as a read-only inspection command.
`telemetry flush` MAY drain work that was published while telemetry was
enabled, but it never changes enablement or captures a new trace.

## Retained trace and privacy contract

Every observation uses `buoy.observation.schema_version=1` and exactly one
root span named `buoy.retrieve`. Permitted child names are:

- `buoy.query.embed`;
- `buoy.namespace.query`;
- `buoy.rerank`; and
- `buoy.evidence.assess`.

The only permitted event is the root event `retrieval.widened`. Namespace
spans identify a target only by one-based route rank. The producer and writer
both discard or reject anything outside the governed names and attributes.

The allowed operational values remain limited to observation/package version,
retrieval mode/outcome/counts/fanout, embedding and reranker labels, requested
top-k/candidate counts, routing reason and finite score/margin, route rank,
widening reason, rerank counts, evidence mode/status/finite score summaries,
and sanitized exception category without message or traceback.

The following are prohibited in every envelope, filename, state, receipt,
database row/JSON value, child environment, status/flush output, resource, and
identifier: query text or hash, `process.command_args`, content, title,
citation, URL, local/repository path, tag, namespace/source/site/document/row
identifier, embedding vector, API key, credential, header, environment value,
provider response, raw exception message, and stack trace.

Span exception auto-recording remains disabled. Buoy keeps a private tracer
provider, never attaches its span to process-wide OpenTelemetry context, never
inherits an ambient trace, never permits automatic outbound trace-header
propagation, and propagates only its own private session/span into executor
work. Unrelated application `ContextVar` values are not copied.

## Exact `trace-envelope/v1` contract

### Encoding and global bounds

An envelope is canonical JSON bytes produced by Python `json.dumps` with
`ensure_ascii=True`, `allow_nan=False`, `sort_keys=True`, and
`separators=(",", ":")`, then UTF-8 encoded. It has no UTF-8 BOM, leading or
trailing whitespace, or trailing newline. Its digest is lowercase SHA-256 of
those exact bytes. Parsing rejects invalid UTF-8, duplicate object keys,
nonfinite numbers, trailing data, or bytes that do not exactly equal a
canonical re-encoding of the parsed object.

Each envelope is at most 65,536 bytes. It contains exactly one run, between 1
and 256 spans, and between 0 and 1 events. Each span has at most 64 attributes
and an event has at most 3. The exact object/array shape below bounds nesting
to four JSON containers. Strings are ASCII governed enums or validated IDs;
the package version is at most 96 ASCII characters and a revision is exactly
40 lowercase hexadecimal characters.

JSON booleans never satisfy integer fields. Every counter/index is an integer
from 0 through 2,147,483,647. Epoch timestamps are integers from 0 through
253,402,300,799,999,999 UTC microseconds. Durations and operational scores are
finite JSON numbers with absolute value at most `1e308`; durations are
nonnegative.

### Top-level object

The exact keys are:

```text
envelope_schema_version  integer, exactly 1
observation_schema_version  integer, exactly 1
run  run object
spans  array of span objects
events  array of event objects
```

Unknown or missing keys are invalid. There is no raw OpenTelemetry span,
OTLP resource/scope, baggage, link, exception event, message, stack, arbitrary
JSON extension, or payload-selected path.

### Run object

The exact run keys and JSON types are:

| Key | Type and constraint |
| --- | --- |
| `trace_id` | 32 lowercase hex, nonzero |
| `root_span_id` | 16 lowercase hex, nonzero |
| `started_at_unix_us` | timestamp integer |
| `ended_at_unix_us` | timestamp integer, not before start |
| `duration_ms` | finite nonnegative number |
| `retrieval_mode` | `explicit_single`, `explicit_multi`, or `automatic` |
| `outcome` | `success`, `partial`, or `error` |
| `hit_count` | counter integer |
| `namespace_count` | counter integer |
| `initial_fanout` | counter integer |
| `final_fanout` | counter integer |
| `failure_count` | counter integer |
| `incomplete` | boolean |
| `widened` | boolean |
| `fallback_reason` | null, `empty_top1`, `failed_top1`, or `weak_top1` |
| `evidence_status` | null or a governed evidence-status value |
| `embedding_model` | `BAAI/bge-small-en-v1.5` or `custom` |
| `embedding_precision` | `float16`, `float32`, or `custom` |
| `top_k` | counter integer |
| `candidates` | counter integer |
| `buoy_version` | package-version regular expression `[0-9A-Za-z][0-9A-Za-z.+-]{0,95}` |
| `observation_schema_version` | integer, exactly 1 |

Governed evidence statuses are `unassessed`, `assessment_failed`,
`would_support`, `would_abstain`, `would_be_inconclusive`, `supported`,
`no_relevant_evidence`, and `inconclusive`.

### Span object

Each span has exactly these keys:

```text
trace_id             32 lowercase hex
span_id              16 lowercase hex, nonzero
parent_span_id       null or 16 lowercase hex, nonzero
name                 one governed span name
started_at_unix_us   timestamp integer
ended_at_unix_us     timestamp integer
duration_ms          finite nonnegative number
status_code          UNSET, OK, or ERROR
attributes           exact governed JSON object
```

Attribute JSON values are only strings, booleans, integers, or finite numbers.
All string enums and numeric rules are the retained instrumentation allowlist.
The exact keys allowed by span name are:

- `buoy.retrieve`: observation/package version; retrieval mode, outcome,
  top-k, candidates, hit/namespace/initial-fanout/final-fanout/failure counts,
  incomplete, widened, and fallback reason; embedding model/precision;
  routing selection reason/semantic score/semantic margin; evidence
  mode/status/candidates-scored/top/second/gap; and error type.
- `buoy.query.embed`: error type only.
- `buoy.namespace.query`: route rank, namespace status/hit count, and error
  type.
- `buoy.rerank`: applied, before/after-dedupe counts, governed model/revision,
  and error type.
- `buoy.evidence.assess`: evidence mode/status/candidates-scored/top/second/
  gap and error type.

Error type is one of `provider_call_error`, `reranker_error`, `runtime_error`,
`value_error`, or `unexpected_error`. Namespace status is `ok` or `failed`.
Routing selection reason is one of `unique_title_or_alias`,
`multiple_named_corpora`, `high_confidence_semantic`, `ambiguous_semantic`,
`high_confidence_prototype`, or `ambiguous_prototype`. Evidence mode is
`collect`, `shadow`, or `active`. The only reranker model literal is
`cross-encoder/ms-marco-MiniLM-L-6-v2`; its optional revision is exactly 40
lowercase hexadecimal characters. No free-form string is accepted.

### Event object

An event has exactly these keys:

```text
trace_id            same root trace ID
span_id             same root span ID
event_index         integer, exactly 0
name                retrieval.widened
occurred_at_unix_us timestamp integer
attributes          exactly initial_fanout, final_fanout, fallback_reason
```

### Graph and cross-record validation

The writer requires all of the following:

- exactly one `buoy.retrieve` span whose IDs equal the run IDs and whose
  parent is null;
- every other span has the same trace ID, a unique span ID, and the root span
  as its direct parent;
- spans are ordered by `(started_at_unix_us, span_id)` and events by
  `event_index`;
- every child/event timestamp is within the root interval and every end is at
  or after its start;
- each stored duration agrees with its timestamp difference within 0.001 ms;
- run timestamps/duration equal the root values;
- every non-null run summary equals its corresponding root attribute, while a
  null optional run field requires that root attribute to be absent;
- root attributes contain every non-null run field represented by an
  instrumentation attribute;
- a widened run has exactly one widening event whose three attributes equal
  the run fanout/reason, while a non-widened run has no event; and
- `incomplete` is true when `failure_count` is nonzero, `final_fanout` does not
  exceed `namespace_count`, and `failure_count` does not exceed
  `final_fanout`.

The producer constructs this form only after applying the same sink-side
sanitizer that currently constructs DuckDB rows. The writer validates it
independently before any database call.

## Canonical paths and supported platform

The existing root and database remain:

```text
~/.buoy/telemetry/
  telemetry.duckdb
  telemetry.duckdb.wal
  write.lock
```

The writer adds only these fixed names:

```text
  queue.lock
  writer.lock
  writer-start.lock
  writer-start-v1.json
  .writer-start-v1.tmp
  producer-accounting-v1.json
  .producer-accounting-v1.tmp
  writer-state-v1.json
  .writer-state-v1.tmp
  database-init-v1/
    telemetry.duckdb
    telemetry.duckdb.wal
  inbox-v1/
    tmp/
    ready/
    claimed/
    receipts/
```

Future envelope versions use a different sibling such as `inbox-v2`; a v1
writer neither scans nor opens it. Unknown entries inside the fixed v1 tree
make that tree unsafe and are never followed, opened as payload, moved, or
deleted automatically.

The strong writer feature is supported on POSIX only when Python exposes
descriptor-relative `mkdir/open/stat/rename/link/unlink/rmdir`,
`O_DIRECTORY`, `O_NOFOLLOW`, `O_CLOEXEC`, `fstat`, `fchmod`, regular-file
`fsync`, effective-UID ownership, and advisory file locking. Directory fsync
is attempted; recognized filesystem unsupported errors produce the explicit
durability-degraded result rather than misclassifying the platform, while
other errors follow the publication rules. Capability absence, Windows, or an
unsafe existing path fails closed: retrieval remains unchanged and creates no
new writer assets; status reports `platform_unsupported` or `unsafe_path`;
flush exits blocked. The rest of Buoy remains OS-independent.

The guarantee assumes a normal local filesystem and cooperative Buoy
processes under one OS user. Network/synchronized filesystem semantics and a
malicious process already running as the same UID are outside the guarantee.
DuckDB's path-only Python API leaves same-UID replacement outside the threat
model; the writer still compares database device/inode metadata before and
after opening.

`database-init-v1` is the sole recognized first-store scratch. The directory
and its database are each bounded to one fixed name; the optional fixed `.wal`
is the only sidecar. Each file is capped at 16,777,216 bytes. With no final
database, startup safely removes any private scratch left before final-link
publication and rebuilds from the still-pending claim. With a final database,
startup removes scratch only after proving it is either an unneeded private
scratch or the same device/inode hard-linked final database. Any unknown,
unsafe, oversized, or additional scratch entry blocks initialization and is
not deleted.

The root `telemetry.duckdb.wal` is the sole recognized final-store sidecar and
is capped at 16,777,216 bytes. Before any database open, an existing WAL must
be a current-user-owned private regular one-link file; an unsafe or oversized
sidecar blocks the store without opening either path. A safe crash-left WAL is
opened only by DuckDB under writer authority and `write.lock` so DuckDB can
recover/roll back the interrupted transaction. After clean close the writer
requires the WAL to be absent, or safely removes only an empty verified WAL
when DuckDB permits; any other remainder leaves the store blocked. Status
inspects only its metadata and reports unsafe/unverified without opening it.

Every directory is a real current-effective-user-owned directory with POSIX
mode `0700`. Every file is a real current-effective-user-owned regular file
with mode `0600` and link count one. Symlinks, hardlinks, FIFOs, sockets,
devices, foreign ownership, unsafe replacements, path traversal, and
payload-selected paths are rejected without following, writing, chmodding, or
deleting their targets. Foreign-ownership tests use mocked metadata unless the
test environment can create a genuine foreign owner.

The sole link-count exception is the governed first-store publication window:
while holding writer authority and `write.lock`, the fixed scratch database
and fixed final database may temporarily be two names with `st_nlink==2` only
after both are proven to have the same device/inode and private parent
directories. The writer immediately removes the scratch link; the next writer
does so after the specified crash point. Every other hardlink or link count is
unsafe.

Operations below the verified Buoy-home descriptor use fixed relative names
and verified directory descriptors. File creation uses
`O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`; reads use
`O_RDONLY|O_NOFOLLOW|O_CLOEXEC`; locks use verified descriptors. Every opened
descriptor is `fstat`-verified before use. Directory/file modes are repaired
only after current-user ownership is established.

## Queue names, limits, and publication

An envelope basename is `v1-` plus 32 random lowercase hexadecimal characters
plus `.json`. A temporary name has the same token and suffix `.part`. Its
unique terminal receipt is `r1-` plus the same random token plus `.json`.
Its recognized receipt-construction temporary is `r1-` plus that token plus
`.part`. Names contain no trace ID, query, namespace, timestamp, model, source,
or observation value.
Under `queue.lock`, publication tries at most eight fresh 128-bit tokens and
accepts one only when its possible tmp, ready, claimed, and receipt names are
all absent. Exhausting eight attempts is a publication failure. Receipt
creation and rotation also hold `queue.lock`, so a token cannot be recycled
between publication and acknowledgement.

Published capacity is a strict maximum of 4,096 ready-plus-claimed envelopes
and 67,108,864 bytes of their exact envelope bytes. One envelope is at most
65,536 bytes. `tmp` is separately bounded to 4,096 recognized entries and
67,108,864 bytes. Receipts are a rotating content-free history bounded to
4,096 files and 4,194,304 bytes. Before adding another, the writer safely
removes recognized receipts that are at least 121 seconds old in ascending
`(mtime_ns, basename)` order until both limits hold. Best-effort idempotent
state reconciliation later increments `receipts_rotated` once per removed
receipt. If only younger receipts
remain at the cap, the classification claim stays pending; valid later claims
may still drain. This keeps every newly published receipt observable for the
full maximum flush timeout plus a one-second polling/lock margin without
exceeding the cap.

Receipt temporaries are separately bounded to 4,096 recognized files,
4,194,304 bytes total, and 1,024 bytes each. Receipt construction exclusively
creates the `.part`, writes at most 1,024 canonical bytes, verifies and fsyncs
it, renames it to `.json`, and fsyncs the receipts directory. That rename is
terminal-receipt publication; only afterward may the matching claim be
removed.

At writer startup, a complete receipt temporary is treated as untrusted. The
writer revalidates its matching claim and, for committed/replayed/conflict,
the exact database terminal condition before taking `queue.lock` and
atomically renaming it to the final receipt. An invalid/partial temporary, a
temporary shadowed by a valid final receipt, or a temporary with no claim is
safely unlinked under that lock. The claim remains whenever a terminal
condition cannot be proven.

The verified `queue.lock` linearizes count/byte capacity, publication, claims,
acknowledgements, and recognized temporary cleanup across processes. A
producer publication waits at most 500 ms, polling every 5 ms; writer and
management queue operations retain the 250-ms lock bound. The 500-ms
publication bound is the smallest tested bound that admitted all 100
synchronized producers on the reference host (250 ms admitted only 93). At
exactly 4,095 entries a
conforming final envelope may publish; at 4,096, or when adding its bytes would
exceed the byte cap, the newest observation is dropped. Queue-lock timeout
also drops only the newest observation. Older published envelopes are never
evicted for capacity.

Publication performs this exact sequence while holding the queue lock:

1. securely scan tmp, ready, and claimed within their fixed bounds;
2. reject unsafe state, published capacity, or a tmp count/byte total that
   would exceed its separate cap after adding this envelope;
3. exclusively create `tmp/<random>.part`;
4. verify, fully write, `fchmod(0600)`, `fsync`, and re-verify the descriptor;
5. descriptor-relatively rename it to `ready/<same-random>.json`; and
6. `fsync` the ready directory where supported.

The rename is the publication linearization point. Failure before it carries
no delivery guarantee and may leave only a recognized temporary. Successful
publication guarantees recovery from supported process crashes, not hardware
power loss. Every directory-sync failure after rename leaves the envelope
published and recoverable, increments the lower-bound
`directory_sync_failure` accounting field when possible, and makes status
durability-degraded; it never increments `publication_failure` or attempts to
undo the rename. A file-sync failure before rename is a publication failure.

A writer removes recognized, safely owned temporary files only when their
mtime is at least 86,400 seconds old. It never describes unlink as secure
erasure. Unrecognized or unsafe entries are left untouched and block the v1
queue.

## Accounting and content-free receipts

`producer-accounting-v1.json` has exactly:

```text
schema_version: 1
queue_full: nonnegative 64-bit integer
queue_lock_timeout: nonnegative 64-bit integer
publication_failure: nonnegative 64-bit integer
directory_sync_failure: nonnegative 64-bit integer
writer_start_failure: nonnegative 64-bit integer
updated_at_unix_ms: nonnegative integer or null
accounting_incomplete: boolean
```

Producer counters are lower bounds because the same failure may prevent their
update. Updates use canonical JSON, a private same-directory temporary,
file/directory synchronization, and atomic replacement while holding the
queue lock when available. Invalid prior accounting is not trusted; it is left
untouched, status reports incomplete, and the retrieval path remains silent.
Counters saturate at `9,223,372,036,854,775,807`; attempted saturation sets
`accounting_incomplete=true`.

The three root state temporaries are the exact fixed names shown in the path
table. Their maxima are 4,096 bytes for producer accounting, 256 bytes for the
start lease, and 262,144 bytes for writer state. Their respective queue,
start, or lifetime lock serializes construction. Readers ignore a recognized
temporary; the next authorized producer/writer replaces or safely removes it
after verifying type, owner, mode, and link count. No arbitrary state-temp name
is accepted.

`producer_dropped_lower_bound` is the saturating sum of `queue_full`,
`queue_lock_timeout`, and `publication_failure`. `writer_start_failure` is
reported separately because a successfully published envelope remains
recoverable even when its immediate start attempt fails.
`directory_sync_failure` is also separate because its envelope crossed the
publication point; any nonzero value makes `durability_degraded=true`.

Each terminal receipt has exactly:

```text
schema_version: 1
kind: committed, replayed, rejected, or conflict
source_name: recognized random envelope basename
envelope_sha256: 64 lowercase hex or null
digest_complete: boolean
envelope_bytes: integer from 0 through 9223372036854775807
recorded_at_unix_ms: nonnegative integer
reason: null or one bounded governed reason code
```

Reason codes are `invalid_utf8`, `invalid_json`, `noncanonical_json`,
`unsupported_envelope_version`, `invalid_shape`, `invalid_value`,
`invalid_graph`, `oversized`, and `trace_conflict`. `envelope_sha256` is a
64-hex string and `digest_complete=true` only when the complete claimed file
was read within the 65,536-byte bound. For `oversized`, the digest is null,
`digest_complete=false`, and `envelope_bytes` is the verified descriptor size;
the writer does not read or hash the oversized payload. Parser/exception text
and payload bytes never enter receipts or output. `committed` and `replayed`
require `reason=null`, a complete digest, and the exact valid-envelope byte
count; rejected/conflict receipts require their matching reason. Every claim
is removed only after its unique receipt is durable; aggregate writer state is
reconciled afterward and is not part of acknowledgement authority. If receipt
creation fails, the claim remains and later valid envelopes may still drain.
If a crash leaves both a valid receipt and its claim, the next writer
validates the receipt and terminal database condition, retains the existing
receipt classification, and acknowledges the claim without creating a second
receipt.

`writer-state-v1.json` is canonical JSON with exactly:

```text
schema_version: 1
phase: starting, idle, draining, blocked, or stopped
reason: governed writer reason code or null
heartbeat_unix_ms: nonnegative integer
last_writer_commit_unix_ms: nonnegative integer or null
store_state: absent, compatible, incompatible, busy, unreadable, or unsafe
store_schema_version: 1 or null
persisted_runs_snapshot: nonnegative 64-bit integer or null
database_device: nonnegative integer or null
database_inode: nonnegative integer or null
database_bytes: nonnegative integer or null
rejected: nonnegative 64-bit integer
conflicts: nonnegative 64-bit integer
replays: nonnegative 64-bit integer
recovered_claims: nonnegative 64-bit integer
write_failures: nonnegative 64-bit integer
receipts_rotated: nonnegative 64-bit integer
durability_degraded: boolean
accounting_incomplete: boolean
accounted_receipts: sorted array of 0..4096 recognized receipt basenames
```

Writer state is at most 262,144 canonical bytes. Writer reason codes are
`database_busy`, `database_incompatible`,
`database_unreadable`, `unsafe_path`, `queue_unsafe`, `receipt_failure`, and
`retry_deadline`. Counters have the same saturation rule. Malformed writer
state is never trusted; status reports accounting incomplete. A writer may
replace it with a new valid state whose `accounting_incomplete` is true.

Receipt reconciliation is idempotent. A recognized receipt present on disk
but absent from `accounted_receipts` enters the sorted set; replayed, rejected,
and conflict kinds also increment their matching cumulative counter once,
while committed has no separate counter. An accounted name missing from the
receipt directory increments `receipts_rotated` once and leaves the set.
Rotation therefore unlinks selected old receipts first and then reconciles
state; a crash on either side cannot double-count. State reconciliation after
claim acknowledgement is best effort. Status supplements stored counters with
currently visible unaccounted receipts without mutating state, so reported
classification counts remain lower bounds if state is corrupt/unwritable.

`writer-start-v1.json` contains exactly schema version 1 and
`lease_started_unix_ms`. It is a 30-second spawn lease, not proof of a live
PID. No state file stores or exposes a PID.

## Writer lifecycle and fixed child boundary

After publication, the producer makes at most one best-effort start attempt.
Under the 250-ms `writer-start.lock`, it suppresses a spawn when writer state
has phase `starting`, `idle`, or `draining` with a heartbeat no older than 30
seconds, when a `blocked` heartbeat is no older than 30 seconds, or when the
start lease is younger than 30 seconds. Phase `stopped` never suppresses a
spawn. An expired lease may be atomically replaced. Failure never rolls back
the published envelope.

The exact POSIX child command is:

```text
<absolute sys.executable> -I -X utf8 -m buoy_search.telemetry_writer
```

It uses no shell, the verified telemetry directory as cwd, `stdin/stdout/
stderr=DEVNULL`, `close_fds=True`, `start_new_session=True`, and an empty
environment. The module accepts no telemetry-root argument and treats its
verified cwd as the root. Its first process action sets `umask(0o077)` before
creating state or importing the DuckDB store, so a DuckDB-created WAL is
private. It imports no provider, credential, model,
retriever, or network client. Windows spawning is unsupported by this slice.

The writer acquires `writer.lock` nonblocking for its lifetime; an extra
writer exits zero without touching the queue or database. After election it
removes a matching/expired start lease, writes an initial heartbeat, and
recovers claims. It updates heartbeat at least every 1 second between bounded
operations.

Fixed lifecycle bounds are:

- producer publication-lock wait: 500 ms, 5-ms lock poll;
- writer/management queue-, start-, and database-lock wait: 250 ms, 5-ms lock
  poll;
- inbox poll: 50 ms;
- database-busy/unavailable retry delay: 10 ms;
- one drain batch: at most 128 envelopes;
- one continuous busy/unavailable retry window: 30 seconds;
- idle exit: 60 seconds after the queue is empty;
- no-new-claim drain deadline: 300 seconds after election; and
- status heartbeat stale threshold with pending work: 35 seconds.

At the 300-second deadline the writer starts no new claim, finishes or fails
the one in-flight operation, leaves unacknowledged work recoverable, records
`retry_deadline` when possible, and exits. The deadline is not a hard wall-
clock process maximum because Python cannot safely cancel an in-flight DuckDB
filesystem call; status marks a heartbeat older than 35 seconds with pending
work stale and flush remains bounded. A later producer or explicit flush
starts another writer once lifetime authority is released. A store classified
incompatible/unsafe stops draining immediately; a transient busy store retries
within the 30-second window and then exits with work pending.

The final idle-exit decision is race-free. While still holding the lifetime
lock, the writer acquires `writer-start.lock`, performs one final bounded ready
scan, and either resumes draining or writes phase `stopped`, releases the
lifetime lock, and only then releases the start lock. Producers publish before
requesting the start lock. Therefore an envelope published before the final
scan is observed by that writer, while one published after the scan cannot
observe the old writer as active and establishes a new lease/spawn.

## Drain, transaction, replay, and crash state machine

Only the elected writer imports the telemetry DuckDB store module. Startup
first executes the receipt-temp/final-receipt recovery rules above. A claim
with a proven final receipt is acknowledged in place; a claim whose valid
receipt temp can prove its terminal condition is finalized and acknowledged.
Only then, under `queue.lock`, the writer moves each remaining recognized safe
claim without terminal receipt state back to ready. After each successful move
it best-effort reconciles one `recovered_claims` increment. It then repeats:

1. under `queue.lock`, atomically rename up to 128 ready envelopes to claimed;
2. safely open one claimed file and verify descriptor size first; if it
   exceeds 65,536 bytes, classify `oversized` without reading/hashing it;
   otherwise bounded-read at most 65,537 bytes to detect growth, re-verify,
   hash, parse, canonicalize, and independently validate it;
3. acquire the existing verified `write.lock` within 250 ms;
4. initialize atomically or open one short-lived verified read-write
   connection and validate the exact DuckDB-v1 store inside the transaction;
5. on that same connection, commit the complete run/spans/events graph and
   close it before acknowledging the envelope;
6. under `queue.lock`, rotate only eligible receipts, durably write the unique
   `committed` or `replayed` receipt, then acknowledge by unlinking the claim
   and synchronizing the claimed directory only after commit; and
7. best-effort reconcile content-free aggregate state and continue, so one
   rejected item does not stop later valid work.

The existing DuckDB schema stays byte/semantically compatible:

- `telemetry_metadata`: exactly one schema-version row plus canonical view
  digests;
- `trace_runs`: the existing 22 typed summary columns;
- `spans`: the existing 9 typed hierarchy/timing/status/JSON columns;
- `span_events`: the existing 6 typed event columns; and
- `retrieval_runs_v1` and `retrieval_stage_latency_v1`: the same code-owned
  views and layouts.

Connections disable external access, extension autoinstall/autoload, and
community extensions. Validation uses qualified DuckDB system catalog
functions, never binds an untrusted stored view, and checks exact objects,
ordered table type/nullability/key layouts, view layouts, metadata, and
canonical code-owned view definitions. No migration, repair, update, delete,
retention, compaction, upload, replication, attach, or external connection is
introduced.

First-store initialization creates the fixed private scratch directory,
builds and closes a complete DuckDB-v1 database containing the claimed trace,
requires the WAL to be absent after close, reopens read-only and validates the
whole store/trace graph, then hard-links the scratch database to the absent
final `telemetry.duckdb` without following links. The final-directory link is
the store-publication point. The writer fsyncs the telemetry directory, unlinks
the scratch name, fsyncs, and removes the empty scratch directory, leaving the
final database with link count one. A crash before the final hard link leaves
the claim plus disposable scratch and zero final store; a crash after the link
leaves a complete final store and possibly the same-inode scratch link, which
the next writer safely removes before exact replay. Direct construction of a
new final database and random `.initialize-*` directories are prohibited.

Replay compares the envelope's complete canonical run/span/event graph with
all existing v1 rows for its trace ID. Exact equality publishes a `replayed`
receipt and acknowledges the claim; best-effort receipt reconciliation then
accounts it. Any missing, extra, or differing value is `trace_conflict`, leaves
the database unchanged, publishes a content-free conflict receipt, and only
then acknowledges the conflicting claim. Aggregate state is never receipt or
acknowledgement authority.

The process-crash contract is exact:

| Injected death point | Immediate allowed state | Database delta | Next elected writer |
| --- | --- | --- | --- |
| before temp creation | no queue item | 0 | nothing to recover |
| after temp write, before ready rename | recognized `.part` may remain | 0 | ignores until safe 24-hour cleanup |
| after ready rename/directory sync | one ready envelope | 0 | claims and commits once |
| after claim rename, before transaction | one claimed envelope | 0 | returns claim to ready, increments recovery, commits once |
| after `BEGIN` or partial inserts, before commit | one claimed envelope plus optional safe final WAL | 0 after rollback/recovery | validates WAL, lets DuckDB roll back, verifies WAL cleanup, recovers and commits once |
| first-store scratch complete, before final hard link | one claimed envelope plus fixed scratch, no final store | 0 final traces | safely removes scratch, rebuilds, publishes once |
| first-store final hard link, before scratch unlink | one claimed envelope plus complete final store and same-inode scratch | exactly 1 complete trace | removes scratch link, exact-replays, receipts, unlinks claim |
| after commit, during receipt-temp write/before receipt rename | one claimed envelope plus optional recognized receipt temp | exactly 1 complete trace | removes/finishes temp safely, exact-replays, publishes one receipt, unlinks |
| after terminal-receipt rename, before claim unlink | one claimed envelope plus one final receipt | exactly 1 complete trace | validates terminal condition, retains receipt kind, unlinks |
| after claim unlink/directory sync | no envelope | exactly 1 complete trace | nothing to recover |

Supported process-crash recovery promises one complete trace after a
subsequent successful writer/flush for every successfully published valid
envelope, except an explicit conflict/rejection. It does not promise power-
loss durability, secure deletion, or observability of a failure before
publication.

The same receipt-temp crash points are injected for rejected/conflicting
claims: before the receipt rename the claim remains authoritative and is
reclassified; after it, the final receipt is authoritative and the next writer
only validates and acknowledges. A partial receipt is never terminal.

## Exact status contract

`buoy telemetry status [--json]` is read-only: it creates no path, opens no
provider/model/credential/network client, starts no writer, acquires no waiting
lock, opens no DuckDB connection, and repairs/migrates/deletes nothing. It
uses only bounded `lstat`/safe scans and canonical state snapshots. Each queue
directory scan stops after 8,193 entries or when 250 ms has elapsed between
filesystem calls; it then reports `scan_incomplete=true`. No hard wall-clock
bound is claimed for a single hostile filesystem syscall. Existing fixed
locks and `database-init-v1` are included in the metadata scan. The exact
same-inode two-link initialization publication window is recoverable and
reported `present_unverified`; every other unsafe lock, scratch entry, or
hardlink is blocked.

JSON output is one compact sorted-key object plus newline with exactly these
top-level objects/fields:

```text
schema_version: 1
requested: boolean
effective: boolean
enablement_reason: enabled, not_requested, otel_sdk_disabled, or platform_unsupported
overall: disabled, healthy, degraded, or blocked
database_path: "~/.buoy/telemetry/telemetry.duckdb"
store: {state, schema_version, bytes, persisted_runs_snapshot,
        last_writer_commit_unix_ms}
queue: {state, ready, claimed, temporary, receipts, pending_bytes,
        oldest_pending_age_ms, capacity_full, scan_incomplete}
writer: {state, reason, heartbeat_age_ms}
accounting: {producer_dropped_lower_bound, queue_full,
             queue_lock_timeout, publication_failure,
             directory_sync_failure, writer_start_failure, rejected,
             conflicts, replays,
             recovered_claims, write_failures, receipts_rotated,
             durability_degraded, incomplete}
```

Nullable numeric values are JSON null. Store state is `absent`,
`present_unverified`, `compatible`, `incompatible`, `busy`, `unreadable`, or
`unsafe`. A prior compatible writer snapshot is used only when its stored
device/inode/current byte size match current safe file metadata; otherwise the
store is `present_unverified`. Thus `persisted_runs_snapshot` and
`last_writer_commit_unix_ms` are explicitly writer snapshots, never fabricated
from trace end time or file mtime.

Queue state is `absent`, `empty`, `backlog`, `full`, `unreadable`, or `unsafe`.
Writer state is `idle`, `starting`, `active`, `stale`, `blocked`, or `unknown`.
A fresh `idle`/`draining` heartbeat yields active; a fresh `starting` phase or
start lease yields starting; pending work plus an old/missing heartbeat or
phase `stopped` without a fresh lease yields stale; blocked writer reason/store
state yields blocked; no pending work yields idle even after the last
heartbeat ages out. A stopped heartbeat never proves an active writer.

Overall precedence is blocked for unsupported platform, unsafe/unreadable
paths, incompatible store, or blocked writer; degraded for pending/full queue,
stale writer, drops/rejections/conflicts/failures, durability degradation, or
incomplete accounting; healthy for effective collection with none of those;
otherwise disabled. Exit is 0 for disabled/healthy, 1 for degraded, and 2 for
blocked.

Text output is the same content-free fields in four stable lines beginning
`Telemetry:`, `Store:`, `Queue:`, and `Writer:` followed by an `Accounting:`
line. It never includes raw exception text, payload/receipt filename, expanded
user path, environment value, or command argument.

## Exact flush contract

`buoy telemetry flush [--timeout SECONDS] [--json]` accepts a finite timeout
from 0 through 120 seconds; default is 30. It validates arguments before
creating or starting anything. Under `queue.lock`, it snapshots the recognized
ready/claimed basenames present at invocation and validates/captures in memory
the kind of any matching terminal receipt already present. It best-effort
starts a writer even when capture is currently disabled, and waits only for
that fixed snapshot. Envelopes published later are outside the request.

Flush checks at most every 50 ms. A snapshot item is terminal only when it is
gone from ready/claimed and has either its unique matching committed/replayed/
rejected/conflict receipt or the already-validated matching classification
captured at snapshot time. A matching rejection/conflict is a completed but
degraded flush. Unsupported/unsafe/incompatible/unreadable state is blocked;
busy/pending at the deadline is timeout. Flush performs no provider/model call,
database repair/migration/deletion, raw-payload output, or network access.

JSON output has exactly `schema_version`, `outcome`, `snapshot`, `committed`,
`replayed`, `rejected`, `conflicts`, `pending`, and `elapsed_ms`. Outcome is
`empty`, `flushed`, `classified`, `timeout`, or `blocked`. Exit is 0 for empty
or fully committed/replayed, 1 for classified or timeout, and 2 for blocked.
Text output reports the same counts in one content-free line.

## Performance methodology

The producer critical-path gate uses a locked persistent environment and one
deterministic in-memory retriever fixture with no provider/network/model work.
A warm elected writer and initialized temporary DuckDB are established first.
Five enabled/disabled fresh-process pairs are discarded as warmup, followed by
100 measured fresh-process pairs alternating enabled-first and disabled-first.
Each subprocess times only immediately before the retrieval call through its
return/raised exception; process startup/import and parent polling are outside
the interval. The paired delta is enabled minus disabled. Percentiles use the
sorted nearest-rank value at `ceil(p*n)-1`. Host OS/architecture, Python,
DuckDB, OpenTelemetry, filesystem, command, fixture, order, and every raw
duration/delta are recorded.

The hard warmed added-latency gates are p50 <=75 ms, p95 <=125 ms, p99 <=250
ms, and maximum <=500 ms. A probe replaces/guards `duckdb.connect` and DuckDB
connection methods in a retrieval-only process and proves zero calls.

Warm-writer visibility is measured from successful ready-rename completion to
the trace becoming queryable in `trace_runs`, polling at 10-ms intervals. Over
100 traces it must be p95 <=250 ms and p99 <=500 ms. Separately, at least three
new temporary homes characterize cold retrieval return, writer startup,
DuckDB initialization, and database visibility without clearing OS caches.
Cold retrieval remains subject to the 500-ms user-path ceiling; cold writer
visibility is reported and must complete within the maximum 120-second flush
bound. The 30-second default is changed before closure if measured cold
initialization cannot complete within it on the reference host.

## Acceptance criteria

1. Disabled/dry-run behavior is byte-compatible and creates no telemetry
   asset/process; enablement and unsupported-platform branches are exact.
2. Success/error/partial/widened traces produce canonical private envelopes
   and eventually byte/semantically identical DuckDB-v1 rows/views.
3. Exact sentinel scans find no prohibited query/content/identifier/path/
   credential/error/argv/resource value in temporary, ready, claimed, receipt,
   state, database, child environment, or command output bytes.
4. Boundary tests cover 4,095 and 4,096 entries, one byte below/at/above 64
   MiB, 64-KiB envelopes, 100 synchronized publishers, and queue-lock timeout.
   With adequate capacity, 100 successful producers flush to exactly 100
   complete trace graphs with one elected writer and no silent loss.
5. Every row of the crash table is injected and proves its exact immediate and
   second-writer queue/database/counter state.
6. Invalid UTF-8, duplicate keys, NaN/infinity, trailing bytes, huge values,
   excessive shape, unknown/missing fields, wrong version, invalid IDs,
   graph/timestamp/summary mismatches, and trace conflicts are independently
   rejected without raw quarantine or database mutation; later valid work
   drains and receipt rotation stays bounded.
7. Symlink, hardlink, FIFO/socket/device, hostile mode/owner, path replacement,
   unsafe database/final-WAL/schema/view/macro, crash-left safe WAL rollback,
   read-only/full storage, malformed state, busy locks, and unsupported
   capabilities fail closed within exact status/flush behavior. POSIX
   ownership uses real-UID tests where possible and mocked foreign `st_uid`
   otherwise.
8. The exact child command/cwd/environment/descriptor/detachment boundary is
   tested from an installed wheel; zero socket/DNS/network calls and zero
   inherited credential/arbitrary environment values are proven.
9. Status covers absent, disabled, healthy, active, backlog, full, stale,
   incompatible, unsafe/unreadable, durability-degraded, and accounting-
   incomplete states in text/JSON without mutation. Flush covers empty,
   concurrent-after-snapshot, disabled-with-backlog, classified, timeout, and
   blocked outcomes with exact exits.
10. The exact performance method passes and records warm paired deltas,
    visibility, and cold characterization.
11. Established explicit/multi/automatic/evidence tests pass with telemetry
    forced enabled, proving unchanged validation order, provider/model/rerank/
    evidence call counts, result fields/order, exceptions, fallback, routing,
    and executor behavior.
12. Focused and complete tests on Python 3.11 and 3.13, dependency lock,
    source/ranking/C6 validators, compilation, distribution, clean-wheel,
    installed-console lifecycle, privacy/no-network checks, and diff hygiene
    pass before independent exact-commit review.

## Exclusions

Standard OpenTelemetry Collector binaries/configuration, OTLP, sockets,
network listeners, remote export, cloud backends, new dependencies, DuckDB
schema migration, raw/dead-letter payload archives, general retention/purge,
analytics UI, new trace signals/instrumentation, query fingerprints, feedback,
installed-tool replacement, release, and `main` are excluded.
