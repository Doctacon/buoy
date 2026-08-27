Status: active
Created: 2026-08-20
Updated: 2026-08-27
Decision: .10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md
Amended-By: .10x/specs/routing-semantic-compatibility.md
Storage: .10x/specs/local-telemetry-v2-storage-and-migration.md
Amends: .10x/specs/local-telemetry-writer.md

# Retrieve Command Telemetry

## Purpose and scope

This specification governs version-2 local telemetry for the `buoy retrieve`
console command. It adds a command-level latency boundary while retaining the
version-1 inner retrieval pipeline as a separately named nested operation.

It covers successfully parsed retrieve invocations that dispatch the retrieve
handler:

- explicit single namespace;
- explicit multiple namespaces;
- automatic routing;
- live execution;
- preview execution selected by `--dry-run` or its `--plan` alias;
- success; and
- sanitized command failure.

It does not instrument `crawl`, `plan`, `apply`, `evals`, `catalog`, telemetry
management commands, top-level help, retrieve help, or argument-parser failures
that never dispatch the retrieve handler. It does not change retrieval,
routing, ranking, evidence, provider, output, exit-code, or preview behavior.

## Terminology

### Command duration

`command_duration_ms` is elapsed time from the earliest timestamp captured by
Buoy's lightweight console entry point before importing `buoy_search.cli`
through completion of the retrieve handler's normal stdout/stderr rendering.
It includes Buoy-owned CLI import/bootstrap, validated command preparation,
automatic routing, model/retriever initialization, the live pipeline when one
occurs, and result/error rendering.

It does not claim to include Python interpreter work before the Buoy entry
point is reached or interpreter/process teardown after Buoy returns. User
documentation MUST call it “Buoy command duration” or “near-shell command
duration,” never exact shell duration.

### Pipeline duration

`pipeline_duration_ms` is elapsed time inside the existing retriever operation.
For live retrieval it starts immediately before query embedding and ends after
the final namespace/rerank/evidence/fallback outcome or raised exception. It
excludes CLI bootstrap, automatic route selection, retrieval-model/retriever
construction, and output rendering. This is the version-2 continuation of the
meaning of `retrieval_runs_v1.duration_ms`.

Preview commands and failures before a live retriever starts have no pipeline
operation and MUST expose null `pipeline_duration_ms`.

### Execution and retrieval modes

`execution_mode` is exactly `live` or `preview`.

`retrieval_mode` is exactly `explicit_single`, `explicit_multi`, or
`automatic`. It is derived only from parsed command structure; no namespace
identifier is persisted.

## Enablement and side effects

Version-2 command telemetry is enabled only when the stripped,
case-insensitive value of `BUOY_TELEMETRY` is `local` and the stripped,
case-insensitive value of `OTEL_SDK_DISABLED` is not `true`.

When disabled, live and preview retrieve commands MUST retain zero telemetry
filesystem, process, output, network, and context side effects. When enabled,
a preview MAY publish one private version-2 telemetry envelope and request the
local writer. This opt-in local observation is the only change to preview's
old telemetry-side-effect contract. It does not authorize content retrieval or
other work prohibited by preview.

Telemetry setup, instrumentation, serialization, publication, writer-start,
status, store, or migration failure MUST NOT change the command's original
result, exception handling, exit code, stdout, stderr, provider/model calls,
route, ranking, or evidence decision.

## Trace lifecycle

### Entry timestamp

The sole console entry point MUST capture an epoch-nanosecond timestamp as its
first command-timing operation, before importing `buoy_search.cli`. It MAY
perform the existing lightweight argument dispatch needed to keep telemetry
management commands isolated. It MUST NOT import the provider-facing CLI
before capturing the timestamp.

The command trace MAY be constructed after the timestamp is captured. In that
case the private OpenTelemetry root MUST use the captured value as its explicit
start timestamp. The timestamp is process-local timing state and is never
persisted except as the governed root start time.

Tests and direct calls to `buoy_search.cli.main` that do not pass through the
console entry point MAY use the earliest timestamp captured by `cli.main`; they
must not reuse a module-import timestamp across calls.

### Materialization boundary

A command trace is persisted only after parsing and validation select the
`retrieve` handler. Help and parser failures are not observations. The
implementation MAY hold the early timestamp until dispatch is known, but it
MUST include the elapsed interval from that timestamp when it materializes the
root.

### Completion boundary

The command root ends after the retrieve handler's final normal output attempt
and immediately before the entry point returns the same exit code. If the
handler returns a nonzero exit, the command root outcome is `error`; a zero
exit is `success`. Telemetry MUST preserve existing handling of broken stdout
or stderr and MUST NOT add a stream flush solely to improve timing.

An unexpected exception escaping the handler ends the root as an error,
records only a governed generic category, republishes best effort, and
re-raises the original exception unchanged. Because no handler return code
exists in this path, the command summary MUST record `exit_code=1`, matching
generic Python process failure. This is observation semantics only and MUST NOT
catch, convert, replace, or otherwise change the escaping exception. A failure
that the handler converts into a returned exit code records that actual code.

## Version-2 trace graph

