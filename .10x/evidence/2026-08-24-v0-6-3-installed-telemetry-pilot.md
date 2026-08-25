Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/done/2026-08-24-install-v0-6-3-and-run-telemetry-pilot.md, .10x/decisions/one-time-v0-6-3-global-install-and-telemetry-pilot.md, .10x/evidence/2026-08-24-v0-6-3-install-and-pilot-preparation.md

# V0.6.3 Installed Telemetry Pilot

## Execution boundary

Execution began only after independent `INSTALL-GO` on preparation commit
`5983ea27c65d1470b17c250d89d4e64d31dfd7e1`. Fresh pre-mutation checks
reproduced every artifact digest, exact release ref/tree, clean records-only
worktree, old global package identity, complete uv-tool inventory, approved
dataset digest, credential-source presence, unchanged 159-entry model-cache
manifest, compatible real schema-v2 store, empty queues, retained immutable
backup, idle writer, and absence of an independent install/writer/migration
process.

The three approved workload values were loaded privately from the digest-bound
dataset. This record contains only approved case IDs and content-free aggregate
observations. It contains no query, argv, namespace, credential, result content,
URL, provider response, raw error, stack trace, or private path component.

## Exact global installation

The exact prepared candidate was the 721,944-byte
`buoy_search-0.6.3-py3-none-any.whl`, SHA-256
`dc9080badd619c5b95b31853a11a8c694d79699a0a4ad177c754c15acdb51b0b`,
built from lightweight tag `v0.6.3`, exact commit
`4c0a04a443ddf792db9089242bca4d1e141db03d`, tree
`5c0da1521f4f82fb65dad12b262e2daa868242bc`. The exact forward command had
SHA-256 `4af7e81124dba21365d395af91e0c5cdd16939538d6f345953648b7883c566a4`.

The forward global replacement was invoked exactly once and exited zero. It
replaced uv-managed `buoy-search 0.6.2.dev2+g796f7384e` with exact
`buoy-search 0.6.3` on Python 3.13.0. Immediate and final readback proved:

- sole console entry point `buoy=buoy_search.entrypoint:main`;
- 82 installed distribution files and 109 compatible environment
  distributions;
- installed distribution manifest SHA-256
  `da728991fd2c271ac9d183c61277270ae159d2df18c8ee1de63894fb84255786`;
- environment distribution manifest SHA-256
  `c8daf722468322527a152fa127024f3191db3fc0c07d55ac75f4ca6ac7563568`;
- exact CLI SHA-256
  `90e7b2ddf7bbde2daaf0ccd78aa2a779d9e61946a8b7f7ae8f3512dec431ebf9`;
- exact entrypoint SHA-256
  `dd2f8b33a3e73c051f1cd95c6478be13c71985ca3fae34b6e0daf80fce56e089`;
- exact telemetry-envelope SHA-256
  `e1681c4c4dab0909270127fbb7b5eeffb7ea99864ca994cda406cac9c6e76b47`;
- exact routing-artifact SHA-256
  `62ec1fe8cb7e49247c24b633379a6b2553475bc0e25ce846998ea5dd77df8cf5`;
  and
- passing dependency check, version, top-level help, telemetry help, and
  read-only compatible-v2 real-home status.

Every non-Buoy uv tool remained byte-for-byte equal in the content-free tool
inventory. Immediate acceptance passed, so the rollback predicate was false
and rollback invocation count is zero. Forward authority is consumed and
rollback authority expired.

## Pre-pilot telemetry state

Before provider access, exact installed `0.6.3` reported disabled collection,
compatible schema v2, persisted snapshot 16, 16 receipts, empty v1/v2 queues,
idle writer, retained migration backup, and zero conflicts, rejections, replays,
write failures, or durability degradation.

Read-only database inspection recorded:

- canonical database: 5,517,312 bytes, mode 0600, one link, SHA-256
  `71e39d9236f70dfd15d329584215c6132338b33179727e92080f90b6a04cdd78`;
- immutable v1 backup: 3,682,304 bytes, mode 0600, one link, SHA-256
  `c184c594439191c3c115f31f0e1eac180be5aca8cd3c10e1bdc7440c2864ef58`;
- 12 preserved v1 runs; and
- four preexisting command-v2 rows.

## Three production-style observations

Exactly three commands began, once each and in the authorized order. Each used
the installed global `0.6.3`, command-local telemetry enablement, effective
OpenTelemetry, enforced offline model settings, and the intended credential
source loaded only in its private command subshell after inherited provider
credentials were removed. All three exited zero and produced one valid JSON
object. No command was retried or substituted.

