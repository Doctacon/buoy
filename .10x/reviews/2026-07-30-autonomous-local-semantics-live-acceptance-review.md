Status: recorded
Created: 2026-07-30
Updated: 2026-07-30
Target: amended acceptance commit `bda745e1dbe8ca258a808e94df59db3d9d3b97b7`
Verdict: pass

# Autonomous Local Semantics Live Acceptance Review

## Findings

### Resolved — historical significant private-namespace fingerprint concern

The prior review of the pre-amend commit found that committed evidence retained a stable fingerprint of the selected private namespace. The amended evidence removes that fingerprint and refers to the candidate only generically (`.10x/evidence/2026-07-30-autonomous-local-semantics-live-acceptance.md:29-37`). Screening confirmed that the fingerprint and private namespace ID are absent from the amended commit's four changed paths and committed tree. This resolves the conflict with the ticket's private-ID exclusion and sanitized evidence allowlist (`.10x/tickets/2026-07-30-autonomous-local-semantics-live-acceptance.md:25-31`). No private value is reproduced in this review.

No blocker or significant finding remains.

## Correct behavior rechecked

- **Closed Content-Length transport repair:** `_read_response_with_deadline()` checks the real `HTTPResponse.isclosed()` state before touching the socket again, while preserving the existing monotonic deadline and response-byte cap (`src/buoy_search/semantics_local_model.py:269-299`). The regression makes a post-body timeout update fail with a closed-socket error and proves the complete declared body is returned (`tests/test_semantics_local_model.py:460-487`).
- **Raw Ollama digest canonicalization:** only exact lowercase raw 64-hex and exact `sha256:`-prefixed digests are accepted, both normalize to the prefixed form before installed/active conflict checks and configured-pin comparison; malformed values continue to fail closed (`src/buoy_search/semantics_local_model.py:43-45`, `src/buoy_search/semantics_local_model.py:319-336`, `src/buoy_search/semantics_local_model.py:613-631`). The regression proves a raw runtime digest matches the equivalent prefixed pin (`tests/test_semantics_local_model.py:192-203`), while the existing invalid/conflict cases remain passing.
- **Strict 1,000-row blocker:** the authorized cap and observed total are recorded in the blocked ticket (`.10x/tickets/2026-07-30-autonomous-local-semantics-live-acceptance.md:33-35`). Production estimate sums exact local ledger totals and returns `would_pass_limits=false` when `row_count > maximum_rows`, without truncation (`src/buoy_search/evidence_remote.py:410-459`, `src/buoy_search/evidence_snapshot.py:382-406`). The recorded active count alone also exceeds the cap, so total-versus-active interpretation cannot change this blocker. Focused no-write/over-limit tests passed.
- **Artifact and privacy screening:** commit `bda745e1` changes only one evidence record, one ticket, one Python source file, and one Python test file. No model/runtime weight, database, raw log, private review bundle, generated artifact, credential, private path, source/semantic content blob, stable namespace fingerprint, or private namespace ID was found among the changed paths or elsewhere in the committed tree.

## Commands

- `uv run python -m unittest tests.test_semantics_local_model` — prior review pass; 25 tests.
- `uv run python -m unittest tests.test_evidence_remote.EvidenceRemoteTests.test_estimate_is_exactly_no_write_and_creates_no_artifact tests.test_evidence_remote.EvidenceRemoteTests.test_sharded_and_limits_fail_before_branch_creation` — prior review pass; 2 tests.
- `git diff a91e09222e904c02bf03dfada351d79676e5fc73..bda745e1dbe8ca258a808e94df59db3d9d3b97b7 --check` — pass.
- Amended commit path/type and committed-tree prohibited-artifact/privacy screening — pass.

## Verdict

**Pass.** The historical significant privacy concern is resolved by the amended evidence, and no blocker or significant finding remains. Both source repairs remain minimal and correct against the active local-inference contract, with focused regression coverage. The 1,000-row gate correctly failed closed and justifies the ticket's blocked state without blocking acceptance of this bounded commit.

## Residual risk

No live provider or model call was made during this review, as required; live compatibility remains supported only by the sanitized attestation. The strict row blocker prevented evidence-bearing semantic estimate/build/verify and quality audit, so the commit establishes transport compatibility but not semantic quality or end-to-end Phase 3B acceptance.
