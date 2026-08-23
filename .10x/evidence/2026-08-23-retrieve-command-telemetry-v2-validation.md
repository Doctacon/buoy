Status: recorded
Created: 2026-08-23
Updated: 2026-08-23
Relates-To: .10x/tickets/2026-08-20-validate-retrieve-command-telemetry-v2.md, .10x/specs/retrieve-command-telemetry.md, .10x/specs/local-telemetry-v2-storage-and-migration.md

# Retrieve Command Telemetry V2 Integrated Validation

## Identity and authority inspected

Validation began from clean records HEAD
`dd6f9ae0511225283d259bcdb44d03b0a9a9de00`. The immutable runtime
implementation is `6bfd0d4cec784cec18e9050bef4a8d0787f354e7`, tree
`269310974768aafb2d79d62c50f0753d94ac8491`. `git diff` proved that the
starting records HEAD changed no `src/`, `tests/`, `docs/`, README, changelog,
package, or lock bytes from that implementation.

Independent documentation inspection found that README and the Unreleased
changelog did not state the version-2 command/pipeline, enabled-preview, and
explicit-migration contract required by validation-ticket criterion 8. The
bounded documentation repair is commit
`c9f0f44348a51ece48cacee97c6cd6335f3f0df2`, tree
`b2656e3402548e8ca439e79405a8f21b6fb56114`; it changes only `README.md` and
`CHANGELOG.md`. Runtime and test bytes remain the immutable implementation
above.

The complete active decision and both focused specifications were reread, as
were both done dependency tickets, their additive evidence, all command and
storage review sequences, and especially these final authorities:

- `.10x/evidence/2026-08-21-retrieve-command-pipeline-telemetry.md`;
- `.10x/reviews/2026-08-23-retrieve-command-pipeline-telemetry-source-reachability-final-review.md`;
- `.10x/reviews/2026-08-23-retrieve-command-pipeline-telemetry-final-acceptance-review.md`;
- `.10x/evidence/2026-08-20-local-telemetry-v2-storage-migration.md`; and
- `.10x/reviews/2026-08-21-local-telemetry-v2-storage-migration-final-acceptance-review.md`.

Host/runtime for the fresh integrated observations was macOS 26.5.1 build
25F80, arm64, Python 3.11.5, uv 0.11.7. Locked source tests used DuckDB 1.5.4;
the accepted exact-wheel environment used DuckDB 1.5.5.

## Fresh controlled command and integrated suites

The fresh isolated-home, offline/frozen Python 3.11 command was:

```text
env -u TURBOPUFFER_API_KEY -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN \
  HOME=<mode-0700-temp-home> PYTHONPYCACHEPREFIX=<temp> \
  PYTHONDONTWRITEBYTECODE=1 BUOY_TELEMETRY= UV_NO_PROGRESS=1 \
  uv run --offline --frozen --python 3.11 --with pytest python -m pytest \
  -q -p no:cacheprovider \
  tests/test_retrieve_command_telemetry.py \
  tests/test_local_retrieval_telemetry.py \
  tests/test_telemetry_envelope.py tests/test_telemetry_producer.py \
  tests/test_telemetry_queue.py tests/test_telemetry_store.py \
  tests/test_telemetry_writer.py tests/test_telemetry_cli.py \
  tests/test_telemetry_v2_storage.py
```

Result: **212 passed, 289 subtests passed in 32.41 seconds**. The mode-0600
log is
`/private/tmp/buoy-v2-integrated-tests.O6AgP3/focused.log`, SHA-256
`8ef129fea2934419562097ec6feed90cb996def5e450954f97e00ae5d22d995f`.
This one bounded suite includes the controlled bootstrap/routing/
initialization/pipeline/render cases; live/preview and explicit/automatic
success/failure graphs; enabled/disabled output and call equivalence; direct-v1
behavior; privacy/context isolation; telemetry sink and stream faults; v1/v2
envelope, queue, store, writer, status, flush, and migration behavior; hostile
paths/schema/content; replay/conflict; shared capacity; process-death hooks;
pending-v2 lock linearization; and socket/DNS/provider-free management tests.

