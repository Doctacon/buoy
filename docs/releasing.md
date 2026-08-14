# Releasing Buoy

## Automatic publication remains paused

The write-capable GitHub release workflow remains disabled. The existing
v0.5.0 lightweight tag and asset-less GitHub Release are preserved as
historical state and are not repaired or replaced.

No current workflow has write permission. A push to `main` runs a read-only
source validation and cannot create or change a tag, Release, artifact
attestation, package publication, or provider resource.

Buoy v0.5.1 was published on 2026-08-13 through the consumed one-time manual
GitHub-only procedure. Its annotated tag peels to
`284b309a02546b13a63e709d9afe7f72c557b474`, and GitHub Release `369682440`
contains the wheel and source archive. The security advisory was published
only after those assets and a clean installation were verified. That completed
procedure grants no authority for another tag or Release.

## Current version authority

Source metadata remains dynamic:

- `project.dynamic = ["version"]`;
- Hatch VCS derives versions from Git;
- Hatch generates `src/buoy_search/_version.py` during build/install;
- the generated file is ignored;
- the editable `uv.lock` root is versionless.

Development builds therefore report a tag-derived development version. No
static version should be added just to make the old publisher run.

The v0.5.1 release build used Python 3.13 and an exact
`SETUPTOOLS_SCM_PRETEND_VERSION=0.5.1` build override before its tag existed.
That override is historical evidence, not current version or publication
authority. New development builds continue to derive their version from Git.

## Read-only validation

Run:

```bash
uv sync --locked --python 3.11
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/release_automation.py validate-source
uv lock --check
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q

uv sync --locked --python 3.13
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q

uv build --python 3.13 --out-dir dist
uv run python scripts/release_automation.py validate-distribution dist
```

`validate-source` verifies dynamic metadata, the generated-version import and
ignore rule, the versionless editable lock root, published changelog history
through v0.5.1 with no staged release, and parsed workflow permissions.
`validate-distribution` checks the
focused archive boundary, entry point, bundled tokenizer, metadata agreement,
presence of the bounded catalog/routing/evaluation modules, and absence of the
Command Center, evidence system, frontend, and internal records.

The legacy `validate`, `artifacts`, `state`, `github-snapshot`, and `policy`
commands fail cleanly with the paused-publication message. They perform no Git,
GitHub, network, or filesystem mutation.

## Protected checks

The `develop`-to-`main` pull request retains the existing four check names so
branch protection is not stranded:

- `Release readiness / Policy`
- `Release readiness / Python 3.11`
- `Release readiness / Python 3.13`
- `Release readiness / Distribution`

These checks are ordinary read-only validation, testing, and ephemeral
diagnostic builds. They clean-install the wheel and exercise both help paths
and the offline tokenizer, but do not upload or retain the archives. Passing
them does not authorize or trigger publication.

## Current publication boundary

The v0.5.1 changelog is closed with its authoritative 2026-08-13 date, its
one-time release decision is superseded and consumed, and the security advisory
is published. `validate-source` therefore requires published history through
v0.5.1 with no staged release.

Publishing any later version requires a new reviewed release decision and
workflow. Until then, do not create, move, replace, or delete a tag, GitHub
Release, asset, or attestation. Do not add write permissions to the paused
workflow and do not upload Buoy to PyPI. The validation commands above are
diagnostic only and confer no publication authority.
