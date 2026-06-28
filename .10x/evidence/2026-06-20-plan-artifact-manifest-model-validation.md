Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-plan-artifact-manifest-model.md, .loom/specs/generic-site-rag-incremental-plan-apply.md

# Plan Artifact Manifest Model Validation

## What was observed

Implemented local-only plan artifact models and deterministic artifact hashing for generic site RAG plans.

Changed implementation files:

- `src/turbo_search/plan_artifacts.py`
- `tests/test_plan_artifacts.py`
- `.loom/tickets/2026-06-20-plan-artifact-manifest-model.md`

The implementation adds typed dataclass models for:

- `plan.json`
- `manifest.json`
- `chunks.jsonl`
- page manifest records
- chunk manifest records

The model computes deterministic artifact hashes from normalized page/chunk/option/manifest payloads and intentionally excludes volatile `crawl_timestamp` frontmatter from hash inputs.

No credentials were accessed. No embedding model was loaded. No turbopuffer calls or live writes/evals were run.

## Procedure

Commands run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_plan_artifacts -v
```

Result: 6 tests ran OK.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Result: 33 tests ran OK.

```bash
uv run python -m unittest discover -s tests -v
```

Result: 33 tests ran OK.

```bash
PYTHONPATH=src python3 -m compileall -q src tests
```

Result: passed with no output.

## What this supports

This supports the ticket acceptance criteria:

- plan/manifest/chunk artifact schema is represented by typed Python structures;
- serialization and artifact hashing are deterministic;
- artifact hash changes when content or relevant options change;
- artifact hash does not change only because generated crawl timestamp frontmatter changes;
- `plan.json` includes schema version, plan ID, site ID, base URL, namespace, state path, options, artifact hash, and diff placeholder fields;
- `manifest.json` records desired pages and chunks;
- `chunks.jsonl` is generated and parseable;
- existing crawl/index/retrieval tests still pass.

## Limits

This evidence does not prove the future `turbo-search plan` CLI or apply workflow. Those are covered by later child tickets. It also does not verify live turbopuffer schema/delete behavior because live calls are out of scope for this ticket.
