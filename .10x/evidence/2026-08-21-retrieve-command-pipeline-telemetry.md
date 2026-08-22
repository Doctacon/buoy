Status: recorded
Created: 2026-08-21
Updated: 2026-08-22
Relates-To: .10x/tickets/2026-08-20-instrument-retrieve-command-pipeline-latency.md, .10x/specs/retrieve-command-telemetry.md, .10x/decisions/buoy-recertifies-final-reviewed-cli-receipt.md, .10x/decisions/superseded/buoy-recertifies-routing-cli-receipt-under-provisional-policy.md, .10x/decisions/superseded/buoy-recertifies-routing-cli-for-command-telemetry.md, .10x/reviews/2026-08-22-retrieve-command-pipeline-telemetry-review.md, .10x/reviews/2026-08-22-retrieve-command-pipeline-telemetry-rereview.md

# Retrieve Command and Pipeline Telemetry Implementation

## Observed implementation boundary

The candidate captures an epoch-nanosecond timestamp in the lightweight entry
point before provider-facing CLI import and passes it only as process-local
state. `cli.main` uses a fresh per-call timestamp when no entry timestamp is
provided, materializes telemetry only after parsed retrieve dispatch, and ends
the root after the handler's final output attempt. Help, parser failures,
validation that prevents handler dispatch, telemetry management, and other
commands do not create command observations.

One private schema-v2 root publishes one canonical envelope to `inbox-v2` at
completion. Live retriever calls convert the retained `retrieval_trace` boundary
into one nested `buoy.retrieve.pipeline`; direct retriever calls remain
standalone schema-v1 producers. Existing embed/namespace/rerank/evidence spans
and widening events retain their semantics beneath the pipeline. Disabled
telemetry is a no-op. Clock, provider/session/span, encoding, publication,
writer-start, and output failures remain isolated from established command
behavior; an output exception is re-raised unchanged and observed with
`exit_code=1` and `render_error`.

Observed graphs are:

- explicit preview: command -> bootstrap, prepare, render; no pipeline;
- automatic preview: command -> bootstrap, prepare (containing occurred
  catalog/model/select stages), render; no pipeline;
- explicit live: command -> bootstrap, prepare, pipeline -> retained retrieval
  stages, then render;
- automatic live: command -> bootstrap, prepare/routing stages, pipeline ->
  retained retrieval stages, then render;
- pre-pipeline failure: command plus only stages reached before governed error
  rendering; and
- pipeline failure: command plus error pipeline and retained reached children,
  then governed error rendering.

The producer persists only exact governed attributes. Tests place unique query,
argv, namespace, credential, raw-error, and unrelated-context sentinels at the
boundary and find none in canonical v2 bytes. The private provider still uses
an empty OpenTelemetry context and is never installed globally.

## Deterministic acceptance tests

`tests/test_retrieve_command_telemetry.py` covers explicit single/multi live,
both preview aliases, automatic live/preview, configuration/model/catalog/
routing/provider/render/unexpected failures, exact exception identity,
`exit_code=1` for escaping exceptions, direct-v1 compatibility, one v2
publication, graph/parent/null-pipeline rules, fake-clock enclosure, privacy,
ambient isolation, disabled output equivalence, and clock/session/envelope/
publication/writer failure isolation. Existing CLI, automatic routing,
retrieval, evidence, v1 telemetry, v2 storage, queue, writer, status, migration,
and distribution tests remain in force.

The dormant certification state restores the exact previously certified
collect-only artifact, SHA-256
`23fb14c49263933a2adb2299a9c04089888fb2ec734b790d9eadda2df295cbed`.
Packaged collect mode retains legacy selection. At this checkpoint, exact
active/anchored routing was injected only by tests while the initially selected
full-live-report path remained pending. The later policy reconciliation below
supersedes that path; it does not change this observed dormant state.

## Local validation before dormant certification

Host: Darwin arm64. Python runtimes: 3.11.5 and 3.13.0.

- Focused command/telemetry/storage suites: **199 passed, 197 subtests** on
  Python 3.11 and independently **199 passed, 197 subtests** on Python 3.13.
