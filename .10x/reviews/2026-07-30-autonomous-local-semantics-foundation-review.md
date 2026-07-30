Status: recorded
Created: 2026-07-30
Updated: 2026-07-30
Target: Complete Phase 3B worktree diff from base `27cdcc7a5cecf527ce558f898d6ad39fa204a5bd`, including current uncommitted source, tests, specifications, tickets, evidence, package metadata, and documentation
Verdict: pass

# Autonomous Local Semantics Foundation Final Acceptance Review

## Findings

### Significant — completed-build reuse does not authenticate the catalog contract

`create_semantic_build()` derives the requested identity and looks up that build ID, but its completed-build branch calls only `_verify_completed_catalog()` before regenerating the local manifest (`src/buoy_search/semantics_remote.py:883-895`). `_verify_completed_catalog()` checks final row hashes, three final counts, and the logical hash, but does not call `_completed_contract()` or compare the catalog snapshot/model/pipeline/threshold/limit/namespace identity to the requested build (`src/buoy_search/semantics_remote.py:715-739`; the missing full contract validation exists separately at `src/buoy_search/semantics_remote.py:1294-1358`). It also does not run the row build/snapshot/status/basis/reference checks used by `verify_semantic_build()`.

A provider-free reproduction built `evidence_test`, changed the completed catalog row's `evidence_snapshot_id` to `evidence_different`, coherently recomputed only its manifest hash, and invoked the identical build again. The command returned `reused_build=True` and overwrote local `build.json` with `evidence_snapshot_id=evidence_different`. This violates immutable completed-build reuse, build/snapshot authentication, and catalog/manifest contracts.

### Significant — build can publish a completed taxonomy with dangling evidence-basis references

The production taxonomy proposer receives concept summaries but no valid mention-ID set (`src/buoy_search/semantics_pipeline.py:214-248`). `build_taxonomy()` bounds `representative_mention_ids` only by length and never validates that the IDs exist or support either endpoint (`src/buoy_search/semantics_pipeline.py:757-790`). The unvalidated IDs and model-selected `basis` are then persisted and catalog completion proceeds (`src/buoy_search/semantics_remote.py:1085-1099`, `src/buoy_search/semantics_remote.py:1220-1255`). The reference check exists only after publication in the separate verification command (`src/buoy_search/semantics_remote.py:1500-1502`).

A provider-free reproduction injected an otherwise accepted `evidence_supported` proposal whose representative list was `['mention_does_not_exist']`. `create_semantic_build()` nevertheless wrote `state=complete` to the catalog with that dangling reference. A completed build therefore need not satisfy the verification contract at publication time.

### Significant — estimate limit truth excludes the mandatory model-contract probe

The CLI performs `doctor()` before estimate and reports that probe separately (`src/buoy_search/semantics_cli.py:196-209`), while `estimate_semantic_build()` computes model-call limits from its pipeline estimate alone (`src/buoy_search/semantics_remote.py:1643-1646`, `src/buoy_search/semantics_remote.py:1659-1670`). Unlike build, estimate has no initial-call accounting input. Consequently its aggregate pass/fail answer is false at the boundary.

A provider-free CLI reproduction used one active row, zero extracted candidates, and `--maximum-model-calls 1`. It made two local-model calls (one mandatory contract probe and one sampled extraction) but returned exit code 0, `estimated_model_calls=1`, `model_limit_passes=true`, and `would_pass_limits=true`, while separately admitting `contract_probe_model_calls=1`. This fails the estimate all-limit truth requirement.

### Minor — one child ticket has incoherent status and placement

`.10x/tickets/done/2026-07-29-implement-autonomous-semantic-pipeline.md:1` says `Status: active` while residing under `tickets/done/`; its progress also says it remains active. This does not cause the product failures above, but the ticket graph is not closure-coherent.

## Correct behavior rechecked

