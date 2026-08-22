Status: recorded
Created: 2026-08-21
Updated: 2026-08-21
Relates-To: .10x/tickets/2026-08-20-instrument-retrieve-command-pipeline-latency.md, .10x/specs/retrieve-command-telemetry.md, .10x/decisions/buoy-recertifies-routing-cli-for-command-telemetry.md

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
Packaged collect mode retains legacy selection. Exact active/anchored routing is
injected only by tests until a new measured dormant report is independently
audited and its receipts are authorized for artifact reactivation.

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

## Limits

This evidence does not claim the reference-host parent-observed timing gate;
that belongs to the dependent validation ticket. It also does not activate a
new routing artifact. The exact dormant commit/tree and 65-case report
identity/results are appended only after committing clean final source and
running the owner-authorized read-only collector from that exact state.
