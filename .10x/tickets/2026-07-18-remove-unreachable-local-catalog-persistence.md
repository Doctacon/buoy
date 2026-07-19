Status: blocked
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-repository-cleanup-plan.md
Depends-On: .10x/tickets/2026-07-18-triage-thistle-qdrant-dead-end.md

# Remove Unreachable Local-Catalog Persistence

## Scope

Remove the production-unreachable local JSON catalog persistence cluster from `src/buoy_search/catalog.py` and its obsolete tests:

- `document_to_dict`
- `empty_catalog`
- `resolve_catalog_path`
- `load_catalog`
- `catalog_lock`
- `_atomic_write`
- `save_catalog`
- `commit_system_card`
- `mutate_catalog`

Preserve production-reachable card models, schema parsing/validation, semantic projection, generated semantics, routing helpers, remote catalog operations, pending recovery, and `catalog migrate-local` source parsing/validation.

## Acceptance criteria

- AST/source-reference inspection confirms each removed symbol has no production caller before deletion.
- No local catalog path, lock, or atomic persistence implementation remains solely for tests.
- `catalog migrate-local`, remote catalog list/mutation/reconcile/abandon, apply registration, automatic routing, and generated card behavior remain unchanged.
- Tests for removed private persistence behavior are deleted rather than preserving dead implementation; protective parser/card/remote tests remain.
- Focused/full Python 3.11/3.13 tests, distribution build, source search, independent review, and hosted checks pass.

## Evidence expectations

Before/after production reachability report, exact deleted symbols/tests, focused/full/build outputs, and no-write/no-remote attestation.

## Blockers

Complete the preceding Thistle disposition and incorporate current `develop` before execution.

## Explicit exclusions

Removing `catalog migrate-local`; changing card schema, semantic projection, remote catalog behavior, pending recovery, routing, compatibility aliases, or user data; deleting catalog files from disk.

## References

- `.10x/tickets/2026-07-18-repository-cleanup-plan.md`
- `.10x/research/2026-07-18-repository-dead-end-inventory.md`
- `.10x/decisions/production-routing-remote-catalog.md`
- `.10x/specs/remote-routing-catalog-cli.md`

## Progress and notes
