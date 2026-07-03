Status: done
Created: 2026-07-02
Updated: 2026-07-02
Depends-On: .10x/tickets/done/2026-07-02-website-docs-version-policy.md

# Docs Version Warning Visibility

## Scope

Make default `--docs-version-policy warn` visible during long website plans instead of only appearing in the final text summary or transient one-line progress.

In scope:

- Explain the observed behavior: the default warning was summary-only/transient while the plan continued crawling.
- Emit a persistent early warning to stderr for text-mode `crawl`/`plan` after sitemap version analysis and before page crawling.
- Preserve clean JSON stdout; JSON summaries continue to include `docs_version_report`.
- Add tests and evidence.

Out of scope:

- Changing the default policy from `warn` to a filtering policy.
- Live turbopuffer writes.

## Acceptance criteria

- A default text-mode Iceberg-like plan surfaces a persistent warning before crawling pages.
- The warning says how to rerun with `--docs-version-policy latest` or `all`.
- Unit tests pass.

## Progress and notes

- 2026-07-02: User observed that `uv run turbo-search plan "https://iceberg.apache.org/"` did not visibly warn before continuing.
- 2026-07-02: Added persistent early stderr warning for text-mode default `warn` policy, plus tests and validation evidence.

## Blockers

- None.

## Evidence

- `.10x/evidence/2026-07-02-docs-version-warning-visibility-validation.md`

## References

- `.10x/specs/website-docs-version-policy.md`
