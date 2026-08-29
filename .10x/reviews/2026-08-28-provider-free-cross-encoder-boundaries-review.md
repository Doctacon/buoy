Status: passed
Created: 2026-08-28
Updated: 2026-08-28
Target: .10x/tickets/done/2026-08-28-measure-provider-free-cross-encoder-boundaries.md
Evidence: .10x/evidence/2026-08-28-provider-free-cross-encoder-boundaries.md
Research: .10x/research/2026-08-28-provider-free-cross-encoder-boundaries-findings.md
Verdict: pass

# Provider-Free Cross-Encoder Boundaries Independent Review

## Scope

Independent acceptance review of the current provider-free cross-encoder boundary campaign, its governing diagnostic decision, two prior immutable no-result campaigns, final evidence and research, production cross-encoder source, executor transcript/result, current repository state, and cleanup. No model measurement was rerun. This review created only this review record.

## Findings

No blocking findings.

The exact production identity in `src/buoy_search/retrieval/cross_encoder.py` matches the campaign: `cross-encoder/ms-marco-MiniLM-L-6-v2` revision `c5ee24cb16019beea0893ab7796b1df96625c6b8`, CPU, max length 512, batch size 8, local-only loading, safetensors, and disabled remote code.

The executor's persisted transcript contains both the final harness source and its complete sanitized success result. Reconstruction of the final harness after its debug-phase edits confirmed:

- `sentence_transformers.CrossEncoder` import begins after the first `perf_counter_ns` checkpoint;
- construction and the 1-, 24-, and 49-pair score calls are separated by consecutive checkpoints, so each retained duration is computed from adjacent boundaries and cannot overlap another interval;
- the parser rejects missing/non-finite intervals, wrong score counts, non-finite scores, wrong model/runtime contract, credential presence, network attempts, and forbidden provider/catalog/worker/telemetry modules;
- measurement authority begins only after preflight, non-model self-test, and a discarded exact-target debug observation;
- the governed loop contains exactly `discarded_warmup`, then `retained_1` through `retained_5`, with identity checks before and after every child and no retry branch;
- each child starts a new session/process group; lineage containment, group RSS, timeout, complete-group termination on failure, and terminal zero-survivor cleanup are checked; and
- the external temporary directory is removed in `finally`.

The persisted success result contains the six ordered ledger entries, five timing rows, score counts/finiteness booleans, source/cache/model/runtime/fixture identities, RSS/elapsed-limit booleans, no-effect counters, and terminal equality/cleanup booleans. A mechanical comparison found both Markdown timing tables exactly equal to that result. Current production source, project, lock, and reranker-cache hashes also equal the recorded identities.

### Prior review concern

The earlier blocking review was reasonable given its restricted interface, but it does not remain a blocker under the current evidence available to this review:

- current Git status, staged state, diff hygiene, production/test diffs, source hashes, cache manifest, record links, and external-artifact absence were independently checked here;
- the machine-readable success result and final harness are inspectable in the executor transcript, rather than existing only as prose; and
- the ticket requires a six-process ledger and five separate timing rows, but does not require retaining a repository machine-readable artifact or absolute interval endpoint values. Non-overlap is established by the inspected adjacent-checkpoint implementation.

Privacy-required deletion of the external harness/raw runtime directory is therefore not an acceptance defect. No credential value, PID, model score, token ID, provider content, query result, or private runtime path is copied into this review.

## Acceptance-criteria map

1. **Preflight, debug separation, and self-test — PASS.** The transcript records a successful discarded debug command before the governed invocation. The final harness performs identity/cache/staged checks, malformed-protocol rejection, descendant containment, watchdog group cleanup, RSS enforcement, and denied-loopback validation before measurement authority.
2. **One discarded warm-up and five retained fresh processes — PASS.** The machine-readable ledger has exactly six fixed-order completed entries, all below 120 seconds and 4 GiB, with complete group cleanup. The loop has no retry/replacement branch.
3. **Five separate intervals and score validation — PASS.** Five retained rows exactly match the transcript result. Adjacent monotonic checkpoints implement non-overlap; all rows report counts `[1, 24, 49]` and finiteness `[true, true, true]`.
4. **Exact identities throughout — PASS.** The harness asserts source/cache/staged identity before and after every child and finalizes only after terminal equality. Current source hashes and cache manifest independently match the recorded identities.
5. **No prohibited effects and complete cleanup — PASS.** The transcript result records zero effects, zero credential keys, zero network attempts, no forbidden modules, contained process groups, and zero surviving lineage. Exact child code has no provider/catalog/content/worker path. Offline/local-only controls plus current cache equality support no-download/no-mutation claims.
6. **Bounded dated findings — PASS.** The research correctly identifies the 7,460.980291–7,928.117125 ms import/runtime interval as dominant over 72.913000–88.451625 ms construction and bounded scoring. It does not sum intervals, claim a percentile/SLA, or authorize implementation.
7. **External artifact deletion — PASS.** Transcript cleanup commands passed; an independent current check found the named harness/result and dynamic external campaign directory absent.
8. **Independent review — PASS.** This review checked method, identities, privacy, sequence, cleanup, no-effects, repository state, and residual risks with no blocker.

The two prior no-result records remain coherent historical evidence. Both state zero governed model processes and do not conflict with the later owner-amended campaign.

## Commands and checks

- `git status --short`, `git diff --cached --name-only`, `git diff --check`, and production/test diff inspection: clean diff syntax, zero staged files, zero production/test diffs; only the current `.10x` research/evidence/ticket records were present before this review.
- `sha256sum` over production cross-encoder source, `pyproject.toml`, and `uv.lock`: exact match to retained evidence.
- Read-only reranker-cache manifest recreation: SHA-256 `602a7517c04e0aa924c595b13cd674591bf3f12e91f6447d5c11e81c33f68a65`, 20 entries, six required snapshot assets complete.
- Record-link/file-presence check: passed.
- External `/tmp` campaign-artifact absence check: passed.
- Executor transcript reconstruction and inspection: final harness method confirmed.
- Mechanical transcript-result versus evidence/research comparison: all five rows exact; ledger, score validation, effect counters, and terminal controls exact.

No model, provider, network, telemetry, build, install, or live retrieval command ran during review. No tests were added because this ticket changes no production or test code.

## Verdict

**PASS. Merge/closure verdict: OK.**

The ticket's eight acceptance criteria are supported. Process-cold Sentence Transformers/CrossEncoder import and transitive runtime initialization is the strongest measured residency candidate in this bounded condition.

## Residual risk

- One Darwin arm64 host, one dependency/runtime set, one cached revision, and synthetic 48–49-token pairs do not establish production-content distributions, percentiles, or cold-host behavior.
- Import timing remains a transitive boundary; it does not attribute Torch, Transformers, native-library, or device-runtime subcomponents.
- The process monitor samples the process table rather than using kernel-enforced containment; a very short-lived escaping helper could theoretically evade one poll. The unchanged local model path showed no cleanup/effect failure, and inherited network denial plus terminal group checks bound this risk.
- Review reproducibility depends partly on the retained executor transcript because privacy policy correctly required deletion of raw external runtime artifacts.
