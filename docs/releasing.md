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

For this one-time release only, build the exact promoted `main` commit before
tag creation with all of the following fixed: Python 3.13,
`SETUPTOOLS_SCM_PRETEND_VERSION=0.5.1`, `SOURCE_DATE_EPOCH` equal to that
commit's timestamp, `PYTHONHASHSEED=0`, `TZ=UTC`, and `LC_ALL=C`. Record the
command, commit SHA, filenames, and SHA-256 digests in release evidence. The
override is build metadata only; it does not authorize another version or
change Hatch-VCS as source version authority.

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

SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)" \
SETUPTOOLS_SCM_PRETEND_VERSION=0.5.1 PYTHONHASHSEED=0 TZ=UTC LC_ALL=C \
uv build --python 3.13 --out-dir dist
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

## Post-release closure

After the hosted assets and installed wheel are verified, a separate reviewed
documentation PR replaces `## [0.5.1] - pending` with the authoritative UTC
release date. `validate-source` accepts exactly those two states: pending with
history through v0.5.0 before publication, or dated v0.5.1 history afterward.
Automatic publication remains paused in either state.

## One-time v0.5.1 operator sequence

1. Confirm the promoted `main` commit is exact and its CI passed. Confirm both
   the authoritative `refs/tags/v0.5.1` lookup and GitHub Release lookup are
   absent. Any existing or partial state stops the release.
2. Build once from that commit with the exact command above. Validate the two
   versioned files, record their SHA-256 digests, and pass the clean-wheel
   version/help/tokenizer smoke.
3. Create and push the annotated `v0.5.1` tag at that exact commit. This
   one-time tag-ref push is authorized; direct or force pushes to branches are
   not. If any later step fails, preserve the partial state and stop.
4. Create a draft GitHub Release named `Buoy v0.5.1` with generated notes,
   upload exactly the wheel and source archive without replacement, download
   them through authenticated GitHub asset endpoints, and require both hashes
   to match before publishing the draft. Do not upload to PyPI.
5. Download both published assets again, verify hashes and the tag's peeled
   commit, clean-install the published wheel, and repeat the offline smoke.
   Record that local GitHub tooling cannot issue an Actions OIDC artifact
   attestation; if verifiable attestations are available, verify them too.
6. Only then publish the draft security advisory and open the separate
   changelog-date closure PR. No step contacts Turbopuffer or changes a
   namespace.