- Established CLI/routing/after-apply/evidence/activation suites: **240 passed,
  200 subtests** on Python 3.13.
- Filtered full suite excluding only separately owned stale
  `tests/test_dynamic_version.py`: **1060 passed, 979 subtests, 57 preexisting
  lxml warnings** on Python 3.11 and independently the same result on Python
  3.13.
- `py_compile`, `compileall`, offline lock check, focused Ruff `F,E9`, ranking
  validator, and `git diff --check` passed.
- An offline clean Python 3.13 wheel install in a temporary home ran an enabled
  explicit preview, flushed its v2 envelope, and reported schema version 2.
  Wheel/source hashes agreed for CLI, routing, and evidence modules; all
  telemetry runtime modules were present. No real telemetry home, installed
  tool, provider, remote, release, or branch outside this worktree changed.

Final pre-certification source hashes are:

- `src/buoy_search/cli.py`:
  `6a92ec38f39574a598befdf841855ed669535ff6b45a10bb1869785596e2fe75`;
- `src/buoy_search/routing.py`:
  `e0711bc40a90c364ca52c7a9884d29342be21e3df43950ec26033a70c2b6e9fd`;
- `src/buoy_search/evidence.py`:
  `78b792098ee0c49bedc7c135dffc33f4096f7d92222bc437f5d8438f1e015c7b`;
  and
- collect artifact:
  `23fb14c49263933a2adb2299a9c04089888fb2ec734b790d9eadda2df295cbed`.

## Dormant source identity and certification stop

Final production bytes and the exact collect-only artifact were committed at
clean dormant commit
`369c5d461f616e89df492b497175312f36b5dcc9`, tree
`ba5c3933d835e5b9d2c7f3664f4847721e880c78`. The source hashes match the
pre-commit values above. No production source changed after that commit.

The owner-authorized source-only collector was invoked from that exact clean
state with the opaque runtime credential present, offline dependency
resolution, a private mode-0700 temporary directory, mode-0077 umask, and an
absent `report.json` target. It stopped before route inference and before report
publication because the complete stable catalog read found one live namespace
without a matching card: `site-docs-aurelio-ai-v1`. The governed message was:

```text
Routing quality evaluation failed: automatic routing requires complete live namespace-card coverage; missing cards: 'site-docs-aurelio-ai-v1' (repair with reviewed buoy catalog upsert site-docs-aurelio-ai-v1 ... --approve)
```

This is an explicit certification drift/coverage stop under
`.10x/specs/bounded-prototype-routing-activation.md`; no repair, catalog write,
content query, content-resource acquisition, model inference/download, artifact
edit, or retry was attempted. Because collection stopped before serialization,
`/private/tmp/buoy-command-telemetry-dormant-369c5d4.zlHpM1/report.json` does
not exist and has no byte size or SHA-256. The preserved private collector log
is `/private/tmp/buoy-command-telemetry-dormant-369c5d4.zlHpM1/collector.log`,
mode `0600`, 223 bytes, SHA-256
`c57edb5c4b3d2d2ef85ad5cfc348dfc2ad40856a4be7136fd3ab134620c41180`.
No credential value appears in output or records.

A first mechanical invocation used a pre-created empty output file and was
rejected locally before collection because reports are no-overwrite. That empty
file was removed and contributes no certification evidence; the clean second
invocation above reached the authoritative catalog stop.

## Provisional-policy reconciliation

The stopped collector enforced the older complete-live-coverage evaluator gate.
Subsequent source/record reconciliation found newer active authority in
`.10x/decisions/buoy-derives-routing-prototypes-from-reviewed-plans.md` and
`.10x/specs/automatic-routing-after-apply.md`: unmanaged live namespaces
without cards are diagnostics, not a global routing stop, and valid catalog
drift routes provisionally while the frozen seven-namespace anchor alone owns
singleton thresholds. The known Aurelio docs gap was already independently
recorded as intentionally unregistered during catalog-v3 migration.

The owner selected local CLI-receipt recertification after this was explained.
No card semantics were invented and no card repair or further live run is
authorized. Current execution authority is
`.10x/decisions/buoy-recertifies-final-reviewed-cli-receipt.md`.
The live stop remains valid evidence of zero mutation and no report; it is not a
routing-quality failure or permission to backfill.

