Status: done
Created: 2026-08-17
Updated: 2026-08-17
Decision: .10x/decisions/buoy-defaults-local-assets-to-one-user-home.md
Specification: .10x/specs/user-global-buoy-home-defaults.md
Evidence: .10x/evidence/2026-08-17-user-global-buoy-home-defaults.md
Review: .10x/reviews/2026-08-17-user-global-buoy-home-defaults-review.md

# Default New Local Assets to the User-Global Buoy Home

## Outcome

Make a globally installed `buoy` executable use one predictable application
home regardless of invocation directory while leaving existing noncanonical
local assets implicit-inert and explicit-only.

## Owned scope

- Add one shared local-path authority and route implicit state, crawl, plan,
  apply discovery, and catalog repair through it.
- Remove implicit working-directory `.buoy`/`.turbo-search` selection.
- Add the canonical managed-plan cleanup exception without weakening any
  other state-root deletion boundary.
- Fail closed on ambiguous global implicit plan selection.
- Give every default plan, including database-relation plans, a distinct
  `-plan` leaf so it cannot collide with default crawl output.
- Add bounded amendment notes to the active local-compatibility,
  package/CLI-identity, plan-cleanup, generic database-relation, DuckDB-relation,
  and DuckDB-only state records whose old implicit-path clauses are superseded.
- Update focused unit/integration tests, catalog-repair help, README, indexing/migration
  documentation, changelog, this task's governing records, evidence, and
  review.

No plan/state schema, remote/provider operation, routing/retrieval behavior,
model/cache location, dependency, workflow, release, or existing local asset
is owned.

## Required implementation properties

- All implicit paths are absolute beneath `Path.home() / ".buoy"` and remain
  identical across working directories.
- Explicit path arguments preserve compatibility and relative-path semantics.
- Existing noncanonical `.buoy`, `.turbo-search`, and `artifacts` trees are
  never inspected for implicit selection and are never copied, moved, merged,
  backfilled, rewritten, archived, cleaned, or deleted implicitly. Explicitly
  selected state and plans retain their normal write and verified cleanup
  lifecycle.
- The first global plan is allowed to have first-apply semantics; it MUST NOT
  infer stale deletes from ignored ledgers.
- Canonical-home creation is user-private and rejects symlink/non-directory
  boundaries before managed writes.
- Plan cleanup proves both the existing exact artifact identity and canonical
  managed-root containment; every noncanonical state-root target retains the
  prior refusal behavior.
- Cleanup race resistance covers cooperative Buoy activity and rejects
  ancestor, symlink, and whole-plan replacement through final quarantine
  binding. It does not claim an unavailable POSIX compare-and-unlink guarantee
  against active same-UID mutation of child names inside that private random
  quarantine after binding.
- Preserve the exact active-routing `cli.py` source receipt. Disclose rather
  than silently bypass or rewrite the receipt for the pre-existing
  default-path help strings; changing those strings requires a separately
  authorized dormant recertification.
- No test or implementation path reads credentials, calls a provider, loads a
  model, installs the tool, or mutates the scanned existing assets.

## Validation

- focused path/state/crawl/plan/apply/catalog-repair/cleanup/CLI tests;
- full unittest discovery on Python 3.11 and Python 3.13;
- `scripts/release_automation.py validate-source`;
- ranking and C6 frozen-contract validators;
- `uv lock --check`, compile validation, distribution build/inspection, and
  clean-wheel command/help smoke tests;
- exact owned-path review and `git diff --check`;
- independent source/security/compatibility review before handoff.

## External effects boundary

Authorized effects are one isolated `work/*` branch/worktree, bounded commits,
branch push, and an ordinary draft PR for owner review. No self-integration,
existing-file migration/deletion, global-tool install, provider request/write,
credential access, package publication, tag, GitHub Release, branch-protection
change, or `main`/`develop` mutation is authorized.

## Completion

Implementation is complete at exact commit
`3c5f2e9b38b752594a68d46eaf4c60b8da3738f0`, tree
`f0eb52f15dd5f4bde7d8ba6ee4e7a3c897bf1d24`, with sole parent
`e101690bc351d92cc6b24a46cb5bc30f00bd6df0`. The commit contains exactly 37
owned paths: 30 modifications and seven additions, with 2,194 insertions and
305 deletions.

The default path, explicit compatibility, plan-discovery, cleanup-containment,
source-identity, documentation, and packaged-wheel requirements passed on both
Python 3.11 and 3.13. The linked evidence records the exact validation and
artifact identities. Independent review is `pass` and found no remaining
correctness, containment, compatibility, or documentation blocker.

Durable repository effects are limited to the isolated worktree/branch and its
bounded implementation and closure-record commits. Local validation also used
isolated temporary homes, build directories, and dependency caches. One early
test run created only an empty mode-`0700` `/Users/crlough/.buoy` boundary;
after independent empty-directory verification it was removed with an
empty-directory-only operation, restoring the initially absent path. No
descendant, database, plan, content, credential, or existing project asset was
created or changed there.

The task did not integrate into `develop` or `main`, mutate old project assets,
install the global tool, access credentials, call a provider/model, publish a
package, or alter tags, Releases, protection, or remote content. Branch push
and one ordinary draft-PR handoff remain authorized follow-up effects for owner
review; they grant no self-integration authority.
