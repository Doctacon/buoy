Status: done
Created: 2026-07-29
Updated: 2026-07-29
Parent: None
Depends-On: None

# Implement Remote Evidence Snapshot Foundation

## Scope

Implement the complete bounded Phase 3A contract in `.10x/specs/remote-evidence-snapshots.md` on `work/remote-evidence-snapshot-foundation`, based on `606c168389e28b09105e8eb139f2cde063994a83` (latest fetched `origin/main`). Use the exact provider findings in `.10x/research/2026-07-29-turbopuffer-evidence-snapshot-api.md`.

Deliver focused remote/core/CLI modules following current architecture, a safe applied-state streaming API, internal namespace filtering in routing/discovery/Command Center, comprehensive provider-free tests including the 100,000-row structural fixture, concise README and command-center/indexing/new evidence-snapshot documentation, packaging coverage, evidence and independent review records, and one final bounded commit.

## Explicit exclusions

No local full corpus, `evidence.duckdb`, content JSONL/Markdown/cache, graph extraction, LLM/model/source-adapter calls, concept/mention/assertion/edge/graph/UI work, Command Center creation UI, schedules, retention/deletion/GC commands, sharded copy fallback, cross-region copy, automatic source selection, source namespace mutation, plan/apply changes, live smoke, push, PR, merge, publish, release, or packaged-asset hash rebuild when frontend source is unchanged.

## Acceptance criteria

1. `buoy evidence estimate`, `snapshot`, and `verify` implement the exact specification with existing text/JSON conventions and lazy provider imports.
2. Snapshot content remains solely in turbopuffer branches; the remote ledger is content/vector-free; the only local snapshot artifact is bounded `snapshot.json`.
3. Eligibility, sorted multi-locking, deterministic identity/names, sharded rejection, budgets, complete reconciliation, branch metadata drift detection, ledger verification, catalog-last finalization/reuse, safe cleanup, and remote-only verification are tested.
4. Internal evidence namespaces cannot enter routing or ordinary source namespace presentation.
5. Tests include requested failure matrices, 10,001-row pagination, 100,000-row bounded scale measurements, provider inertness, and package authority checks without network/credentials.
6. README, `docs/indexing.md`, `docs/command-center.md`, and `docs/evidence-snapshots.md` accurately state storage, billing, immutability, estimate-first, reuse, explicit/manual lifecycle, and roadmap limits.
7. Run and record exact results for `git diff --check`, `uv sync --locked`, `uv lock --check`, ranking contract validation, C6 syntax forecast validation, full unittest discovery, focused evidence/regression tests, frontend validation only if required, `uv build`, package-content/import/help checks, cleanup of dist/node_modules, and final environment restoration.
8. `.10x/evidence/2026-07-29-remote-evidence-snapshot-foundation.md` and an independent `.10x/reviews/...` record map claims to observed evidence and residual limits.
9. Commit the bounded implementation; do not push or integrate.

## Evidence expectations

Record base/final commit, branch, SDK/API, namespace/schema contracts, limits, exact validation outputs, 100,000-row peak RSS/local bytes/provider fake call counts/timing, remote logical-byte fixture estimate, cleanup behavior, package inspection, no-live-smoke status, and confirmation of prohibited side effects.

## Blockers

None. Product semantics and acceptance criteria are explicitly ratified by the user request and captured in the active governing specification.

## Progress and notes

