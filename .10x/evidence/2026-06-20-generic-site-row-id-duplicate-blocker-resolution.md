Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-generic-site-stable-row-ids-and-schema.md, .loom/reviews/2026-06-20-generic-site-plan-apply-phase1-review.md

# Generic Site Row ID Duplicate Blocker Resolution

## What was observed

Resolved the Phase 1 review blocker where repeated identical chunks in the same URL/section/content group could produce duplicate generic-site row IDs.

Changed implementation/test files:

- `src/turbo_search/plan_artifacts.py`
- `src/turbo_search/plan_diff.py`
- `tests/test_plan_artifacts.py`
- `tests/test_plan_diff.py`
- `.loom/tickets/2026-06-20-generic-site-stable-row-ids-and-schema.md`

Key behavior added/refined:

- Unique chunks keep the existing stable row ID based on `site_id + canonical_url + section_path + chunk_hash`.
- Duplicate chunks within the same URL/section/content group receive deterministic duplicate ordinals.
- Only non-zero duplicate ordinals are added into the row ID hash, so ordinary unique chunks do not churn.
- Duplicate disambiguation does not include page hash, page path, or chunk index in normal row identity.
- `ChunkManifestRecord` records `duplicate_ordinal` for review/debugging.
- `plan_diff` now validates desired manifest row IDs and fails clearly with `PlanDiffError` if duplicate row IDs reach diffing, preventing silent dictionary-collapse before apply.
- `PlanDocument` now includes `created_at`, resolving the minor Phase 1 review note.

No credentials were accessed. No embedding model was loaded. No turbopuffer API calls or live writes/evals were run.

## Procedure

Targeted validation:

```bash
PYTHONPATH=src python3 -m unittest tests.test_plan_artifacts tests.test_plan_diff -v
```

Result: 20 tests ran OK.

Full local test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Result: 55 tests ran OK.

Full uv test suite:

```bash
uv run python -m unittest discover -s tests -v
```

Result: 55 tests ran OK.

Compile check:

```bash
PYTHONPATH=src python3 -m compileall -q src tests
```

Result: passed with no output.

## What this supports

This supports the Phase 1 review blocker resolution:

- repeated identical chunks now get unique row IDs in generated plan artifacts;
- the generated IDs are deterministic across equivalent plan generations;
- normal unique chunks keep their previous stable identity behavior;
- the fix does not reintroduce page-hash-based churn;
- diff code cannot silently collapse duplicate desired row IDs.

## Limits

This evidence does not verify live turbopuffer writes or delete behavior. Exact live SDK compatibility remains a later apply-ticket responsibility.