## Local schema-v3 CLI receipt reactivation

The schema-v3 active artifact from pre-instrumentation authority `6fd5595` has
raw SHA-256
`745cdb76c894ef1770f6daf3d303f2b6d0ba6905098924f1cb1a8fa40e738fea`.
The reactivated artifact changes exactly one JSON scalar and one text line:
`receipts.cli_module_sha256` changes from
`92c49e943ed5918df7fe65294ff89717e2654a8e9d76317979b63198f1b98ee9`
to measured final CLI receipt
`6a92ec38f39574a598befdf841855ed669535ff6b45a10bb1869785596e2fe75`.
Its new raw SHA-256 is
`c66d0bebecdda87e5d2db98f30fd9cca0885e1bf036bf0d3132e9f8357bfb2e3`.
A parsed deep-equality probe proved every other schema, revision, binding,
certified namespace, provisional policy, threshold, calibration,
certification, report, evaluator, routing, evidence, and collect-artifact
value exact. The no-argument loader accepted schema 3 / active /
`active-anchor-e559a8aa-v1`; substituting the old CLI receipt failed with the
content-free incompatible-source-receipt error.

`git diff 369c5d4 -- 'src/buoy_search/*.py'` is empty. All production Python
bytes remain identical to the clean dormant commit after the stopped collector;
only the packaged authority JSON is reactivated under the owner-selected local
receipt policy.

### Reactivated-artifact validation

- One combined command-telemetry, v1/v2 telemetry, CLI, automatic-routing,
  after-apply, routing-quality, activation, evidence, and multi-namespace suite
  passed **417 tests and 374 subtests** on Python 3.13 and independently the
  same **417 tests and 374 subtests** on Python 3.11.
- The filtered full suite, excluding only the separately owned stale
  `tests/test_dynamic_version.py` collector, passed **1060 tests and 979
  subtests** with 57 preexisting lxml warnings on Python 3.13 and independently
  the same result on Python 3.11.
- Exact privacy, ambient isolation, disabled equivalence, render/unexpected
  exception identity, clock/session/envelope/publication/writer failure, old
  source-receipt rejection, and new source-receipt acceptance cases are part of
  those passing focused suites.
- `uv lock --check --offline` resolved 157 packages. Python 3.13 compileall,
  targeted py_compile, focused Ruff `F,E9`, `git diff --check`, production-
  source equality, and the ranking validator passed. Ranking retained 13
  datasets, 369 judgments, 90 composite identities, and bundle SHA-256
  `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`.
- An offline diagnostic working-tree build produced a 719,468-byte 77-file
  wheel at SHA-256
  `b28981b46d94a08e3e573a3b5d3144314bcd74db1ea41e1657c0cb953ad8898a`
  and a 1,251,740-byte 156-file source distribution at SHA-256
  `5a2e395ec41ae77bb074fe11dbe687fff86ab5fbc24d7ce546110b0d1d252ced`.
  Source, wheel, and source distribution each reproduced exact CLI receipt
  `6a92ec38...` and artifact receipt `c66d0beb...`.
- Offline installation of that wheel and its cached dependencies into a new
  temporary Python 3.13 environment reproduced the same installed CLI and
  artifact hashes, loaded schema 3 / active / `active-anchor-e559a8aa-v1`,
  passed version output, and ran one disabled explicit preview from an isolated
  empty home. The preview created no `.buoy` path.

All build/install/pytest homes and outputs were temporary. Commands used offline
resolution and made no provider, catalog, content, credential, live collector,
real telemetry-home, installed-tool replacement, remote Git, integration,
release, or publication operation.

## Limits

This evidence does not claim the reference-host parent-observed timing gate;
that belongs to the dependent validation ticket. The diagnostic archive hashes
identify the validated working tree before its final governance commit; exact-
commit archive reproduction belongs to independent review. The stopped
collector produced no report and no quality result. Final exact-commit review
remains required before this ticket can close.

## Independent-review challenge

