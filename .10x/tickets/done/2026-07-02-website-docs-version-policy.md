Status: done
Created: 2026-07-02
Updated: 2026-07-02
Depends-On: .10x/tickets/done/2026-07-02-sitemap-progress-estimates.md

# Website Docs Version Policy

## Scope

Implement `.10x/specs/website-docs-version-policy.md` for `turbo-search crawl` and `turbo-search plan`.

In scope:

- Add `--docs-version-policy` to website crawl/plan CLI flows with values `warn`, `all`, `latest`, `stable-latest`, and `latest-nightly`.
- Analyze sitemap URLs before page crawling when the policy is not `all`.
- Detect versioned docs families and report warnings/suggestions for the default `warn` policy.
- Apply policy filtering by adding effective exclude-path filters for non-selected version prefixes.
- Preserve non-versioned site pages and GitHub repository defaults.
- Add tests, docs/knowledge updates, and validation evidence.

Out of scope:

- Live turbopuffer writes.
- Link-only total estimation.
- A UI prompt/interactive confirmation flow.

## Acceptance criteria

- Default website plan/crawl can detect an Iceberg-like `/docs/{version}/...` sitemap family and report a suggestion without filtering.
- `--docs-version-policy latest` filters old version docs when a moving latest/current/stable alias exists.
- `--docs-version-policy stable-latest` filters to the highest semantic version.
- `--docs-version-policy latest-nightly` keeps current aliases plus preview aliases.
- `--docs-version-policy all` avoids automatic analysis/filtering.
- Plan artifacts and summaries record the effective policy/filter state.
- Unit tests pass.

## Progress and notes

- 2026-07-02: User approved building automatic detection/filtering after seeing Iceberg's duplicated version docs.
- 2026-07-02: Implemented `--docs-version-policy`, sitemap pre-analysis, warning/reporting, effective exclude filters for selected policies, tests, docs, and validation evidence.

## Blockers

- None.

## Evidence

- `.10x/evidence/2026-07-02-website-docs-version-policy-validation.md`

## References

- `.10x/specs/website-docs-version-policy.md`
