Status: recorded
Created: 2026-08-16
Updated: 2026-08-16
Ticket: .10x/tickets/done/2026-08-16-promote-automatic-routing-to-main-once.md
Decision: .10x/decisions/one-time-automatic-routing-main-promotion.md
Authority-Review: .10x/reviews/2026-08-16-automatic-routing-main-promotion-authority-review.md
Review: .10x/reviews/2026-08-16-automatic-routing-main-promotion-review.md

# Automatic-Routing Main Promotion Evidence

## Pre-authority observation

Fresh local fetch before any record mutation bound:

- exact current main `M = 0db802ec1a895f289c7600b19c80603986839873`,
  with sole parent `059753a0cff756c531ec1b723747c85d22fc542d` and tree
  `1df8c48adc5d578dc274693e9aea2c8cf786a9f0`;
- exact current develop / authority-task base
  `D0 = 4abb931e9a6bd15040287e84dc68bf502e0fea9e`, with sole parent
  `33e7a52d85ed28a637090cedfa470c5ed9e8196b` and tree
  `04ce39472d3ee3989976063bd8040412148b4b9d`;
- exact merge base `M`; `M` is an ancestor of `D0`;
- `M...D0` divergence `0` main-only / `7` develop-only commits.

The `D0` tree includes the completed PR #117 ancestry repair and its consumed
closure, the reviewed empty-prototype remote-reader fix, the automatic-routing
implementation, and the exact newcomer README retained from `M`. This authority
task adds records only. Final release head `D` intentionally remains unbound
until the authority-record PR is independently reviewed, passes ordinary CI,
and squash-integrates into `develop`.

The user's conversation explicitly directed the completed routing work into
`develop` and then `main`. That request authorizes shaping this bounded release
authority, but it does not waive the repository's exact PR, CI, review,
merge-method, publication-pause, or no-provider/no-migration boundaries.

## Hosted and publication baseline

The integrated topology-closure evidence records a read-only GitHub observation
at `2026-08-17T05:04:33Z`: `main` and `develop` were unprotected,
`protection.enabled=false` for both, repository ruleset count was zero, six
existing tags and five non-draft/non-prerelease Releases were present, and
publication remained paused. This task has performed no hosted settings, tag,
Release, package, provider, migration, content, credential, or publication
operation. The release executor must freshly read and bind these inventories;
this historical checkpoint cannot substitute for execution-time readback.

## Recorded authority integration

The four-record authority branch completed at exact head
`43a59bf77a5e4f4a281c9799522b9bfb10dd56bb`. Same-repository PR #123 targeted
exact `develop` base
`4abb931e9a6bd15040287e84dc68bf502e0fea9e` from that exact head. GitHub
reported four changed files, 404 additions, zero deletions, and no comments,
hosted reviews, requested reviewers, or discussion blockers.

CI run `31998914467` passed all three exact-head jobs:

- `CI / Python 3.11`, job `95295477582`;
- `CI / Python 3.13`, job `95295477557`;
- `CI / Build distributions`, job `95295798883`.

Ordinary squash integration produced exact release head
`D = 4dad7237baf69989b67270a4afb60d3c0444edfc`, whose sole parent is
`4abb931e9a6bd15040287e84dc68bf502e0fea9e` and whose tree is
`a62ac8b774ca66aa4a8ae369daccbe38e0606531`. Exact release base
`M = 0db802ec1a895f289c7600b19c80603986839873` remained unchanged, is the merge
base and an ancestor of `D`, and `M...D` divergence was zero main-only / eight
develop-only commits.

## Recorded release candidate and independent GO

Same-repository PR #124 had exact base branch `main` at `M` and head branch
`develop` at `D`. GitHub reported 21 changed paths, 1,640 additions, and 42
deletions. Comments, hosted reviews, review requests, and review threads were
empty; the separately executed independent repository review was the required
behavioral review gate and was not submitted as a GitHub review.

The exact reviewed 21-path inventory was:

- `.10x/decisions/one-time-automatic-routing-main-promotion.md`;
- `.10x/decisions/one-time-pr-117-squash-topology-repair.md`;
- `.10x/evidence/2026-08-16-automatic-routing-main-promotion.md`;
- `.10x/evidence/2026-08-16-empty-remote-prototype-float-canonicalization.md`;
- `.10x/evidence/2026-08-16-pr-117-squash-topology-repair.md`;
- `.10x/reviews/2026-08-16-automatic-routing-main-promotion-authority-review.md`;
- `.10x/reviews/2026-08-16-empty-remote-prototype-float-canonicalization-review.md`;
- `.10x/reviews/2026-08-16-pr-117-squash-topology-governance-review.md`;
- `.10x/reviews/2026-08-16-pr-117-squash-topology-repair-review.md`;
- `.10x/specs/one-time-pr-117-squash-topology-repair.md`;
- `.10x/specs/pi-worktree-development-flow.md`;
- `.10x/specs/protected-github-branches.md`;
- `.10x/specs/remote-empty-prototype-float-canonicalization.md`;
- the then-active `.10x/tickets/` path named
  `2026-08-16-promote-automatic-routing-to-main-once.md`, now moved to the
  done-ticket path linked in this record;
