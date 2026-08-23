Status: recorded
Created: 2026-08-23
Updated: 2026-08-23
Target: d4c336c8289f5eda4cfadbc0b2bbe255349e62dc
Verdict: fail
Ticket: .10x/tickets/done/2026-08-20-instrument-retrieve-command-pipeline-latency.md
Prior-Review: .10x/reviews/2026-08-22-retrieve-command-pipeline-telemetry-final-review.md
Evidence-Head: 9a18b42169cde89a7d5919c263a4cedc65736f18

# Retrieve Command and Pipeline Telemetry Acceptance Review

## Review performed

Two fresh reviewers inspected immutable implementation `d4c336c8`, tree
`08863bae239f0ae442912b288bcc38e834572a0c`, cumulatively against all prior
reviews, active specifications, CLI/retriever/telemetry/writer/store source,
tests, and parent-observed exact package evidence. Parent independently proved
the records-only follow-up changes no runtime/package/test bytes and completed
clean detached wheel/sdist/archive/install acceptance.

The reviewers accepted all previously named repairs: truthful two-assessment
weak-evidence widening, namespace count/rank reconciliation, mode-specific
rerank/evidence cardinality, command-success/error-pipeline rejection, baseline-
versus-delay subprocess attribution, privacy, broken-stream compatibility,
one-field routing receipt equality, package byte agreement, and direct-v1
coverage.

## Findings

### High — automatic error traces with a pipeline may omit routing

The validator requires the complete automatic catalog/model/select graph only
when the command outcome is success. In source, automatic routing and live
retriever construction complete before `live_call` can begin. Therefore every
automatic trace containing a pipeline—whether the pipeline succeeds, fails, or
is followed by render failure—must contain the completed successful automatic
routing prerequisites.

Enforce for any automatic pipeline: initial model, catalog, route-embedder model,
select, and optional nested reranker-model cardinality/order already defined,
all with `OK` status before the pipeline. Add error-pipeline and successful-
pipeline/render-error positive cases and missing/error/reordered routing
adversarial decoder/writer cases.

Once automatic routing is reached, the initial routing-model span precedes the
credential/evidence/catalog decisions. Preserve truthful prefixes: one failed
initial model; one successful initial model followed by configuration/evidence
failure; initial model plus failed catalog; initial model/catalog plus failed
second model; and full prefix ending in failed select/nested model. Do not
synthesize unreached stages.

**Source correction recorded after review:** empty query and namespace-resolution
or `RuntimeConfigError` failure occurs inside prepare before the first routing-
model span, even when retrieval mode was classified as automatic from raw CLI
arguments. Such an error truthfully has no routing span. The safe invariant is:
an automatic pipeline or `prepare=OK` requires the complete successful routing
graph; `prepare=ERROR` with no pipeline may have zero routing stages or a
source-reachable routing prefix. This correction narrows the repair and
supersedes any reading that every automatic error must contain the initial
model.

### High — prerequisite status and retrieval ordering are under-enforced

A successful explicit trace may mark preparation `ERROR` and still pass. A
multi trace may place rerank before query embedding and still pass. Source makes
both impossible: command stage failures re-raise, and retrieval executes embed,
namespace batches, then rerank.

Enforce source-backed prerequisites and status/order:

- bootstrap is already exactly one `OK` span;
- any pipeline requires preparation `OK`; command success requires preparation
  and render `OK`; preparation `OK` implies every nested routing stage is `OK`;
- a failed prepare cannot lead to a pipeline; a failed automatic routing stage
  cannot lead to any later routing stage or pipeline;
- query embed ends before every namespace starts;
- all namespace spans end before rerank starts;
- a retrieval stage that is required as a prerequisite is `OK` before dependent
  work starts; and
- successful/partial operations have successful embed and rerank stages, while
  namespace failures remain valid only for truthful partial/error paths.

Derive an explicit reachability/status table from current `HybridRetriever`,
`MultiNamespaceRetriever`, and CLI source. Add positive embed failure, all-
namespace failure, partial failure, normal success, weak-evidence widening,
pipeline failure, preview/render failure, and automatic prefix cases plus
adversarial status/order mutations before writer database access.

While hardening this exact contract, reconcile source-backed operation summary
semantics that the same stage graph proves: success has zero namespace failures;
partial has at least one failed and one successful namespace and matching
failure count; successful/partial fanout is positive; and failure-stage counts
must not be inferred for unexpected error paths whose summary legitimately
remains at initialized defaults. Do not add semantics not established by source
and active specs.

## Accepted evidence

The acceptance review accepted parent-observed exact `d4c336c8` package
reproduction: clean identity/tree before and after, source/archive/install hash
agreement, strict old-receipt rejection/new active receipt acceptance, one-field
artifact equality, runtime versions, disabled installed preview, failed harness
attempt disclosure, and no external operation. No package rerun is needed until
source changes again; after this repair, the final exact implementation must be
reproduced once more.

## Verdict

FAIL. Prior findings are closed, but independent writer validation still admits
impossible automatic error graphs and failed/out-of-order prerequisites.

## Limits

Reviewers performed static inspection. Parent runtime evidence remains bounded
to the recorded host and runtimes. The dependent five-run reference-host timing
gate is correctly excluded from this ticket. No provider, catalog, content,
credential, model, live collector, or external-state operation is authorized.
