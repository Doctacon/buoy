Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-python-prototype-scaffold.md

# Python prototype scaffold validation

## Scope validated

Created a minimal Python/uv scaffold for the Jellyfish docs turbopuffer RAG prototype. Validation stayed within scaffold-only boundaries:

- No secrets accessed.
- No Proton Pass access attempted.
- No turbopuffer API calls attempted.
- No indexing or retrieval executed against turbopuffer.
- Dependency installation was intentionally not run because `sentence-transformers` can trigger a large install/model-related environment setup; the safe `uv run --no-sync` module fallback was used instead.

## Changed files

- `.gitignore`
- `.loom/evidence/2026-06-20-python-prototype-scaffold-validation.md`
- `.loom/tickets/2026-06-20-python-prototype-scaffold.md`
- `README.md`
- `pyproject.toml`
- `src/turbo_search/__init__.py`
- `src/turbo_search/__main__.py`
- `src/turbo_search/cli.py`
- `src/turbo_search/config.py`
- `tests/test_cli.py`

## Tests added

- `tests/test_cli.py`
  - Verifies help text advertises dry-run scaffold commands.
  - Verifies `index` command reports dry-run/no-credentials/no-API-call defaults and baseline region/namespace.

## Commands run

### Help command fallback

Command:

```bash
PYTHONPATH=src uv run --no-sync python -m turbo_search --help
```

Result: passed

Output:

```text
Using CPython 3.13.0
Creating virtual environment at: .venv
usage: turbo-search [-h] [--version] {index,retrieve} ...

Scaffold CLI for Jellyfish docs RAG. Current subcommands are dry-run only and
require no credentials.

positional arguments:
  {index,retrieve}
    index           show the planned indexing configuration without contacting
                    turbopuffer
    retrieve        show the planned retrieval configuration without
                    contacting turbopuffer

options:
  -h, --help        show this help message and exit
  --version         show program's version number and exit
```

### Unit tests

Command:

```bash
PYTHONPATH=src uv run --no-sync python -m unittest discover -s tests
```

Result: passed

Output:

```text
..
----------------------------------------------------------------------
Ran 2 tests in 0.001s

OK
```

### Dry-run index preview

Command:

```bash
PYTHONPATH=src uv run --no-sync python -m turbo_search index --corpus-dir jellyfish-site-docs
```

Result: passed

Output:

```json
{
  "command": "index",
  "corpus_dir": "jellyfish-site-docs",
  "corpus_dir_exists": true,
  "credentials_required": false,
  "dry_run": true,
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "namespace": "jellyfish-site-docs-v1",
  "region": "gcp-us-central1",
  "status": "scaffold-only; indexing is not implemented in this ticket",
  "turbopuffer_api_calls": false
}
```

### Dry-run retrieve preview

Command:

```bash
PYTHONPATH=src uv run --no-sync python -m turbo_search retrieve "What does Jellyfish say about DORA metrics?"
```

Result: passed

Output:

```json
{
  "command": "retrieve",
  "credentials_required": false,
  "dry_run": true,
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "namespace": "jellyfish-site-docs-v1",
  "query": "What does Jellyfish say about DORA metrics?",
  "region": "gcp-us-central1",
  "status": "scaffold-only; retrieval is not implemented in this ticket",
  "turbopuffer_api_calls": false
}
```

### Syntax compilation

Command:

```bash
PYTHONPATH=src uv run --no-sync python -m compileall -q src tests
```

Result: passed

Output: none

### No staged files check

Command:

```bash
git diff --cached --quiet; echo "cached_diff_exit=$?"
```

Result: passed

Output:

```text
cached_diff_exit=0
```

## Validation output summary

- CLI module help works without credentials using the documented safe fallback.
- Dry-run `index` and `retrieve` commands explicitly report `credentials_required: false` and `turbopuffer_api_calls: false`.
- Unit tests pass.
- Syntax compilation passes.
- No files are staged.

## Residual risks

- `uv sync` and `uv run turbo-search --help` were not executed because installing `sentence-transformers` and related dependencies can be expensive in this scaffold-only ticket. The README documents `uv sync` as the normal install path and the validated no-sync module fallback for safe scaffold checks.
- Actual indexing, embedding model loading, turbopuffer client creation, writes, and retrieval are intentionally not implemented in this ticket.
