Status: recorded
Created: 2026-07-14
Updated: 2026-07-14
Relates-To: .10x/tickets/2026-07-14-repair-release-workflow-and-bump-v0-2-1.md

# Buoy v0.2.1 Workflow Repair Validation

## Observed

Release validation now obtains the tag ref object type from the authoritative GitHub Git Data API and passes that value to a side-effect-free checker. It no longer infers annotation from checkout's dereferenced local ref. Project/module/lock/build assets and release docs target 0.2.1. Changelog preserves v0.2.0 as an annotated tag without a Release.

Remote preflight confirmed v0.2.0 still resolves to Git object type `tag`, failed run 29360369610 remains completed/failure at commit d846d2b, and no v0.2.0 Release exists.

## Validation

- Focused release automation: 9 tests passed.
- Full suite: 235 tests passed.
- Built exact `buoy_search-0.2.1` wheel and sdist.
- Positive remote-type/tag/assets checks passed; lightweight type `commit` rejection is unit-tested.
- `uv lock --check` and `git diff --check` passed.
- No tag, release, PyPI, branch-protection, or Turbopuffer mutation occurred during repair validation.

## Limits

Hosted behavior requires the repaired commit to be pushed and canonical main CI to pass. No v0.2.1 tag was created.