A first harness attempt without `--with pytest` failed before collection
because the existing project environment did not contain pytest. Adding the
cached test dependency corrected only the harness and produced the result
above.

### Controlled attribution observations

The accepted wheel's Python ran the no-provider fixture directly, with separate
zero and 500 ms subprocesses for initialization, automatic routing, and
rendering. The fixture uses local fakes, captures the entry timestamp before
provider-facing imports, and patches publication/writer start. Results were:

| Delay seam | Baseline command / pipeline ms | Delayed command / pipeline ms | Command delta ms | Absolute pipeline delta ms |
| --- | ---: | ---: | ---: | ---: |
| initialization | 331.952 / 0.090 | 728.064 / 1.065 | 396.112 | 0.975 |
| routing | 219.079 / 0.124 | 723.855 / 1.277 | 504.776 | 1.153 |
| rendering | 224.734 / 0.085 | 729.681 / 0.093 | 504.947 | 0.008 |

All command deltas were within the fixture's 375-750 ms bound and all pipeline
deltas were <=25 ms. Routing observations contained catalog, model, model, and
select spans, all ending before the pipeline. Exact fake-clock coverage in the
passing suite separately proved command 12 ms, bootstrap 1 ms, preparation 1
ms, pipeline 5 ms, embed 1 ms, namespace 1 ms, render 1 ms, exact enclosure,
and no nested-span summation. The raw mode-0600 log is
`/private/tmp/buoy-v2-controlled-probe.3Pv3eg/probe.jsonl`, SHA-256
`5a763592661d283aa92c935bbe29f503b3679b7c57a90e3de63773208e4b7786`.

These are controlled attribution observations only. They are not the five-run
reference-host timing gate.

## Exact-wheel console migration rehearsal

Before use, the parent-built files in
`/private/tmp/buoy-parent-accept-6bfd0d4.P6jVgj/dist/` were independently
hashed:

- 722,022-byte wheel SHA-256
  `8dd11b7d203797d122a709c780936553172cd9178289e7828a7a34ad010566fd`;
- 1,268,999-byte sdist SHA-256
  `65a21357da2d45e70c5434b253441cd4b81c6ccd08df97501bcf2237d3a2bef7`.

These exactly match the parent evidence. Source, wheel, sdist, and the existing
isolated wheel install were inspected, not rebuilt, and reproduced:

- `cli.py` SHA-256
  `90e7b2ddf7bbde2daaf0ccd78aa2a779d9e61946a8b7f7ae8f3512dec431ebf9`;
- `telemetry_envelope.py` SHA-256
  `e1681c4c4dab0909270127fbb7b5eeffb7ea99864ca994cda406cac9c6e76b47`;
- active routing artifact SHA-256
  `62ec1fe8cb7e49247c24b633379a6b2553475bc0e25ce846998ea5dd77df8cf5`;
- installed version `0.5.2.dev84+g6bfd0d4ce`.

This preserves, rather than replaces, the parent-observed clean-build/full-suite
provenance in the implementation evidence. No fresh full dual-runtime suite or
package build is claimed here. The documentation-only follow-up commit is not
present in those immutable implementation archives.

The exact-wheel console command was then exercised under the mode-0700
isolated home
`/private/tmp/buoy-v2-integrated-migration.VbzrPH/home`. A deterministic
fixture loaded against the installed wheel created:

- an exact schema-v1 canonical store with one v1 row;
- one distinct ready v1 envelope; and
- one valid ready v2 command envelope.

`buoy telemetry status --json` was non-creating beyond the existing fixture,
opened no database, reported the two versioned queue entries and
`present_unverified`, and exited degraded as expected without proven writer
state. The exact installed command then returned:

