Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Target: https://github.com/Doctacon/buoy-search/pull/53 at 7f3225b8c964ffa035ad0c8d6f6679d47094bdd1
Verdict: pass

# Node.js 24 GitHub Actions Review

## Target

PR [#53](https://github.com/Doctacon/buoy-search/pull/53), base `develop` at `5647cc6f08eeaf6319ac53f62b1bf136d0a67d80`, reviewed head `7f3225b8c964ffa035ad0c8d6f6679d47094bdd1`.

## Findings

No blockers.

- The reviewed workflow/source diff changes only the `actions/checkout` and `astral-sh/setup-uv` full-SHA pins, their identifying major comments, and the static test's expected major values. CI/release triggers, permissions, commands, matrices, action inputs, artifact handling, and the no-PyPI boundary are unchanged.
- `actions/checkout` release and tag `v5.0.1` resolve to `93cb6efe18208431cddfb8368fd83d5badbf9bfd` through GitHub's release/ref APIs and an independent upstream `git ls-remote` query. `action.yml` at that immutable commit declares `runs.using: node24`.
- `astral-sh/setup-uv` release and tag `v7.6.0` resolve to `37802adc94f370d6bfd71619e3f0bf239e1f3b78` through GitHub's release/ref APIs and an independent upstream `git ls-remote` query. `action.yml` at that immutable commit declares `runs.using: "node24"`.
- The focused release-automation suite independently passed all 11 tests, including full-SHA/comment identification, read-only locked CI matrix behavior, and tag-only GitHub release/no-PyPI behavior. Existing evidence records 422 passing full tests on each of Python 3.11 and 3.13 plus a successful wheel/sdist build.
- Exact-head hosted CI run [`29713376040`](https://github.com/Doctacon/buoy-search/actions/runs/29713376040) completed successfully for `7f3225b8c964ffa035ad0c8d6f6679d47094bdd1`: Python 3.11 check run `88261229854`, Python 3.13 check run `88261229820`, and Build distributions check run `88261311384` all passed. Each exact check-run annotation endpoint returned `[]` (`count=0`), so no Node.js 20 action-runtime deprecation annotation was present.

## Verdict

Pass. The ticket's acceptance criteria remain satisfied and `.10x/tickets/done/2026-07-14-update-node24-github-actions.md` may close. PR #53 remains open and unmerged.

## Residual risk

The hosted run exercises the pull-request CI workflow, not the tag-only release workflow. Creating a tag or release solely for review would violate the ticket's explicit exclusions. This is a non-blocking residual because the release workflow uses the same reviewed immutable action commits as CI with unchanged release-specific inputs, release semantics are statically covered, and the action revisions executed successfully without annotations in exact-head CI. The next authorized release remains the first hosted release-path observation.
