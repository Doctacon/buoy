# Releasing Buoy

Buoy releases are GitHub-only. Buoy is not published to PyPI, and release automation never contacts Turbopuffer.

## Simple release flow

1. On a task branch from `develop`, choose the next stable `MAJOR.MINOR.PATCH` version.
2. Set that exact version in `pyproject.toml`, `src/buoy_search/__init__.py`, and `uv.lock`.
3. Keep `Unreleased` empty and add exactly one `## [X.Y.Z] - pending` changelog section. Every older release section must have its ISO release date.
4. Open the ordinary task pull request to `develop` and pass the strict CI checks.
5. Open a pull request from the repository's exact `develop` branch to `main`. GitHub validates its prospective merge result with exactly four required checks:
   - `Release readiness / Policy`
   - `Release readiness / Python 3.11`
   - `Release readiness / Python 3.13`
   - `Release readiness / Distribution`
6. Merge the passing pull request. The push to `main` automatically validates both Python versions, builds once deterministically, creates the annotated tag, attests the exact wheel and sdist, and creates the GitHub Release.
7. Verify the hosted tag, Release, two asset digests, and provenance. Then date the changelog section and update its links in a separately reviewed task pull request to `develop`.

There is no release-specific ancestry sync, tag push, workflow dispatch, or environment approval. Do not create a tag manually. A main commit with an unchanged released version is rejected by readiness. The release workflow accepts an already-published version only when its annotated tag, exact commit, Release identity, two asset digests, and provenance are all complete and exact.

## Fail-closed publication

Publication is serialized repository-wide and runs with cancellation disabled. Validation, testing, building, artifact inspection, and state planning are read-only. Only the final job receives write permissions; it downloads the immutable build and plan, installs nothing, and executes no checked-out repository code.

An absent tag and absent Release produce the only create plan. An exact complete state produces a no-op. Lightweight tags, partial state, conflicting commits, missing or changed assets, and provenance mismatches fail permanently for that version. Automation never moves, overwrites, deletes, or repairs release objects. Recovery requires a separately authorized operator decision or a new version.

The already-published v0.4.0 is the sole transition exception: its exact recorded tag, commit, two asset digests, repository, workflow, subjects, and Release identity accept the historical provenance source ref `refs/tags/v0.4.0`. Any mismatch fails. Every future version requires `refs/heads/main`.

## Portable local checks

The release-critical logic is standard Python in `scripts/release_automation.py`. On a release-preparation commit, run:

```bash
python3 scripts/release_automation.py validate
uv sync --locked --python 3.11
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q
uv sync --locked --python 3.13
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q
```

Build with the commit timestamp and deterministic environment used by both workflows:

```bash
export SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)"
export PYTHONHASHSEED=0 TZ=UTC LC_ALL=C
rm -rf /tmp/buoy-release-dist
uv build --out-dir /tmp/buoy-release-dist
python3 scripts/release_automation.py artifacts \
  --dist /tmp/buoy-release-dist --output /tmp/buoy-release-manifest.json
```

`state` accepts a normalized hosted snapshot and emits a hash-addressed create/no-op plan without mutation. Tests exercise every collision and permanent-failure branch without touching hosted state.

## Self-hosted migration

The workflows are adapters, not release authority. On a self-hosted Git forge and runner:

| GitHub check or operation | Self-hosted equivalent |
| --- | --- |
| Policy | Construct the prospective `develop`-to-`main` merge commit, then run `release_automation.py policy` with exact base/head identities and a normalized forge snapshot. |
| Python 3.11 / Python 3.13 | Run the locked validator and complete-test commands above in independent workers and require both statuses. |
| Distribution | Build once with the deterministic environment, run `artifacts`, perform a normal fresh-wheel install, and load/smoke-count the bundled tokenizer. |
| Annotated tag | Create one standard annotated Git tag with the planned tagger/message and atomically create its ref. |
| Provenance | Sign an in-toto/SLSA statement over the exact manifest names and SHA-256 digests, repository, workflow, source ref, and source commit. |
| GitHub Release | Use the forge's generic release API to create a non-draft/non-prerelease release with generated notes and the exact wheel/sdist. |

Configure the forge to require the same four prospective-merge statuses and to serialize the main-push publisher. Preserve the state-plan schema and standard wheel, sdist, Git tag, SHA-256, and in-toto/SLSA objects. No proprietary package registry or GitHub-only artifact format is required.
