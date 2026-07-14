Status: active
Created: 2026-07-14
Updated: 2026-07-14

# Buoy Brand Assets and Documentation

## Purpose and scope

Apply the Buoy identity consistently to the showcase landing page, focused docs, operational skills, and repository assets without rewriting historical provenance.

## Visual identity

- Commit an original, dependency-free SVG at `images/buoy.svg` using deep navy (`#0B1F33`), signal orange (`#FF6B35`), and white.
- The mark MUST remain legible at README/logo scale and in monochrome-like contexts. It SHOULD depict a minimal buoy with stacked bands and restrained signal rings; it MUST avoid gradients, embedded fonts, remote assets, and generic AI sparkle imagery.
- README MUST use the SVG with accessible alt text. The old puffin asset MUST be removed once no active reference remains.

## Documentation

- README MUST retain the details-on-demand structure governed by `.10x/knowledge/documentation-details-on-demand.md` while changing the product name, tagline, commands, paths, and install examples to Buoy.
- Current docs and in-repository operational skills MUST use `buoy`, `buoy-search`, `buoy_search`, `.buoy`, and `BUOY_*` where applicable, while clearly documenting 0.2 compatibility aliases and legacy state fallback in one migration section rather than repeating it everywhere.
- Add a concise migration guide covering CLI alias lifetime, Python import clean break, environment-variable fallback, state-root resolution, old plan compatibility, and unchanged remote namespaces/row IDs.
- Active specifications, knowledge, and open tickets MUST be repaired when paths or current identity references change. Done/cancelled tickets, evidence, reviews, research, accepted decision rationale, and other historical records MUST retain old names when they describe historical facts.
- Bundled self-search eval data MUST be updated for the new repository/module paths and product questions; relevance labels affected by path changes MUST be reviewed rather than blindly replaced.

## Operational limits

- Documentation MUST not claim GitHub repository rename or package publication before those external actions occur.
- No live Turbopuffer operation is part of branding documentation validation.

## Verification

Local links, SVG validity, asset references, CLI command parsing, details-on-demand README limits, active-record coherence, skill command accuracy, and self-search eval fixture behavior MUST be validated.
