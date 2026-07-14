Status: done
Created: 2026-07-14
Updated: 2026-07-14
Parent: .10x/tickets/done/2026-07-14-buoy-rebrand-plan.md
Depends-On: .10x/tickets/done/2026-07-14-buoy-core-package-rename.md, .10x/tickets/done/2026-07-14-buoy-local-compatibility.md

# Apply Buoy Brand to Docs, Assets, Skills, and Evals

## Scope

Implement `.10x/specs/buoy-brand-assets-and-documentation.md`: original SVG logo, details-on-demand README identity, focused docs, migration guide, in-repository operational skills, active-record references, and reviewed self-search eval data/path updates.

## Acceptance criteria

- Visual and documentation contracts in the governing spec are satisfied.
- README remains approximately 100 lines or fewer and does not duplicate migration/reference detail.
- Current commands/paths/configuration reflect the integrated code and compatibility behavior.
- Historical `.10x` facts are not mechanically rewritten.
- Self-search eval questions/judgments are reviewed for renamed module/repository paths and fixture validation passes.
- Old puffin and stale current-brand references have no active consumers before deletion.
- Local links, SVG parsing, CLI command parsing, focused/full tests, and independent editorial/technical review pass.

## Explicit exclusions

Application behavior changes beyond reference repair, external repository mutation, PyPI publication, and live operations.

## References

- `.10x/specs/buoy-brand-assets-and-documentation.md`
- `.10x/knowledge/documentation-details-on-demand.md`
- `.10x/tickets/done/2026-07-14-buoy-local-compatibility.md`

## Evidence expectations

Asset/reference inventory, README counts, link/SVG/command validation, active-vs-historical record search, eval fixture result, full suite, and dual editorial/technical review.

## Progress and notes

- 2026-07-14: Core identity and compatibility dependencies closed; assigned to a single worker.
- 2026-07-14: Added the original navy/orange `images/buoy.svg`, replaced the puffin, rewrote the 94-line README and focused docs for Buoy, added the canonical 0.2 migration guide, updated in-repository operational skills, repaired active record paths, and reviewed self-search eval questions/judgments. SVG, five-file links, seven command shapes, 10-case fixture autoresearch (score 100.0, no API calls), lock/diff checks, and the full 226-test suite pass. Evidence: `.10x/evidence/2026-07-14-buoy-brand-docs-assets-and-evals.md`.
- 2026-07-14: Independent editorial and technical reviews passed. Review: `.10x/reviews/2026-07-14-buoy-brand-docs-assets-and-evals-review.md`.

## Blockers

- None.
