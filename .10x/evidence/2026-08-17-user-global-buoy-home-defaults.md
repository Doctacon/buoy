Status: recorded
Created: 2026-08-17
Updated: 2026-08-17
Ticket: .10x/tickets/done/2026-08-17-default-local-assets-to-user-home.md
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

## Implementation identity and scope

The reviewed implementation is exact commit
`3c5f2e9b38b752594a68d46eaf4c60b8da3738f0`, tree
`f0eb52f15dd5f4bde7d8ba6ee4e7a3c897bf1d24`, with sole parent and exact
`develop` base `e101690bc351d92cc6b24a46cb5bc30f00bd6df0`. A pre-commit remote
readback confirmed that `develop` remained that exact SHA and `main` remained
`7f7ddfe245e1e5b57946eb6ac10dcc01358559fc`.

The implementation commit changes exactly 37 owned paths: 30 modifications
and seven additions, totaling 2,194 insertions and 305 deletions. It adds one
shared local-path module and focused tests, updates the state/crawl/plan/apply/
repair and cleanup call sites, updates affected tests and user documentation,
and records the bounded governing amendments. It does not change dependency,
lock, or workflow files; plan/state schemas; routing/retrieval behavior;
provider operations; or release machinery.

The exact active-routing CLI module remains byte-identical to the base with
SHA-256
`92c49e943ed5918df7fe65294ff89717e2654a8e9d76317979b63198f1b98ee9`.
Consequently its legacy path option descriptions remain the disclosed UX
limitation rather than invalidating or silently rewriting the active routing
receipt.

## Behavioral proof

Focused tests prove that unrelated working directories resolve the same
absolute temporary-home defaults and receive no implicit `.buoy` or
`artifacts` writes. Project `.buoy`, `.turbo-search`, and artifact decoys stay
byte-identical and never affect implicit selection. Explicit relative old
roots and plans retain their established semantics. Website, GitHub, local
document, DuckDB, BigQuery, and Snowflake plan defaults share the canonical
root and use distinct `-plan` leaves. Argument-free apply accepts exactly one
supported global plan and fails closed when ambiguous.

Path-boundary tests prove mode-`0700` creation, symlink/file rejection, clear
home-resolution failures, state-subtree protection, exact canonical-artifact
cleanup, dot/sibling containment, final-parent and nested-ancestor symlink
rejection, configured-root precedence, whole-plan replacement resistance, and
retention on platforms without fd/symlink-safe recursive removal. The tests
also cover the documented portable threat boundary: cooperative Buoy
concurrency is protected; no atomic child-entry compare-and-unlink guarantee
is claimed against an actively malicious same-UID actor mutating a private
random quarantine after final binding.

## Validation receipts

- Python 3.11: 348 focused tests and all 883 tests passed.
- Python 3.13: 292 focused tests and all 883 tests passed.
- The independent reviewer additionally passed 235 focused tests.
- Source validation passed with active routing artifact
  `745cdb76c894ef1770f6daf3d303f2b6d0ba6905098924f1cb1a8fa40e738fea`
  and canary suite
  `0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5`.
- Ranking validation passed 13 datasets, 369 judgments, and 90 composite
  identities; C6 validation passed with digest
  `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`
  and its expected non-release-ready state.
- The 154-package offline lock check and in-memory compilation of 90 Python
  files passed on both runtimes.
- Both runtimes produced and validated identical distributions: the 70-file,
  648,068-byte wheel SHA-256 is
  `d9e02ba96cc979e919622350e53d96a28ec41f159ee06b820d517d99c91a536a`;
  the 144-file, 1,143,550-byte sdist SHA-256 is
  `e687a12c5c66e9c39b26b764c1ee57339923c5cff58a20884a6547fff54ed777`.
- Fresh offline wheel installs passed console/module/version/help smoke,
  canonical default-path assertions, local-plan creation, implicit apply
  selection, active-routing loading, distribution inspection, and diff
  hygiene without credentials, embeddings, models, provider calls, or
  external network access.

## Compatibility and external effects

The final isolated checks kept `/Users/crlough/.buoy` absent. A Python 3.11
temporary home created only its private `.buoy` boundary, no state database;
the Python 3.13 temporary home remained empty. All working-directory decoys
remained byte-identical. The earlier accidental empty real-home boundary and
its empty-only restoration remain fully accounted for in the initial
observation above.

Users separating remote accounts or regions must choose explicit distinct
roots. Direct consumers of internal source dataclass constructors or removed
module constants may notice implementation-surface changes; the supported CLI
and documented explicit flags remain compatible. The global installed `uv`
tool was not replaced.

No existing project-local asset, credential, provider/catalog/content state,
model cache, package publication, tag, Release, protection rule, `develop`, or
`main` was changed. Durable repository effects at handoff are limited to the
isolated task worktree/branch and its bounded implementation and closure-record
commits; branch push and draft-PR handoff remain pending and do not authorize
integration.
