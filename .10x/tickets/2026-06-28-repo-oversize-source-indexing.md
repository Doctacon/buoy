Status: open
Created: 2026-06-28
Updated: 2026-06-28
Depends-On: .10x/tickets/2026-06-28-cross-corpus-validation-basket.md

# Repo Oversize Source Indexing

## Scope

Investigate and improve GitHub repository planning for important source files above the current 50 KiB file-size cap.

The expanded validation basket exposed that central implementation files can be skipped as oversized:

- `pytest-dev/pytest`: examples include `src/_pytest/fixtures.py`, `src/_pytest/python.py`, and `src/_pytest/config/__init__.py`.
- `fastapi/typer`: examples include `typer/main.py` and `typer/params.py`.

This limits repository-search validation because seed labels must avoid skipped source files even when those files are the primary authority for a user query.

## Acceptance criteria

- Characterize how many files and chunks would be added by increasing or replacing the current oversize-file policy across current validation repos.
- Preserve local-only `plan` behavior: no credentials, embeddings, turbopuffer calls, or namespace mutation during investigation.
- Propose the smallest safe change, such as a higher cap, line-range chunking for oversized text files, or per-language limits.
- Validate that generated artifacts remain reviewable and do not admit binary/vendor/generated noise.
- Do not change live namespaces or defaults without separate approval.

## Explicit exclusions

- No Tree-sitter or syntax-aware chunking unless separately selected.
- No live apply or reindex.
- No stale deletion or namespace deletion.

## Blockers

- None for local investigation.

## References

- `.10x/evidence/2026-06-28-cross-corpus-validation-local-plans.md`
- `.10x/evidence/2026-06-28-cross-corpus-seed-eval-datasets.md`
- `src/buoy_search/github_repo.py`

## Progress and notes

- 2026-06-28: Opened after seed dataset drafting found central pytest and Typer implementation files skipped by the 50 KiB repo file cap.
- 2026-06-28: Added explicit opt-in `--repo-max-file-bytes` and locally planned pytest/Typer with a 200 KiB cap plus search metadata. Central authority files are included (`src/_pytest/fixtures.py`, `src/_pytest/python.py`, `src/_pytest/config/__init__.py`, `typer/main.py`, `typer/params.py`). Planned rows: pytest 6893, Typer 3221. No live apply in this local slice. Evidence: `.10x/evidence/2026-06-28-repo-oversize-metadata-local-validation.md`.
- 2026-06-28: After explicit user approval for writes/evals to new namespaces, live-applied oversize-only, metadata-only, and oversize+metadata ablations for pytest/Typer. Oversize recovered authority-file query score (`pytest 23.136 -> 78.622`, `Typer 27.002 -> 69.619`) but regressed existing seed score (`pytest 84.742 -> 81.354`, `Typer 59.423 -> 52.042`). Keep oversize opt-in/query-routed; do not promote as a global default. Evidence: `.10x/evidence/2026-06-28-repo-oversize-metadata-live-eval.md`.
