Status: recorded
Created: 2026-07-21
Updated: 2026-07-21
Relates-To: .10x/tickets/done/2026-07-21-promote-develop-to-main-for-v0-4-0.md, .10x/tickets/done/2026-07-21-buoy-v0-4-0-release-plan.md

# Buoy v0.4.0 Ancestry Sync Readiness

## What was observed

After reviewed candidate PR #82 integrated, exact release-ready `develop` was `47a0c33c412062f6467b1858e411179bfca60dcf`; current `main` was `820b8abba4308481eace728203d98f3365154956`. PR #80 conflicted because current main ancestry was absent from develop.

Dedicated branch `work/sync-main-v0-4-release` began at exact release-ready develop and created content-neutral merge commit `1abd9f587d3e188fa19be11755c786d81df3d455` with exact parents:

1. release-ready develop `47a0c33c412062f6467b1858e411179bfca60dcf`;
2. current main `820b8abba4308481eace728203d98f3365154956`.

The release-ready develop tree and ancestry merge tree are both `4c6395c330bb14ab75012d4b82c78f8b9a739aa8`. The merge imported ancestry only and no content from stale main.

## Procedure

- Fetched exact remote `main` and `develop`.
- Created the dedicated work branch from remote develop.
- Used Git's `ours` merge strategy with `--no-ff` to create a true two-parent merge commit while retaining exact develop content.
- Asserted both exact parent identities and exact tree equality immediately after the merge.
- Added only this durable readiness record and ticket progress after the content-neutral merge commit.

## What this supports

This supports opening a protected sync PR to `develop`. It does not itself prove hosted checks, PR mergeability, independent review, sync integration, PR #80 readiness, main promotion, or release publication.

## Limits and side effects

The only remote mutation permitted next is pushing this bounded work branch and opening its PR. No direct push to `main` or `develop`, protection change, tag, Release, PyPI, Turbopuffer/provider operation, user-state mutation, or product-service call occurred.
