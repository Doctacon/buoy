Status: recorded
Created: 2026-07-19
Updated: 2026-07-19
Target: .10x/tickets/done/2026-07-19-buoy-v0-4-compatibility-removal-plan.md
Verdict: concerns

# Buoy 0.4 Aggregate Packaging Blocker Review

## Target

Aggregate candidate evidence at `.10x/evidence/2026-07-19-buoy-v0-4-compatibility-removal-candidate.md` and PR #49 through record head `d05bcef00338c56de8edcee561428817edcfd358`.

This is a focused blocker finding, not the final independent aggregate review.

## Finding

**Significant / blocking:** direct inspection of the recorded aggregate candidate artifacts found zero `.10x` entries in the 45-entry wheel but 441 `.10x` entries in the 536-entry sdist. Internal project records therefore ship in the source distribution, and adding record-only evidence changes the candidate sdist rather than leaving an otherwise identical deterministic artifact stable.

The user ratified a narrow repair: preserve `.10x/**` in the repository, exclude exactly `.10x/**` from both wheel and sdist artifacts, prove record-only evidence cannot change corresponding deterministic artifacts under controlled build conditions, and rerun aggregate clean-install and released-0.3.0 upgrade validation. The governing contract is `.10x/specs/buoy-v0-4-internal-record-artifact-exclusion.md`; execution is owned by `.10x/tickets/done/2026-07-19-exclude-internal-records-from-buoy-v0-4-artifacts.md`.

No broader packaging exclusion, runtime/package change, bundled-data change, user-documentation change, publication, tag, or release is authorized by this finding.

## Verdict

Concerns raised. The aggregate candidate, parent plan, and aggregate acceptance review are blocked pending implementation evidence, independent bounded review, and exact-head hosted checks for the new child. The existing console and environment children remain active; this focused finding does not invalidate their passed bounded reviews.

## Residual risk

The exclusion has not been implemented or validated. Current wheel absence is incidental to its existing package target and does not prove an explicit both-artifact boundary. Exact archive stability across a controlled `.10x/**`-only delta, refreshed clean-install/upgrade behavior, and final aggregate review remain pending.

## Subsequent disposition

The finding and residual-risk statement above describe only the pre-repair target through `d05bcef00338c56de8edcee561428817edcfd358`. They are not claims about the current candidate. Exact reviewed head `9e7ec237d31d9fb4ef79209df1d45fcc2b0dd6cf` implements and validates the exclusion; `.10x/evidence/2026-07-19-exclude-internal-records-from-buoy-v0-4-artifacts.md` records zero `.10x` members in both artifacts, controlled record-only byte stability, refreshed install/upgrade validation, and passing exact-head hosted checks. Current disposition and residual risks are recorded in `.10x/reviews/2026-07-19-buoy-v0-4-compatibility-removal-final-aggregate-review.md`.
