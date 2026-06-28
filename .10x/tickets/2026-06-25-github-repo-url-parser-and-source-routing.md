Status: done
Created: 2026-06-25
Updated: 2026-06-25
Parent: .loom/tickets/2026-06-25-github-repo-url-ingestion-plan.md
Depends-On: .loom/specs/github-repo-url-ingestion.md, .loom/knowledge/github-repo-ingestion-vocabulary.md

# GitHub Repo URL Parser and Source Routing

## Scope

Add the typed URL/source-detection foundation for GitHub repository ingestion.

This ticket should introduce a small source abstraction that lets `plan` and `crawl` route URLs to either:

- existing `website` Scrapling behavior; or
- new `github_repo` behavior in later tickets.

It should also fix the current host-only default identity problem for GitHub repository URLs.

## In scope

- Add a parser for supported GitHub repository URLs:
  - `https://github.com/owner/repo`
  - `https://github.com/owner/repo/`
  - `https://github.com/owner/repo.git`
  - `https://github.com/owner/repo/tree/<ref>/<optional-subdir>`
  - optionally detect `blob/<ref>/<path>` and either return a structured single-file/subpath hint or reject clearly pending implementation.
- Add source detection API, e.g. `detect_source(url) -> WebsiteSource | GitHubRepoSource`.
- Normalize GitHub repository root to `https://github.com/<owner>/<repo>`.
- Derive repo-specific defaults:
  - `site_id = github-<owner-slug>-<repo-slug>`
  - `namespace_candidate = github-<owner-slug>-<repo-slug>-v1`
  - default out dir name is repo-specific.
- Keep ordinary website behavior unchanged.
- Ensure explicit `--namespace` and `--out-dir` continue to override defaults.

## Out of scope

- Actual git clone/acquisition.
- File filtering/corpus generation.
- Apply live writes.
- Private repository auth.

## Acceptance criteria

- Unit tests cover accepted GitHub URL forms and normalized structured output.
- Unit tests cover rejected GitHub non-repo pages with clear errors or website fallback when appropriate.
- Unit tests show `https://github.com/Doctacon/open-streaming-lab` defaults to:
  - source kind `github_repo`
  - site ID `github-doctacon-open-streaming-lab`
  - namespace candidate `github-doctacon-open-streaming-lab-v1`
  - repo-specific default output directory.
- Existing tests for non-GitHub websites still pass.
- No network calls are introduced by parser/source-routing tests.

## Progress and notes

- 2026-06-25: Started under `/loom-driver`; related spec and vocabulary have been read.
- 2026-06-25: Implementation worker read ticket/spec/vocabulary and existing crawler/CLI/plan artifact tests; adding parser/source routing/default identity helpers without repository acquisition.
- 2026-06-25: Added source-detection dataclasses, GitHub URL parser, repo-specific namespace/source-id/default-out-dir helpers, and source-aware plan site ID derivation.
- 2026-06-25: Added parser/default tests for GitHub root, trailing slash, `.git`, tree URLs, blob hints, non-repo fallback, invalid repo-like paths, and unchanged website defaults.
- 2026-06-25: Validation recorded in `.loom/evidence/2026-06-25-github-repo-url-parser-routing-validation.md`.

## Current State

Done. The parser/source-routing foundation is implemented and focused tests pass. Later tickets still need acquisition/corpus/chunking/CLI integration so GitHub plan execution routes to repository contents.

## Journal

- 2026-06-25: Activated ticket and delegated implementation/review cycle.
- 2026-06-25: Began narrow implementation in `crawler.py`, `cli.py`, and `plan_artifacts.py`; planned tests for accepted/rejected GitHub forms and non-GitHub compatibility.
- 2026-06-25: The async worker run failed before persisting output and a foreground worker timed out, but the partial edit it left was inspected, completed, and validated in the parent session to avoid blocking the driver.
- 2026-06-25: Ran `uv run python -m unittest tests.test_crawler tests.test_plan_artifacts tests.test_cli` successfully: 46 tests passed.

## Blockers

- None.
