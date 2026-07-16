Status: active
Created: 2026-07-15
Updated: 2026-07-15

# Buoy Product Identity and Compatibility Through 0.3

## Context

`.10x/decisions/superseded/buoy-product-identity-and-compatibility.md` established Buoy's identity and scheduled deprecated `turbo-search` and `TURBO_SEARCH_*` aliases for removal in 0.3. The 0.3 release now has a substantial, independently reviewed semantic-routing scope. Removing compatibility aliases in the same release would add unrelated breakage and validation risk. The user explicitly chose to retain the aliases through 0.3 and move their removal target to 0.4.

The local `.turbo-search` state-root fallback was never scheduled for automatic removal by that alias decision. It remains governed separately and must not be conflated with command/environment aliases.

## Decision

- Retain the established identity: product **Buoy**, tagline **Search that stays anchored to the source.**, repository `Doctacon/buoy-search`, distribution `buoy-search`, package `buoy_search`, primary CLI `buoy`, Apache-2.0 license, and existing visual identity.
- Version 0.3 MUST retain the deprecated `turbo-search` console alias and branded `TURBO_SEARCH_*` environment fallbacks with their existing warning/conflict behavior.
- Their announced removal target becomes version 0.4. This is a schedule change, not permanent compatibility.
- Python imports remain a clean break at `buoy_search`; no `turbo_search` import shim is added.
- New projects continue to default to `.buoy`. Existing state-root fallback, old plan compatibility, deterministic IDs, and remote namespace identity remain governed by `.10x/specs/buoy-local-compatibility.md` and are not removed by the 0.3 release.
- The 0.3 release MUST update active specifications, changelog, migration/release documentation, and tests so no active authority still promises alias removal in 0.3.

This decision supersedes `.10x/decisions/superseded/buoy-product-identity-and-compatibility.md`.

## Alternatives considered

### Remove aliases in 0.3

Rejected by explicit user choice. It would mix unrelated compatibility removal into the semantic-routing release and enlarge regression risk.

### Remove all legacy compatibility

Rejected. State-root behavior is a separate compatibility contract, and no product-wide removal was ratified.

### Keep aliases indefinitely

Rejected. The old brand remains a maintenance obligation; this decision grants one additional release, not permanence.

## Consequences

Version 0.3 remains backward-compatible for installed command and branded environment-variable users. Documentation must change the announced target consistently to 0.4. A future 0.4 removal still requires an executable ticket, verification, and release notes; this decision does not itself authorize implementation before that release.