- `.10x/tickets/done/2026-08-16-bridge-pr-117-squash-topology-once.md`;
- `.10x/tickets/done/2026-08-16-canonicalize-empty-remote-prototype-floats.md`;
- `.10x/tickets/done/2026-08-16-govern-pr-117-squash-topology-repair.md`;
- `AGENTS.md`;
- `CHANGELOG.md`;
- `src/buoy_search/remote_catalog.py`;
- `tests/test_remote_catalog.py`.

Prospective result
`P = cedc0deb8940d87a9d7b9381f753d93e20c64733` had exact ordered parents
`[M,D]` and exact tree `a62ac8b774ca66aa4a8ae369daccbe38e0606531`, equal to `tree(D)`.
Independent release review returned final GO on the unchanged refs, exact
candidate, complete path inventory, empty hosted discussions, merge-commit-only
method, and exclusion boundary after all seven required jobs succeeded:

- CI run `31999853685`:
  - `CI / Python 3.11`, job `95297998406`;
  - `CI / Python 3.13`, job `95297998286`;
  - `CI / Build distributions`, job `95298335924`;
- Release readiness run `31999853666`:
  - `Release readiness / Policy`, job `95297998387`;
  - `Release readiness / Python 3.11`, job `95297998309`;
  - `Release readiness / Python 3.13`, job `95297998391`;
  - `Release readiness / Distribution`, job `95298358423`.

## Recorded merge and post-main verification

PR #124 merged at `2026-08-17T06:07:18Z` using the merge-commit method as
exact result `R = 4d1efc458fd13b270bf84984ffeb550d5b24fd04`. `R` has exact ordered
parents `[M,D]` and tree
`a62ac8b774ca66aa4a8ae369daccbe38e0606531`, equal to `tree(D)` and
`tree(P)`. Fresh fetch and readback proved `origin/main == R`,
`origin/develop == D`, both `M` and `D` are ancestors of `R`, final divergence
is one main-only / zero develop-only commits, and the `D..R` content diff is
empty.

Exact-main CI run `32000356490` passed:

- `CI / Python 3.11`, job `95299359343`;
- `CI / Python 3.13`, job `95299359374`;
- `CI / Build distributions`, job `95299758263`.

Exact-main Release run `32000356516` also passed its sole read-only
`Release / Publication paused` job `95299359542`.

Fresh post-merge hosted readback found `main == R`, `develop == D`, both
branches `protected=false` with `protection.enabled=false`, and zero repository
rulesets. The tag inventory remained exactly:

- `v0.5.1` at `284b309a02546b13a63e709d9afe7f72c557b474`;
- `v0.5.0` at `c7a47a8565f578b9efcef9d23e072c05c98848d8`;
- `v0.4.0` at `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`;
- `v0.3.0` at `595d157177bd032c20cf6e6c0112ee6b43212a88`;
- `v0.2.1` at `0afde6643162fdedc00810152e226701aa1d38b1`;
- `v0.2.0` at `d846d2b2e965e7f62ff180442724d02705688a1a`.

The GitHub Release inventory remained exactly five non-draft,
non-prerelease Releases: `v0.5.1` (`369682440`), `v0.5.0` (`363582802`),
`v0.4.0` (`357504706`), `v0.3.0` (`355388511`), and `v0.2.1`
(`354036337`). Thus only the authorized `main` ref changed; protection,
rulesets, tags, Releases, and publication state were unchanged.

## External effects and consumption

The release performed only the authorized PR #124, read-only hosted checks and
independent review, and one merge commit on `main`. It made exactly zero
provider requests or writes and performed no routing-catalog migration,
indexed-content mutation, model inference, credential access/change,
deployment, package publication, tag or GitHub Release operation, retained
artifact operation, protection/ruleset mutation, or direct/force push.
Publication remained paused throughout.

This Phase-4 task changes only the five owned closure records and may push only
its ordinary task branch for later review and squash integration into
`develop`. The one-time release authority is consumed and grants no retry,
second main merge, or other future action.

Phase 4 integrates into `develop` only. Exact `main` result `R` therefore
physically retains the pre-closure `accepted`, `active`, and `provisional`
headers that were present in reviewed `D`; those bytes are a historical
snapshot, not current authority. Consumption triggered when `R` was created,
so the headers retained on `main` grant no retry, second merge, publication,
or other action.
