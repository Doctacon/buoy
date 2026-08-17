Status: provisional
Created: 2026-08-16
Updated: 2026-08-16
Ticket: .10x/tickets/2026-08-16-promote-automatic-routing-to-main-once.md
Decision: .10x/decisions/one-time-automatic-routing-main-promotion.md
Authority-Review: .10x/reviews/2026-08-16-automatic-routing-main-promotion-authority-review.md

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

## Pending authority and release evidence

Before Phase 1 integration, this record must add only the exact pre-review
scope/blobs, local validation, and independent authority-review target/verdict.
The task commit, authority PR, exact-head three-check identities, and squash
integration SHA/parent/tree cannot exist in the checked-in candidate. The
read-only post-integration handoff must collect those facts and use them to bind
future exact `D`; Phase 4 closure must add them durably without changing `D`
before the release.

Before release integration, the read-only release handoff and independent
review must collect and bind exact `M`, `D`, and prospective merge commit `P`;
parents/trees/ancestry/divergence; complete release diff inventory;
same-repository PR identity and mergeability; all seven exact workflow/run/job
identities and conclusions; fresh hosted inventories; and the independent
release-review target/verdict. These are mandatory behavioral merge gates but
must not be written into `D`; Phase 4 closure adds them durably afterward.

After integration, the read-only post-merge handoff must collect actual merge
result `R`, merge method, ordered parents/tree, final refs and
ancestry/divergence, empty `D..R` diff, exact-main CI and
`Release / Publication paused` identities, unchanged hosted inventories, and
the zero-provider/zero-migration/no-publication attestation. Phase 4 closure
must add those facts durably. Missing or mismatched pre-merge gates block the
merge; missing or mismatched post-merge facts block closure.

## External effects so far

At this pre-push evidence checkpoint, only the isolated local authority
worktree exists. The authorized task-branch push will be this task's sole
external effect. No pull request, long-lived-branch mutation, direct or force
push to `main` or `develop`, force push anywhere, protection/ruleset change,
tag, GitHub Release, retained artifact, package publication, deployment,
provider request/write, routing-catalog migration, indexed-content mutation,
model inference, or credential change has occurred or is authorized by this
task session.
