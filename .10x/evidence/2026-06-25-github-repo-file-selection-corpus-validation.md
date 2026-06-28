Status: recorded
Created: 2026-06-25
Updated: 2026-06-25
Relates-To: .loom/tickets/2026-06-25-github-repo-file-selection-and-corpus.md

# GitHub Repo File Selection and Corpus Validation

## What was observed

Implemented and validated repository tracked-file selection and Markdown corpus generation.

Changed files:

- `src/turbo_search/github_repo.py`
  - Added tracked file enumeration with `git ls-files -z`.
  - Added repo subdir, include/exclude glob, binary, empty, oversize, and default vendor/generated/build/cache/lockfile filtering.
  - Added user include override for default-filtered paths.
  - Added generated `pages/*.md` corpus writer with GitHub frontmatter: `source_kind`, repo full name/owner/name/ref, commit SHA, repo path, language, source hash, and `git-shallow-clone` fetcher.
  - Added Markdown/prose preservation and code-file Markdown rendering with line-range sections and fenced code blocks.
- `tests/test_github_repo.py`
  - Added local-git-repo tests for binary/oversize/empty/vendor/generated/user-excluded filtering, parseable frontmatter, code rendering, `--max-pages`-style cap, repo subdir selection, and user include opt-in for lockfiles.

Validation command:

```bash
uv run python -m unittest tests.test_github_repo tests.test_crawler tests.test_plan_artifacts tests.test_cli
```

Output:

```text
.......................................................
----------------------------------------------------------------------
Ran 55 tests in 0.773s

OK
```

## Procedure

1. Read file-selection/corpus ticket and relevant GitHub ingestion spec sections.
2. Implemented repository corpus functions in `github_repo.py`.
3. Extended GitHub repository tests with local temporary git repositories and no live network.
4. Ran focused tests plus existing crawler/CLI/plan-artifact compatibility tests.

## What this supports or challenges

Supports the ticket acceptance criteria that:

- tests use local git fixtures and no live GitHub;
- binary, oversize, empty, vendor/generated, and user-excluded files are skipped with counted reasons;
- generated Markdown frontmatter is parseable by the existing chunker;
- max-file caps are enforced;
- a generated small repo corpus can be processed into chunks without errors;
- selection summary counts are available through corpus stats.

## Limits

This evidence does not prove the CLI is wired end-to-end for GitHub planning or that apply preflight accepts a generated GitHub plan. Those are covered by later tickets.
