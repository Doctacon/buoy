Status: done
Created: 2026-08-28
Updated: 2026-08-29
Parent: .10x/tickets/done/2026-08-28-retrieval-telemetry-v3-plan.md
Depends-On: .10x/tickets/done/2026-08-28-implement-local-telemetry-v3-store-and-migration.md

# Validate Retrieval Telemetry V3 Integration

## Scope

Integrate and independently validate the completed v3 observation, provider accounting, queue/writer/store, migration, documentation, packaging, and installed-wheel behavior without changing retrieval results.

## Acceptance criteria

- All child acceptance criteria map to raw reproducible evidence.
- Full test suites pass on Python 3.11 and 3.13.
- Source/wheel/sdist build and isolated installed-wheel telemetry lifecycle pass.
- Controlled provider-free commands prove worker spawned/reused, in-process opt-out/compatibility, worker fallback, preview, command failure, provider complete/unavailable, and exact view rows.
- Disabled commands create no telemetry artifact/process/output/context effect.
- Output/route/ranking/evidence/provider-call fixtures are byte/value equivalent to pre-v3 behavior.
- Synthetic v2 migration preserves every old row/view and exact backups without touching the real store.
- Documentation accurately labels caller-observed inference duration and `provider_client_invocation`, never wire/cost semantics.
- Independent review reports pass or all findings are repaired and revalidated.
- A separate preflight fixes the exact live cases, expected call families, credential source, no-write controls, telemetry scratch home, model-cache controls, cleanup, and a lower call budget before any Turbopuffer call.
- Live execution, if still necessary after provider-free PASS, performs at most the frozen lower budget, never exceeds the owner's cumulative 20-call ceiling, never writes provider state, never retries an executed case, and records sanitized telemetry/equality evidence only.

## Evidence expectations

Record dual-runtime commands/results, package identities, installed lifecycle, privacy scans, schema/view results, diff summary, review, residual risks, and—if run—exact live call accounting and cleanup. No query/content/provider identity or credential may enter durable records.

## Explicit exclusions

Unbounded benchmarking, real-store migration, provider writes, query/corpus fingerprints, automatic telemetry enablement, release/publication, retention/purge, dashboard/UI, and unrelated changes.

## References

- `.10x/tickets/done/2026-08-28-retrieval-telemetry-v3-plan.md`
- `.10x/evidence/2026-08-28-retrieval-telemetry-v3-authorization.md`
- `.10x/specs/retrieve-inference-telemetry-v3.md`
- `.10x/specs/retrieve-provider-invocation-telemetry-v3.md`
- `.10x/specs/local-telemetry-v3-storage-and-migration.md`

## Progress and notes

