Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/2026-08-24-run-local-telemetry-v2-canary.md, .10x/decisions/superseded/one-time-local-telemetry-v2-canary.md, .10x/evidence/2026-08-24-local-telemetry-v2-canary-authorization.md, .10x/specs/retrieve-command-telemetry.md, .10x/specs/local-telemetry-v2-storage-and-migration.md, .10x/specs/local-telemetry-writer.md

# Local Telemetry V2 Canary

## Execution boundary

The canary ran on `work/local-telemetry-v2-canary` only after the ticket was
activated and committed separately as `e14e853`. The candidate came from an
owner-private detached temporary clone of exact integrated source commit
`d3ae1ba272c9ce8999332dd04058116e8a5dda0f`, tree
`38174e3d8167bbe4a7bd1afd3e1f16402ad8b7bc`. The later records commits were
never candidate source.

No command installed, replaced, removed, or invoked the user-global tool for
canary behavior. No push, pull request, merge, release, tag, workflow, main,
provider-write, catalog-write, namespace-write, content-write, credential,
model-download, or cache-repair operation occurred.

Commands below are identified by operation rather than raw argument vectors.
The approved dataset supplied query and namespace values privately at runtime;
this record contains neither those values nor retrieval output.

## Exact candidate identity

The source dataset SHA-256 was
`29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`.
The three accepted production source identities were exact:

- CLI SHA-256
  `90e7b2ddf7bbde2daaf0ccd78aa2a779d9e61946a8b7f7ae8f3512dec431ebf9`;
- telemetry envelope SHA-256
  `e1681c4c4dab0909270127fbb7b5eeffb7ea99864ca994cda406cac9c6e76b47`;
- routing authority SHA-256
  `62ec1fe8cb7e49247c24b633379a6b2553475bc0e25ce846998ea5dd77df8cf5`.

The offline build created one 722,168-byte, 77-member traversal-free wheel,
SHA-256
`38f6017cae692e280a1cc966cd67032134c084a1d2c6e90460a092331e784cc2`.
Wheel metadata, installed metadata, candidate version output, and module
metadata all reported exact Hatch-VCS version
`0.5.2.dev45+gd3ae1ba27`. The sole console entry point was
`buoy=buoy_search.entrypoint:main`. The installed distribution had 82 files
with complete relative-file/content manifest SHA-256
`d46b77f3f3972f346ec93c7246ab92f4d107e743f5c25da3cc2cd211c9e025f3`.
Its Python runtime was 3.13.0, dependency checking passed, and its installed
copies reproduced all three accepted source identities.

Candidate version/help, migration help, and read-only status passed in an
isolated empty home. The isolated home remained absent after inspection.

## User-global tool identity

Complete content-free pre/post package inspection was byte-identical:

- package `buoy-search` version `0.6.2.dev2+g796f7384e` on Python 3.13.0;
- sole entry point `buoy=buoy_search.entrypoint:main`;
- 82 installed distribution files;
- complete distribution manifest SHA-256
  `86dd1192f28930d9d216d54e5e337323ef7fc1a25d9c669faa5c4cd9728d7afc`;
- installed CLI SHA-256
  `92c49e943ed5918df7fe65294ff89717e2654a8e9d76317979b63198f1b98ee9`;
- installed envelope SHA-256
  `7b58d95df5709380b2f263dda9d58f8ef64923c950756a8d83870a0fe4ef05d4`;
- installed routing-authority SHA-256
  `745cdb76c894ef1770f6daf3d303f2b6d0ba6905098924f1cb1a8fa40e738fea`;
- Python executable path digest
  `b7345ab746dd413f5a5b779eeeb79d7c185bf8d907f1f28770464f580661d0cc`;
- complete path-bearing uv-tool-list output was identical pre/post with
  SHA-256
  `c5b482c26a34ba5a4af40c34a8fdd9bdd06a84c79b095de59f65e08b066ca399`.

