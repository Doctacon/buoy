Status: recorded
Created: 2026-07-14
Updated: 2026-07-14
Relates-To: .10x/tickets/done/2026-07-14-create-buoy-v0-2-1-github-release.md, .10x/decisions/superseded/github-only-release-automation-v0-2-1.md

# Buoy v0.2.1 GitHub Release

## Raw evidence

Sanitized structured preflight, tag, approval, workflow, release, asset, checksum, and attestation observations are retained at `.10x/evidence/.storage/2026-07-14-buoy-v0-2-1-github-release.json`.

## What was observed

Preflight confirmed canonical `main` at reviewed commit `0afde6643162fdedc00810152e226701aa1d38b1`, successful CI run `29362284969`, project/module version 0.2.1, no v0.2.1 tag or Release, preserved annotated v0.2.0 with no Release, PyPI `buoy-search` absent (HTTP 404), unprotected `main`, and the `release` environment requiring reviewer `Doctacon` with self-review allowed.

An annotated `v0.2.1` was created and normally pushed at the reviewed commit. GitHub remote metadata reported object type `tag` and tag object `959a1d814af8a71260bc1e7b84a0b332a3883725`.

Release run `29362749172` passed authoritative tag validation and build, then reached status `waiting` with one pending `release` environment deployment. Only after that gate was observed, deployment `5446773429` was approved. Both jobs completed successfully.

GitHub Release [Buoy v0.2.1](https://github.com/Doctacon/buoy-search/releases/tag/v0.2.1) is published, not draft/prerelease, with generated notes and exactly:

- `buoy_search-0.2.1-py3-none-any.whl` — SHA-256 `9c49b9eb699e66e26455a20b7c529557811d6c259de55706d25e415c7f117183`
- `buoy_search-0.2.1.tar.gz` — SHA-256 `d830a6fe620a6e7d1462f050c695502fb68a42523700ef8481e935e8517a90d7`

Downloaded checksums matched GitHub asset digests. `gh attestation verify` succeeded for both assets with signer workflow `Doctacon/buoy-search/.github/workflows/release.yml` and source ref `refs/tags/v0.2.1`.

Postflight confirmed v0.2.0 still has no Release, PyPI remains absent, and `main` remains unprotected. No source, moved tag, PyPI, branch-protection, package-token, or Turbopuffer mutation occurred.

## Procedure

1. Read-only preflight of main/version/CI/tags/releases/environment/PyPI/branch policy.
2. Created and normally pushed annotated v0.2.1.
3. Observed workflow validation/build and pending environment deployment.
4. Approved the exact pending release deployment.
5. Waited for terminal workflow success.
6. Downloaded assets, matched digests, verified attestations, and rechecked exclusions.

## Limits

GitHub controls hosted release/attestation availability. The hosted run emitted already-tracked Node.js runtime deprecation annotations; `.10x/tickets/2026-07-14-update-node24-github-actions.md` owns that follow-up. Independent review remains required before closure.