```json
{"backup_present":true,"database_path":"~/.buoy/telemetry/telemetry.duckdb","elapsed_ms":1001,"migrated_v1_events":0,"migrated_v1_runs":2,"migrated_v1_spans":2,"outcome":"migrated","pending_v2":1,"schema_version":1,"source_schema_version":1,"target_schema_version":2}
```

Read-only DuckDB inspection proved:

- canonical schema version 2 and retained backup schema version 1;
- the same two ordered, complete `retrieval_runs_v1` rows in canonical and
  backup databases;
- backup SHA-256
  `5f60b314f7435db7b132ea60ec483786cd7875a59932a1407bad9dcb151398b3`;
- canonical v2 metadata view identities, in v1-runs/v1-stage/v2-command/v2-stage
  order:
  `192e912beff4dd19d9367942ac89fcfdf03bfae49c85987fbf794a90befb3f13`,
  `8aaf49161023810a1b2dbd715a8f3c4ae960cc4f0fb6666845bf90438e0e6c3b`,
  `68af0f43a4906431f7b30ea8d87c61190f048eca32b87e4bf089347ba03ed200`,
  and
  `be9f2be5ed95736ab5ebb47edfa7d52a8cac42572abfe6de1f88b37d52ea8453`;
- the exact 30-column `retrieval_command_runs_v2` identity from `trace_id`
  through `observation_schema_version`; and
- zero v2 rows before explicit recovery.

`buoy telemetry flush --timeout 30 --json` returned `flushed`, snapshot 1,
committed 1, pending 0. The canonical v2 view then contained exactly one command
with command/pipeline durations `10.0/6.0` ms. After the bounded 60-second writer
idle lifetime ended, a repeated `buoy telemetry migrate --json` returned
`already_current`. The backup hash remained exact across migration, flush, and
rerun; the post-flush canonical SHA-256
`b9b7b031d550ca4342d0019f92c169837043e73ebebd983f4ba366baa779d622`
was unchanged by the rerun. Final status was healthy with empty v1/v2 queues and
schema version 2.

A first setup harness used `inspect.py`, shadowed the Python standard-library
`inspect` module, and failed before fixture creation. A second omitted the
preexisting private `.buoy` parent and failed before store creation. The first
idempotency attempt truthfully returned `busy` while the successful flush's
bounded writer still held lifetime authority; waiting for the specified
60-second idle exit and rerunning established `already_current`. None of these
harness corrections touched tracked files, a real home, or external state.

Raw summary:
`/private/tmp/buoy-v2-integrated-migration.VbzrPH/summary.json`, SHA-256
`931d8a4df565fa2b8dacd26ba4e3b974a4732aa8ed7e08cd733ab5b2c5c96356`.

## Documentation, help, and SQL

`docs/telemetry.md`, README, CHANGELOG, the installed `buoy telemetry --help`,
`buoy telemetry migrate --help`, status text, migrate text, and all published
SQL examples were inspected independently.

- The detailed guide distinguishes near-shell Buoy command duration from the
  inner pipeline, expressly denies exact shell identity, documents enabled
  preview observations, privacy/no-network behavior, explicit backed-up
  migration, immutable backup retention, and warns against adding nested stage
  durations.
- The bounded README/changelog repair adds the missing public summary without
  changing runtime behavior.
- Installed management help says management commands never contact a Collector
  or network and describes migrate as backing up and explicitly upgrading an
  exact v1 store. Empty-home status/migrate text was content-free and did not
  create `.buoy`.
- The four guide SQL examples executed read-only against the migrated exact-wheel
  fixture. Results were two v1 daily/success rows at 5.0 ms, an empty v1
  non-root-stage result, two explicit-single non-widened rows, and one v2 live
  row at command/pipeline `10.0/6.0` ms.

Targeted wording assertions and `git diff --check` passed.

