Status: superseded
Created: 2026-07-18
Updated: 2026-07-18

# Approved Apply Remote Catalog Registration

## Purpose and scope

Replace local JSON card commit with revision-bound remote registration while preserving content ordering, manual/enabled ownership, crash truthfulness, replay blocking, and explicit recovery.

## Preflight and confirmation boundary

Apply mode selection and interactive confirmation are governed by `.10x/specs/interactive-apply-confirmation.md`. `buoy apply --dry-run` remains local, credential-free, model-free, and API-free. Interactive plain apply performs that complete preflight before prompting; cancellation remains a zero-write success. Preflight reports content diff/intent plus `remote_catalog_state=unknown_until_approved`; it cannot claim manual/enabled preservation, expected revision, or final card mutation. Only `--approve` or interactive `y`/`yes` may enter the approved sequence below. This remains coherent with `.10x/specs/apply-to-retrieval-handoff.md`.

## Approved lock and local precompute

Approved apply holds the existing local namespace lock through completion. Before credentials/API work it MUST:

1. verify plan/artifacts/diff/applied state;
2. derive and validate generated source/retrieval candidate fields;
3. compute candidate semantic vector with the cached pinned model;
4. validate reserved target/region/card ID;
5. reject any pending collision.

## Authenticated preparation before content writes

After local precompute:

1. read credentials and strongly validate remote catalog schema/stability;
2. strongly fetch existing card or absence;
3. preserve existing manual semantics and enabled state;
4. bind the complete base-card snapshot plus expected revision/absence;
5. construct/hash/atomically persist pending state containing final intended card, base snapshot, expected revision, catalog namespace/region, plan/artifact/state identities, and intended apply identity.

Any failure stops before content writes. Reads are allowed; card writes are not.

## Content and card sequence

With pending durable and lock held:

1. existing ordered depth-one content upsert/delete pipeline;
2. compact local applied-state commit;
3. confirm pending with exact apply identity/ledger;
4. conditional remote card create/update per remote catalog spec;
5. two-pass strong re-read and validation;
6. remove exact revalidated pending artifact.

Identical already-committed card/apply state is idempotent. Zero affected rows is conflict and leaves confirmed pending.

## Failure truthfulness and replay

- Failure before content work may leave unconfirmed pending only after final remote-bound intent exists; rerun blocks until approved abandonment.
- Content failure leaves unconfirmed pending and never claims card registration.
- Applied-state success followed by pending-confirmation interruption is recoverable: reconcile may promote unconfirmed pending to confirmed only when the current compact ledger exactly proves the pending intended plan/apply identity and row counts/hashes. Otherwise it remains unconfirmed/blocked.
- Confirmed pending forbids automatic content replay and generic abandonment.
- Card failure after state success reports `content_applied=true`, `catalog_updated=false`, exact pending path/conflict, and recovery commands.
- Card success plus cleanup failure reports `catalog_updated=true`, committed revision, `pending_cleanup=false`; reconcile only verifies/removes.

## Recovery commands

### Ordinary reconcile

`catalog reconcile --pending PATH` validates trusted path/payload/inode after lock, promotes narrowly ledger-proven confirmation if needed, and attempts the original conditional card write. Identical committed state removes pending idempotently. A changed revision remains blocked with diagnostics.

### Approved safe rebase

`catalog reconcile --pending PATH --rebase --approve` is allowed only when:

- pending is confirmed or ledger-promotable;
- remote current card strongly stabilizes;
- compared with pending base snapshot, remote changes are limited to `enabled`, or manual semantic fields (`title`, `summary`, `aliases`, `tags`, `semantic_origin=manual`) plus their mechanically derived timestamps/revision/semantic hash/vector/vector hash;
- source, retrieval contract, target, and remote `last_plan_id`/`last_apply_id` still equal the pending base.

It preserves current enabled/manual semantics, merges pending verified system/apply fields, recomputes semantic projection locally if semantics changed, writes conditionally against exact current revision, strongly verifies, and removes pending. Any system/lineage change is not rebase-safe.

If the pending base was absence and a manual card was concurrently created, rebase is safe only when the card is valid/manual, same target, source/retrieval fields exactly equal the pending verified candidate, lineage remains null, and all other differences are manual semantics/enabled plus derived fields. It then follows the same preserve/merge/conditional-write path. Otherwise it remains blocked.

### Approved accept-remote

Apply-ID wall clocks are not causal across machines. `catalog reconcile --pending PATH --accept-remote --approve --expected-remote-revision REV` performs no remote write and makes no automatic newer-state claim. It may remove confirmed pending only when two strong reads return the exact operator-supplied revision, the card is valid for the same target, and it has non-null plan/apply identities different from the pending intended identities. Output must show both identity sets and explicitly state that the operator is declaring this exact remote revision authoritative despite unresolved content ordering. Revision drift or missing/matching lineage fails without removal.

`--rebase` and `--accept-remote` are mutually exclusive, require approval, and have distinct JSON actions/exit success. Neither repeats content.

### Abandon

`abandon-pending --approve` applies only to genuinely unconfirmed state not promotable by ledger proof, performs no remote mutation, and removes only the exact revalidated artifact. Confirmed/promotable state cannot be abandoned.

## Concurrency and security

Remote conditional writes are the cross-machine concurrency boundary; no distributed lock is claimed. Local lock protects one machine's state/pending. Every recovery rereads strongly and binds exact revisions. Cards contain no secrets; output redacts vectors/credentials. Permission matrix follows the remote catalog spec and was user-approved.

## Acceptance scenarios

- First apply: absence-bound pending, content/state, conditional card create, strong verify, cleanup.
- Manual/disabled card: semantics/enabled preserved while system/lineage refresh.
- Concurrent disable/manual edit: original commit conflicts; approved rebase safely preserves it and completes without content replay.
- Concurrent system/apply change: rebase refuses; the operator may explicitly accept one exact stable remote revision and clear pending without claiming timestamp causality.
- Confirmation interruption: exact applied ledger promotes pending; mismatch cannot.
- Content success/card failure and card success/cleanup failure report truthful recoverable states.
- Missing credentials/schema/conflict fails at specified phase without silent overwrite.
- `apply --dry-run` and cancelled interactive apply make zero model/credential/API calls and label remote fields unknown; only confirmed interactive or `--approve` execution enters remote preparation.
- No local catalog JSON is read/written after cutover.

## Explicit exclusions

Remote distributed locks, automatic conflict merge, generic confirmed abandonment, content replay, content namespace deletion, cross-region card writes, ID inference, telemetry, or unapproved live operations.
