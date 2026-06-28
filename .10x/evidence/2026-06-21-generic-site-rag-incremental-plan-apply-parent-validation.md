Status: recorded
Created: 2026-06-21
Updated: 2026-06-21
Relates-To: .loom/tickets/2026-06-20-generic-site-rag-incremental-plan-apply.md, .loom/specs/generic-site-rag-incremental-plan-apply.md

# Generic Site RAG Incremental Plan/Apply Parent Validation

## What was observed

The generic site RAG plan/apply parent workflow was implemented across child tickets:

- local plan artifacts and deterministic manifests;
- stable generic-site row IDs and metadata;
- local applied-state store;
- incremental diff engine;
- `turbo-search plan` local-only artifact workflow;
- `turbo-search apply` preflight and approved upsert path;
- explicit `--delete-stale` stale-row delete guardrail;
- docs/skill updates and safe validation;
- generic namespace retrieval/eval dry-run support with a Scrapling docs eval dataset.

No live generic apply, live turbopuffer write/delete, live eval, live retrieval, or credential access was performed for this parent validation.

## Procedure

Full local unit suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Result: 76 tests ran OK after adding approved `--delete-stale`/no-stale rejection coverage.

Full uv unit suite:

```bash
uv run python -m unittest discover -s tests -v
```

Result: 76 tests ran OK after adding approved `--delete-stale`/no-stale rejection coverage.

Compile checks:

```bash
PYTHONPATH=src python3 -m compileall -q src tests
uv run python -m compileall -q src tests
```

Result: both passed with no output.

Apply preflight against the safe Scrapling docs plan smoke artifact:

```bash
uv run turbo-search apply \
  --plan artifacts/site-crawls/scrapling-readthedocs-io-plan-docs-validation-smoke/plan.json \
  --namespace site-scrapling-readthedocs-io-v1 \
  --state-root artifacts/site-crawls/scrapling-readthedocs-io-plan-docs-validation-smoke-state \
  --json
```

Observed key fields:

```json
{
  "command": "apply",
  "approved": false,
  "dry_run": true,
  "credentials_required": false,
  "turbopuffer_api_calls": false,
  "api_calls_occurred": false,
  "artifact_verified": true,
  "rows_to_upsert": 15,
  "rows_upserted": 0,
  "embeddings_generated": 0,
  "state_updated": false
}
```

Generic eval dry-run smoke:

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

Observed key fields:

```text
command=evals dry_run=True credentials_required=False turbopuffer_api_calls=False namespace=site-scrapling-readthedocs-io-v1 region=gcp-us-central1 top_k=4 candidates=40 total=4
```

Generic retrieve dry-run smoke:

```bash
uv run turbo-search retrieve \
  "How does Scrapling LinkExtractor filter links?" \
  --dry-run \
  --namespace site-scrapling-readthedocs-io-v1 \
  --region gcp-us-central1 \
  --json
```

Observed key fields:

```text
command=retrieve dry_run=True credentials_required=False turbopuffer_api_calls=False namespace=site-scrapling-readthedocs-io-v1 region=gcp-us-central1
```

Secret-adjacent and staging checks:

- Searched for literal `TURBOPUFFER_API_KEY` assignments with token-looking values: no matches.
- Searched for Bearer-token-looking values: no matches.
- Searched for `pass-cli item view` invocations with concrete quoted vault/item values: no matches.
- Checked staged files with `git diff --cached --name-only`: no output.

## What this supports

This supports the parent acceptance criteria:

- all child tickets were implemented and validated;
- plan/preflight are local-only and require no credentials;
- apply can verify artifacts before live work;
- approved apply is gated by `--approve` and environment credentials in tests;
- fake approved apply embeds/upserts only diff rows;
- fake stale delete requires `--delete-stale`, and approved `--delete-stale` with no stale rows fails before credential access/live work;
- local state records active and retained-stale rows;
- existing tests pass;
- docs distinguish plan, preflight, approved apply, and stale delete;
- generic retrieve/eval dry-runs can target a site namespace.

## Limits

This evidence does not prove live turbopuffer SDK behavior for generic upserts or deletes. Live generic apply/delete and live retrieval/evals remain blocked until explicit user approval for a specific namespace/site.
