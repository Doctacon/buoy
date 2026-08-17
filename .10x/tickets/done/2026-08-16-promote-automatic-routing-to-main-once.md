Status: done
Created: 2026-08-16
Updated: 2026-08-16
Decision: .10x/decisions/one-time-automatic-routing-main-promotion.md
Evidence: .10x/evidence/2026-08-16-automatic-routing-main-promotion.md
Authority-Review: .10x/reviews/2026-08-16-automatic-routing-main-promotion-authority-review.md
Review: .10x/reviews/2026-08-16-automatic-routing-main-promotion-review.md

# Promote Automatic Routing to Main Once

## Outcome

Honor the user's explicit request to deliver the completed automatic-routing
work through `develop` and then `main`: first integrate this bounded authority
record set normally, then promote exact reviewed `develop` through one
same-repository, seven-check, independently reviewed merge-commit PR while
publication stays paused.

## Phase 1: integrate release authority normally

1. Begin the isolated branch
   `work/authorize-automatic-routing-main-promotion` at exact current develop
   `D0 = 4abb931e9a6bd15040287e84dc68bf502e0fea9e`; require current main still
   equals `M = 0db802ec1a895f289c7600b19c80603986839873`.
2. Add only the governing one-time decision, this executable ticket, provisional
   evidence, and the independent authority review. Do not edit source, tests,
   README, dependencies, lock, workflows, instructions, or active general
   policy.
3. Validate the exact four-record allowlist, links/statuses, source policy,
   lock, unchanged executable surface, and diff hygiene.
4. Push only the task branch. Open one ordinary PR to `develop`, require exact-
   head `Python 3.11`, `Python 3.13`, and `Build distributions` success plus
   independent authority review, and use ordinary squash integration.
5. Only after that integration, fetch again and bind exact `origin/develop` as
   `D`. Record its commit, parent, and tree. Do not open a release PR before the
   authority records are present on `D`.

## Phase 2: bind and review the release candidate

1. Require `origin/main == M`, `origin/develop == D`, and `M` to be an ancestor
   of `D`. Require the complete intended routing/reader/governance tree and the
   newcomer README to be present; source validation must report valid active
   routing receipts.
2. Require read-only `git merge-tree --write-tree M D` to succeed with exact
   output `tree(D)`, and inspect the complete `M..D` release diff and diff
   hygiene. Bind the fresh absent-protection/ruleset and tag/Release
   inventories without changing them.
3. Open at most one pull request in `Doctacon/buoy` whose exact head is the
   same-repository branch `develop` at `D` and whose exact base is branch
   `main` at `M`. Do not use a release branch or fork.
4. Bind GitHub's prospective merge commit `P`; require ordered parents `[M,D]`
   and `tree(P) == tree(D)`. Any base/head drift invalidates `P` and stops the
   operation until the exact candidate is independently reviewed again.
5. Require all seven exact candidate checks to succeed:
   - `CI / Python 3.11`;
   - `CI / Python 3.13`;
   - `CI / Build distributions`;
   - `Release readiness / Policy`;
   - `Release readiness / Python 3.11`;
   - `Release readiness / Python 3.13`;
   - `Release readiness / Distribution`.
6. Obtain independent release review of exact `M`, `D`, `P`, the complete
   release diff, all seven workflow/run/job identities, mergeability,
   discussion state, merge method, and every no-write exclusion. Preserve the
   verdict for
   `.10x/reviews/2026-08-16-automatic-routing-main-promotion-review.md` during
   post-merge closure; adding it before the merge would change `D` and
   invalidate the candidate.

## Phase 3: merge and verify

1. Immediately recheck refs, candidate, checks, independent verdict, and
   mergeability. A dedicated release session may then merge only with the
   merge-commit method, never squash or rebase.
2. Fetch and bind result `R`. Require ordered parents `[M,D]`,
   `tree(R) == tree(D) == tree(P)`, `origin/main == R`,
   `origin/develop == D`, both `M` and `D` as ancestors of `R`, and an empty
   `D..R` content diff.
3. Require exact-main `CI / Python 3.11`, `CI / Python 3.13`,
   `CI / Build distributions`, and `Release / Publication paused` to pass on
   `R`.
4. Freshly read branches, protection/rulesets, tags, and Releases. Require only
   the expected main merge to have changed hosted release state. Confirm zero
   provider requests/writes, zero migration or indexed-content operations,
   and no credential, publication, deployment, or protection mutation.

## Phase 4: durable closure

