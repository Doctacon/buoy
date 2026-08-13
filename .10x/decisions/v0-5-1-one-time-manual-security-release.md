Status: active
Created: 2026-08-13
Updated: 2026-08-13

# v0.5.1 One-Time Manual Security Release

## Decision

Authorize one manual GitHub-only v0.5.1 release containing the GitHub
repository containment fix and minimum installation/first-index onboarding.
The write-capable workflow remains disabled.

The release must come from the separately reviewed and promoted `main` commit,
after the complete Python 3.11/3.13 and distribution checks pass. It creates an
annotated `v0.5.1` tag and a non-draft GitHub Release containing exactly the
`buoy_search-0.5.1-py3-none-any.whl` and `buoy_search-0.5.1.tar.gz` assets. The
downloaded assets must match the locally recorded SHA-256 digests, and the
published wheel must pass a clean install and offline CLI/tokenizer smoke test
before the draft security advisory is published. GitHub artifact attestations
for both assets are required when the authenticated GitHub tooling can create
and verify them without changing the assets; otherwise the exact signed tag,
source commit, and downloaded SHA-256 evidence remain the one-time manual
release authority and the evidence must record that limitation explicitly.

## Fail-closed boundary

The existing v0.5.0 lightweight tag and asset-less Release are immutable
history. If any v0.5.1 tag, Release, or asset exists before creation, or if a
write leaves partial hosted state, stop without moving, overwriting, or
deleting it and require a new reviewed recovery decision.

## Exclusions

No PyPI publication, Turbopuffer operation, namespace or stale-row mutation,
branch-protection change, direct or force push, reusable release automation,
or unrelated product work is authorized. Automatic publication remains paused
after v0.5.1.
