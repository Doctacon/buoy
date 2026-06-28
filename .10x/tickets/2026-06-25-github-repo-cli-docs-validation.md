Status: done
Created: 2026-06-25
Updated: 2026-06-25
Parent: .loom/tickets/2026-06-25-github-repo-url-ingestion-plan.md
Depends-On: .loom/tickets/2026-06-25-github-repo-url-parser-and-source-routing.md, .loom/tickets/2026-06-25-github-repo-local-acquisition.md, .loom/tickets/2026-06-25-github-repo-file-selection-and-corpus.md, .loom/tickets/2026-06-25-github-repo-aware-chunking-and-artifacts.md, .loom/specs/github-repo-url-ingestion.md

# GitHub Repo CLI Docs and Validation

## Scope

Finish user-facing CLI behavior, documentation, and validation for GitHub repository URL ingestion.

## In scope

- Update CLI help text to explain automatic GitHub repository handling.
- Ensure text and JSON summaries include:
  - `source_kind`;
  - repo owner/name/full name;
  - repo ref and commit SHA;
  - checkout/acquisition strategy;
  - selected/skipped file counts;
  - repo-specific namespace/state/out-dir paths.
- Update README/docs with examples:

```bash
uv run turbo-search plan https://github.com/Doctacon/open-streaming-lab
uv run turbo-search apply
uv run turbo-search apply --approve
```

- Document file filtering examples:

```bash
uv run turbo-search plan https://github.com/owner/repo --include-path 'docs/**'
uv run turbo-search plan https://github.com/owner/repo --exclude-path 'dist/**'
```

- Validate that ordinary website examples and tests still work.
- Add an end-to-end dry-run test using local fixtures/mocks, not live GitHub/turbopuffer.
- Record evidence after tests pass.

## Out of scope

- Live apply to turbopuffer unless separately approved.
- Private GitHub token docs unless private repo support is explicitly added later.

## Acceptance criteria

- `turbo-search --help` and subcommand help are accurate for source auto-detection.
- README includes the GitHub repo example and explains repo-specific defaults.
- JSON summary fields are stable enough for future tests/automation.
- End-to-end dry-run test proves a GitHub repo URL produces plan artifacts without live GitHub/turbopuffer dependencies.
- Full relevant test suite passes.
- Evidence record is written under `.loom/evidence/` with command outputs and limits.

## Progress and notes

- 2026-06-25: Activated after implementation tickets completed.
- 2026-06-25: Added `crawl_github_repo` summary wrapper over acquisition/corpus/chunking.
- 2026-06-25: Wired CLI `crawl` and `plan` through source detection so GitHub repository URLs route to repo ingestion instead of Scrapling site crawling.
- 2026-06-25: Updated CLI help/text summaries to mention site/repository sources and show GitHub repo/file counts.
- 2026-06-25: Added CLI tests for GitHub `crawl` and `plan` routing, repo-specific namespace/site ID/state path, and artifact metadata.
- 2026-06-25: Updated `README.md` and `docs/generic-site-rag-plan-apply.md` with public GitHub repository examples and repo-relative path filtering.
- 2026-06-25: Validation recorded in `.loom/evidence/2026-06-25-github-repo-cli-docs-validation.md`.

## Current State

Done. CLI routing, help/docs, mocked end-to-end GitHub plan behavior, and full test validation are complete.

## Journal

- 2026-06-25: Ran `uv run python -m unittest discover tests` successfully: 103 tests passed.
- 2026-06-25: Inspected `uv run turbo-search --help | head -40`; help now mentions website or public GitHub repository crawl/plan.

## Blockers

- None.
