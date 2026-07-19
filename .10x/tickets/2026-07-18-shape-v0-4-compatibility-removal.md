Status: blocked
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-repository-cleanup-plan.md
Depends-On: .10x/tickets/2026-07-18-review-stale-ticket-statuses.md

# Shape Buoy 0.4 Compatibility Removal

## Scope

Inventory and shape—not implement—the explicit 0.4 compatibility removal promised by active 0.3 records. Candidate surfaces include:

- `turbo-search` console alias;
- `TURBO_SEARCH_EMBEDDING_MODEL` and `TURBO_SEARCH_EMBEDDING_PRECISION`;
- any other behavior explicitly scheduled for 0.4 removal by active records.

Separately classify compatibility with no ratified removal release, including `.turbo-search` state-root fallback, old-plan compatibility, `--auto-route`, `--live`, `--plan`, positional/flag source aliases, and `catalog migrate-local`. Do not silently include them in 0.4.

After code/record inspection, present a user-legible removal contract, migration consequences, release/version boundary, and exact confirm-or-correct questions. Only ratified behavior may become active specs and executable tickets.

## Acceptance criteria

- Inventory every active deprecation/removal promise across source, parser/help, package metadata, docs, changelog, tests, skills, specs, and decisions.
- Distinguish explicitly scheduled 0.4 removals from retained compatibility with no removal authority.
- Identify user-visible breakage, script/config migration, state/data implications, and release-note requirements for each candidate.
- Check conflicts with the completed direct-command-defaults plan.
- Produce focused draft specs/questions; do not create executable tickets with unratified semantics.

## Evidence expectations

Source/record inventory with exact paths, compatibility matrix, conflict analysis, and user checkpoint.

## Blockers

Direct-command implementation and stale-record review must complete first so this work shapes against current authority.

## Explicit exclusions

Implementing removals; changing version numbers; publishing a release; deleting state/data; removing `.turbo-search` fallback, old-plan support, command flags, or migration commands without separate ratification.

## References

- `.10x/tickets/2026-07-18-repository-cleanup-plan.md`
- `.10x/research/2026-07-18-repository-dead-end-inventory.md`
- `.10x/decisions/buoy-product-identity-and-compatibility-v0-3.md`
- `.10x/specs/buoy-local-compatibility.md`
- `.10x/tickets/2026-07-18-direct-command-defaults-plan.md`

## Progress and notes
