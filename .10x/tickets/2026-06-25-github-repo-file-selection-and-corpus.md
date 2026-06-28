Status: done
Created: 2026-06-25
Updated: 2026-06-25
Parent: .loom/tickets/2026-06-25-github-repo-url-ingestion-plan.md
Depends-On: .loom/tickets/2026-06-25-github-repo-local-acquisition.md, .loom/specs/github-repo-url-ingestion.md, .loom/research/2026-06-25-github-repo-url-ingestion-research.md

# GitHub Repo File Selection and Corpus Generation

## Scope

Convert an acquired GitHub repository checkout into a deterministic local corpus that can feed the existing `plan.json` / `manifest.json` / `chunks.jsonl` workflow.

## In scope

- Enumerate tracked files with `git ls-files -z` from the checkout.
- Apply deterministic selection filters:
  - repo subdir from `tree/<ref>/<subdir>` URL when present;
  - user include/exclude globs, mapped from `--include-path` / `--exclude-path` to repo-relative file paths;
  - binary detection;
  - empty-file skip;
  - oversize skip using a conservative default cap, initially 50 KiB unless implementation evidence changes it;
  - vendor/generated/build/cache/dependency path denylist.
- Produce generated `pages/*.md` files with frontmatter containing GitHub metadata:
  - `source_kind`, `repo_full_name`, `repo_owner`, `repo_name`, `repo_ref`, `commit_sha`, `repo_path`, `language`, `fetcher`, `source_hash`.
- Preserve Markdown/prose file bodies where practical.
- Represent code/config files in a way that preserves path/language context and prepares for repo-aware chunking.
- Include skip counts and reasons in the crawl/plan summary payload.

## Out of scope

- Advanced semantic Tree-sitter parsing.
- Live apply.
- Private repo support.

## Acceptance criteria

- Tests use a fixture checkout/local git repo and do not require live GitHub.
- Binary, oversize, empty, vendor/generated, and user-excluded files are skipped with counted reasons.
- Included files produce Markdown files with valid scalar frontmatter parseable by existing `parse_markdown_file`.
- `--max-pages` caps selected files for repository sources.
- A generated corpus for a small repo can be processed into chunks without file errors.
- Summary output includes selected/skipped file counts.

## Progress and notes

- 2026-06-25: Activated under `/loom-driver` after local acquisition ticket completed.
- 2026-06-25: Implemented `git ls-files -z` tracked-file enumeration, repo subdir/user include/exclude filters, binary/empty/oversize/default generated-vendor-build-cache-lockfile filters, and selected-file cap handling.
- 2026-06-25: Implemented generated Markdown corpus with GitHub frontmatter and code-file line-range fenced sections.
- 2026-06-25: Added tests for filtering counts, parseable frontmatter, code rendering, max-file caps, repo subdir restriction, and user include opt-in for default-filtered files.
- 2026-06-25: Validation recorded in `.loom/evidence/2026-06-25-github-repo-file-selection-corpus-validation.md`.

## Current State

Done. Acquired repository checkouts can be converted into deterministic generated Markdown corpus pages with source metadata and selection stats.

## Journal

- 2026-06-25: Read ticket and relevant spec sections; acquisition result shape is available.
- 2026-06-25: Ran `uv run python -m unittest tests.test_github_repo tests.test_crawler tests.test_plan_artifacts tests.test_cli` successfully: 55 tests passed.

## Blockers

- None.
