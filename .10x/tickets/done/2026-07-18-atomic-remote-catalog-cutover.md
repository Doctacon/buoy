Status: done
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/done/2026-07-18-remote-semantic-routing-plan.md
Depends-On: .10x/tickets/done/2026-07-18-build-remote-routing-backend.md

# Atomic Remote Catalog Cutover

## Scope

Execute `.10x/specs/atomic-remote-catalog-cutover.md` as one cohesive authority transition:

- integrate the reviewed backend into remote public catalog CLI;
- replace approved-apply local card registration/reconcile with the remote contract including safe rebase/accept remote;
- replace local automatic routing with authenticated live-list/remote-card reads while preserving explicit CLI bypass;
- update CLI/help/docs/changelog/tests and remove obsolete local catalog paths/modules where no longer used;
- after implementation review and hosted PR checks, enter the mutation freeze, seed exactly two cards through `buoy catalog migrate-local`, verify branch behavior, integrate, verify integrated behavior, and delete only the exact bound local catalog; any lock presence blocks deletion.

The implementation subagent owns code only. Parent/release sessions own live preflight, user-authorized remote writes, protected integration, post-merge verification, local deletion, evidence, review, and closure.

## Acceptance criteria

### Implementation

- Public catalog CLI, approved apply, automatic routing, outputs, and help satisfy the remote card, backend, CLI, apply, and routing active specs.
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
- Only `/Users/crlough/Code/personal/turbo-search/.buoy/catalog.json` is deleted; any lock appearance blocks, and other `.buoy` state is untouched.
- Post-deletion remote behavior still matches across directories and no local catalog IO remains.
- Freeze is released; durable evidence enumerates remote reads/writes, billing/counts, affected IDs, integration checks, deletion identity, and no-content-operation boundary.
- Independent post-cutover review and parent graph closure pass.

## Explicit exclusions

Live content retrieval/evals; content namespace query/write/delete; extra cards; remote catalog deletion; cross-region work; local cache; ID fallback; distributed locks; protection changes; unrelated cleanup.

## References

- `.10x/specs/namespace-routing-card-contract.md`
- `.10x/specs/remote-turbopuffer-routing-catalog.md`
- `.10x/specs/remote-routing-catalog-cli.md`
- `.10x/specs/approved-apply-remote-catalog-registration.md`
- `.10x/specs/default-remote-namespace-routing.md`
- `.10x/specs/atomic-remote-catalog-cutover.md`

## Evidence expectations

Implementation fake/request matrices and full/hosted checks; exact live preflight/freeze; schema/cards/affected IDs/stability/billing; two-directory branch/integrated/post-deletion previews; PR/check/commit identities; file deletion proof; side-effect attestation; independent reviews.

## Blockers

None. The reviewed backend was integrated through PR #31 as `bc8bdc30555e66837288d049c3c4885e3cf1df71`.

## Progress and notes

- 2026-07-18: Backend dependency closed after passing independent review, 387 integration tests, and hosted Python 3.11/3.13/build checks. Cutover implementation started on `work/atomic-remote-catalog-cutover`; live operations remain gated behind reviewed implementation and fail-closed preflight.
- 2026-07-18: Public catalog/apply/retrieval authority integration completed after replacing every temporary skipped suite with remote-contract fakes. Adversarial findings on preview/live truthfulness, post-mutation proof, migration inode binding, request accounting, pending recovery, and test isolation were repaired. Final independent reviews passed; Python 3.11 and 3.13 each passed 392 tests and wheel/sdist built. Evidence: `.10x/evidence/2026-07-18-atomic-remote-catalog-cutover-implementation.md`; review: `.10x/reviews/2026-07-18-atomic-remote-catalog-cutover-implementation-review.md`.
- 2026-07-18: After initial PR #32 hosted checks passed, mutation freeze began. Read-only preflight found absent catalog/four content namespaces. Approved migration created exact schema/two intended rows but verification failed on provider omission of null lineage fields. Raw catalog-only inspection confirmed exactly both intended rows and no content operation. Commit `e83fe90` added strict nullable-omission normalization.
- 2026-07-18: A controlled idempotent verification retry then failed before writes because provider metadata omits `filterable:false` for the exact vector attribute. Raw catalog metadata showed exact `[384]f32`/cosine ANN. Commits `27b36db` and `48b4021` narrowly normalize only that representation.
- 2026-07-18: The next read-only preview reached vector integrity and found provider decimal rendering drift up to `1.47e-8`; f32 byte/hash comparison proved exact stored vectors. Commit `647e65f` canonicalizes incoming remote values to IEEE-754 f32 before strict hashes. Forty-seven focused unittests and independent review passed.
- 2026-07-18: Final read-only and approved idempotent migration checks classified exact with zero affected IDs/writes. Branch, integrated `eba8145bb12eb7a0749a96ee4088938060a9fb12`, and post-deletion previews matched from canonical and unrelated directories. Explicit preview remained API-free; apply preflight remained local/API-free. Exact inode/hash/revisions were rebound and only `.buoy/catalog.json` was deleted. Post-delete remote proof passed and the mutation freeze was explicitly released. Evidence: `.10x/evidence/2026-07-18-remote-routing-catalog-live-cutover.md`.
- 2026-07-18 retrospective: Live friction revealed three narrow provider equivalences now captured in `.10x/knowledge/turbopuffer-routing-catalog-normalization.md`. No new operational skill is warranted because the migration CLI and tests encode the repeatable procedure. No provider-audit or live-apply follow-up is opened for the explicit reasons recorded in live evidence. Final merged-head review found no product defect.
- 2026-07-18: Closure review passed with no blockers: `.10x/reviews/2026-07-18-remote-routing-catalog-closure-review.md`. All acceptance criteria map to implementation/live evidence; ticket closed.
