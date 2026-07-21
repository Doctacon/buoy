Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Relates-To: .10x/tickets/done/2026-07-15-bootstrap-protected-develop-branch.md, .10x/specs/protected-github-branches.md, .10x/decisions/superseded/protected-development-and-github-release-governance.md

# Bootstrap Protected Develop Branch

## What was observed

### Preflight

Before mutation:

- `HEAD`: `78d255b6e54567018e4ea7ad565a67224ee9c4bf`
- local `main`: `78d255b6e54567018e4ea7ad565a67224ee9c4bf`
- local `origin/main`: `78d255b6e54567018e4ea7ad565a67224ee9c4bf`
- current branch: `main`
- local `develop`: absent
- remote `origin/develop`: absent (`git ls-remote --exit-code --heads origin develop` exited 2 with no ref)
- `main` protection: absent (GitHub API HTTP 404 `Branch not protected`)
- staged paths: none
- working-tree changes: only the expected shaping-record deletion/move/additions for the protected-development plan

The authenticated GitHub account reported `admin: true` for public repository `Doctacon/buoy-search`. No token or credential material was recorded.

### Branch bootstrap

The following bounded mutation created `develop` without checking it out:

```text
git branch develop 78d255b6e54567018e4ea7ad565a67224ee9c4bf
git push origin refs/heads/develop:refs/heads/develop
```

Observed afterward:

- local `develop`: `78d255b6e54567018e4ea7ad565a67224ee9c4bf`
- remote `origin/develop`: `78d255b6e54567018e4ea7ad565a67224ee9c4bf`
- root worktree remained on `main`
- repository default branch remained `main`

### GitHub protection readback

Classic branch protection was configured through `PUT /repos/Doctacon/buoy-search/branches/{branch}/protection` for `main` and `develop`. Required checks were bound to GitHub Actions app ID `15368`.

Sanitized independent `GET` readback for `main`:

```json
{
  "branch": "main",
  "required_status_checks": {
    "strict": true,
    "checks": [
      {"context": "Build distributions", "app_id": 15368},
      {"context": "Python 3.11", "app_id": 15368},
      {"context": "Python 3.13", "app_id": 15368}
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false,
    "require_last_push_approval": false,
    "bypass_pull_request_allowances": null
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false,
  "lock_branch": false,
  "allow_fork_syncing": false
}
```

Sanitized independent `GET` readback for `develop` was identical except `"branch": "develop"`.

### Preservation validation

SHA-256 checks after the external mutations matched the preflight digests for every non-ticket shaping record:

```text
c50c48130ee15f40e90e818a50e9f04e7407f36739ee55155b1cb4bfd96c39b3  .10x/decisions/protected-development-and-github-release-governance.md
932306a5a9b25a7cd1fb56650e33e343d535451ed65c55196c68fbc876ff9708  .10x/decisions/superseded/github-only-release-automation-v0-2-1.md
e9a02b1575c80b486fd0aabf134fe40090a55cbc24b50b120ef7c62e3f82b67f  .10x/specs/pi-worktree-development-flow.md
1272001a1d59ae6e213f14e03663ab0fcd4b3cc2ce436732a243bb84c2cc9ae4  .10x/specs/protected-github-branches.md
4ef3f63713a7dc1d7592ce8b0a05966e11344091ce52ae1a58888ff2722f9fe4  .10x/tickets/2026-07-15-add-pi-worktree-governance.md
6e6301be3881709f1fba6b3d67de646573ab3e4a2f22ea4de4d75ce617996abf  .10x/tickets/2026-07-15-establish-protected-development-workflow.md
ce69df57907bb04f7f8ff9ad5a9e8aee014995f7b178e8de15c1a5975335a604  .10x/tickets/2026-07-15-integrate-pi-worktree-governance.md
```

The owning child ticket changed only through its required status/progress updates. This evidence record was added as required. `git diff --cached --quiet` passed: no files are staged.

## Procedure

1. Read the owning child ticket and every referenced active record.
2. Compared exact local/remote main commits, branch absence, protection absence, staged state, status paths, and shaping-record digests.
3. Created local `develop` directly at the ratified commit and pushed that exact ref.
4. Queried the current successful check runs to bind the three names to GitHub Actions app ID `15368`.
5. Applied the ratified protection payload independently to `main` and `develop`.
6. Queried each protection endpoint independently and asserted exact required checks, strictness, administrator enforcement, zero approvals/no bypass allowance, force-push denial, and deletion denial.
7. Rechecked branch SHAs, default/current branches, shaping-record digests, and staged state.

All mutating and assertion commands exited 0. One first digest assertion command transiently reported a mismatch even though the file timestamp and immediately repeated SHA-256 read matched the unchanged preflight digest; the explicit diagnostic rerun of every non-ticket record passed. No content repair or rewrite was performed.

## What this supports or challenges

This supports that:

- `develop` was bootstrapped from the exact ratified `main` commit;
- both long-lived branches now have matching active protection;
- pull requests, strict required GitHub Actions checks, zero approvals, administrator enforcement, no bypass allowance, and force-push/deletion denial are represented in GitHub's authoritative API readback;
- the root worktree stayed on `main` and its pre-existing shaping records were not absorbed into a commit, stage, stash, rename, or branch switch.

No observation challenged the governing decision or specification.

## Limits

- Configuration readback does not itself exercise every rejected-push or pull-request scenario.
- No synthetic commit was created merely to test rejection because that would widen this ticket and disturb the preserved working tree.
- No pull request or CI run was created; the next child ticket owns the first protected task pull request and the integration child owns merge-path validation.
- This evidence does not prove future administrators cannot deliberately reconfigure protection.
- The transient digest-command anomaly is bounded by unchanged file metadata and a successful immediate full digest rerun, but its cause was not reproduced.