Every observation uses `buoy.observation.schema_version=2` and exactly one root
span named `buoy.retrieve.command`. Its span kind is `INTERNAL`.

The governed version-2 child names are:

- `buoy.cli.bootstrap` — entry timestamp through retrieve-handler dispatch;
- `buoy.retrieve.prepare` — parsed configuration/options and live retriever
  construction not otherwise represented;
- `buoy.routing.catalog` — automatic remote routing-catalog read and eligibility
  preparation;
- `buoy.routing.model` — automatic routing model/component loading;
- `buoy.routing.select` — automatic route selection after eligible cards and
  routing components exist;
- `buoy.retrieve.pipeline` — the retained live retriever operation;
- `buoy.query.embed` — retained query-embedding stage;
- `buoy.namespace.query` — retained route-rank-only namespace stage;
- `buoy.rerank` — retained reranking stage;
- `buoy.evidence.assess` — retained evidence stage; and
- `buoy.output.render` — normal result or error rendering inside the handler.

The bootstrap span MAY be created with explicit start and end timestamps after
handler dispatch is known. Every child timestamp MUST remain within the command
root. Stages that do not occur are absent rather than zero-duration synthetic
spans.

For live execution, exactly one `buoy.retrieve.pipeline` span exists if the
retriever operation begins, and every successful live command MUST contain
that pipeline. Its retrieval-mode attribute MUST equal the command retrieval
mode. Existing query, namespace, rerank, and evidence spans are descendants of
that pipeline span. The existing `retrieval.widened` event belongs to the
pipeline span; widening requires one governed non-null fallback reason and a
matching event. Concurrent namespace spans retain one trace ID and the correct
route-rank-only relationship.

For preview execution there is no pipeline, query, namespace, rerank, evidence,
or widening telemetry. Automatic preview MAY contain catalog, routing-model,
and route-selection spans because those operations occur in established
preview behavior. Explicit preview normally contains only bootstrap,
preparation, and rendering stages.

Stage spans MAY be nested. Consumers MUST NOT add nested durations to estimate
total elapsed time; the command and pipeline columns are authoritative for
their scopes.

## Attribute contract

The command root permits only:

- `buoy.observation.schema_version`: integer exactly 2;
- `buoy.version`: the existing bounded package-version value;
- `buoy.command.name`: string exactly `retrieve`;
- `buoy.command.execution_mode`: `live` or `preview`;
- `buoy.retrieval.mode`: `explicit_single`, `explicit_multi`, or `automatic`;
- `buoy.command.outcome`: `success` or `error`;
- `buoy.command.exit_code`: integer from 0 through 255;
- `buoy.error.type`: one governed low-cardinality command error category when
  outcome is error; and
- `buoy.retrieval.pipeline_present`: boolean.

Governed command error categories are `configuration_error`,
`catalog_error`, `routing_error`, `model_error`, `provider_call_error`,
`render_error`, and `unexpected_error`. Error categories never contain a
class/module name selected from untrusted provider data.

The pipeline span retains the version-1 root retrieval attributes: retrieval
outcome/counts/fanout, embedding labels, requested top-k/candidates, routing
reason and finite score/margin, evidence summary, widening/fallback state, and
the existing generic error category. Its allowed values and content-free
sanitization remain unchanged except that observation schema version is 2.

Bootstrap, prepare, catalog, routing-model, route-selection, and render spans
permit only governed generic error category. They MUST NOT persist durations as
attributes because span timestamps already own duration. No stage accepts a
free-form attribute.

The producer and writer independently enforce the exact name, parent, event,
attribute-key, type, enum, cardinality, timestamp, and graph contract.

## Privacy and isolation

The complete version-1 prohibited-data contract remains in force. In
particular, every version-2 resource, span, event, envelope, filename, queue
artifact, state file, receipt, database scalar/JSON value, status/migration
output, and child environment prohibits:

- query text or hash;
- command arguments or executable path;
- content, title, excerpt, citation, URL, tag, or local/repository path;
- namespace, source, site, document, row, plan, card, or provider identifier;
- embedding vector;
- API key, token, credential, header, or environment value;
- provider response;
- raw exception message, traceback, or stack trace;
- ambient OpenTelemetry resource, baggage, link, or trace context; and
- unrelated `ContextVar` state.

The command trace uses Buoy's private provider, is never installed as the
process-wide provider/current span, never inherits ambient context, and is
never eligible for outbound trace-header propagation. Only Buoy's private
session/current-parent state may be copied into namespace workers.

## Compatibility

Direct `HybridRetriever` and `MultiNamespaceRetriever` callers outside an
active command trace retain the version-1 pipeline-only producer and envelope.
Inside an active command trace, their existing `retrieval_trace` boundary MUST
create the single version-2 pipeline child and MUST NOT publish independently.
Only command-root completion publishes the complete version-2 graph.

Established command validation order, result classes, error wording, output,
call counts, and provider/model behavior remain unchanged. Instrumentation
wrappers MUST be no-op compatible and MUST not force model loading earlier than
established behavior.

## Routing certification compatibility

