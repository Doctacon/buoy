Status: done
Created: 2026-07-19
Updated: 2026-07-19
Parent: .10x/tickets/done/2026-07-19-buoy-v0-4-compatibility-removal-plan.md
Depends-On: None

# Remove Buoy 0.4 Environment Aliases

## Scope

Implement `.10x/specs/buoy-v0-4-environment-alias-removal.md`:

- replace fallback/warning/conflict selection for exactly `TURBO_SEARCH_EMBEDDING_MODEL` and `TURBO_SEARCH_EMBEDDING_PRECISION` with the ratified presence-rejection gate;
- invoke the gate after successful parsing and before every actual primary CLI or autoresearch handler/experiment dispatch;
- preserve help/version, parser failures, parsed no-handler help, current variables/defaults/overrides, plan-derived apply configuration, and every unrelated compatibility surface;
- update focused config/CLI/autoresearch tests and only environment-migration/changelog/spec references affected by this removal.

## Acceptance criteria

- Each old name rejects on presence, including an empty value and old+new equal/different combinations; no old value becomes effective.
- Actual `crawl`, `plan`, `apply`, `namespaces`, `retrieve`, `evals`, every catalog subcommand, and autoresearch invocation return 2 before sentinel handler dispatch or any read/write/model/credential/remote side effect.
- Model-only, precision-only, and both-present diagnostics match the active specification byte-for-byte; both-present order is model then precision under either environment insertion order; no value is printed.
- Rejection emits no stdout, including with `--json`, and emits exactly one newline-terminated stderr diagnostic.
- `buoy --help`, `buoy --version`, each top-level and catalog-subcommand help path, bare `buoy`, bare `buoy catalog`, `python -m buoy_search --help`, and autoresearch help remain available with old names present. Malformed arguments retain argparse behavior.
- With old names absent, all existing `BUOY_*`, `TURBOPUFFER_*`, defaults, CLI overrides, plan authority, parser/output, direct-command, state/data, catalog, identifier, and remote behavior remain unchanged.
- Focused config/CLI/autoresearch and no-side-effect tests, complete Python 3.11/3.13 suites, distribution checks, migration-reference checks, independent review, and hosted checks pass.

## Validation and evidence expectations

Record exact changed files; table-driven command/help/version coverage; old/new/empty/insertion-order matrix; exit/stdout/stderr bytes; sentinel call traces; checks proving autoresearch rejects before experiment reads and commands reject before local/remote effects; focused/full commands and results; hosted identities; and explicit no-state/no-data/no-remote attestation. Redact all environment values from evidence.

## Dependencies and parallelism

No child execution dependency. Work may proceed in parallel with `.10x/tickets/done/2026-07-19-remove-buoy-v0-4-console-alias.md`, but both reviewed diffs must be assembled into one aggregate 0.4.0 candidate before integration to `develop`.

## Blockers

None.

## Explicit exclusions

Console-script/`legacy_main` changes; version/tag/publication work; changes to current variables/defaults or `TURBOPUFFER_*`; plan schemas; state/data migration; remote operations; any unrelated compatibility removal; stale skill-reference correction.

## References

- `.10x/tickets/done/2026-07-19-buoy-v0-4-compatibility-removal-plan.md`
- `.10x/specs/buoy-v0-4-environment-alias-removal.md`
- `.10x/specs/buoy-v0-4-console-alias-removal.md`
- `.10x/specs/buoy-local-compatibility.md`
- `.10x/specs/embedding-inference-precision.md`

## Progress and notes

- 2026-07-19: Opened from the ratified active environment-removal specification. No implementation performed.
- 2026-07-19: Implemented the exact pre-dispatch presence gate in the primary and autoresearch entry points, removed config fallback/warning/conflict selection, added exhaustive command/help/version/matrix/no-dispatch coverage, and updated focused migration/changelog/active-spec references. Local Python 3.11 and 3.13 suites each pass 422 tests; focused tests and temporary wheel/sdist construction/inspection pass. Evidence: `.10x/evidence/2026-07-19-remove-buoy-v0-4-environment-aliases.md`.
- 2026-07-19: Candidate version metadata remains intentionally unchanged because the parent plan assigns it to the console-alias sibling; aggregate reconciliation must produce coherent 0.4.0 metadata. Opened PR #48 from implementation commit `96ff96e563a0e5b57207446534040fe881e5e2cb`; hosted Python 3.11, Python 3.13, and distribution-build jobs passed in workflow `29708193056`.
- 2026-07-19: Independent bounded review passed implementation head `6d9e050176c46722a89c5daa00bbc872efb0fc2a` and observed exact-head hosted checks. Integration remains blocked until aggregate 0.4 reconciliation passes. Review: `.10x/reviews/2026-07-19-buoy-v0-4-environment-alias-removal-review.md`. Ticket remains active.
- 2026-07-19: Full reviewed tip `a049bbf` is preserved as an ancestor of aggregate candidate `68477fdca5a5b5f7b890d059c484739f02fc1dd8`. Aggregate exhaustive gate, distribution, clean/upgrade launcher, diff/reference, and Python 3.11/3.13 validation passed with coherent sibling-owned 0.4.0 metadata and console removal present. Evidence: `.10x/evidence/2026-07-19-buoy-v0-4-compatibility-removal-candidate.md`. Independent aggregate review remains pending; ticket stays active.
- 2026-07-19: Post-assembly packaging repair preserved runtime/package code and reran all 75 focused configuration/environment/CLI/autoresearch/release tests plus full Python 3.11/3.13 suites. Exact presence/value/order/stream/exit and sentinel pre-dispatch/pre-read/pre-write assertions passed; a normally installed valid command also returned 2 with zero stdout, exact redacted stderr, and an untouched temporary HOME. Evidence: `.10x/evidence/2026-07-19-exclude-internal-records-from-buoy-v0-4-artifacts.md`.
- 2026-07-19: Final aggregate closure review and exact-head hosted checks passed; all acceptance criteria map to child and aggregate evidence. Review: `.10x/reviews/2026-07-19-buoy-v0-4-compatibility-removal-closure-review.md`.
