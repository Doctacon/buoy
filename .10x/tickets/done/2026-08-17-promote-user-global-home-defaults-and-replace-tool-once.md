Status: done
Created: 2026-08-17
Updated: 2026-08-17
Decision: .10x/decisions/one-time-user-global-home-main-promotion-and-tool-replacement.md
Evidence: .10x/evidence/2026-08-17-user-global-home-main-promotion-and-tool-replacement.md
Authority-Review: .10x/reviews/2026-08-17-user-global-home-main-promotion-authority-review.md
Review: .10x/reviews/2026-08-17-user-global-home-main-promotion-and-tool-replacement-review.md

# Promote User-Global-Home Defaults and Replace the Tool Once

## Outcome

Carry the reviewed forward-only `~/.buoy` defaults from exact `develop` through
one governed `main` merge, then replace only the user-global `buoy-search` uv
tool with the exact-main build and verify it, while publication and every live
provider/content operation remain paused.

## Fixed starting identities

- implementation integration: `D0 = cd3f1bef4c9c4856c727f4891512278eafd82841`;
- `parent(D0) = e101690bc351d92cc6b24a46cb5bc30f00bd6df0`;
- `tree(D0) = 8c6790ac8be55601b25c7b79aad17994b790a533`;
- current main: `M = 7f7ddfe245e1e5b57946eb6ac10dcc01358559fc`;
- merge base: `B = e101690bc351d92cc6b24a46cb5bc30f00bd6df0`;
- `tree(M) = tree(B) = 98cb3e56af4d867987d4e23f279f68fcf912e666`;
- PR #129 head: `c1b76f329496358198af6a9af1a80a095418af1d`;
- PR #129 exact-head CI run `32039880977`, successful jobs Python 3.11
  `95417652397`, Python 3.13 `95417652864`, and Build distributions
  `95417935994`.

## Phase 1: integrate this authority normally

1. Start the isolated authority branch at exact `D0` and require `main == M`.
2. Add exactly the accepted decision, this active ticket, provisional evidence,
   and independent PASS authority review. Change no source, tests, docs, specs,
   policy, dependency, lock, workflow, or prior task record.
3. Validate links/statuses, exact four-path scope, source policy, lock, diff
   hygiene, and zero executable-surface change.
4. Open one ordinary PR to exact `develop@D0`. Require exact-head
   `CI / Python 3.11`, `CI / Python 3.13`, and
   `CI / Build distributions`, empty blocking discussion, mergeability, and
   independent authority review; then squash only.
5. Fetch and bind the actual single-parent squash result as final release head
   `D`. Do not write `D`, authority-PR check IDs, or its squash result into the
   checked candidate before they exist; collect them as read-only handoff facts.

## Phase 2: release candidate and merge

1. Re-fetch and require unchanged `M`, exact `D`, exact `B`,
   `tree(M) == tree(B)`, and an empty `B..M` diff. Require `D` to descend from
   exact `D0` through only the Phase-1 authority integration.
2. Require `git merge-tree --write-tree M D` to succeed with exact `tree(D)`.
   Audit the complete `M..D` path/content diff and unchanged protection,
   ruleset, tag, and GitHub Release inventories.
3. Open at most one same-repository draft PR with base `main@M` and head
   `develop@D`. Bind prospective `P`; require ordered parents `[M,D]` and
   `tree(P) == tree(D)`.
4. Require all seven exact-head jobs:
   - `CI / Python 3.11`;
   - `CI / Python 3.13`;
   - `CI / Build distributions`;
   - `Release readiness / Policy`;
   - `Release readiness / Python 3.11`;
   - `Release readiness / Python 3.13`;
   - `Release readiness / Distribution`.
5. Require independent release GO on exact refs, prospective topology, complete
   scope, check/run/job identities, discussions, mergeability, merge method,
   and exclusions. Mark ready, re-fetch, and merge with method `merge` only.
6. Bind actual `R`; require ordered parents `[M,D]`, exact `tree(D)`,
   `main == R`, `develop == D`, and an empty `D..R` content diff.
7. Require exact-main `CI / Python 3.11`, `CI / Python 3.13`,
   `CI / Build distributions`, and `Release / Publication paused` success,
   plus unchanged protection/rulesets/tags/Releases.

## Phase 3: exact-main local tool replacement

1. Use a clean detached worktree at exact `R`. Validate source, lock,
   compilation, build, distribution contents, and an isolated-home clean-wheel
   smoke without provider credentials, model/network access, or real-home
   application-state creation.
2. Record the existing global baseline before mutation: executable/link target,
   uv-tool package, Python runtime, version, direct-url/source identity, and
   active-routing CLI hash. Require the current baseline to remain the expected
   pre-release main build; any mismatch stops for review.
3. Build one exact-R wheel, record its name/size/SHA-256 and installed-source
   identities, and bind a locked Python 3.13 runtime-constraints artifact and
   digest. Obtain independent `INSTALL-GO` on those exact facts and the precise
   one-shot command.
