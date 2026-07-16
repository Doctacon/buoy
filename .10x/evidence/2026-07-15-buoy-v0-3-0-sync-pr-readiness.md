Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Relates-To: .10x/tickets/2026-07-15-promote-develop-to-main-for-v0-3-0.md

# Buoy v0.3.0 Protected Sync PR Readiness

## What was observed

After the update-branch failure recorded in `.10x/evidence/2026-07-15-buoy-v0-3-0-promotion-update-branch-blocker.md`, the user explicitly ratified a dedicated protection-compliant sync PR and authorized preparation only, not merge.

Fresh preflight observed the required unchanged refs:

- exact remote `develop`: `1441c142dae2f501fd8d7306ab3bf1a9db1532d2`;
- exact remote `main`: `1fa99431de85b9de435250f273919bf2d247d1fc`;
- divergence: one main-only commit and eighteen develop-only commits;
- no existing local/remote `release/v0.3.0-sync` branch and no sync PR;
- release PR #22 remained open at those exact develop/main refs.

A dedicated `release/v0.3.0-sync` branch was created from exact develop and exact main was merged into it with `--no-ff`. The resulting merge commit is:

`e32061ea33f4efe41cd4288e85083748fd0102fc`

Its ordered parents are exactly:

1. `1441c142dae2f501fd8d7306ab3bf1a9db1532d2` — release-prepared develop;
2. `1fa99431de85b9de435250f273919bf2d247d1fc` — current main release merge.

Both commits are ancestors of the sync head. `git diff --exit-code 1441c142..e32061e` and `git diff --check` passed, proving the sync tree is byte-for-byte identical to release-prepared develop. Project and module versions remained exactly 0.3.0.

Protected sync PR #23 was opened:

- URL: `https://github.com/Doctacon/buoy-search/pull/23`;
- base: `develop` at `1441c142dae2f501fd8d7306ab3bf1a9db1532d2`;
- head: `release/v0.3.0-sync` at `e32061ea33f4efe41cd4288e85083748fd0102fc`;
- state: `OPEN`;
- mergeability: `MERGEABLE` / `CLEAN`;
- Python 3.11: success, `https://github.com/Doctacon/buoy-search/actions/runs/29537212668/job/87751253365`;
- Python 3.13: success, `https://github.com/Doctacon/buoy-search/actions/runs/29537212668/job/87751253415`;
- Build distributions: success, `https://github.com/Doctacon/buoy-search/actions/runs/29537212668/job/87751374200`.

Post-check ref verification confirmed remote main and develop remained at their exact preflight commits and the sync branch remained at the reviewed merge commit. Neither PR #23 nor release PR #22 was merged.

## Procedure

1. Re-fetched main/develop and compared local and GitHub API refs to the exact user-ratified commits; stopped-on-drift assertions passed.
2. Inspected a prospective merge for conflict markers.
3. Created `release/v0.3.0-sync` from exact develop in a dedicated worktree.
4. Ran `git merge --no-ff <exact-main> -m "Merge main ancestry for Buoy v0.3.0 release"`.
5. Verified exact ordered parents, ancestor relationships, unchanged tree/content, diff hygiene, and 0.3.0 project/module versions.
6. Re-read exact remote main/develop immediately before pushing the sync branch.
7. Pushed only the dedicated branch and opened PR #23 to develop with ancestry-only scope and an explicit merge-commit requirement.
8. Waited for all three required checks and verified `OPEN`, `MERGEABLE`, `CLEAN`, exact head/base, and unchanged protected refs.
9. Stopped before any PR merge as authorized.

## What this supports or challenges

This supports that PR #23 is a protection-compliant, content-neutral ancestry sync ready for independent review. If later merged to develop with a merge commit, exact current main will become an ancestor without changing the release-prepared tree.

It does not supersede or erase the prior update-branch failure; that evidence explains why the separately ratified sync PR exists.

## External-side-effect boundary

Successful mutations were limited to pushing `release/v0.3.0-sync` and opening PR #23. No develop/main mutation, sync/release PR merge, direct push, rebase, squash, force push, protection change, tag, environment approval, GitHub Release, PyPI operation, source-content change, credential output, or Turbopuffer operation occurred.

## Limits

PR #23 has not yet received the required independent review or been merged. PR #22 must not be merged before the sync PR lands with a merge commit, develop/check freshness is re-established, and the exact release diff is independently reviewed.
