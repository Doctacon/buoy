Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/tickets/done/2026-07-19-implement-opt-in-python-syntax-chunking.md, .10x/specs/repo-python-syntax-chunking-experiment.md

# Python Syntax Chunking Implementation Validation

## What was observed

The implementation worktree passed the focused syntax/repository/CLI suites, the complete 462-test suite, and the frozen ranking-contract validator on both required local CPython runtimes. CPython 3.13 also built the wheel and source distribution successfully.

| Runtime | Command | Result |
|---|---|---|
| CPython 3.11.5 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest tests.test_repo_syntax_chunking tests.test_github_repo tests.test_cli -q` | PASS, 69 tests |
| CPython 3.11.5 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python scripts/validate_ranking_contract.py` | PASS, 13 datasets / 90 identities / 369 judgments / 13 folds |
| CPython 3.11.5 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q` | PASS, 462 tests |
| CPython 3.13.0 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest tests.test_repo_syntax_chunking tests.test_github_repo tests.test_cli -q` | PASS, 69 tests |
| CPython 3.13.0 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python scripts/validate_ranking_contract.py` | PASS, 13 datasets / 90 identities / 369 judgments / 13 folds |
| CPython 3.13.0 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q` | PASS, 462 tests |
| CPython 3.13.0 | `rm -rf /tmp/buoy-c5-dist && uv build --out-dir /tmp/buoy-c5-dist` | PASS, wheel and source distribution built outside the project |

`git diff --check` also passed. Test output contained only the suite's pre-existing temporary plan-cleanup warnings; no test failed.

Hosted GitHub Actions run `29770845903` passed on PR #69 implementation commit `2e92103ad92d1c4aeb2e83899e06c6850629fe12`: Python 3.11 passed in 49 seconds, Python 3.13 passed in 45 seconds, and the dependent distribution build passed in 11 seconds. The evidence-only follow-up head also passed hosted run `29771166533`.

## PR #69 review-blocker repair validation

Review repair commit `b5588aa48c8d916e8ff50eb3d77a2ab4403bd0dc` makes explicit `current-default` fail closed unless generic `--max-chunks` output contains the complete expected generic chunk sequence—including exactly one unchanged first header—for every selected code file. Tests now exercise truncation immediately before a later code-file header, CRLF acquisition through `Path.read_text` into both syntax arms, and a bounded `buoy plan --repo-chunking-arm python-ast` command through written plan/manifest artifacts while the existing no-arm artifact assertion remains unchanged.

| Runtime | Command | Result |
|---|---|---|
| CPython 3.11.5 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest tests.test_repo_syntax_chunking tests.test_github_repo tests.test_cli -q` | PASS, 72 tests |
| CPython 3.11.5 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q` | PASS, 465 tests |
| CPython 3.11.5 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python scripts/validate_ranking_contract.py` | PASS, 13 datasets / 90 identities / 369 judgments / 13 folds |
| CPython 3.13.0 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest tests.test_repo_syntax_chunking tests.test_github_repo tests.test_cli -q` | PASS, 72 tests |
| CPython 3.13.0 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q` | PASS, 465 tests |
| CPython 3.13.0 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python scripts/validate_ranking_contract.py` | PASS, 13 datasets / 90 identities / 369 judgments / 13 folds |
| Build | `rm -rf /tmp/buoy-pr69-review-dist && uv build --out-dir /tmp/buoy-pr69-review-dist` | PASS, wheel and source distribution built outside the project |
| Hosted CI | GitHub Actions run `29771927189` on commit `b5588aa48c8d916e8ff50eb3d77a2ab4403bd0dc` | PASS, Python 3.11 (52s), Python 3.13 (45s), distribution build (9s) |

An initial attempt to launch both `uv run --python 3.11` and `uv run --python 3.13` validation concurrently failed because both commands replace the worktree's shared `.venv`. The same commands were rerun sequentially by runtime and passed as recorded above; the failure did not expose an implementation defect or alter tracked files.

