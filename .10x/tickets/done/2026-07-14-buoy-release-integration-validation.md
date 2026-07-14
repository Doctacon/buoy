Status: done
Created: 2026-07-14
Updated: 2026-07-14
Parent: .10x/tickets/done/2026-07-14-buoy-rebrand-plan.md
Depends-On: .10x/tickets/done/2026-07-14-buoy-local-compatibility.md, .10x/tickets/done/2026-07-14-buoy-brand-docs-assets-and-evals.md

# Validate the Buoy 0.2 Release Integration

## Scope

Execute `.10x/specs/buoy-release-validation.md` against the integrated rebrand. This ticket validates and repairs only rebrand integration defects; it does not add features.

## Acceptance criteria

- Built wheel/sdist metadata and contents match `buoy-search` 0.2.0 and Apache-2.0.
- Isolated installation proves new CLI/module behavior and bounded legacy CLI behavior.
- Temporary-directory compatibility scenarios prove new/default and legacy state safety plus old-plan preflight.
- Fixture autoresearch and self-search eval validation pass after path changes.
- Full suite, docs links, SVG, active-reference search, diff hygiene, and independent adversarial review pass.
- Every criterion maps to durable evidence; child tickets and parent plan are coherent.

## Explicit exclusions

GitHub mutation, PyPI publication, live Turbopuffer work, float16 inference, and unrelated cleanup.

## References

- `.10x/specs/buoy-release-validation.md`
- `.10x/tickets/done/2026-07-14-buoy-local-compatibility.md`
- `.10x/tickets/done/2026-07-14-buoy-brand-docs-assets-and-evals.md`

## Evidence expectations

Raw build/install inventories, temporary compatibility observations, command outputs, eval/test results, link/reference checks, and independent review.

## Progress and notes

- 2026-07-14: All code-level dependencies closed; assigned to integration validator/repair worker.
- 2026-07-14: Built and inspected 0.2.0 wheel/sdist, installed the wheel in isolation, validated primary/module/legacy CLI behavior, exercised all temporary state/environment compatibility paths with no-copy snapshots, ran fixture/self-search eval validation, checked SVG/docs/active identity, and passed 120 focused plus 226 full tests. Repaired two stale old-brand test constant names in `tests/test_evals.py`. Evidence: `.10x/evidence/2026-07-14-buoy-release-integration-validation.md`; raw inventory: `.10x/evidence/.storage/2026-07-14-buoy-release-integration-validation.json`.

- 2026-07-14: Independent adversarial review passed; parent revalidated the complete 226-test suite, lock/diff checks, and primary/module version identity. Review: `.10x/reviews/2026-07-14-buoy-release-integration-validation-review.md`.

## Blockers

- None.
