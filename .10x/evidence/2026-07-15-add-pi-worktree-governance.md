Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Relates-To: .10x/tickets/done/2026-07-15-add-pi-worktree-governance.md, .10x/specs/pi-worktree-development-flow.md, .10x/specs/protected-github-branches.md

# Add Pi Worktree Governance

## What was observed

### Preflight and branch creation

Before branch mutation:

- root worktree branch and `HEAD`: `main` at `78d255b6e54567018e4ea7ad565a67224ee9c4bf`;
- local/remote `develop`: the same exact bootstrapped commit;
- staged paths: none;
- working-tree changes: only the expected decision supersession, focused specifications, parent/child tickets, bootstrap evidence, and bootstrap review;
- both `main` and `develop` protection readback remained strict with the exact three required checks, zero approvals, administrator enforcement, and force-push/deletion denial.

`work/establish-protected-development-flow` was created from local `develop` without losing or staging the governance records. `git merge-base --is-ancestor develop HEAD` exited 0.

### Repository changes

The bounded change:

- adds root `AGENTS.md` with startup inspection, task/integration/release branch roles, stop conditions, 10x execution-gate preservation, task handoff, squash task integration, and merge-commit release integration;
- adds `develop` to `.github/workflows/ci.yml` push branches while retaining pull-request CI and all existing jobs, permissions, commands, pins, concurrency, and build behavior;
- updates `tests/test_release_automation.py` to assert the exact `main`, `develop` push branch order;
- replaces obsolete advisory-CI/direct-main contributor and release wording with protected task-to-`develop` and release-to-`main` pull-request flow;
- incorporates the ratified workflow records and the completed bootstrap evidence/review.

`.github/workflows/release.yml` remained byte-for-byte unchanged in the working diff. No launcher, worktree script, Git hook, `.pi` resource, product code, release workflow semantic, or package configuration was added.

Pi's installed documentation at `/Users/crlough/.bun/install/global/node_modules/@earendil-works/pi-coding-agent/docs/usage.md` states that Pi loads `AGENTS.md` or `CLAUDE.md` from the current directory and parent directories at startup unless context loading is disabled. No new interactive Pi process was started, so this evidence does not claim direct startup-header observation.

### Local validation

Focused static/release automation tests:

```text
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_release_automation -v
Ran 9 tests in 0.169s
OK
```

Complete suite:

```text
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q
Ran 274 tests in 8.812s
OK
```

The suite emitted one existing best-effort temporary cleanup warning and still exited 0.

Clean temporary build:

```text
rm -rf /tmp/buoy-protected-development-build
uv build --out-dir /tmp/buoy-protected-development-build
Successfully built buoy_search-0.2.1.tar.gz
Successfully built buoy_search-0.2.1-py3-none-any.whl
```

Additional checks:

- `git diff --check`: exit 0;
- staged-index emptiness before commit: exit 0;
- parsed CI triggers: `pull_request` plus `push.branches == [main, develop]`;
- release workflow diff: empty.

### Hosted protected pull request

The first bounded commit was `cc7e8507178d8b32e617259170e658ebfbb2fa33`. It was pushed to `origin/work/establish-protected-development-flow`, and pull request [#1](https://github.com/Doctacon/buoy-search/pull/1) was opened against `develop`.

While the test jobs were in progress, GitHub reported the open pull request as `BLOCKED`. GitHub Actions run [29439859286](https://github.com/Doctacon/buoy-search/actions/runs/29439859286) then completed successfully for exact head `cc7e8507178d8b32e617259170e658ebfbb2fa33`:

- `Python 3.11`: success;
- `Python 3.13`: success;
- `Build distributions`: success.

After all three checks passed, GitHub reported the still-open pull request as `CLEAN` and `MERGEABLE`. `develop` and `main` remained unchanged at `78d255b6e54567018e4ea7ad565a67224ee9c4bf`; the task session did not merge the pull request.

## Procedure

1. Read the owning ticket, parent plan, active decision/specifications, completed dependency ticket/evidence/review, installed Pi context documentation, CI workflow/static tests, contributor guide, and release guide.
2. Verified exact status paths, refs, protection summary, empty index, branch absence, and governance-record preservation before switching.
3. Created the bounded work branch from `develop` and implemented only the governed files.
4. Ran focused tests, the complete suite, a clean temporary build, diff hygiene, trigger parsing, ancestry, and release-workflow checks.
5. Committed and pushed the bounded branch, opened pull request #1 to `develop`, observed its blocked in-progress state, watched all three required checks pass, and confirmed the pull request remained open.

## What this supports or challenges

This supports the checked-in Pi guidance, exact CI branch trigger, retained release automation boundaries, focused documentation coherence, and local validation required by the owning ticket.

No observation challenged the active decision or specifications.

## Limits

- `AGENTS.md` loading is supported by installed Pi documentation, not a newly observed interactive startup header.
- Hosted results above apply to first committed head `cc7e8507178d8b32e617259170e658ebfbb2fa33`. The final evidence/ticket update commit requires its own hosted checks before integration; the integration ticket owns final-head verification.
- The cleanup warning from the complete suite was non-fatal and occurred under a temporary test path; this evidence does not investigate unrelated cleanup behavior.
- GitHub configuration can later be deliberately changed by an administrator.