- Focused semantic/evidence/catalog/namespace/Command Center tests passed: 232 tests.
- The final runtime contract re-probe is reserved against the hard call budget and occurs before evidence/final scans and catalog completion (`src/buoy_search/semantics_remote.py:1179-1183`, `src/buoy_search/semantics_remote.py:1220-1251`); drift prevents catalog completion.
- Focused tests cover incomplete namespace reporting, conditional/catalog-last writes, active evidence and chunk provenance, persisted-row/logical hashes, status/basis/cycle/count/manifest corruption, fresh versus reused activity, deterministic sampling/resume, endpoint privacy, no-provider help, and internal namespace filtering.
- The independent 500-row structural rerun matched the evidence arithmetic for 500 rows, 3,000 candidates, 2,900 concepts, 3,000 mentions, four taxonomy rows, 6,405 remote rows, 1,326 accounted calls, 19 writes, 7,449,020 canonical request bytes, 7,424,226 derived bytes, 32,600 evidence bytes, 10,867 approximate tokens, and a 7,638-byte manifest plus zero-byte lock. Its logical hash differed from the recorded observation because persisted rows contain the run timestamp; the count/byte arithmetic matched.
- Documentation describes zero/small retained lock state and the Phase 3A/3B/3C/4/5 roadmap consistently. Package build/inventory contained all five semantic modules and `docs/semantics.md`, with no model weights, semantic manifests, snapshots, DuckDB files, or `node_modules`.
- No source/evidence-branch write path, hosted inference adapter/fallback, vector request, or model download was found in the reviewed semantic implementation. Estimate/verify/inspect tests remained write-free, and help remained provider/connection inert.

## Commands

- `git status --short --branch && git worktree list` — pass; confirmed task worktree/branch and pre-existing Phase 3B diff.
- `git diff --stat`, `git diff --numstat`, targeted source/record reads, and `git diff --check` — pass; no whitespace errors.
- `PYTHONDONTWRITEBYTECODE=1 UV_CACHE_DIR=/tmp/buoy-review-uv-cache uv run --frozen python -B -m unittest tests.test_semantics_models tests.test_semantics_local_model tests.test_semantics_pipeline tests.test_semantics_remote tests.test_semantics_cli tests.test_evidence_snapshot tests.test_evidence_remote tests.test_evidence_cli tests.test_catalog tests.test_catalog_cli tests.test_catalog_pending tests.test_remote_catalog tests.test_namespaces tests.test_command_center_remote` — pass; 232 tests in 19.932s.
- Provider-free 500-row structural probe in `/tmp` — pass; reproduced the evidence counts and byte arithmetic listed above.
- Provider-free dangling taxonomy-reference probe in `/tmp` — reproduced significant finding; catalog completed with nonexistent representative mention ID.
- Provider-free one-row CLI estimate probe in `/tmp` — reproduced significant finding; two actual calls were reported as a passing one-call limit.
- Provider-free completed-reuse catalog mutation probe in `/tmp` — reproduced significant finding; mismatched snapshot catalog was reused and written to the local manifest.
- `uv build --out-dir /tmp/buoy-phase3b-review-dist` — pass; wheel and sdist built. The first compound inventory attempt used unavailable system `python` after the successful build; rerun with `uv run --frozen python -B` passed.
- Package inventory — pass; 77 wheel entries, 179 sdist entries, all five semantic modules in both, semantics documentation in sdist, and no prohibited artifact matches.
- Pre-review status comparison — pass; validation created no project-status changes.

## Verdict

Fail. The three significant findings permit reuse of a catalog that conflicts with the requested immutable build, publication of a completed taxonomy that fails its own reference contract, and a false passing estimate at the model-call limit. These are acceptance failures, not residual live-provider uncertainty.

## Residual risk

Live Ollama/llama.cpp and turbopuffer behavior remains unobserved by design; all review verification used deterministic provider-free fakes. Best-effort inference remains non-bit-identical across environments. The final commit/evidence commit hash is still pending. These residuals would not independently fail acceptance, but they do not mitigate the significant deterministic failures above.

## Repair disposition (pending independent re-review)

The three significant findings were addressed in the working diff on 2026-07-30 without changing this review's historical fail verdict:

1. Completed-build reuse now reconstructs and validates the completed catalog contract, derives its deterministic names/build ID, and requires its complete identity payload to equal the exact requested snapshot/coverage/sampling/model/embedding/pipeline/threshold/limit identity before any manifest is regenerated. A coherently rehashed conflicting snapshot regression now fails reuse.
2. Build publication now validates every proposed representative mention against current published mentions and requires its concept to be one of the relation endpoints. Verification independently enforces both existence and endpoint relevance. Provider-free build and corruption regressions cover unknown and unrelated IDs.
3. Estimate accepts explicit prior-model-call accounting; CLI passes the mandatory doctor probe as one prior call. Sample inference stops before exceeding the remaining hard limit, actual and estimated counts include the probe, and a one-call maximum now returns `would_pass_limits=false` after only the doctor call.

Focused semantic CLI/remote tests passed after repair. A fresh independent re-review is still required before the verdict can change.

## Independent final re-review

### Significant — completed reuse still does not validate the catalog's semantic schema identity field

