Status: pass
Created: 2026-08-16
Updated: 2026-08-16
Ticket: .10x/tickets/done/2026-08-16-implement-automatic-routing-after-apply.md
Specification: .10x/specs/automatic-routing-after-apply.md
Decision: .10x/decisions/buoy-derives-routing-prototypes-from-reviewed-plans.md

# Automatic Routing after Apply Review

## Scope

Independent review examined the complete task diff implementing reviewed,
content-derived routing evidence from plan through approved apply and immediate
namespace-free retrieval. The review included plan/delta schema changes, remote
card schema and migration boundaries, provisional confidence behavior,
per-evidence shortlist nomination, repair authority, CLI output/privacy,
documentation, tests, and recorded performance/package evidence.

## Findings and repairs

The first review rejected unsafe automatic catalog bootstrap, a cross-bank
overlap mismatch, invalid duplicate-row prototype authority, corpus-sized
verification materialization, an inexact generic repair, raw passage leakage,
an incomplete acceptance test, missing performance evidence, stale lifecycle
documentation, and evidence overclaims. Those findings were repaired with an
explicit reader-first schema prerequisite, shared evidence validation, bounded
source-link reads, retained-plan repair authority, a true fake-provider
apply-to-retrieve test, measured timing, and corrected records.

A subsequent review rejected unknown-state `catalog show` fallback,
non-idempotent recovery after an ambiguous successful write, repair/local-apply
races, and generic operator mutation of system-owned passages. The final code
uses a lock-held, read-only `repair-apply --inspect-current` stage when no safe
remote precondition is known, followed by an absence- or revision-bound
approved repair. The bound command revalidates the retained plan and committed
state under the namespace apply lock, recognizes an already-current exact
plan/apply authority without another write, holds the lock through verification
and cleanup, and prints fresh opaque authority on text-mode drift. Generic
`catalog upsert` cannot set or clear generated passages.

No blocking correctness, security/privacy, migration, atomicity, repair, or
authority finding remains.

## Independent validation

- `93/93` focused repair/catalog/apply tests passed.
- `108/108` additional plan, end-to-end, and routing tests passed.
- `git diff --check` passed.
- Review confirmed current discovery contains 848 tests; the parent reran all
  848 under both supported Python versions and recorded final package receipts
  separately in the evidence record.

## Residual boundaries

Per-passage max scoring gives passage-bearing v3 cards more nomination
opportunities than legacy centroid-only cards; these cards therefore remain in
conservative provisional top-three mode until separately certified. Existing
catalogs still require an explicitly reviewed schema-v3 migration, whose
operator-time concurrency boundary cannot be made atomic with the current
provider schema API. Raw catalog-row access can expose the bounded source
excerpts and must be governed as source-content access. Tests use fake providers
and do not constitute live quality certification, migration, or deployment.

No live source, warehouse, Turbopuffer, deployment, registry, release, merge,
or publication operation was performed by implementation or review.
