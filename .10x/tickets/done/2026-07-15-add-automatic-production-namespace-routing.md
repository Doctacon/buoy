Status: done
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/done/2026-07-15-production-semantic-routing-plan.md
Depends-On: .10x/tickets/done/2026-07-15-integrate-approved-apply-catalog-registration.md

# Add Automatic Production Namespace Routing

## Outcome

Implement opt-in `retrieve --auto-route`, local dry route preview, and live catalog-routed multi-namespace retrieval under `.10x/specs/automatic-production-namespace-routing.md`.

## Branch and worktree

Execute on `work/add-automatic-production-namespace-routing` in its own worktree after apply/catalog integration is reviewed, closed, and integrated into current `develop`.

## Scope

- Add `--auto-route`, bounded `--route-top-k` default three, exact retrieve catalog-path precedence, and rejection of route-only flags outside auto-route.
- Preserve explicit namespace behavior and implement argument/environment conflict semantics exactly.
- Load/validate catalog and apply enabled/compatibility gates before scoring.
- Implement production lexical, persisted-vector semantic, and equal-weight hybrid namespace routing with existing `RRF_K`.
- Add route-aware dry-run plans that load the local pinned model but read no credentials/contact no remote service.
- Feed selected compatible cards in route order into existing multi-namespace live retrieval and downstream RRF.
- Add routed text/JSON metadata without vectors or new persistence/telemetry.
- Add focused tests for CLI/stderr-JSON separation, fixed 384 compatibility, eligibility, algorithms, dry safety, live fakes, mixed card ranking contracts plus field-level/global overrides, explicit regression, output, all-or-nothing failure, and no-download behavior.
- Update retrieval documentation.
- Record evidence and obtain independent review before closure.

## Acceptance criteria

- Automatic routing activates only with `--auto-route`; explicit retrieval does not load catalog code.
- CLI namespace conflict, environment replacement warning, route-top-k validation, and catalog overrides match the spec.
- Disabled/incompatible high-score canaries are excluded before lexical/semantic scoring.
- Hybrid route uses persisted vectors, exact lexical semantics, pinned local-only query model, imported `RRF_K=60`, deterministic ties, and pre-retrieval top-three default truncation.
- Dry preview performs no credential read, SDK construction, remote call, state/catalog mutation, model download, or vector leakage.
- Live route queries only selected cards in route order, embeds retrieval query once, preserves per-card ranking contracts/CLI overrides, reuses namespace-qualified downstream RRF, and fails without partial results.
- Routed output remains explicit even when one card is selected; existing explicit single/multi contracts remain compatible.
- No remote namespace discovery fallback, remote catalog, ACL, graph, taxonomy, tag filtering, telemetry, or online learning is added.
- Focused tests, full suite, and `git diff --check` pass.
- Independent review has no unresolved significant finding.

## Explicit exclusions

- catalog core or apply registration changes beyond necessary integrated API use;
- automatic default activation;
- routing uncataloged visible namespaces;
- concurrent or partial-success retrieval;
- query/card logging;
- production feedback learning;
- concepts/relationships/graphs.

## Evidence expectations

Evidence must prove argument and fail-closed boundaries, eligibility-before-score, deterministic route metrics/fixtures, route-order handoff, embed-once live behavior, existing RRF identity/ties, dry no-side-effect sentinels, explicit retrieval regression, output redaction, and full validation.

## Blockers

None. Dependency `.10x/tickets/done/2026-07-15-integrate-approved-apply-catalog-registration.md` is reviewed, closed, and integrated at develop commit `ac6a3ca`.

## Progress and notes

- 2026-07-15: Opened as the final sequential child; no implementation occurred.
- 2026-07-15: Marked active after dependency integration at develop commit `ac6a3ca`; implementation started on `work/add-automatic-production-namespace-routing`.
- 2026-07-15: Implemented opt-in automatic routing with bounded CLI/catalog-path semantics, enabled/runtime compatibility gating before exact lexical and persisted-vector semantic scoring, equal `RRF_K=60` hybrid fusion, local-only routed preview, route-ordered existing multi-namespace live handoff, per-card ranking plus field/global overrides, routed output metadata/redaction, and fail-closed stage attribution. Added focused fake/sentinel coverage and retrieval documentation. Focused tests passed (124), full suite passed (362), compilation and `git diff --check` passed. Evidence: `.10x/evidence/2026-07-15-automatic-production-namespace-routing-implementation.md`. Ticket remains active pending independent review.
- 2026-07-15: Applied only the two minor review fixes: restored explicit retrieval's missing-namespace-before-empty-query error precedence while retaining auto-route query validation, and added credential-read sentinels for missing/corrupt catalog and missing route-model live failures. Focused tests passed (125), full suite passed (363), compilation and `git diff --check` passed. Evidence updated; ticket remains active pending review.

- 2026-07-15: Minor compatibility/sentinel findings were corrected in `ab2d89f`; final and holistic reviews passed. Review: `.10x/reviews/2026-07-15-automatic-production-semantic-routing-review.md`.

## Closure mapping

- Activation, eligibility, algorithms, dry/live safety, route handoff, ranking overrides, output, and failures map to focused tests/evidence.
- 125 focused and 363 full-suite tests, compilation, and diff checks passed.
- No excluded remote catalog/ACL/taxonomy/graph/telemetry behavior was added.

## Retrospective

Opt-in routing can preserve legacy behavior only when argument error precedence and credential-read boundaries are tested directly. Those regressions now have focused sentinels. Live quality remains user-judged by explicit design.
