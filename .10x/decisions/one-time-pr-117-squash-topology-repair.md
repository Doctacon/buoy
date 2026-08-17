Status: superseded
Created: 2026-08-16
Updated: 2026-08-16

# One-Time PR #117 Squash-Topology Repair

## 2026-08-16 disposition

The exact repair completed through content-empty bridge PR #121 as integration
`33e7a52d85ed28a637090cedfa470c5ed9e8196b` and is consumed. Final `develop`
contains exact PR #117 main squash
`0db802ec1a895f289c7600b19c80603986839873` as an ancestor without any change
from the bound pre-bridge develop tree. This decision is retained as historical
context only and grants no current or recurring branch, merge-method, release,
provider, or publication authority.

## Context

The completed automatic-routing work reached `develop` as squash commit
`7e55f73bb6df428bddd24aa9db80039ba0809923`. PR #117 then promoted that work
to `main` with accidental one-parent squash commit
`0db802ec1a895f289c7600b19c80603986839873` (`M`) rather than the required
merge commit. The branches therefore contain equivalent reviewed routing work
on separate lineages. Current `develop` subsequently advanced to reader-fix
squash `fc867bebb541f06f116502798a08640df375a3dc` (`D0`); their exact merge base
is `b9d996250893974c11b4dc69ecd12fd99bf2e016`.

The trees are not yet suitable for a content-neutral ancestry bridge. `M`
retains the user's reviewed newcomer README and its three governing records,
while `D0` retains the older README and lacks those records. Conversely, `D0`
contains the seven reviewed empty-prototype reader-fix paths not yet on `M`.
Silently choosing either branch tree would discard reviewed content.

The historical v0.4 squash-topology exception is superseded, consumed, and
expressly non-repeatable. It provides no authority here. Active branch-flow
policy otherwise requires every `work/* -> develop` task to squash. Hosted
branch protection is intentionally absent under the user's retained choice, so
the CI, review, and merge-method gates below are behavioral rather than claims
of mechanical enforcement; this repair may not restore or change protection.

## Decision

Accept one new, exact, non-repeatable repair in two separately reviewed phases:

1. Through an ordinary squash-integrated task based on exact `D0`, restore only
   the four newcomer-README paths from exact `M` and integrate this decision,
   the exact repair specification, executable bridge ticket, provisional
   evidence, the truth update from stale mechanical-protection claims to the
   owner-retained absent hosted posture and behavioral gates, and the narrow
   bridge merge-method exception across the active branch/worktree-flow specs
   and root instructions. No ancestry changes in this phase.
2. After that ordinary integration, bind freshly fetched `develop` as `D` and
   require `main` still equal exact `M`. From `D`, create one content-neutral
   bridge commit with ordered parents `[D, M]` and tree byte-identical to `D`.
   Expose it through one pull request to `develop`; after exact-head hosted CI
   and independent topology review pass as behavioral gates, a dedicated
   integration session must merge that PR with a merge commit whose ordered
   parents are `[D, bridge]` and whose tree remains byte-identical to `D`.

The four restored paths must be exact `M` blobs. All other preexisting paths in
the governance candidate remain exact `D0` unless this task explicitly owns
their governance additions or the exact branch-policy truth/exception
amendment. The future bridge changes ancestry only.

The user's request for the newcomer-focused README and subsequent direction to
deliver the completed routing work through `develop` and then `main` authorizes
this bounded repair design. It does not waive review, CI, merge-method,
branch-role, or release-publication boundaries.

## Required stop conditions

Stop without bridge creation or integration if `origin/main` differs from `M`,
the post-governance `origin/develop` cannot be bound exactly, any imported blob
differs, the bridge tree differs from its first parent, the PR has a content
diff, an ordered parent differs, required CI/review is absent, or the host
cannot represent the exact pull-request/merge-commit topology. A new
observation and explicitly reviewed plan are required after any such drift.

## Consequences

The governance/content-alignment task remains an ordinary squash-integrated
task. The exact later ancestry bridge is the sole additional exception and must
use merge-commit integration; squash or rebase would discard `M` ancestry and
recreate the defect. Once final develop contains `M` as an ancestor with the
bound tree, the exception is consumed and grants no recurring sync authority.

A later `develop -> main` pull request remains a separate release-role action
and must use the repository-required merge commit. Automatic publication stays
paused. This decision authorizes no main merge, direct/force push, protection
mutation, tag, GitHub Release, package publication, provider call/write,
catalog migration, content-index mutation, credential change, or branch bypass.

## Alternatives rejected

- **Reuse the v0.4 exception:** its authority is consumed and pinned to a
  different exact main commit.
- **Squash the bridge PR:** preserves files but loses the ancestry being
  repaired.
- **Bridge current `D0` unchanged:** would later replace the reviewed newcomer
  README and remove its governing records from `main`.
- **Import all main content opportunistically:** broadens content authority and
  makes conflict resolution unauditable.
- **Rebase, force-push, or direct-push a long-lived branch:** rewrites shared
  history or bypasses the required review boundary.
