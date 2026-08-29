Status: completed
Created: 2026-08-28
Updated: 2026-08-28
Ticket: .10x/tickets/done/2026-08-28-run-cross-encoder-worker-three-command-live-ab.md
Review: .10x/reviews/2026-08-28-cross-encoder-worker-three-command-live-ab-review.md
Decision: .10x/decisions/buoy-runs-one-three-command-cross-encoder-worker-live-ab.md
Specification: .10x/specs/cross-encoder-worker-three-command-live-ab.md
Research: .10x/research/2026-08-28-cross-encoder-worker-live-ab-findings.md
Prior-Evidence: .10x/evidence/2026-08-27-experimental-retrieve-embedding-worker-ab.md

# Cross-Encoder Worker Three-Command Live A/B Evidence

## Disposition

The exact owner-authorized three-command automatic read-only campaign completed successfully in baseline, cold-worker, warm-worker order. Exactly three live retrieve subprocesses started and completed; there was no retry, replacement, reorder, or fourth command. All three exited zero with empty stderr and byte-identical output, payload, route, structural shape, hit count, namespace count, and content-free logical provider-read counts.

The schema-v2 worker was absent before and after the baseline, started for the cold command, and was reused by the warm command. Its natural five-minute idle cleanup completed without signaling. No raw result content, namespace or route value, URL, credential, PID, socket/cache path, provider response, decoded provider object, or raw error was retained.

No provider write/management operation, fallback warning, telemetry/store change, model download/cache mutation, source/lock change, install, release, deployment, commit, or staging operation occurred.

## Successor harness and preflight

A new successor harness was created at `tests/fixtures/cross_encoder_worker_live_ab.py`. The retired historical harness was not edited or reactivated. The executed successor harness SHA-256 was `de223a905e088a935cb40dc0a88cec01de7369db9582693d0f140779f4dc4ca2`. Immediately after the successful campaign, only its live-authority constant was changed to consumed; the final retired harness SHA-256 is `8a96535b211a2d0a8cd9609e5dd1149dc66066a8e71cbd1054f07b7f0605e34b`.

Before live authority began:

- the harness provider-free synthetic self-test passed redaction, raw-file deletion, malformed-output classification, nonzero-stop classification, exact order, and exact three-command count;
- focused schema-v2 worker, multi-namespace, automatic-routing/provider-count/fallback/privacy, and CLI suites passed 196 tests in 9.907 seconds;
- harness and focused test compilation passed;
- the exact credential name was present, but its value was not read, printed, hashed, or retained;
- unrelated exact credential names and `PYTHONPATH` were removed from the one-shot harness process before live children inherited the environment;
- Buoy, OpenTelemetry, and model telemetry were disabled; model loading was forced offline/local-only while normal authorized provider network remained available;
- no schema-v2 socket/ready state or worker process was present;
- source, changed-path, lock, runtime/package/worker, embedding-cache, reranker-cache, and telemetry-store identities were bound;
- both exact revision snapshots were complete/readable;
- `git diff --check` passed and no file was staged; and
- all temporary files used mode 0600 under mode-0700 directories outside the repository.

Pre-campaign bound identities:

| Identity | SHA-256 | Entry/count detail |
| --- | --- | ---: |
| `src/buoy_search` excluding bytecode | `795b22f09a451a17e85aa41676478bc9a61abe305fdfe0d506917d5754c2ccc4` | 101 |
| changed-path manifest | `4e0f935c8b3b2f46d05809074db191fc367c47cb5350e158740c8a20f5eb6264` | 28 |
| `pyproject.toml` plus `uv.lock` | `29a9aa17734905bb2ba70e6065d3343732d70e5edb5351cc56d2fc4b00ddb400` | 2 |
| runtime/package/worker identity | `5c0c7b1c4b6a1f740016a3ef9c88fc2ce84cb64fd12448a972932553a058a0c9` | schema 2 |
| embedding model cache | `abfc9af76d72e33fe5e56feee7ea1ae05deae2ef9329caf99a4dc885610a7dc9` | 43 |
| reranker model cache | `69129010156c6adb79160561f37ba8a1138f6565e660df1ffab825aa48043e23` | 26 |
| telemetry store | `17badacc47e8b82fe00846cc353b2195e01e349d18da94c75eb1a7871cb3855c` | 37 |

The runtime was CPython 3.13.0 on Darwin arm64, package `0.6.5.dev0+g42ec57198.d20260828`, worker schema 2/implementation `887bd4f2d299b007d60f4a5bccc13bb27bc13d455841c01e7eaf0f5c858c5ca6`, exact `BAAI/bge-small-en-v1.5` revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, and exact `cross-encoder/ms-marco-MiniLM-L-6-v2` revision `c5ee24cb16019beea0893ab7796b1df96625c6b8` on CPU/max-length 512/batch-size 8.