Three fresh reviewers returned FAIL for exact candidate `40ef5f74`. The
reported passing commands remain useful implementation observations, but they
do not support ticket closure. Independent inspection found that writer-side
v2 validation accepts incomplete/reordered success graphs and error commands
with exit code zero; retrieve-specific broken-stderr behavior regressed for
caught `RuntimeConfigError`; exact timing/graph/equivalence/failure-injection
coverage is incomplete; the privacy sentinel test does not exercise all claimed
seams/artifacts; and one documentation sentence omits previews. The accepted
findings and bounded repair requirements are recorded at
`.10x/reviews/2026-08-22-retrieve-command-pipeline-telemetry-review.md`.

## Review-repair candidate

The bounded repair working tree based on governing commit `828680d6` addresses
every accepted finding without routing or provider work:

- the independent v2 validator now requires exact bootstrap/preparation,
  returned-render, pipeline/retrieval, and mode-conditional routing graph
  cardinality, direct parentage/ancestry, truthful ordering, and success/error
  exit agreement before writer database access;
- adversarial decoder/writer tests reject missing, duplicate, reordered,
  misparented, explicit-routing, incomplete automatic success, successful live
  without embed/namespace, escaping-successful-render, and error-plus-zero
  envelopes while a later valid trace commits;
- caught retrieve `RuntimeConfigError` once again suppresses broken-stderr
  `OSError` and returns 2 in both enabled and disabled modes; exact object,
  write-attempt, result, and output behavior match;
- deterministic tests now cover explicit-multi preview under both aliases,
  exact span counts/IDs/parents/ancestry/order, automatic call equivalence,
  all governed error classes, exact fake-clock boundaries, controlled
  initialization/routing/render attribution, and a reusable no-provider
  subprocess probe for the dependent timing ticket;
- the private synchronous span processor contains exporter failures without the
  SDK writing recursive diagnostics to command stderr; provider/tracer/start,
  attribute/status/end/export/context/envelope/publication/writer/stream faults
  retain exact command behavior;
- one real entrypoint invocation uses `sys.argv`, a live fake two-namespace
  executor, unique prohibited-data and ambient-context sentinels, the real v2
  queue/writer/schema-v2 store/status/migrate paths, and exact queue/file/
  DuckDB scalar/JSON scans. Worker threads observed only the unrelated
  `ContextVar` default and no ambient OpenTelemetry current span; two governed
  namespace spans remained under the private pipeline; and
- documentation now says enabled preview command observations also grow the
  database.

No card, catalog, provider, content service, credential, model, live collector,
real telemetry home, installed tool, remote Git, integration, release, or
publication operation occurred. All retrieval/provider behavior in tests used
local fakes and temporary homes.

### Repair validation

Host remained Darwin arm64. Dual-runtime validation used Python 3.11.5 and
3.13.0 with offline dependency resolution.

- Combined affected command, v1/v2 telemetry, queue, writer, store, CLI,
  multi-namespace, automatic-routing, after-apply, routing-quality, and
  activation suites passed **403 tests** on Python 3.11 and independently
  **403 tests** on Python 3.13.
- Filtered full suites excluding only separately owned
  `tests/test_dynamic_version.py` passed **1068 tests** on Python 3.11 and
  independently **1068 tests** on Python 3.13. The only displayed library
  diagnostic was the preexisting lxml `strip_cdata` deprecation warning.
- `uv lock --check --offline` resolved 157 packages. Python 3.11 targeted
  compilation, Python 3.13 full `compileall`, Ruff `F,E9`, `git diff --check`,
  and ranking validation passed. Ranking retained 13 datasets, 369 judgments,
  90 composite identities, and bundle SHA-256
  `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`.
- Final CLI SHA-256 is
  `90e7b2ddf7bbde2daaf0ccd78aa2a779d9e61946a8b7f7ae8f3512dec431ebf9`.
  The artifact restored from `6fd5595` differs at exactly
  `receipts.cli_module_sha256`, changing old receipt `92c49e94...` to that
  measured hash; parsed deep equality found no other field. Final artifact
  SHA-256 is
  `62ec1fe8cb7e49247c24b633379a6b2553475bc0e25ce846998ea5dd77df8cf5`.
  The active loader accepted the new artifact, while a temporary source copy
  with the old receipt rejected it as an incompatible source receipt.
