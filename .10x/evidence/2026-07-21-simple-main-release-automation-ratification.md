Status: recorded
Created: 2026-07-21
Updated: 2026-07-21
Relates-To: .10x/specs/develop-to-main-release-readiness.md, .10x/specs/main-push-automatic-github-release.md, .10x/tickets/done/2026-07-21-shape-simple-main-release-automation.md

# Simple Main Release Automation Ratification

## Decision

After independent review, the user selected `Confirm simplest flow (Recommended)` and ratified:

- main strict freshness/main-ancestor and last-push approval removed; four required checks validate GitHub's prospective develop-to-main merge result;
- develop keeps strict ordinary CI;
- main retains the previously accepted force-push allowance, but workflows/agents remain prohibited from using it;
- stable `MAJOR.MINOR.PATCH` releases only, with exact version/changelog readiness;
- serialized non-cancelling deterministic main-push builds;
- automatic annotated tag, exact provenance, and GitHub Release with no environment/manual approval;
- exact complete-state no-op only; every partial/mismatched state permanently fails without automated completion, overwrite, move, deletion, cleanup, or repeated mutation;
- a subsequently approved, narrowly pinned transition exception accepts the already-published v0.4.0 provenance source ref `refs/tags/v0.4.0` only when tag `v0.4.0`, commit `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`, wheel SHA-256 `89b84c6beba2979ab6ffd0d244d1d0f5c1af938cfbec021a89094a7109e5c4c8`, sdist SHA-256 `9c0469d2fc03b8e03780b06793537736391c21f0ed07c43adab9e674988ffd3a`, repository `Doctacon/buoy-search`, workflow `release.yml`, subjects, and every other Release identity field all match; every future version still requires `refs/heads/main`;
- mandatory deletion of the unused release environment after zero references/deployments;
- explicit supersession of old ceremony, truthful v0.4 record reconciliation, preserved history, and a repository-local self-hosted migration path.

## Effect

The two focused specs are active. This ratification permits opening bounded implementation and hosted-configuration tickets. It does not itself edit workflows/docs/scripts/tests, change protection/environment, choose/bump a version, merge main, create a tag/Release, publish to a registry, or access Turbopuffer/user state.

## Provenance

- Initial upstream choices: release ceremony removal, exact-state no-op/otherwise fail, fully automatic publication.
- Independent review: `.10x/reviews/2026-07-21-simple-main-release-automation-shaping-review.md`.
- Final exact confirmation: `Confirm simplest flow (Recommended)` in the current workstream.
