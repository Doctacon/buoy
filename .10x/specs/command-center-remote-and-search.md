Status: active
Created: 2026-07-23
Updated: 2026-07-23

# Command Center Remote Snapshot and Search

## Purpose and scope

Define the two explicit read-only operations that may access turbopuffer: remote namespace/catalog refresh and retrieval search. Neither operation may run at startup or during ordinary local browsing.

## Remote snapshot behavior

- Remote refresh MUST occur only after an explicit request.
- It MUST reuse current namespace listing, remote catalog readers, and existing compatibility classifiers.
- It MUST return a sanitized snapshot that combines live namespace IDs and catalog cards with local inventory without synthesizing or writing cards.
- The result MUST state whether credentials were required, API calls occurred, and writes occurred (`false`).
- Missing credentials MUST return structured `remote_credentials_missing`/not-configured state without provider stack traces.
- Remote statuses MUST remain `not_checked` before refresh; lack of a remote match is not automatically an error.

## Search behavior

- Search MUST reuse current retrieval, multi-namespace retrieval, ranking-default, and automatic-routing functions rather than implementing a second ranking path.
- Explicit namespaces MUST bypass automatic routing. Contradictory explicit/automatic settings MUST fail clearly.
- Multi-namespace failure behavior MUST match the current CLI: no partial result set when one selected namespace fails.
- Requests MUST bound query length, namespace count, route/top-k values, candidates, and ranking overrides.
- Results MUST expose available namespace, title, URL/citation, section, content preview, tags, score, and safe diagnostics.
- Search MAY read turbopuffer credentials, call turbopuffer, load the local content embedding model, and read the remote catalog only after explicit execution.
- Provider errors MUST be logged in sanitized form and returned as structured safe errors.

## Acceptance criteria

1. Fake-client tests cover live/catalog/local classification, no writes, and missing credentials.
2. Fake-retriever tests cover explicit, multi-namespace, and automatic routing; contradictory requests fail.
3. No browser response includes credentials, connection settings, private paths, or unsafe provider exceptions.
4. Startup and local endpoints make no provider calls and load no embedding model.

## Constraints and exclusions

No catalog mutation, namespace deletion, source provider access, arbitrary SQL, browser credentials, or persisted remote snapshot is required in Phase 1.
