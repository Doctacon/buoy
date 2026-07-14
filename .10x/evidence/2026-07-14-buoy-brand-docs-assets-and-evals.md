Status: recorded
Created: 2026-07-14
Updated: 2026-07-14
Relates-To: .10x/tickets/done/2026-07-14-buoy-brand-docs-assets-and-evals.md, .10x/specs/buoy-brand-assets-and-documentation.md

# Buoy Brand, Documentation, Assets, and Evals Validation

## What was observed

- `README.md` is a 94-line / 424-word details-on-demand landing page using product name **Buoy**, tagline “Search that stays anchored to the source,” primary `buoy` commands, `.buoy` state, and `images/buoy.svg`.
- `images/buoy.svg` is an original dependency-free SVG using `#0B1F33`, `#FF6B35`, and `#FFFFFF`. It contains a minimal banded buoy, restrained signal rings, waves, a title/description, no gradients, no fonts/text elements, and no remote assets.
- The old `images/puffin.png` has no current README/doc/skill/source consumer and was removed. Puffin references remaining in old autoresearch run output are historical captured content, not active consumers.
- `docs/indexing.md`, `docs/retrieval.md`, and `docs/evaluation.md` use current `buoy`, `buoy_search`, `.buoy`, and `BUOY_EMBEDDING_MODEL` interfaces. `docs/migrating-to-buoy.md` is the canonical compatibility guide for the 0.2 CLI alias, Python import break, environment fallback/conflict, state-root truth table, old plans, and unchanged remote identities.
- In-repository site-RAG skill/reference commands and paths use the primary Buoy identity while retaining the bounded legacy-state warning.
- Active behavioral specs and knowledge were repaired to current CLI/module/state paths. Historical evidence/progress names and the explicitly preserved `github-doctacon-turbo-search-v1` namespace remain unchanged.
- The bundled self-search dataset uses `buoy-search`, existing `src/buoy_search` judgments, and Buoy product questions. Its planning-safety case now distinguishes public source fetching from being local with respect to Turbopuffer.

## Procedure and results

### Asset, links, command shapes, and eval paths

A local Python validation parsed `images/buoy.svg`, asserted required colors and forbidden SVG features, resolved relative links in README plus all four `docs/*.md` files, parsed seven README command shapes through `buoy_search.cli.build_parser()` without dispatching them, loaded all self-search cases, and confirmed every judged repository path exists.

```text
svg=valid
markdown_files=5
command_shapes=7
eval_cases=10
judgments=33
README.md: 94 lines, 424 words
```

A current-surface search found no stale primary `uv run turbo-search`, `python -m turbo_search`, `src/turbo_search`, old README title, or puffin asset reference in README, docs, in-repository skills, active specs, or active knowledge. Remaining old-name references in user docs are limited to the migration/state compatibility contract. Remaining active-record references are compatibility requirements or historical eval evidence/semantic namespaces.

### Fixture autoresearch

```text
PYTHONDONTWRITEBYTECODE=1 uv run python -m buoy_search.autoresearch \
  --experiment autoresearch/experiments/repo-search-fixture-baseline.json \
  --out /tmp/buoy-brand-fixture.<temporary> \
  --json

status=passed
repo_search_score=100.0
passed=10/10
turbopuffer_api_calls=false
```

The first post-check looked for the aggregate score at the JSON root and failed because the result stores it under `repo_metrics`; inspection and the corrected assertion confirmed the values above. The runner itself succeeded on the first invocation and made no live call.

### Complete validation

```text
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q
Ran 226 tests in 6.528s
OK

uv lock --check
git diff --check
OK
```

The suite emitted the existing non-fatal temporary plan-cleanup warning and completed successfully.

## Changed files in this child

- `README.md`
- `docs/indexing.md`
- `docs/retrieval.md`
- `docs/evaluation.md`
- `docs/migrating-to-buoy.md`
- `images/buoy.svg`
- `images/puffin.png` (removed)
- `.pi/skills/turbopuffer-site-rag/SKILL.md`
- `.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md`
- `src/buoy_search/data/buoy_search_repo_search_seed_evals.json`
- `.10x/knowledge/documentation-details-on-demand.md`
- `.10x/knowledge/repo-search-ranking-defaults.md`
- `.10x/knowledge/buoy-site-planning-workflow.md` (renamed from the old brand path)
- `.10x/specs/approved-apply-throughput-measurement.md`
- `.10x/specs/compact-duckdb-applied-state.md`
- `.10x/specs/local-markitdown-document-source-ingestion.md`
- `.10x/specs/local-pdf-source-ingestion.md`
- `.10x/specs/plan-artifact-lifecycle-cleanup.md`
- `.10x/specs/repo-search-eval-autoresearch.md`
- `.10x/specs/website-crawl-strategy-default.md`
- `.10x/specs/website-docs-version-policy.md`
- `.10x/specs/website-language-policy.md`
- `.10x/specs/buoy-package-and-cli-identity.md`
- `.10x/tickets/2026-06-28-repo-oversize-source-indexing.md`
- `.10x/tickets/done/2026-07-03-website-crawl-strategy-default-sitemap.md` (knowledge-path reference repair only)
- `.10x/tickets/done/2026-07-03-website-language-policy.md` (knowledge-path reference repair only)
- `.10x/tickets/done/2026-07-14-buoy-brand-docs-assets-and-evals.md`

No application behavior or test file changed in this child.

## Preservation of pre-existing work

Eleven documentation/record paths were already staged before this child. The worker did not stage, unstage, reset, or alter the index; the staged path list remains the same eleven paths. Some of those files now also have unstaged Buoy updates layered over the preserved index. The repository is therefore not globally free of staged files.

## What this supports or challenges

Supports the visual, details-on-demand, migration, current-reference, skill, and self-search-eval requirements without claiming GitHub rename/package publication or executing live operations.

## Limits

- External web links were not network-checked.
- The repository/GitHub remote still has its pre-rename identity; current docs deliberately do not claim otherwise.
- Historical `.10x` prose and autoresearch outputs retain old names by design.
- Independent editorial/technical review is still required before ticket closure.
