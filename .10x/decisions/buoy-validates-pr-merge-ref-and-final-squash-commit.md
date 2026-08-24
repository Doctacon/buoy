Status: active
Created: 2026-08-24
Updated: 2026-08-24

# Buoy Validates PR Merge Refs and the Final Squash Commit

## Context

PR #145's GitHub Actions check suite is associated with exact task head
`049a4ac4149923f4f6592840534c929532262044` and exact
`develop@3eabedd6b1e2c60a2a8be2489327b014d04130fc`, but the repository's normal
`pull_request` workflow uses default `actions/checkout` behavior. Its jobs
therefore execute GitHub's synthetic merge ref, commit
`848b6ec1a9c91873e4299bf3e0e1ce6bdb8c99a6`, rather than the literal task-head
commit.

This distinction matters because Hatch-VCS derives version metadata from the
checked-out commit. The successful pull-request run built and smoked
`0.5.2.dev109+g848b6ec1a`; it did not and cannot prove an archive identity
containing `g049a4ac`. The authorized squash merge will create another commit,
so neither a task-head build nor a synthetic-merge build can be the final
`develop` artifact identity.

The active integration ticket and earlier review guidance required literal
exact-PR-head Hatch-VCS evidence, while the user explicitly excluded new
workflow behavior. Final closure review correctly failed rather than silently
weakening either condition. At the 2026-08-24 checkpoint, the user explicitly
selected **“Merge-ref then post-merge”** over changing CI checkout behavior or
stopping without merge.

## Decision

Buoy MUST use this two-stage hosted verification contract for PR #145 and
future equivalently configured squash integrations:

1. **Before merge**, the pull-request check suite MUST be associated with the
   exact reviewed PR head and exact current base. All required jobs MUST execute
   the corresponding GitHub synthetic merge ref and pass. The run validates the
   candidate plus base as a combined tree. Records MUST name the associated
   head/base, executed merge commit, jobs, and generated Hatch-VCS identity.
   They MUST NOT represent merge-ref package bytes as literal task-head or final
   squash-commit identities.
2. **At integration**, a dedicated integrator MUST re-read current head, base,
   open/draft state, mergeability, and required check conclusions before making
   the PR ready and squash-merging it. The resulting squash tree MUST equal the
   reviewed PR-head tree.
3. **After merge**, the normal `push` workflow on `develop` MUST execute at the
   exact final squash commit. Python 3.11, Python 3.13, and the dependent
   distribution build/clean-wheel smoke MUST all pass before the overall
   integration is reported complete. This post-merge run supplies the final
   Hatch-VCS commit/version observation. Its canonical receipt MUST be recorded
   on PR #145, which remains the external integration authority.

The implementation ticket MAY close before the dedicated merge because repo
records must be finalized on the reviewed PR branch. The final records-only PR
head still requires the pre-merge check suite above. Dedicated merge and
post-merge `develop` CI are external integration stop gates: failure forbids a
completion claim and requires a durable blocker/follow-up before reporting.

This decision explicitly supersedes the literal exact-PR-head Hatch-VCS gate in
`.10x/tickets/2026-08-24-integrate-retrieve-command-telemetry-into-develop.md`
and the corresponding recommendation in
`.10x/reviews/2026-08-24-retrieve-command-telemetry-develop-integration-review.md`.
It does not weaken any telemetry, storage, migration, privacy, routing, test,
or source-identity contract.

## Alternatives considered

### Change pull-request checkout to the literal head

Rejected for this work. It would violate the explicit workflow-change exclusion,
expand PR #145, and stop exercising the automatically synthesized candidate-plus-
base tree unless a second path were added. It still would not prove the later
squash commit's Hatch-VCS identity.

### Treat the head-bound check suite as a literal head build

Rejected as false. Check-suite association and checkout identity are distinct;
the raw log proves checkout of `848b6ec1`.

### Stop without merging

Rejected by the user in favor of the two-stage contract.

## Consequences

- No workflow file changes are required.
- Pre-merge CI proves compatibility of the exact reviewed head with the exact
  base while preserving truthful package identity.
- Post-merge `develop` CI proves the final squash commit and its generated
  Hatch-VCS metadata before completion is claimed.
- Repository closure records precede the external integration receipt; PR #145
  is canonical for the final merge and post-merge result.
- Any change to PR head or base invalidates the corresponding synthetic merge
  observation and requires a fresh pre-merge run.
