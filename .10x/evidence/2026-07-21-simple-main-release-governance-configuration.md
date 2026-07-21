Status: recorded
Created: 2026-07-21
Updated: 2026-07-21
Relates-To: .10x/tickets/done/2026-07-21-configure-simple-main-release-governance.md, .10x/tickets/done/2026-07-21-simple-main-release-automation-plan.md

# Simple Main Release Governance Configuration

## Preconditions

- Repository automation integrated to develop at `7fa4bd726d09a671b76d408e7383e9fbc58c41de` through PR #89 after independent PASS.
- Develop push CI run `29864439022` passed.
- Integrated workflows contain zero `environment:` references.
- v0.4.0 Release `357504706` and release run `29851435791` remained successful/intact.
- Release deployment `5542522847` had latest status `success`, which GitHub treats as active; no pending deployment existed.

## Authorized hosted mutations

1. Posted `inactive` only to completed deployment `5542522847` after revalidating its exact release/run identities.
2. Verified the latest deployment state was inactive, then deleted only GitHub environment `release`; subsequent API readback returned not found.
3. Replaced `main` required status checks with exactly these GitHub-Actions app-bound contexts and `strict=false`:
   - `Release readiness / Policy`
   - `Release readiness / Python 3.11`
   - `Release readiness / Python 3.13`
   - `Release readiness / Distribution`
4. Set main fixed approvals to zero and `require_last_push_approval=false`; retained administrator enforcement, PR requirement, deletion denial, and `allow_force_pushes=true`.
5. Closed obsolete PR #87 unmerged with an explanatory comment and did not delete its branch.

The first review-policy PATCH included `dismissal_restrictions`, which GitHub rejects for personal repositories with HTTP 422. That request made no review-policy change. A second PATCH omitted the unsupported organization-only field and succeeded with the exact authorized values.

## Verification

Final main readback:

- strict freshness: false;
- exact four required contexts above, app ID 15368;
- last-push approval: false;
- required approving review count: 0;
- administrator enforcement: true;
- force-push allowance: true;
- deletion allowance: false.

Canonical before/after readback proved develop protection unchanged: strict existing Python 3.11/Python 3.13/Build distributions, last-push false, zero fixed approvals, admin enforcement, force-push denial, deletion denial, and non-linear history.

Environment `release` is absent; deployment latest state is inactive; PR #87 is closed and unmerged.

## Limits

No workflow/source/version/main/tag/Release/asset/provenance/PyPI/Turbopuffer/user-state mutation occurred. Existing v0.4 tag, Release, assets, and successful run remain unchanged. No release was triggered.
