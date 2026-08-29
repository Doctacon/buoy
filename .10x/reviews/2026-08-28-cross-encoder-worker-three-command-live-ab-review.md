Status: passed
Created: 2026-08-28
Updated: 2026-08-28
Target: .10x/tickets/done/2026-08-28-run-cross-encoder-worker-three-command-live-ab.md
Evidence: .10x/evidence/2026-08-28-cross-encoder-worker-three-command-live-ab.md
Research: .10x/research/2026-08-28-cross-encoder-worker-live-ab-findings.md
Verdict: pass

# Cross-Encoder Worker Three-Command Live A/B Independent Review

## Scope

Independent acceptance review of the governing decision/specification, active ticket, prior embedding-only campaign, scoring-worker implementation evidence/review, successor harness and tests, retained live evidence/research, executor transcript/result, current Git state, exact source/dual-model-cache identities, worker cleanup, privacy, and bounded interpretation.

This review ran no live retrieve/provider command and changed no harness, source, tests, evidence, research, decision, specification, or ticket. It created only this review record.

## Findings

No blocking findings.

### Authority, order, and exact command accounting

The executor transcript establishes that the 196-test focused provider-free suite passed before preflight, exact preflight completed with worker absence and bound identities, and only then one shell tool invocation started the live harness. The transcript contains exactly one `--execute-live` bash tool start. That invocation completed successfully and emitted one sanitized machine-readable result.

The inspected harness freezes:

- query `How is approximate vector recall evaluated?` with retained SHA-256 `c52585eb8082f84b6f0cdde17e9ce83cbbb3c050eed378748c500f7ac041f348`;
- baseline arguments `--json --no-embedding-worker`;
- cold arguments `--json`;
- warm arguments `--json`; and
- exactly three ordered roles: baseline, cold worker, warm worker.

Its fixed loop has no retry, replacement, or fourth-command branch. It marks each ordinal started/completed/failed, stops on the first command, parity, worker, identity, or cleanup failure, and reports started/completed counts. The retained result contains exactly three completed ledger rows, `live_operation_count=3`, `completed_operation_count=3`, no stop category, and no fourth entry. Immediately afterward the executor changed only `LIVE_AUTHORITY_CONSUMED` from false to true; the current entry point rejects live execution before credential or subprocess work, and its source-named test passes.

### Retained result and evidence accuracy

The executor transcript's sanitized result mechanically matches evidence/research:

| Role | Wall ms | Exit | stdout bytes | stderr bytes | Hits | Namespaces | Catalog logical reads | Namespace results |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 16,101.925875 | 0 | 20,738 | 0 | 5 | 3 | 5 | 3 |
| cold worker | 6,752.035625 | 0 | 20,738 | 0 | 5 | 3 | 5 | 3 |
| warm worker | 2,853.658708 | 0 | 20,738 | 0 | 5 | 3 | 5 | 3 |

All stdout, stderr, payload, route, structural-shape, hit-count, namespace-count, catalog-count, and namespace-result parity booleans are true. The retained hashes and byte counts match the transcript result. Independent arithmetic reproduces 58.066907% cold below baseline, 82.277532% warm below baseline, and 57.736320% warm below cold.

The baseline worker-absence check occurs immediately after baseline reduction. Cold and warm validate the complete schema-v2 worker identity and one transient process identity; only identity/reuse booleans cross the retained boundary. The retained worker RSS is 691,650,560 bytes. Natural cleanup is recorded after 300,607.889708 ms without signaling, and both the harness result and a current independent check show no compatible worker state/process or external campaign directory.

### Privacy and external-effect boundary

`_run_and_reduce` writes stdout/stderr only to mode-private files, parses successful JSON, derives approved hashes/counts, explicitly drops decoded payload/route/raw byte references, and unlinks both raw files in `finally` before returning to the command loop. The provider-free sentinel test proves result content is absent from reduced output and raw files are gone. The current records contain no private path, credential assignment/value, PID value, socket path, URL/result content, provider sentinel, or raw error. A read-only executor-transcript scan found no required-credential assignment, private-key header, AWS-secret assignment, or common OpenAI secret prefix.

The outer live wrapper used private files, emitted the already-sanitized harness result, and deleted its result/error files and directory. Harness stderr was empty. The current harness self-test again proves redaction/raw cleanup, and no external campaign directory remains.

The harness invokes only the public retrieve CLI and contains no provider client/API call. The baseline opt-out and default commands have no write option; retained output reports the same five content-free logical catalog reads and three namespace results in every run. Empty stderr shows no visible worker fallback, and the reviewed scoring-worker fallback contract requires that warning on failure. Thus no worker-caused provider replay is observed. Logical payload counts do not expose physical SDK/provider retries; the evidence correctly preserves that as a limit rather than claiming packet-level accounting.

