Status: done
Created: 2026-07-19
Updated: 2026-07-19
Parent: .10x/tickets/done/2026-07-19-buoy-v0-4-compatibility-removal-plan.md
Depends-On: None

# Remove Buoy 0.4 Console Alias

## Scope

Implement `.10x/specs/buoy-v0-4-console-alias-removal.md` as one bounded 0.4.0 package cutover:

- remove the `turbo-search` script entry from `pyproject.toml`;
- delete the dedicated `buoy_search.cli:legacy_main` hook and alias-only tests/imports;
- set coherent candidate 0.4.0 package/module/lock metadata required to build and identify the candidate wheel;
- replace legacy-presence validation with wheel metadata, clean-install, and same-environment released-0.3.0-to-candidate-0.4.0 upgrade validation;
- update only console-command migration, changelog, package identity, and release-validation text affected by this removal.

## Acceptance criteria

- Source and built metadata expose `buoy = buoy_search.cli:main` and no `turbo-search` entry point; `legacy_main` is absent.
- `buoy --help`, `buoy --version`, `python -m buoy_search --help`, parser behavior, outputs, exit codes, direct-command defaults, and safety gates remain unchanged except the reported 0.4.0 version.
- Candidate package/module/lock metadata consistently identifies 0.4.0 without tagging, publishing, or creating a release.
- A fresh isolated candidate-wheel install has `buoy` and no package-owned `turbo-search` launcher.
- A second isolated environment installs the released GitHub 0.3.0 wheel only after verifying SHA-256 `048dba11df692a7efcd7ab7269fc2eec82f6b53e57573a3de113bbd051750bab`, proves both 0.3 launchers, upgrades that same environment normally to the candidate wheel, then proves 0.4.0 `buoy` works and package metadata plus launcher-directory inspection find no `turbo-search`.
- Focused CLI/package/release tests, complete Python 3.11/3.13 suites, wheel/sdist build and inventory, migration-reference checks, independent review, and hosted checks pass.
- Console migration guidance says only to replace the executable name and does not promise deletion of user-owned launchers.
- No retained compatibility, state/data, remote behavior, or environment-alias behavior changes.

## Validation and evidence expectations

Record exact changed files, artifact paths/hashes/versions, 0.3 URL and digest verification, isolated install/upgrade commands, installed entry points and launcher listings before/after, primary CLI outputs, focused/full tests, distribution inventory, hosted run identities, and an explicit no-state/no-remote/no-publication attestation. Evidence must distinguish clean-install absence from same-environment upgrade deletion.

## Dependencies and parallelism

No child execution dependency. Work may proceed in parallel with `.10x/tickets/done/2026-07-19-remove-buoy-v0-4-environment-aliases.md`, but the two reviewed diffs and coherent 0.4.0 metadata must be assembled into one aggregate candidate before integration to `develop`.

## Blockers

None.

## Explicit exclusions

Environment-alias runtime/config changes; removal of any other compatibility; arbitrary user-owned launcher cleanup; unrelated parser refactoring; state/data migration; remote operations; PyPI publication; Git tag/GitHub Release creation; stale skill-reference correction.

## References

- `.10x/tickets/done/2026-07-19-buoy-v0-4-compatibility-removal-plan.md`
- `.10x/specs/buoy-v0-4-console-alias-removal.md`
- `.10x/specs/buoy-v0-4-environment-alias-removal.md`
- `.10x/decisions/buoy-product-identity-and-compatibility-v0-3.md`
- `.10x/evidence/2026-07-16-buoy-v0-3-0-github-release.md`

## Progress and notes

- 2026-07-19: Opened from the ratified active console-removal specification. No implementation performed.
- 2026-07-19: Began bounded implementation on `work/remove-v0-4-console-alias` from `develop` commit `31b355a`; read the governing plan, both active 0.4 compatibility specs, identity/local/precision/release-validation specs, compatibility inventory research, shaping reviews, and immutable v0.3.0 release evidence before changing source.
- 2026-07-19: Implementation commit `8fca87520847433fd325e82ddf4e2e487ae03d14` removes only the package console entry and dedicated hook, advances project/module/lock metadata to 0.4.0, replaces alias-only tests with bounded package/source/migration assertions, and updates affected active identity/release-validation and user/release text. Isolated Python 3.11 and 3.13 full suites each passed 414 tests; focused Python 3.13 passed 48 tests.
- 2026-07-19: Exact-commit wheel/sdist build, metadata/content inventory, clean Python 3.13 install, and digest-verified released-0.3.0-to-candidate-0.4.0 same-environment upgrade passed. Clean install had only `buoy`; pre-upgrade metadata/launchers had `buoy` and package-owned `turbo-search`; post-upgrade metadata and launcher directory had only `buoy`. Evidence: `.10x/evidence/2026-07-19-remove-buoy-v0-4-console-alias.md`. No state/data/remote/publication/tag/release operation occurred. Independent review and hosted checks remain required before closure.
- 2026-07-19: Opened PR #47 without merging. Hosted CI run `29707534036` passed Python 3.11 job `88246909509`, Python 3.13 job `88246909505`, and distribution build job `88246964840` on pushed head `5bfa8455f35f12aae0041f8cfec98c6bec70e22f`.
- 2026-07-19: Independent bounded review passed implementation head `f518a78` and observed exact-head hosted checks. Integration remains blocked until the environment-alias child and aggregate 0.4 reconciliation pass. Review: `.10x/reviews/2026-07-19-buoy-v0-4-console-alias-removal-review.md`. Ticket remains active.
- 2026-07-19: Full reviewed tip `b6bbfcc` is preserved as an ancestor of aggregate candidate `68477fdca5a5b5f7b890d059c484739f02fc1dd8`. Aggregate build/install/upgrade and Python 3.11/3.13 validation passed with the sibling environment removal present. Evidence: `.10x/evidence/2026-07-19-buoy-v0-4-compatibility-removal-candidate.md`. Independent aggregate review remains pending; ticket stays active.
- 2026-07-19: Post-assembly packaging repair preserved runtime/package code and reran clean plus digest-verified released-0.3.0 same-environment upgrade validation: pre-upgrade metadata/launcher inspection had both package-owned launchers; candidate metadata and the complete post-upgrade launcher directory had only `buoy`, with no `legacy_main` source/package hook change. Evidence: `.10x/evidence/2026-07-19-exclude-internal-records-from-buoy-v0-4-artifacts.md`.
- 2026-07-19: Final aggregate closure review and exact-head hosted checks passed; all acceptance criteria map to child and aggregate evidence. Review: `.10x/reviews/2026-07-19-buoy-v0-4-compatibility-removal-closure-review.md`.
