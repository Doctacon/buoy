Status: recorded
Created: 2026-08-16
Updated: 2026-08-16
Ticket: .10x/tickets/done/2026-08-16-rewrite-readme-for-newcomers.md

# README Newcomer Rewrite Evidence

## Outcome

The 258-line / 1,479-word README was replaced with a 94-line / 456-word
landing page. It now leads with the user problem and supported inputs, explains
the plan -> review/apply -> search loop in three steps, and states that Buoy
returns cited passages rather than generated answers.

The published-v0.5.1 walkthrough keeps one explicit namespace and separates
the source-fetching plan, provider-free apply preview, approved Turbopuffer
write, and live retrieval. The README retains only the supported-source summary
and links to focused detail. Routing calibration, catalog migration, thresholds,
model revisions and resource measurements, internal certification history,
failure contracts, and state mechanics were removed from the landing page.

## Validation

- `wc -l -w README.md`: `94 456 README.md`.
- Local Markdown/image audit: all eight README targets resolve (`images/buoy.svg`,
  `LICENSE`, `CONTRIBUTING.md`, and five focused documents).
- Parser-only audit: all four displayed Buoy workflow command shapes parse
  through `buoy_search.cli.build_parser()` without dispatch.
- Safe CLI audit: `buoy --version`, top-level help, and `plan`, `apply`, and
  `retrieve` help all exit 0.
- `uv lock --check`: pass; 154 packages resolve under the existing lock.
- Final full Python 3.13 suite: 805 tests pass in 52.437 seconds.
- `scripts/validate_ranking_contract.py`: pass for 13 datasets, 369 judgments,
  and 90 composite identities.
- `scripts/c6_syntax_forecast.py validate`: pass at forecast digest
  `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
- `git diff --check`: pass.

The initial sandboxed full-suite run had exactly five loopback-bind denials and
two uv-cache permission denials. The required rerun with loopback and the
existing local uv cache available passed all 805 tests; those denials were
environment restrictions, not product failures.

## Independent review

The first independent editorial/technical review found no blocker and two
significant wording issues: the example omitted its `uv` and Git prerequisites,
and a dry-run safety sentence could be misread as including automatic retrieval
previews. It also suggested plainer source/citation language and a more precise
description of the apply preview. All were repaired. The relative retrieval
link now explicitly identifies its target as current-source documentation so
it does not imply that unreleased behavior exists in the installed v0.5.1
wheel. Final re-review passed with no remaining blocker or significant finding.

Review: `.10x/reviews/2026-08-16-readme-newcomer-rewrite-review.md`.

## External effects and limits

No plan, crawl, apply, retrieve, catalog, or provider command was executed; no
credential was read and no model weights were loaded. No Turbopuffer namespace
or catalog, database relation, source, release, package publication, deployment,
or external repository state was read or mutated by product behavior. External
badge and release URLs were not network-checked; the displayed live workflow
was parser-validated only and was deliberately not executed.
