Status: done
Created: 2026-07-15
Updated: 2026-07-15
Parent: None
Depends-On: None

# Establish Protected Development Workflow

## Plan outcome

Replace direct Pi work on `main` with repository-loaded session rules, a long-lived `develop` integration branch, isolated `work/*` task branches, required pull requests, and strict CI enforcement on both long-lived branches.

This is a parent plan, not an executable ticket.

## Governing records

- `.10x/decisions/protected-development-and-github-release-governance.md`
- `.10x/specs/pi-worktree-development-flow.md`
- `.10x/specs/protected-github-branches.md`
- `.10x/specs/buoy-ci-and-github-releases.md`

## Child sequence

1. `.10x/tickets/done/2026-07-15-bootstrap-protected-develop-branch.md`
   - Create remote `develop` at the ratified `main` commit.
   - Install matching protection on `main` and `develop` before ordinary integration.
2. `.10x/tickets/done/2026-07-15-add-pi-worktree-governance.md`
   - On a bounded `work/*` branch, add root Pi instructions and make CI validate pushes to both long-lived branches.
   - Open a pull request to `develop`; do not self-merge.
3. `.10x/tickets/done/2026-07-15-integrate-pi-worktree-governance.md`
   - Independently review the pull request and remote protection, observe required CI, and squash-merge into `develop` when supported.

Children are sequential because the protected integration target must exist before the first ordinary task pull request demonstrates the intended workflow.

## Aggregate acceptance criteria

- `origin/develop` exists from exact bootstrap commit `78d255b6e54567018e4ea7ad565a67224ee9c4bf`.
- `main` and `develop` both require pull requests, all three named CI checks, current target state, zero approvals, and no administrator bypass; force pushes and deletion are disabled.
- A tracked root `AGENTS.md` gives every new Pi session the ratified branch/worktree rules.
- CI runs on pull requests and pushes to both `main` and `develop` without weakening existing release or security boundaries.
- The first governance task is squash-merged through a passing pull request into `develop`.
- No launcher, local Git hook, Pi extension, tag, release, package publication, secret/environment change, or Turbopuffer operation occurs.
- Evidence, independent review, specifications, decision status, and child/parent ticket status agree before closure.

## Integration points

- GitHub repository configuration for `Doctacon/buoy-search`.
- `.github/workflows/ci.yml` and its static tests.
- Root `AGENTS.md` loaded by Pi from every checkout/worktree.
- Existing tag-only release automation from reviewed `main`.

## Blockers

None. The maintainer ratified branch scope, status checks, zero approvals, strict base freshness, administrator enforcement, local-enforcement exclusions, branch bootstrap, and merge strategy.

## Progress and notes

- 2026-07-15: User authorized implementation of root Pi instructions and mechanical enforcement, explicitly excluding a standard launcher.
- 2026-07-15: User selected protection for both branches with PR plus all CI checks, zero approvals, no administrator bypass, GitHub-only enforcement, immediate `develop` creation, strict base freshness, task squash merges, and release merge commits.
- 2026-07-15: Shaping records created. Implementation intentionally deferred to child tickets under the specification-first execution gate.
- 2026-07-15: Bootstrap and implementation children completed with evidence and pass reviews. PR #1 passed required CI on final record-complete head and was squash-merged into `develop` as `27e3fdff62c75ef7766bceea21f8aeb2ac9d94dd`; `main` remained unchanged and both protections remained conformant. Post-merge evidence is `.10x/evidence/2026-07-15-integrate-pi-worktree-governance.md`.
- 2026-07-15: Fresh-context aggregate closure review passed the integration child and found one mechanical parent blocker: six live references still pointed to the pre-move release decision path. The exact six references were repaired to `.10x/decisions/superseded/github-only-release-automation-v0-2-1.md` while historical digest-output paths were preserved. Review: `.10x/reviews/2026-07-15-protected-development-workflow-closure-review.md`.
- 2026-07-15: All three children are done. Aggregate acceptance maps to the child evidence/reviews, active decision/specifications, protected PR #1 integration, root `AGENTS.md`, exact CI triggers, and GitHub protection readback. No excluded launcher, hook, Pi extension, release/tag, publication, environment/secret, product, or Turbopuffer mutation occurred. Parent closed.

## Retrospective

The durable model is intentionally layered: `AGENTS.md` gives every Pi session local branch-role guidance, while GitHub protection supplies the hard merge boundary. Strict current-base CI trades some integration friction for reliable concurrency across task worktrees. The closure review also demonstrated why decision moves require graph-wide live-reference repair while historical command-output paths must remain untouched. That lesson is already embodied by the repository's always-on record-reference rules and this evidence trail; no additional knowledge or skill record is needed.
