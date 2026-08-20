# Releasing Buoy

Buoy publishes versioned wheels and source archives as GitHub Release assets.
It does not publish to PyPI.

## Routine release flow

A routine release has two human actions:

1. Merge a reviewed release-preparation change through `develop` and then into
   `main`.
2. After exact-main CI is green, push one annotated `vMAJOR.MINOR.PATCH` tag at
   that exact `main` commit.

The tag is the publication approval. The reusable `Release` workflow then
validates the annotated tag, runs the complete locked Python 3.11 and 3.13
suites, builds the wheel and source archive once, validates and clean-installs
the wheel, attests both distributions, creates a draft GitHub Release, verifies
the draft downloads byte-for-byte, and publishes that same Release. Published
Releases are immutable.

Before the first automated release, a repository owner enables GitHub's
immutable-Releases setting once and verifies it through the administration
API. The workflow token intentionally has no repository-administration
permission; every run instead proves that the published Release is immutable.

No version-specific release decision, manual artifact upload, or local build-
wheelhouse ceremony is required. A normal bounded implementation ticket and
review still govern source changes. After publication, that ticket receives a
small records-only closure under the repository's ordinary development rules;
the closure does not alter the GitHub Release.

## Release-preparation change

The release change must:

- leave an empty `## Unreleased` section;
- move the accumulated notes under `## [X.Y.Z] - YYYY-MM-DD`;
- add the exact `vPREVIOUS...vX.Y.Z` comparison link;
- update the README wheel URL to the new GitHub Release asset; and
- list the new version as supported in `SECURITY.md`.

`scripts/release_automation.py validate-source` checks those relationships
without contacting GitHub or changing state. The `Release readiness` workflow
retains its four read-only checks on pull requests to `main`; its Distribution
job builds and inspects the exact reviewed release version.

## Version authority

`pyproject.toml` remains dynamic and uses pinned Hatch-VCS. Development
checkouts report a tag-derived development version. Release-readiness builds
use `SETUPTOOLS_SCM_PRETEND_VERSION` only to validate the prospective artifact;
the public workflow builds from the real annotated tag.

Useful local checks are:

```bash
uv lock --check
uv run python scripts/release_automation.py validate-source
uv run python scripts/release_automation.py release-version
uv run python -m unittest tests.test_release_automation -q
```

## Publishing

After the release-preparation merge is present on `main` and exact-main CI is
green, verify that immutable Releases remain enabled and then:

```bash
git fetch origin main --tags
git switch --detach origin/main
git tag -a vX.Y.Z -m "Buoy vX.Y.Z"
git push origin refs/tags/vX.Y.Z
```

Do not use a lightweight tag, move an existing tag, force-push, upload assets
manually, or publish to PyPI. The workflow refuses a mismatched tag, Release,
notes body, or asset set. An exact completed rerun verifies the immutable
Release and succeeds without rewriting it; an exact draft can continue to its
publish step; conflicting or partial state stops for operator inspection.

The build and publication permissions are separated. Every job defaults to
`contents: read`; only the final publication job receives narrowly scoped
`contents: write`, `id-token: write`, and `attestations: write` permissions.
That job cannot delete, replace, or overwrite a public release artifact.

## Portability

The portable contract is conventional Git and Python packaging: an annotated
version tag, a clean build from that tag, exact wheel/sdist validation, and a
release containing those two files. GitHub Actions, GitHub Releases, and GitHub
attestations are the managed-host implementation. A self-hosted forge can use
the same tag, tests, build commands, release notes, and artifact hashes.
