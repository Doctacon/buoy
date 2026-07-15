Status: open
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
3. `.10x/tickets/2026-07-15-integrate-pi-worktree-governance.md`
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