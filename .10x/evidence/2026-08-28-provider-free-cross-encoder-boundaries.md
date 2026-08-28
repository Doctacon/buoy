Status: recorded
Created: 2026-08-28
Updated: 2026-08-28
Ticket: .10x/tickets/done/2026-08-28-measure-provider-free-cross-encoder-boundaries.md
Research: .10x/research/2026-08-28-provider-free-cross-encoder-boundaries-findings.md
Review: .10x/reviews/2026-08-28-provider-free-cross-encoder-boundaries-review.md
Prior-No-Result: .10x/evidence/2026-08-28-provider-free-cross-encoder-boundaries-no-result.md, .10x/evidence/2026-08-28-provider-free-cross-encoder-boundaries-continuation-no-result.md
Decision: .10x/decisions/provider-free-local-diagnostics-separate-debugging-from-measurement.md

# Provider-Free Cross-Encoder Boundary Measurement

## Disposition

The owner-ratified provider-free campaign completed its exact governed sequence after descendant executable/module/cardinality allowlisting was removed as an immaterial constraint. Runtime descendants were permitted only inside the monitored model-child process group, inherited the credential-free/offline/network-denied child environment, and left zero surviving lineage processes after every observation.

Exactly one discarded fresh-process warm-up and five retained fresh processes completed in fixed order with no governed retry, replacement, or reordering. Each retained process reported five separate, ordered, non-overlapping intervals. No interval is summed into a command total.

The two prior no-result records remain truthful and unchanged: they stopped before measurement authority under earlier descendant policies. The sequence recorded here was still entirely unconsumed when this successful campaign began.

## Bound identity

The external preflight bound:

- source manifest SHA-256 `5d002ab46aa180c38473f72c8b3e135c8faeb5f2cc5ea21a080546f4b17624e5`, 1,270 tracked/untracked non-ignored entries;
- changed-path manifest SHA-256 `ad787e552084d4af1bf428269287f422a340311b9ad24a1deec0345536719f7b`, six entries;
- `src/buoy_search/retrieval/cross_encoder.py` SHA-256 `ed963371948f9c51fdbc7d25df4193613e7b2616f34ba18e7b7b2e01d2ba1674`;
- `pyproject.toml` SHA-256 `29c69a012a4374b4a4f81328382fd42bb5662e5d14d378b74c7463dd7a5b500b`;
- `uv.lock` SHA-256 `ad7508159bc00271b21fc598bad07b56045329c938ed4fbd37a5a18d71c4c254`;
- exact reranker-cache regular-file/symlink manifest SHA-256 `602a7517c04e0aa924c595b13cd674591bf3f12e91f6447d5c11e81c33f68a65`, 20 entries, including six complete/readable exact-revision snapshot entries; and
- CPython 3.13.0, Darwin arm64, sentence-transformers 5.6.0, torch 2.12.1, transformers 5.12.1, and NumPy 2.4.6.

The unchanged production model identity was:

- `cross-encoder/ms-marco-MiniLM-L-6-v2`;
- revision `c5ee24cb16019beea0893ab7796b1df96625c6b8`;
- CPU, float32 production behavior, max length 512, batch size 8, local-only safetensors, and remote code disabled.

The deterministic content-free fixture identity was SHA-256 `8ee2638f79dd81a3bd9b0541f5af15378512adfc9e07f36f168bb0841314b86b`, 18,145 canonical UTF-8 bytes, one nine-word query, and 74 thirty-word passages. The pinned tokenizer produced paired lengths 48–49 and token-shape SHA-256 `8262cf88e43eb3e821665283b3b4ab206c20a9060330ac2aaee86a50343ab665`. No token ID or model score was retained.

## Preflight, debugging, and self-test

The campaign used a mode-0700 temporary directory outside the repository and mode-0600 runtime files. Child environments removed an exact 12-key provider credential denylist, removed Buoy/OpenTelemetry export activation, disabled telemetry and bytecode writes, and enabled Hugging Face, Transformers, and datasets offline controls. A private inherited `sitecustomize` guard denied socket connect, connect-ex, sendto, and create-connection operations and wrote only a temporary attempt marker.

