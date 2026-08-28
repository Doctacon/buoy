Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Ticket: .10x/tickets/done/2026-08-27-connect-embedding-worker-to-retrieve-experiment.md
Decision: .10x/decisions/superseded/buoy-connects-the-embedding-worker-behind-an-experimental-retrieve-flag.md
Specification: .10x/specs/superseded/experimental-retrieve-embedding-worker.md
Prerequisite-Review: .10x/reviews/2026-08-27-dormant-local-embedding-worker-independent-review.md

# Experimental Retrieve Embedding Worker A/B

## Implemented boundary

The reviewed dormant worker is connected only through the explicit retrieve flag:

```text
buoy retrieve --experimental-embedding-worker
```

Changed production paths:

- `src/buoy_search/cli/main.py` adds the retrieve-only parser flag, lazy worker import, exact model/precision/POSIX validation before credential/provider work, value-redacted adapter, routing injection, retrieval injection, and phase-correct model-error handling.
- `src/buoy_search/retrieval/retriever.py` adds optional keyword-only embedder injection to `HybridRetriever.from_config` and `MultiNamespaceRetriever.from_configs`. Omitting it retains the existing `SentenceTransformerEmbedder` construction path and call spelling.
- `docs/retrieval.md` documents exact scope, dry-run boundaries, five-minute idle lifetime, approximate warm RSS, no fallback/environment activation/default, and custom-model rejection.

The CLI module does not import the worker backend unless the flag is selected. The adapter contains no provider client or credential. Automatic mode passes one adapter object to semantic routing and retrieval; explicit live mode passes it only to retrieval. Explicit dry-run validates compatibility/capability with `activate=False` and creates no worker path or process. No telemetry marker or result-payload field was added.

## Focused coverage

Updated focused tests cover:

- flag locality and help;
- no-flag lazy-import/dormancy and unchanged construction calls;
- exact model/precision and unsupported-capability failure before provider construction;
- explicit dry-run validation with no encode/spawn/retriever;
- explicit live injection and exactly one embedding;
- automatic dry-run routing-only embedding and no content retriever;
- automatic live use of the same adapter for route and retrieval embeddings;
- optional single/multi retriever factory injection without local model construction;
- bounded worker runtime failure rendered as `model_error`, not provider failure, with no raw detail or telemetry backend/query value; and
- unchanged result payloads without an experimental marker.

Focused Python 3.11 and 3.13 runs each passed 220 tests. Final full suites passed:

- Python 3.11: 1,236 tests in 108.308 seconds;
- Python 3.13: 1,236 tests in 100.598 seconds.

Only the established plan-cleanup warnings and upstream lxml deprecation warning appeared.

## Provider-free and package gates

All gates completed before any live command:

- dual-runtime compilation;
- explicit experimental namespace dry-run under an isolated home with no credential and no `~/.buoy` creation;
- exact-model provider-free worker validation: vector delta 0.0, equal ranking, same PID, no Sentence Transformers import in fresh clients, 440,074,240-byte RSS, startup 8,524.129 ms, first client 222.107 ms, second client 16.119 ms, unchanged source/cache, complete cleanup;
- ranking contract, ranking promotion, and C6 validators;
- wheel and sdist build;
- isolated Python 3.13 wheel install, root/retrieve help, flag inventory, no-flag lazy import, explicit experimental dry-run dormancy, and injected factory signature inventory;
- `git diff --check`; and
- no staged files.

Pre-live validation checked names/booleans only: the existing credential name was present, model/precision were compatible, removed environment aliases were absent, and compatible worker socket/state were absent.

## Live authority and privacy procedure

Exactly three owner-authorized automatic read-only retrieval commands ran, once each, in this order and with the fixed query governed by the specification:

1. baseline without flag;
2. cold worker with flag;
3. warm worker with flag.

The harness is `tests/fixtures/experimental_retrieve_worker_ab.py`. It used the same current Python/source/environment, set `BUOY_TELEMETRY=off`, disabled OpenTelemetry/model telemetry, and forced Hugging Face/Transformers offline behavior. Raw stdout/stderr existed only in mode-0600 files beneath a mode-0700 temporary directory outside the repository. Each was parsed and deleted immediately. The harness retained no hit content, URL, namespace value, route value, query output, credential, raw provider response, worker PID, or socket path. It emitted only counts, booleans, timings, RSS, and SHA-256 values. No fourth command, retry, provider write, index/apply/catalog mutation, release, install, or deployment ran.

The harness waited without signaling until the worker's fixed idle shutdown removed validated socket/state. Cleanup completed after 299,012.238 ms of post-command observation; the idle clock began at the warm command's accepted embedding request before the remainder of that command completed.

## Redacted live results

All three commands exited zero, wrote zero stderr bytes, returned five hits across three selected namespaces, and were byte-identical despite provider/network timing confounding.

