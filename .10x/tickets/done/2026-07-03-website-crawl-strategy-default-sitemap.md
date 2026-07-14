Status: done
Created: 2026-07-03
Updated: 2026-07-03

# Website Crawl Strategy Default Sitemap

## Scope

Change ordinary website `crawl` and `plan` defaults so sitemap discovery is the default crawl strategy. If sitemap pages exist, do not continue into broad link crawling unless the user explicitly chooses it. Link crawl remains available as either explicit `--crawl-strategy link` or fallback when sitemap discovery yields no pages. Exhaustive sitemap-plus-link behavior remains available as explicit `--crawl-strategy hybrid`.

In scope:

- Change `DEFAULT_CRAWL_STRATEGY` from `hybrid` to `sitemap`.
- Update CLI help to explain the new default and explicit hybrid mode.
- Update tests for default strategy and sitemap fallback behavior.
- Update README, generic workflow docs, and site-planning knowledge.

Out of scope:

- Removing `hybrid` or `link` strategies.
- Changing live apply behavior.
- Changing GitHub repository ingestion behavior.

## Acceptance criteria

- Default `crawl`/`plan` options use `sitemap` when no strategy flag is passed.
- A non-empty sitemap result does not run the link crawler.
- Empty sitemap results still fall back to link crawling.
- `--crawl-strategy hybrid` remains available for explicit exhaustive sitemap-plus-link discovery.
- Unit tests pass.

## Progress and notes

- 2026-07-03: User confirmed default should be sitemap-only when available, with link crawling only when explicitly requested or as a backup when no sitemap pages are available.
- 2026-07-03: Implemented default strategy change, CLI help update, docs/knowledge updates, and tests for default sitemap-only behavior plus empty-sitemap link fallback.

## Blockers

- None.

## Evidence

- `.10x/evidence/2026-07-03-website-crawl-strategy-default-validation.md`

## References

- `.10x/specs/website-crawl-strategy-default.md`
- `.10x/knowledge/buoy-site-planning-workflow.md`