From exact post-release `develop == D`, use one ordinary records-only task to
add the independent release-review record, change shared evidence from
`provisional` to `recorded`, move this ticket to `.10x/tickets/done/`, and mark
the one-time decision superseded/consumed. That closure uses an ordinary squash
PR to `develop` only and grants no second main merge.

## Acceptance

- Phase 1 changes exactly four records and integrates by the ordinary reviewed,
  three-check squash flow before any release PR exists.
- Exact `M` remains unchanged; future `D` is bound only after Phase 1
  integration and remains unchanged through release integration.
- The release PR is exact same-repository `develop -> main`; `P` has exact
  parents `[M,D]` and the exact `D` tree.
- All seven exact checks and independent release review pass on the unchanged
  candidate before merge.
- Integration uses one merge commit `R` with parents `[M,D]` and the exact `D`
  tree; post-main CI and paused-publication validation pass.
- Final readback proves correct refs, topology, ancestry, empty content diff,
  unchanged protection/rulesets/tags/Releases, and zero provider/migration
  effects.
- Evidence and review close durably, the exception is consumed, and no current
  record grants another main merge or publication action.

## Validation commands and evidence

Phase 1 must run:

- `PYTHONDONTWRITEBYTECODE=1 uv run --locked --python 3.13 python
  scripts/release_automation.py validate-source`;
- `uv lock --check`;
- `git diff --check` plus exact four-path allowlist, link, status, and stale-
  authority audits;
- `git diff --exit-code D0 -- README.md AGENTS.md CHANGELOG.md src tests scripts
  pyproject.toml uv.lock .github .10x/specs
  .10x/decisions/release-publication-is-paused.md`.

Release execution must record fresh exact refs/trees/parents, merge-base and
divergence, `merge-tree` output, complete diff inventory, PR identity,
prospective merge SHA, all seven workflow/run/job/check conclusions,
independent review target and verdict, actual merge method/SHA/parents/tree,
post-main run/job identities, final refs/ancestry/divergence, and pre/post
hosted inventories. Every mismatch stops execution.

## External effects and exclusions

The user's explicit develop-then-main request authorizes the bounded branch,
ordinary authority PR, exact same-repository release PR, required hosted
checks/review, one merge-commit integration, and later ordinary closure PR.
It does not authorize this task session to open or merge either PR.

No direct or force push to `main` or `develop`, no force push anywhere,
protection or ruleset change, tag, GitHub Release, retained artifact, package
publication, deployment, provider request/write, routing-catalog migration,
indexed-content mutation, model inference, credential change, or unrelated
change is permitted.

## Progress

- 2026-08-16: Fresh local fetch bound exact `M` and `D0`; `M` is an ancestor
  of `D0` with divergence `0` main-only / `7` develop-only commits. The
  isolated authority worktree was created. No PR, main merge, protection,
  publication, provider, migration, content, credential, tag, or Release
  operation occurred.
- 2026-08-16: The exact four-record authority head
  `43a59bf77a5e4f4a281c9799522b9bfb10dd56bb` passed independent authority
  review and PR #123 hosted CI. PR #123 squash-integrated as exact release
  head `D = 4dad7237baf69989b67270a4afb60d3c0444edfc`, with sole parent
  `4abb931e9a6bd15040287e84dc68bf502e0fea9e` and tree
  `a62ac8b774ca66aa4a8ae369daccbe38e0606531`.
- 2026-08-16: Independent release review passed exact PR #124 at base
  `M = 0db802ec1a895f289c7600b19c80603986839873`, head `D`, and prospective
  result `cedc0deb8940d87a9d7b9381f753d93e20c64733`. All seven required
  candidate jobs passed and hosted discussions were empty. The dedicated
  release session used merge-commit integration only.
- 2026-08-16: PR #124 merged as exact
  `R = 4d1efc458fd13b270bf84984ffeb550d5b24fd04`, with ordered parents `[M,D]`
  and exact `D` tree. Post-main CI and `Release / Publication paused` passed;
  refs, ancestry, empty `D..R` content diff, and unchanged hosted inventories
  were independently verified. The exception is consumed.

## Closure mapping

- Exact authority integration, PR #124 scope and check identities, candidate
  and merge topology, post-main checks, hosted inventories, and zero-effect
  boundaries are recorded in
  `.10x/evidence/2026-08-16-automatic-routing-main-promotion.md`.
- Independent premerge GO and post-merge PASS are recorded in
  `.10x/reviews/2026-08-16-automatic-routing-main-promotion-review.md`.
- Every acceptance criterion passed. The governing decision is superseded and
  consumed, publication remains paused, and no record in this closed task
  authorizes another main merge.

## Blockers

None.
