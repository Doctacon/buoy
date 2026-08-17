Status: recorded
Created: 2026-08-16
Updated: 2026-08-16
Target: .10x/tickets/done/2026-08-16-rewrite-readme-for-newcomers.md
Verdict: pass

# README Newcomer Rewrite Review

## Review scope

Independent editorial and technical review of the exact README rewrite against
the executable ticket, the active details-on-demand knowledge record, the
public-project-surface specification, the released v0.5.1 workflow, and the
current CLI/source documentation.

## Findings and repair

The first review found no blocker and two significant issues:

1. The prerequisites named Python and Turbopuffer but omitted `uv` and Git,
   which the displayed GitHub-repository workflow uses.
2. “Planning and dry runs do not connect to Turbopuffer” was too broad because
   automatic retrieval previews read remote routing state.

The rewrite now names all example prerequisites and scopes the provider-free
claim exactly to `plan` and `apply --dry-run` in the walkthrough. It also
replaces “provenance” and other insider phrasing with plain source/citation
language, describes the preflight as a verified change summary rather than the
individual exact changes, and labels the retrieval reference as current-source
documentation rather than released-v0.5.1 behavior.

Final re-review found no remaining blocker or significant issue.

## Acceptance mapping

- User value appears before product terminology: pass.
- Plan -> review/apply -> search is understandable without prior Buoy context:
  pass.
- Displayed workflow matches released v0.5.1 explicit-namespace behavior: pass.
- Source access and Turbopuffer read/write boundaries are accurate: pass.
- All four supported source categories are visible in plain language: pass.
- README remains under the approximately-100-line policy at 94 lines: pass.
- Logo, CI/license badges, focused links, and repository scope are preserved:
  pass.
- Independent diff inspection and `git diff --check`: pass.

## Residual risk

External URLs and the live workflow were deliberately not executed. The local
retrieval guide follows the current source tree and is labeled accordingly;
the quick start remains pinned to the published v0.5.1 wheel.
