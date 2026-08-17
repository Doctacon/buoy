Status: provisional
Created: 2026-08-17
Updated: 2026-08-17
Ticket: .10x/tickets/2026-08-17-default-local-assets-to-user-home.md
Decision: .10x/decisions/buoy-defaults-local-assets-to-one-user-home.md
Specification: .10x/specs/user-global-buoy-home-defaults.md
Review: .10x/reviews/2026-08-17-user-global-buoy-home-defaults-review.md

# User-Global Buoy Home Defaults Evidence

## Initial observation

The implementation session began from exact
`origin/develop@e101690bc351d92cc6b24a46cb5bc30f00bd6df0` in isolated worktree
`/private/tmp/buoy-global-home-defaults` on
`work/global-buoy-home-defaults`. The original `develop` worktree was clean and
was not used for implementation.

A metadata-only scan found no `/Users/crlough/.buoy` and found two independent
project-local state trees under `/Users/crlough/Code`: six `state.duckdb` files
totaling 17,113,088 bytes plus one retained 27,537,408-byte plan delta. File
contents and credentials were not read. Those paths are diagnostic context
only and are excluded from every write, migration, cleanup, and validation
operation in this task.

One early Python 3.13 validation snapshot inherited the real user home while a
database lazy-dependency test exercised an implicit output path. That run
created only the previously absent empty `/Users/crlough/.buoy` directory
boundary (mode `0700`); it created no descendant, database, plan, content, or
other asset. The Python 3.11 validator independently proved the boundary was
empty, removed it with an empty-directory-only operation, and confirmed the
initial absent state was restored. The test now binds `Path.home()` to its own
temporary directory, and final validation must guard the exact real path. This
effect is disclosed rather than described as zero filesystem activity.

Source inspection established that current implicit state is `Path(".buoy")`
with `.turbo-search` fallback, plan/crawl output is relative
`artifacts/site-crawls`, argument-free apply searches only that relative tree,
and catalog repair independently defaults to relative `.buoy`. Retrieve,
ordinary catalog operations, and evals create no application database.

## Intended proof

The final record will bind the exact implementation commit/tree, changed-path
inventory, path-resolution and cleanup invariants, supported-source coverage,
explicit legacy opt-in, dual-runtime test results, source/lock/distribution
receipts, package smoke results, and independent review verdict.

Cleanup evidence will distinguish the proven no-follow ancestor and
whole-plan replacement defenses from the documented portable threat boundary:
cooperative Buoy concurrency is covered, while active same-UID mutation of
child names inside a private random quarantine after final binding is not
claimed to have atomic compare-and-unlink protection.

It will explicitly account for that restored empty-boundary effect and prove that no existing
project-local asset, credential, provider/catalog/content state, model cache,
installed uv tool, package publication, tag, Release, protection rule,
`develop`, or `main` was changed.
