Status: recorded
Created: 2026-08-22
Updated: 2026-08-22
Target: 40ef5f74cdd074c25c5adbbe5e5a6a71bb4d9a27
Verdict: fail
Ticket: .10x/tickets/done/2026-08-20-instrument-retrieve-command-pipeline-latency.md
Evidence: .10x/evidence/2026-08-21-retrieve-command-pipeline-telemetry.md
Specifications: .10x/specs/retrieve-command-telemetry.md, .10x/specs/local-telemetry-v2-storage-and-migration.md

# Retrieve Command and Pipeline Telemetry Review

## Review performed

Three fresh independent reviewers inspected exact commit `40ef5f74`, tree
`7da8af9dcf6b10827e009b1042816a26e1d8134a`, the complete
`d51f927..40ef5f74` range, active records, implementation, tests,
documentation, and routing receipt. Review perspectives were command/timing
correctness, adversarial privacy/failure isolation, and routing/artifact
compatibility. All returned FAIL.

The reviewers verified several core boundaries: the entry timestamp precedes
provider-facing CLI import; trace materialization follows retrieve dispatch;
escaping exceptions retain identity with stored exit code 1; live retrieval
creates one nested pipeline and one command publication; private context and
local buffering avoid ambient/exporter propagation; and the schema-v3 routing
artifact changes only the measured CLI receipt under the current provisional
policy. No routing-semantic or direct-library-v1 regression was found by static
inspection.

## Accepted findings

### High — writer accepts incomplete or impossible successful command graphs

`telemetry_envelope.py` validates generic tree shape and pipeline cardinality
but does not enforce mode/outcome-dependent required stages or ordering. The
storage fixture proves a root-plus-pipeline-only live success is accepted. An
untrusted v2 envelope can therefore persist behavior the active command spec
says cannot occur.

Repair the independent decoder/writer contract with conditional cardinality,
ancestry, and ordering rules. At minimum every dispatched command has exactly
one bootstrap and prepare stage; every normally returned command has exactly
one render stage; successful live commands have exactly one pipeline with
query-embed and namespace-query descendants; preview commands have no retrieval
stages; successful automatic commands have the governed catalog/model/select
sequence before any pipeline; explicit commands have no automatic-routing
stages. Error graphs require exactly the stages that can truthfully occur and
must not synthesize unexecuted work. Add adversarial missing/duplicate/reordered/
misparented cases and update deterministic storage fixtures to valid graphs.

### High — error command with exit code zero passes independent validation

The v2 validator requires an error type but does not reject `outcome=error`
with `exit_code=0`. Enforce command outcome/exit agreement: success requires
zero; error requires 1 through 255. Add direct decoder/writer adversarial tests.

### Significant — broken stderr behavior regressed for `RuntimeConfigError`

The retrieve-specific main branch re-raises `OSError` from rendering a caught
`RuntimeConfigError`, while the established generic dispatch suppresses the
stream error and returns 2. Restore exact behavior while still recording
best-effort render failure telemetry only to the extent compatible with that
suppression. Add enabled/disabled identity tests for this exact path.

### Significant — deterministic behavior and graph coverage are incomplete

Focused tests do not yet prove explicit-multi preview; exact stage cardinality,
parent IDs, ordering, or timestamps; automatic operation/call equivalence;
mode/error stdout, stderr, exit, call-count, and validation-order equivalence;
or OpenTelemetry provider/span/context/export failure isolation. The current
clock test proves only enclosure inequalities.

Add exact fake-clock root, bootstrap, preparation, routing, pipeline, and render
boundaries plus controlled initialization/routing/render delay attribution.
Add explicit single/multi/automatic live, preview, and error graph assertions,
including both preview spellings where relevant. Expand enabled/disabled
behavior comparisons and inject session/provider/tracer/start-span/set-
attribute/status/end/export/context/publication/writer/stream failures without
encoding invented product behavior.

### Significant — privacy/isolation proof is incomplete and partly tautological

The current privacy test puts a sentinel in `sys.argv` while calling
`cli.main` with an explicit list, so that sentinel does not reach the tested
seam. It intercepts only envelope bytes and does not exercise real queue,
receipt/state, writer, DuckDB, status, or migration-visible values. It omits a
complete combination of query, argv, namespace, path, content, credential, raw
error/stack, ambient resource/baggage/link/trace, and unrelated context
sentinels, and does not cover a namespace worker.

Add a real entrypoint-to-v2-queue-to-writer-to-store sentinel test under an
isolated home, inspect exact bytes and database scalar/JSON values, and exercise
a live multi-namespace worker path with only Buoy private context propagated.
No real provider or external state is authorized.

### Minor — documentation excludes recorded previews from growth wording

`docs/telemetry.md` says the database grows with each recorded “live
retrieval,” although enabled previews now add v2 command observations. Correct
the sentence without implying disabled-preview side effects.

## Phase allocation clarification

One reviewer treated the five-run parent-observed subprocess timing gate as an
implementation-ticket blocker. The active parent plan and
`.10x/tickets/2026-08-20-validate-retrieve-command-telemetry-v2.md` deliberately
assign the reference-host five-run measurement and external shell
representativeness claim to the dependent validation child. That final gate
remains mandatory before parent closure, but it is not claimed by this ticket.
The implementation ticket still owns exact fake-clock boundaries and the
controlled delay seams/tests needed for that later measurement; those are
currently inadequate and are accepted findings above.

## Verdict

FAIL. The routing receipt and main trace architecture are plausible, but
independent writer acceptance, broken-stream compatibility, required scenario
attestation, privacy/isolation evidence, and documentation must be repaired
before exact-commit re-review.

## Residual limits

Reviewers performed static inspection and did not independently rerun the
reported package/full-suite commands. Existing evidence remains one macOS arm64
host and DuckDB 1.5.4, with the separately owned stale dynamic-version
collector excluded. The stopped live collector produced no report or quality
result and authorizes no card repair or retry.
