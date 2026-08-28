Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Relates-To: .10x/tickets/done/2026-08-27-measure-current-provider-free-retriever-construction.md
Preflight-Failure: .10x/evidence/2026-08-27-current-provider-free-retriever-construction-preflight-failure.md

# Current Provider-Free Retriever Construction

## Execution authority and boundary

After the first preflight stopped before any child, the owner explicitly authorized continuation of the still-unconsumed campaign with one narrow harness correction: child-environment validation compared the exact approved key set and exact known credential-key denylist intersection, inspecting names only. Every other preflight, self-test, network denial, source/cache identity, automatic-device, watchdog, descendant, privacy, cleanup, and no-retry control remained unchanged.

The continuation used current reorganized source, not installed v0.6.3. It performed no production edit or instrumentation. All harness/runtime material existed only in an owner-private temporary directory outside the repository.

## Bound identities

The complete current worktree manifest before model execution contained 1,233 entries and 17,591,423 content bytes:

- worktree manifest SHA-256: `399a605d8736a73b410d8b2a5c7c27dd0fba2ecff4f9abf5a2fba53eacf58122`;
- Git status manifest SHA-256: `d1f5585a7f753527e98572a5ba38e5ce39187d7f44f311c4cc7c7b90d6ca0cc2`; and
- five preexisting records-only status entries.

Relevant exact identities remained:

- `pyproject.toml`: `29c69a012a4374b4a4f81328382fd42bb5662e5d14d378b74c7463dd7a5b500b`;
- `uv.lock`: `ad7508159bc00271b21fc598bad07b56045329c938ed4fbd37a5a18d71c4c254`;
- `src/buoy_search/config.py`: `b33407002f60c6ca3429e05043f2c1451902112bf793ce2ae2ed0ae9e4da5620`;
- `src/buoy_search/indexing/chunker.py`: `98a036fa829cbec675b5fd04cc1dd717a0ccc04c417a25ea33433827cec908d8`;
- `src/buoy_search/retrieval/retriever.py`: `e087019eb373d433eaedd3a6ab26db297be740e7992ab53159251e9c5031b2b0`; and
- Python executable: `2bfbeb6d935f72272e37921df5f0588be257b95ac67187691461af74308169f1`.

Runtime was CPython 3.13.0 on Darwin 25.5.0 arm64 with sentence-transformers 5.6.0, transformers 5.12.1, torch 2.12.1, and turbopuffer 2.4.0.

The exact local model was `BAAI/bge-small-en-v1.5` revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, float32. Its exact ref and 12 snapshot assets were present under offline/local-only controls. The complete relevant cache manifest contained 44 entries and 267,600,148 content bytes at SHA-256 `ba04c92fd9f4705fc3c9da63cd4c07da4c6d9d86c055e861d071d53528a205ae`. Production automatic device selection resolved to `mps`; no device was forced and no precision conversion occurred.

## Preflight and non-model self-test

Before model authority was consumed, the corrected exact-name credential validation passed. The child environment exactly equaled its approved key set and had an empty intersection with the exact known credential-key denylist; no value was inspected, printed, or retained.

The non-model self-test then passed all governed controls:

- successful sanitized child launch and interval parsing;
- rejection of malformed protocol and invalid/non-monotonic interval data;
- watchdog timeout and terminal cleanup;
- unexpected descendant detection and process-group termination;
- process-level network denial;
- generic failure-category handling; and
- unchanged worktree, model-cache, and telemetry filesystem state.

A separate provider-free device probe selected `mps` and left the model cache unchanged. It did not construct a model or consume warm-up/sample authority.

## Six-process ledger

Exactly one discarded warm-up followed by exactly five retained fresh processes completed in order. There were no retries, replacements, reordering, timeouts, limit hits, or descendants.

| Sequence | Role | Outcome | Elapsed <120s | RSS <4GiB | Maximum observed RSS bytes |
| ---: | --- | --- | --- | --- | ---: |
| 1 | discarded warm-up | completed | passed | passed | 468,418,560 |
| 2 | retained 1 | completed | passed | passed | 495,648,768 |
| 3 | retained 2 | completed | passed | passed | 498,253,824 |
| 4 | retained 3 | completed | passed | passed | 484,753,408 |
| 5 | retained 4 | completed | passed | passed | 495,452,160 |
| 6 | retained 5 | completed | passed | passed | 488,095,744 |

Each process imported the current production classes before measurement, then measured three non-overlapping source-ordered boundaries: sentence-transformers import evaluation, unchanged production `SentenceTransformerEmbedder` construction, and `RuntimeConfig` plus fake namespace plus directly injected `HybridRetriever` construction. The last boundary did not call `HybridRetriever.from_config`, `build_namespace`, a provider SDK/client factory, or any provider resource.

## Retained component intervals

These intervals are independent and are deliberately not summed.

| Retained order | sentence-transformers import ms | production model construction ms | fake-provider retriever/config construction ms |
| ---: | ---: | ---: | ---: |
| 1 | 7,840.622667 | 329.810083 | 0.029625 |
| 2 | 7,782.102417 | 336.065833 | 0.015542 |
| 3 | 7,797.322083 | 336.444459 | 0.083333 |
| 4 | 7,759.534833 | 314.368125 | 0.053208 |
| 5 | 7,633.771292 | 436.569583 | 0.230917 |

No end-to-end total, nested-span sum, percentile, mode comparison, cold-host claim, performance target, or causal resource-utilization claim is derived from these values.

## State equality and prohibited effects

After every model child and at terminal state, the complete worktree and relevant model-cache manifests exactly equaled their preflight identities. Telemetry filesystem metadata state also remained equal. The sandbox denied writes to the repository, model cache, and telemetry root and denied network operations.

Observed operation counts were zero for provider operations, queries, embedding encodes, retrievals, telemetry/store operations, and allowed network attempts. Real credentials were absent from child environments. The harness did not call catalog, namespace, content, reranking, evidence, model-download, cache-repair, build/install, global-tool, Git-ref, release, or deployment paths.

Raw stdout/stderr and interval-boundary timestamps were not retained. The complete external harness/runtime root was deleted after sanitized result extraction, and terminal filesystem inspection verified it absent. `git diff --check` passed and no files were staged after durable records were written.

## What this supports

This supports completion of the bounded provider-free measurement sequence and independent review of its method and no-effect claims. The research interpretation is `.10x/research/2026-08-27-current-provider-free-retriever-construction-findings.md`.

It does not itself authorize an optimization, production lifecycle change, provider campaign, release, or deployment. Independent acceptance review passed with no findings at `.10x/reviews/2026-08-27-current-provider-free-retriever-construction-review.md`.
