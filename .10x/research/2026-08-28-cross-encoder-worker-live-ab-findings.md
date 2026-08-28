Status: recorded
Created: 2026-08-28
Updated: 2026-08-28
Ticket: .10x/tickets/done/2026-08-28-run-cross-encoder-worker-three-command-live-ab.md
Evidence: .10x/evidence/2026-08-28-cross-encoder-worker-three-command-live-ab.md
Prior-Research: .10x/research/2026-08-28-provider-free-cross-encoder-boundaries-findings.md
Review: .10x/reviews/2026-08-28-cross-encoder-worker-three-command-live-ab-review.md

# Cross-Encoder Worker Live A/B Findings

## Question

In one current automatic read-only retrieval sequence, what end-to-end baseline/cold/warm behavior is observed after both the exact embedding model and pinned cross-encoder can remain in the default schema-v2 worker?

## Method

After provider-free harness/self-test, focused-suite, identity/cache, credential-name-only, telemetry/offline, worker-absence, diff, and staged-state gates passed, exactly three fresh CLI processes ran in fixed order with the governed query:

1. complete in-process `--no-embedding-worker` baseline;
2. default cold schema-v2 worker; and
3. identical default warm worker.

There was no retry, replacement, reorder, or fourth command. Each command's raw output/error was privately reduced to hashes/counts/timing and deleted immediately. The warm worker was then allowed to exit naturally after five minutes. Complete retained method/evidence is `.10x/evidence/2026-08-28-cross-encoder-worker-three-command-live-ab.md`.

## Observations

| Role | Wall ms | Exit | Hits | Namespaces | Logical catalog reads | Namespace results |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 16,101.925875 | 0 | 5 | 3 | 5 | 3 |
| cold worker | 6,752.035625 | 0 | 5 | 3 | 5 | 3 |
| warm worker | 2,853.658708 | 0 | 5 | 3 | 5 | 3 |

All complete stdout, canonical payload, ordered route, structural shape, stderr, hit-count, namespace-count, catalog-read-count, and namespace-result-count identities were equal. Every stderr was empty. The cold and warm commands reused one matching worker. One post-command worker RSS observation was 691,650,560 bytes. Natural idle cleanup completed in 300,607.889708 ms.

Source/lock/runtime/package, exact embedding cache, exact reranker cache, changed-path, and telemetry-store identities remained equal. No provider write, fallback warning, telemetry/store mutation, model download/cache repair, install, release, deployment, commit, or staging occurred.

The arithmetic within this ordered sequence is:

- cold worker 58.066907% below baseline;
- warm worker 82.277532% below baseline; and
- warm worker 57.736320% below cold worker.

## Bounded interpretation

This observation is consistent with the provider-free attribution: process-cold in-process retrieval pays repeated Sentence Transformers/Torch/CrossEncoder runtime initialization, while the cold default command starts one worker that can serve both model families and the warm command reuses them. The byte-identical outputs and equal route/result counts show no observed semantic change in this case.

The warm 2.854-second wall observation also makes the remaining remote catalog and namespace-query path comparatively more visible, consistent with prior residual-latency research. It does not isolate those stages because live telemetry was deliberately disabled.

The worker's 691.7 MB RSS observation shows the local latency benefit has a memory-residency cost after both models load. It is one post-command sample, not a peak, distribution, budget, or target.

## Historical context

The new output/payload/route/shape hashes equal the prior embedding-only campaign hashes for the same query. Prior wall observations were 10,522.682 ms baseline, 8,789.305 ms cold, and 5,880.203 ms warm. The new timings must not be treated as a direct causal improvement over those historical values: source, worker protocol/model placement, command order, host state, remote service, and network conditions may differ. Historical equality is useful parity context only.

## Limits

- Exactly three ordered observations on one Darwin arm64 host; no randomization, repetition, percentile, distribution, statistical test, or cold-host control.
- Provider/network latency and order/host warming are confounders.
- Telemetry was disabled, so there is no current per-stage timing or physical provider-attempt attribution.
- Logical catalog/namespace counts come from the established payload; they do not reveal hidden SDK retries or provider-internal work.
- RSS is one bounded post-command observation, not peak memory.
- The fixed query selected three namespaces and five hits; behavior for other routes/cardinalities is not measured live.
- Privacy controls intentionally retain no content or raw response for later qualitative inspection.

## Conclusion

In this one bounded live sequence, default schema-v2 embedding plus cross-encoder residency preserved byte-identical output and route/result structure while the warm command observed 2,853.658708 ms versus 16,101.925875 ms for complete in-process baseline. This supports the implemented residency direction as an observed repeated-command latency optimization, while establishing no SLA, release gate, provider-adjusted causal estimate, or authority for another campaign.
