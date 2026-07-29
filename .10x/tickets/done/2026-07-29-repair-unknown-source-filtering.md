Status: done
Created: 2026-07-29
Updated: 2026-07-29
Parent: .10x/tickets/done/2026-07-29-command-center-bounded-review-hardening-plan.md
Depends-On: .10x/tickets/done/2026-07-29-guard-focused-plan-review-requests.md

# Repair Unknown-Source Filtering

## Scope

Implement `.10x/specs/command-center-unknown-source-filtering.md` in namespace service filtering and API/frontend regressions.

## Acceptance criteria

- An attributable malformed applied-state namespace remains `local_status=error`, `source=None`.
- `source_kind=unknown` and the combined `local_status=error&source_kind=unknown` return it.
- Website, GitHub, document, and database filters exclude it.
- Frontend issues the unknown filter contract and displays `Unknown source` without synthesizing provenance.
- Existing source-kind behavior and namespace pagination/filter history remain unchanged.

## Evidence expectations

Record service, API, and frontend test results and exact filter outcomes.

## Explicit exclusions

No provenance synthesis, source definition, identity/schema change, provider access, or mutation.

## Progress and notes

- 2026-07-29: Opened from the ratified hardening contract.
- 2026-07-29: Execution started after inspecting the governing spec, current source-less malformed-state summary path, API delegation, and URL-backed frontend filtering.
- 2026-07-29: Implemented effective namespace source matching as the persisted source kind or `unknown` when `source=None`; no provenance object is synthesized. Extended the existing attributable malformed-state regression to prove `local_status=error`, `source=None`, inclusion under `unknown` and `unknown+error`, and exclusion from website/GitHub/document/database. API coverage proves the same effective filtering, and the URL-backed frontend regression requests `source_kind=unknown`, preserves it with `local_status=error`, and renders `Unknown source`.
- 2026-07-29: Focused validation passed 67 local/API tests, all 49 frontend tests, and `git diff --check`.
- 2026-07-29: Aggregate validation and independent final review passed; service, API, and frontend coverage prove source-less error namespaces match `unknown` and no known source kind.

## Closure mapping

- Exact source-less error and filter outcomes are recorded in `.10x/evidence/2026-07-29-command-center-bounded-review-hardening.md`.
- Final review confirms no provenance synthesis, identity change, source access, or scope widening.

## Retrospective

The effective unknown-source rule is fully captured in the focused spec and regression tests. No additional durable learning or follow-up is needed.

## Blockers

None.
