Status: done
Created: 2026-08-15
Updated: 2026-08-15
Decision: .10x/decisions/buoy-defaults-live-retrieval-to-compact-citations.md
Specification: .10x/specs/compact-retrieval-output.md

# Implement Compact Retrieval Output

## Outcome

Make every successful live `buoy retrieve` easier to read by default while
keeping today's detailed diagnostics behind `--explain` and preserving JSON as
the complete machine contract.

## Bounded implementation

- Add `--explain` to `retrieve` and reject its combination with `--json` before
  configuration, credentials, models, or provider work.
- Render default live text as citation-first passages with rank, title, best
  citation, optional section, and a deterministic whitespace-collapsed excerpt
  of at most 320 characters.
- Keep dry-run/plan text detailed. Keep partial warnings,
  `assessment_failed` warnings, no-relevant-evidence, and inconclusive output
  prominent and behaviorally unchanged; hide positive/observational/shadow
  evidence diagnostics only in compact text.
- Suppress third-party model weight-loading progress bars without changing
  model construction or failure behavior.
- Preserve exact JSON structure and prove that output selection does not alter
  retrieval results or calls.
- Update public documentation, active tag/precision contracts, changelog,
  evidence, and independent review.

## Acceptance

- Compact formatting, citation fallbacks, whitespace collapse, truncation,
  pluralization, and diagnostic omissions match the governing specification.
- `--explain` retains current detailed output for explicit single, explicit
  multi, automatic, partial, and supported results.
- Assessment-failed warnings and empty, abstained, and inconclusive messages
  remain unchanged.
- JSON comparison is exact and plan output remains detailed.
- Flag conflicts fail before query/configuration/environment/credential/model
  or provider effects.
- Existing routing, ranking, per-corpus coverage promotion, evidence decisions,
  partial-result semantics, and provider-call accounting do not change.
- Python 3.11 and 3.13 focused/full suites, source/release validators,
  distribution build/install smoke, diff checks, and independent review pass
  before handoff.

## Effect boundary

This ticket authorizes source, test, and documentation changes required for
presentation only. It does not authorize ranking/fusion/tie changes, coverage
removal, routing or threshold tuning, evaluation refresh, answer synthesis,
provider writes, catalog/card changes, content migration, namespace changes,
credential changes, release publication, or branch-protection changes.

No implementation result or validation claim from the stopped
`work/compact-retrieval-pure-relevance` branch is inherited. Reusable
presentation code must be ported onto the current task branch and validated
against the current authoritative retrieval behavior.

## Closure

The bounded implementation is complete. Compact live text, `--explain`, exact
JSON compatibility, detailed plans, failure-state output, and silent model
construction satisfy the acceptance contract without changing routing,
ranking, per-corpus coverage promotion, evidence decisions, or provider calls.

Focused tests passed `131/131` and the full suite passed `690/690` on both
Python 3.11 and Python 3.13. Source validation, distribution build and
validation, clean-wheel installation, CLI and cached-model smokes, compilation,
and diff hygiene passed. No provider call, provider write, catalog mutation,
namespace mutation, release publication, or integration occurred.

Independent review is recorded at
`.10x/reviews/2026-08-15-compact-retrieval-output-review.md` with a final PASS
and no remaining blocker. The task branch is ready for integration review; it
does not approve or restore the rejected pure-global ranking experiment.
