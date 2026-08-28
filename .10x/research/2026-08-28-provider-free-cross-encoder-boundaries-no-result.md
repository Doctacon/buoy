Status: blocked-no-result
Created: 2026-08-28
Updated: 2026-08-28
Ticket: .10x/tickets/done/2026-08-28-measure-provider-free-cross-encoder-boundaries.md
Evidence: .10x/evidence/2026-08-28-provider-free-cross-encoder-boundaries-no-result.md
Prior-Research: .10x/research/2026-08-28-post-worker-retrieval-latency-residuals.md

# Provider-Free Cross-Encoder Boundaries: No Result

## Question

After query embeddings moved to the persistent worker, which process-cold cross-encoder boundary—import/runtime initialization, pinned model construction, first inference, or warmed bounded scoring—is the strongest residency candidate?

## Result

No governed timing result exists. The campaign stopped during debug/preflight separation before its discarded warm-up because the exact production score path inherently launches a standard-library `multiprocessing.resource_tracker` helper, while the ratified measurement contract prohibits every descendant process.

No debug timing or score was retained. The strongest latency boundary therefore remains unknown, and this record does not support cross-encoder worker expansion or any production optimization.

## Bounded operational finding

The descendant is attributable to presentation-lock setup rather than explicit parallel scoring:

- production passes `show_progress_bar=False` to Sentence Transformers;
- Sentence Transformers still constructs a disabled tqdm range;
- tqdm creates a multiprocessing write lock;
- Python starts `multiprocessing.resource_tracker` to track the semaphore.

The helper was observed as the only child and exited with its model process. That does not make it compliant with the current unqualified no-descendant rule.

This finding is version-bound to CPython 3.13.0, sentence-transformers 5.6.0, torch 2.12.1, transformers 5.12.1, NumPy 2.4.6, Darwin arm64, and the exact pinned MiniLM revision. It is not a latency benchmark, production-content observation, resource target, or general claim about other runtimes.

## Required decision before measurement

A successor or explicit ticket amendment must choose one policy before a governed sequence can run:

1. preserve the strict no-descendant rule, in which case this exact production path is currently ineligible for the campaign; or
2. permit exactly the standard-library resource-tracker companion created by the unchanged production tqdm lock, while still rejecting any other child, any extra child, abnormal helper termination, or any descendant surviving its model process.

Changing production tqdm locking merely to satisfy the harness would be a production behavior change and was outside this ticket. This research does not choose between those policies.

## Preserved direction

The prior investigation order remains valid but blocked at step one. Cross-encoder startup still warrants measurement before worker extension; the current evidence simply cannot rank its sub-boundaries under the existing campaign contract.
