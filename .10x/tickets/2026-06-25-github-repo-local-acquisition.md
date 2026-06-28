Status: done
Created: 2026-06-25
Updated: 2026-06-25
Parent: .loom/tickets/2026-06-25-github-repo-url-ingestion-plan.md
Depends-On: .loom/tickets/2026-06-25-github-repo-url-parser-and-source-routing.md, .loom/specs/github-repo-url-ingestion.md, .loom/research/2026-06-25-github-repo-url-ingestion-research.md

# GitHub Repo Local Acquisition

## Scope

Implement local-only public GitHub repository acquisition for parsed `github_repo` sources.

The acquisition layer should resolve the default branch/ref and clone repository contents into generated artifacts without reading or persisting GitHub credentials.

## In scope

- Define a GitHub repository acquisition model with at least:
  - repo owner/name/full name;
  - canonical repo root URL;
  - clone URL;
  - requested ref/subdir if supplied by a tree URL;
  - resolved ref/default branch;
  - checked-out commit SHA;
  - checkout directory.
- Resolve metadata using unauthenticated GitHub REST for public repos when available.
- Fallback to `git ls-remote --symref <clone_url> HEAD` when metadata/default branch lookup is unavailable.
- Shallow clone using an equivalent of:

```bash
git clone --depth 1 --single-branch --branch <ref> --no-tags <clone_url> <checkout_dir>
```

- Store checkout under generated artifacts/cache paths that are gitignored.
- Surface clear errors for:
  - missing `git` executable;
  - inaccessible/private repository in MVP mode;
  - failed metadata/default-branch resolution;
  - failed clone;
  - requested tree ref/subdir not found.

## Out of scope

- Token/private repo support.
- File selection and corpus writing beyond returning a checkout path and metadata.
- Live turbopuffer work.
- Networked unit tests; tests should mock subprocess/HTTP or use local temporary git repositories.

## Acceptance criteria

- Acquisition can be tested without live network by using faked metadata and local temporary git repositories or subprocess mocks.
- Metadata fallback behavior is covered in tests.
- Failed acquisition errors are user-friendly and do not mention secret/token values.
- The acquisition result includes commit SHA for later frontmatter/summary metadata.
- Existing website workflow remains unaffected.

## Progress and notes

- 2026-06-25: Activated under `/loom-driver` after parser/source-routing ticket completed.
- 2026-06-25: Added `src/turbo_search/github_repo.py` with public metadata resolution, `git ls-remote --symref` fallback, shallow clone acquisition, commit SHA capture, tree subdirectory validation, and user-friendly git/blob errors.
- 2026-06-25: Added `tests/test_github_repo.py` using fake REST/subprocess paths and local temporary git repositories; no live GitHub network is required.
- 2026-06-25: Validation recorded in `.loom/evidence/2026-06-25-github-repo-local-acquisition-validation.md`.

## Current State

Done. Local acquisition helpers are implemented and focused tests pass. Later tickets will use the checkout to select files and generate the reviewable corpus.

## Journal

- 2026-06-25: Read ticket, spec, and research; starting acquisition module work.
- 2026-06-25: Ran `uv run python -m unittest tests.test_github_repo tests.test_crawler tests.test_plan_artifacts tests.test_cli` successfully: 52 tests passed.

## Blockers

- None.
