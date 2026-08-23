Status: recorded
Created: 2026-08-22
Updated: 2026-08-22
Target: 5945b047d525658d0db55dd74cee8010cf5b27b3
Verdict: fail
Ticket: .10x/tickets/done/2026-08-20-instrument-retrieve-command-pipeline-latency.md
Prior-Review: .10x/reviews/2026-08-22-retrieve-command-pipeline-telemetry-rereview.md
Evidence-Commit: 7b190ebaeb337ad4478324f39e568d4aa4ed7bef

# Retrieve Command and Pipeline Telemetry Final Review

## Review performed

Two fresh reviewers inspected immutable implementation commit `5945b047`, tree
`c38e5cd25da9104ce2545c6fd38835357a69d18b`, cumulatively against both prior
failed reviews, active specifications, source behavior, tests, and records-only
evidence commit `7b190eb`. Parent inspection proved `7b190eb` changes only the
telemetry evidence and instrumentation ticket; parent also reran the four second-
repair tests, which passed in 52.28 seconds.

The reviewers accepted command-success/error-pipeline rejection, controlled
automatic routing delay presence and stage ordering, persisted filename/path-
component privacy scans, error-plus-zero rejection, broken-stderr preservation,
private exporter isolation, one-field routing receipt equality, and the
records-only distribution exclusion.

## Findings

### High — truthful weak-evidence widening traces are rejected

Automatic live retrieval may run `buoy.evidence.assess` twice: once on the
initial top-one result, then again after `weak_top1` widening. The independent
v2 validator rejects more than one evidence span. A valid command trace is
therefore silently dropped precisely for the governed weak-evidence widening
path.

Allow the exact source-backed cardinality: at most two evidence spans for an
automatic pipeline, with two permitted only when widening is true and fallback
reason is `weak_top1`. Preserve zero/one cases and reject evidence spans in
explicit modes. Add a real command-trace regression for initial weak evidence,
second assessment, widened event, namespace fanout, and successful publication,
plus independent encoder/decoder/writer adversarial controls.

### High — namespace-stage cardinality is not reconciled with final fanout

The decoder requires at least one namespace stage for success but accepts any
count and duplicate route ranks. Duplicating the canonical explicit-single
namespace span with a unique span ID while retaining route rank 1 and summary
`final_fanout=1` passes. This violates the independently enforced exact graph.

For every present pipeline, require namespace-stage count exactly equal to
operation `final_fanout`; route ranks MUST be unique and exactly `1..final_fanout`.
This naturally allows zero namespaces when embedding fails before fanout and
requires every attempted target, including failures, when fanout begins. Add
positive explicit single/multi/automatic widening and failure graphs plus
adversarial missing/extra/duplicate/gapped rank cases before writer mutation.

While repairing source-backed stage cardinality, verify adjacent truthful
cardinalities rather than retaining another known hole: a successful/partial
multi or automatic pipeline has exactly one rerank span; explicit-single has no
rerank or evidence spans; explicit-multi has no evidence spans; pipeline error
may have only stages actually reached. Do not infer requirements beyond current
retriever/CLI source and active specs.

### Significant — delayed subprocesses do not prove an increase

The subprocess test runs only delayed commands and compares duration to a fixed
30 ms floor. Because timing starts before CLI imports, normal startup overhead
can exceed that floor even if the sleeps are removed. For each initialization,
routing, and rendering case, run a zero-delay baseline and a meaningfully delayed
subprocess under the same fake behavior. Assert command-duration delta tracks
the injected delay within a non-flaky tolerance while pipeline duration remains
stable. Keep the dependent five-run reference-host gate separate.

### Acceptance evidence — parent has not reproduced package claims

The records-only evidence now durably reports clean exact-commit wheel/sdist/
install results, but those commands were executed by the worker. Parent has
observed only Git/hash checks and the four repaired tests. After the final source
repair, the parent must independently reproduce from a clean detached exact
implementation commit: offline wheel and sdist; archive hashes; source/archive/
isolated-install CLI, envelope, and artifact byte equality; old-receipt rejection
and new acceptance; runtime/build/DuckDB versions; disabled installed preview;
and post-run cleanliness. This is an evidence gate, not a demonstrated source
defect.

## Verdict

FAIL. The second repair closes its named findings but over-restricts a valid
widening trace, under-restricts namespace cardinality, and does not yet prove
subprocess delay increase. Exact package acceptance remains parent-unverified.

## Limits

Reviewers had static/read-only inspection without shell execution. Parent's four
targeted tests support only those cases. No live provider, catalog, content,
credential, model, collector, or external-state operation is authorized.
