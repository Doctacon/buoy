Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Relates-To: .10x/tickets/done/2026-07-15-integrate-approved-apply-catalog-registration.md, .10x/specs/approved-apply-catalog-registration.md, .10x/specs/production-local-namespace-catalog.md

# Approved Apply Catalog Registration Implementation Evidence

## What was observed

- Apply and plan preflight now include model-free, non-mutating catalog registration previews with catalog path, action, semantic origin, region, fixed dimensions, and current namespace ranking defaults.
- Approved apply acquires the namespace lock before catalog/model/pending/credential/remote work, recomputes the state diff under that lock, and retains it through applied-state persistence, pending confirmation, and namespace-before-catalog commit.
- The precomputed schema-v1 pending artifact binds normalized state/catalog/applied-state paths, plan/source/namespace identity, prior catalog/card and applied-state identities, resolved retrieval contract, prospective card/vector, confirmation state, and canonical payload hash. Focused tests verify it excludes credentials and chunk content.
- Confirmed and unconfirmed pending collisions block apply before model/credential/remote work. Unconfirmed remote-failure state requires approved abandonment; an interrupted confirmation backed by a new exact applied-state identity points to reconciliation instead.
- Successful apply commits one card and removes pending state. Focused tests prove manual semantics, disabled state, and valid unchanged vectors survive while system/retrieval/apply fields refresh.
- Remote failure leaves the catalog unchanged and an unconfirmed non-reconcilable artifact. Post-state catalog failure returns exit 2 with truthful partial-success fields and an exact local reconcile command, with no automatic second remote write.
- A simulated pending-confirmation atomic-write failure after applied-state success also returns truthful partial success. Reconciliation safely finalizes it from the exact bound state only because the new apply identity differs from the precomputed prior identity; no second remote write occurs.
- Reconcile and abandon are local-only, namespace-locked, hash/path/catalog/state bound, symlink/out-of-root/tamper rejecting, and covered for preview, approval, exact-card idempotency, and successful pending removal.
- Existing schema-v1 plans without embedding precision continue to hash/apply as float32. Existing supported PDF plans retain canonical `pdf://<source-id>` identity and derive human filenames only from verified metadata.

## Procedure and results

```text
uv run python -m unittest tests.test_apply_cli tests.test_catalog_pending tests.test_catalog tests.test_catalog_cli tests.test_cli
Ran 127 tests in 4.052s
OK

uv run python -m unittest discover -s tests -p 'test_*.py'
Ran 340 tests in 6.675s
OK

uv run python -m py_compile src/buoy_search/*.py tests/test_catalog_pending.py tests/test_apply_cli.py tests/test_catalog.py
# no output

git diff --check
# no output
```

Focused tests use fake content embedders, a fixed 384-dimensional routing embedder, fake remote writers, lock/order event sentinels, credential-read sentinels, and injected local persistence failures. No live Turbopuffer call, real credential read, hosted model request, or model download occurred.

## Independent-review fix verification

The bounded review repair split catalog commit from pending cleanup, preserves enabled state for generated and manual cards, hardens pending-directory creation and reconcile/abandon pathname races, and covers missing credentials as an intentional precomputed-pending collision.

Observed focused regressions prove:

- catalog commit plus failed unlink reports exit 2 with `catalog_updated=true`, catalog/card revisions, `pending_cleanup=false`, pending path, and reconcile command; reconcile reports `already-committed` and removes the artifact without remote work;
- a generated card disabled concurrently after precompute remains disabled while generated/system fields refresh;
- reconcile and abandon reject identical-content inode replacement after namespace-lock acquisition and immediately before unlink; reconcile does not commit when replacement occurs at lock entry, and retains the pending path after a post-commit replacement;
- pending creation rejects both a symlinked `catalog-pending` directory and a non-directory path, creates nothing through the symlink target, and performs no remote write;
- missing credentials leave a valid unconfirmed pending artifact, construct no remote writer, block rerun, remain after abandonment preview, and require approved local abandonment.

```text
uv run python -m unittest tests.test_apply_cli tests.test_catalog_pending tests.test_catalog tests.test_catalog_cli tests.test_cli
Ran 133 tests in 4.365s
OK

uv run python -m unittest discover -s tests -p 'test_*.py'
Ran 346 tests in 6.721s
OK

uv run python -m py_compile src/buoy_search/*.py tests/test_catalog_pending.py tests/test_catalog.py
# no output

git diff --check
# no output
```

## What this supports

This evidence supports child 2 acceptance for apply `--region`/`--catalog`, non-mutating previews, lock acquisition/lifetime/order, collision/precompute/confirmation/commit phases, partial-success and confirmation-failure recovery, reconciliation and approved abandonment, exact bindings/path safety/idempotency, manual/enabled preservation, schema-v1/source compatibility, documentation, and regression preservation of existing apply remote/write/stale/state behavior.

## Limits

- This is implementation evidence, not independent review and not ticket closure.
- Filesystem atomicity and lock behavior are unit/integration observations on the local test filesystem, not a power-loss or network-filesystem qualification.
- No `retrieve --auto-route`, remote catalog, ACL, graph, taxonomy, or live remote behavior was implemented or exercised.