The executable path itself is withheld. Its content-free path digest is
`94e9e7c70db4c62b2b072b6ca17256e77688fcf5da2b190bfe227d2736ad265f`.
Post-readback confirmed the same uv-managed symlink shape, mode 0755, target
path digest
`9b199d448fc7bb368a55e30271b2cc2ada4e5960f7b75f0e02a667dae6d5d267`,
347-byte resolved launcher, and resolved launcher SHA-256
`b16c6717cdfad76f916f9262f37bbe1ee2863926c015642d8e7f83ed23cf6281`.
The global executable was never used as the candidate and no global-tool
mutation command ran.

## Final drift gate

Immediately before migration, candidate status reported:

- output schema 2, overall `degraded`, store `upgrade_required`, store schema 1;
- exact database size 3,682,304 bytes and 12 persisted v1 runs;
- 12 receipts; zero ready, claimed, temporary, or pending bytes in both inbox
  versions;
- idle writer; no migration backup; and
- zero drops, rejections, conflicts, and write failures.

A fresh process-table scan excluded the executor and its complete ancestor set,
then found no independent telemetry writer or migration process. The database
was a private mode-0600, one-link regular file with pre-migration SHA-256
`c184c594439191c3c115f31f0e1eac180be5aca8cd3c10e1bdc7440c2864ef58`.
The fixed backup and migration scratch paths were absent. The intended
credential source was present after removing the inherited key before
command-local loading; no value was printed, copied, or persisted.

## One-time migration

The public migration operation was invoked exactly once. It exited zero with
outcome `migrated` after 1,389 ms and reported 12 migrated v1 runs, 55 spans,
one event, zero pending v2 envelopes, and a retained backup.

The immutable backup is a 3,682,304-byte, mode-0600, one-link regular file. Its
SHA-256 is exact pre-migration database SHA-256
`c184c594439191c3c115f31f0e1eac180be5aca8cd3c10e1bdc7440c2864ef58`.
The immediate schema-v2 database was 3,158,016 bytes, mode 0600, one link, and
SHA-256
`22614efa830de3134916216f198236c5d03b9585e48c842237554f12b0c8302c`.
Migration scratch and WAL were absent.

Streamed ordered v1 semantics matched pre-store, backup, and migrated store:

| Object | Rows | Ordered-value SHA-256 |
| --- | ---: | --- |
| `trace_runs` | 12 | `7864a37848a6a71bd46f14ee14f5e706f282ad2a64d0c3753d647ee95ba8b712` |
| `spans` restricted to v1 traces | 55 | `3ac44a7dd5fc04b58696f88cdf9203d62a744fd5f99ab3a8d7928fb5caea920f` |
| `span_events` restricted to v1 traces | 1 | `45dfc041080de025341b885ab41da54f7a6268930c6af812c29d8e56136599cf` |
| `retrieval_runs_v1` | 12 | `7864a37848a6a71bd46f14ee14f5e706f282ad2a64d0c3753d647ee95ba8b712` |
| `retrieval_stage_latency_v1` | 43 | `3ebd0500e594f2e1c5d2157f6729e9fa800a4403a4c9bc4d3221b8bf54a51224` |

The exact v1 view-definition SHA-256 identities were
`192e912beff4dd19d9367942ac89fcfdf03bfae49c85987fbf794a90befb3f13`
and
`8aaf49161023810a1b2dbd715a8f3c4ae960cc4f0fb6666845bf90438e0e6c3b`.
Immediate readback had zero v2 commands and stages, an idle writer, empty
queues, exact schema 2, and the retained backup.

The first post-migration read-only verifier mistakenly expected the migration
management output's own schema field to be 2. Exact integrated source defines
that management-output schema as 1 while separately reporting target store
schema 2. The verifier was corrected against source and repeated read-only;
the migration was not retried.

## Four approved observations

The approved dataset digest and the two approved case IDs were revalidated and
the private inputs were extracted only at runtime. Each command ran in its own
subshell. The inherited credential key was removed before loading the intended
repository credential source. Local telemetry was then enabled and offline
model flags were enforced. No command was retried.

