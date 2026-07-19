Status: active
Created: 2026-07-10
Updated: 2026-07-18

# Sitemap Resource Limits

## Purpose and scope

Bound memory exposure during trusted-local website sitemap and robots discovery without adding service-grade SSRF controls.

This contract was user-ratified and implemented on historical commit `d7a37d79de7011d9b4c0a0180f8bcea6265a7f62`, but current `develop` does not contain its bounded reader. The historical branch record is provenance only; this file is the current governing contract.

## Behavior

- Robots response bodies MUST be limited to 512 KiB.
- Each compressed or uncompressed sitemap network response MUST be limited to 10 MiB transferred bytes.
- Each decompressed sitemap XML document MUST be limited to 50 MiB.
- Limit enforcement MUST be incremental; code MUST NOT first read or decompress an unbounded body and check afterward.
- Exceeding a limit MUST produce a clear error naming the URL, limit type, and configured ceiling. It MUST NOT silently treat an oversized sitemap as empty and broaden into link crawling.
- A sitemap declared as gzip by its URL or response headers, or detected as gzip by magic bytes, MUST fail closed with a clear malformed-gzip error when decompression fails. It MUST NOT broaden into link crawling.
- Existing sitemap-count and page-URL-count caps remain.
- The CLI/docs MUST state that website URLs are supplied by a trusted local operator. Private-network SSRF blocking is not part of this local CLI contract.

## Acceptance criteria

- Tests cover exact-boundary and over-limit robots bodies, compressed sitemap transfer, decompressed gzip output, malformed gzip, and multiple sitemap queue behavior.
- A gzip expansion bomb fixture is stopped before exceeding the decompressed ceiling.
- Existing normal sitemap discovery behavior does not regress.

## Explicit exclusions

- Service/multi-user URL ingestion.
- DNS/IP allowlists, redirect network validation, or private-address blocking.
- Scrapling page-body limits beyond sitemap/robots discovery unless separately evidenced and scoped.

## Provenance

Historical non-authoritative source paths at commit `d7a37d7`:

- `d7a37d7:.10x/specs/sitemap-resource-limits.md`
- `d7a37d7:.10x/tickets/done/2026-07-10-bound-sitemap-resource-usage.md`
- `d7a37d7:.10x/evidence/2026-07-10-sitemap-resource-limits.md`
- `d7a37d7:.10x/reviews/2026-07-10-sitemap-resource-limits-review.md`
