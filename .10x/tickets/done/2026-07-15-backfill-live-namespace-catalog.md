Status: done
Created: 2026-07-15
Updated: 2026-07-15
Parent: None
Depends-On: .10x/tickets/done/2026-07-15-production-semantic-routing-plan.md

# Backfill Live Namespace Catalog

## Context

The production routing implementation was integrated, but catalog registration is prospective: namespaces applied before the apply-registration release were not backfilled. The user's first live route therefore found an empty legacy-root catalog even though verified local applied state exists, including 6,763 active Oscilar rows. The completed parent was operationally incomplete for immediate use.

The user selected a read-only live Turbopuffer namespace inventory as the existence authority, followed by local catalog registration from verified local plan/applied-state metadata. This authorizes remote reads only, not remote writes or deletion.

## Scope

- Read the live Turbopuffer namespace inventory without exposing credentials.
- Match exact live namespace IDs to trustworthy local applied-state and plan/source records under the resolved legacy `.turbo-search` state root and tracked artifacts.
- Preview the proposed cards and explicitly classify live namespaces lacking trustworthy local metadata and local historical namespaces absent remotely.
- Register locally only cards whose source, region, embedding, precision, schema, and ranking contracts are supported by verified records and active specifications.
- Use concise source-backed semantic fields sufficient for routing; do not decode namespace IDs as semantic authority.
- Prove the resulting catalog with `catalog list --all` and a local-only dry auto-route for the user's Oscilar-purpose query.
- Record commands, counts, selected/excluded namespaces, and limits without secrets.

## Explicit exclusions

- No Turbopuffer writes, namespace mutation, row retrieval, deletion, or live routed retrieval.
- No registration inferred solely from a live namespace ID.
- No code changes unless inspection proves the existing catalog CLI cannot perform the ratified operation; if so, block and shape that change separately.
- No model download or substitution.

## Acceptance criteria

- The read-only live inventory is captured with namespace IDs but no credentials.
- Every registered card has exact live namespace existence plus locally verified source/applied compatibility provenance.
- Unsupported/unmatched entries are reported and not registered.
- The new default `.buoy/catalog.json` contains the approved compatible cards with normalized persisted vectors; the legacy `.turbo-search` root is absent after the user-authorized migration.
- `uv run buoy retrieve "what is the purpose of oscilar?" --auto-route --dry-run` succeeds without a legacy-root warning and selects `site-oscilar-com-v1` when eligible.
- No remote write path is invoked.

## Evidence expectations

- Durable evidence records the inventory command shape, matching procedure, card list, exclusions, catalog revision, dry-route selection, and limitations.
- Independent review checks provenance, absence of remote mutation, and route output before closure.

## Blockers

None. User ratified read-only remote inventory and local registration in the current workstream.

## Progress and notes

- 2026-07-15: Reproduced empty `.turbo-search/catalog.json`; inspected verified Oscilar DuckDB state and current plan. User selected read-only remote inventory over Oscilar-only or all-local backfill.

- 2026-07-15: Read-only inventory returned four live IDs in `gcp-us-central1`. Pre-mutation match table `.10x/evidence/.storage/2026-07-15-live-namespace-catalog-backfill-match.json` proposes two registrations (Dagster benchmark and Oscilar), excludes two live IDs with local state but incomplete canonical compatibility provenance, and identifies 58 historical local-only IDs. No catalog mutation had occurred at this checkpoint.
- 2026-07-15: Locally registered the two fully supported cards with the API key removed from each mutation process. Catalog revision is `cd77c5ce97dd7f8df82b191b9e534d0c5535c7fa5224ef81edcbacb7732b01e6`; both vectors validate at 384 dimensions and unit norm.
- 2026-07-15: The exact Oscilar dry route succeeded locally with no credentials/API calls and selected `site-oscilar-com-v1` first, followed by the Dagster benchmark. Evidence: `.10x/evidence/2026-07-15-live-namespace-catalog-backfill.md`. Ticket remains active for independent review and closure.

- 2026-07-15: Independent local-only review passed. Review: `.10x/reviews/2026-07-15-live-namespace-catalog-backfill-review.md`.

## Closure mapping

- Read-only inventory: four live IDs recorded without credentials.
- Provenance match: two registered, two deliberately excluded, 58 historical local-only.
- Canonical catalog: two enabled validated cards under `.buoy/catalog.json` at revision `cd77c5ce97dd7f8df82b191b9e534d0c5535c7fa5224ef81edcbacb7732b01e6`; catalog bytes and hashes were preserved through migration.
- Legacy cleanup: the explicitly disposable 513 MB applied-state tree, old catalog/lock, and empty `.turbo-search` root were removed only after validating the new catalog; no pending recovery files existed.
- User reproduction: exact default dry route succeeds without a legacy warning and ranks `site-oscilar-com-v1` first without credentials or remote calls.
- Reviews: backfill and state-root migration pass; remote audit-log and historical deletion-observation limits retained explicitly.

## Retrospective

Prospective registration is not operational migration. When a new local authority is introduced over pre-existing remote resources, delivery must either include a provenance-safe backfill or explicitly state that the catalog starts empty. The backfill preserved the stricter rule: live existence alone never supplies semantic or compatibility authority.

- 2026-07-15: Reopened after the user explicitly declared legacy applied state disposable and directed migration to the new default root. Exact inspected scope: preserve the validated two-card catalog, remove the empty catalog lock and 513 MB `.turbo-search/state`, remove `.turbo-search`, and verify default `.buoy/catalog.json` behavior without credentials or remote calls. No pending recovery files exist and `.buoy` was absent before migration.
- 2026-07-15: Migrated the catalog byte-for-byte to private `.buoy/catalog.json`, then deleted only the authorized 538,263,552-byte old state, old catalog/lock, and empty legacy root. Original default catalog and Oscilar dry-route commands now use `.buoy` without a legacy warning; the revision, file hash, two cards, and Oscilar-first route are unchanged. Credentials were removed and model networking forced offline for all validation. Evidence: `.10x/evidence/2026-07-15-default-buoy-state-root-migration.md`. Ticket remains active pending independent review.

- 2026-07-15: Independent migration review passed after stale acceptance text was corrected. Review: `.10x/reviews/2026-07-15-default-buoy-state-root-migration-review.md`.

## Migration closure

The canonical local catalog now lives at the normal `.buoy/catalog.json` path, the disposable legacy applied state and `.turbo-search` root are absent, default commands are warning-free, and the exact Oscilar route remains correct. The user-authorized loss of applied ledgers may make later approved applies re-upsert rows; no remote state was changed by this migration.
