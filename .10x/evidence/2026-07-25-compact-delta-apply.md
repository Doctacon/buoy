Status: recorded
Created: 2026-07-25
Updated: 2026-07-25
Relates-To: .10x/tickets/done/2026-07-24-implement-compact-delta-apply.md, .10x/reviews/2026-07-25-compact-delta-apply.md, .10x/specs/compact-delta-plan-artifacts.md

# Compact Delta Apply Evidence

## What was observed

Apply now accepts only fully verified schema-v2 `plan.json` plus `delta.duckdb`. Explicit schema 1 is rejected after reading only its bounded `plan.json`; implicit selection skips schema-1, malformed, oversized, missing-delta, and unsafe candidates without opening legacy payloads. Preflight loads the compact delta, reloads applied state, binds database presence plus the canonical row/metadata projection, and fails with replan guidance on any drift before credentials, models, providers, pending state, or writes.

Approved apply reacquires the namespace lock and repeats full artifact and baseline verification under lock. It embeds/upserts only verified changed/new/reactivated rows, applies current retain/delete behavior only to verified stale identities, and constructs next state by combining untouched baseline rows with delta operations. No manifest, chunks JSONL, source crawl/clone/document/database access, or source credentials are used.

Catalog semantics are projected solely from the verified plan-level source, including zero-upsert plans. Existing remote cards with lineage version 1 remain parseable/routable; compatibility accepts lineage 1 or the current version; new approved applies write lineage 2. Approved no-change apply retains current catalog, zero-row state/apply-run, lineage, and prospective cleanup behavior.

Schema-v2 prospective cleanup continues to call the full verifier. The stale-row verifier was narrowed to accept nonempty historical applied `prior_plan_id` values rather than requiring schema-v2 plan-ID syntax, because existing compact applied state is intentionally retained across the local artifact hard cutover.

## Tests and procedures

- `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_apply_cli -q` — 53 tests passed after adding explicit schema-1 inertness, implicit supported-plan selection, absent-to-empty drift, under-lock drift ordering, and schema-v2 no-change lineage assertions.
- `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_apply_cli tests.test_catalog tests.test_catalog_cli tests.test_catalog_pending tests.test_remote_catalog tests.test_applied_state tests.test_plan_cleanup tests.test_compact_delta_planning tests.test_cli -q` — 225 tests passed in 16.306 seconds. Two existing cleanup-safety fixtures emitted expected warnings for refusing directories under the state root.
- `PYTHONDONTWRITEBYTECODE=1 uv run python -m py_compile src/buoy_search/apply.py src/buoy_search/catalog.py src/buoy_search/remote_catalog.py src/buoy_search/plan_artifacts.py` — passed.
- `git diff --check` — passed.

Side-effect tests prove explicit old-schema rejection leaves legacy manifest/chunks bytes unchanged; dry-run invokes no embedder/writer; absent-to-empty state creation is drift; a lock-time state mutation fails before catalog projection, remote client, embedder, writer, pending creation, or plan cleanup; failed content/delete work preserves prior state and plan; and successful/no-change paths preserve existing pending/catalog/cleanup semantics.

## Post-review hardening

Independent review found that database presence was sampled separately from state load, and verified plan directories could be replaced between verification and cleanup. State loading now opens the state parent and database with no-follow descriptors, copies the exact opened inode into a private temporary DuckDB snapshot, loads only that snapshot, and checks file identity/metadata plus parent directory identity/mtime/ctime and path-to-fd binding after the read. A swap-read-restore ABA injection under the namespace lock changed the parent identity and failed with replan guidance before catalog projection, remote client, embedder, writer, pending creation, or cleanup. Absent state retains deterministic first-apply behavior and detects persistent absent-to-present drift.

Applied and supersession cleanup now binds exact schema-v2 plan ID, artifact hash, namespace, validated creation time, and directory device/inode. Supersession removes only strictly older fully verified candidates; later and equal-time plans remain. Cleanup atomically renames a candidate through a held no-follow parent descriptor to an unpredictable quarantine name, reverifies the exact payload/identity after rename, and uses fd-relative symlink-safe removal. Same-namespace races to newer content are restored/retained rather than deleted; schema-1, corrupt, unexpected-entry, state-root, and symlink candidates remain untouched.

Final cleanup hardening captures a typed `ApplyCleanupBinding` from the exact full verification performed while the namespace lock is held. The binding carries plan path/ID/hash/namespace plus the verified directory device/inode through an internal callback; it is never added to the public apply summary or JSON/text output. CLI cleanup requires every binding field. A deterministic A→B→A test uses logically identical artifacts with equal plan IDs and artifact hashes but distinct directory inodes: apply authorizes B under lock, the lock restores A, cleanup observes A's different inode, retains both directories, and emits a warning.

Delta action verification now requires exact baseline lineage for `new`, `changed`, and `reactivate_retained_stale`; `changed` rejects an unchanged same-row hash and accepts only a changed active row or an absent row with active canonical-URL lineage. Approved reactivation transitions the retained row to active and records an apply summary. The approved no-change regression inspects the second apply-run summary and proves zero upserts/deletes.

- `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_plan_cleanup tests.test_apply_cli -q` — 65 tests passed.
- Expanded apply/catalog/pending/remote/state/cleanup/planning/CLI basket — 232 tests passed in 18.026 seconds; two existing state-root safety fixtures emitted expected warnings.
- Updated apply/cleanup/CLI modules compiled; `git diff --check` passed.
- Post-rereview `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_plan_cleanup tests.test_apply_cli -q` — 67 tests passed.
- Post-rereview expanded apply/catalog/pending/remote/state/cleanup/planning/CLI basket — 234 tests passed in 19.307 seconds; two expected state-root cleanup warnings were emitted.
- Post-rereview apply/CLI/cleanup compilation and `git diff --check` — passed.
- Final exact-cleanup `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_plan_cleanup tests.test_apply_cli -q` — 67 tests passed.
- Final exact-cleanup expanded apply/catalog/catalog-CLI/pending/remote/state/cleanup/planning/CLI basket — 234 tests passed in 18.574 seconds; two expected state-root cleanup warnings were emitted.
- Final `python -m compileall -q src/buoy_search tests` and `git diff --check` — passed.

## Limits

This is focused local validation. No real source reacquisition, model inference, turbopuffer credential/call/write, remote catalog mutation, approved real apply, user artifact deletion, push, PR, merge, publish, or release occurred. Full repository and Command Center matrices remain owned by the dependent integration ticket. Independent review is still required before this child closes.
