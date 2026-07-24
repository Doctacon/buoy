Status: done
Created: 2026-07-23
Updated: 2026-07-23
Parent: .10x/tickets/done/2026-07-23-command-center-phase-1-plan.md
Depends-On: .10x/tickets/done/2026-07-23-command-center-local-inventory-services.md, .10x/tickets/done/2026-07-23-command-center-remote-search-services.md, .10x/tickets/done/2026-07-23-command-center-api-server-cli.md, .10x/tickets/done/2026-07-23-command-center-frontend.md

# Close Original-Brief Command Center Acceptance Gap

## Scope

Complete the bounded original-brief fields omitted from the first integrated implementation while preserving all established security and laziness boundaries.

## Acceptance criteria

- `/api/v1/capabilities` reports sanitized `artifacts_root_available`, `state_root_available`, `turbopuffer_credentials_available`, `ui_build_available`, `bigquery_extra_installed`, and `snowflake_extra_installed` booleans plus current version/read-only fields. Readiness uses environment/module/filesystem presence only; it constructs no clients and imports no optional adapters.
- Dashboard service/API/UI includes explicit pending-change namespace count and artifact-error count alongside plan, namespace, applied, and active-row counts. Pending means a namespace's latest valid plan proposes at least one row upsert or stale row; unknown diff values are not invented.
- Namespace summary/API/UI includes a stable local status (`planned`, `applied`, `pending_changes`, or conflict/error status when attributable), active rows, retained stale rows, latest planned upserts/stale rows, document/page count, chunk count, latest plan/apply identity, and source kind/label through existing safe provenance.
- Namespace inventory table renders retained stale, planned upsert, and planned stale columns and filters the actual local/remote/catalog statuses.
- Namespace detail combines the current in-memory explicit remote snapshot when available, otherwise says `Not checked`; it displays remote and catalog status, safe source details, retrieval region when persisted/known, document/chunk counts, and the exact graph empty message `No knowledge graph has been built for this namespace.`
- Plan history surfaces first-apply and recorded source credential/API activity where known without source reconnection.
- Dashboard visibly reports whether turbopuffer credentials are configured as a boolean readiness indicator without exposing values.
- Startup remains remote/model/source-adapter inert; no mutation endpoint/control is added.
- Python/API/frontend regression tests cover each field and the ordinary core environment remains independent of UI/source extras.

## Explicit exclusions

No new remote call, persisted snapshot, source access, apply/delete/catalog mutation, arbitrary paths, graph implementation, hosted access, or semantic change to existing catalog/retrieval classifiers.

## Evidence expectations

Record focused Python/frontend results, startup/import isolation, final build synchronization, and full-suite impact. Update the parent review only after independent acceptance passes.

## References

- Original user Phase 1 command-center brief dated 2026-07-23
- `.10x/specs/command-center-local-inventory.md`
- `.10x/specs/command-center-local-api-and-server.md`
- `.10x/specs/command-center-operator-interface.md`
- `.10x/reviews/2026-07-23-command-center-phase-1.md`

## Progress and notes

- 2026-07-23: Opened before final handoff when direct comparison to the original brief found the omitted readiness/dashboard/namespace-detail presentation slice.
- 2026-07-23: Implemented the bounded capability readiness, dashboard pending/error counts, namespace status/count/detail presentation, persisted retrieval region, plan-history activity, in-memory remote detail, and exact graph-empty message. Rebuilt packaged assets and recorded focused, compatibility, full-suite, static-root, and core-isolation validation at `.10x/evidence/2026-07-23-command-center-acceptance-gap.md`.
- 2026-07-23: Independent review found one nullable catalog `Not checked` rendering/filtering mismatch. The repair added correct classification plus a frontend regression and a non-empty service-through-FastAPI schema contract. Final focused results passed: 21 frontend, 12 API, and 17 local tests.
- 2026-07-23: Independent re-review verdict is pass with no remaining blocker/significant mismatch. Review reconciled at `.10x/reviews/2026-07-23-command-center-phase-1.md`; ticket closed after parent acceptance mapping.

## Blockers

None.
