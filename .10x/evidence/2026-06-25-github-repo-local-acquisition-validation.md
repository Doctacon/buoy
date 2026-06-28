Status: recorded
Created: 2026-06-25
Updated: 2026-06-25
Relates-To: .loom/tickets/2026-06-25-github-repo-local-acquisition.md

# GitHub Repo Local Acquisition Validation

## What was observed

Implemented and validated local-only public GitHub repository acquisition helpers.

Changed files:

- `src/turbo_search/github_repo.py`
  - Added `GitHubRepoError`, `GitHubRepoMetadata`, and `GitHubRepoAcquisition`.
  - Added unauthenticated GitHub REST metadata resolution.
  - Added `git ls-remote --symref` default-branch fallback.
  - Added shallow clone acquisition via `git clone --depth 1 --single-branch --branch <ref> --no-tags`.
  - Added commit SHA reading and requested tree subdirectory validation.
  - Added clear errors for missing git and unsupported blob/single-file acquisition.
- `tests/test_github_repo.py`
  - Added tests using fake metadata/fake subprocess and local temporary git repositories; no live GitHub network is required.

Validation command:

```bash
uv run python -m unittest tests.test_github_repo tests.test_crawler tests.test_plan_artifacts tests.test_cli
```

Output:

```text
....................................................
----------------------------------------------------------------------
Ran 52 tests in 0.351s

OK
```

## Procedure

1. Read the local acquisition ticket, GitHub ingestion spec, and research record.
2. Added a new acquisition module with metadata, fallback, clone, and error helpers.
3. Added tests for REST metadata parsing, fallback to `git ls-remote`, actual local git clone acquisition, tree subdirectory validation, blob rejection, and missing git error messaging.
4. Ran focused unit tests plus crawler/plan-artifact/CLI compatibility tests.

## What this supports or challenges

Supports the ticket acceptance criteria that:

- acquisition can be tested without live network;
- metadata fallback behavior is covered;
- failed acquisition errors are user-friendly;
- acquisition result includes commit SHA;
- existing website workflow tests remain unaffected.

## Limits

This evidence does not prove file filtering, generated repository Markdown corpus, repo-aware chunking, or end-to-end CLI planning. Those are covered by later tickets.
