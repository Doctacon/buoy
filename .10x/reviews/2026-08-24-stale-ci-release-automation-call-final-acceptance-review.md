Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Target: 86f1c152be1c853cc7d389e55170d8473a815377
Verdict: pass

# Stale CI Release-Automation Call Final Acceptance Review

## Target

Fresh independent read-only acceptance review covered aggregate cleanup PR #144
at exact head `86f1c152be1c853cc7d389e55170d8473a815377`, workflow implementation
`33a6d8eb60319f074ee0a5139957cd8353b174c0`, base `develop@0c669c5e`, both
cleanup tickets/evidence/reviews, complete workflow and test diffs, and raw
hosted GitHub Actions run `32755450115`.

## Findings

No code, workflow, test, evidence, scope, graph, significant, minor, nitpick, or
test-weakening defect was found.

- Current workflows and scripts contain no reference to either absent release
  script.
- Ranking/C6 validation, unfiltered tests, distribution build, isolated wheel
  installation, CLI/module help, tokenizer, routing-canary, dataset, and active
  routing smoke remain.
- Workflow implementation removes exactly the two user-authorized dead
  invocations and nothing else.
- Three retained dynamic-version tests exercise live Hatch-VCS/package/module/
  CLI behavior; the deleted test exclusively targeted the deleted helper.
- Deleted source/distribution validation coverage is explicitly disclosed and
  is not represented as replaced.

Raw run `32755450115` is a successful pull-request event bound to exact head
`86f1c152be1c853cc7d389e55170d8473a815377`. Its check-run artifact contains
exactly three completed successful checks:

- Python 3.13 job `97521813969`;
- Python 3.11 job `97521814256`; and
- Build distributions job `97522805169`.

The hosted log shows both unfiltered 1,009-test suites, both ranking/C6 pairs,
distribution build, and clean-wheel smoke passing. GitHub synthesized and
checked out conflict-free merge commit `3da3ef5...` from exact head `86f1c152`
and base `0c669c5e` for the run.

## Criterion assessment

| Criterion | Verdict |
| --- | --- |
| No absent release-script references | pass |
| Ranking and C6 checks retained | pass |
| Dual-runtime tests/build/install/smoke retained | pass |
| Exact two-line workflow deletion | pass |
| YAML/static and hosted exact-head CI | pass |
| Deleted coverage disclosed as unreplaced | pass |
| Aggregate stale-test repair | pass |
| Record graph and retrospective | pass after mechanical closure in the next records commit |

## Verdict

**Pass.** Ticket closure, a final records-only exact-head CI rerun, and dedicated
squash integration are supported. Immediate merge before those mechanics is not
supported.

## Residual risk

- Intentionally deleted release source/distribution invariants remain uncovered
  by explicit user choice.
- Local validation was offline/cache-backed; hosted CI supplies the independent
  Ubuntu/action/dependency-resolution observation.
- Temporary raw logs may be removed; their hashes and canonical Actions URLs
  are durably recorded.
- The dedicated integrator must re-read current PR head/base, draft/open state,
  checks, and mergeability immediately before merging.
