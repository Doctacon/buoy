Status: active
Created: 2026-07-14
Updated: 2026-07-14

# Buoy CI and GitHub Releases

## Purpose and scope

Provide reproducible CI and GitHub-only release automation for the public Buoy repository.

## CI workflow

- `.github/workflows/ci.yml` MUST run for pull requests and pushes to `main` with default `contents: read` permissions.
- CI MUST use locked dependencies and repository-native commands: `uv sync --locked`, complete tests, documentation/SVG validation, and `uv build`.
- Supported-runtime coverage MUST include Python 3.11 and 3.13. Build need only run once after test success.
- Concurrent runs for the same ref SHOULD cancel older in-progress runs.
- CI MUST NOT read repository secrets, publish artifacts externally, call Turbopuffer, or mutate repository state.
- External actions MUST be pinned to full commit SHAs with comments naming their upstream versions.

## Release workflow

- `.github/workflows/release.yml` MUST trigger only on tags matching `v*`.
- Before release mutation it MUST verify the tag is exactly `v<project version>`, package/module versions agree, and authoritative remote GitHub tag metadata identifies an annotated tag object. It MUST NOT infer annotation from checkout's dereferenced local ref.
- It MUST run the complete release validation, build the wheel and sdist once from the tagged commit, and retain them as workflow artifacts.
- The mutation job MUST use the GitHub environment `release`; environment approval is the launch boundary.
- Release permissions MUST be minimal and explicit: read source, write release contents, issue OIDC identity, and write attestations only where needed.
- After approval it MUST attest wheel/sdist provenance and create a GitHub Release for the existing tag with generated notes and both artifacts.
- Re-running MUST not silently overwrite a conflicting release. Fail with a clear diagnostic if the tag/release/version state is inconsistent.
- The workflow MUST NOT publish to PyPI, create another registry project, modify branches, or call Turbopuffer.

## Local reproducibility and validation

- `docs/releasing.md` MUST list the same local validation/build commands and exact first-release sequence.
- Workflow YAML, permissions, triggers, action pins, version checks, artifact names, and no-PyPI boundary MUST have automated/static validation.
- A dry local harness MUST validate version/tag matching and release-asset selection without creating a tag or release.

## First release

Public annotated `v0.2.0` and failed hosted run `29360369610` are preserved without a GitHub Release. The first intended GitHub Release is `v0.2.1`, only after the remote-tag validation fix and version bump are committed/pushed and CI succeeds on canonical `main`.
