Status: done
Created: 2026-07-23
Updated: 2026-07-23
Parent: .10x/tickets/done/2026-07-23-command-center-phase-1-plan.md
Depends-On: .10x/tickets/done/2026-07-23-command-center-local-inventory-services.md, .10x/tickets/done/2026-07-23-command-center-remote-search-services.md, .10x/tickets/done/2026-07-23-command-center-api-server-cli.md, .10x/tickets/done/2026-07-23-command-center-frontend.md

# Package, Document, Validate, and Review Command Center Phase 1

## Scope

Implement optional-dependency/static-asset packaging, README and command-center documentation, CI changes, lockfiles, complete required validation, package-content inspection, evidence, adversarial review, and coherent parent/child handoff governed by `.10x/specs/command-center-packaging-documentation-ci.md`.

## Acceptance criteria

- UI extra is optional and ordinary imports need neither web dependencies nor Node.
- Wheel contains packaged index and hashed assets; sdist contains intended build inputs.
- README/docs/CLI help accurately describe local-only read-only behavior, activity/secrets, screens, troubleshooting, non-goals, and Phase 2–4 roadmap.
- CI runs pinned Node LTS frontend checks and UI-extra Python/package checks without live credentials.
- Every required command from the user brief is run; exact outcomes and limits are recorded.
- Independent review findings are resolved or durably handled; graph and ticket statuses remain coherent.

## Explicit exclusions

Push, PR, merge, publish/release, live provider/source operations, Phase 2, and graph implementation.

## Evidence expectations

Create evidence records for full validation/package inventory and a review record for the final diff. Do not claim live remote validation.

## References

- `.10x/specs/command-center-packaging-documentation-ci.md`
- all preceding command-center tickets/specifications/evidence

## Progress and notes

- 2026-07-23: Opened from user-ratified Phase 1 brief.
- 2026-07-23: Added the bounded optional `ui` extra and lock entries, explicit wheel static/sdist frontend inclusion with `node_modules` exclusion, concise README entry, comprehensive Command Center guide, contributor asset-sync workflow, immutable Node 24.18.0 frontend CI, and locked UI-extra Python/package CI checks. Updated release/workflow metadata tests without changing ordinary runtime dependencies.
- 2026-07-23: Required validation passed: core locked sync and import isolation; ranking/C6 validators; 649-test full suite; UI-extra sync and 40 focused Python tests; frontend install, 13 tests, synchronized production build; exact `uv build`; wheel/sdist and metadata inventories; installed-wheel default-static lookup; CI archive script; final core restoration, lock/diff hygiene, and no-staged-files checks. Evidence: `.10x/evidence/2026-07-23-command-center-packaging-docs-ci-validation.md`.
- 2026-07-23: Implementation and executor validation are complete. Ticket remains active because independent adversarial review and aggregate parent closure are explicitly parent-owned.
- 2026-07-23: Repaired all named Phase 1 review findings without widening the read-only/local-only boundary: loopback Host and guarded same-origin POST enforcement; token-query citation stripping; state-root containment and duplicate-identity unknown counts; exact search-mode validation and provider-call provenance; complete/merged/paginated frontend inventories; score/diagnostic, freshness/truncation, preview-error, skip-link, contrast, route-wide no-mutation, contributor workflow, and complete sdist-input coverage. Rebuilt packaged assets.
- 2026-07-23: Subsequent review findings covering post-provider activity, internal citation shapes, duplicate-state UI wording, and page/chunk pagination coherence were repaired with regressions. Final parent validation passed 660 core tests (11 skipped), 49 UI-extra command-center tests, 20 frontend tests/build, ranking/C6 validators, wheel/sdist inventory, installed-wheel static lookup, core restoration, and diff hygiene. Evidence: `.10x/evidence/2026-07-23-command-center-packaging-docs-ci-validation.md`.
- 2026-07-23: Independent final review passed with no unresolved acceptance finding. Review: `.10x/reviews/2026-07-23-command-center-phase-1.md`. Closed after graph/status/reference reconciliation and retrospective extraction to `.10x/knowledge/loopback-command-center-security.md`.
- 2026-07-23: Repaired exactly the four findings remaining after final product/security review: post-response normalization/ranking failures now retain provider-call provenance; local and remote citations drop fragments and accept document URIs only in the persisted safe source-ID/one-encoded-filename shape; duplicate applied-state identities receive accurate namespace-detail copy; and chunk transitions retain/reload the selected page preview. Added focused Python/retriever/frontend regressions and rebuilt packaged assets (`index-CdLxZlZF.js`). Validation passed: 79 focused Command Center/release tests, 132 retriever compatibility tests, 20 frontend tests, TypeScript/Vite build, diff hygiene, and no-staged-files check. No live provider/source/model operation ran. Ticket and parent remain open for final independent review.
- 2026-07-23: Repaired the one database-citation finding remaining from final acceptance. Both citation sanitizers now accept only bounded canonical `database_document_url()` values with a validated DuckDB/BigQuery/Snowflake source authority and exactly one percent-encoded document-ID segment; raw path hierarchies are redacted. Local leakage regressions cover all three schemes, and fake-backed explicit search preserves generated citations for all three. The focused local/remote/retriever suite passed (61 tests), direct sanitizer reproduction passed, and diff/no-staged-files hygiene passed. No live provider/source/model operation ran. This closure ticket and its parent remain open for independent acceptance review.

## Blockers

None after dependencies complete.
