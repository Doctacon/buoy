Status: recorded
Created: 2026-07-14
Updated: 2026-07-20
Relates-To: .10x/tickets/done/2026-07-14-publish-buoy-rebrand-commit.md, .10x/tickets/done/2026-07-14-buoy-public-ci-release-plan.md

# Buoy Rebrand and CI Commit Pre-Push Validation

## What was observed

The canonical branch and remote were `main` and `git@github.com:Doctacon/buoy-search.git`. The working tree contained only the completed Buoy public CI/release plan layered on the already-pushed Buoy rebrand tree; ignored `.env`, local state, artifacts, caches, and temporary build output were not selected for commit.

## Procedure

- Enumerated staged, unstaged, untracked, and ignored paths.
- Scanned tracked/candidate project files and retained CI evidence for private-key, GitHub token, PyPI token, password, secret, and API-key assignment patterns; no credential value was found.
- Ran the complete test suite and package build.
- Verified the uv lock and whitespace.
- Staged the complete governed source/docs/workflow/record tree, then inspected staged names/stat/content before commit.

## Results

```text
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q
Ran 235 tests in 5.030s
OK

uv build --out-dir /tmp/buoy-publish-commit-build
built buoy_search-0.2.0-py3-none-any.whl
built buoy_search-0.2.0.tar.gz

uv lock --check
PASS

git diff --check
PASS
```

The known cleanup-boundary warning appeared during tests and remained non-fatal.

## What this supports or challenges

Supports creating one normal `feat: rebrand project as Buoy` commit and pushing it without tag, release, PyPI, force, history rewrite, or live Turbopuffer activity.

## Commit, push, and hosted CI observation

- Commit: `d846d2b2e965e7f62ff180442724d02705688a1a`
- Subject: `feat: rebrand project as Buoy`
- Push: normal fast-forward `836a921..d846d2b` to canonical `origin/main`; no force.
- CI: https://github.com/Doctacon/buoy-search/actions/runs/29359814276 completed successfully.
- Jobs: Python 3.11 passed in 32 seconds; Python 3.13 passed in 39 seconds; distribution build passed in 11 seconds.

GitHub emitted deprecation annotations because the pinned checkout/setup-uv action revisions target the Node.js 20 action runtime and are currently forced onto Node.js 24. This did not fail CI; durable follow-up is `.10x/tickets/done/2026-07-14-update-node24-github-actions.md`.

## Limits

No release tag, release, PyPI publication, force push, history rewrite, or live operation occurred. Post-commit ticket/evidence updates necessarily remain outside the commit whose ID they record.