| Case | Retrieval mode | Wall ms | Command ms | Pipeline ms | Outer command ms | Hits | Fanout | Failures | Namespace spans | Evidence | Widened |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `u01-dagster-purpose` | explicit single | 48,634.137 | 47,845.827 | 1,572.189 | 46,273.638 | 5 | 1 | 0 | 1 | n/a | false |
| `m01-dagster-turbopuffer-quality` | explicit multi | 10,675.437 | 9,887.648 | 1,130.154 | 8,757.494 | 5 | 2 | 0 | 2 | n/a | false |
| `m01-dagster-turbopuffer-quality` | automatic | 11,819.667 | 11,067.981 | 874.174 | 10,193.807 | 5 | 2 | 0 | 2 | supported | false |

Command duration captured 98.4%, 92.6%, and 93.6% of parent-observed wall time
respectively. Pipeline duration represented only 3.3%, 11.4%, and 7.9% of
command duration. The substantial measured latency therefore occurred outside
the nested retrieval pipeline in all three production-style samples; the
single-namespace command was the strongest example.

Every command had one root, one enclosed pipeline, source-reachable governed
stage ancestry, truthful success/zero exit, nonnegative durations, and command
scope enclosing pipeline scope. Explicit single contained bootstrap, prepare,
pipeline, embed, one namespace, and render stages. Explicit multi additionally
contained two namespace stages and rerank. Automatic contained routing model,
catalog, route-selection, two namespace, rerank, evidence, and render stages.

The complete pilot recorded five logical namespace operations, below the
ratified maximum six. Automatic fanout was two, evidence was supported, no
fallback/widening occurred, and every command returned five hits with zero
namespace failure. Physical provider transport-attempt count remains unknown;
logical spans are not represented as physical-attempt evidence. Automatic
catalog accounting remains source-bounded rather than packet-observed.

## Flush, final state, privacy, and invariants

The bounded telemetry flush was invoked exactly once and exited zero with
`outcome="empty"`, zero pending/committed/replayed/rejected/conflicting rows,
because detached writers had already committed all three observations. No
second flush occurred. The writer then reached terminal absence and status
reported idle writer plus empty queues.

Final state was:

- compatible schema v2, snapshot 19, 19 receipts, three new command rows;
- canonical database 5,779,456 bytes, mode 0600, one link, SHA-256
  `3eef4252e758b041f5826da7e0fd4b51ed12e025ae8c94e2ff04b55006791268`;
- exactly 12 preserved v1 runs;
- byte-identical immutable v1 backup at its pre-pilot identity;
- empty v1/v2 queues, idle writer, and zero conflicts, rejections, replays,
  write failures, or durability degradation; and
- no independent writer, migration, or uv replacement process.

Privacy validation used 87 private runtime literals in memory, including the
approved inputs, namespace/source identifiers, credential, result content,
URLs/paths/IDs/tags, and private runtime paths. Whole-file scanning covered the
changed canonical database and every newly modified telemetry artifact: five
files and 5,781,571 bytes. Exact new-trace scalar scanning covered 488
string/JSON values. Neither scan found a prohibited match. The scanner never
printed or persisted a private literal.

The first whole-file scanner treated generic result tags as unique binary
sentinels and found one coincidental DuckDB byte match. The corrected check
retained all tags for exact new-row scalar validation while limiting binary
whole-file checks to unique workload/content/credential values. It found zero
matches without rerunning any retrieval or flush. Likewise, the first flush
output checker expected a nonexistent `pending_after` field; correction read
the already-produced schema-v2 output's `pending` field and did not invoke a
second flush. A pre-install isolated rollback smoke checker initially expected
schema-v2 management output from the exact old binary; source-consistent
schema-v1 output, dependency check, version/help, and absent-home status all
passed without touching the global tool.

The complete 159-entry model-cache manifest remained exact at SHA-256
`c395f5807452ede94efade87f5be77c0492911e6ac5936a85ce9aaf72ac4263f`.
`develop`, `origin/develop`, `main`, `origin/main`, tag `v0.6.3`, root/task
source, release/GitHub state, and all non-Buoy tools remained unchanged. No
provider, catalog, namespace, or content write path; model download/cache
mutation; credential mutation; telemetry migration/purge; backup change; or
unrelated operation occurred.

## Cleanup and limits

The owner-private candidate, rollback, source, environment, command-output,
and analysis artifacts were retained only through durable evidence creation
and are removed before handoff. The installed global `0.6.3`, three sanitized
telemetry rows, and immutable backup remain as authorized.

This is three observations on one host and one provider/model state. It proves
released global installation, end-to-end local telemetry persistence, privacy,
and timing attribution for the three live modes. It does not establish latency
distributions, other hosts, physical request count, packet-level provider
accounting, recurring collection behavior, or a retention policy.
