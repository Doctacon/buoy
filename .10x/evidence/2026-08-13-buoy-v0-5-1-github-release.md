Status: recorded
Created: 2026-08-13
Updated: 2026-08-13
Ticket: .10x/tickets/2026-08-13-ship-buoy-v0-5-1.md

# Buoy v0.5.1 GitHub Release Evidence

## Promoted source

- Containment PR #101 was squash-merged to `develop` as
  `f68dcf5f0a4352df59e14ca1d78bef1ea1b7f6ee` after public CI and independent
  integration review passed.
- Release PR #102 passed all four release-readiness jobs and was merge-committed
  to `main` as `284b309a02546b13a63e709d9afe7f72c557b474` by a separate release
  role. Exact-main CI passed.
- Annotated tag v0.5.1 has tag object
  `081b128c9f02761342e473e4faf7d034c7097627` and peels to that exact `main`
  commit.

## Published GitHub Release

- Release: https://github.com/Doctacon/buoy/releases/tag/v0.5.1
- Release ID: `369682440`
- Published: `2026-08-13T05:20:44Z`
- `buoy_search-0.5.1-py3-none-any.whl`: 513103 bytes; SHA-256
  `b79850464b4c968fc3a711941dbc5a395560cda4330f9fd49f090698d651741d`.
- `buoy_search-0.5.1.tar.gz`: 871801 bytes; SHA-256
  `13c67b5a73a7afc21f03015c3d518e094a001d028b570c8011a0902999e5eceb`.

The two published downloads were byte-identical to the once-built exact-main
artifacts. Their version metadata, package boundaries, CLI entry point, and
tokenizer passed distribution validation. The wheel installed cleanly from
the versioned GitHub asset and reported v0.5.1. The documented bounded public
repository `plan`, dry-run `apply`, and explicit-namespace dry-run `retrieve`
smoke path passed without provider calls. The local manual path had no Actions
OIDC issuer, so no provenance attestation was available; exact tag/source
binding and downloaded SHA-256 verification satisfied the recorded one-time
decision.

The earlier containment evidence preserves different candidate hashes from a
pre-integration commit and timestamp. Those candidate hashes are not presented
as the published artifact hashes above.

## Advisory and effect boundary

[GHSA-q6rp-r8g8-5xgh](https://github.com/Doctacon/buoy/security/advisories/GHSA-q6rp-r8g8-5xgh)
was published at `2026-08-13T05:25:48Z` with 0.5.1 as the patched version, no
CVE request, and the temporary private fork removed.

No PyPI publication, Turbopuffer operation, namespace or stale-row mutation,
branch-protection change, direct branch push, or force push occurred.
Automatic publication remains paused.
