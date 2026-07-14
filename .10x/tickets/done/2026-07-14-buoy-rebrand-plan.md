Status: done
Created: 2026-07-14
Updated: 2026-07-14
Parent: None
Depends-On: None

# Buoy 0.2 Rebrand Plan

## Aggregate outcome

Deliver the ratified Buoy code-level identity, compatibility transition, visual/documentation rebrand, release validation, and exact GitHub repository rename without changing remote Turbopuffer data.

This is a parent plan and is not executable.

## Governing records

- `.10x/decisions/buoy-product-identity-and-compatibility.md`
- `.10x/specs/buoy-package-and-cli-identity.md`
- `.10x/specs/buoy-local-compatibility.md`
- `.10x/specs/buoy-brand-assets-and-documentation.md`
- `.10x/specs/buoy-release-validation.md`
- `.10x/knowledge/documentation-details-on-demand.md`

## Child sequence

1. `.10x/tickets/done/2026-07-14-buoy-core-package-rename.md` — rename distribution/module/CLI and establish Apache-2.0 identity.
2. `.10x/tickets/done/2026-07-14-buoy-local-compatibility.md` — implement state-root and environment transition after the new module exists.
3. `.10x/tickets/done/2026-07-14-buoy-brand-docs-assets-and-evals.md` — apply visual/docs/skills/eval identity after code and compatibility contracts settle.
4. `.10x/tickets/done/2026-07-14-buoy-release-integration-validation.md` — build/install/migration/eval integration gate.
5. `.10x/tickets/done/2026-07-14-buoy-github-repository-rename.md` — rename the external GitHub repository only after integration passes.

Children 2 and 3 both depend on child 1 and may be shaped for parallel execution, but must use isolated worktrees or run sequentially because both can affect repository-wide references. Child 4 depends on both. Child 5 depends on child 4.

## Aggregate acceptance criteria

- Product, distribution, module, command, license, logo, docs, skills, and active records agree with the ratified identity.
- Version 0.2 compatibility works exactly as specified without state copying or remote mutation.
- Existing plans, row IDs, namespace names, and local ledgers remain safe.
- Clean built artifacts install and execute under the new identity; deprecated aliases are bounded and tested.
- GitHub ends at `Doctacon/buoy-search` with the local remote updated, or the external child records a concrete availability/auth blocker without weakening code-level closure.
- The pending float16 ticket is rebased and unblocked only after integration.

## Explicit exclusions

PyPI publication, domain purchase, social-handle changes, remote namespace renames/deletes/reindexing, and float16 implementation.

## Progress and notes

- 2026-07-14: User ratified Apache-2.0, legacy in-place state fallback, minimal navy/orange SVG, and one-release CLI/environment compatibility for the recommended full Buoy identity.
- 2026-07-14: Plan execution authorized; child 1 assigned.
- 2026-07-14: All five child tickets closed with pass reviews. Code-level 0.2 integration and exact GitHub rename completed; float16 ticket rebased and unblocked.
- 2026-07-14: Aggregate independent closure review passed. Review: `.10x/reviews/2026-07-14-buoy-rebrand-parent-closure-review.md`.

## Blockers

- None.
