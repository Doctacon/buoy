# Releasing Buoy

Buoy releases on GitHub only. It is not published to PyPI. The annotated `v0.2.0` tag is preserved as a failed pre-release attempt without a GitHub Release, and `v0.2.1` is the first published Release. The next planned release is `v0.3.0`.

## Release contract

An annotated `vX.Y.Z` tag starts `.github/workflows/release.yml`. Validation enforces the annotated tag object, exact package versions, and the pinned Hatchling build backend before artifact construction. GitHub Release creation waits for approval through the `release` environment, then attaches the wheel and source distribution and records provenance attestations.

The workflow never creates the tag, publishes to a package registry, modifies a branch, or contacts Turbopuffer.

## Prepare

1. Update `pyproject.toml` and `src/buoy_search/__init__.py` to the same version.
2. Move relevant `CHANGELOG.md` entries from Unreleased into a pending version section. Keep it marked pending and omit release/compare links until the downstream release ticket verifies that the GitHub Release exists.
3. Run the exact portable checks used by CI:

   ```bash
   uv sync --locked --python 3.13
   PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q
   rm -rf /tmp/buoy-release-dist
   uv build --out-dir /tmp/buoy-release-dist
   uv run --no-project python scripts/release_checks.py tag --tag v0.3.0
   uv run --no-project python scripts/release_checks.py assets --dist /tmp/buoy-release-dist
   ```

4. Land release preparation in `develop` through a passing task pull request.
5. Confirm the `develop` CI workflow succeeds.
6. Open a release pull request from `develop` to `main`, incorporate current `main`, and merge it with a merge commit after all required checks pass.
7. Confirm the `main` CI workflow succeeds on the reviewed release commit.
8. Confirm the GitHub `release` environment exists with the intended approval rule.

## Create v0.3.0

Create the tag only from the reviewed main commit:

```bash
git switch main
git pull --ff-only
git tag -a v0.3.0 -m "Buoy v0.3.0"
# Hosted workflow verifies remote GitHub tag metadata after push
git push origin v0.3.0
```

The tag starts the release workflow. Review its validated commit and artifacts, then approve the pending `release` environment deployment. Do not approve a run for an unexpected commit, version, or artifact set.

## Verify

After the workflow succeeds:

- confirm the GitHub Release points to the tag commit;
- download and inspect both `buoy_search-0.3.0-py3-none-any.whl` and `buoy_search-0.3.0.tar.gz`;
- verify the GitHub provenance attestation;
- confirm no PyPI project or publication was created;
- record the workflow, release, tag, assets, and attestation in durable evidence;
- only after that observation, replace the changelog's pending marker and add release/compare links in a separately reviewed source commit.

The workflow refuses to overwrite an existing release. Resolve conflicting tag/release state explicitly rather than deleting or replacing it automatically.
