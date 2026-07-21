Status: blocked
Created: 2026-07-21
Updated: 2026-07-21
Parent: .10x/tickets/2026-07-21-release-buoy-v0-4-1-through-main-automation.md
Depends-On: None

# Bridge v0.4 Squash Topology Once

## Outcome

Perform the exact user-ratified, protected, content-neutral, non-repeatable bridge that makes v0.4 main commit `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d` an ancestor of then-current develop without changing develop's tree, then prove PR #93 can construct its prospective merge result.

## Scope

1. After the governing PR #94 is reviewed and integrated, fetch exact remote state and bind `D` to current `origin/develop`.
2. Revalidate exact main `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`, PR #93 `CONFLICTING/DIRTY`, and absence of v0.4.1 tag/Release.
3. From exact `D`, create isolated `work/bridge-v0-4-squash-topology-once` and one merge commit whose first parent is `D`, whose other parent is exact main, and whose tree is byte-identical to `D`.
4. Push only that task branch; open a protected PR to develop; require strict protected Python 3.11, Python 3.13, and Build distributions checks.
5. Obtain independent review of commit parents, exact tree identity, diff absence, remote identities, and non-mutation boundaries.
6. A dedicated integration action MUST merge the bridge PR with a merge commit, not squash/rebase, and MUST NOT alter protection.
7. Verify resulting develop tree equals `D`, exact main is an ancestor of develop, no release state changed, and refreshed/recreated exact `develop -> main` PR #93 becomes mergeable and starts the four readiness checks.
8. Record evidence/review and close this child. The bridge MUST NOT recur.

## Acceptance criteria

- Governing decision/spec exception is integrated before bridge creation.
- Exact main identity is unchanged and no v0.4.1 tag/Release exists before execution.
- Bridge task commit has exact parents and exact develop-parent tree.
- Bridge PR has zero file-content delta and all protected develop checks pass.
- Independent review passes before integration.
- Integration uses merge-commit ancestry preservation through protected PR; no direct/force push, rebase, squash, or protection change occurs.
- Final develop tree equals pre-bridge `D`; exact main is an ancestor of final develop.
- No source/version/changelog/workflow/product/tag/Release/asset/PyPI/Turbopuffer/configuration state changes.
- PR #93 can construct a prospective merge result after develop advances.

## Explicit exclusions

Any content change; any main commit other than exact `c49dc05`; recurring ancestry sync; squash/rebase/direct/force push; protection mutation; main merge; tag/Release/asset/provenance mutation; PyPI; Turbopuffer; retry after an identity/tree mismatch.

## References

- `.10x/decisions/one-time-v0-4-squash-topology-bridge.md`
- `.10x/decisions/simple-main-release-governance.md`
- `.10x/specs/develop-to-main-release-readiness.md`
- `.10x/specs/protected-github-branches.md`
- `.10x/evidence/2026-07-21-buoy-v0-4-1-prospective-merge-blocker.md`

## Evidence expectations

Exact refs/parents/tree IDs; pre/post protection and release-state observations; PR/check identities; independent review; integration method/commit; ancestry proof; tree equality; PR #93 mergeability/readiness run; no-live-operation attestation.

## Blockers

Blocked until PR #94 integrates these governing records after independent review.

## Progress and notes

- 2026-07-21: Opened from the user-ratified exact bridge contract. No bridge branch, commit, merge, release, provider, or configuration mutation occurred.