- 2026-08-28: Opened after ratification. Live authorization ceiling is 20 bounded Turbopuffer calls; this ticket must freeze a smaller necessary budget before execution.
- 2026-08-29: Activated for provider-free aggregate integration validation after all three implementation dependencies closed with recorded evidence and independent pass reviews. Provider/credential/network access and the real telemetry store remain prohibited in this phase.
- 2026-08-29: Dual-runtime full suites passed under short private temporary homes and offline controls: Python 3.13 and isolated Python 3.11 each `1326 passed, 1408 subtests passed`, with only 57 pre-existing lxml warnings. An initial Python 3.13 harness used an overlong HOME and truthfully failed 32 established Unix-socket-length tests before worker startup; it was removed and rerun once with the required short path.
- 2026-08-29: Focused aggregate inference/provider/store/command validation passed `85 passed, 115 subtests passed`. Exact view scenarios cover worker spawn/reuse, fallback, in-process, preview, failures, provider complete/unavailable, catalog/content, and automatic combined shapes. Existing full-suite equivalence fixtures preserved output, route/error ordering, ranking/evidence results, provider calls, observer-fault behavior, and v1/v2 contracts.
- 2026-08-29: Offline sdist/wheel build passed. The offline-installed Python 3.11 wheel ran one public explicit preview in a temporary HOME, flushed one v3 observation, and exposed truthful schema-3 command/provider/null-pipeline/zero-inference rows; status was healthy with empty queue, one receipt, complete accounting, and no writer survivor. Package hashes and lifecycle facts are recorded in `.10x/evidence/2026-08-29-retrieval-telemetry-v3-provider-free-integration.md`.
- 2026-08-29: Static/contract validation passed: compileall, `git diff --check`, ranking contract, explicit local unchanged-default promotion validation, and C6 forecast. The first promotion command omitted its mandatory local base and exited with a harness-configuration error; the corrected explicit `HEAD`/`exact` command passed.
- 2026-08-29: Tightened `docs/telemetry.md` to label inference duration as caller-observed IPC/startup-inclusive backend wait rather than worker CPU time, prohibit nested-duration addition, and show safe v3 inference/provider queries with exact non-wire/non-billing unit language.
- 2026-08-29: Provider-free integration is sufficient for implementation acceptance. Supervisor declined to interpret the owner's ambiguous “20 bounded calls” on this child's behalf. Candidate evidence records two exact optional live alternatives; no provider call ran.
- 2026-08-29: Applied all parent-accepted aggregate-review repairs. Valid migration database/backup candidates no longer inherit the 16 MiB initialization cap; exact source/schema/history validation remains authoritative and hostile WALs retain the bounded fail-closed cap. Replaced the rejection fixture with valid >16 MiB prepublication and backup-published crash/retry cases.
- 2026-08-29: Renamed the misleading internal successful-migration `paths_v2`/final-v2 seam to version-neutral next-version terminology without changing the fixed public output schema. Documentation now states that compatibility key `pending_v2` reports v3 queue work after v2→v3.
- 2026-08-29: Updated current v3 command/stage/inference/provider SQL examples, labeled retained v1 views historical/direct-library, updated CHANGELOG, and repaired stale producer/store docstrings.
- 2026-08-29: Final exact validation passed: focused migration/CLI `104 passed, 209 subtests passed`; full Python 3.13 and isolated Python 3.11 each `1327 passed, 1408 subtests passed`; compileall, diff check, ranking validators, and C6 passed. Rebuilt artifacts and reran the offline installed-wheel lifecycle with exact commands/identities/hashes recorded in candidate evidence. Temporary distribution/install/home roots were deleted and proved absent.
- 2026-08-29: Applied the final accepted evidence/documentation repairs. Added and literally reran the hashed executable installed-wheel lifecycle script at `.10x/evidence/scripts/2026-08-29-retrieval-telemetry-v3-installed-wheel-lifecycle.sh`; it creates private generated inputs, asserts offline/privacy controls and exact artifacts, exercises preview/flush/status/help, validates privacy-safe exact v3 rows, proves zero process survivors, and performs literal dist/HOME/venv/run absence checks. Corrected repeat schema-3 migration documentation to bounded reconciliation/state refresh/recognized scratch cleanup rather than a read-only no-op, and made the remaining producer pipeline and `StoreReconcileResult` docstrings v2/v3-correct. Final focused telemetry validation passed `57 passed, 58 subtests passed`; lifecycle script syntax/mode/hash, documentation truth assertions, compileall, diff check, no-staging, and no-process-survivor checks passed.
- 2026-08-29: Applied the accepted P1 replay-independence repair to the evidence script only. It now asserts exact `uv.lock` identity, uv 0.11.7, distribution-specific `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BUOY_SEARCH`, and fixed `SOURCE_DATE_EPOCH=1787961600`; exports and hash-asserts the frozen 108-distribution runtime set from the lock; syncs it with required hashes; installs the exact local wheel with `--no-index --no-deps`; and asserts the literal installed identity object. Two fixed-control builds produced byte-identical wheels and sdists with the same hashes. The final literal lifecycle rerun passed all prior v3/privacy/process/deletion checks.
- 2026-08-29: Final fresh-context review mapped every integration criterion to evidence and found no P0/P1/P2 issue. Parent literally reran the retained lifecycle script; deterministic hashes, exact installed identity, schema-v3 rows/status, zero survivors, cleanup, and absence checks matched. Review: `.10x/reviews/2026-08-29-retrieval-telemetry-v3-integration-review.md`.
- 2026-08-29: Closure reconciliation accepted provider-free evidence as sufficient. Zero optional live calls ran because no implementation claim required them and the ceiling unit remained ambiguous; `.10x/evidence/2026-08-28-retrieval-telemetry-v3-authorization.md` records the no-action rationale. Retrospective extracted `.10x/knowledge/reproducible-installed-wheel-evidence-binds-version-lock-and-cleanup.md`.

## Blockers

None.
