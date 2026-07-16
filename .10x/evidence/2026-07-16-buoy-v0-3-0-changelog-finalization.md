Status: recorded
Created: 2026-07-16
Updated: 2026-07-16
Relates-To: .10x/tickets/2026-07-15-finalize-buoy-v0-3-0-changelog.md, .10x/tickets/done/2026-07-15-create-buoy-v0-3-0-github-release.md

# Buoy v0.3.0 Changelog Finalization

## What was observed

The reviewed hosted-release evidence `.10x/evidence/2026-07-16-buoy-v0-3-0-github-release.md` records published GitHub Release `355388511` at <https://github.com/Doctacon/buoy-search/releases/tag/v0.3.0>, annotated tag object `21a8d122151711a863dfb63d356baebbddca8d45`, and reviewed main commit `595d157177bd032c20cf6e6c0112ee6b43212a88`.

Fresh read-only checks observed:

- `git ls-remote --tags origin refs/tags/v0.3.0 refs/tags/v0.3.0^{}` returned the same tag object and peeled commit;
- the exact public Release URL returned HTTP 200;
- the public Release page title is `Release Buoy v0.3.0 · Doctacon/buoy-search · GitHub` and reports the release time `2026-07-16T22:17:09Z`, establishing release date `2026-07-16`;
- GitHub's JSON release API returned transient HTTP 503/HTML responses during this verification. No mutation was attempted, and the public page plus already-reviewed hosted evidence supplied the required authority.

The scoped changelog diff:

- replaces `## [0.3.0] - pending` with `## [0.3.0] - 2026-07-16`;
- advances `[Unreleased]` from `v0.2.1...HEAD` to `v0.3.0...HEAD`;
- adds `[0.3.0]: https://github.com/Doctacon/buoy-search/releases/tag/v0.3.0`;
- preserves all release content and the existing v0.2.1 link.

## Procedure

1. Read the finalization ticket and reviewed hosted release evidence.
2. Queried the exact remote annotated tag and peeled commit read-only.
3. Requested the public release URL and inspected its release timestamp/title read-only.
4. Applied three bounded changelog metadata changes.
5. Updated only the existing changelog regression test assertions to require the finalized date, exact release link, and advanced Unreleased comparison. An interrupted edit had emptied that test file locally; it was restored byte-for-byte from `HEAD` before the narrow 6-addition/3-deletion assertion change, and diff inspection confirmed all other tests remained intact.
6. Ran focused release automation tests, the full suite, package release tag dry-check, documentation link/reference checks, Python compilation, and `git diff --check`.

## Validation results

- `uv run python -m unittest tests.test_release_automation -v`: 10 tests passed.
- `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q`: 364 tests passed.
- `uv run --no-project python scripts/release_checks.py tag --tag v0.3.0`: passed.
- Changelog metadata assertions and local documentation references: passed.
- `uv run python -m compileall -q src tests scripts`: passed.
- `git diff --check`: passed.
- Final test diff: 6 additions / 3 deletions in the existing changelog test; no broad deletion remained.

## What this supports

This supports that the post-release changelog date and links are sourced from the observed hosted v0.3.0 Release, are internally consistent, and do not change release content or product behavior.

## External-side-effect attestation

This child performed only Git/GitHub/public-web reads and local tracked-file edits. It did not mutate main, develop, tags, GitHub Releases, assets, workflows, branch protection, PyPI, or Turbopuffer.

## Limits

Hosted PR checks and independent review remain required before integration to develop. The GitHub JSON API was transiently unavailable, but this did not contradict the current public page, remote annotated tag, or previously verified hosted evidence.
