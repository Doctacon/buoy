Status: no-result-continuation
Created: 2026-08-28
Updated: 2026-08-28
Ticket: .10x/tickets/done/2026-08-28-measure-provider-free-cross-encoder-boundaries.md
Prior-Evidence: .10x/evidence/2026-08-28-provider-free-cross-encoder-boundaries-no-result.md
Research: .10x/research/2026-08-28-provider-free-cross-encoder-boundaries-continuation-no-result.md

# Provider-Free Cross-Encoder Boundary Measurement Continuation: No Result

## Disposition

The owner-ratified continuation stopped fail-closed in the separately authorized harness-debugging phase. No governed warm-up and no retained measurement process started. The original six-process sequence remains entirely unconsumed. No timing or score is retained or claimed.

The amended contract permits at most one direct, exactly attributed standard-library `multiprocessing.resource_tracker` companion under the same CPython executable and rejects every other descendant. After the monitor was corrected to recognize the runtime's exact `python3 -B -c` resource-tracker form, the next exact-target debug launch observed a different direct child. It did not contain the `multiprocessing.resource_tracker` module marker and did not match either permitted `-c` command shape. The monitor rejected it immediately. That is an amended-contract failure, so debugging stopped without broadening the exception or starting governed measurement.

## Bound preflight identity

The continuation re-bound current identity before model debugging:

- source manifest: SHA-256 `5010640eeb6fea1038519e43c58fcbe2893c604eb85d64e7df60e61efd5f7b7c`, 1,268 tracked/untracked non-ignored entries;
- changed-path manifest: SHA-256 `93b327ff36a0a97fab92c1021de21d28de6a6effa13f3d98f7649c280778b624`, four entries;
- `src/buoy_search/retrieval/cross_encoder.py`: SHA-256 `ed963371948f9c51fdbc7d25df4193613e7b2616f34ba18e7b7b2e01d2ba1674`;
- `pyproject.toml`: SHA-256 `29c69a012a4374b4a4f81328382fd42bb5662e5d14d378b74c7463dd7a5b500b`;
- `uv.lock`: SHA-256 `ad7508159bc00271b21fc598bad07b56045329c938ed4fbd37a5a18d71c4c254`;
- exact reranker-cache regular-file/symlink manifest: SHA-256 `1b48ba93fbfb431d256caf1e2c1531a0f942b0631f340f39e2a4dfe820d133ff`, 20 entries, including six exact-revision snapshot entries; and
- model `cross-encoder/ms-marco-MiniLM-L-6-v2` revision `c5ee24cb16019beea0893ab7796b1df96625c6b8`, production CPU, max length 512, batch size 8, local-only safetensors, and remote code disabled.

Runtime identity was CPython 3.13.0 on Darwin arm64 with sentence-transformers 5.6.0, torch 2.12.1, transformers 5.12.1, and NumPy 2.4.6.

The deterministic synthetic fixture identity was SHA-256 `9f7fb2b71be7d5e19f7d88ec9d990591beec941abef0b04159fb5e33400b3da9`, 18,271 UTF-8 bytes, a nine-word query, and 74 33-word passages. It contained no provider, retrieved, namespace, credential, user, or path content.

## Controls and debugging

The external harness lived in a mode-0700 directory outside the repository and was mode 0600. Child environments removed an exact 12-key credential denylist and `PYTHONPATH`; set Hugging Face, Transformers, and datasets offline controls; disabled Hugging Face, OpenTelemetry, and Buoy telemetry; disabled bytecode writes; and installed a connect/connect-ex/sendto/create-connection network guard before importing production retrieval code.

The preflight passed cache completeness/readability, source/cache identity, fixed model/fixture identity, credential removal, offline controls, and no-staged-files checks. The non-model self-test passed valid/malformed protocol handling, watchdog termination, descendant detection, process-group cleanup, synthetic loopback denial, and the 4 GiB RSS-limit check.

Harness debugging remained separate from measurement authority. Early debug launches exposed monitor parsing defects around process-table loss of shell quoting and CPython's inherited `-B` flag. Those launches were discarded under debugging authority and retained no timing or score. The parser was narrowed to the exact standard-library command form rather than weakening module or parent validation.

The next exact-target debug launch then exposed the unapproved direct descendant described above. It was not reclassified, allowlisted, retried under governed authority, or inspected into a new product/runtime exception. Its raw command, process identifiers, paths, stderr, and stack material were not retained.

The final external harness SHA-256 was `20c9ba0ea241d8a4d684cf437703159d8de8bfe869610885683af9984a021adf`. Because execution stopped during debug, the final parser revision did not consume measurement authority and no claim is made that it completed a model observation.

## Governed sequence ledger

| Governed order | Role | Status |
| ---: | --- | --- |
| 1 | discarded warm-up | not started |
| 2 | retained 1 | not started |
| 3 | retained 2 | not started |
| 4 | retained 3 | not started |
| 5 | retained 4 | not started |
| 6 | retained 5 | not started |

There was no governed retry, replacement, reordering, timing retention, percentile, total, target, or optimization claim.

## Effects, terminal equality, and cleanup

A terminal preflight recomputed the bound source, changed-path, cache, source-file, lock, fixture, runtime, and model identities. Every compared field equaled the initial preflight. No staged file existed.

No provider credential was available to a child. No live command, provider SDK/client, catalog/namespace/content retrieval, embedding worker, telemetry store, model download/cache repair, source/test edit, build/install, Git ref mutation, release, deployment, or publication ran. The installed network guard permitted zero connection operation; no external service was contacted.

No external harness process or model-child lineage remained. The complete external harness directory, child output/error files, debug material, and identity files were deleted, and directory absence was verified.

## Acceptance disposition

The ticket's method correctly rejected a descendant outside the one owner-approved exception. Criteria requiring the accepted warm-up, five retained rows, exact final model protocol, and a performance conclusion remain unsatisfied. Source/cache preservation, no staged files, no prohibited external effect, truthful no-result retention, and external cleanup passed. The ticket remains blocked; this evidence does not authorize another descendant exception or cross-encoder worker expansion.
