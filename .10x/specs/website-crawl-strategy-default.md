Status: active
Created: 2026-07-03
Updated: 2026-07-03

# Website Crawl Strategy Default

## Purpose and scope

`buoy crawl` and `buoy plan` SHOULD make sitemap-based website planning predictable by default. When a website publishes sitemap URLs, the default crawl SHOULD use those URLs only instead of silently continuing into broad same-site link discovery after the sitemap pass completes.

This specification governs ordinary website sources. GitHub repository ingestion remains first-class git ingestion and is out of scope.

## Behavior

The default website crawl strategy MUST be `sitemap`.

`--crawl-strategy sitemap` MUST:

- run robots/sitemap discovery first;
- crawl eligible sitemap pages when sitemap discovery yields pages;
- NOT run link crawling after a non-empty sitemap crawl;
- fall back to same-site link crawling only when sitemap crawling yields zero pages.

`--crawl-strategy link` MUST ignore sitemap URLs and crawl same-site links from the base URL.

`--crawl-strategy hybrid` MUST be explicit exhaustive mode: crawl sitemap pages, then crawl same-site links from the base URL, and merge unique pages.

All crawl strategies MUST continue to obey robots.txt, host restrictions, include/exclude path filters, page caps, concurrency, and delay settings.

## Acceptance criteria

- Running `buoy plan https://example.com/` without `--crawl-strategy` uses requested crawl strategy `sitemap`.
- A non-empty sitemap crawl does not run the link spider.
- An empty sitemap crawl falls back to link crawling and reports `link_fallback`.
- CLI help describes `sitemap` as the default and `hybrid` as explicit merged sitemap+link mode.