All four commands exited zero, produced one valid JSON object, and persisted
exactly these content-free rows:

| Case ID | Execution / retrieval mode | Command ms | Pipeline ms | Hits | Fanout | Failures | Namespace spans | Governed stages |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `u01-dagster-purpose` | preview / explicit-single | 456.779 | null | null | null | null | 0 | bootstrap, prepare, render |
| `u01-dagster-purpose` | live / explicit-single | 43,997.248 | 2,402.982 | 5 | 1 | 0 | 1 | bootstrap, prepare, pipeline, embed, namespace, render |
| `m01-dagster-turbopuffer-quality` | live / explicit-multi | 12,571.450 | 3,255.380 | 5 | 2 | 0 | 2 | bootstrap, prepare, pipeline, embed, namespace x2, rerank, render |
| `m01-dagster-turbopuffer-quality` | live / automatic | 12,762.722 | 1,367.358 | 5 | 2 | 0 | 2 | bootstrap, prepare, routing model, catalog, routing model, select, pipeline, embed, namespace x2, rerank, evidence, render |

Every row had truthful success/zero exit, schema version 2, nonnegative command
duration, and the required nullable/non-null pipeline duration. Every live
pipeline interval was enclosed by its command interval, every span reached the
single command root, all live failure counts were zero, and automatic fanout
was two, below the maximum three.

The complete canary recorded five `buoy.namespace.query` spans. Those spans
count logical namespace operations, not physical provider invocations. Exact
integrated source first requests server-side fusion and may issue a second
provider request inside the same span when that fusion form is unsupported.
Retained telemetry records neither the selected fusion path nor physical call
count. The raw result/runtime artifacts were deleted as required and no
independent provider-call receipt was retained. Consequently this evidence does
**not** prove the ticket's at-most-six content-provider-call criterion; five
spans permit more than six physical calls if compatibility fallback occurred.

Automatic routing had one governed catalog stage. Exact catalog request counts
are not telemetry fields; their bounded read-only list/metadata/card behavior
and absence of write paths come from the exact integrated retrieval source
contract rather than an independent packet-level audit. No provider write
operation was invoked.

Raw stdout/stderr existed only as mode-private temporary files. Machine checks
inspected exit status and JSON-object shape; no retrieval values entered this
record.

## Flush, terminal state, privacy, and model assets

The governed flush operation was invoked exactly once. It exited zero after
2 ms with `empty`, snapshot 0, and zero committed/replayed/rejected/conflict/
pending counts because the detached writer had already committed all four
accepted envelopes. A process-terminal wait then proved the detached writer
had exited. Final read-only status reported:

- compatible schema-v2 store, 5,517,312 bytes;
- persisted snapshot 16 and 16 receipts;
- zero ready, claimed, temporary, or pending work;
- idle writer and retained migration backup.

The final canonical database is mode 0600, one link, 5,517,312 bytes, SHA-256
`71e39d9236f70dfd15d329584215c6132338b33179727e92080f90b6a04cdd78`.
The immutable backup retained its exact pre-migration byte identity. Migration
scratch and WAL remained absent.

The first process-terminal probe conservatively self-matched its own ancestor
command text and timed out. It did not invoke flush or any workload. The
corrected read-only probe excluded the complete executor ancestry and proved no
independent writer remained.

Privacy validation used 66 private runtime literals without printing them. It
scanned 23 telemetry artifact files totaling 9,205,190 bytes and 1,073 string
scalars across the canonical and backup databases. No approved input, argument
form, namespace value, credential, retrieved private literal, URL, raw error,
stack marker, or private path appeared. An initial private scanner included
allowed operational result values as prohibited needles; the corrected scanner
restricted the same read-only check to prohibited literal classes. No telemetry
or provider operation was repeated.

