Status: done
Created: 2026-08-28
Updated: 2026-08-29
Parent: None
Depends-On: None

# Retrieval Telemetry V3 Plan

## Outcome

Deliver opt-in, strict-private observation/store schema v3 that attributes command-scoped inference worker/in-process operations and persists validated content-free provider SDK call-attempt accounting while preserving retrieval semantics and immutable v1/v2 history.

This is a parent plan, not an executable ticket.

## Governing records

- `.10x/decisions/buoy-records-worker-and-provider-attempt-retrieval-telemetry-v3.md`
- `.10x/specs/retrieve-inference-telemetry-v3.md`
- `.10x/specs/retrieve-provider-invocation-telemetry-v3.md`
- `.10x/specs/local-telemetry-v3-storage-and-migration.md`
- `.10x/specs/provider-client-invocation-accounting.md`
- `.10x/specs/provider-client-invocation-receipt.md`
- `.10x/evidence/2026-08-28-retrieval-telemetry-v3-authorization.md`

## Child sequence

1. `.10x/tickets/done/2026-08-28-implement-retrieve-inference-observation-v3.md`
2. `.10x/tickets/done/2026-08-28-integrate-provider-accounting-into-telemetry-v3.md`
3. `.10x/tickets/done/2026-08-28-implement-local-telemetry-v3-store-and-migration.md`
4. `.10x/tickets/done/2026-08-28-validate-retrieval-telemetry-v3-integration.md`

Children are sequential because each extends the same exact envelope/store contract. One writer subagent at a time owns the shared working tree.

## Aggregate acceptance criteria

- New retrieve command observations are schema v3; direct-library v1 behavior and persisted v1/v2 semantics remain exact.
- Inference requests identify only governed operation/backend/role/count/lifecycle/outcome/error dimensions and correctly represent worker spawn/reuse/fallback.
- Validated content/catalog `provider_client_invocation` fields persist without claiming wire requests.
- Strict prohibited-data sentinels are absent from every v3 artifact and output.
- Disabled telemetry remains zero-side-effect; enabled telemetry remains local-only and failure-isolated.
- Fresh stores initialize at schema v3; explicit v2-to-v3 migration preserves old rows/views and retains an exact v2 backup.
- Python 3.11 and 3.13 full suites, packaging, isolated-wheel lifecycle, schema/privacy validators, and independent review pass.
- Live validation, if needed, runs only after provider-free PASS, performs provider reads only, uses a separately frozen lower budget within the authorized 20-call ceiling, and records exact reached calls without retries beyond that frozen case.

## Explicit exclusions

Provider writes, default-on telemetry, query/corpus/result fingerprints, worker-side persistence, SDK transport interception, changed retrieval/ranking/routing/evidence/output, retention/purge, dashboard/UI, release, publication, and unrelated cleanup.

## Progress and notes

- 2026-08-28: Owner ratified worker plus SDK v3, strict privacy, opt-in enablement, and a 20-call live-validation ceiling.
- 2026-08-28: Focused decision/specification set created. No implementation began in the specification/ticket-authoring turn.
- 2026-08-28: Inference observation child closed after two independent-review repair rounds, dual-runtime full/focused tests, parent-observed acceptance validation, and retrospective extraction. Production v3 activation remains correctly deferred to the queue/store integration child.
- 2026-08-28: Provider-accounting child closed after repairing command/route/catalog graph reconciliation and callback-driven privacy evidence. Dual-runtime full/focused tests, parent-observed validation, and independent review passed without provider calls. Persistence-ready provider fields remain dormant until the store child.
- 2026-08-29: Store/migration child closed after two review-repair rounds covering backup retry ordering, history subsets, receipt accounting, bounded hostile data, WAL safety, v3 privacy/no-network, exact view scenarios, production timing, and terminal drain. Production now activates v3 through the distinct v3 inbox/writer/store path; dual-runtime, package, installed-wheel, parent validation, and independent review passed.
- 2026-08-29: Aggregate integration child closed after repairing valid >16 MiB migration recovery, current documentation, exact raw evidence, and deterministic installed-wheel replay. Full Python 3.11/3.13 suites passed (`1327 passed, 1408 subtests passed` each); provider-free focused tests, ranking validators, C6, build, and literal installed lifecycle passed. Final review found no P0/P1/P2 issue.
- 2026-08-29: Parent closure reconciliation confirmed every child is done, all active specs match implementation, evidence/review paths are coherent, no live provider call or real-store migration was required, and the working tree remains unstaged. Retrospective lessons were preserved in three focused knowledge records: atomic version activation, terminally drained migration snapshots, and reproducible installed-wheel evidence.

## Blockers

None. Provider-free evidence satisfied implementation acceptance. The optional live ceiling unit was never interpreted or consumed; any future live campaign requires its own exact case/unit decision.
