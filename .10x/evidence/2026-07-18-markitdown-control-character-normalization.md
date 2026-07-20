Status: recorded
Created: 2026-07-18
Updated: 2026-07-18
Relates-To: .10x/tickets/2026-07-18-restore-markitdown-control-character-normalization.md, .10x/specs/local-markitdown-document-source-ingestion.md, .10x/specs/local-pdf-source-ingestion.md

# MarkItDown Control-Character Normalization Evidence

## What was observed

Local MarkItDown ingestion now removes Unicode `Cc` control characters from converted Markdown before the existing empty-output check, generated page write, and chunking. Newline, carriage return, and tab are explicitly preserved.

Focused fixtures cover the shared sanitizer, PDF ingestion, non-PDF ingestion, artifact and chunk output, valid Unicode and Markdown whitespace preservation, and PDF/non-PDF output that becomes empty only after normalization.

## Procedure and results

### Python 3.11 focused tests

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest tests.test_crawler.CrawlerHelperTests.test_markitdown_normalization_removes_only_unicode_controls tests.test_crawler.CrawlerHelperTests.test_crawl_local_file_normalizes_markitdown_control_characters tests.test_crawler.CrawlerHelperTests.test_crawl_pdf_normalizes_markitdown_control_characters tests.test_crawler.CrawlerHelperTests.test_local_document_rejects_output_emptied_by_normalization -v
```

Result: 4 tests passed in 0.006 seconds.

### Python 3.11 full non-live suite

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q
```

Result: 426 tests passed in 25.946 seconds. Two existing expected cleanup-warning fixtures wrote warnings for intentionally unremovable temporary plan artifact directories; the suite passed.

### Python 3.13 focused and full non-live suites

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest tests.test_crawler.CrawlerHelperTests.test_markitdown_normalization_removes_only_unicode_controls tests.test_crawler.CrawlerHelperTests.test_crawl_local_file_normalizes_markitdown_control_characters tests.test_crawler.CrawlerHelperTests.test_crawl_pdf_normalizes_markitdown_control_characters tests.test_crawler.CrawlerHelperTests.test_local_document_rejects_output_emptied_by_normalization -v
PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q
```

Result: 4 focused tests passed in 0.005 seconds; 426 full-suite tests passed in 23.377 seconds. The same two expected cleanup-warning fixtures wrote warnings; the suite passed.

### Static and diff hygiene

```bash
python3 - <<'PY'
from pathlib import Path
for path in [Path('src/buoy_search/crawler.py'), Path('tests/test_crawler.py')]:
    compile(path.read_text(encoding='utf-8'), str(path), 'exec')
print('compiled 2 changed Python files')
PY
git diff --check
```

Result: both changed Python files compiled and `git diff --check` reported no errors.

### Distribution build

```bash
rm -rf /tmp/buoy-markitdown-normalization-dist
uv build --out-dir /tmp/buoy-markitdown-normalization-dist
```

Result: `buoy_search-0.4.0-py3-none-any.whl` and `buoy_search-0.4.0.tar.gz` built successfully outside the repository.

## What this supports

- PDF and non-PDF MarkItDown paths share normalization before generated artifacts and chunks.
- Embedded NUL, C0/C1 examples, and every character categorized by Python as `Cc` are removed by the category predicate, except `\n`, `\r`, and `\t`.
- Markdown structure, ordinary Markdown whitespace, valid Unicode text, and emoji remain.
- Output containing only removable controls triggers the existing clear empty-extraction failure before the output directory is created.
- Existing non-live behavior passes the complete test suite on supported Python 3.11 and 3.13.

## Hosted validation and pull request

Implementation commit `403d4f9` was pushed on branch `work/restore-markitdown-normalization` and opened as PR #52: <https://github.com/Doctacon/buoy-search/pull/52>.

GitHub Actions run `29713256945` passed:

- Python 3.11: passed in 43 seconds;
- Python 3.13: passed in 44 seconds;
- distribution build: passed in 10 seconds.

## Limits

- No OCR, semantic cleanup, converter change, live apply, Turbopuffer call, or external source crawl was performed.
- Independent review remains required; this evidence does not close the active ticket.
- The task worktree did not merge PR #52.
