Status: done
Created: 2026-06-28
Updated: 2026-06-28
Depends-On: .10x/evidence/2026-06-28-repo-search-metadata-cross-repo-validation.md, .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md

# Repo File-Card Metadata Indexing

## Scope

Implement and validate an opt-in repository indexing mode that writes separate lightweight metadata card pages for selected repository files instead of inserting metadata into every code page.

The mode must preserve default behavior unless explicitly requested.

## Acceptance criteria

- Add an opt-in CLI/config flag, expected name: `--repo-file-cards`, for `crawl` and `plan`.
- Generated file cards include repository path, path tokens, file stem, language, and Python symbols/tokens where available.
- File cards preserve normal source metadata (`source_kind`, `repo_path`, `repo_full_name`, ref, commit, language) so repo-level eval matching by `repo_path` still works.
- Existing `--repo-search-metadata` behavior remains opt-in and unchanged except for bug fixes.
- Local unit tests cover card generation and CLI option propagation.
- Run full unittest suite and `git diff --check`.
- If implementation validates, run approved live apply/eval to new namespaces across the five repo basket; no stale deletion or namespace deletion.

## Explicit exclusions

- Do not promote file cards as a default in this ticket.
- Do not enable oversize indexing unless separately requested.
- Do not delete stale rows or namespaces.

## Progress and notes

- 2026-06-28: Opened after metadata preamble improved average/P@5 but regressed turbo-search and Requests by composite score. File cards are intended to test metadata discoverability without perturbing ordinary code chunk embeddings.
- 2026-06-28: Implemented opt-in `--repo-file-cards`, added unit coverage, live-applied new file-card namespaces across the five-repo basket, and ran retrieval evals. File cards improved four of five repos and average score/P@5, but turbo-search regressed, so no default promotion. Evidence: `.10x/evidence/2026-06-28-repo-file-card-metadata-validation.md`.