## Focused-spec scenario map

### Retrieve Command Telemetry

| Material scenario/contract | Current proof |
| --- | --- |
| 1. Explicit live success | `test_explicit_single_and_multi_live_emit_one_nested_v2_pipeline`; v2 canonical/view fixtures |
| 2. Automatic live success | `test_automatic_preview_and_live_have_governed_routing_stages`; weak-evidence real fake CLI; source-reachability decoder/writer cases |
| 3. Automatic preview | automatic live/preview test proves routing stages, null pipeline, and established fake call counts |
| 4. Explicit preview | both `--dry-run`/`--plan` aliases and explicit single/multi coverage; enabled/disabled output equivalence |
| 5. Pre-pipeline failure | configuration/model/catalog/routing category and output/order cases; null-pipeline error round trip |
| 6. Pipeline failure | provider/pipeline and automatic error cases preserve command behavior and reached graph |
| 7. Disabled behavior | disabled/global-OTel no-file test; sink-failure and enabled/disabled output/call equivalence |
| 8. Direct library behavior | direct retriever v1/context-isolation case plus established v1 producer/envelope/store suites |
| 9. Privacy | real entrypoint/queue/writer/store/path-component scan; exact-byte v2 terminal-artifact scan; v1 privacy suite |
| 10. Timing boundaries | exact fake clock; controlled in-process and six subprocess observations above; parent gate still blocked below |
| 11. Failure isolation | private-provider/span/export/context/sink and clock/session/publication/writer/stream fault matrices |
| Material graph/query/routing contracts | comprehensive decoder shape/value/graph matrix, source-backed reachability/cardinality/order, writer-before-DuckDB rejection, exact v2 view fixture, final source and acceptance reviews |

### Local Telemetry V2 Storage and Migration

| Material scenario/contract | Current proof |
| --- | --- |
| 1. Absent home/store | absent status/migrate and fresh v2 initialization tests; installed empty-home management rehearsal |
| 2. Exact v1, no pending work | backed-up atomic idempotent migration test and exact-wheel rehearsal |
| 3. V1 backlog | migration snapshot test and exact-wheel two-row console rehearsal |
| 4. V2 backlog before migration | status/flush/dual-writer tests plus pending=1 migration and explicit flush recovery above |
| 5. Already current | deterministic idempotency test and exact-wheel immutable-hash rerun |
| 6. Hostile backup/scratch/store | preflight, exact-object inventory, altered v2 content, retained-backup identity, orphan state, hostile large scratch, append fail-closed matrices |
| 7. Crash table | every migration fault, mid-copy, link-publication, post-publication, backed-up retry, state-publication and queue-lock tests |
| 8. Replay/conflict | same/cross-version global atomic store and terminal-receipt cases |
| 9. View compatibility | exact schema/view fixture tests and ordered v1 query equivalence plus v2 view identities above |
| 10. Privacy | exact-byte terminal-artifact/content tests, retained-store validators, and real command path/file/database scan |
| 11. No network/provider | socket/DNS fail hooks across status/flush/producer/writer/migrate; lazy management import tests; installed empty-home commands |
| 12. Compatibility | fresh 212-test integrated suite; inherited exact dual-runtime full/package evidence; exact-wheel console lifecycle |
| Material bounds/authority | shared queue/receipt capacity, trusted-time recovery, incomplete scans, 128-trace streaming, final lock-linearized pending snapshot, exact output parity, no-auto-migration tests |

## Integrated ticket criterion status

1. Spec maps: satisfied by the two tables above.
2. Five warm parent-observed two-second subprocesses: satisfied by the parent
   observation recorded below. Median shell-minus-command was 117.155667 ms and
   median command/shell was 0.9500946372682385, passing both gates.
3. Controlled attribution: satisfied by exact fake-clock and six subprocess
   observations.
