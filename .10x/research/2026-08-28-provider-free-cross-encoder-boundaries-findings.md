Status: recorded
Created: 2026-08-28
Updated: 2026-08-28
Ticket: .10x/tickets/done/2026-08-28-measure-provider-free-cross-encoder-boundaries.md
Evidence: .10x/evidence/2026-08-28-provider-free-cross-encoder-boundaries.md
Review: .10x/reviews/2026-08-28-provider-free-cross-encoder-boundaries-review.md
Prior-No-Result: .10x/research/2026-08-28-provider-free-cross-encoder-boundaries-no-result.md, .10x/research/2026-08-28-provider-free-cross-encoder-boundaries-continuation-no-result.md

# Provider-Free Cross-Encoder Boundary Findings

## Question

After compatible query embeddings moved to the persistent worker, which process-cold cross-encoder boundary—import/runtime initialization, pinned model construction, first inference, or warmed bounded scoring—is the strongest residency candidate?

## Method

A provider-free external harness measured the exact production `cross-encoder/ms-marco-MiniLM-L-6-v2` revision `c5ee24cb16019beea0893ab7796b1df96625c6b8` on production CPU settings with local-only cached safetensors. One fresh-process warm-up was discarded, followed by five retained fresh processes without retry, replacement, or reordering.

Each retained process separately timed:

1. `sentence_transformers.CrossEncoder` import/runtime initialization;
2. unchanged production `_PinnedMiniLMReranker` construction after import;
3. first production one-pair score;
4. warmed production 24-pair score; and
5. warmed production 49-pair score.

The fixed synthetic passages were 48–49 paired tokens under the pinned tokenizer. The 24- and 49-pair cases represent current bounded retrieval and routing cardinalities, not production-content latency. Credentials were removed, network operations denied, telemetry/offline controls applied, source and cache identities checked between observations, runtime-created descendants process-group-contained, and external artifacts deleted.

## Observations

The intervals are not summed.

| Order | Import/runtime ms | Construction ms | First 1-pair ms | Warm 24-pair ms | Warm 49-pair ms |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 7,612.028209 | 74.445500 | 25.756541 | 45.996500 | 90.814500 |
| 2 | 7,764.103083 | 88.451625 | 30.563000 | 53.246459 | 103.686750 |
| 3 | 7,928.117125 | 75.736375 | 25.909375 | 46.074125 | 102.357334 |
| 4 | 7,768.446375 | 79.791041 | 25.404792 | 48.574208 | 92.560417 |
| 5 | 7,460.980291 | 72.913000 | 24.548709 | 46.372333 | 88.842917 |

Observed process-group RSS remained below 4 GiB; the maximum among the warm-up and five retained children was 558,891,008 bytes. All score counts and finiteness checks passed. Source/cache identity and cleanup checks remained exact.

## Bounded interpretation

The process-cold `CrossEncoder` import/runtime boundary was numerically dominant in every retained observation: 7,460.980291–7,928.117125 ms. Post-import model construction was 72.913000–88.451625 ms. First one-pair inference was 24.548709–30.563000 ms. Warm bounded scoring was 45.996500–53.246459 ms for 24 pairs and 88.842917–103.686750 ms for 49 pairs.

Within this host-warm/process-cold condition, residency that avoids repeating the import/runtime boundary is therefore the strongest local cross-encoder optimization candidate. Keeping only model construction or warmed scoring logic resident while still repeating Sentence Transformers/Torch runtime import would not address the dominant measured interval.

This finding explains why old 295–397 ms rerank spans could not predict post-embedding-worker startup: those older processes had already paid Sentence Transformers/Torch initialization while constructing the in-process query embedder. The new evidence isolates a roughly 7.5–7.9 second process-cold import/runtime boundary when the client no longer imports that stack for embedding.

The finding supports investigating cross-encoder residency. It does not itself authorize extending the worker, selecting an IPC protocol, changing fallback behavior, moving routing/retrieval data across a process boundary, or changing model/ranking semantics.

## Limits

- One Darwin arm64 host, CPython 3.13.0, sentence-transformers 5.6.0, torch 2.12.1, transformers 5.12.1, NumPy 2.4.6, exact cached MiniLM revision, and CPU only.
- One discarded host warm-up and five ordered retained process-cold observations; no cold-host, percentile, distribution, SLA, or target claim.
- Synthetic 48–49-token pairs; production passage lengths and mixed routing/retrieval sequences may differ.
- Import includes transitive Torch, Transformers, native-library, and runtime initialization. It does not attribute those subcomponents or prove CPU utilization causality.
- Intervals are separate and must not be summed into an end-to-end command total.
- No provider, live retrieval, production content, telemetry trace, or worker comparison ran.
- Independent acceptance review passed all eight ticket criteria; review reproducibility partly depends on the retained executor transcript because raw external runtime artifacts were deleted as required.

## Conclusion

The strongest measured cross-encoder residency candidate is unambiguously process-cold Sentence Transformers/CrossEncoder import and transitive runtime initialization, not model construction or bounded scoring. A separately specified worker-residency design can now be evaluated against this evidence while preserving model, score, routing, ranking, credential, privacy, and fallback parity.
