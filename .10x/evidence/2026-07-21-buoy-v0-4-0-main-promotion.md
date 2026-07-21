Status: recorded
Created: 2026-07-21
Updated: 2026-07-21
Relates-To: .10x/tickets/done/2026-07-21-promote-develop-to-main-for-v0-4-0.md, .10x/tickets/done/2026-07-21-buoy-v0-4-0-release-plan.md

# Buoy v0.4.0 Main Promotion

## What was observed

Release PR #85 merged reviewed `develop` head `e702aee115a57b5057b8d5d5917b260e6417c74d` into `main` on 2026-07-21 at `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`.

The user selected GitHub's squash method rather than the governed merge-commit method. The result has one parent, prior main `820b8abba4308481eace728203d98f3365154956`, but its tree `7de04d70c442de5fb5051cd6ceafda5b4c39c285` is exactly equal to reviewed develop's tree. After the mismatch was named, the user explicitly selected `Accept and release (Recommended)`, ratifying `c49dc05` as v0.4.0 release authority and requiring a post-release ancestry sync.

Exact-main CI run `29851219914` passed Python 3.11, Python 3.13, both validators, complete tests/documentation checks, and Build distributions.

## Review and prior gates

- Candidate PR #82 passed repaired artifact-level independent review and integration.
- PR #83 integrated prior main ancestry into develop through a content-neutral two-parent merge.
- PR #84 recorded user-retained branch-specific protection settings.
- PR #85 content/ancestry/version/CI readiness passed independent review; retained last-push approval was satisfied by the user's hosted merge action.
- PR #86 repaired exact SHA citations and recorded final-head readiness before the release merge.

## Post-release ancestry repair

Dedicated branch `work/record-v0-4-release` began at develop `e702aee115a57b5057b8d5d5917b260e6417c74d` and created content-neutral merge commit `644867f9ef8a26b137e0aabf69cb0cf4f66601a3` with exact second parent released main `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`. The merge tree remains exact `7de04d70c442de5fb5051cd6ceafda5b4c39c285`. Once its protected PR integrates, released main will be an ancestor of develop for future work without changing release content.

## What this supports

This supports technical completion of the v0.4.0 main promotion under the user's explicit squash-topology exception and the bounded post-release ancestry repair.

## Limits and side effects

The release PR changed `main` and exact-main CI read source. No force push, direct push, protection mutation, tag overwrite, PyPI publication, Turbopuffer/provider call, namespace operation, or user-state mutation occurred. Tag/Release effects are recorded separately in `.10x/evidence/2026-07-21-buoy-v0-4-0-github-release.md`.
