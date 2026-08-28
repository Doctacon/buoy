Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Relates-To: .10x/tickets/done/2026-08-27-measure-current-provider-free-retriever-construction.md

# Current Provider-Free Retriever Construction Preflight Failure

## Outcome

The authorized current-source campaign stopped during credential-removal preflight before the non-model protocol self-test and before any model child started. The sanitized failure category is `credential_environment_validation_failed`.

No warm-up or retained observation authority was consumed. Zero model children, zero provider operations, zero queries, zero embedding encodes, zero telemetry/store operations, and zero permitted network attempts occurred. No timing was retained and there is no five-sample result.

The failure is not interpreted as a retrieval, model, cache, provider, or performance result. It grants no implicit retry.

## Bound preflight identities

The stopped preflight bound the current source state before child launch:

- Git status entries: 2 records-only entries;
- Git status manifest SHA-256: `f6a94eb449ec1fa4d1ff4e39a4e2026b1daa21222a55159263fb6249a0c26b02`;
- `pyproject.toml` SHA-256: `29c69a012a4374b4a4f81328382fd42bb5662e5d14d378b74c7463dd7a5b500b`;
- `uv.lock` SHA-256: `ad7508159bc00271b21fc598bad07b56045329c938ed4fbd37a5a18d71c4c254`;
- `src/buoy_search/config.py` SHA-256: `b33407002f60c6ca3429e05043f2c1451902112bf793ce2ae2ed0ae9e4da5620`;
- `src/buoy_search/indexing/chunker.py` SHA-256: `98a036fa829cbec675b5fd04cc1dd717a0ccc04c417a25ea33433827cec908d8`;
- `src/buoy_search/retrieval/retriever.py` SHA-256: `e087019eb373d433eaedd3a6ab26db297be740e7992ab53159251e9c5031b2b0`; and
- Python executable SHA-256: `2bfbeb6d935f72272e37921df5f0588be257b95ac67187691461af74308169f1`.

The bounded runtime was CPython 3.13.0 on Darwin arm64 with sentence-transformers 5.6.0, transformers 5.12.1, torch 2.12.1, and turbopuffer 2.4.0.

The exact local model ref remained `BAAI/bge-small-en-v1.5` revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, float32, with 12 snapshot assets. The complete relevant model-cache manifest contained 44 entries and 267,600,148 content bytes at SHA-256 `ba04c92fd9f4705fc3c9da63cd4c07da4c6d9d86c055e861d071d53528a205ae`.

## Stop and cleanup

The preflight rejected the sanitized child environment before launching a subprocess. Therefore network denial, descendant detection, watchdog behavior, protocol parsing, production automatic-device selection, and model construction were not executed or claimed.

The owner-private temporary harness root was removed by the terminal cleanup handler. A bounded filesystem check found no remaining campaign root. No files are staged.

Because no child started and the only pre-stop actions were repository/cache identity reads plus creation of the external temporary harness, no source, cache, telemetry, provider, network, model, build, install, Git ref, release, or deployment mutation occurred.

## Limits

This record intentionally retains no raw exception, stack, command environment, credential presence/value, process identifier, private path, host/user identity, raw child output, or partial timing. It supports only the preflight stop, zero-child ledger, bounded identities, and cleanup result.
