Status: recorded
Created: 2026-07-21
Updated: 2026-07-21
Target: PR #85 at `35cf2d6e4da48a5e84c7f97d9e81e8f13950b504`
Verdict: concerns

# Buoy v0.4.0 Main Promotion Readiness Review

## Findings

Independent review confirmed:

- current main `820b8abba4308481eace728203d98f3365154956` is an ancestor of candidate develop `35cf2d6e4da48a5e84c7f97d9e81e8f13950b504`, with divergence `0/59`;
- candidate source outside `.10x/**` is byte-identical to the independently reviewed PR #82 candidate integration;
- version metadata is consistently 0.4.0, direct runtime pins include `transformers==5.12.1` and `scrapling[fetchers]==0.4.9`, and the pending changelog is coherent;
- PR #85 is current, conflict-free, mergeable, and passed exact-head pull-request and develop-push Python 3.11, Python 3.13, and distribution checks;
- no v0.4.0 tag, GitHub Release, v0.4 release workflow run, or PyPI 0.4.0 distribution exists;
- merge-commit topology is otherwise eligible, with expected parents prior main then exact develop; squash/rebase remain prohibited.

## Blocking concern

Hosted `main` protection retains `require_last_push_approval=true`. PR #85 has no reviews and the latest push actor is `Doctacon`. An eligible reviewer other than that latest pusher must approve the final current head. This review does not fabricate or satisfy that GitHub approval.

## Additional correction

Review found three durable citations used a nonexistent abbreviated expansion `278400909a71...`; the actual repaired PR #82 commit is `278400909596b5644431bd03fe526e600153f152`. This record-only follow-up repairs those exact citations before final-head approval.

## Verdict

Content, ancestry, versions, CI, and merge-commit topology pass. Promotion remains mechanically blocked until the final replacement release-PR head passes CI and receives the eligible last-push approval required by retained main protection.

## Residual risk

No merge, tag, Release, publication, or live product operation occurred. Main force-push capability remains enabled by user decision but is not authorized for this release.
