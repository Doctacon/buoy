Status: blocked
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-remote-semantic-routing-plan.md
Depends-On: .10x/tickets/2026-07-18-build-remote-routing-backend.md

# Atomic Remote Catalog Cutover

## Scope

Execute `.10x/specs/atomic-remote-catalog-cutover.md` as one cohesive authority transition:

- integrate the reviewed backend into remote public catalog CLI;
- replace approved-apply local card registration/reconcile with the remote contract including safe rebase/accept remote;
- replace local automatic routing with authenticated live-list/remote-card reads while preserving explicit CLI bypass;
- update CLI/help/docs/changelog/tests and remove obsolete local catalog paths/modules where no longer used;
- after implementation review and hosted PR checks, enter the mutation freeze, seed exactly two cards, verify branch behavior, integrate, verify integrated behavior, and delete only the exact bound local catalog/lock.

The implementation subagent owns code only. Parent/release sessions own live preflight, user-authorized remote writes, protected integration, post-merge verification, local deletion, evidence, review, and closure.

## Acceptance criteria

### Implementation

- Public catalog CLI, approved apply, automatic routing, outputs, and help satisfy all three active behavior specs.
- Apply preview remains local/API-free and labels remote state unknown; approved phases/recovery are exact and replay-safe.
- Automatic preview uses credentials/read-only remote calls; explicit CLI dry preview remains local.
- Local path options/environment/read-write code is removed from public authority.
- Complete fake matrices cover schema/pagination/stability/counts/permissions, default/explicit routing, mutation concurrency, pending confirmation/rebase/accept-remote, error precedence, and redaction.
- Focused/full tests, Python 3.11/3.13/build CI, evidence, and independent review pass before live mutation.

### Live seed and integration

- Freeze is declared and exact local file identity/remote refs/live inventory are revalidated.
- Migration handles absent/partial/exact states per spec with exact affected IDs and final two-pass proof of exactly two cards/no extras.
- Five listed IDs classify as one control-plane, four content-live, two eligible cards, and two missing cards.
- Branch remote previews from canonical and unrelated directories match without content queries; local catalog hash remains unchanged.
- Exact reviewed PR integrates with required checks; integrated develop repeats remote/explicit previews and catalog/apply-preflight validation.

### Deletion and closure

- Exact bound regular non-symlink local catalog/hash/revision/card revisions and pending/lock state revalidate after integration.
- Only `/Users/crlough/Code/personal/turbo-search/.buoy/catalog.json` and an exact regular lock if present are deleted; other `.buoy` state is untouched.
- Post-deletion remote behavior still matches across directories and no local catalog IO remains.
- Freeze is released; durable evidence enumerates remote reads/writes, billing/counts, affected IDs, integration checks, deletion identity, and no-content-operation boundary.
- Independent post-cutover review and parent graph closure pass.

## Explicit exclusions

Live content retrieval/evals; content namespace query/write/delete; extra cards; remote catalog deletion; cross-region work; local cache; ID fallback; distributed locks; protection changes; unrelated cleanup.

## References

- `.10x/specs/remote-turbopuffer-routing-catalog.md`
- `.10x/specs/approved-apply-remote-catalog-registration.md`
- `.10x/specs/default-remote-namespace-routing.md`
- `.10x/specs/atomic-remote-catalog-cutover.md`

## Evidence expectations

Implementation fake/request matrices and full/hosted checks; exact live preflight/freeze; schema/cards/affected IDs/stability/billing; two-directory branch/integrated/post-deletion previews; PR/check/commit identities; file deletion proof; side-effect attestation; independent reviews.

## Blockers

Remote backend dependency only.

## Progress and notes