- The offline diagnostic build produced a 720,733-byte wheel at SHA-256
  `e44ba11f95849a63cf9c12978f4c2eacd207e4f21ea2f9bdf26725e063c64185`
  and a 1,260,741-byte source distribution at SHA-256
  `620cda378de51b4f24c347c737ad148207fa37d1a99a41795a1ab82a2d1c1ffa`.
  Source, wheel, source distribution, and isolated installed wheel reproduced
  the exact CLI/artifact hashes and active routing mode. A disabled installed
  preview under a temporary home created no `.buoy` path.

The build version reflects governing clean HEAD `828680d6` because it was
produced from the bounded dirty repair tree; source and artifact byte receipts
are final and commit-independent. Fresh exact-commit review MUST rebuild from
the committed candidate before closure. The five-run parent-observed timing
gate remains deliberately unclaimed and belongs to the dependent validation
child.

## Rereview challenge

Fresh independent rereview of exact candidate `d8e0008c` accepted most first-
round repairs but returned FAIL. Static adversarial inspection demonstrated that
the decoder still accepts command `success/0/OK` paired with an internally
consistent `error/ERROR/provider_call_error` pipeline. The controlled
subprocess probe covers initialization and render delay but not required routing
delay. The real privacy test scans artifact contents but not relative filenames
or path components. Finally, the worker-reported exact-commit package hashes
are not durable evidence and the committed record explicitly identifies its
package build as dirty-tree diagnostic output. The accepted findings and
required parent-observed exact-commit verification are bounded at
`.10x/reviews/2026-08-22-retrieve-command-pipeline-telemetry-rereview.md`.

## Second repair and immutable implementation acceptance

The bounded second repair is immutable implementation commit
`5945b047d525658d0db55dd74cee8010cf5b27b3`, tree
`c38e5cd25da9104ce2545c6fd38835357a69d18b`. Its only changed paths relative
to governing `082290b6` are:

- `src/buoy_search/telemetry_envelope.py`;
- `tests/fixtures/retrieve_command_timing_probe.py`;
- `tests/test_retrieve_command_telemetry.py`; and
- `tests/test_telemetry_v2_storage.py`.

The independent encoder/decoder now rejects command success paired with an
internally consistent error pipeline. Direct encoder and decoder cases use
`error/ERROR/provider_call_error` operation/span state; the writer case proves
three malformed envelopes receive `invalid_graph` receipts before one later
valid envelope alone reaches DuckDB. Positive controls retain success with a
partial operation and error-after-successful-pipeline render failure.

The no-provider subprocess probe now performs automatic live routing entirely
through local fakes, delays the governed route-selection call, emits model,
catalog, model, and select stages before the fake pipeline, and reports both
scope durations. The test covers initialization, routing, and rendering delays,
requires at least 30 ms outside the pipeline for each, requires pipeline duration
below 10 ms, and checks the automatic routing-stage set and ordering. This is
only controlled delay attribution; the dependent ticket's five-run parent-
observed reference-host gate was not run or claimed.

The real entrypoint privacy case now records every extant relative path and each
path component under the isolated telemetry root before and after writer/store
processing, including v2 ready names, queue directories, terminal receipts,
state/lock artifacts, and DuckDB. Every prohibited sentinel is absent from those
names as well as the existing envelope/file/status/migration/database scalar and
JSON scans. The test first proves its random telemetry-root path contains none
of the sentinels, so the assertion does not sanitize or select the root around
sentinel input.

### Dual-runtime validation

Temporary project environments used locked offline dependencies with DuckDB
1.5.4. Commands and observed results were:

- four exact repaired cases: `4 passed` on Python 3.11.5, including one rerun
  from clean immutable `5945b04`;
- affected command/storage/writer/routing suite (15 named test modules): `404
  passed, 370 subtests passed` independently on Python 3.11.5 and Python 3.13.0;
- full suite excluding only separately owned `tests/test_dynamic_version.py`:
  `1069 passed, 1017 subtests passed, 57 warnings` independently on both
  runtimes; all warnings are the existing lxml `strip_cdata` deprecation in
  `tests/test_crawler_exact_host.py`;
