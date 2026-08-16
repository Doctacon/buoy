Status: pass
Created: 2026-08-15
Updated: 2026-08-15
Ticket: .10x/tickets/2026-08-15-activate-bounded-prototype-routing.md
Specification: .10x/specs/bounded-prototype-routing-activation.md
Decision: .10x/decisions/buoy-activates-certified-bounded-prototype-routing.md

# Bounded Prototype Routing Phase-Fixture Review

## Scope

This independent review examined only the test-only phase-fixture repair made
after clean dormant commit `a8190f3`. Relative to that commit, the complete
pre-review delta was exactly these three files:

```text
tests/routing_confidence_fixtures.py
tests/test_release_automation.py
tests/test_routing_quality_runner.py
```

The delta contained 24 insertions and 5 deletions and passed
`git diff --check`. No production source, evaluator, packaged canary,
workflow, documentation, or existing governance record differed from
`a8190f3`. This review record is the sole additional path created by the
reviewer.

## Findings

- `collect_routing_confidence_bytes()` reconstructs the exact governed
  schema-v1 collect authority as 994 bytes. Its SHA-256 is
  `23fb14c49263933a2adb2299a9c04089888fb2ec734b790d9eadda2df295cbed`.
- The tracked packaged artifact
  `src/buoy_search/data/automatic_routing_confidence_calibration.json`
  remained byte-identical to `a8190f3` and had the same exact SHA-256,
  `23fb14c49263933a2adb2299a9c04089888fb2ec734b790d9eadda2df295cbed`.
- The two evaluator-runner cases whose assertions explicitly concern
  collect-only authority now inject that test-only collect authority. Their
  meaning no longer depends on whether the final package default is collect
  or active.
- The collect archive test now obtains the exact governed collect bytes from
  the phase-independent helper. It still requires the hard raw-byte SHA and
  still rejects a one-byte mutation.
- Active source, wheel/source-distribution module receipts, evaluator-runner
  receipts, source validation, and installed-loader checks were not weakened.
  The missing-credential ordering test also remains unpatched and retains its
  production failure-boundary coverage.

## Validation

With the tracked package still at its exact collect artifact, all 26 focused
tests in `tests.test_routing_quality_runner` and
`tests.test_release_automation` passed.

The reviewer then copied the candidate to a temporary directory, replaced
only that copy's packaged default with a structurally valid schema-v2 active
artifact bound to the copied scorer, routing, CLI, evidence, and evaluator
runner bytes, and reran the same focused boundary. All 26 tests passed. The
production default loader in that temporary copy additionally returned
`mode=active`, `owner_approved=true`, and non-null activation receipts. The
temporary copy was removed after validation; the task worktree's packaged
artifact was never changed.

No provider credential was acquired. The review and its tests made no
Turbopuffer or other provider call, no catalog or content read, no provider
write, no model download, and no external mutation. The reviewer did not
commit, push, merge, deploy, tag, release, or publish.

## Verdict and mandatory next gate

GO for the exact three-file phase-fixture repair above. No P1 or P2 finding
remains, and the repair eliminates packaged-default collect assumptions
without weakening production or packaging enforcement.

This GO does not authorize flipping the packaged artifact. The prior dormant
commit and any collection made from it do not cover this repaired task tree.
Before any schema-v2 artifact flip, the repaired dormant tree including this
review must be committed as a new clean dormant commit, the complete required
dormant validation must pass from that commit, and the governed read-only
65-case route collection must be rerun from that exact clean commit and
independently audited. Any attempt to reuse the earlier dormant collection or
to flip the artifact before that recommit, recollection, and audit is a STOP.
