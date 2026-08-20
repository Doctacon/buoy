Status: superseded
Created: 2026-08-19
Updated: 2026-08-19
Ticket: .10x/tickets/2026-08-19-ship-buoy-v0-6-0.md
Evidence: .10x/evidence/2026-08-19-buoy-v0-6-0-github-release.md
Decision: .10x/decisions/annotated-tag-triggered-github-releases.md
Specification: .10x/specs/annotated-tag-triggered-github-release.md
Superseded-By: .10x/reviews/2026-08-19-annotated-tag-release-workflow-smoke-repair-review.md

# Annotated-Tag Release Workflow Review

## Correction

This PASS is superseded only for its claim that the workflow clean-wheel smoke
was release-ready. Release PR #138 proved that both workflow assertions
expected bare `0.6.0`, while the governed argparse CLI prints `buoy 0.6.0`.
The failure happened after installation and before any main merge or release
write. All review findings about tests, artifacts, permissions, tags, Release
state, attestations, governance, and privacy remain valid for unchanged bytes.
Only the later bounded smoke-repair review may authorize renewed handoff.

Target: uncommitted release-preparation candidate based on exact
`develop@06708ce39e9b5e8c15ce6204c2af4e9c73334ade`.

## Scope reviewed

Independent review covered the reusable tag-triggered workflow, unchanged
read-only CI/readiness boundary, v0.6.0 changelog/README/security state,
generic release and distribution validators, documentation, accepted standing
authority, superseded unused manual records, active ticket/evidence, and every
changed path in the ticket.

The frozen critical SHA-256 values were:

- `.github/workflows/release.yml`:
  `051219535e0e2bba3a09e1e911b8c7f74e30c78007094dba21b9fc74d44c2654`;
- `.github/workflows/release-readiness.yml`:
  `5a9e41e4d1aab7dfad0ef5e892ea6d46bdf3018d294918c45a8a03b84950f153`;
- `scripts/release_automation.py`:
  `3b40c1020de291a36ef0bebf39f7c9aa41051356a334ba5829360350615f47de`;
- `tests/test_release_automation.py`:
  `223f1900ea8ecbd845838dc97bbef81e13a24170cf767f44be7df783d8a0c0cf`;
- `docs/releasing.md`:
  `dcad97c198c3b8c88f896609347c05e36d20d4cf77b55d0dcb71328aae027b85`.

## Findings

The workflow uses an annotated version tag as the human approval boundary,
runs the complete locked Python 3.11/3.13 suites before publication, validates
and clean-smokes the exact wheel/sdist pair, and separates read-only build work
from the only write-capable job. That job has exactly `contents: write`,
`id-token: write`, and `attestations: write`, does not check out or execute
repository code, and has no delete, replace, clobber, force, or PyPI path.

The workflow verifies tag type, exact message, peel, current-main identity,
release body, exact two asset names, API sizes/digests, numeric-ID downloads,
and build attestations before its only irreversible publish edit. It then
requires the same Release to be latest and immutable and re-verifies the tag,
downloads, and attestations. Exact published reruns are verification-only;
exact drafts may resume; mismatches fail closed.

One draft implementation tried to read the immutable-Releases repository
setting with `GITHUB_TOKEN`. Review rejected that because GitHub requires
repository Administration permission, which the workflow intentionally does
not receive. The final design requires owner-admin verification before the tag
and proves `immutable=true` after publication. This preserves least privilege.

Governance review confirmed a coherent accepted decision, active spec, active
ticket, provisional evidence, superseded pause, and unused manual records
marked superseded before use. It also required the repository's ordinary
records-only post-run closure, without reintroducing bespoke release approval
or hosted mutation.

## Validation

- Actionlint passed all workflow files; YAML parsing and every embedded shell
  step passed syntax checks.
- Focused release automation passed 24 tests with ResourceWarning fatal.
- Full locked Python 3.11 and 3.13 suites each passed 1,033 tests with
  ResourceWarning fatal.
- Source, lock, ranking, C6, Python compilation, and diff-hygiene gates passed.
- Fresh exact-version build, distribution validation, and isolated clean-wheel
  smoke passed; the evidence records the diagnostic artifact sizes/hashes.
- No tag, Release, asset, attestation, PyPI, provider/model/data, real-home,
  global-install, protection, force-push, or unrelated hosted effect occurred.

## Verdict

PASS. No correctness, supply-chain, permission-boundary, release-state,
packaging, governance, privacy, or scope blocker remains in the reviewed
candidate.

This review authorizes the bounded commit and ordinary task/release PR
handoffs. It does not by itself authorize a tag before exact reviewed main CI
and owner-admin immutable-Releases verification. The owner's accepted standing
decision authorizes that later tag and the workflow's narrowly scoped writes
when those gates pass.
