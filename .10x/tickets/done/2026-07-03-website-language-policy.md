Status: done
Created: 2026-07-03
Updated: 2026-07-03

# Website Language Policy

## Scope

Add default website language duplicate handling so ordinary site plans avoid indexing detected non-English localized URL families when the intended corpus is English.

In scope:

- Add `--language-policy {english,all}` to `crawl` and `plan`.
- Default to `english` for website planning/crawling.
- Detect sitemap locale-prefix families such as `/de/**`, `/fr/**`, `/pt-br/**`, and `/zh-cn/**`.
- Add effective exclude-path filters for detected non-English locale prefixes under the default policy.
- Preserve `--language-policy all` as an explicit opt-out.
- Record language policy/report fields in crawl and plan summaries/artifacts.
- Update tests and user-facing docs.

Out of scope:

- Live turbopuffer writes.
- Translating, canonicalizing, or semantically deduplicating page content across languages.
- Sitemap language filtering for `--crawl-strategy link`, which intentionally ignores sitemap pre-analysis.

## Acceptance criteria

- Blowfish-style sitemap URLs produce effective excludes for `/de/**`, `/es/**`, `/fr/**`, `/it/**`, `/ja/**`, `/pt-br/**`, `/pt-pt/**`, and `/zh-cn/**` under default `--language-policy english`.
- `--language-policy all` does not add language-derived exclude filters.
- `crawl` and `plan` help expose `--language-policy`.
- Unit tests pass.
- Documentation explains the default and opt-out.

## Progress and notes

- 2026-07-03: User reported `https://blowfish.page/` planning discovered about 1400 pages because localized paths such as `/de/samples/` duplicated the English corpus; user stated only English pages matter.
- 2026-07-03: Implemented sitemap pre-analysis language policy, CLI flag, summaries, tests, README/docs updates, and durable workflow knowledge update.
- 2026-07-03: Added a tail-overlap signal so a single ordinary section named like a language code is less likely to be treated as localization unless it overlaps unprefixed/English page paths.

## Blockers

- None.

## Evidence

- `.10x/evidence/2026-07-03-website-language-policy-validation.md`

## References

- `.10x/specs/website-language-policy.md`
- `.10x/knowledge/buoy-site-planning-workflow.md`
