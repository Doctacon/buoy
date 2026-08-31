Status: active
Created: 2026-08-30
Updated: 2026-08-30
Parent: None
Depends-On: None

# Minimize README to the basic Buoy workflow

## Scope

Rewrite `README.md` as a minimal newcomer landing page governed by
`.10x/knowledge/documentation-details-on-demand.md` and
`.10x/specs/buoy-public-project-surface.md`.

Preserve the logo, truthful CI/license badges, a one-sentence description, the
published-wheel installation command, the Turbopuffer API-key requirement, the
single basic workflow, and focused links for later detail.

The basic workflow MUST be presented without namespaces, dry runs, approval
flags, or optional operational branches:

```bash
buoy plan <source>
buoy apply
buoy retrieve "<question>"
```

Mention `TURBOPUFFER_API_KEY` immediately before the workflow in a copyable
form.

## Acceptance criteria

- A newcomer sees the install command and the three-command workflow without
  encountering optional workflow branches first.
- The workflow is exactly `plan <source>`, `apply`, then `retrieve
  "<question>"` at the conceptual command level.
- The README clearly states that a Turbopuffer API key is required and shows
  `export TURBOPUFFER_API_KEY=...`.
- The README does not explain dry runs, namespaces, approval flags, local
  storage, telemetry, migrations, source matrices, or implementation details.
- Detailed indexing, retrieval, evaluation, migration, contribution, and
  release material remains discoverable through links.
- Logo, CI badge, license badge, and Apache-2.0 license statement remain.
- Markdown links resolve, displayed commands parse where safely checkable, and
  `git diff --check` passes.

## Exclusions

CLI behavior, source code, package metadata, dependencies, reference-document
rewrites, releases, provider calls, live indexing, and live retrieval are
excluded.

## Evidence expectations

Record the final line/word counts, local-link validation, safe parser/help
checks, `git diff --check`, and an independent editorial/technical review. No
source crawl, provider call, index mutation, model load, or publication may be
used for validation.

## Blockers

None. The user explicitly ratified the three-command workflow and requested
that the Turbopuffer API-key requirement remain visible.

## Progress and notes

- 2026-08-30: Inspected the current README, active documentation policy,
  public-project-surface specification, and prior newcomer rewrite records.
- 2026-08-30: User rejected namespaces, dry runs, and approval flags in the
  primary workflow; ratified `buoy plan <source>`, `buoy apply`, then
  `buoy retrieve "<question>"`, with the Turbopuffer API key mentioned.
- 2026-08-30: Rewrote `README.md` from 130 lines / 703 words to 41 lines /
  129 words. Preserved the logo, truthful badges, published v0.6.1 wheel,
  concise product description, API-key export, exact three-command workflow,
  focused documentation links, and Apache-2.0 statement. Removed optional and
  operational detail from the landing page.
- 2026-08-30: Non-live validation confirmed all seven local links resolve,
  excluded detail is absent, each displayed subcommand has a valid current CLI
  help surface, and `git diff --check` passes. No crawl, retrieval, provider
  call, model load, publication, or index mutation ran. Independent review
  remains for the parent workflow.
