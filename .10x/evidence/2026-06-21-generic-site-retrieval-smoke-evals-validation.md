Status: recorded
Created: 2026-06-21
Updated: 2026-06-21
Relates-To: .loom/tickets/2026-06-20-generic-site-retrieval-smoke-evals.md, .loom/specs/generic-site-rag-incremental-plan-apply.md

# Generic Site Retrieval Smoke Evals Validation

## What was observed

Implemented lightweight generic-site retrieval/eval validation support.

Changed files for this ticket:

- `src/turbo_search/cli.py`
- `src/turbo_search/evals.py`
- `src/turbo_search/data/scrapling_retrieval_smoke_evals.json`
- `tests/test_cli.py`
- `tests/test_evals.py`
- `README.md`
- `docs/generic-site-rag-plan-apply.md`
- `.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md`
- `.loom/tickets/2026-06-20-generic-site-retrieval-smoke-evals.md`

Key behavior added:

- `turbo-search retrieve` accepts non-secret runtime overrides: `--namespace`, `--region`, and `--embedding-model`.
- `turbo-search evals` accepts the same runtime overrides.
- Environment defaults remain supported through `TURBOPUFFER_REGION`, `TURBOPUFFER_NAMESPACE`, and `TURBO_SEARCH_EMBEDDING_MODEL`.
- Added `src/turbo_search/data/scrapling_retrieval_smoke_evals.json` with Scrapling docs questions and expected URL/topic hints.
- Dry-run retrieve/evals with generic namespace overrides remain credential-free and turbopuffer-free.
- Live retrieve/evals remain explicitly gated by `--live` and still fail before embedding/querying when `TURBOPUFFER_API_KEY` is absent.

No credentials were read. No `TURBOPUFFER_API_KEY` value was set or inspected. No live retrieval, live evals, live writes, or turbopuffer calls were run.

## Procedure

Targeted tests:

```bash
PYTHONPATH=src python3 -m unittest tests.test_cli tests.test_evals -v
```

Result: 20 tests ran OK.

Full local unit suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Result: 75 tests ran OK.

Full uv unit suite:

```bash
uv run python -m unittest discover -s tests -v
```

Result: 75 tests ran OK.

Compile checks:

```bash
PYTHONPATH=src python3 -m compileall -q src tests
uv run python -m compileall -q src tests
```

Result: both passed with no output.

Generic eval dry-run smoke, no credentials or turbopuffer calls:

```bash
uv run turbo-search evals \
  --dry-run \
  --dataset src/turbo_search/data/scrapling_retrieval_smoke_evals.json \
  --namespace site-scrapling-readthedocs-io-v1 \
  --region gcp-us-central1 \
  --top-k 4 \
  --candidates 40 \
  --json
```

Observed summary:

```text
command=evals dry_run=True credentials_required=False turbopuffer_api_calls=False namespace=site-scrapling-readthedocs-io-v1 region=gcp-us-central1 top_k=4 candidates=40 total=4
```

Generic retrieve dry-run smoke, no credentials or turbopuffer calls:

```bash
uv run turbo-search retrieve \
  "How does Scrapling LinkExtractor filter links?" \
  --dry-run \
  --namespace site-scrapling-readthedocs-io-v1 \
  --region gcp-us-central1 \
  --json
```

Observed summary:

```text
command=retrieve dry_run=True credentials_required=False turbopuffer_api_calls=False namespace=site-scrapling-readthedocs-io-v1 region=gcp-us-central1
```

No staged files check:

```bash
git diff --cached --name-only
```

Result: no output.

## What this supports

This supports the ticket acceptance criteria:

- retrieval and eval commands can target a generic namespace/region/model through CLI flags without code changes;
- a Scrapling docs eval dataset exists with expected URL/topic hints;
- dry-run/list modes remain credential-free and turbopuffer-free;
- live modes remain explicitly gated by `--live` and environment credentials;
- tests and docs were updated;
- no live retrieval/eval or credential access occurred.

## Limits

This evidence does not prove live retrieval quality against an applied Scrapling namespace because no live namespace has been approved or queried for this ticket. The Scrapling eval dataset is a smoke set, not a comprehensive benchmark.
