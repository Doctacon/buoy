Status: recorded
Created: 2026-06-25
Updated: 2026-06-25
Relates-To: .loom/tickets/2026-06-25-github-repo-url-parser-and-source-routing.md

# GitHub Repo URL Parser and Source Routing Validation

## What was observed

Implemented and validated first-pass GitHub repository URL source detection and repo-specific defaults.

Changed files:

- `src/turbo_search/crawler.py`
  - Added `WebsiteSource`, `GitHubRepoSource`, `GitHubBlobHint`, `detect_source`, `parse_github_repo_url`, and `source_id_for_url`.
  - Changed `namespace_candidate` and `default_out_dir` to derive repo-specific GitHub defaults.
- `src/turbo_search/plan_artifacts.py`
  - Changed `site_id_for_url` to use the source-aware ID helper.
- `tests/test_crawler.py`
  - Added tests for GitHub repo root, trailing slash, `.git`, tree, blob hint, non-repo fallback, invalid repo-like URLs, and unchanged website defaults.

Validation command:

```bash
uv run python -m unittest tests.test_crawler tests.test_plan_artifacts tests.test_cli
```

Output:

```text
..............................................
----------------------------------------------------------------------
Ran 46 tests in 0.043s

OK
```

An attempted `uv run pytest ...` validation failed because `pytest` is not installed in this project environment:

```text
error: Failed to spawn: `pytest`
  Caused by: No such file or directory (os error 2)
```

The successful `unittest` command is the applicable local test runner for the current dependency set.

## Procedure

1. Read the active parser/source-routing ticket and related GitHub repository ingestion spec/vocabulary.
2. Added source-detection structures and parser logic locally.
3. Added parser/default tests without network calls.
4. Ran focused crawler/plan-artifact/CLI tests through `unittest`.

## What this supports or challenges

Supports the ticket acceptance criteria that:

- accepted GitHub URL forms are parsed;
- non-repo GitHub pages can fall back to website source;
- invalid repo-like GitHub URLs fail clearly;
- `https://github.com/Doctacon/open-streaming-lab` gets repo-specific source kind, site ID, namespace candidate, and output directory;
- ordinary website tests still pass;
- parser tests require no network.

## Limits

This evidence does not prove GitHub repository acquisition, corpus generation, repo-aware chunking, or end-to-end GitHub planning. Those are covered by later child tickets.
