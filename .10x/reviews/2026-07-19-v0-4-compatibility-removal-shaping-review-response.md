Status: recorded
Created: 2026-07-19
Updated: 2026-07-19
Target: .10x/tickets/done/2026-07-19-buoy-v0-4-compatibility-removal-plan.md
Verdict: pass

# Buoy 0.4 Compatibility Removal Shaping Review Response

## Target and provenance

This record indexes the review contract supplied in the current workstream for PR #46 and the user's explicit ratification of the reviewer's exact recommendation. It records the shaping response; it does not claim that the future source implementation has been reviewed.

Reviewed response targets:

- `.10x/specs/buoy-v0-4-console-alias-removal.md`
- `.10x/specs/buoy-v0-4-environment-alias-removal.md`
- `.10x/tickets/done/2026-07-19-buoy-v0-4-compatibility-removal-plan.md`
- its two executable children and the separate stale-guidance owner.

## Review findings and response

1. **Environment rejection boundary was underspecified.** The active response now requires inspection after successful parsing and before actual handler dispatch, covers every primary/catalog/autoresearch command, preserves parser/help/version/no-handler behavior, and rejects before reads or side effects.
2. **Diagnostic and stream behavior was underspecified.** The active response defines exact singular/both diagnostics, presence including empty values, old/new matrices, deterministic model-then-precision ordering, value redaction, exit 2, one stderr line, and empty stdout under `--json`.
3. **Console source and upgrade proof were incomplete.** The active response requires deletion of both the `pyproject.toml` script and dedicated `legacy_main` hook, plus clean install and a same-environment normal upgrade from the immutable digest-verified released GitHub 0.3.0 wheel to a candidate 0.4.0 wheel. Entry-point metadata and launcher directories are inspected before and after.
4. **Graph/exclusions needed hardening.** The response creates a non-executable parent, two bounded executable children with parallel-work/aggregate-integration constraints, and a separate open record-only owner for both stale statements found in the Scrapling workflow reference: retrieval no longer requires `--live`, and apply should not instruct setting `TURBOPUFFER_NAMESPACE` because the reviewed plan/CLI governs its namespace. The skill reference remains explicitly excluded from 0.4 implementation.
5. **Retained compatibility and effects needed an exact boundary.** Both active specs preserve every inventoried non-alias compatibility surface and prohibit state/data/remote/publication/tag/release effects.

## Verification of shaping graph

- Both focused specifications are active and contain behavior, edge cases, exact scenarios, acceptance criteria, exclusions, and evidence requirements.
- Both implementation children have `Blockers: None`, reference the smallest governing spec, and contain no unresolved semantic default.
- The parent is explicitly non-executable and states parallelism plus the aggregate 0.4.0 integration gate.
- Both stale skill-reference corrections have the same exact, separate durable owner, with scope, acceptance criteria, exclusions, evidence expectations, and authority references for each; neither correction is a child or acceptance evidence for the 0.4 removal.
- The shaping ticket's criteria map to the completed inventory, ratified specs, executable graph, and this response.

## Verdict

Pass for shaping. The ratified graph is execution-ready; no source, tests, user docs, package/version metadata, or release behavior was changed by this response.

## Residual risk

The active specifications intentionally describe future 0.4.0 behavior while current source remains 0.3.0-compatible. The open parent and two children own that expected implementation gap. Future implementation and aggregate closure still require independent source review and recorded evidence.