The requested identity includes `semantic_schema_version` (`src/buoy_search/semantics_remote.py:271-287`), and fresh catalog publication stores that field (`src/buoy_search/semantics_remote.py:1216-1219`). However, `_completed_contract()` reconstructs the completed identity using the current hard-coded schema version without comparing `row["semantic_schema_version"]` to it (`src/buoy_search/semantics_remote.py:1319-1362`). The reuse branch then sees the reconstructed identity as equal and regenerates the local manifest from the mutated catalog row (`src/buoy_search/semantics_remote.py:885-905`).

A provider-free reproduction built a completed semantic build, changed only its catalog `semantic_schema_version` to `semantic-build-v999`, coherently recomputed `manifest_hash`, and requested the identical build again. Reuse returned `reused_build=true` and overwrote `build.json` with `semantic_schema_version=semantic-build-v999`. The snapshot-drift regression at `tests/test_semantics_remote.py:426-435` proves one identity component but does not cover this catalog field. Completed reuse therefore still does not authenticate the exact requested identity.

### Correct — taxonomy representative mentions now fail closed during build and verification

Before final namespace publication, build maps every representative mention to its current-build concept and rejects missing IDs or IDs unrelated to both relation endpoints (`src/buoy_search/semantics_remote.py:1094-1110`). Read-only verification independently enforces existence and endpoint relevance (`src/buoy_search/semantics_remote.py:1525-1535`). Focused regressions cover build-time unknown IDs and verification-time unknown/unrelated IDs (`tests/test_semantics_remote.py:437-470`, `tests/test_semantics_remote.py:918-945`).

### Correct — estimate now includes the mandatory doctor probe in model-call budget truth

The CLI passes the doctor call as `prior_model_calls=1` (`src/buoy_search/semantics_cli.py:196-209`). Estimate subtracts prior calls before each sample inference, includes the prior call in projected/actual accounting, and derives limit truth from that aggregate (`src/buoy_search/semantics_remote.py:1635-1746`). The one-call-boundary regression confirms no sample call occurs, estimated calls exceed the one-call maximum, and `would_pass_limits` is false (`tests/test_semantics_remote.py:755-780`); CLI propagation is covered at `tests/test_semantics_cli.py:123-152`.

### Validation and verdict

- `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_semantics_remote tests.test_semantics_cli -q` — pass; 37 tests in 1.376s.
- `git diff --check` — pass; no whitespace errors.
- Short blocker/significant scan of the final source, tests, specifications, documentation, and package diff — one significant identity-authentication defect above; no blocker found.
- Provider-free semantic-schema mutation/reuse probe — reproduced the significant finding (`reused_build=true`, regenerated manifest contained `semantic-build-v999`).

Verdict remains **fail**. Two of the three prior findings are resolved, but completed reuse still accepts a catalog whose declared semantic schema conflicts with the requested build identity.

### Residual risk after re-review

Live local-runtime and turbopuffer behavior remains unobserved; focused verification uses provider-free fakes. Best-effort inference remains environment-dependent. The previously recorded minor done-ticket status/placement incoherence remains. These are residual/minor concerns, but the deterministic semantic-schema reuse defect independently prevents a pass verdict.

## Final schema-version repair (pending independent re-review)

`_completed_contract()` now fails unless the catalog's declared `semantic_schema_version` exactly equals the current `SEMANTIC_SCHEMA_VERSION` used by the requested identity. A provider-free regression mutates only that catalog field, coherently recomputes the manifest hash, and proves completed reuse fails closed. This historical review header and verdict remain **fail** until an independent reviewer accepts the repair.

## Final concise re-review — pass

- **Correct:** Completed reuse invokes `_completed_contract()` before manifest regeneration (`src/buoy_search/semantics_remote.py:885-899`), and that contract now rejects any catalog `semantic_schema_version` unequal to `SEMANTIC_SCHEMA_VERSION` (`src/buoy_search/semantics_remote.py:1319-1321`).
- **Correct:** The regression mutates only the schema version, coherently recomputes the catalog manifest hash, and expects reuse to fail (`tests/test_semantics_remote.py:437-446`).
- **Validation:** Semantic remote+CLI suites passed: 38 tests. `git diff --check` passed. No blocker or significant finding remains from the prior review.
- **Note (minor/residual):** `.10x/tickets/done/2026-07-29-implement-autonomous-semantic-pipeline.md:1` still says `Status: active`; live runtime/provider behavior remains unobserved. Neither prevents this focused pass.

**Verdict: pass.**

## Parent closure reconciliation

The minor done-ticket status inconsistency noted during re-review was mechanically corrected before closure. No implementation finding changed; verdict remains **pass**.
