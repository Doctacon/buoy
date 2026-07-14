Status: superseded
Created: 2026-07-14
Updated: 2026-07-14
Superseded-By: .10x/decisions/github-only-release-automation-v0-2-1.md

# GitHub-Only Release Automation

## Context

Buoy is now a public showcase repository but has no CI workflows, badges backed by automation, releases, changelog, release procedure, or branch policy. The package is not published to PyPI. Public signals must be truthful and release authority must remain explicit.

## Decision

- Version 0.2.0 will be released on GitHub only. No PyPI project or publication is created.
- CI runs on pull requests and pushes using repository-native uv/test/build/documentation checks. `main` remains unprotected by explicit user choice.
- Production release is triggered by an annotated `vX.Y.Z` tag whose version must exactly match project/module metadata.
- The release job uses a GitHub `release` environment with required approval before GitHub Release creation.
- Release artifacts are the wheel and sdist built once from the tagged commit, with GitHub artifact provenance attestation and generated release notes.
- Workflows use least-privilege permissions and pin external actions to full commit SHAs. No long-lived publication token is stored.
- README initially shows only real CI and Apache-2.0 badges. A latest-GitHub-release badge is added only after v0.2.0 exists. PyPI, download, star, coverage, and security badges are excluded unless the corresponding maintained system later exists.
- Release mechanics remain locally reproducible with uv and standard shell/Python commands.

## Alternatives considered

### GitHub plus PyPI trusted publishing

Rejected for 0.2 by user choice. PyPI OIDC is viable later but would introduce an external package-publication boundary not currently desired.

### Manual-dispatch release

Rejected in favor of conventional version tags plus an explicit environment approval gate.

### GitHub Release published-event trigger

Rejected because it makes the release object precede validated artifact construction and provenance.

### Required CI branch protection

Rejected by user choice. CI remains advisory on pull requests/pushes for now.

### Decorative badge set

Rejected. Badges without real maintained evidence make the showcase less trustworthy.

## Consequences

The first release requires workflows/public-project docs to be committed and pushed, a passing main CI run, external `release` environment configuration, an annotated `v0.2.0` tag, approval of the pending release deployment, and verification of release assets/attestations. A tag may exist before approval; rejected/abandoned deployments require deliberate cleanup rather than automatic publication.
