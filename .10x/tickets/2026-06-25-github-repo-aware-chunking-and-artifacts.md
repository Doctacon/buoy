Status: done
Created: 2026-06-25
Updated: 2026-06-25
Parent: .loom/tickets/2026-06-25-github-repo-url-ingestion-plan.md
Depends-On: .loom/tickets/2026-06-25-github-repo-file-selection-and-corpus.md, .loom/specs/github-repo-url-ingestion.md

# GitHub Repo-Aware Chunking and Plan Artifacts

## Scope

Ensure GitHub repository corpus content produces useful, stable chunks and standard plan/apply artifacts.

The existing Markdown chunker works well for docs, but repository source files need at least safe line/block fallback behavior so code is not destroyed by sentence/word splitting.

## In scope

- Decide and implement the MVP chunking path for repository content:
  - Markdown/prose: existing heading-aware chunking.
  - Code/config: repo-aware line/block chunks with path/language context; avoid arbitrary word/sentence splitting of code.
- Preserve existing `IndexingPlan` / `MarkdownChunk` or introduce a minimal compatible abstraction if necessary.
- Ensure `build_plan_artifacts` can include GitHub source metadata in page/manifest/chunk records where useful.
- Add or plan schema fields for `source_kind`, repo metadata, language, and file path without breaking website rows.
- Verify row identity remains stable across no-change repository plans and changes only for new/changed chunks.
- Ensure apply preflight can verify a generated GitHub plan through existing artifact-hash logic.

## Out of scope

- Full Tree-sitter semantic chunking unless implementation chooses it as small enough and tests it adequately.
- Retrieval UI changes beyond metadata preservation.
- Live apply to turbopuffer.

## Acceptance criteria

- Tests cover docs/Markdown files chunking through existing heading behavior.
- Tests cover code/config files chunking by lines/blocks with path/language context.
- Tests show no-change second plan reports unchanged chunks against fake/local state.
- Tests show changed file content yields rows to upsert and removed files yield stale rows.
- Apply preflight accepts and verifies a generated GitHub plan.
- Existing generic website plan/apply tests continue passing.

## Progress and notes

- 2026-06-25: Activated under `/loom-driver` after file-selection/corpus ticket completed.
- 2026-06-25: Confirmed the MVP code/config chunking path uses generated Markdown line-range sections and fenced code blocks with path/language context, while Markdown files preserve existing heading-aware chunking.
- 2026-06-25: Added chunk `source_metadata` propagation through plan artifacts and apply manifest parsing.
- 2026-06-25: Added row/schema fields for GitHub source metadata: `source_kind`, repo full name/owner/name/ref, commit SHA, repo path, and language.
- 2026-06-25: Added tests for metadata propagation, no-change/changed/stale diff behavior, and apply preflight compatibility.
- 2026-06-25: Validation recorded in `.loom/evidence/2026-06-25-github-repo-aware-chunking-artifacts-validation.md`.

## Current State

Done. Repository corpus chunks feed standard plan/apply artifacts safely, GitHub metadata is preserved into chunks/rows, incremental diff behavior is covered, and generated GitHub plans pass apply preflight verification.

## Journal

- 2026-06-25: Read ticket; generated corpus shape is available from `github_repo.py`.
- 2026-06-25: Ran focused tests successfully: 73 tests passed.
- 2026-06-25: Ran full `uv run python -m unittest discover tests` successfully: 101 tests passed.

## Blockers

- None.
