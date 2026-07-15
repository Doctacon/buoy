Status: active
Created: 2026-07-15
Updated: 2026-07-15

# Pi Worktree Development Flow

## Purpose and scope

Define the repository-local instructions every new Pi session receives for isolated task development and controlled integration.

This specification governs the root `AGENTS.md` and Pi session behavior. GitHub enforcement is governed by `.10x/specs/protected-github-branches.md`.

## Behavior

### Session startup

The root `AGENTS.md` MUST instruct every Pi session to inspect at least:

```bash
git status --short --branch
git worktree list
```

before implementation. The session MUST identify its current branch and role before mutating source or project behavior.

### Branch roles

- Ordinary implementation MUST occur only on a `work/<ticket-or-task>` branch based on current `develop` and checked out in its own worktree.
- `develop` MUST be treated as integration-only.
- `main` MUST be treated as release-only.
- A normal task session started on `main` or `develop` MUST stop before implementation and request or use an appropriate task worktree.
- A task session MUST NOT merge its own branch into `develop` or `main`.
- A dedicated integration session MAY review and squash-merge a passing task pull request into `develop`.
- A dedicated release session MAY perform explicitly authorized release work involving `main`; `develop`-to-`main` release pull requests use merge commits.

### Handoff

Before handing work to integration, a task session MUST:

1. incorporate the current `develop` branch;
2. run the repository-required validation relevant to its ticket;
3. commit the bounded change on its `work/*` branch;
4. report the branch, commit, validation, compatibility risks, and external-side-effect risks.

When `develop` advances before merge, the task branch MUST incorporate the new target state and re-run required CI before GitHub allows integration.

### Durable project discipline

The root instructions MUST retain the repository's 10x execution gate, ticket ownership, evidence, review, and closure requirements rather than replacing them with Git-only process. A task branch or worktree does not itself authorize implementation.

## Acceptance criteria

- A tracked root `AGENTS.md` exists and contains the startup checks, branch roles, stop conditions, handoff requirements, and integration/release exceptions above.
- Starting Pi from a checkout containing the file makes it visible as a loaded context file in Pi's startup header unless context loading was explicitly disabled.
- The instructions do not tell task sessions to merge themselves.
- The instructions identify squash merge for task pull requests and merge commits for `develop`-to-`main` release pull requests.
- The instructions do not introduce a standard launcher, Git hook, Pi extension, release branch, or hotfix branch.

## Constraints

- `AGENTS.md` is behavioral guidance, not a security boundary.
- GitHub branch protection remains the mechanical merge boundary.
- Instructions MUST be concise enough to remain useful in every Pi session.
- Existing parent/global instructions remain additive; the root file MUST NOT attempt to replace Pi's system prompt.

## Explicit exclusions

- A worktree creation script or standard launcher.
- Local Git hook installation.
- A project-local Pi extension.
- Full GitFlow release/hotfix branch semantics.
- Changes to product runtime behavior.