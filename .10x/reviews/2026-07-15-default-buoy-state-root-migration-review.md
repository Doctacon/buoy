Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: commits `a0a50b8` and `dbab451`; canonical runtime state `/Users/crlough/Code/personal/turbo-search/.buoy`
Verdict: pass

# Default Buoy State-Root Migration Review

## Findings

- The change is limited to operational state migration and durable records; no implementation changed.
- `.turbo-search` is absent. `.buoy` is private mode `0700`; `.buoy/catalog.json` is mode `0600`.
- Catalog size, SHA-256, catalog revision, two enabled cards, dimensions, and vector norms match the pre-migration record.
- No pending recovery paths existed before deletion or remain afterward.
- Evidence bounds deletion to the user-authorized 513 MB legacy state, old catalog/lock, and empty legacy root after the new catalog validated.
- With credentials removed and model networking forced offline, default catalog list and the exact Oscilar dry route emit no legacy warning, use `.buoy/catalog.json`, and rank Oscilar first.
- Commit `dbab451` corrected stale ticket acceptance and closure language to the new default root.

## Verdict

Pass. No blocker remains and the reopened backfill ticket may close.

## Residual risk

The exact historical deletion scope and pre-deletion absence of pending files depend on contemporaneous operator evidence because deleted state cannot be reconstructed. Deleting applied-state ledgers means a future approved apply may treat a corpus as a first apply and re-upsert rows; the user explicitly accepted that state as disposable. No remote audit log was inspected.
