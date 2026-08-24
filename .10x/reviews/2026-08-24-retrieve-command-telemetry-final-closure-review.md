Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Target: 049a4ac4149923f4f6592840534c929532262044
Verdict: fail

# Retrieve Command Telemetry Final Closure Review

## Target

Fresh independent read-only closure review covered exact draft PR #145 head
`049a4ac4149923f4f6592840534c929532262044`, exact base
`3eabedd6b1e2c60a2a8be2489327b014d04130fc`, all governing and terminal
records, current source/tests/workflow, failed run `32761209125`, repaired local
validation, and successful run `32764801426`.

## Findings

### Blocker: literal task-head Hatch-VCS evidence was not produced

The successful check suite is associated with exact PR head `049a4ac` and base
`3eabedd6`, but all jobs checked out synthetic PR merge commit
`848b6ec1a9c91873e4299bf3e0e1ce6bdb8c99a6`. Hatch-VCS therefore built,
installed, and smoked `buoy_search-0.5.2.dev109+g848b6ec1a`, not an artifact
whose generated version identifies `049a4ac`.

The run proves the exact candidate and base work as a merged tree. It did not
satisfy the then-active literal exact-PR-head package-identity requirement.
Closure was correctly blocked pending either a head-checkout run or explicit
contract supersession.

### Significant: successful hosted evidence was not durable

At review time, no `.10x` record named current head `049a4ac`, successful run
`32764801426`, its job IDs, synthetic checkout identity, generated version, raw
artifact hashes, or its resolution relationship to failed run `32761209125`.

### Significant: integration state remained pending

The ticket remained active and dedicated integration was incomplete. Raw
artifacts established the PR association and run-time synthetic merge, but a
dedicated integrator still had to obtain fresh current head/base, state,
mergeability, and check information immediately before merge.

## Correct findings

- Successful run `32764801426` contains exactly three successful jobs: Python
  3.11 `97551744742`, Python 3.13 `97551745084`, and Build distributions
  `97552647317`.
- Both hosted test jobs ran unfiltered discovery and passed all 1,076 tests,
  including the repaired timing test.
- The prior 500 ms hosted failure remains accurately recorded and is resolved
  functionally by the warm-up/2,000 ms repair without weakening bounds or
  attribution assertions.
- Local repair evidence passed unfiltered dual-runtime suites, six concurrent
  timing repetitions, focused telemetry, lock, Ruff, compilation, ranking, C6,
  diff, and source identities.
- Production source and schema-v3 routing authority retain accepted identities.
- Every material retrieve-command and storage/migration scenario remains mapped
  to unchanged implementation and passing tests; no active-spec drift or weaker
  semantic assertion was found.
- Cleanup tickets and record references remain coherent, with all three live
  dynamic-version tests retained.

## Verdict

**Fail.** This review controls closure at target `049a4ac`. The user subsequently
ratified the merge-ref-then-final-squash contract recorded in
`.10x/decisions/buoy-validates-pr-merge-ref-and-final-squash-commit.md`. That
contract decision does not retroactively turn this verdict into a pass. Hosted
evidence and ticket language must be corrected, then a fresh independent
rereview must assess the new authority before closure.

## Residual risk

- Pull-request checks produce merge-ref, not task-head, package metadata.
- Final squash-commit package identity remains unknown until post-merge
  `develop` CI.
- Current PR state must be refreshed by the dedicated integrator.
- Local crash evidence remains deterministic macOS injection rather than
  hardware-power-loss or cross-filesystem evidence.
- Deleted release validators remain intentionally unreplaced.
