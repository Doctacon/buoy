Status: done
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-remote-semantic-routing-plan.md
Depends-On: None

# Build Remote Routing Backend

## Scope

Implement only the inert backend primitives in `.10x/specs/remote-turbopuffer-routing-catalog.md` and recovery merge/identity helpers needed by `.10x/specs/approved-apply-remote-catalog-registration.md`:

- provider-neutral canonical card serializer/hash from the active card contract and exact remote schema constants;
- deterministic ID and row conversion/validation;
- injected-client namespace listing, metadata normalization, two-pass strong paginated reads, stable snapshot/intersection counts;
- exact conditional create/update/delete and re-read verification;
- migration-state classifier;
- safe-rebase and exact operator-accepted stable remote revision validation helpers without clock-based ordering;
- permission/API/timeout/billing diagnostics and vector redaction.

Do not connect these primitives to public catalog CLI, apply, or retrieval. Do not create a public temporary migration command. Existing local behavior remains byte-for-byte where practical.

## Acceptance criteria

- Exact schema golden fixture and server-normalization tests cover every attribute/type/index/nullability rule.
- Request-shape fakes prove page size 100, strong consistency, ID filters/order, vectors, two-pass card stability, two identical auto-paginated namespace-list passes at page size 1000, and bounded non-advancing protections.
- Mutations prove exact conditions/affected IDs/re-read, including delete conflicts and partial migration races.
- Count precedence and five-ID/two-card fixture match the spec.
- Recovery helpers distinguish rebase-safe manual/enabled edits, unsafe system changes, and exact operator-accepted stable remote revisions without using wall-clock causality.
- SDK error/timeout/429 diagnostics and billing counts are bounded/redacted.
- No public CLI/help/docs behavior changes, local catalog IO changes, credentials, live calls, or remote writes.
- Focused/full/hosted checks, evidence, and independent review pass.

## Explicit exclusions

Public catalog/apply/retrieve integration, live migration, local deletion, content namespace operations, temporary commands, unrelated cleanup.

## References

- `.10x/specs/namespace-routing-card-contract.md`
- `.10x/specs/remote-turbopuffer-routing-catalog.md`
- `.10x/specs/approved-apply-remote-catalog-registration.md`
- `.10x/research/2026-07-18-turbopuffer-remote-routing-catalog.md`

## Evidence expectations

Golden schema/cards, exact captured fake requests/responses, pagination stability, mutation/recovery matrices, no-public-diff proof, focused/full/hosted checks, independent review.

## Blockers

None.

## Progress and notes

- 2026-07-18: Execution started on `work/build-remote-routing-backend`; active specs, research, current local catalog/card implementation, installed SDK 2.4.0 contracts, and existing tests inspected. Public behavior and live operations remain excluded.
- 2026-07-18: Implemented inert remote backend; initial Python 3.11/3.13 full suites each passed 382 tests and focused compatibility passed 59. Review repairs expanded coverage to 23 backend tests and added mutation prevalidation, projection-safe rebase, stable accept-remote, 10,000-page/cursor bounds, payload-free provider errors, independent 29-attribute schema/nullability fixture, and zero-eligible management/routing behavior. Final review passed after formatted tracebacks proved factory/list/query/write failures omit raw provider payloads. PR #31 hosted Python 3.11, Python 3.13, and distribution checks passed; dedicated integration reran 387 tests and merged as `bc8bdc30555e66837288d049c3c4885e3cf1df71`. Evidence: `.10x/evidence/2026-07-18-remote-routing-backend-implementation.md`; review: `.10x/reviews/2026-07-18-remote-routing-backend-review.md`.
