Status: done
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-turbopuffer-jellyfish-rag-plan.md
Depends-On: .loom/reviews/2026-06-20-turbopuffer-rag-diff-review.md

# Fix index command behavior for missing corpus paths

## Scope

Make `turbo-search index --corpus-dir <missing>` fail clearly instead of returning success with `corpus_dir_exists=false`.

In scope:

- Add a path existence/directory validation before corpus discovery.
- Return a non-zero CLI exit with a user-friendly error when the corpus directory is missing or not a directory.
- Add/adjust tests for missing corpus behavior.
- Record validation evidence.

Out of scope:

- Live turbopuffer writes.
- Retrieval behavior changes.
- Any broad refactor of chunking/indexing.

## Acceptance criteria

- Missing corpus path produces non-zero exit code.
- Error message is user-friendly and non-secret.
- Existing tests still pass.
- Evidence records commands and output.

## Progress and notes

- 2026-06-20: Opened from review finding in `.loom/reviews/2026-06-20-turbopuffer-rag-diff-review.md`.
- 2026-06-20: Added corpus path validation before Markdown discovery, CLI handling for missing/non-directory corpus paths, and a unit test for missing corpus behavior. Validated unit tests, syntax compilation, and `turbo-search index --corpus-dir /tmp/turbo-search-missing-corpus-loom` returning exit status 2 with a friendly stderr error. Evidence: `.loom/evidence/2026-06-20-fix-index-missing-corpus-error.md`.

## Blockers

- None.
