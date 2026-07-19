Status: cancelled
Created: 2026-07-11
Updated: 2026-07-18
Parent: None
Depends-On: None

# Smoke Test Mercury Site — Historical Qdrant Branch

## Provenance and non-authority

This record indexes the untracked active ticket of the same path in dirty worktree `thistle-site-test` at HEAD `d7a37d79de7011d9b4c0a0180f8bcea6265a7f62`. It describes superseded `turbo_search`/Qdrant behavior and is not authority for current Buoy/Turbopuffer operations.

## Historical result

On 2026-07-11 the authorized branch workflow completed one Mercury plan, one local preflight, one approved apply to fresh Qdrant collection `site-mercury-com-v1`, and exactly one fixed search, then stopped Qdrant without deletion. The plan reported 1,589 pages, 31,861 pre-dedup chunks, 19,416 retained chunks, and zero failed requests. The first search hit directly answered the question; two of five hits were weak. Full observation, artifact hashes, and raw-path inventory are preserved in `.10x/research/2026-07-18-thistle-qdrant-dead-end-disposition.md` and `.10x/evidence/.storage/2026-07-18-thistle-qdrant-dead-end/dirty-path-inventory.tsv`.

## Cancellation rationale

The owning provider/package/collection workflow was abandoned and cannot be accepted against current architecture. No current live smoke is implied or authorized. The valuable historical quality/scale observation has the durable research owner above, so the old active ticket is cancelled rather than left actionable.

## Explicit exclusions

No crawl, search, Qdrant start, remote request, mutation, deletion, or current-source claim occurred during cancellation.

## Progress and notes

- 2026-07-18: Cancelled during read-only dead-end triage after preserving provenance and findings.
