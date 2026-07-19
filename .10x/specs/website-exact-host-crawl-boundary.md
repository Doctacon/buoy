Status: active
Created: 2026-07-18
Updated: 2026-07-18

# Website Exact-Host Crawl Boundary

## Purpose and scope

A Buoy website crawl MUST remain on the exact hostname reviewed in its base URL across discovery, sitemap/robots acquisition, page requests, and every redirect hop. This is a crawl-boundary safety contract, not a general SSRF defense.

This contract is record-backed by the user-ratified historical ticket at `thistle-site-test@d7a37d7:.10x/tickets/done/2026-07-11-block-cross-host-crawl-redirects.md`, its local destination-side evidence, and its independent pass review. Those dirty-branch records describe the superseded `turbo_search`/Qdrant implementation and are historical evidence only; they are indexed in `.10x/research/2026-07-18-thistle-qdrant-dead-end-disposition.md` and do not govern current source.

## Behavior

- The allowed hostname MUST be the lowercase hostname of the validated base URL. Port is not part of hostname identity.
- A discovered HTTP(S) URL whose hostname differs from the allowed hostname MUST be rejected before scheduling or requesting it. Sibling and child subdomains are out of scope unless separately crawled from their own base URL.
- Automatic redirect following MUST NOT permit a request to an unreviewed hostname. Every redirect target MUST be resolved and validated before the next request.
- Same-host redirects MAY continue when they pass existing robots, include/exclude path, and request-limit rules.
- Sitemap and robots fetches MUST enforce the same redirect boundary before requesting a redirect destination.
- Sitemap and robots declarations outside the exact hostname MUST be rejected before request.
- Redirect chains MUST be bounded to at most 20 hops.
- Crawl output MUST report count-only blocked-discovery and blocked-redirect totals separately. It MUST NOT expose blocked URLs, redirect locations, query strings, or credentials in summaries/errors.
- Existing robots enforcement, crawl strategies, path filters, caps, delays, concurrency, canonicalization, and trusted-local base-URL model MUST remain unchanged.

## Acceptance criteria

- A local two-server fixture proves sibling-subdomain, external-host, protocol-relative, OAuth-shaped, chained, and open-redirect destinations receive zero requests.
- Fixtures cover same-host one-hop and multi-hop redirects, robots-denied same-host targets, sitemap/robots redirects, and the 20-hop limit.
- Final response URLs are checked even if an underlying client redirects unexpectedly.
- JSON/text summaries distinguish blocked discovered URLs and redirect targets using counts only.
- Focused crawler and full non-live validation pass without a live crawl or remote-service operation.

## Explicit exclusions

Registrable-domain/subdomain expansion, service-grade DNS/IP/private-network SSRF policy, a Thistle/Mercury rerun, Turbopuffer writes, or changing source authorization.
