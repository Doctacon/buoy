Status: cancelled
Created: 2026-07-16
Updated: 2026-07-18
Parent: None
Depends-On: .10x/tickets/done/2026-07-15-production-semantic-routing-plan.md

# Make Automatic Routing the Retrieval Default

## Scope

Implement `.10x/specs/superseded/default-production-namespace-routing.md`:

- route automatically whenever retrieve has no CLI `--namespace`;
- preserve explicit repeatable CLI namespaces as the sole manual override;
- stop reading or warning about `TURBOPUFFER_NAMESPACE` in retrieve;
- retain `--auto-route` as a compatibility affirmation;
- allow `--route-top-k` and retrieve `--catalog` in default automatic mode;
- reject automatic-only options when explicit CLI namespaces are supplied;
- update CLI help, retrieval documentation, changelog Unreleased notes, and precise regression tests.

## Acceptance criteria

- `buoy retrieve QUERY` performs the same local route and output previously produced by `--auto-route`.
- `--live` without a CLI namespace routes first and reads credentials only after a valid non-empty route.
- Explicit CLI namespace retrieval remains catalog/model independent and output-compatible.
- `TURBOPUFFER_NAMESPACE` has no effect and produces no retrieve warning; tests use sentinels to prove it is not read where practical.
- Existing `--auto-route` commands remain valid and behaviorally equivalent to the new default.
- Automatic-only controls work without the flag and fail with explicit namespaces.
- Live/dry-plan conflict remains the first retrieval error; contradictory explicit/automatic options precede namespace-list validation; explicit malformed/duplicate namespace errors precede empty query; automatic whitespace-only query fails before catalog/config/model/credential work.
- Missing/corrupt/incompatible/empty catalog and missing route model continue to fail closed before credentials or remote calls.
- Focused and full tests, Python 3.11/3.13 CI, build, docs, and independent review pass.

## Explicit exclusions

Removing `--namespace`; removing `--auto-route`; adding `--no-auto-route`; changing routing algorithms/fan-out/model/catalog formats; remote discovery; ACL/taxonomy/graph/telemetry; Turbopuffer writes or live validation.

## References

- `.10x/decisions/superseded/production-routing-default-local-catalog.md`
- `.10x/specs/superseded/default-production-namespace-routing.md`
- `.10x/specs/explicit-multi-namespace-retrieval.md`
- `.10x/specs/superseded/production-local-namespace-catalog.md`

## Evidence expectations

Argument/precedence matrix including live/dry, contradictory modes, duplicate/empty namespaces, and whitespace-only queries; credential/environment sentinels; default dry/live routing fakes; explicit compatibility; fail-closed cases; help/docs; focused/full/hosted checks; and independent review.

## Blockers

None. The user ratified default automatic routing, no retrieval namespace environment behavior, and retained explicit CLI namespace override on 2026-07-16.

## Progress and notes


## Cancellation

Cancelled on 2026-07-18 before implementation. The user superseded the working-directory local-catalog architecture with live Turbopuffer namespace discovery plus a dedicated remote card namespace. No runtime code or tests were produced under this ticket. Replacement owner: `.10x/tickets/done/2026-07-18-remote-semantic-routing-plan.md`.