| Run | Wall ms | Exit | Hits | Namespace count | Payload SHA-256 | Route SHA-256 | Shape SHA-256 |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| Baseline | 10,522.682 | 0 | 5 | 3 | `8b2c9649427313151f79e0be16dd836cefab1b5d9f23b8112624431570f20580` | `91ff1a2a6375d7201f4de839d2460ad5de36fbbd2dff4cf0a6ac8b1bbda57e32` | `0590147f28af1890f8275bb4191b3ceb27f475423b8276c9457b290f5e566a67` |
| Cold worker | 8,789.305 | 0 | 5 | 3 | `8b2c9649427313151f79e0be16dd836cefab1b5d9f23b8112624431570f20580` | `91ff1a2a6375d7201f4de839d2460ad5de36fbbd2dff4cf0a6ac8b1bbda57e32` | `0590147f28af1890f8275bb4191b3ceb27f475423b8276c9457b290f5e566a67` |
| Warm worker | 5,880.203 | 0 | 5 | 3 | `8b2c9649427313151f79e0be16dd836cefab1b5d9f23b8112624431570f20580` | `91ff1a2a6375d7201f4de839d2460ad5de36fbbd2dff4cf0a6ac8b1bbda57e32` | `0590147f28af1890f8275bb4191b3ceb27f475423b8276c9457b290f5e566a67` |

The complete stdout SHA-256 was `aa583f89a669f940faf5ad8767fa9c12f021b1c7f9ff6044d504474a81b54d36` for all runs; each stdout was 20,738 bytes. Empty stderr SHA-256 was `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

Parity booleans were all true: exit, hit count, namespace count, ordered route hash, payload hash, and structural shape. Cold and warm commands used one worker PID; the PID itself was not retained. Observed warm-worker RSS was 185,499,648 bytes. Exact model-cache manifest remained equal. Validated idle cleanup completed.

Numerically, cold-worker wall time was 16.47% below baseline, warm-worker was 44.12% below baseline, and warm-worker was 33.10% below cold-worker. Governed local span timings were unavailable because command telemetry was deliberately disabled; no substitute production instrumentation was added. These are three ordered observations, not a distribution, percentile, causal provider-adjusted estimate, SLA, release gate, or default-on authority. Provider and network work remained a confounder even though the complete outputs were identical.

## Source-manifest mismatch

The live harness reported `source_unchanged=false`. This mismatch is retained rather than overwritten or treated as a successful equality check.

The executed harness version hashed every file beneath `src/buoy_search`, including ignored `__pycache__`/`.pyc` runtime cache files. Post-campaign inspection found recently touched Python bytecode files alongside the already-modified source paths. Git reported no newly staged files or unexpected tracked source path beyond this ticket's intended edits, and `git diff --check` remained clean, but the campaign did not retain before/after constituent manifest entries. Therefore the exact cause and source-byte equality cannot be proven retrospectively; source equality is inconclusive for this campaign. The harness now excludes Python bytecode cache artifacts from its future source manifest, but no fourth live command was run to regenerate evidence.

The executed harness deleted each raw file immediately but held decoded payload objects transiently in process memory until idle cleanup and sanitized emission; they were never written or retained. After the campaign, the harness was tightened to compute redacted parity and clear decoded objects before the five-minute wait. This post-campaign privacy hardening was compile-checked but, correctly, did not trigger a fourth live command.

This is the sole retained A/B mismatch. Model-cache equality and all output/route/result parity checks passed.

## Acceptance mapping and limits

1. Prerequisite independent review: passed and closed before integration.
2. Retrieve-only flag/help/docs: implemented and tested.
3. No-flag behavior/dormancy: lazy backend import and unchanged no-flag calls tested; full suites passed.
4. Automatic same-worker route/retrieval: same adapter object and two exact calls tested; live PID reused across commands.
5. Explicit live/dry-run: one injected encode tested; dry-run no worker path tested.
6. Configuration/capability/runtime errors: bounded, redacted, phase-correct, no fallback/replay tests passed.
7. Local validation/package gates: passed before live.
8. Exactly three commands: completed in required order; no fourth command.
9. Redacted evidence: retained above, including the source-manifest mismatch.
10. Independent post-change review: passed at `.10x/reviews/2026-08-27-experimental-retrieve-embedding-worker-review.md`; its one minor harness privacy finding was corrected and targeted rereview passed.
11. Default-on: not changed or recommended automatically.

Residual limits:

- Source equality is inconclusive because the executed broad manifest included ignored runtime bytecode and constituent differences were not retained.
- Three commands on one Darwin arm64 host cannot establish a latency distribution or isolate provider/network variance.
- Same-effective-user processes remain inside the Unix socket permission boundary.
- Network absence inside the worker is controlled by offline/source procedure rather than packet tracing; normal CLI provider reads were authorized and expected.
- The observed RSS is one post-command sample, not peak RSS.
