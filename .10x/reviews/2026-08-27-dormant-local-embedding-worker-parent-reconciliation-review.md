Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Target: src/buoy_search/retrieval/embedding_worker.py; tests/retrieval/test_embedding_worker.py; tests/fixtures/embedding_worker_validation.py; .10x/tickets/done/2026-08-27-build-dormant-local-embedding-worker-prototype.md
Verdict: concerns

# Dormant Local Embedding Worker Parent Reconciliation Review

## Scope

Parent inspection after implementation against `.10x/specs/dormant-local-embedding-worker-prototype.md`, focused on bounded transport failures, no replay, worker lifetime authority, socket/state cleanup, dormancy, and retained evidence.

This is a parent reconciliation review, not the ticket's required independent review. The scheduled independent reviewer did not start because the containing subagent workflow exhausted its reported-token hard budget after implementation.

## Findings

### Significant — post-connect transport failures could escape the bounded public API

Initial `_connect_and_encode` handling mapped connection establishment failures but could allow greeting/response timeout, reset, or truncated transport failures to escape as raw exceptions. This violated the bounded visible-error contract and made the idle-shutdown race unsafe at the public boundary.

Resolution: corrected. Pre-query greeting transport failures now enter only the safe start/reuse path. Once request transmission begins, failures are never retried: timeout maps to `busy_timeout`, reset/OSError to `internal_worker_failure`, and malformed/truncated protocol to `protocol_error`. Focused tests cover greeting reset, response timeout, truncated response, and no post-request spawn/fallback.

### Significant — shutdown released lifetime authority before listener and inode cleanup

Initial `run_worker` cleanup released the lifetime flock before closing the listening socket and unlinking inode-bound socket/state objects. A new starter could acquire cleanup authority while the old listener was still momentarily live.

Resolution: corrected. Listener close and inode-bound socket/state cleanup now occur while the lifetime lock remains held. Focused tests prove close-before-unlink, competing lock exclusion through cleanup, and successful acquisition only after shutdown.

## Verification observed

- Parent reran `uv run --python 3.13 python -m unittest -q tests.retrieval.test_embedding_worker`: 28 tests passed.
- Parent reran `git diff --check`: passed.
- Parent inspected production references: only the dormant module's own subprocess module string references `embedding_worker`; no established production path imports or calls it.
- Implementer reran full Python 3.11 and 3.13 suites after corrections: 1,219 tests passed on each runtime.
- Corrected provider-free model validation retained exact vector/ranking parity and worker reuse.

## Verdict

Concerns. Both parent findings are resolved with focused tests, and no further significant issue was identified in bounded parent inspection. Ticket closure remains unsupported until a genuinely independent reviewer inspects the post-correction implementation and returns a passing verdict with no unresolved significant findings.

## Residual risk

- No independent post-correction review exists yet.
- Real-model evidence is limited to one Darwin arm64 host.
- Same-effective-user processes remain inside the Unix permission boundary.
- Product activation and rollout behavior remain explicitly out of scope and undecided.