4. Built-console migration: satisfied by the isolated exact-wheel rehearsal.
5. Fault/hostile/replay/management/privacy/no-network/provider-free paths:
   satisfied by the fresh integrated suite and console observations.
6. Output/call compatibility and direct v1: satisfied by the fresh integrated
   suite.
7. Full/package/static matrix: parent exact-implementation evidence remains the
   authority for dual-runtime full, lock, compilation, Ruff, ranking, routing
   receipt, and runtime archive/install behavior. The worker independently
   verified those archive/runtime hashes before use. The parent additionally
   built the exact documentation target after criterion-8 repair and proved its
   README/changelog metadata plus unchanged runtime bytes and installed preview.
8. Public documentation/help/SQL: satisfied after bounded documentation commit
   `c9f0f44` and fresh inspection/execution.
9. Independent final integrated review: still required and not created here.

## Parent timing invocation and method

Run from this worktree after independently rechecking the wheel hash. This uses
one discarded warm-up followed by exactly five ordered, parent-timed subprocess
observations. The 2,000 ms delay is in explicit retriever initialization before
the pipeline; all provider, model, publication, and writer seams are local
fakes in the controlled fixture.

```bash
/private/tmp/buoy-parent-accept-6bfd0d4.P6jVgj/install/bin/python - <<'PY'
import json, os, statistics, subprocess, tempfile, time
from pathlib import Path

python = "/private/tmp/buoy-parent-accept-6bfd0d4.P6jVgj/install/bin/python"
probe = "/private/tmp/buoy-retrieval-command-telemetry-v2/tests/fixtures/retrieve_command_timing_probe.py"
with tempfile.TemporaryDirectory(prefix="buoy-parent-timing-") as directory:
    home = Path(directory) / "home"
    home.mkdir(mode=0o700)
    env = {
        "HOME": str(home),
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        "BUOY_TELEMETRY": "local",
    }
    argv = [python, probe, "--stage", "initialize", "--delay-ms", "2000"]
    subprocess.run(argv, check=True, capture_output=True, text=True, env=env,
                   timeout=15)  # discarded warm-up
    rows = []
    for order in range(1, 6):
        started = time.monotonic_ns()
        completed = subprocess.run(argv, check=True, capture_output=True,
                                   text=True, env=env, timeout=15)
        shell_ms = (time.monotonic_ns() - started) / 1_000_000
        assert completed.stderr == ""
        observed = json.loads(completed.stdout)
        command_ms = float(observed["command_duration_ms"])
        rows.append({
            "order": order,
            "shell_ms": shell_ms,
            "command_ms": command_ms,
            "pipeline_ms": float(observed["pipeline_duration_ms"]),
            "shell_minus_command_ms": shell_ms - command_ms,
            "command_over_shell": command_ms / shell_ms,
        })
    print(json.dumps({
        "raw": rows,
        "median_shell_minus_command_ms": statistics.median(
            row["shell_minus_command_ms"] for row in rows
        ),
        "median_command_over_shell": statistics.median(
            row["command_over_shell"] for row in rows
        ),
    }, sort_keys=True))
PY
```

The parent ran that method unchanged after independently rechecking the accepted
wheel SHA-256. Host/runtime were macOS 26.5.1 build 25F80 arm64, Python 3.11.5,
and installed package `0.5.2.dev84+g6bfd0d4ce`. The probe SHA-256 was
`f6b10ea94541f31fd046a4fe0cced08e9cffb60bf82bd45ddf120ecd1c4fe069`.
One warm-up was discarded, then these five runs occurred in order:

| Order | Shell ms | Command ms | Pipeline ms | Shell minus command ms | Command / shell |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2347.556667 | 2230.401 | 1.346 | 117.155667 | 0.9500946372682385 |
| 2 | 2352.331417 | 2234.71 | 1.25 | 117.62141699999984 | 0.9499979398523674 |
| 3 | 2344.231666 | 2227.613 | 1.165 | 116.6186660000003 | 0.9502529260689544 |
| 4 | 2353.277 | 2237.891 | 1.043 | 115.38599999999997 | 0.9509679480996075 |
| 5 | 2344.083 | 2224.819 | 1.277 | 119.26400000000012 | 0.9491212555186825 |

