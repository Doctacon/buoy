Status: recorded
Created: 2026-07-30
Updated: 2026-07-30
Relates-To: .10x/tickets/2026-07-30-autonomous-local-semantics-live-acceptance.md, .10x/specs/local-semantic-inference.md, .10x/specs/autonomous-semantic-builds.md, .10x/specs/semantic-build-operations.md, .10x/specs/remote-evidence-snapshots.md

# Autonomous Local Semantics Live Acceptance

## What was observed

The live acceptance ran from Buoy commit `4ec8186ef3245abbc56072c343f5d6c0140b8712` on `work/autonomous-local-semantics-live-acceptance`. The foundation branch was backed up on origin and the acceptance branch remained unmerged.

Hardware was macOS 26.5.1 on arm64 Apple M2 Pro with 16 GiB physical memory. Buoy used Python 3.13.0. Ollama 0.11.10 was already installed and bound to loopback. The authorized model remained `qwen2.5:3b-instruct-q4_K_M`, GGUF 3.1B Q4_K_M, 1,929,912,432 bytes, with immutable runtime revision `sha256:357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b` and configured context 4,096. No model was downloaded or switched during the continuation.

Before evidence-bearing work, hosted-provider and proxy variables were removed from the command environment. The earlier completed doctor remained the model/runtime gate: it passed strict structured output, seed support, runtime digest verification, and loopback transport with 3.043808 seconds local-call latency and zero evidence, turbopuffer, or hosted activity.

## Previously repaired implementation defects

The branch retains two narrow repairs with deterministic regressions:

1. Completed declared-Content-Length responses are recognized before another socket timeout update, preventing a closed-socket `EBADF` from being misclassified as transport failure.
2. Exact lowercase raw Ollama SHA-256 digests are canonicalized to `sha256:<hex>` before pin comparison while malformed or conflicting values continue to fail closed.

Both repairs were already validated in the prior acceptance phase. They were not changed during this continuation.

## Revised authorization and evidence attempt

The same previously selected non-internal applied namespace was used; no alternate namespace was selected. Its applied-state ledger contains 3,301 active and 84 retained-stale rows, 3,385 total. Previously observed approximate source logical size was 7,920,763 bytes. The user explicitly raised the one-snapshot bounds to 5,000 rows and 104,857,600 approximate logical bytes, so the exact rows and approximate bytes passed the revised pre-write gate.

Exactly one snapshot command was attempted with those explicit bounds. It created one point-in-time evidence branch and made the first bounded 1,000-row ledger write. Turbopuffer reported the expected 1,000 affected rows, but Buoy's additional ownership proof rejected the successful response because its returned affected-ID representation did not exactly equal the expected ordered list. The command failed closed before any further ledger batch, full reconciliation, catalog completion, or local manifest write.

A strong read after failure found exactly 1,000 rows in the incomplete ledger. Remote metadata showed the branch retained approximately 3,385 source rows. The two incomplete internal namespaces together reported approximately 4,385 rows and 8,443,697 logical bytes. There is no completed evidence-catalog row and no valid evidence snapshot. No `snapshot.json` exists; local evidence-manifest bytes are zero. Source namespace writes were zero. Evidence-branch writes after branch creation were zero. One branch was created, no branch was reused, one ledger batch containing 1,000 rows was written, and zero catalog rows were written.

Classification: the affected-ID ownership mismatch is an **implementation defect** in the real SDK boundary. The remote 1,000-row partial ledger is also a **contract recovery limitation**: the active specification requires partial ledgers to fail without overwrite or deletion, while this run explicitly prohibits deletion/garbage collection and evidence-branch writes after creation. A new exact-prefix recovery semantic would change the ratified contract and was not inferred or implemented. The separately authorized exact resume therefore cannot proceed safely from this incomplete deterministic identity.

## Semantic workflow result

Semantic estimate, semantic build, semantic verification, semantic inspection, the private review bundle, and the local-model quality audit were not run because no completed evidence snapshot exists. No semantic build identity or internal semantic namespace was created. Model calls on source evidence were zero, extraction retries were zero, semantic wall time and quality counts are unavailable, local semantic-manifest bytes are zero, and semantic internal rows/bytes are zero.

The Phase 3B pipeline and semantic quality of the current local model therefore remain unevaluated. No conclusion that the model is suitable or unsuitable can be supported from this blocked run.

## Side-effect and privacy accounting

- Source namespace writes: zero.
- Evidence branches created/reused: one/zero.
- Evidence-branch writes after creation: zero.
- Evidence ledger write calls/rows: one/1,000.
- Evidence catalog rows written: zero.
- Valid evidence snapshot: none.
- Local evidence corpus or manifest: none; zero bytes.
- Semantic namespaces, rows, bytes, model calls, or manifests: zero.
- Hosted inference, hosted embeddings, and hosted cost: zero.
- Apply, source mutation, deletion, garbage collection, graph visualization, ontology assertions, merge, pull request, publish, and release: none.
- Private namespace IDs, source content, semantic labels, excerpts, prompts, responses, credentials, and raw provider output are absent from this record and the commit.

## Validation

No source or test file changed during the continuation, so the prior full source-change validation remains authoritative for the two committed repairs: 83 focused semantic tests passed; ranking and C6 validators passed; full discovery passed 937 tests with 39 skipped; wheel/sdist construction passed with 77/179 entries; lock and diff checks passed.

Continuation-specific validation passed 37 focused evidence snapshot/CLI tests in 13.482 seconds, `git diff --check`, `uv lock --check`, changed-record privacy screening, and local-artifact absence checks after recording the blocker. No full suite or package build was required because this continuation changed records only.

## What this supports and limits

This supports the revised evidence limits passing for the same selected namespace, one correctly bounded live branch/ledger attempt, fail-closed catalog-last behavior, zero source/evidence-branch mutation, and discovery of a deterministic real-SDK ownership-proof defect. It does not support a valid evidence snapshot, complete evidence verification, semantic estimate/build/verification, private quality review, throughput metrics, or local-model quality conclusions.

Recommendation: **implementation defect blocks review**. Completion requires a separately ratified and tested recovery contract for this exact incomplete deterministic ledger, or separately authorized deletion followed by a clean retry. Neither action was authorized in this run.