- `uv lock --check --offline`: 157 packages resolved;
- Python 3.11 targeted `py_compile`, Python 3.13 `compileall`, changed-file Ruff
  `--select F,E9`, `git diff --check`, and ranking validation passed;
- ranking retained 13 datasets, 369 judgments, 90 composite identities, and
  dataset bundle SHA-256
  `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`.

A broader non-gating Ruff diagnostic over all `src` and `tests` reported 21
existing F401/F402 findings in files untouched by this repair. Changed-file
Ruff passed; no unrelated cleanup was made because this ticket does not own
those baseline findings.

### Clean exact-commit package and receipt reproduction

All following checks ran after the implementation commit with clean status
before and after. Host/runtime identity was macOS 26.5.1 build 25F80, arm64;
Python 3.11.5 and 3.13.0; uv 0.11.7; pinned build backend hatchling 1.31.0 and
hatch-vcs 0.5.0. The locked test environments used DuckDB 1.5.4. The isolated
wheel install resolved offline with DuckDB 1.5.5 and OpenTelemetry API/SDK
1.44.0.

Measured source hashes are:

- CLI: `90e7b2ddf7bbde2daaf0ccd78aa2a779d9e61946a8b7f7ae8f3512dec431ebf9`;
- v2 envelope module:
  `21e87573c04161f52cdbcb86b5899f53730c24941fee46008b3ba59bbee2d47b`;
- active routing artifact:
  `62ec1fe8cb7e49247c24b633379a6b2553475bc0e25ce846998ea5dd77df8cf5`.

Compared with `6fd5595`, parsed deep equality and unified text diff found
exactly one scalar/line changed:
`/receipts/cli_module_sha256`, from
`92c49e943ed5918df7fe65294ff89717e2654a8e9d76317979b63198f1b98ee9`
to the measured CLI hash above. The clean source loader accepted schema 3,
mode `active`, revision `active-anchor-e559a8aa-v1`; an isolated source copy
with the old receipt failed specifically as an incompatible source receipt.

`uv build --offline` at exact `5945b04` produced:

- 720,613-byte wheel
  `buoy_search-0.5.2.dev70+g5945b047d-py3-none-any.whl`, SHA-256
  `0c8790a4520ae04ac5a809fb8e6f4f052e6fbf3ad8702e57c3b6c29e27755bd0`;
- 1,261,638-byte source distribution
  `buoy_search-0.5.2.dev70+g5945b047d.tar.gz`, SHA-256
  `9ef63dafc0bf3ab06bb0922cbae851855a3a46ee55478ff5a52c56988d1819f8`.

Source, wheel, source distribution, and isolated installed wheel reproduced the
three exact file hashes above. The installed package reported
`0.5.2.dev70+g5945b047d`, loaded the active routing artifact, and completed a
disabled explicit preview in an isolated empty home without creating `.buoy`.
The source distribution excludes `.10x/**` by the pinned build configuration;
therefore this evidence/ticket-only follow-up changes no package, runtime,
fixture, or test bytes relative to the accepted implementation commit.

Private raw logs remain outside the repository at
`/private/tmp/buoy-v2-accept-5945b04.QtcE8Y/`, mode 0600:

- `acceptance.log`: 2,115 bytes, SHA-256
  `e8996277ebf33eff910137473fdeb8f2c72022da0f38b7fc8d0d0ccc8980ae2d`;
- `build.log`: 1,115 bytes, SHA-256
  `b32f7c2f3448b872a0a609da3d8e375a2d6b9f720e7efb1d8ee3d72e8daa1172`;
- `package-byte-install.log`: 1,855 bytes, SHA-256
  `5a671d3e6b2105a598bd35fbe0235124e6a2e7fbbdee2fb3f94f8cdb99af4ee3`.

No provider, catalog, content, credential, model, live collector, real telemetry
home, installed tool, remote Git, integration, release, or publication action
occurred. All homes, builds, installs, package extractions, old-receipt copies,
and test environments were temporary and isolated. Fresh independent review of
immutable implementation commit `5945b04` remains mandatory; this evidence does
not close the ticket or claim the dependent external timing gate.
