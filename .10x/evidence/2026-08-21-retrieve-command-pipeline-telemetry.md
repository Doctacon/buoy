Status: recorded
Created: 2026-08-21
Updated: 2026-08-22
Relates-To: .10x/tickets/2026-08-20-instrument-retrieve-command-pipeline-latency.md, .10x/specs/retrieve-command-telemetry.md, .10x/decisions/buoy-recertifies-routing-cli-receipt-under-provisional-policy.md, .10x/decisions/superseded/buoy-recertifies-routing-cli-for-command-telemetry.md, .10x/reviews/2026-08-22-retrieve-command-pipeline-telemetry-review.md

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
`.10x/decisions/buoy-recertifies-routing-cli-receipt-under-provisional-policy.md`.
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
