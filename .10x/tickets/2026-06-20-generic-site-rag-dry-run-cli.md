Status: done
Created: 2026-06-20
Updated: 2026-06-20
Parent: none
Depends-On: .loom/specs/generic-website-rag-dry-run-crawl.md, .pi/skills/turbopuffer-site-rag/SKILL.md

# Generic Site RAG Dry-Run CLI

## Scope

Implement the first-class dry-run CLI described in `.loom/specs/generic-website-rag-dry-run-crawl.md`.

In scope:

- Add a `turbo-search crawl` command.
- Use Scrapling for crawling/fetching/extraction.
- Prefer sitemap/robots discovery first, with capped same-domain link-crawl fallback when no sitemap pages are available.
- Generate a local Markdown corpus under `--out-dir`.
- Chunk the generated Markdown with the existing indexer.
- Print/write a JSON summary with safety fields and sample chunks.
- Add tests and docs.
- Add necessary open-source dependencies to project metadata/lockfile.

Out of scope:

- Live turbopuffer writes.
- Namespace creation/deletion/replacement.
- Live evals.
- Browser-rendered crawling/stealth mode.
- Arbitrary-namespace retrieval.
- Incremental recrawls.

## Clarification: extraction and Scrapling

The user correctly noted that Scrapling handles extraction. The implementation should not invent a new extraction stack. It should use Scrapling’s parsing/conversion path. The only extraction-related product surface needed in this ticket is an optional `--css-selector` pass-through so a user can scope extraction to a known main-content wrapper when a site includes noisy nav/sidebar/sponsor content in the body.

## Acceptance criteria

- `turbo-search crawl --base-url <url> --json` is available from the CLI.
- Default command is dry-run/local-only and reports:
  - `dry_run: true`
  - `credentials_required: false`
  - `turbopuffer_api_calls: false`
  - `api_calls_occurred: false`
- Base URL validation rejects non-HTTP(S) or relative URLs with exit code 2.
- The command reports deterministic namespace candidates like `site-scrapling-readthedocs-io-v1`.
- The command writes generated Markdown pages and `summary.json` under `--out-dir`.
- The command chunks generated pages and includes sample chunks in summary output.
- Tests cover helper functions and CLI behavior without requiring external network access.
- A local smoke test against `https://scrapling.readthedocs.io/en/latest/` is run with a small cap and recorded as evidence.
- Existing test suite and compile check pass.

## Progress and notes

- 2026-06-20: Ticket opened after user selected dry-run CLI, sitemap-first strategy, and Loom ticket organization.
- 2026-06-20: Existing skill helper `.pi/skills/turbopuffer-site-rag/scripts/scrapling_dry_crawl.py` can be used as a reference but should not remain the only implementation surface.
- 2026-06-20: Implemented `src/turbo_search/crawler.py` and wired first-class `turbo-search crawl` CLI.
- 2026-06-20: Added Scrapling/Markdownify dependencies to `pyproject.toml` and refreshed `uv.lock`.
- 2026-06-20: Added no-network tests for crawl helpers and mocked CLI behavior.
- 2026-06-20: Updated README with dry-run crawl usage.
- 2026-06-20: Parent review added stale generated page cleanup so rerunning a crawl in the same `--out-dir` cannot accidentally chunk old Markdown files.
- 2026-06-20: Parent review also added host/netloc allowed-domain coverage for base URLs that include explicit ports.
- 2026-06-20: Final validation passed:
  - `PYTHONPATH=src python3 -m unittest tests.test_crawler -v` ran 8 tests OK.
  - `PYTHONPATH=src python3 -m unittest discover -s tests -v` ran 27 tests OK.
  - `uv run python -m unittest discover -s tests -v` ran 27 tests OK.
  - `PYTHONPATH=src python3 -m compileall -q src tests .pi/skills/turbopuffer-site-rag/scripts/scrapling_dry_crawl.py` passed.
  - `uv run python -m compileall -q src tests` passed.
  - `uv run turbo-search crawl --base-url "https://scrapling.readthedocs.io/en/latest/" --out-dir artifacts/site-crawls/scrapling-readthedocs-io-cli-smoke-final --max-pages 3 --max-chunks 15 --css-selector ".md-content__inner" --json` passed with `dry_run: true`, `turbopuffer_api_calls: false`, 3 pages scraped, and 15 chunks generated.
  - `uv run turbo-search crawl --base-url /relative --json` exited 2 with `base URL must be an absolute http(s) URL`.

## Blockers

None.
