Status: recorded
Created: 2026-08-23
Updated: 2026-08-23
Target: e28a8b173624903e6d06e6485d0e87b9da2d7e01
Verdict: fail

# Retrieve Command Telemetry Source-Reachability Review

## Target and method

Two fresh read-only reviewers cumulatively inspected exact candidate
`e28a8b173624903e6d06e6485d0e87b9da2d7e01`, including graph repair
`cb0ebea9a72f4cd4d0612581552364530fe105c8`, against the active command and
writer specifications, the prior acceptance review, CLI/retriever/telemetry
source, decoder/writer behavior, and focused tests. The parent independently
reproduced the first malformed-envelope acceptance below.

The review preserved these source-backed boundaries: an early automatic
preparation error may have no routing span; successful evidence spans may be
`UNSET` or `OK`; and error operations may retain initialized summary values.
The model-free privacy-test follow-up was accepted as deterministic and as
retaining its real entrypoint, queue, writer, store, worker-context, filename,
and content privacy seams.

## Findings

### High — evidence may precede the namespace result it consumes

`src/buoy_search/telemetry_envelope.py:2293-2309` prevents evidence/rerank
overlap and requires some successful namespace, but does not require evidence
to start after the relevant successful namespace result exists. The parent
inserted one automatic evidence span at embed completion while the successful
namespace span was still running; `decode_trace_envelope_v2` accepted it.

Current retriever source completes the initial namespace batch before an
initial assessment and completes reranking before a final assessment. The
repair must preserve both truthful forms: initial evidence after the initial
namespace batch but before rerank, and final evidence after rerank. Decoder and
writer adversarial tests must reject evidence that starts before its required
namespace result.

### High — successful automatic pipelines may omit evidence

`src/buoy_search/telemetry_envelope.py:2326-2353` bounds automatic evidence at
two spans but accepts zero for success or partial outcomes. Automatic CLI live
execution always supplies `CalibratedEvidenceAssessor`, and successful retrieval
performs either the initial assessment or final assessment; weak-top-one
widening performs both. `_automatic_v2_object()` currently masks this by
constructing an automatic success without evidence.

Require exactly one successful assessment for non-weak automatic
success/partial and exactly two for weak-top-one widening, while preserving
zero or reached-prefix cardinality for truthful automatic errors and preserving
successful span status as `UNSET` or `OK`.

### High — automatic error prefixes may stop after a successful prerequisite

`src/buoy_search/telemetry_envelope.py:2193-2210` accepts a successful catalog
with no reached second routing-model span and a successful second routing model
with no reached selection span. Under the reviewed CLI state machine, those
successful prerequisites immediately enter the next governed stage; a failure
there produces the terminal `ERROR` span rather than a successful-stage gap.

Continue to accept zero routing for early preparation failures, a successful
first model followed by credential/evidence failure, a failed first model, a
failed catalog, a failed second model, and failed selection/nested-model
prefixes. Reject only the impossible gaps after successful catalog and
successful second model, and prove writer rejection before database mutation.

## Accepted portions

The review accepted direct command/pipeline ancestry, bootstrap/prepare/
pipeline/render dependencies, embed-before-namespace and namespace-before-
rerank ordering, success/partial namespace summary reconciliation, terminal
error status behavior, early zero-routing automatic failures, evidence
`UNSET`/`OK`, initialized error summaries, prior privacy/failure-isolation
repairs, and the model-free test seam.

Parent validation at this failed candidate observed filtered full-suite results
of 1,073 passed tests plus 1,057 subtests on both Python 3.11 and 3.13, with only
57 pre-existing lxml warnings. Those passing tests do not override the three
adversarial findings.

## Verdict and next gate

FAIL. The implementation ticket remains blocked on the three bounded graph
repairs above. Exact wheel/sdist/archive/install reproduction was correctly
deferred because source is not final. After repair, rerun dual-runtime
validation, exact-package acceptance, and a fresh exact-commit review.

## Residual risk

This was source/static and adversarial decoder review, not a live provider or
catalog exercise. No provider, catalog, content, credential, model, collector,
real telemetry-home, installed-tool, remote, integration, release, or
publication operation occurred.
