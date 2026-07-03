Status: done
Created: 2026-07-02
Updated: 2026-07-02
Depends-On: .10x/tickets/done/2026-07-02-docs-version-warning-visibility.md

# Docs Version Default Stop

## Scope

Change default website docs-version behavior so detected duplicated version docs stop the run before page crawling unless the user chooses an explicit policy.

In scope:

- Default `--docs-version-policy warn` detects versioned docs and aborts before crawling pages.
- Error text tells the user to rerun with `latest`, `stable-latest`, `latest-nightly`, or `all`.
- Explicit policies continue to work: `latest`, `stable-latest`, and `latest-nightly` filter; `all` keeps every version.
- Update spec, docs, tests, and validation evidence.

Out of scope:

- Changing the default to auto-filter.
- Live turbopuffer writes.

## Acceptance criteria

- `turbo-search plan "https://iceberg.apache.org/"` stops after detecting versioned docs and exits non-zero before page crawling.
- `--docs-version-policy latest` proceeds with effective excludes.
- `--docs-version-policy all` proceeds without automatic filtering.
- Unit tests pass.

## Progress and notes

- 2026-07-02: User confirmed “Stop by default” when versioned docs are detected under the default policy.
- 2026-07-02: Changed default `warn` policy to raise before page crawling, updated docs/spec/tests, and validated with Iceberg sitemap detection plus explicit `latest` policy.

## Blockers

- None.

## Evidence

- `.10x/evidence/2026-07-02-docs-version-default-stop-validation.md`

## References

- `.10x/specs/website-docs-version-policy.md`
