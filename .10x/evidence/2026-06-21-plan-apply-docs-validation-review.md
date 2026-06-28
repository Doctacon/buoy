Status: recorded
Created: 2026-06-21
Updated: 2026-06-21
Relates-To: .loom/tickets/2026-06-20-plan-apply-docs-validation-review.md, .loom/specs/generic-site-rag-incremental-plan-apply.md

# Plan/Apply Docs Validation Review Evidence

## What was observed

Documentation and skill guidance were updated to distinguish the generic website RAG modes:

- `turbo-search plan`: local-only crawl/extract/chunk/diff and review artifacts.
- `turbo-search apply` without `--approve`: local-only preflight verification, no credentials/embeddings/turbopuffer calls.
- `turbo-search apply --approve`: explicit live upsert path, requiring `TURBOPUFFER_API_KEY` from the environment.
- `--delete-stale`: separate stale-row delete guardrail; live delete requires both `--approve` and `--delete-stale`.

Changed files for this ticket:

- `README.md`
- `docs/generic-site-rag-plan-apply.md`
- `.pi/skills/turbopuffer-site-rag/SKILL.md`
- `.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md`
- `.loom/tickets/2026-06-20-plan-apply-docs-validation-review.md`

Tests were not added or changed in this docs/validation ticket. Existing tests from implementation tickets already cover no-credential/no-live-call plan and apply preflight behavior.

No credentials were read. No `TURBOPUFFER_API_KEY` value was set or inspected. No live turbopuffer writes, deletes, evals, or retrievals were run.

## Procedure

Full local unit tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Result: 70 tests ran OK.

Full uv unit tests:

```bash
uv run python -m unittest discover -s tests -v
```

Result: 70 tests ran OK.

Compile checks:

```bash
PYTHONPATH=src python3 -m compileall -q src tests
uv run python -m compileall -q src tests
```

Result: both passed with no output.

Real-network local-only plan smoke against Scrapling docs:

```bash
rm -rf artifacts/site-crawls/scrapling-readthedocs-io-plan-docs-validation-smoke && \
uv run turbo-search plan \
  --base-url "https://scrapling.readthedocs.io/en/latest/" \
  --out-dir artifacts/site-crawls/scrapling-readthedocs-io-plan-docs-validation-smoke \
  --state-root artifacts/site-crawls/scrapling-readthedocs-io-plan-docs-validation-smoke-state \
  --max-pages 3 \
  --max-chunks 15 \
  --css-selector ".md-content__inner" \
  --json
```

Result: passed. Key output:

```json
{
  "command": "plan",
  "dry_run": true,
  "credentials_required": false,
  "turbopuffer_api_calls": false,
  "api_calls_occurred": false,
  "crawl_strategy": "sitemap",
  "pages_scraped": 3,
  "chunks_generated": 15,
  "rows_to_upsert": 15,
  "state_first_apply": true,
  "namespace": "site-scrapling-readthedocs-io-v1"
}
```

Private identifier / secret-adjacent grep:

- Searched the repository for the exact private vault/item identifiers previously objected to by the user. Result: no output. The literal private identifiers are intentionally not reproduced in this evidence record.
- Searched for concrete `TURBOPUFFER_API_KEY` assignments, Bearer-token-looking values, common API-key-looking values, and `pass-cli item view` invocations with concrete quoted vault/item values. Result: no output.
- Searched docs/skill/Loom records for credential lookup placeholders and pass-cli option mentions. Result: only generic placeholders and safety notes were found; no private vault names, private item titles, share IDs, tokens, or API key values were found.

No staged files check:

```bash
git diff --cached --name-only
```

Result: no output.

## What this supports

This supports the ticket acceptance criteria:

- README, docs, and skill references distinguish plan, apply preflight, approved apply, and `--delete-stale`.
- Plan and preflight safety are documented as local-only.
- Approved apply is documented as live and requiring explicit approval plus an environment API key.
- Validation evidence was gathered with full tests, compile checks, grep checks, and a safe real-network Scrapling docs plan smoke.
- No private credential identifiers or secret values were found by exact/private-pattern grep.
- No live turbopuffer write/delete/eval/retrieval or credential access occurred.

## Limits

This evidence does not prove live turbopuffer SDK compatibility for generic upserts/deletes because live writes/deletes were intentionally out of scope. The real-network smoke only contacted the public Scrapling docs site for crawling and did not contact turbopuffer.
