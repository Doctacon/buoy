Status: recorded
Created: 2026-07-21
Updated: 2026-07-21
Relates-To: .10x/tickets/2026-07-21-implement-simple-main-release-automation.md, .10x/specs/develop-to-main-release-readiness.md, .10x/specs/main-push-automatic-github-release.md, .10x/tickets/2026-07-21-finalize-buoy-v0-4-0-changelog.md

# Simple Main Release Automation Implementation

## What was observed

The implementation worktree adds the four-check prospective-main readiness workflow, replaces tag-trigger/manual-environment publication with serialized main-push automation, and moves release-critical validation/state logic into `scripts/release_automation.py`. The state machine emits hash-addressed plans, accepts absent/absent only for create, accepts complete exact state only for no-op, and rejects partial or mismatched state without repair behavior.

The sole legacy provenance exception is exact published v0.4.0: annotated `v0.4.0`, peeled commit `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`, Release `Buoy v0.4.0`, exact wheel/sdist names and recorded digests, repository `Doctacon/buoy-search`, workflow `release.yml`, source commit, subjects, and historical source ref `refs/tags/v0.4.0`. Tests prove a changed SHA, either changed asset digest, repository, workflow, source ref, source commit, or other state mismatch fails. A future-version tag source ref fails; future versions require `refs/heads/main`.

`CHANGELOG.md` records the already-observed v0.4.0 date and links. `docs/releasing.md` documents the version-bump/develop-PR/main-PR flow, fail-closed publication, the narrow v0.4.0 transition, portable local commands, and self-hosted mappings.

## Procedure and results

### Focused and static validation

- `uv run --python 3.13 python -m unittest tests.test_release_automation -v`: 24 focused tests passed.
- PyYAML parsed all three workflow files and found job mappings.
- `python3 -m py_compile scripts/release_automation.py tests/test_release_automation.py`: passed.
- `uv lock --check`: passed with 130 resolved packages.
- CLI dry state generation accepted the exact legacy v0.4.0 snapshot as `noop` at the recorded commit and emitted `refs/tags/v0.4.0`; the same snapshot with SHA `2222222222222222222222222222222222222222` failed permanently.
- Static forbidden-operation scan found no release-workflow environment gate, manual dispatch, publish command, destructive Release/tag/ref operation, or force push.
- `git diff --check`: passed.
- `git fetch origin develop` followed by exact `HEAD == origin/develop` comparison passed before commit, proving the work began on current develop.

### Complete Python validation

On locked CPython 3.11:

- `scripts/validate_ranking_contract.py`: passed; 90 composite identities, 13 datasets/folds, 369 judgments, dataset bundle SHA-256 `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`.
- `scripts/c6_syntax_forecast.py validate`: passed while retaining readiness false; forecast SHA-256 `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
- `python -m unittest discover -s tests -p 'test_*.py' -q`: 531 tests passed in 72.618 seconds.

On locked CPython 3.13:

- Ranking validation passed with the same frozen identities and dataset digest.
- C6 forecast validation passed with the same intentionally blocked result.
- Complete suite: 531 tests passed in 66.652 seconds.

Both complete suites emitted only the pre-existing mocked temporary plan-artifact cleanup advisories and an upstream lxml deprecation warning; neither affected success.

### Deterministic distributions and clean-wheel smoke

Two builds used the same commit timestamp as `SOURCE_DATE_EPOCH` and `PYTHONHASHSEED=0`, `TZ=UTC`, `LC_ALL=C`. `scripts/release_automation.py artifacts` passed on each build, including names, metadata, forbidden inventory, exact entry point, and required tokenizer files in wheel and sdist. Corresponding digests were identical:

- wheel: `8bc92c5638b698e88a9c501fc1dfd725418f6eb1ffa9841a354b44738682cefa`;
- sdist: `4d1dbae9009b101e4945eac4995d1fe9b7a916d2c331e1ffbc4e2326a85032a3`.

A normal fresh virtual environment installed the wheel with dependencies. `buoy --version` returned `buoy 0.4.0`; `buoy --help` and `python -m buoy_search --help` succeeded; mandatory loading of the bundled tokenizer returned exact smoke count 9.

### Hosted exact-head CI

Commit `af7841a` was pushed to `work/implement-simple-release` and opened as PR #89 targeting `develop`: `https://github.com/Doctacon/buoy-search/pull/89`. CI run `29860668978` passed all ordinary protected checks on that implementation commit:

- Python 3.11 job `88736249196`: passed in 1m52s;
- Python 3.13 job `88736249170`: passed in 1m41s;
- Build distributions job `88736713496`: passed in 11s.

A following record-only evidence commit requires the same checks to rerun at final PR head before handoff.

## What this supports

This supports local implementation and deterministic-validation acceptance for `.10x/tickets/2026-07-21-implement-simple-main-release-automation.md`, including the approved exact v0.4.0 transition. It also supports the source portion of v0.4.0 changelog finalization and hosted CI for the implementation commit.

## PR #89 blocker repair

Targeted repair after review tightened stable SemVer to reject leading-zero core identifiers and validates changelog dates as real calendar dates. Readiness Policy now scans the bounded release-behavior surface of every workflow plus both release helpers and rejects forbidden registry/backend behavior. The publication workflow's ref-creation 422 branch now performs one full authoritative tag, Release, API asset, downloaded digest, and provenance reinspection: exact complete state emits no-op so attestation and Release creation are skipped; partial or mismatched state fails. The unconditional final verifier now performs the same fresh hosted readback, download/digest comparison, and provenance verification for both initial no-op and create paths.

Executable fake-`gh` tests ran the actual workflow shell for exact-complete and partial 422 fixtures and for both final-verification entry paths. Focused Python 3.13 release tests passed 27 tests. Full locked Python 3.11 and 3.13 suites each passed 534 tests; ranking and C6 validators retained their recorded hashes. Two clean deterministic builds had identical manifests: wheel `466c167fbc3a7c20d71baeee6f8f4f4bc8c440ab563044198635827c8dc088a4`, sdist `513483974f62ba48eae0a556f5efdab8b175131ae64eb47f1daf9604206032db`. Artifact inspection, normal clean-wheel CLI/help, and exact tokenizer count 9 passed. `uv lock --check`, workflow YAML parsing, repository policy scan, Python compilation, and `git diff --check` passed.

The standalone current-tree `release_automation.py validate` command correctly failed because the already-released v0.4.0 section is dated rather than a future version's required pending section. This is not used by ordinary develop PR CI; a future develop-to-main release PR must bump to a new stable version and create its pending section as specified.

## Limits

This evidence does not prove hosted workflow execution, GitHub protection/environment configuration, a future version-bumped prospective merge, tag/Release publication, or independent rereview. No live configuration, environment, tag, Release, main, registry, backend, provider, namespace, or user state was read or mutated. Hosted final-head PR checks and independent rereview remain closure gates for the implementation ticket.
