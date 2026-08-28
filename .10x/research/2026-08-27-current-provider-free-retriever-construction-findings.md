Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Ticket: .10x/tickets/done/2026-08-27-measure-current-provider-free-retriever-construction.md
Evidence: .10x/evidence/2026-08-27-current-provider-free-retriever-construction.md
Prior-No-Result: .10x/research/2026-08-27-current-provider-free-retriever-construction-no-result.md

# Current Provider-Free Retriever Construction Findings

## Question

Within current explicit retrieval preparation, what are the independently measured intervals for sentence-transformers import, local production model construction after import, and fake-provider retriever/configuration construction?

## Method

After an explicitly authorized narrow preflight correction, an external provider-free harness passed exact source/model/cache/runtime identity, credential-name, offline/network-denial, protocol, watchdog, descendant, automatic-device, privacy, and cleanup controls.

One fresh-process model warm-up was discarded. Five retained fresh processes then ran in fixed order on automatic `mps`, exact local `BAAI/bge-small-en-v1.5` revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, float32. Each measured three non-overlapping intervals in source order. No query, embedding encode, retrieval, provider SDK/client, network, telemetry, model download, or cache mutation occurred.

## Observations

The three intervals are not summed.

| Order | sentence-transformers import ms | production model construction ms | fake-provider retriever/config construction ms |
| ---: | ---: | ---: | ---: |
| 1 | 7,840.622667 | 329.810083 | 0.029625 |
| 2 | 7,782.102417 | 336.065833 | 0.015542 |
| 3 | 7,797.322083 | 336.444459 | 0.083333 |
| 4 | 7,759.534833 | 314.368125 | 0.053208 |
| 5 | 7,633.771292 | 436.569583 | 0.230917 |

All six model processes, including the discarded warm-up, stayed below 120 seconds and 4 GiB RSS. The maximum observed RSS among them was 498,253,824 bytes. There were no retries, descendants, provider operations, queries, encodes, retrievals, telemetry operations, or allowed network attempts. Source and cache identities remained exact.

## Bounded interpretation

In every retained process, the measured sentence-transformers import interval was numerically much larger than the separately measured post-import production model-construction interval. Direct fake-provider configuration and wrapper construction was below one millisecond in every observation.

The import boundary includes transitive Python imports and dynamic-library/runtime initialization reached by importing sentence-transformers. It does not isolate individual dependencies, device runtime setup, filesystem reads, or resource utilization. The result therefore identifies the next attribution boundary—import/runtime initialization—without proving which transitive component causes its duration.

The post-import constructor interval measures `SentenceTransformerEmbedder` after sentence-transformers is already imported and after one discarded host warm-up. It is not comparable to a cold process's unsplit constructor call, and it does not establish a cold-host model-load duration.

The fake-provider interval proves only that current local `RuntimeConfig`, fake namespace, and direct `HybridRetriever` wrapper construction are negligible in this controlled seam. It intentionally says nothing about real provider SDK/client construction.

## Conclusion

The current provider-free evidence narrows explicit host-warm/process-cold preparation from a coarse retriever-construction span to the sentence-transformers import/runtime-initialization boundary. It does not support optimizing the local wrapper constructor first and does not yet distinguish sentence-transformers package import from its transitive torch, transformers, numerical-library, or device-runtime work.

No production optimization is authorized by this research. The brittle one-shot import campaign was cancelled after its harness failed while the exact ordinary production import succeeded. Current bounded import attribution is `.10x/research/2026-08-27-ordinary-sentence-transformers-import-diagnostic.md`, governed by `.10x/decisions/provider-free-local-diagnostics-separate-debugging-from-measurement.md`. Persistent-worker implementation remains excluded.

## Limits

- One Darwin arm64 host, one automatic `mps` device class, one exact cached model revision, and five ordered retained observations.
- One discarded warm-up means the retained condition is process-cold but host-warm; no cold-host claim is made.
- No percentile, distribution, end-to-end total, latency target, causal utilization profile, or mode comparison is claimed.
- No real provider/client/network construction or live retrieval was measured.
- Exact current worktree bytes were bound, but this was not an installed-release comparison.
- Independent acceptance review passed with no findings; privacy-required harness deletion leaves method/state claims bounded by retained content-addressed attestations.