Telemetry and model-network controls are set before live child creation. The exact provider credential is checked by name membership only and inherited by the CLI; the harness never reads, prints, hashes, or retains its value. Unrelated named credentials and `PYTHONPATH` are removed before child execution. The worker remains credential-free under its independently reviewed spawn contract.

### Identity and hygiene

The live result reports before/after equality for source, changed-path, lock, runtime/package/worker, embedding cache, reranker cache, and telemetry-store identities. Current independent read-only recreation exactly matches the retained source, lock, runtime/worker, dual-cache, and telemetry-store hashes/counts. The final retired harness hash also matches evidence.

`git diff --check` passes. No file is staged. The retired historical experimental harness has no diff. Campaign production scope is zero; the new successor harness and three source-named harness tests are the only test/runtime additions for this ticket, alongside its evidence/research/ticket records.

## Acceptance-criteria map

1. **Provider-free preflight/self-test before authority — PASS.** Transcript order, self-test, focused 196-test run, exact identity preflight, worker absence, credential-name presence, diff hygiene, and staged-state checks precede the sole live invocation.
2. **Exactly three fixed commands — PASS.** One live-harness invocation, exact three-entry loop/ledger, three completed counts, no retry/replacement/reorder/fourth branch, and consumed current entry point.
3. **Baseline dormancy and schema-v2 reuse — PASS.** Baseline absence check passed; cold/warm complete worker identity and transient-process equality produced true identity/reuse booleans; no sensitive identity was retained.
4. **Exit/output parity — PASS.** Three zero exits, empty stderr, 20,738-byte identical stdout, five hits/three namespaces, and all payload/route/shape/count hashes equal.
5. **Read-only provider behavior/no duplication — PASS within the specified logical boundary.** Public retrieve-only harness, no write surface, equal logical catalog/namespace counts, empty fallback stderr, and unchanged fallback/provider-count tests support the claim. Evidence correctly disclaims physical SDK-attempt attribution.
6. **Raw/decoded destruction and allowed retention — PASS.** Source, synthetic sentinel test, transcript result, outer-wrapper deletion, leakage scan, and current artifact absence support per-boundary reduction/deletion and approved redacted-only records.
7. **Identity equality/no mutation — PASS.** Transcript result and independent current hashes match for source/lock/runtime/worker/dual caches/telemetry store; telemetry/model network were disabled; no staged/install/release/deployment effect exists.
8. **Reuse/RSS/natural cleanup — PASS.** One reused worker, bounded 691,650,560-byte observation, natural 300,607.889708 ms cleanup, external deletion, and current zero survivors are supported without retained PID/path.
9. **Bounded evidence/research — PASS.** Exact observations and historical context are reported without percentile, SLA, release, cold-host, statistical, or provider-adjusted causal claims; order/network/RSS/physical-attempt limitations are explicit.
10. **Independent review — PASS.** This review checked command accounting, source-backed behavior, privacy, external effects, identities, cleanup, evidence accuracy, diff hygiene, and staged state with no blocker.

## Commands and checks

- `uv run python tests/fixtures/cross_encoder_worker_live_ab.py --self-test` — PASS: redaction, raw cleanup, malformed/nonzero categories, fixed order, exact count 3.
- `uv run python -m unittest tests.retrieval.test_embedding_worker tests.retrieval.test_multi_namespace_retrieval tests.retrieval.test_automatic_routing tests.cli.test_cli` — PASS: 196 tests in 7.756 seconds.
- `python3 -m compileall -q tests/fixtures/cross_encoder_worker_live_ab.py` — PASS.
- `git diff --check`, staged-file check, and historical-harness diff check — PASS; zero staged files and historical harness unchanged.
- Read-only source/lock/runtime/worker/dual-cache/telemetry manifest recreation — PASS: exact retained hashes/counts; worker absent; consumed final harness hash exact; zero external campaign directories.
- Static exact query/command/count inspection — PASS.
- Executor transcript inspection — PASS: preflight before authority, exactly one live-harness shell start, exact sanitized result, no common credential-value signatures.
- Retained-record leakage scan and timing arithmetic — PASS.

No live retrieve/provider command, credential read, model inference, download, telemetry operation, build/install, global mutation, release, deployment, or publication ran during review.

## Verdict

**PASS. Merge/closure verdict: OK.**

All ten ticket criteria are supported. The campaign authority is consumed and the successor harness is safely retired.

## Residual risks

- Exactly three ordered observations on one Darwin arm64 host do not establish a distribution, cold-host result, SLA, or statistical significance.
- Provider/network and order/host warming remain confounders because telemetry was intentionally disabled.
- Logical payload counts do not reveal physical SDK retries or provider-internal work.
- RSS is one post-command observation, not peak memory or a budget.
- Review reproducibility depends partly on the retained executor transcript because privacy correctly required deletion of raw live output and external runtime artifacts.
