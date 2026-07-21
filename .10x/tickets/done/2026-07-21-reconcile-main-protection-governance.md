Status: done
Created: 2026-07-21
Updated: 2026-07-21
Parent: .10x/tickets/2026-07-21-buoy-v0-4-0-release-plan.md
Depends-On: None

# Reconcile Main Protection Governance

## Outcome

Record the user's exact decision to retain current hosted `main` protection during v0.4.0 release execution: force pushes remain allowed and last-push approval remains required. Preserve every other protection/release boundary, change no hosted protection, and keep force push/direct push behavior prohibited operationally.

## Scope completed

- Superseded the original governance decision with `.10x/decisions/protected-development-and-github-release-governance-v2.md` while preserving the original under `.10x/decisions/superseded/`.
- Updated `.10x/specs/protected-github-branches.md` with exact branch-specific protection behavior.
- Repaired references to the moved superseded decision and updated active release records to the v2 authority.
- Recorded completed PR #83 ancestry integration, closed/stale PR #80 history, and the remaining mechanically required replacement release-PR gates.

## Acceptance criteria

- V2 records exactly the two user-selected main exceptions and retains strict CI, freshness, PR requirement, admin enforcement, deletion denial, merge-commit release flow, and GitHub-only publication.
- Develop remains governed by force-push denial and no last-push approval.
- No record authorizes direct/force push, protection bypass, service-configuration mutation, tag, Release, PyPI, or Turbopuffer operations.
- References to the superseded decision resolve.

## Evidence

- User selected `Keep current rules` after the exact settings and release-blocking consequence were presented, then explicitly directed `execute` after the remaining release sequence was explained.
- Hosted inspection reported main `allow_force_pushes=true`, `require_last_push_approval=true`, strict three-check freshness, zero required approvals, administrator enforcement, and deletion denial; develop remained compliant with the original stricter settings.

## Blockers

None for this record-only reconciliation. PR #80 is closed/stale and will not merge. GitHub may require an eligible last-push approval before the required replacement release PR can merge; this ticket does not bypass it.

## Explicit exclusions

Hosted protection mutation; approval fabrication; force/direct push; source/runtime changes; tag/Release/PyPI/Turbopuffer operations.

## Progress and notes

- 2026-07-21: Initial independent review confirmed the exact user-selected branch settings and no hosted mutation, then blocked integration on superseded status, one historical evidence-path rewrite, stale PR #80 state, missing parent graph membership, and consumed bootstrap-authority wording. Repaired all five record-only defects: the old decision is superseded, historical output is verbatim, PR #80 is accurately closed/stale with a replacement PR required, this child is in the parent sequence, and bootstrap/configuration authority is explicitly consumed. No hosted protection, source, branch, tag, Release, or product state changed.

## Retrospective

When the user elects to retain observed service configuration rather than restore a prior contract, the durable record must distinguish configuration acceptance from permission to use its riskiest capability. Historical command output must remain verbatim when its referenced file later moves.
