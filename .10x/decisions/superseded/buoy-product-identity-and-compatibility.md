Status: superseded
Created: 2026-07-14
Updated: 2026-07-14

# Buoy Product Identity and Compatibility

## Context

The project is becoming a showcase codebase. `turbo-search` describes speed but does not express the product's strongest qualities: source anchoring, navigation, provenance, and finding information again. “Buoy” provides that metaphor and supports a restrained nautical visual identity.

The bare name is crowded: an old `buoy` PyPI distribution exists and another active Buoy developer CLI uses the name. The technical identity therefore needs a unique distribution/repository name while preserving the short product and command name.

The current 0.1 codebase also has durable interfaces: `.turbo-search` DuckDB ledgers, old plan paths, `TURBO_SEARCH_*` environment configuration, installed CLI commands, deterministic `jf_*` row IDs, and applied Turbopuffer namespaces. A brand change must not silently lose state or force remote reindexing.

## Decision

- Product/display name: **Buoy**.
- Tagline: **Search that stays anchored to the source.**
- Repository target: `Doctacon/buoy-search`.
- Python distribution: `buoy-search`.
- Python import package: `buoy_search`.
- Primary CLI: `buoy`.
- Rebrand release: `0.2.0`.
- License: Apache License 2.0.
- Initial logo: a committed, original, minimal navy/orange SVG buoy with stacked bands and retrieval signal rings.
- Version 0.2 retains a deprecated `turbo-search` CLI alias and branded environment-variable fallbacks. Version 0.3 removes those aliases. Python imports make a clean break at 0.2; no `turbo_search` import shim is promised.
- New projects default to `.buoy`. Existing projects with only `.turbo-search` continue using that ledger in place with a warning. No automatic state move or copy occurs.
- Existing plan artifacts, deterministic row IDs, and remote namespace names remain compatible and are not rebranded in place.
- The pending float16 implementation is blocked until the source/package rebrand is integrated, then resumes against `buoy_search` and `BUOY_*` configuration.

## Alternatives considered

### Surface-only rebrand

Rejected. Keeping `turbo-search` as the package and command would make a showcase repository feel internally inconsistent and leave the technical identity tied to the old brand.

### Bare `buoy` distribution and repository

Rejected because package/developer-tool collisions reduce discoverability and create installation ambiguity.

### Immediate hard cutover

Rejected because it would silently ignore existing local ledgers and break common command/environment workflows without a transition.

### Automatic state copy or move

Rejected. Copying risks split-brain ledgers; moving mutates durable local state during a branding change. In-place fallback is smaller and safer.

### Permanent compatibility aliases

Rejected because they would make the old brand a continuing maintenance and documentation obligation.

## Consequences

The code, tests, bundled datasets, docs, skills, package metadata, lockfile, and repository-facing assets require coordinated changes. Existing Python imports break intentionally at 0.2, while CLI/environment users receive one migration release. Existing local and remote data identities remain stable. External GitHub repository mutation occurs only after code-level integration passes and the exact external action is confirmed.