## Immutable command ledger

| Ordinal | Role | Worker mode | Status | Retry/replacement |
| ---: | --- | --- | --- | --- |
| 1 | baseline | `--no-embedding-worker` | completed | none |
| 2 | cold worker | default schema-v2 worker | completed | none |
| 3 | warm worker | same default worker | completed | none |

Live operation count was exactly 3. Completed operation count was exactly 3. The harness has no fourth command entry. After the result was reduced, live authority was retired in source; no live command followed.

## Redacted live observations

The fixed query identity was SHA-256 `c52585eb8082f84b6f0cdde17e9ce83cbbb3c050eed378748c500f7ac041f348`. The query text is governed by the decision/specification and is not result content.

| Role | Wall ms | Exit | stdout bytes | stderr bytes | Hits | Namespaces | Catalog logical reads | Namespace results |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 16,101.925875 | 0 | 20,738 | 0 | 5 | 3 | 5 | 3 |
| cold worker | 6,752.035625 | 0 | 20,738 | 0 | 5 | 3 | 5 | 3 |
| warm worker | 2,853.658708 | 0 | 20,738 | 0 | 5 | 3 | 5 | 3 |

All three retained these exact hashes:

- complete stdout: `aa583f89a669f940faf5ad8767fa9c12f021b1c7f9ff6044d504474a81b54d36`;
- canonical payload: `8b2c9649427313151f79e0be16dd836cefab1b5d9f23b8112624431570f20580`;
- ordered route identity: `91ff1a2a6375d7201f4de839d2460ad5de36fbbd2dff4cf0a6ac8b1bbda57e32`;
- structural shape: `0590147f28af1890f8275bb4191b3ceb27f475423b8276c9457b290f5e566a67`;
- empty stderr: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

Every within-campaign parity boolean was true: exit, stdout bytes/hash, stderr bytes/hash, payload, route, shape, hits, namespaces, catalog logical reads, and namespace-result count. No failure/stop category occurred.

The catalog/read counts are content-free logical counts reduced from the established result payload. They do not instrument physical SDK attempts or establish absence of provider-side retries. Empty stderr proves no visible worker fallback warning occurred. The public retrieve command has no provider write surface, and the harness invoked no provider API directly.

Observed differences for this one ordered sequence:

- cold worker wall time was 58.066907% below baseline;
- warm worker wall time was 82.277532% below baseline; and
- warm worker wall time was 57.736320% below cold worker.

These are arithmetic descriptions of three observations, not a distribution, percentile, causal provider-adjusted estimate, SLA, target, or release gate.

## Worker lifecycle, privacy, and cleanup

The cold and warm commands used one matching schema-v2 worker identity and the same transient process identity; only the reuse boolean was retained. One post-command combined worker RSS observation was 691,650,560 bytes. This is neither peak RSS nor a memory target.

After warm output was parsed and reduced, decoded payload references and raw stdout/stderr were deleted before idle waiting. The harness waited without signaling. Validated socket/state/process absence completed after 300,607.889708 ms. The campaign temporary directory and the outer private result/error wrapper were deleted. Harness stderr was empty with SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

No compatible worker state/process survived. No raw output or decoded provider-derived object was retained. Durable records contain only the specification-approved redacted fields.

## Terminal identity and side-effect checks

Before/after equality was true for:

- source manifest;
- changed-path manifest;
- lock manifest;
- runtime/package/worker identity;
- exact embedding cache;
- exact reranker cache; and
- telemetry store.

Telemetry remained disabled and model network remained disabled. Provider writes were zero. No fallback warning, model download/cache repair, bytecode source-manifest pollution, install/build, release, deployment, publication, commit, or staging occurred.

The complete output/payload/route/shape hashes also happen to equal the prior embedding-only campaign's retained hashes. That historical equality is context only; it is not an acceptance dependency because source, worker protocol, and remote state could have changed.

## Acceptance disposition

After retirement, harness/test compilation and the provider-free synthetic self-test passed again; the same focused suite passed 196 tests in 7.786 seconds. `git diff --check`, zero staged files, historical-harness no-diff, no compatible worker process, and external campaign-directory absence checks passed.

Criteria 1–9 are supported by this evidence and `.10x/research/2026-08-28-cross-encoder-worker-live-ab-findings.md`. Independent review at `.10x/reviews/2026-08-28-cross-encoder-worker-three-command-live-ab-review.md` passed criterion 10 and all campaign acceptance claims. No additional live campaign or production/release action is authorized.