4. Invoke `uv tool install --force` exactly once for `buoy-search`, using only
   the reviewed exact-R artifact and runtime constraints. The invocation itself
   consumes installation authority. Do not retry, uninstall, or roll back on
   failure or uncertainty.
5. Verify the global `buoy` executable, uv-tool inventory, Python runtime,
   package/direct-url or local-artifact binding, dynamic version, source-module
   hashes, active routing receipt, version/help exits, and isolated-home path
   defaults. Verify other uv tools are unchanged and the real `~/.buoy` asset
   path remains in its pre-install state.

## Phase 4: durable closure

From exact post-release `develop == D`, create one ordinary records-only branch:
mark the decision superseded/consumed, move this ticket to `tickets/done`, set
evidence recorded, time-scope/update the authority review, and add the final
execution review with release and install PASS. Integrate that five-logical-
record closure to `develop` by the ordinary exact-head three-check squash flow.
It grants no second main merge or tool replacement; exact `main@R` necessarily
retains the pre-closure record headers as historical bytes.

## Validation and stop gates

- exact Phase-1/Phase-4 allowlists, links, statuses, stale-path scans, and
  `git diff --check`;
- `PYTHONDONTWRITEBYTECODE=1 uv run --locked --python 3.13 python
  scripts/release_automation.py validate-source` and `uv lock --check`;
- zero Phase-1/Phase-4 diff across source, tests, scripts, README, docs,
  CHANGELOG, specs, dependencies, lock, and workflows;
- fresh exact refs/trees/parents/merge-base/merge-tree and hosted identities at
  every state-changing boundary;
- stop on any drift, failing/pending check, discussion blocker, lost
  mergeability, wrong merge/install method, artifact mismatch, real-home asset
  mutation, or uncertain install result.

## External effects and exclusions

Only the effects explicitly enumerated by the governing decision are allowed.
In particular: no branch deletion; no direct/force long-lived-branch push; no
tag, GitHub Release, package publication, provider/catalog/content request or
mutation, model inference, credential access, deployment, protection/ruleset
change, old-asset migration/backfill/delete, real `~/.buoy` plan/state creation,
or mutation of any uv tool other than `buoy-search`.

## Progress

- 2026-08-17: PR #129 passed independent review and exact-head CI, was marked
  ready, and squash-integrated as exact `D0`. Fresh readback proved its sole
  parent, reviewed tree, unchanged `main`, and preserved source branch.
- 2026-08-17: Fresh topology audit bound exact `M`, `D0`, and `B`; divergence
  is two main-only merge commits and one develop-only squash commit. Although
  neither tip is an ancestor of the other, `tree(M) == tree(B)` and the exact
  merge construction equals `tree(D0)`, so the candidate is content-coherent.
- 2026-08-17: The four-record authority branch ended at exact
  `266a5f586f939c044fe3fe8a40243bbfd9a8a7b7`. PR #130 passed its exact-head
  three-job CI and squash-integrated as final release head
  `D = 74f80d6a32b4b9ae4556e1af4cd06b628d9474e6`, with sole parent `D0` and
  tree `f43548540aa203013164164648549795c49dd44b`.
- 2026-08-17: Independent release review passed exact same-repository PR #131
  at base `M`, head `D`, and prospective result
  `P = c02f5d7ec88821450517a79ffa2a117b8710114f`. All seven exact-head jobs
  passed and hosted discussions were empty. The dedicated release session used
  merge-commit integration only.
- 2026-08-17: PR #131 merged as exact
  `R = 78ffbf796d4fbe1bee8de0544fa018c8da512698`, with ordered parents `[M,D]`
  and exact `D` tree. Exact-main CI and `Release / Publication paused` passed;
  refs, topology, empty `D..R` content diff, and unchanged hosted inventories
  were independently verified.
- 2026-08-17: Two independent install reviews issued `INSTALL-GO` for the
  exact command digest and artifact set. The command was invoked exactly once,
  exited zero, installed `buoy-search 0.5.2.dev36+g78ffbf796`, and required no
  retry, rollback, uninstall, or fallback. Post-install review passed the
  executable, environment, receipt, source hashes, path defaults, other-tool,
  and real-home invariants.

## Closure mapping

- Exact PR #130 and PR #131 identities, check runs and jobs, merge topology,
  post-main state, artifact preparation, package-network accounting, one-shot
  installation, hash-enforcement caveat, installed identities, and zero-effect
  boundaries are recorded in
  `.10x/evidence/2026-08-17-user-global-home-main-promotion-and-tool-replacement.md`.
- Independent final release/install verification and the final PASS are
  recorded in
  `.10x/reviews/2026-08-17-user-global-home-main-promotion-and-tool-replacement-review.md`.
- Every acceptance criterion passed. The governing decision is superseded and
  consumed, publication remains paused, and no closed-task record authorizes
  another main merge or tool replacement.

## Blockers

None.
