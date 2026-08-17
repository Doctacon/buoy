Status: provisional
Created: 2026-08-17
Updated: 2026-08-17
Ticket: .10x/tickets/2026-08-17-promote-user-global-home-defaults-and-replace-tool-once.md
Decision: .10x/decisions/one-time-user-global-home-main-promotion-and-tool-replacement.md
Authority-Review: .10x/reviews/2026-08-17-user-global-home-main-promotion-authority-review.md

# User-Global-Home Main Promotion and Tool Replacement Evidence

## Authority trigger and completed prerequisite

The owner explicitly superseded the earlier stop-at-PR boundary and directed
the agent to merge passing pull requests, continue until the requested changes
are on `main`, and install the tool. This record does not interpret that request
as publication, provider, credential, migration, protection, direct-push, or
unrelated authority.

PR #129 integrated the reviewed implementation through the ordinary flow:

- base `develop = e101690bc351d92cc6b24a46cb5bc30f00bd6df0`;
- head `c1b76f329496358198af6a9af1a80a095418af1d`;
- exact-head CI run `32039880977` succeeded with Python 3.11 job
  `95417652397`, Python 3.13 job `95417652864`, and Build distributions job
  `95417935994`;
- GitHub comments, reviews, review requests, and threads were empty and the PR
  was mergeable;
- squash result `D0 = cd3f1bef4c9c4856c727f4891512278eafd82841`;
- `parent(D0) = e101690bc351d92cc6b24a46cb5bc30f00bd6df0`;
- `tree(D0) = 8c6790ac8be55601b25c7b79aad17994b790a533`, exactly the reviewed head tree.

Current release topology at this authority boundary is:

- `M = 7f7ddfe245e1e5b57946eb6ac10dcc01358559fc`;
- `B = merge-base(M,D0) = e101690bc351d92cc6b24a46cb5bc30f00bd6df0`;
- `tree(M) = tree(B) = 98cb3e56af4d867987d4e23f279f68fcf912e666`;
- divergence `M...D0` is two main-only / one develop-only commits;
- neither tip is an ancestor of the other;
- `B..M` has no content diff;
- read-only `merge-tree(M,D0)` is conflict-free and equals exact
  `tree(D0) = 8c6790ac8be55601b25c7b79aad17994b790a533`.

## Current installed baseline

Read-only observation before authority integration found:

- `/Users/crlough/.local/bin/buoy` is a symlink to
  `/Users/crlough/.local/share/uv/tools/buoy-search/bin/buoy`;
- uv `0.11.7` manages a healthy 104-package `buoy-search` environment on
  CPython `3.13.0`;
- `buoy --version` reports `0.5.2.dev33+g7f7ddfe24`;
- installed `direct_url.json` SHA-256 is
  `7d181c6d8d00e3d04682f95082ad93b062f47fdf18cbafb6b5a5e021f2908047`
  and binds both commit and requested revision to exact `M`;
- installed `buoy_search/cli.py` SHA-256 is the active receipt
  `92c49e943ed5918df7fe65294ff89717e2654a8e9d76317979b63198f1b98ee9`;
- installed `buoy_search/local_paths.py` is absent, as expected before this
  release; and
- `/Users/crlough/.buoy` is absent.

This is a preliminary baseline only. Every identity and the complete other-tool
inventory must be freshly rebound immediately before install.

## Pending evidence timing

Before Phase 1 integration, this checked candidate may durably bind only the
exact three pre-review record blobs, the independent authority verdict, local
validation, and fixed `M`/`D0`/`B` facts. The authority task commit, PR/check
identities, and its squash result do not exist yet; a read-only handoff must
collect them after integration and bind final `D` without rewriting the checked
release head.

Before the main merge, a read-only release handoff must collect and bind exact
`M`, `D`, `B`, prospective `P`, complete diff, all seven run/job conclusions,
hosted inventories, discussions, mergeability, and independent release GO.
Those facts must not be written into `D` before its merge. Afterward, read-only
post-main and install handoffs must bind actual `R`, its topology, exact-main
jobs, paused-publication job, final hosted inventories, exact build/artifact,
installed baseline, INSTALL-GO, one-shot invocation, and verification.

Phase 4 closure must add all those facts durably without changing the already
released `D` or `R`. Until then this record remains `provisional`, the ticket
remains active, and the authority is not reusable.

## Required zero-effect accounting

At this boundary there has been no tag, GitHub Release, package publication,
provider/catalog/content request or mutation, model inference, credential
access, protection/ruleset change, direct/force push, old-asset migration,
real `~/.buoy` state/plan creation, or global-tool mutation by this authority
task. PR #129 caused only its authorized task-branch/PR and squash integration
effects. Subsequent effects must be recorded phase by phase rather than rolled
into an invented all-history total.
