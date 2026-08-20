Status: provisional
Created: 2026-08-19
Updated: 2026-08-19
Ticket: .10x/tickets/2026-08-19-ship-buoy-v0-6-0.md
Decision: .10x/decisions/annotated-tag-triggered-github-releases.md
Specification: .10x/specs/annotated-tag-triggered-github-release.md

# Buoy v0.6.0 and Reusable Release Evidence

## Starting state

- Preparation starts from exact
  `develop@06708ce39e9b5e8c15ce6204c2af4e9c73334ade`, tree
  `7215cfca561987c51f0590345b3d745ae7b33d82`.
- Pre-release main is exact
  `main@caed68fdce3ef91e41c11f5d586a6166837d0392`; its second parent is that
  develop commit and its tree is identical.
- The latest tag and GitHub Release are v0.5.1. v0.6.0 has no local or remote
  tag and no GitHub Release, including drafts, at this checkpoint.
- Existing Release publication is paused and all workflows are read-only.
  Repository immutable Releases are available but disabled.

## Authorized pivot

The owner selected v0.6.0, rejected the bespoke manual procedure, and
explicitly authorized a persistent narrowly scoped GitHub Actions publisher
and repository immutable Releases. The unused one-time decision and
specification are retained as `superseded before use`; no hosted write occurred
under them.

The replacement is conventional: a reviewed release-preparation tree reaches
main, exact-main CI passes, and one annotated version tag is the human
publication approval. GitHub Actions then tests, builds, attests, creates and
verifies a draft, and publishes that same immutable Release. PyPI remains out
of scope.

## Validation recorded so far

- Focused release-automation suite: 24 tests passed with ResourceWarning
  promoted to error.
- Source validator, release-version derivation, Python compilation, workflow
  YAML parsing, Actionlint, and diff hygiene passed on the current candidate.
- Locked Python 3.11 full suite: 1,033 tests passed with ResourceWarning
  promoted to error; source, lock, ranking, and C6 validators passed.
- Locked Python 3.13 full suite: 1,033 tests passed with ResourceWarning
  promoted to error; source and lock validation passed on the same frozen
  workflow/helper/test/docs bytes.
- A fresh 0.6.0 validation build produced a 697,773-byte wheel with SHA-256
  `ed3948d435edc27dfcfc2108bb7547ed4ca2a2a2ba3a3fa8e7e5f18c74851cb1`
  and a 1,227,032-byte sdist with SHA-256
  `7b42488d49b3afe212c080d680550f36e410af80d4b86664761e73760656f1ba`.
  Exact-version distribution validation and an isolated, offline-cache clean
  install passed version, CLI/module/telemetry help, import, and tokenizer
  smoke. The isolated home and cache roots remained empty. These hashes prove
  the candidate procedure; the public workflow rebuilds the exact tagged
  source and publishes only its own validated artifact pair.

## Evidence required to complete

- Final candidate path/blob scope and independent review verdict.
- Task PR, exact-head CI, develop integration, release-readiness PR, ordered
  main merge, and exact-main CI identities.
- Owner-admin immutable-Releases activation and fresh v0.6.0 tag/Release
  absence immediately before tag creation.
- Annotated tag object, exact message/peel/current-main identity, and the
  successful Release workflow run.
- Published Release ID/URL/latest/immutable flags; exact two asset names,
  sizes, API digests, downloaded hashes, and build/release attestations.
- Clean downloaded-wheel version/help/module/telemetry/tokenizer smoke.

## Release-readiness correction

Develop integration PR #137 succeeded and produced exact squash
`ad57706c10bc16cf71103ef00203b3ea80bfa538`. Release PR #138 then ran exact
readiness workflow `32327633991`: Policy and both Python jobs passed, while
Distribution job `96302401935` stopped after clean installation because its
shell assertion expected `0.6.0` instead of the CLI's governed output
`buoy 0.6.0`. The same incorrect expectation existed in the tag workflow.

The failure was deterministic, local to two workflow assertions, and occurred
before any main merge or release-side effect. The bounded repair expects the
program-name prefix in both locations and adds focused source regression
coverage. The prior implementation review is superseded by a repair review;
all earlier full-suite, package, permission, and release-state findings remain
valid for unchanged bytes.

## Effect log

No tag, Release, release asset, attestation, registry publication, provider or
data operation, global installation, real Buoy-home inspection, protection
change, force push, or unrelated hosted mutation has occurred under this
ticket at this provisional checkpoint.

This record is evidence, not a reusable credential or an instruction to bypass
the workflow's reviewed tag boundary.
