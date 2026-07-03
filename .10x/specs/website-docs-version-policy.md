Status: active
Created: 2026-07-02
Updated: 2026-07-02

# Website Docs Version Policy

## Purpose and scope

`turbo-search crawl` and `turbo-search plan` SHOULD help users avoid indexing large families of duplicated versioned documentation unless they explicitly want the full historical corpus.

This specification governs ordinary website sources only. GitHub repository ingestion is out of scope.

## Behavior

### Detection

For sitemap-based website crawls, the system MUST inspect sitemap URLs before page crawling when the docs version policy is not `all`.

The system MUST detect a versioned docs family when a shared path prefix contains at least three version-like child path segments and at least thirty matching sitemap page URLs after host, include-path, exclude-path, and trailing-slash normalization filters.

Version-like child path segments include:

- semantic versions such as `1.10.2` or `v2.0.0`;
- moving current aliases such as `latest`, `current`, or `stable`;
- moving preview aliases such as `nightly`, `main`, `master`, `dev`, or `snapshot`.

Given `https://iceberg.apache.org/docs/1.10.2/configuration/` and `https://iceberg.apache.org/docs/latest/configuration/`, the detected versioned family is `/docs/{version}/...`.

### Policy values

The CLI MUST support these website docs version policy values:

- `warn` default: detect versioned docs and stop before page crawling with a message that asks the user to choose an explicit policy.
- `all`: keep all pages and suppress automatic docs-version filtering.
- `latest`: keep moving current aliases (`latest`, `current`, `stable`) when present; otherwise keep the highest semantic version. Exclude other detected versions in the same family.
- `stable-latest`: keep the highest semantic version and exclude aliases/previews and older semantic versions in the same family.
- `latest-nightly`: keep moving current aliases plus preview aliases (`nightly`, `main`, `master`, `dev`, `snapshot`) when present. If no current alias is present, keep the highest semantic version. Exclude other detected versions in the same family.

Policy filtering MUST be implemented as additional effective exclude-path filters for non-selected version prefixes so non-versioned site pages, blogs, specs, and releases remain eligible.

### Reporting

Text summaries SHOULD report detected docs version families, selected versions when filtering is applied, and excluded version count. If the default warning policy detects a large versioned family, the run MUST stop before page crawling and the error text MUST suggest an explicit filtering policy and `all`.

Successful JSON summaries MUST include the requested policy and a `docs_version_report` object with at least:

- `detected`
- `policy`
- `root_path` when detected
- `version_count` when detected
- `versioned_url_count` when detected
- `selected_versions` when applicable
- `excluded_versions` when applicable
- `added_exclude_paths` when applicable
- `suggested_policy` when applicable

## Acceptance scenarios

### Default warning stops before crawl

Given a website sitemap contains `/docs/1.9.0/...`, `/docs/1.10.2/...`, and `/docs/latest/...`
When the user runs `turbo-search plan https://example.com/` with the default policy
Then the run stops before page crawling
And the error reports that versioned docs were detected
And the error suggests `--docs-version-policy latest` or another explicit policy.

### Latest policy prunes historical docs

Given the same sitemap
When the user runs `turbo-search plan https://example.com/ --docs-version-policy latest`
Then `/docs/latest/**` remains eligible
And old `/docs/<semver>/**` prefixes are excluded
And non-versioned pages such as `/blog/**` remain eligible.

### Stable latest policy is reproducible

Given a sitemap contains semantic versions `1.10.1` and `1.10.2` plus `latest`
When the user runs with `--docs-version-policy stable-latest`
Then only `/docs/1.10.2/**` remains eligible from that versioned family.

### Link-only totals remain dynamic

Given the user runs with `--crawl-strategy link`
Then the system MUST NOT claim a sitemap-derived docs version estimate.
