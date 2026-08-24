Status: recorded
Created: 2026-08-23
Updated: 2026-08-23
Target: 33a6d8eb60319f074ee0a5139957cd8353b174c0
Verdict: pass

# Stale CI Release-Automation Call Implementation Review

## Target

Fresh independent read-only review covered workflow implementation
`33a6d8eb60319f074ee0a5139957cd8353b174c0`, tree
`6fe239332c866613acd7185df1124744639fd1e7`, evidence HEAD
`d25a3dfc4edcd7c07b8fabd1ea1465560170c68c`, base `develop@0c669c5e`,
the complete pre/post workflow, cleanup history, aggregate stale-test repair,
package/test configuration, and raw local validation artifacts.

## Findings

No blocker, significant, minor, nitpick, hidden-widening, or test-weakening
implementation finding was found. The implementation is safe to push as a draft
PR for hosted exact-head CI.

Workflow commit `33a6d8eb` removes exactly two complete lines and changes no
other path:

- deleted `scripts/release_automation.py validate-source` invocation; and
- deleted `scripts/release_automation.py validate-distribution dist` invocation.

The resulting workflow retains pull-request and `main`/`develop` push triggers,
read-only permission, concurrency, Python 3.11/3.13 matrix, pinned actions,
ranking/C6 validation, unfiltered tests, locked build, isolated wheel install,
CLI/module help, tokenizer, routing-canary, dataset, calibration, and conditional
active-routing assertions. Current workflows contain no reference to either
absent release script.

Raw structural comparison supports equivalence of workflow name, triggers,
permissions, concurrency, jobs, matrix, step order/names, action pins/inputs,
and every command except the two authorized deletions. Local dual-runtime tests,
validators, build, install, and smoke pass. The aggregate stale dynamic-version
repair is independently closed and reviewed.

The evidence truthfully enumerates the removed source/distribution invariants
and does not claim remaining checks replace them.

## Criterion assessment

| Criterion | Verdict |
| --- | --- |
| No absent release-script references | pass |
| Ranking and C6 checks remain | pass |
| Dual-runtime tests/build/install/smoke remain | pass locally |
| Workflow diff is exactly two deletions | pass |
| YAML/static/local validation | pass |
| Hosted exact-head CI | pending hosted gate |
| Unreplaced coverage disclosed | pass |

## Verdict

**Pass for implementation and draft-PR handoff.** Hosted exact-head CI remains
an acceptance gate rather than an implementation defect. This review does not
close the active ticket.

## Residual risk

- Hosted Ubuntu/action execution and exact-head dependency resolution remain
  unverified until PR CI passes.
- Local wheel installation was offline and cache-backed.
- Intentionally deleted release source/distribution invariants remain uncovered
  by explicit user choice.
- Raw artifacts are temporary, with durable hashes in evidence.
