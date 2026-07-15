Status: done
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/done/2026-07-15-establish-protected-development-workflow.md
Depends-On: .10x/tickets/done/2026-07-15-bootstrap-protected-develop-branch.md

# Add Pi Worktree Governance

## Scope

Create a bounded `work/establish-protected-development-flow` branch from bootstrapped `develop`, preserving and incorporating the ratified uncommitted shaping records, then:

- add concise root `AGENTS.md` instructions implementing the Pi session/worktree contract;
- update `.github/workflows/ci.yml` so pushes to both `main` and `develop` run CI;
- update focused static tests for the exact branch set;
- update contributor/release documentation only where needed to prevent direct-to-main instructions from contradicting the active workflow;
- commit and push the task branch;
- open a pull request targeting `develop` and observe the required checks;
- do not merge the pull request.

## Acceptance criteria

- Before switching branches, the executor verifies the root worktree contains only the expected shaping records created for this workflow and preserves them exactly.
- The work branch starts from the bootstrapped `develop` commit.
- Root `AGENTS.md` satisfies every acceptance criterion in `.10x/specs/pi-worktree-development-flow.md` and remains concise.
- CI push branches are exactly `main` and `develop`; pull-request CI and all existing permissions, commands, matrix, pins, artifact, no-secret, no-PyPI, and release boundaries remain unchanged.
- Static tests assert the exact push branch set and pass.
- Contributor and release instructions no longer tell maintainers to commit/push ordinary release preparation directly to `main`; release tags remain created only from reviewed `main`.
- Complete repository tests and a clean temporary build pass.
- The commit contains only this plan's records, root instructions, CI/static-test changes, and necessary focused documentation.
- A GitHub pull request from `work/establish-protected-development-flow` to `develop` exists and reports the three required checks.
- The task session does not merge its own pull request.

## Explicit exclusions

- Standard launcher or worktree script.
- Git hooks or Pi extensions.
- Product behavior changes.
- Release workflow changes unless an existing static assertion must be preserved without semantic change.
- GitHub protection changes, which belong to the dependency ticket.
- Tags, releases, package publication, secrets/environments, or Turbopuffer operations.
- Hotfix or release branches.

## References

- `.10x/decisions/protected-development-and-github-release-governance.md`
- `.10x/specs/pi-worktree-development-flow.md`
- `.10x/specs/protected-github-branches.md`
- `.10x/specs/buoy-ci-and-github-releases.md`
- `.10x/tickets/done/2026-07-15-establish-protected-development-workflow.md`
- `.10x/tickets/done/2026-07-15-bootstrap-protected-develop-branch.md`
- Pi context-file documentation inspected during shaping: `/Users/crlough/.bun/install/global/node_modules/@earendil-works/pi-coding-agent/docs/usage.md`

## Evidence expectations

Record the bounded diff, branch/base/head commits, focused static-test result, complete test result, build result, pull-request URL, and required-check observations. State that Pi context loading is documented behavior; do not claim a new interactive Pi process was observed unless one was actually started and its startup header inspected.

## Design notes

Pi automatically concatenates root `AGENTS.md`/`CLAUDE.md` context files at startup unless `--no-context-files` is used. `AGENTS.md` is guidance, while GitHub protection is the hard integration boundary. Task pull requests are squash-merged by a separate integration session.

## Blockers

Depends on successful branch bootstrap and remote protection.

## Progress and notes

- 2026-07-15: Ticket opened with implementation semantics fully ratified. No implementation has occurred.
- 2026-07-15: Preflight confirmed the root worktree was on clean-index `main` at the exact bootstrapped `develop` base, with only the expected governance records present and both long-lived protections intact. Created `work/establish-protected-development-flow` from `develop` without losing or staging those records.
- 2026-07-15: Added concise root Pi instructions, exact `main`/`develop` CI push triggers and static assertion, and focused contributor/release pull-request wording. Focused 9-test release automation suite, complete 274-test suite, clean temporary wheel/sdist build, diff hygiene, workflow parsing, and release-workflow immutability checks passed. Evidence: `.10x/evidence/2026-07-15-add-pi-worktree-governance.md`.
- 2026-07-15: Committed bounded implementation as `cc7e8507178d8b32e617259170e658ebfbb2fa33`, pushed `work/establish-protected-development-flow`, and opened protected pull request https://github.com/Doctacon/buoy-search/pull/1 to `develop`. GitHub reported `BLOCKED` while checks ran; run `29439859286` then passed `Python 3.11`, `Python 3.13`, and `Build distributions`, after which the open PR reported `CLEAN`/`MERGEABLE`. The task session did not merge it.
- 2026-07-15: A fresh-context independent review passed on final implementation/evidence head `9520b4170c53d41606bedb1ee8f7dd27a30497ca` with no findings: `.10x/reviews/2026-07-15-add-pi-worktree-governance-review.md`. Review confirmed the complete 16-file diff, focused 9 tests, full 274 tests, diff hygiene, exact branch protection, current-base eligibility, and hosted run `29439997131` with all three required checks. Every acceptance criterion maps to `.10x/evidence/2026-07-15-add-pi-worktree-governance.md` and the review. Implementation child closed for integration.

## Retrospective

The first protected task pull request demonstrated the intended split between task and integration roles: the task worker stopped after a passing PR, and a fresh reviewer challenged the exact head without mutating it. Recording final evidence added a second record-only commit and therefore required a second hosted run; future task evidence should, where practical, be finalized before the first push to reduce redundant CI while never predicting hosted results. This is already captured by the ticket/evidence discipline and does not require a separate knowledge or skill record.