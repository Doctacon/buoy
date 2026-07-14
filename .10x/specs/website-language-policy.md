Status: active
Created: 2026-07-03
Updated: 2026-07-03

# Website Language Policy

## Purpose and scope

`buoy crawl` and `buoy plan` SHOULD help users avoid indexing duplicated non-English localized pages when the intended website RAG corpus is English.

This specification governs ordinary website sources only. GitHub repository ingestion is out of scope.

## Behavior

For sitemap-based website crawls, the system MUST inspect sitemap URLs before page crawling when the language policy is not `all` and the crawl strategy is not `link`.

The CLI MUST support these website language policy values:

- `english` default: keep unprefixed pages and English locale-prefixed pages such as `/en/**`, while adding effective exclude-path filters for detected non-English locale prefixes.
- `all`: keep every language and suppress automatic language filtering.

The system MUST detect a multilingual locale-prefix family from sitemap URLs before applying automatic excludes. Locale prefixes are first path segments that look like supported language tags such as `/de/**`, `/fr/**`, `/it/**`, `/ja/**`, `/pt-br/**`, `/pt-pt/**`, or `/zh-cn/**`.

To reduce false positives, automatic `english` filtering MUST require:

- at least 20 non-English locale-prefixed sitemap URLs;
- either at least two non-English locale prefixes or at least five path-tail overlaps between non-English locale pages and unprefixed/English pages;
- evidence of English content through unprefixed sitemap URLs or `/en/**`-style sitemap URLs.

Policy filtering MUST be implemented as additional effective exclude-path filters for detected non-English locale prefixes so other unprefixed site pages remain eligible. User-provided include/exclude path filters still apply.

Successful JSON summaries MUST include the requested `language_policy` and a `language_report` object with at least:

- `detected`
- `policy`
- `applied`
- `non_english_locales`
- `excluded_languages` when applicable
- `non_english_url_count`
- `unprefixed_url_count`
- `url_count_by_language`
- `tail_overlap_count_by_language`
- `added_exclude_paths` when applicable

Text summaries SHOULD report applied language filtering and the excluded locale prefixes.

## Acceptance scenarios

### Default English policy filters duplicated localized pages

Given a website sitemap contains unprefixed English pages and repeated locale-prefixed pages such as `/de/samples/`, `/fr/samples/`, and `/zh-cn/samples/`
When the user runs `buoy plan https://example.com/` with the default policy
Then non-English locale prefixes are added as effective exclude-path filters
And unprefixed pages remain eligible.

### Multilingual opt-out keeps every language

Given the same sitemap
When the user runs with `--language-policy all`
Then no language-derived exclude-path filters are added.

### Link-only crawls do not claim sitemap language detection

Given the user runs with `--crawl-strategy link`
Then the system MUST NOT claim sitemap-derived language detection or filtering.
