Status: recorded
Created: 2026-08-22
Updated: 2026-08-22
Target: d8e0008c45954aba5bb918409e33997778ff194e
Verdict: fail
Ticket: .10x/tickets/done/2026-08-20-instrument-retrieve-command-pipeline-latency.md
Prior-Review: .10x/reviews/2026-08-22-retrieve-command-pipeline-telemetry-review.md

# Retrieve Command and Pipeline Telemetry Rereview

## Review performed

Three fresh independent reviewers inspected immutable commit `d8e0008c`, tree
`de16e562895d6e8ea535e3d8bd9238cce09054de`, after the first review-repair
round. Perspectives covered command graph/timing behavior, privacy/failure/
store boundaries, and routing/package/record acceptance.

The reviewers accepted the repaired error-plus-zero rejection, required
bootstrap/prepare/render graph, broken-stderr suppression, core automatic and
pipeline cardinalities, real `sys.argv` and multi-worker privacy seam, ambient
context exclusion, private synchronous exporter failure containment, empty
writer environment, pre-store independent decode, one-field routing receipt,
fail-closed installed-byte validation, absence of static routing-semantic drift,
and preview-inclusive storage documentation.

## Findings

### High — command success can contain an error pipeline

The independent decoder validates pipeline outcome/status/error agreement
internally but does not reconcile it with the command summary. A canonical live
trace mutated to retain command `success`, exit 0, and root `OK` while changing
the operation to `error`, pipeline status to `ERROR`, and pipeline generic error
to `provider_call_error` is accepted. This graph is unreachable: an escaping or
returned pipeline failure produces an error command. Reject pipeline outcome
`error` when command outcome is `success`; preserve valid command errors after a
successful pipeline, such as render failure, and valid successful commands with
partial pipeline outcomes. Add producer/decoder and writer-before-mutation
adversarial tests.

### Significant — controlled subprocess coverage omits routing delay

The reusable timing probe accepts only initialization and rendering delay, and
the subprocess test runs only those cases. The active spec and ticket allocate
controlled initialization, routing, and rendering delay attribution to this
implementation child, while only the five-run parent-observed reference-host
gate belongs to the dependent validation ticket. Add a no-provider automatic
routing case with a controlled pre-pipeline routing delay. Prove the delay
increases command duration and not pipeline duration, with routing stages
truthfully represented. Do not execute the five-run gate here.

### Significant — filename privacy is asserted only for content

The real privacy test scans queue and later file contents but does not inspect
artifact filenames or relative paths, although the active privacy contract
explicitly prohibits sentinel data in every version-2 filename. Scan every
queue, receipt, state, database, temporary, and status/migration-visible
artifact relative name under the isolated telemetry root for all prohibited
sentinels. Preserve the existing exact-byte and DuckDB scalar/JSON scans.

### Acceptance evidence — exact-commit package run is not durable

The committed evidence explicitly records a diagnostic wheel/sdist build from a
dirty repair tree based on `828680d6` and delegates exact-commit archive
reproduction to review. The worker subsequently reported exact-commit wheel and
sdist hashes, but that report is a claim and was not added to durable evidence.
The routing/package reviewer could not execute commands, so package acceptance
remains unsupported rather than disproven. After source repairs are committed,
a parent-observed clean exact-commit run must record HEAD/tree/clean status,
CLI/artifact hashes, one-line and one-field equality to `6fd5595`, strict old
receipt rejection/new receipt acceptance, offline wheel/sdist hashes, source/
archive/isolated-install byte agreement, runtime versions including DuckDB, and
post-run clean status. Temporary isolated output only.

## Verdict

FAIL. The first repair round closes most prior findings but leaves one impossible
writer graph, one required controlled timing case, one explicit privacy surface,
and exact-commit package evidence unresolved.

## Limits

The reviewers' harness did not expose shell/Git execution, so their runtime
observations were static. Parent inspection separately confirmed HEAD
`d8e0008c`, tree `de16e562`, clean status, CLI SHA-256 `90e7b2dd...`, artifact
SHA-256 `62ec1fe8...`, and exact parsed equality to `6fd5595` except the CLI
receipt. Those checks do not replace the required post-repair package run.
No provider, catalog, content, credential, live collector, or external state
operation is authorized by this review.
