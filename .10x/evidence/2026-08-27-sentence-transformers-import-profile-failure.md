Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Relates-To: .10x/tickets/cancelled/2026-08-27-profile-sentence-transformers-import-tree.md

# Sentence Transformers Import Profile Failure

## Outcome

The authorized import-only campaign passed its complete preflight and non-target self-test sequence, then stopped fail-closed when the first and only target child—the discarded warm-up—terminated nonzero. The sanitized failure category is `child_nonzero_exit`.

The warm-up authority was consumed. No retained observation started, no retry/replacement/reordering occurred, and there are zero import-profile timing rows. Raw stderr/stdout, profile rows, exception detail, process identity, paths, and partial timing were not retained. This failure is not interpreted as import, retrieval, model, device, or performance evidence.

## Pre-consumption controls

Before the warm-up began, the external harness:

- bound the deterministic current worktree/status, relevant source/lock, Python executable, package, model-cache, and telemetry-metadata states;
- used CPython 3.13.0 on Darwin 25.5.0 arm64;
- resolved `sentence-transformers 5.6.0`, `transformers 5.12.1`, `torch 2.12.1`, `numpy 2.4.6`, `scipy 1.18.0`, `scikit-learn 1.9.0`, `pandas 3.0.3`, `huggingface-hub 1.20.1`, `tokenizers 0.22.2`, `safetensors 0.8.0`, and `turbopuffer 2.4.0` from package metadata without importing the target libraries;
- constructed a minimal exact-key child environment whose intersection with the exact credential-key denylist was empty, inspecting names only;
- enabled offline/local-only controls, disabled telemetry, and installed process-level network denial;
- passed a standard-library-only `-X importtime` launch/parser control;
- rejected empty, non-importtime, malformed-numeric, and incomplete synthetic profiles;
- passed watchdog timeout, unexpected-descendant detection/process-group termination, denied-network, cleanup, and bound-state-equality self-tests; and
- protected the repository, relevant model cache, and telemetry root from child writes through the temporary sandbox profile.

The self-test imported neither `sentence_transformers`, `torch`, nor `transformers`. No target warm-up authority was consumed until all these controls passed.

## Bound and terminal identities

Exact relevant identities were:

- `pyproject.toml` SHA-256: `29c69a012a4374b4a4f81328382fd42bb5662e5d14d378b74c7463dd7a5b500b`;
- `uv.lock` SHA-256: `ad7508159bc00271b21fc598bad07b56045329c938ed4fbd37a5a18d71c4c254`;
- `src/buoy_search/indexing/chunker.py` SHA-256: `98a036fa829cbec675b5fd04cc1dd717a0ccc04c417a25ea33433827cec908d8`;
- `src/buoy_search/retrieval/retriever.py` SHA-256: `e087019eb373d433eaedd3a6ab26db297be740e7992ab53159251e9c5031b2b0`; and
- Python executable SHA-256: `2bfbeb6d935f72272e37921df5f0588be257b95ac67187691461af74308169f1`.

After terminal cleanup and before this evidence record was added, bounded readback reported:

- worktree manifest: 1,237 entries, 17,613,212 content bytes, SHA-256 `75f2c8056b6cc03acfed8c77b231d253d900bf00950b3cf5df1b07d9a433ead6`;
- Git status manifest: nine entries, SHA-256 `4edf10b8719077450230cd1a1497453f134ae1020dd7cfda101e6dedddfb415c`;
- relevant model-cache manifest: 43 entries, 267,599,470 content bytes, SHA-256 `1c5900741f69fcf4efcdaae0591dacd7301a0509b6d800354e9db58af9709817`; and
- telemetry metadata manifest: 37 entries, SHA-256 `4a8965d85e73784812473a85adf63d354b700fa2a5d3653e27d6a9f91fd4f89a`.

The preflight's in-memory state comparison passed immediately before target execution. The protected sandbox denied writes to the three governed roots during the failed warm-up. The privacy contract required deletion rather than retention of the private harness and raw state payload, so the record does not claim an independently reproducible pre/post manifest pair beyond those bounded controls and terminal identities.

## Cleanup and prohibited effects

The external harness root and sanitized-result target were removed after the stop, and filesystem checks verified both absent. The failed child executed only the governed import statement; it did not construct a model, retriever, or provider client and could not run query, encode, retrieve, catalog, content, telemetry/store, build/install, Git-ref, release, or deployment paths. Network operations were denied by the sandbox. No production or test source was edited.

`git diff --check` passed and no files were staged after cleanup. No further target child may run under this ticket.

## Limits

No raw failure detail, module row, exclusive/cumulative interval, RSS value, elapsed value, or partial timing survives. The evidence supports only the passed preflight/self-tests, consumed failed warm-up, zero retained observations, fail-closed stop, bounded identities, prohibited-effect boundary, and cleanup.