Median shell-minus-command was **117.155667 ms**, at or below the 250 ms
limit. Median command/shell was **0.9500946372682385**, at or above 0.95. The
reference-host timing gate therefore passed. Individual ratios were not rounded
before median evaluation.

Raw parent artifacts are under mode-0700
`/private/tmp/buoy-parent-timing-6bfd0d4.WAgXE5/`:

- mode-0600 `parent-timing.log`, 2,688 bytes, SHA-256
  `9f10c95d819caf4075a9a22f9ab7655ce9782d28057afc1f2cd0a5e615fa9790`;
- mode-0600 `timing-result.json`, 888 bytes, SHA-256
  `52df9e054b8022b6bdc4fd42b37f08bad237802750afbdb9cc9e415ed0e2ea8d`.

## Documentation-target distribution acceptance

Because criterion-8 repair changed packaged README/changelog content after the
runtime archive was accepted, the parent also built exact documentation commit
`c9f0f44348a51ece48cacee97c6cd6335f3f0df2`, tree
`b2656e3402548e8ca439e79405a8f21b6fb56114`, from a clean detached worktree.
Its only non-record differences from runtime implementation `6bfd0d4c` are
`README.md` and `CHANGELOG.md`; CLI, envelope, routing artifact, tests, package
configuration, and lock bytes are unchanged.

The offline build produced:

- 722,173-byte wheel
  `buoy_search-0.5.2.dev88+gc9f0f4434-py3-none-any.whl`, SHA-256
  `7bc7f08a638cd0d623382ce6f795ee85f790017d5f3692d936b8e1a0b602a98b`;
- 1,269,309-byte source distribution
  `buoy_search-0.5.2.dev88+gc9f0f4434.tar.gz`, SHA-256
  `ebd3575fc5fa07d376d46de23f836ae2c60258e636094a0b30e704494032763b`.

Wheel metadata and source-distribution README/changelog contain the repaired
command/pipeline, enabled-preview, explicit-migration, and privacy wording.
Source, wheel, sdist, and isolated install reproduce unchanged CLI SHA-256
`90e7b2dd...`, envelope SHA-256 `e1681c4c...`, and routing-artifact SHA-256
`62ec1fe8...`. The installed artifact loaded active schema 3 revision
`active-anchor-e559a8aa-v1`; a disabled explicit preview created no `.buoy`.
Clean identity held before and after, and the temporary worktree was removed.

Private artifacts are under mode-0700
`/private/tmp/buoy-parent-integrated-package-c9f0f44.vY43m3/`:

- mode-0600 `integrated-package.log`, 5,988 bytes, SHA-256
  `bcf203832ccd1b2bdad7d1bd6ac8216c1084a962d0b856b2af117ed80d14e05a`;
- mode-0600 `installed-preview.json`, 2,162 bytes, SHA-256
  `11b3f3a1fcbd547577df68a0f011c5a2c8477635dfcec993c0f89eda088ba487`;
- wheel and sdist with the sizes and hashes above.

## Limits and remaining blockers
- Fresh integrated runtime observations are one macOS arm64 host. Crash tests
  are deterministic process-death/fault injection, not hardware power-loss or
  unrelated-filesystem evidence.
- Exact schema/view identities were observed on DuckDB 1.5.5 and match the
  existing DuckDB-1.5.4 authority; future DuckDB identities remain
  version-sensitive.
- The fresh independent final integrated review record remains required.
- No live provider/model download/credential/catalog/content/namespace, real
  `~/.buoy`, installed-tool replacement, remote, integration, release,
  publication, automatic migration, or backup deletion occurred.
