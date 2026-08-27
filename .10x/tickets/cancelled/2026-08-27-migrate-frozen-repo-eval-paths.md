Status: cancelled
Created: 2026-08-27
Updated: 2026-08-27
Parent: None
Depends-On: .10x/tickets/done/2026-08-27-reorganize-buoy-search-subpackages.md, .10x/tickets/cancelled/2026-08-27-recertify-routing-receipts-after-subpackage-migration.md

# Migrate frozen repository-evaluation paths

## Cold-start context

The subpackage migration and approved routing-receipt recertification now pass focused routing validation, but the full suite has ten failures because the immutable Buoy repository-search dataset still references removed flat module paths. The owner first approved a narrow path-only migration, then authorized a truthful Buoy corpus-identity refresh after inspection proved the paths are bound to a historical source manifest.

Historical governing authority: `.10x/decisions/superseded/buoy-refreshes-repo-eval-corpus-identity-for-subpackage-layout.md`.

Required context:

- `.10x/specs/buoy-search-subpackage-layout.md`
- `.10x/evidence/2026-08-27-routing-receipt-recertification-blocked-by-eval-path-contract.md`
- `.10x/tickets/done/2026-08-27-reorganize-buoy-search-subpackages.md`
- `.10x/tickets/cancelled/2026-08-27-recertify-routing-receipts-after-subpackage-migration.md`

## Scope

- Update only moved source-path strings in the Buoy repository-search dataset and matching test/evaluation fixtures.
- Deterministically refresh the Buoy source-manifest entry against the reorganized local source, including its truthful source/corpus identity.
- Recompute only mechanically derived dataset/manifest/inventory/bundle integrity hashes required by those authorized changes.
- Prove all non-path judgment content unchanged and every new path exists.
- Run focused ranking-contract/autoresearch validation, the full suite, CLI, wheel inventory, and isolated installed-wheel checks.
- Obtain independent review of the complete structural migration, routing receipt update, and eval-path contract migration.
- Record evidence and reconcile the three tickets when criteria are fully supported.

## Explicit exclusions

- Judgment, query, case, grade, label, reason, threshold, fold, namespace, ranking, model, or retrieval changes.
- Retrieval candidate regeneration, provider/model calls, or live operations.
- Changes to non-Buoy corpus manifests or unrelated evaluation datasets.
- Compatibility forwarding modules or duplicate source files.
- Release, publication, deployment, or integration operations.

## Acceptance criteria

1. Only authorized path strings, matching fixture paths, and mechanically derived integrity hashes change in the evaluation-contract surface.
2. Canonical comparison proves every non-path dataset value unchanged.
3. Every migrated judgment path exists and old moved paths are absent from active dataset/fixtures.
4. Dataset/bundle hash validators reproduce the new exact values.
5. Focused ranking-contract and autoresearch tests pass.
6. The complete repository suite passes.
7. CLI, wheel inventory, and isolated installed-wheel validation pass.
8. Independent review passes with no unresolved significant findings.
9. Durable evidence records exact mappings, before/after hashes, commands, outputs, review, and limits.

## Blockers

None. Cancelled because the owner superseded in-place frozen-corpus rewriting with versioned immutable historical artifacts and a separate current dataset.

## Progress and notes

- 2026-08-27: Opened after explicit owner approval. No dataset, fixture, or derived-hash mutation was performed in this decision/ticket-authoring turn.
- 2026-08-27: Read the ticket and all required records completely, then traced ranking validation before mutation. Found 21 affected judgment occurrences across nine distinct moved paths. The dataset paths cannot be migrated consistently without also rewriting a source-path manifest pinned to a historical corpus identity. Escalated the unexpected hash/provenance dependency; supervisor selected the mandatory stop and prohibited both inconsistent manifest rewriting and unapproved corpus regeneration. No eval-contract files were changed, validation was not rerun after the stop, and no files were staged. Marked blocked with evidence in `.10x/evidence/2026-08-27-eval-path-migration-provenance-blocker.md`.
- 2026-08-27: Owner selected a truthful corpus-identity refresh. Superseded the path-only decision, activated the now-superseded corpus-refresh decision, and reopened this ticket. No corpus mutation occurred in that authority-update turn.
- 2026-08-27: Cancelled when the owner selected immutable versioned historical eval artifacts, a separate current dataset permitted to remain `baseline_pending`, and promotion-only benchmark gating. Replacement work is owned by the new evaluation-versioning plan.
