Status: done
Created: 2026-08-27
Updated: 2026-08-27
Parent: None
Depends-On: .10x/tickets/done/2026-08-27-build-dormant-local-embedding-worker-prototype.md
Decision: .10x/decisions/superseded/buoy-connects-the-embedding-worker-behind-an-experimental-retrieve-flag.md
Specification: .10x/specs/superseded/experimental-retrieve-embedding-worker.md
Evidence: .10x/evidence/2026-08-27-experimental-retrieve-embedding-worker-ab.md

# Connect the Embedding Worker to Retrieve and Run a Live A/B

## Cold-start context

The dormant prototype proved exact embeddings and cross-process reuse but is not connected to retrieval. The owner authorized an explicit `buoy retrieve --experimental-embedding-worker` path, selected worker-backed automatic-routing plus retrieval-query embeddings, authorized exactly three live automatic read-only retrievals, selected the documented query `How is approximate vector recall evaluated?`, and wants a later default-on decision only if evidence is favorable.

The prerequisite worker independently rereviewed pass and closed before product connection executed. This ticket's implementation and bounded live evidence remain subject to independent post-change review.

## Scope

- Obtain and durably record an independent post-correction pass review of the dormant worker prerequisite; repair within its existing ticket only if findings require it.
- Add the retrieve-only experimental flag and worker-backed embedder adapter.
- Inject that embedder into automatic semantic routing and live retrieval while retaining all established non-embedding behavior.
- Preserve exact no-flag behavior and explicit-dry-run no-worker behavior.
- Add focused parser/CLI/retriever/integration tests and required documentation.
- Run provider-free parity/dormancy checks first.
- Run the exact three-command live A/B only after local validation and review pass.
- Record redacted evidence and review; reconcile both tickets without making the worker default.

## Explicit exclusions

Default-on behavior; environment activation; silent fallback; custom worker model/precision; provider credentials/clients in worker; reranker residency; pools/batching; apply/index/evals integration; Windows; global tool installation; release/deploy/publication; more than three live retrieval commands; output/content retention.

## Acceptance criteria

1. The prerequisite dormant-worker ticket has a genuinely independent post-correction pass review with no unresolved significant findings.
2. `--experimental-embedding-worker` exists only on `retrieve`; help and docs accurately describe the experiment.
3. Without the flag, established imports, construction, files/processes, provider calls, errors, telemetry, and output remain unchanged.
4. With the flag, compatible automatic retrieval uses the same resident exact worker for semantic routing and final retrieval embedding; the CLI process does not construct Sentence Transformers.
5. Explicit live namespace retrieval embeds exactly once through the worker; explicit dry-run starts no worker; automatic dry-run may route through it but performs no content retrieval.
6. Incompatible configuration/capability and every worker failure are bounded, phase-correct, credential-safe, no-fallback, and no-replay.
7. Full focused, dual-runtime, validator, package, isolated-install, CLI/help, dormancy, diff, and no-staged-files checks pass.
8. Exactly three owner-authorized live automatic retrieval commands run in baseline/cold-worker/warm-worker order with telemetry disabled and restrictive temporary output.
9. Live evidence reports redacted route/result parity, exit/count/hash comparisons, baseline/cold/warm wall and available local timings, worker reuse/RSS/cleanup, source/cache equality, provider/network confounding, and all mismatches without retaining result content or credentials.
10. Independent post-change review passes with no unresolved significant findings.
11. No default-on recommendation is activated automatically; evidence supports a separate owner decision.

## Evidence expectations

- Prerequisite independent review and any repair evidence.
- Exact changed paths and injection map.
- Tests mapped to every acceptance scenario.
- Dual-runtime/full packaging outputs and test counts.
- Redacted three-run A/B procedure, timings, parity hashes/counts, process/RSS/cleanup, source/cache manifests, operation count, and limits.
- Independent post-change review, residual risk, no staged files, and retrospective.

## Blockers

None. Independent post-change review passed at `.10x/reviews/2026-08-27-experimental-retrieve-embedding-worker-review.md`. Executed-campaign source equality remains explicitly inconclusive and does not invalidate the bounded parity/latency observations.

## Progress and notes

- 2026-08-27: Owner authorized connection behind a retrieve flag, selected routing plus retrieval embedding reuse, authorized a live A/B, and selected the documented query. Activated the focused decision/spec and opened this ticket blocked only on prerequisite independent review. No implementation or live provider operation occurred in this specification/ticket-authoring turn.
- 2026-08-27: Independent prerequisite review found three significant worker lifecycle/security gaps. The prerequisite writer repaired all three; independent rereview passed with no unresolved significant finding. The prerequisite closed, this ticket moved to active, and implementation/live A/B execution remained explicitly authorized.
- 2026-08-27: Implemented the retrieve-only flag, lazy exact-config/POSIX worker adapter, automatic routing plus retrieval injection, explicit retrieval injection, optional retriever factory seams, bounded phase-correct errors, docs, and focused tests. No-flag calls remain unchanged; explicit dry-run validates without worker state; no default/env/fallback/custom-worker/provider-in-worker behavior was added. Focused Python 3.11/3.13 suites each passed 220 tests; full suites each passed 1,236 tests. Provider-free exact-model parity, validators, compile, wheel/sdist, isolated install/help/flag/dormancy/factory checks, diff hygiene, and no-staged-files checks all passed before live execution.
- 2026-08-27: Ran exactly three owner-authorized automatic live retrieval commands—baseline, cold worker, warm worker—in required order and no fourth command. All exited zero with byte-identical redacted payload/route/shape hashes, five hits, three selected namespaces, and empty stderr. Wall times were 10,522.682 ms, 8,789.305 ms, and 5,880.203 ms. Cold/warm reused one worker; observed RSS was 185,499,648 bytes; model cache remained equal; validated idle cleanup completed after 299,012.238 ms without signaling. Raw output files were mode 0600 outside the repository and deleted; no result content, URL, namespace value, credential, PID, or raw response was retained.
- 2026-08-27: The live harness's broad source manifest reported unequal because it included ignored `__pycache__`/`.pyc` runtime artifacts. Constituent before/after entries were not retained, so exact source equality is honestly inconclusive; no fourth command was run. The harness now excludes bytecode for future source manifests. Complete bounded evidence and this mismatch are recorded at `.10x/evidence/2026-08-27-experimental-retrieve-embedding-worker-ab.md`.
- 2026-08-27: Independent post-change review passed with no significant finding. Its one minor finding showed the post-campaign harness retained decoded objects in memory during idle waiting; future harness behavior was corrected to return only redacted values and delete raw files before waiting. Parent observed 32 focused tests, py_compile, diff hygiene, and no staged files; targeted independent rereview passed. No fourth live command ran. Review: `.10x/reviews/2026-08-27-experimental-retrieve-embedding-worker-review.md`.
- 2026-08-27: Retrospective: end-to-end evidence confirms the worker is useful for repeated commands but not sufficient alone for default-on policy. A/B harnesses should reduce live outputs to redacted values at each command boundary, exclude runtime bytecode from source manifests before measurement, and separate local reuse observations from provider/network causality. These procedures are preserved in the focused harness, evidence, and governing specification. Default activation remains a separate owner decision.
