Status: open
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
- 2026-07-29: Follow-up repair normalizes SDK timestamps, binds deterministic source identity to snapshot ID, recomputes source fingerprints remotely, byte-bounds writes, removes the global ID set, repeats branch metadata checks after ledger verification, conservatively reports rather than deletes incomplete deterministic resources, hides internal rows across Command Center paths, makes reuse metrics factual, and adds focused regressions. Independent re-review and parent closure remain pending.