## Finalization rerun after current `origin/develop`

Current `origin/develop` at `3e6005c13e5e35907eee2ae80992524074740921` is an ancestor of the reviewed implementation branch and was already incorporated; `git merge --ff-only origin/develop` reported `Already up to date.` Finalization then reran the required matrix sequentially without altering the reviewed implementation:

| Runtime | Command | Result |
|---|---|---|
| CPython 3.11.5 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest tests.test_repo_syntax_chunking tests.test_github_repo tests.test_cli -q` | PASS, 72 tests |
| CPython 3.11.5 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q` | PASS, 465 tests |
| CPython 3.11.5 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python scripts/validate_ranking_contract.py` | PASS, 13 datasets / 90 identities / 369 judgments / 13 folds; Buoy remains insufficient/pending baseline approval |
| CPython 3.13.0 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest tests.test_repo_syntax_chunking tests.test_github_repo tests.test_cli -q` | PASS, 72 tests |
| CPython 3.13.0 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q` | PASS, 465 tests |
| CPython 3.13.0 | `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python scripts/validate_ranking_contract.py` | PASS, 13 datasets / 90 identities / 369 judgments / 13 folds; Buoy remains insufficient/pending baseline approval |
| Build | `rm -rf /tmp/buoy-pr69-final-dist && uv build --out-dir /tmp/buoy-pr69-final-dist` | PASS, wheel and source distribution built outside the project |

The focused/full suites emitted only the same pre-existing temporary plan-cleanup warnings. `git diff --check` passed. Independent implementation review is recorded at `.10x/reviews/2026-07-20-python-syntax-chunking-implementation-review.md` with PASS at `360c6b9c666ccf432c082ac44d0a1400955ce3e9`.

Hosted GitHub Actions run `29773131065` passed on closure commit `bc0b76e491428d15855e30a02929d0fde058e355`: Python 3.11 passed in 49 seconds, Python 3.13 passed in 1 minute 12 seconds, and the dependent distribution build passed in 8 seconds.

## Coverage represented

Focused tests cover:

- unchanged ordinary no-arm output and explicit `current-default` page/body/chunk/ID/hash/citation parity;
- LF-only coordinates, terminal LF, blank lines, form-feed, and bare-carriage-return rejection;
- standard-library Python 3.11 parsing and tokenizer-owned sync/async/class decorator spans, including multiline decorators, final-row comments, expression-internal `@`, trivia, and nesting;
- fixed-window all-intersecting ancestor breadcrumbs and AST innermost/module ownership with nested carving;
- forward-except-at-EOF outside-symbol trivia assignment, all-trivia modules, deterministic `80/80/1` subdivision, exact reconstruction, adjacency, and zero overlap;
- one identical control/treatment header chunk, exact treatment line citations and immutable blob URLs, and generic Markdown/prose compatibility;
- whole-file sanitized Python parse fallback, deterministic non-Python fallback, unexpected tokenizer/coordinate failure propagation, and partial-plan refusal;
- CLI opt-in propagation, non-repository rejection, metadata/card incompatibility, fixed experiment token/overlap settings, local manifest row generation, and omission of the arm option from ordinary no-arm plan inputs.

## Safety observation

Validation loaded no embedding model, read no service credential, contacted no remote retrieval/provider service, and performed no namespace/catalog/applied-state write or delete. Distribution output and generated paired-plan pages were written only under temporary directories outside the project and removed or left outside the repository. No default, dataset, label, dependency, or lockfile changed.

## Limits

Independent review and the final local rerun support C5 closure, but the bounded three-file local plans are not the exact C6 Buoy/pytest/Ruff pilot forecast. Exact pilot commits/corpora, namespace names, selected-file and header/source/total row counts, storage multipliers, and write counts remain unreported, and exact namespace-write approval remains ungranted. C6 remains blocked; this record authorizes no live plan/apply, retrieval, namespace, catalog, state, dataset, label, default, or promotion action.
