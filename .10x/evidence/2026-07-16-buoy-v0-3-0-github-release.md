Status: recorded
Created: 2026-07-16
Updated: 2026-07-20
Relates-To: .10x/tickets/done/2026-07-15-create-buoy-v0-3-0-github-release.md, .10x/tickets/done/2026-07-15-buoy-v0-3-0-release-plan.md

# Buoy v0.3.0 GitHub Release

## What was observed

### Strict preflight before mutation

Exact remote `main` was the reviewed release merge `595d157177bd032c20cf6e6c0112ee6b43212a88`. Its project, module, and lock metadata all declared 0.3.0; exact-main push CI run `29537732717` passed; and promotion evidence/review named the same commit.

Before tag creation, local and remote `v0.3.0`, a GitHub Release, and any `v0.3.0` release-workflow run were absent. PyPI returned HTTP 404 for `buoy-search`. Prior immutable history was recorded and later rechecked:

- annotated `v0.2.0` object `7eef05d045cc7e59000e2e8ae9abd268e2c21c5f` peels to `d846d2b2e965e7f62ff180442724d02705688a1a` and still has no GitHub Release;
- annotated `v0.2.1` object `959a1d814af8a71260bc1e7b84a0b332a3883725` peels to `0afde6643162fdedc00810152e226701aa1d38b1`; Release `RE_kwDOTCenNM4VGipx` and its two prior asset digests were unchanged.

The existing `release` environment required reviewer `Doctacon`, allowed self-review, and reported the current user able to approve. Exact-main tag/assets dry checks passed. A temporary exact-main build produced the expected wheel and sdist with 0.3.0 metadata, `buoy_search` content, and no old implementation package.

### Tag and approval boundary

The first external mutation created and pushed only annotated `v0.3.0` with message `Buoy v0.3.0`. Authoritative remote metadata reports object type `tag`, object `21a8d122151711a863dfb63d356baebbddca8d45`, peeled commit `595d157177bd032c20cf6e6c0112ee6b43212a88`.

Exactly one tag-triggered run appeared: Release run `29538957482` at the expected commit. Job `87756794753` completed authoritative tag/version validation, all 364 tests, build, asset validation, and retained artifact `8391651975` successfully. The run then reached `waiting`; exactly one pending `release` deployment existed; Release `v0.3.0` was still absent; and the current user was explicitly eligible to approve. Only then was environment `18151168858` approved for the exact run/commit, producing deployment `5481277630`. Publication job `87756932412` and the complete workflow then succeeded.

### Release, assets, installation, and provenance

GitHub Release numeric ID `355388511` / node ID `RE_kwDOTCenNM4VLsxf` is published at <https://github.com/Doctacon/buoy-search/releases/tag/v0.3.0>. It is neither draft nor prerelease, has generated notes plus the `v0.2.1...v0.3.0` full comparison, and contains exactly:

- `buoy_search-0.3.0-py3-none-any.whl` (158,125 bytes), SHA-256 `048dba11df692a7efcd7ab7269fc2eec82f6b53e57573a3de113bbd051750bab`;
- `buoy_search-0.3.0.tar.gz` (965,191 bytes), SHA-256 `e7146865a9c54a418ccf6df7aab8e980895877678cf8e2ecc2483c9c8f863eef`.

Downloaded hashes matched GitHub's asset digests. Both packages report `buoy-search` 0.3.0 and Apache-2.0, include `buoy_search`, catalog, and routing implementation, and omit an old `turbo_search` package. Isolated Python 3.13 wheel installation ran `buoy --version` as 0.3.0; the intentionally retained legacy console alias emitted its 0.4-removal warning and ran 0.3.0; the old Python import remained absent.

Strict `gh attestation verify` succeeded for each asset while enforcing repository `Doctacon/buoy-search`, signer workflow `.github/workflows/release.yml`, source ref `refs/tags/v0.3.0`, source digest `595d157...`, SLSA provenance v1, and GitHub-hosted runners. The signed certificate binds Release run `29538957482`, workflow/ref, repository, and exact commit. Provenance subjects contain both exact asset digests and a Rekor transparency-log timestamp.

### Postflight

Remote main remained `595d157...`; no main/develop/protection mutation was performed by release publication. There is exactly one `v0.3.0` release run and it succeeded. Prior tags/releases remained unchanged, PyPI remained HTTP 404, and no Turbopuffer operation occurred.

## Procedure

1. Fetched exact refs/tags and inspected promotion evidence, versions, main CI, prior tags/releases, absent v0.3.0 state, release environment, workflow contract, and PyPI.
2. Built and inspected wheel/sdist from a temporary detached exact-main worktree; ran local tag/assets checks.
3. Created one annotated tag at exact reviewed main and pushed only `refs/tags/v0.3.0`.
4. Verified remote tag object/peel and the single exact tag-triggered run.
5. Waited for validate/build success and exactly one pending environment deployment; rechecked Release absence and approval eligibility; approved only the exact run/commit.
6. Waited for terminal workflow success; downloaded and hashed assets; inspected package contents/metadata and isolated install behavior; strictly verified provenance; rechecked immutable prior history and no-PyPI state.

Machine-readable observations are in `.10x/evidence/.storage/2026-07-16-buoy-v0-3-0-github-release.json`.

## What this supports

This supports every technical acceptance criterion for the GitHub-only v0.3.0 publication and leaves the ticket active only for independent acceptance review and parent closure.

## Limits and residual risk

- GitHub generated notes include the complete compare range; curated release content remains the pending changelog section until the separately owned post-release finalization child lands.
- Hosted jobs emitted Node.js 20 deprecation/forced-Node-24 annotations but succeeded. The existing owner is `.10x/tickets/done/2026-07-14-update-node24-github-actions.md`; this release did not widen scope to change action pins.
- PyPI absence is an HTTP 404 observation at preflight/postflight, not a permanent guarantee.
- The downloaded dependency installation contacted package indexes for dependencies but did not publish anything. No secret values were recorded.
