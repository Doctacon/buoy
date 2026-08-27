Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Target: .10x/tickets/done/2026-08-27-decouple-evidence-from-source-layout-plan.md
Verdict: pass

# Evidence/layout final review

## Target

Complete working-tree implementation of semantic routing compatibility, immutable versioned repository evaluations, promotion-only ranking authority, and the concern-oriented package layout.

Independent review run: `534dbdb5-32a0-4fe3-b000-8868f5339ec9`.

## Findings

No issues found.

The reviewer confirmed:

- registered datasets have strict identity/version/repository/case/judgment validation;
- registered corpus manifests have strict repository/full-commit/nonempty canonical document/content identity validation;
- consistently rehashed semantic substitutions are rejected by tests;
- pending v2 is path-membership-only and promotion-ineligible;
- production truthfully has no registered promotion basket;
- hosted CI uses only new subpackage imports;
- promotion requires complete registered 13-repository evidence, equal non-authority inputs, safe options, and fail-closed PR/push comparison;
- routing uses schema-v4 semantic compatibility without active Python-byte receipts; and
- package layout matches the specification without flat shims.

## Validation considered

Durable integration evidence records exact validators and 1,191 tests passing on Python 3.11 and 3.13, focused promotion/workflow mutation coverage, wheel/sdist and isolated-install validation, all moved-module imports, CLI parity, hosted workflow smoke, layout/no-shim audits, `git diff --check`, and no staged files.

## Verdict

Pass. Merge verdict: OK.

## Residual risk and disposition

- GitHub-hosted Actions has not run. No follow-up ticket is required because hosted execution occurs naturally when a PR is opened; exact workflow snippets and both event modes were exercised locally.
- No real promotion basket exists. This is deliberate `baseline_status=pending` behavior, not unfinished implementation; any future promotion must create separately authorized evidence.
- Semantic routing depends on maintainers revising the descriptor for semantic changes. This is an accepted consequence recorded in `.10x/decisions/buoy-validates-routing-semantics-not-python-bytes.md` and enforced by mutation/behavior tests.
