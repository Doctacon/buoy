Status: active
Created: 2026-08-21
Updated: 2026-08-21
Amends: .10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md, .10x/decisions/buoy-activates-certified-bounded-prototype-routing.md

# Buoy Recertifies the Routing CLI for Command Telemetry

## Context

The active bounded-routing artifact fail-closes unless the installed raw bytes
of `src/buoy_search/cli.py` match its independently certified SHA-256 receipt.
That broad receipt protects the CLI's pre-content automatic-routing order. The
command-telemetry implementation must change the same module to create governed
preparation, routing, pipeline, and rendering spans without changing routing
semantics.

The first bounded candidate correctly triggered the stop gate: its CLI SHA-256
is `cd571184fd013a7731cec55ab8ee9f2b7a26cc6333a0311f1a96b3dc9a6b5d72`,
while the active artifact records
`92c49e943ed5918df7fe65294ff89717e2654a8e9d76317979b63198f1b98ee9`.
Five established automatic-routing tests failed because the strict loader
rejected the changed bytes before credentials, catalog access, or content work.
No artifact or loader was bypassed.

This creates an active-record conflict: preserving the old receipt makes the
ratified command instrumentation unusable for automatic retrieval, while
silently replacing the hash would violate the routing activation decision and
its clean dormant-source certification protocol.

After this conflict and its effects were explained, the repository owner chose
“Re-certify CLI.” The disclosed option retains the existing safety gate and
authorizes the required clean 65-case read-only routing certification. It does
not authorize provider mutation or a broader routing-boundary redesign.

## Decision

Buoy will retain the exact active routing certification boundary and recertify
the final command-instrumented `cli.py` bytes under the existing ordered
activation protocol in
`.10x/specs/bounded-prototype-routing-activation.md`.

The implementation must:

1. restore the exact certified collect-only artifact while command telemetry
   source, tests, and documentation are completed;
2. commit one clean dormant source state containing the final production bytes;
3. run the existing source-only 65-case routing collector from that exact clean
   commit;
4. require exact equality with every frozen suite, catalog projection,
   threshold, calibration, certification, verdict, call-accounting, privacy,
   and no-mutation value in the active routing specification, except the new
   measured dormant commit/tree/report and source receipts;
5. obtain independent audit of that exact dormant report before changing the
   packaged authority;
6. update the packaged active artifact only with measured, audited receipts,
   including the final `cli_module_sha256`; and
7. rerun exact source, automatic-routing, command-telemetry, distribution, and
   installed-package validation plus independent final review.

The owner authorizes only the certification's already-governed read effects:
the complete stable routing-catalog read, 65 routing-query inferences, and 65
bounded local reranker calls. Expected accounting remains two namespace-list
pages, one metadata request, two catalog-query pages, zero shortlist/per-card
provider queries, zero content queries, zero content-resource acquisitions,
zero provider writes, and zero model downloads. Any drift or unexpected call
class stops before artifact activation.

No threshold, route algorithm, suite, card, example, projection, fanout,
evidence rule, content behavior, or output contract may change. No credential
value enters records or output.

## Alternatives considered

### Replace only the hash

Rejected. A guessed or locally recomputed hash without a clean report and audit
would launder changed control-flow bytes into an owner-approved artifact and
violate the fail-closed authority.

### Remove or narrow the CLI receipt now

Rejected for this workstream. A narrower routing-boundary module may reduce
future recertification cost, but it changes a deliberate security boundary and
requires separate architecture, specification, migration, and certification.
It is not needed to deliver the current telemetry contract.

### Keep `cli.py` byte-identical

Rejected for this implementation. Meeting the exact command-stage and render
boundaries without changing the module would require fragile runtime
monkeypatching, duplicated orchestration, or weaker direct-handler semantics.
Those alternatives increase behavior risk and do not satisfy the smallest
complete solution.

### Abandon command telemetry

Rejected by the owner. It would leave the original latency defect unresolved
and contradict the active command-telemetry decision.

## Consequences

The command-telemetry task gains one governed dormant-certification and
artifact-reactivation checkpoint. It may perform the disclosed read-only
routing certification despite the ticket's earlier no-provider-validation
exclusion; every other provider, credential, namespace, installed-tool,
release, remote, and real-telemetry-home restriction remains in force.

A report mismatch, dirty source, unexpected call class, model download,
provider mutation, content access, source change after certification, failed
audit, or failed final validation blocks activation and leaves the ticket open.
The existing artifact remains authoritative until the newly measured artifact
passes every gate. No branch integration, deployment, installed-tool
replacement, `main` change, tag, release, or publication is authorized.
