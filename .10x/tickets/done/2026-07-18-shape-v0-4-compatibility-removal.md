Status: done
Created: 2026-07-18
Updated: 2026-07-19
Parent: .10x/tickets/2026-07-18-repository-cleanup-plan.md
Depends-On: .10x/tickets/done/2026-07-18-review-stale-ticket-statuses.md

# Shape Buoy 0.4 Compatibility Removal

## Scope

Inventory and shape—not implement—the explicit 0.4 compatibility removal promised by active 0.3 records. Distinguish scheduled removals from retained compatibility, obtain user ratification for every execution-critical semantic, activate focused specifications, and open a bounded execution graph.

## Acceptance criteria

- Inventory every active deprecation/removal promise across source, parser/help, package metadata, docs, changelog, tests, skills, specs, and decisions.
- Distinguish explicitly scheduled 0.4 removals from retained compatibility with no removal authority.
- Identify user-visible breakage, script/config migration, state/data implications, release boundaries, diagnostics, command coverage, and package upgrade verification.
- Check conflicts with the completed direct-command-defaults plan and give independently stale guidance a separate owner.
- Harden and activate focused ratified specs; create a non-executable parent and bounded executable children with no unresolved semantics.
- Perform no source, test, user-doc, package/version, or release implementation.

## Evidence expectations

Source/record inventory with exact paths, compatibility matrix, conflict analysis, user checkpoint/ratification, active specifications, executable graph, and shaping review response.

## Blockers

None. The user ratified the reviewer's exact recommended contract on 2026-07-19.

## Explicit exclusions

Implementing removals; changing source/tests/user docs/version numbers; publishing a release; deleting state/data; removing `.turbo-search` fallback, old-plan support, command flags, or migration commands.

## References

- `.10x/tickets/2026-07-18-repository-cleanup-plan.md`
- `.10x/research/2026-07-19-v0-4-compatibility-removal-inventory.md`
- `.10x/specs/buoy-v0-4-console-alias-removal.md`
- `.10x/specs/buoy-v0-4-environment-alias-removal.md`
- `.10x/tickets/2026-07-19-buoy-v0-4-compatibility-removal-plan.md`
- `.10x/reviews/2026-07-19-v0-4-compatibility-removal-shaping-review-response.md`
- `.10x/decisions/buoy-product-identity-and-compatibility-v0-3.md`
- `.10x/specs/buoy-local-compatibility.md`
- `.10x/tickets/done/2026-07-18-direct-command-defaults-plan.md`

## Progress and notes

- 2026-07-19: Dependency `.10x/tickets/done/2026-07-18-review-stale-ticket-statuses.md` completed; this shaping ticket became unblocked.
- 2026-07-19: Inspected active removal authority and current implementation across source, parser/help, package metadata, user docs, changelog, tests, operational skill, decisions, specifications, release mechanics, and integrated direct-command behavior. Only `turbo-search`, `TURBO_SEARCH_EMBEDDING_MODEL`, and `TURBO_SEARCH_EMBEDDING_PRECISION` have an explicit 0.4 schedule. Inventory: `.10x/research/2026-07-19-v0-4-compatibility-removal-inventory.md`.
- 2026-07-19: Classified `.turbo-search` state-root fallback, old plans, retrieve flags, source aliases, and `catalog migrate-local` as retained. Found two independently stale statements in the Scrapling workflow reference: retrieval no longer requires `--live`, and apply should not be directed by ambient `TURBOPUFFER_NAMESPACE` instead of its reviewed plan/CLI authority.
- 2026-07-19: User ratified the exact reviewed 0.4.0 contract: pre-dispatch rejection of either old variable, exact stream/diagnostic/order behavior, console script and hook deletion, same-environment released-wheel upgrade proof, retained compatibility, and no state/data/remote effects.
- 2026-07-19: Activated two focused specs; opened a non-executable parent and two bounded executable children; opened a separate record-only owner for both stale Scrapling workflow statements. Shaping response review passed. No source, tests, user docs, package/version metadata, state/data, remote resource, tag, publication, or release changed.

## Closure mapping

- Removal inventory, compatibility matrix, migration/effect analysis, and direct-command conflict check: `.10x/research/2026-07-19-v0-4-compatibility-removal-inventory.md`.
- Ratified console behavior and upgrade validation: `.10x/specs/buoy-v0-4-console-alias-removal.md`.
- Ratified command boundary, diagnostics, coverage, retained config, and no-side-effect behavior: `.10x/specs/buoy-v0-4-environment-alias-removal.md`.
- Non-executable aggregate plan and bounded execution children: `.10x/tickets/2026-07-19-buoy-v0-4-compatibility-removal-plan.md`.
- Stale retrieval-mode and apply-namespace guidance disposition: `.10x/tickets/2026-07-19-reconcile-scrapling-site-workflow-direct-command-guidance.md` owns both corrections.
- Review response and graph-coherence check: `.10x/reviews/2026-07-19-v0-4-compatibility-removal-shaping-review-response.md`.

## Retrospective

The source-level removal schedule was insufficient to choose safe old-variable behavior. Inventorying command dispatch, JSON streams, apply plan authority, and released artifact mechanics exposed the semantic and upgrade boundaries before tests could encode an assumption. The focused specs and separate stale-guidance owner preserve those distinctions for cold-start executors.