Before measurement authority:

1. exact model cache completeness/readability and source/cache identities passed;
2. no staged files existed;
3. the non-model protocol self-test passed valid parsing, malformed rejection, watchdog whole-group termination, runtime-descendant containment, RSS limit enforcement, denied synthetic loopback, and terminal process-group cleanup;
4. an initial debug-only harness run exposed a cleanup-probe `PermissionError`, was corrected under debugging authority, and retained no model timing;
5. the corrected complete preflight/self-test/exact-target debug command passed once and was discarded; and
6. the production exact-target debug observation embedded in the final harness also passed and was discarded before measurement authority.

The harness monitored only temporary PID/PPID/process-group/RSS state needed for containment and limits. It did not inspect or retain descendant executable/module identity or cardinality. Every complete model-child lineage remained in its process group. Timeout and limit self-tests terminated the whole group; every debug, self-test, warm-up, and retained process left zero surviving lineage processes.

## Governed sequence ledger

| Governed order | Role | Status | Maximum group RSS bytes | Elapsed < 120 s | RSS < 4 GiB | Group cleanup |
| ---: | --- | --- | ---: | --- | --- | --- |
| 1 | discarded warm-up | completed | 520,290,304 | yes | yes | complete |
| 2 | retained 1 | completed | 525,385,728 | yes | yes | complete |
| 3 | retained 2 | completed | 531,300,352 | yes | yes | complete |
| 4 | retained 3 | completed | 533,463,040 | yes | yes | complete |
| 5 | retained 4 | completed | 558,891,008 | yes | yes | complete |
| 6 | retained 5 | completed | 557,727,744 | yes | yes | complete |

Warm-up timing was discarded. There was no governed retry, replacement, reordering, timeout, RSS failure, malformed result, score failure, identity drift, or cleanup failure.

## Retained observations

All values are milliseconds. The intervals are independent and are not added.

| Order | CrossEncoder import/runtime | Production reranker construction | First 1-pair score | Warm 24-pair score | Warm 49-pair score |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 7,612.028209 | 74.445500 | 25.756541 | 45.996500 | 90.814500 |
| 2 | 7,764.103083 | 88.451625 | 30.563000 | 53.246459 | 103.686750 |
| 3 | 7,928.117125 | 75.736375 | 25.909375 | 46.074125 | 102.357334 |
| 4 | 7,768.446375 | 79.791041 | 25.404792 | 48.574208 | 92.560417 |
| 5 | 7,460.980291 | 72.913000 | 24.548709 | 46.372333 | 88.842917 |

Every score call returned exactly 1, 24, and 49 finite numeric values respectively. Score values were validated in the child and not retained.

## Identity, effects, and cleanup

Exact source, changed-path, source-file, lock, cache, runtime, model, and fixture identities were checked before, between, and after observations and remained equal throughout the campaign. Record-writing occurred only after terminal equality. No staged file existed before, during, or after execution.

Observed prohibited-effect counts were zero for provider, catalog, namespace, content retrieval, embedding worker, telemetry, allowed network, model download, cache mutation, source mutation, install, live command, release, and deployment operations. Credential keys were absent from model-child environments. The production child loaded no provider, catalog, embedding-worker, or Buoy telemetry module.

After sanitized results were transferred into this record, the external harness script, sanitized result file, raw stdout/stderr, network markers, runtime helpers, and all temporary directories were deleted. Their absence and zero surviving model-child lineage were verified.

## Acceptance disposition

All eight ticket criteria passed independent review at `.10x/reviews/2026-08-28-provider-free-cross-encoder-boundaries-review.md`. This evidence identifies the dominant bounded interval but does not authorize a production optimization, worker extension, live campaign, percentile, SLA, or release target.
