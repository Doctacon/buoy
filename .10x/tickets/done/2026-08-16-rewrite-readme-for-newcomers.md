Status: done
Created: 2026-08-16
Updated: 2026-08-16
Knowledge: .10x/knowledge/documentation-details-on-demand.md
Specification: .10x/specs/buoy-public-project-surface.md
Evidence: .10x/evidence/2026-08-16-readme-newcomer-rewrite.md
Review: .10x/reviews/2026-08-16-readme-newcomer-rewrite-review.md

# Rewrite README for Newcomers

## Outcome

Replace the implementation- and release-history-heavy README with a short,
plain-language introduction that lets someone new to Buoy understand what it
does, why they might use it, and the source-to-search workflow.

## Scope

- Rewrite `README.md` as the project landing page.
- Preserve the logo, truthful CI/license badges, a copyable released-version
  workflow, supported source categories, and links to the detailed guides.
- Keep detailed routing, catalog, evaluation, migration, model, threshold, and
  operational material in its existing canonical documentation and history.

## Acceptance

- The README explains the user value before introducing product terminology.
- A first-time visitor can identify the plan, review/apply, and retrieve loop
  without knowing Buoy, Turbopuffer, corpus, delta, or namespace vocabulary.
- The representative commands work with released v0.5.1 behavior and make the
  local-review versus live-write boundary clear.
- Websites, public GitHub repositories, local documents, and prepared database
  relations are discoverable without an exhaustive compatibility list.
- The README is approximately 100 lines or fewer and links to the focused
  indexing, retrieval, evaluation, migration, contribution, and release docs.
- Local links, displayed command shapes, full tests, diff hygiene, and an
  independent editorial/technical review pass.

## Exclusions

Application behavior, CLI flags, dependencies, lockfiles, package metadata,
focused reference-document rewrites, provider operations, publication,
deployment, and integration are excluded.

## External effects

Validation must not crawl a source, read credentials, load models, call a
provider, mutate an index/catalog, or publish a release.

## Progress

- 2026-08-16: User requested a reality-based README focused only on what Buoy
  can do for a newcomer and the highest-level explanation of how it works.
- 2026-08-16: Replaced the 258-line / 1,479-word implementation-heavy README
  with a 94-line / 456-word newcomer landing page and a released-v0.5.1
  explicit-namespace walkthrough. Local links, parser/help checks, the lock,
  full 805-test suite, ranking contract, syntax forecast, and diff hygiene pass.
- 2026-08-16: Repaired the independent review's prerequisite and dry-run-scope
  findings plus its plain-language suggestions. Final editorial/technical
  re-review passed with no blocker or significant finding. No live source,
  provider, credential, model-weight, publication, or deployment operation ran.
