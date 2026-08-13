# Releasing Buoy

## Automatic publication remains paused

The write-capable GitHub release workflow remains disabled. The existing
v0.5.0 lightweight tag and asset-less GitHub Release are preserved as
historical state and are not repaired or replaced.

No current workflow has write permission. A push to `main` runs a read-only
source validation and cannot create or change a tag, Release, artifact
attestation, package publication, or provider resource.

The reviewed v0.5.1 security fix is a one-time manual GitHub-only release after
the exact promoted `main` commit passes the complete validation below. It must
produce an annotated `v0.5.1` tag plus one wheel and one source archive. It must
not publish to PyPI or contact Turbopuffer. Any pre-existing or partial v0.5.1
tag, Release, or asset state is a stop condition rather than permission to
overwrite or delete it.

## Current version authority

Source metadata remains dynamic:

- `project.dynamic = ["version"]`;
- Hatch VCS derives versions from Git;
- Hatch generates `src/buoy_search/_version.py` during build/install;
- the generated file is ignored;
- the editable `uv.lock` root is versionless.

Development builds therefore report a tag-derived development version. No
static version should be added just to make the old publisher run.

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

uv build --out-dir dist
uv run python scripts/release_automation.py validate-distribution dist
```

`validate-source` verifies dynamic metadata, the generated-version import and
ignore rule, the versionless editable lock root, published changelog history
through v0.5.0, the pending v0.5.1 notes, and parsed workflow permissions.
`validate-distribution` checks the
focused archive boundary, entry point, bundled tokenizer, metadata agreement,
and absence of Command Center, catalog, routing, evidence, frontend, and
internal records.

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