- 2026-07-29: Created clean worktree from fetched `origin/main` commit `606c168389e28b09105e8eb139f2cde063994a83`.
- 2026-07-29: Verified official documentation and installed SDK 2.4.0; recorded exact API findings.
- 2026-07-29: Ticket assigned to a single implementation subagent; parent retains orchestration, evidence verification, and closure authority.
- 2026-07-29: Implemented provider-inert local identity/streaming contracts, remote estimate/create/verify orchestration, exact ledger/catalog schemas, deterministic branches, catalog-last finalization/reuse, guarded cleanup, CLI wiring, and internal namespace filtering.
- 2026-07-29: Added provider-free selection/identity/lock/branch/ledger/reconciliation/atomicity/verification/import/package tests, including 100,000-row full fake snapshot, 100,000-row local stream, 10,001-row paging, and bounded ledger batches.
- 2026-07-29: Documented the operator workflow, billing/immutability limits, CLI-only Command Center boundary, and Phase 3A/3B/3C/4 roadmap. A zero-row state is rejected before remote creation because the provider cannot create an absent schema-only ledger without a contract-breaking sentinel.
- 2026-07-29: Final validation passed: focused 182 tests; full 839 tests with 39 skips; ranking and C6 validators; locked sync/lock check; wheel/sdist build and content inspection; provider-inert imports/help; diff checks and environment restoration. Frontend was unchanged and intentionally not rebuilt. Live smoke was not run.
- 2026-07-29: Recorded reproducible evidence at `.10x/evidence/2026-07-29-remote-evidence-snapshot-foundation.md` and initial review at `.10x/reviews/2026-07-29-remote-evidence-snapshot-foundation-review.md`. Ticket remains open for parent acceptance/closure as assigned.
- 2026-07-29: Two independent reviews failed commit `cf37f5f`, identifying SDK datetime serialization, unsafe cleanup ownership, unauthenticated catalog/source metadata, byte-unbounded ledger batches, O(total rows) hash state, finalization ordering, Command Center visibility, reuse activity/metric, supplied-manifest, and CLI/package evidence gaps.
- 2026-07-29: Follow-up repair normalizes SDK timestamps, binds deterministic source identity to snapshot ID, recomputes source fingerprints remotely, byte-bounds writes, removes the global ID set, repeats branch metadata checks after ledger verification, conservatively reports rather than deletes incomplete deterministic resources, hides internal rows across Command Center paths, makes reuse metrics factual, and adds focused regressions.
- 2026-07-29: Fresh correctness re-review passed those repairs but failed SDK `updated_at` write-marker handling and identical post-catalog-failure ledger recovery. A second repair canonicalizes `last_write_at`/`updated_at` with fail-closed absence and reuses only exact fully reconciled deterministic ledgers; partial/mismatched ledgers remain collisions.
- 2026-07-29: Second-repair validation passed: 241 focused tests, 852 full-suite tests with 39 skips, ranking/C6 validators, locked sync/lock check, wheel/sdist content inspection, provider-inert imports/help, restoration, and diff checks. A first focused invocation used nonexistent suggested module `tests.test_apply`; corrected repository module `tests.test_apply_cli` passed.
- 2026-07-29: Final independent correctness review found that the normal and retry paths could hash/count a ledger mutation after their last exact source validation and still publish complete. Final repair now repeats exact ledger-to-locked-local fingerprints/counts/identity plus branch reconciliation immediately before catalog completion, followed by the final branch metadata check. New hash/provenance mutation regressions fail before catalog publication. The redundant normal branch scan was removed, preserving one ordered branch reconciliation scan per source.
- 2026-07-29: Final repair validation passed: 250 focused tests, 854 full-suite tests with 39 skips, locked sync/lock check, ranking/C6 validators, provider-inert imports/help, wheel/sdist build and exact inventory, diff checks, and a 100,000-row measurement (202,145,792-byte RSS delta, 1,018 local bytes, 1 branch call, 33 fake remote query calls, 100 ledger writes, 9.165245s reconciliation). A nested package-build unit regression was intentionally not added because it would write repository artifacts and slow normal discovery; the independent provider-free build inventory remains the non-blocking package check.
- 2026-07-29: Fresh independent acceptance review of final implementation commit `d517e860ec2af791f647eca7c80fb2f13b1d9805` passed with no blocker or significant finding. Parent-observed closure validation passed `git diff --check`, locked sync/lock checks, both repository validators, 195 focused tests, 854 full-suite tests with 39 skips, wheel/sdist build and 72/168-entry inventory, provider-inert imports/help, cleanup/restoration, and final diff/status checks.
- 2026-07-29: Acceptance criteria map to `.10x/evidence/2026-07-29-remote-evidence-snapshot-foundation.md`; independent findings and repair history map to `.10x/reviews/2026-07-29-remote-evidence-snapshot-foundation-review.md`. No unresolved blocker remains. Ticket closed after retrospective extraction; residual limits are documented in evidence/review and require no Phase 3A follow-up ticket because they are explicit non-goals or provider/live-smoke boundaries.
