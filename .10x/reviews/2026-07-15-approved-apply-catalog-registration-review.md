Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: commits `0ea4571` and `e7a8170`
Verdict: pass

# Approved Apply Catalog Registration Review

## Target

Independent lifecycle/safety and compatibility review of approved apply catalog registration, pending recovery, CLI/docs/tests, evidence, and ticket against `.10x/specs/superseded/approved-apply-catalog-registration.md`.

## Findings and resolution

Initial review found false catalog status when pending cleanup failed, stale enabled-state overwrite for generated cards, pending pathname replacement races, symlinked pending-root escape, and insufficient missing-credential recovery coverage.

Corrective commit `e7a8170` resolved each:

- catalog-committed/pending-cleanup failure reports `catalog_updated=true`, revisions, `pending_cleanup=false`, and idempotent reconcile;
- current enabled state is preserved for generated and manual cards;
- reconcile/abandon revalidate payload and inode after namespace lock and immediately before unlink;
- pending creation rejects symlinked/non-directory roots;
- missing credentials leave unconfirmed state, reruns block, and only approved abandonment permits later apply.

A parent-requested hardening also made confirmation-write interruption recoverable when applied state proves success. Source-backed `pdf://` document identity was added narrowly to active specs and tests while filenames remain metadata-derived.

## Correct

- Namespace lock spans model, pending, credentials, remote pipeline, state, confirmation, and catalog commit with namespace-before-catalog order.
- Confirmed/unconfirmed collisions block automatic remote replay.
- Pending hashes and catalog/state/path bindings, trusted-root checks, reconciliation, abandonment, and idempotency are covered.
- Schema-v1 precision/source compatibility, GitHub/website/file/PDF mapping, preflight safety, region/catalog precedence, existing depth-one/stale semantics, and output contracts are preserved.
- Manual semantics and enabled state survive apply; generated/system fields refresh.
- No automatic routing, remote catalog, ACL, taxonomy, graph, or live validation call was added.
- 133 focused and 346 full-suite tests, compilation, and `git diff --check` passed.

## Verdict

Pass. Two fresh re-reviewers found no blocker.

## Residual risk

Power-loss and network-filesystem behavior is not qualified beyond atomic local filesystem tests. Unconfirmed remote state intentionally requires explicit operator abandonment when applied state cannot prove success.