> Current authority note: `.10x/specs/routing-semantic-compatibility.md` supersedes the Python-byte receipt and CLI recertification requirements in this section. Command telemetry must preserve the semantic routing descriptor and established routing behavior instead.

Command instrumentation changes the exact `src/buoy_search/cli.py` bytes bound
by the active schema-v3 routing artifact. The implementation MUST NOT bypass or
weaken that receipt. Under the newer provisional-routing amendment in
`.10x/specs/automatic-routing-after-apply.md`, it MUST preserve the frozen
seven-namespace certified anchor and replace only `cli_module_sha256` with the
measured final CLI receipt, as authorized by
`.10x/decisions/superseded/buoy-recertifies-final-reviewed-cli-receipt.md`.

The final active artifact MUST retain every non-CLI semantic and receipt:
schema/revision, certified namespaces, provisional policy, models, thresholds,
suite, projection, calibration, certification, original reports, evaluator,
routing, evidence, and collect-artifact identities. Source, wheel, source
distribution, and isolated installed-package bytes MUST reproduce the new CLI
receipt and exact artifact. Focused/full tests and independent exact-commit
review MUST prove routing validation order, selection, fanout, evidence,
provider/content behavior, output, errors, and explicit bypass behavior are
unchanged.

The stopped live collector is not a quality report and MUST NOT be represented
as one. Its known missing `site-docs-aurelio-ai-v1` card remains a diagnostic
under provisional routing, not permission to invent or write a card. No
further live certification or provider mutation is authorized by this spec.
Invalid routing authority continues to stop automatic retrieval before content
access.

## Stable query contract

After store migration, `retrieval_command_runs_v2` exposes one row per
version-2 command with at least:

- trace and root span IDs;
- command start/end;
- `command_duration_ms`;
- execution mode;
- retrieval mode;
- command outcome and exit code;
- nullable pipeline span ID, start/end, and `pipeline_duration_ms`;
- nullable retained live retrieval outcome/count/fanout/fallback/evidence
  summary;
- bounded model/precision labels where known;
- requested top-k/candidates where known;
- Buoy version; and
- observation schema version exactly 2.

`retrieval_stage_latency_v2` exposes the command identity fields plus every
non-root governed stage span, including its name, parent, timestamps, duration,
status, and governed attributes. Version-1 view names and columns remain exact.

## Acceptance scenarios

1. **Explicit live success:** Given effective local telemetry and one explicit
   namespace, when live retrieval succeeds, then one version-2 command row has
   non-null command and pipeline duration, the pipeline contains the retained
   embed/namespace stages, and command duration encloses pipeline duration.
2. **Automatic live success:** Given effective local telemetry and automatic
   routing, when retrieval succeeds, then catalog/model/select stages precede
   the pipeline and command duration includes all of them.
3. **Automatic preview:** Given effective local telemetry and `--dry-run`, when
   routing preview succeeds, then one command row and routing stages persist,
   pipeline fields are null, and no content-retrieval stage/provider call is
   introduced.
4. **Explicit preview:** Given effective telemetry and an explicit preview,
   then one command row persists with null pipeline fields and no provider or
   model operation beyond established preview behavior.
5. **Pre-pipeline failure:** Given a missing credential, invalid catalog, or
   model-construction failure after retrieve dispatch, then one error command
   row persists best effort with null pipeline when it never began, existing
   stderr/exit behavior is unchanged, and no raw detail persists.
6. **Pipeline failure:** Given a provider failure after pipeline start, then
   command and pipeline are both present with governed error outcomes and the
   original command error behavior is unchanged.
7. **Disabled behavior:** Given telemetry absent, another value, or
   `OTEL_SDK_DISABLED=true`, then live and preview behavior and filesystem/
   process/context/output effects remain byte-compatible with telemetry absent.
8. **Direct library behavior:** Given no command trace, a direct retriever call
   continues to produce one valid version-1 observation with established
   duration semantics.
9. **Privacy:** Given unique sentinels in query, argv, namespaces, paths,
   content, credentials, errors, ambient resources, and unrelated context,
   exact-byte inspection finds none in any version-2 artifact or output.
10. **Timing boundaries:** Deterministic fake-clock tests prove exact root and
    pipeline boundaries. Controlled delayed subprocesses prove initialization,
    routing, and rendering delays increase command duration but not pipeline
    duration. On the reference host, five warm controlled subprocesses with a
    two-second pre-pipeline delay MUST have median parent-observed minus command
    duration no greater than 250 ms and median command duration at least 95% of
    parent-observed duration. Raw observations and host/runtime identity are
    recorded; this gate is not generalized to unrelated hosts.
11. **Failure isolation:** Every injected OpenTelemetry, clock, envelope,
    publication, writer-start, and stream failure preserves established command
    behavior and does not produce recursive telemetry.

## Exclusions

Plan/apply/crawl/eval/catalog telemetry, exact pre-interpreter/post-return shell
time, process PID/path/argv, metrics/log signals, automatic instrumentation,
OTLP/Collector/network export, query fingerprinting, subjective feedback,
retention/purge, analytics UI, provider behavior changes, ranking/evidence
changes, release, publication, installed-tool replacement, and existing live
asset/provider mutation are excluded.