A complete three-root local model-cache manifest had 159 entries and SHA-256
`c395f5807452ede94efade87f5be77c0492911e6ac5936a85ce9aaf72ac4263f`
both before and after the commands. Offline inference therefore used the
already available pinned assets without download or cache mutation.

## Repository and external-state comparison

After observation, local `develop` and `origin/develop` remained exact
`d3ae1ba272c9ce8999332dd04058116e8a5dda0f`. Local `main` and `origin/main`
remained exact `796f7384e2c86f6fb9e10f9099dbec589f8e47e6`. The complete local tag-ref
manifest SHA-256 was
`694a5c57ab274ff15a8214623e4daf0faa46ce4997bf524ca08789a2cf02f822`.
Source and workflow diffs from the exact integrated candidate were empty. The
only repository changes are the separately committed ticket activation and
this bounded evidence/progress update on the task branch.

No ref-mutating, hosted, release, provider-write, catalog-write, namespace-
write, content-write, global-install, credential, model-download, or unrelated
cleanup command ran.

## Cleanup and limits

A post-record private-literal scan passed before cleanup. The complete temporary
runtime root was then removed, including the detached source, wheel,
environment, scripts, raw command output, and validation logs. Absence was
read back from the filesystem. The required immutable v1 backup remains exact:
3,682,304 bytes, mode 0600, one link, SHA-256
`c184c594439191c3c115f31f0e1eac180be5aca8cd3c10e1bdc7440c2864ef58`.
Migration scratch and WAL remain absent.

This is one macOS arm64 host observation of one ratified v1 store and four
approved requests. It establishes exact local artifact/store/trace facts but
not the required physical content-provider-call bound. It does not establish
other hosts, power-loss behavior, recurring operation, release readiness, or
independent network-level provider accounting. Both independent reviews failed
on the unsupported provider-call criterion; the ticket is blocked and must not
close from this evidence.

## Parent post-review readback

After execution and worker reconciliation completed, the correctness/privacy
reviewer requested sanitized parent-observed current facts. The parent rebuilt
exact integrated commit `d3ae1ba272c9ce8999332dd04058116e8a5dda0f` offline in
an owner-private temporary review environment and verified candidate version
`0.5.2.dev45+gd3ae1ba27`. The exact v2 status implementation then performed its
documented read-only inspection of the real store and reported:

- output/store schema 2 and a compatible, disabled store;
- 5,517,312 database bytes and 16 persisted snapshots;
- an empty queue with 16 receipts and zero v1/v2 ready, claimed, temporary, or
  pending work;
- retained migration backup and idle writer with null reason; and
- zero conflicts, rejections, replays, write failures, or durability
  degradation.

Read-only file and DuckDB inspection independently observed the canonical
schema-v2 database at mode 0600, one link, SHA-256
`71e39d9236f70dfd15d329584215c6132338b33179727e92080f90b6a04cdd78`,
with 12 v1 rows, 43 v1 stage rows, four v2 command rows, and 30 v2 stage rows.
The retained backup remained 3,682,304 bytes, mode 0600, one link, SHA-256
`c184c594439191c3c115f31f0e1eac180be5aca8cd3c10e1bdc7440c2864ef58`,
with 12 v1 rows, 55 spans, one event, and 43 v1 stage rows.

Read-only Git and package inspection confirmed clean task/root worktrees,
unchanged `develop`, `origin/develop`, `main`, and `origin/main`, and unchanged
global `buoy-search 0.6.2.dev2+g796f7384e`. The temporary review environment
was removed. No migration, flush, retrieve, provider/model, credential,
global-install, ref, hosted, or telemetry write operation was performed.

A broad process-text probe self-matched its own review command and is discarded
as non-evidence; no process-count claim relies on it. Exact v2 status reported
an idle writer, and the independent correctness/privacy reviewer separately
confirmed stopped-writer state through read-only fixed-state inspection.

This post-review readback corroborates the durable store, backup, global-tool,
and ref state. It cannot reconstruct the physical provider invocation count and
does not repair the blocked acceptance criterion.
