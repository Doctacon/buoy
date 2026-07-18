Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Relates-To: .10x/tickets/done/2026-07-15-backfill-live-namespace-catalog.md, .10x/specs/superseded/production-local-namespace-catalog.md

# Default Buoy State-Root Migration

## What was observed

Before mutation, `/Users/crlough/Code/personal/turbo-search/.turbo-search` contained exactly:

- `catalog.json`, 26,063 bytes;
- empty `catalog.json.lock`;
- `state/`, 538,263,552 allocated bytes (`513M`).

`.buoy` was absent. No `catalog-pending` path or `*.pending` file existed. The source catalog contained exactly the enabled Dagster benchmark and Oscilar cards at revision `cd77c5ce97dd7f8df82b191b9e534d0c5535c7fa5224ef81edcbacb7732b01e6`; its file SHA-256 was `aafe3e6752671badef9da1aa0150903056bb856666289c271e0a67cef7a5ab1a`.

The catalog was copied through a same-directory temporary file into `.buoy/catalog.json`, flushed, file-`fsync`ed, atomically renamed, directory-`fsync`ed, and assigned mode `0600` under a mode-`0700` `.buoy` directory. Before any deletion, explicit-path catalog validation and the exact Oscilar dry route passed with credentials removed and offline model flags set. The copied file was byte-for-byte identical, retained both cards/revision/hash, and routed Oscilar first.

Only after that validation, the operation removed exactly:

- `.turbo-search/state/**`;
- `.turbo-search/catalog.json`;
- `.turbo-search/catalog.json.lock`;
- the resulting empty `.turbo-search` directory.

No artifact, plan, source, remote namespace, or Turbopuffer row was deleted or rewritten.

After deletion, the user's original default commands—without `--catalog`—resolved `.buoy/catalog.json`, emitted no legacy-root warning, retained the same two cards/revision/hash, and routed `site-oscilar-com-v1` first. The dry route reported `dry_run=true`, `credentials_required=false`, `turbopuffer_api_calls=false`, and `api_calls_occurred=false`.

## Procedure

1. Rechecked the exact legacy-root shape, absence of `.buoy` and pending recovery files, catalog revision/card identities/hash, and legacy-state size.
2. Created the private `.buoy` directory and atomically persisted the source catalog with file and directory durability calls.
3. Ran with `TURBOPUFFER_API_KEY` removed and `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`:
   - `uv run buoy catalog list --all --catalog .buoy/catalog.json --json`;
   - `uv run buoy retrieve "what is the purpose of oscilar?" --auto-route --dry-run --catalog .buoy/catalog.json --json`.
4. Compared source/destination bytes and SHA-256, parsed both JSON outputs, and asserted Oscilar was route rank one with no credential/API requirement.
5. Removed only the authorized old state, catalog, lock, and now-empty root.
6. Repeated the two commands without `--catalog`, parsed outputs, checked the absence of the legacy warning, and verified directory/file modes.

## What this supports or challenges

This supports that the canonical local routing catalog now uses the Buoy default `.buoy/catalog.json`, while the explicitly disposable legacy applied-state ledgers are gone. It also supports that the migration preserved the catalog exactly and did not require credentials, network access, model downloads, or Turbopuffer operations.

## Limits

- Deleting the old applied-state ledgers means a future approved apply starts without those local row histories and may re-upsert the reviewed corpus; this was explicitly accepted by the user.
- Historical tracked plans and evidence still truthfully record their original `.turbo-search` paths; they were not rewritten.
- The dry route proves local selection and configuration only, not live content freshness or retrieval quality.
- Remote non-mutation is established by removing the API key, forcing offline model operation, using only catalog/dry-route commands, and inspecting their reported flags; no external audit log was consulted.
