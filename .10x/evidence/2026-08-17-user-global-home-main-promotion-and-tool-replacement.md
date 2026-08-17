Status: recorded
Created: 2026-08-17
Updated: 2026-08-17
Ticket: .10x/tickets/done/2026-08-17-promote-user-global-home-defaults-and-replace-tool-once.md
Decision: .10x/decisions/one-time-user-global-home-main-promotion-and-tool-replacement.md
Authority-Review: .10x/reviews/2026-08-17-user-global-home-main-promotion-authority-review.md
Review: .10x/reviews/2026-08-17-user-global-home-main-promotion-and-tool-replacement-review.md

# User-Global-Home Main Promotion and Tool Replacement Evidence

## Authority trigger and completed prerequisite

The owner explicitly superseded the earlier stop-at-PR boundary and directed
the agent to merge passing pull requests, continue until the requested changes
are on `main`, and install the tool. This record does not interpret that request
as publication, provider, credential, migration, protection, direct-push, or
unrelated authority.

PR #129 integrated the reviewed implementation through the ordinary flow:

- base `develop = e101690bc351d92cc6b24a46cb5bc30f00bd6df0`;
- head `c1b76f329496358198af6a9af1a80a095418af1d`;
- exact-head CI run `32039880977` succeeded with Python 3.11 job
  `95417652397`, Python 3.13 job `95417652864`, and Build distributions job
  `95417935994`;
- GitHub comments, reviews, review requests, and threads were empty and the PR
  was mergeable;
- squash result `D0 = cd3f1bef4c9c4856c727f4891512278eafd82841`;
- `parent(D0) = e101690bc351d92cc6b24a46cb5bc30f00bd6df0`;
- `tree(D0) = 8c6790ac8be55601b25c7b79aad17994b790a533`, exactly the reviewed head tree.

Current release topology at this authority boundary is:

- `M = 7f7ddfe245e1e5b57946eb6ac10dcc01358559fc`;
- `B = merge-base(M,D0) = e101690bc351d92cc6b24a46cb5bc30f00bd6df0`;
- `tree(M) = tree(B) = 98cb3e56af4d867987d4e23f279f68fcf912e666`;
- divergence `M...D0` is two main-only / one develop-only commits;
- neither tip is an ancestor of the other;
- `B..M` has no content diff;
- read-only `merge-tree(M,D0)` is conflict-free and equals exact
  `tree(D0) = 8c6790ac8be55601b25c7b79aad17994b790a533`.

## Pre-install global baseline

Read-only observation before authority integration found:

- `/Users/crlough/.local/bin/buoy` is a symlink to
  `/Users/crlough/.local/share/uv/tools/buoy-search/bin/buoy`;
- uv `0.11.7` manages a healthy 104-package `buoy-search` environment on
  CPython `3.13.0`;
- `buoy --version` reports `0.5.2.dev33+g7f7ddfe24`;
- installed `direct_url.json` SHA-256 is
  `7d181c6d8d00e3d04682f95082ad93b062f47fdf18cbafb6b5a5e021f2908047`
  and binds both commit and requested revision to exact `M`;
- installed `buoy_search/cli.py` SHA-256 is the active receipt
  `92c49e943ed5918df7fe65294ff89717e2654a8e9d76317979b63198f1b98ee9`;
- installed `buoy_search/local_paths.py` is absent, as expected before this
  release; and
- `/Users/crlough/.buoy` is absent.

This was the preliminary baseline only. Every identity and the complete
other-tool inventory was freshly rebound immediately before install and is
closed by the later sections of this record.

## Recorded authority integration

The four-record authority branch completed at exact head
`266a5f586f939c044fe3fe8a40243bbfd9a8a7b7`, with parent `D0` and tree
`f43548540aa203013164164648549795c49dd44b`. Same-repository PR #130 targeted
exact `develop@D0` from that exact head and changed only the four authority
records. Comments, hosted reviews, review requests, and discussion threads were
empty; the separately executed independent repository review was the required
behavioral review gate.

CI run `32060878742` passed all three exact-head jobs:

- `CI / Python 3.11`, job `95481656534`;
- `CI / Python 3.13`, job `95481656332`;
- `CI / Build distributions`, job `95482429069`.

Ordinary squash integration produced final release head
`D = 74f80d6a32b4b9ae4556e1af4cd06b628d9474e6`, whose sole parent is exact
`D0` and whose tree is
`f43548540aa203013164164648549795c49dd44b`, exactly the reviewed authority
head tree. No source branch was deleted.

## Recorded release candidate and independent GO

Fresh release audit bound:

- unchanged release base
  `M = 7f7ddfe245e1e5b57946eb6ac10dcc01358559fc`;
- exact release head
  `D = 74f80d6a32b4b9ae4556e1af4cd06b628d9474e6`;
- exact merge base
  `B = e101690bc351d92cc6b24a46cb5bc30f00bd6df0`;
- `tree(M) == tree(B) == 98cb3e56af4d867987d4e23f279f68fcf912e666`;
- empty `B..M` content diff and divergence two main-only / two develop-only
  commits; and
- prospective merge
  `P = c02f5d7ec88821450517a79ffa2a117b8710114f`, with ordered parents `[M,D]`
  and exact tree `f43548540aa203013164164648549795c49dd44b`, equal to `tree(D)`.

Same-repository PR #131 had exact base branch `main@M`, exact head branch
`develop@D`, and the complete expected 41-path release diff: the 37-path
forward-only global-home implementation set plus the four authority records.
It was mergeable with empty hosted comments, reviews, review requests, and
threads. Independent release review passed that exact candidate, complete
scope, prospective topology, merge-commit-only method, and exclusion boundary
after all seven required jobs succeeded:

- CI run `32061770133`:
  - `CI / Python 3.11`, job `95484432051`;
  - `CI / Python 3.13`, job `95484431939`;
  - `CI / Build distributions`, job `95486769380`;
- Release readiness run `32061770074`:
  - `Release readiness / Policy`, job `95484431650`;
  - `Release readiness / Python 3.11`, job `95484431586`;
  - `Release readiness / Python 3.13`, job `95484431674`;
  - `Release readiness / Distribution`, job `95487031177`.

The preceding exact-`D` push CI run `32061635962` also passed Python 3.11 job
`95484012316`, Python 3.13 job `95484012274`, and Build distributions job
`95484960515`.

## Recorded main merge and post-main verification

PR #131 integrated once with the merge-commit method as exact result
`R = 78ffbf796d4fbe1bee8de0544fa018c8da512698`. `R` has exact ordered parents
`[M,D]` and exact tree `f43548540aa203013164164648549795c49dd44b`, equal
to `tree(D)` and `tree(P)`. Fresh readback proved `origin/main == R`,
`origin/develop == D`, and an empty `D..R` content diff. No branch was deleted.

Exact-main CI run `32062953903` passed:

- `CI / Python 3.11`, job `95488225766`;
- `CI / Python 3.13`, job `95488225821`;
- `CI / Build distributions`, job `95488813281`.

Exact-main Release run `32062953919` passed its sole read-only
`Release / Publication paused` job `95488221893`.

Fresh post-merge hosted readback found the owner-selected absent branch
protection unchanged, zero repository rulesets, the same six tags at the same
commits, and the same five non-draft/non-prerelease GitHub Releases. Only the
authorized `main` ref changed. Publication remained paused.

## Exact-R build and reviewed install bundle

A clean detached worktree at exact `R` in retained owner-only bundle
`/private/tmp/buoy-install-preflight.IKZD3P` passed source validation, the
154-package offline lock, compilation of 90 source files, distribution
validation, and isolated-home clean-wheel smoke. Two deterministic builds
produced byte-equal artifacts:

- wheel `buoy_search-0.5.2.dev36+g78ffbf796-py3-none-any.whl`, 647,944 bytes,
  SHA-256
  `aca9bef7b146ae25a0557d9174c875afac0efdc936f5889171b871629c6b5ba0`;
- sdist SHA-256
  `c89ddcdbb1c5f6fb384314de00a11efadfa3f3e8ec237db6b6515ce767fd29f2`.

The exact 103 non-root runtime pins had SHA-256
`41acb9249e44d8056a9cdebc2eb5cc3c29687b6c3f5e9912c37ef6bc81fddce9`.
The generated requirements file had SHA-256
`b77b91dfaf463a3fbfda795b6709eadb75893782938e222675be69d1ca425ee3`.
Pre-install preparation used package-network reads to stage exactly 103
regular, one-per-pin dependency wheels, totaling 360,269,621 bytes, in the
owner-only mode-`0700` temporary bundle. The URL manifest SHA-256 was
`51c87189869376ab37ffa1b4ab70a65b15d2e29ab81c669661d649d19c385028`,
the realized wheelhouse manifest SHA-256 was
`3204f7fca96184a4b0053183a663517f758ec625c2548c965501f741bebe9b4d`,
and the checksum-list file SHA-256 was
`e7985887706e57a809e45bfe224ee6b7ece6c46c03bdcd65c5474e428c6a1c97`.
Every staged wheel passed its prebound checksum, ZIP integrity, metadata, and
pin check. These unauthenticated public package-file downloads are counted as
network reads; they were not package publication, provider application access,
credential access, or a live Buoy content operation.

Important caveat: `uv 0.11.7` ignores hashes embedded in a file passed through
`--with-requirements`; a negative control proved that an invalid embedded hash
did not stop installation. Therefore the reviewed requirements-file digest and
embedded hashes bound review evidence but were not install-time hash
enforcement. The compensating install boundary was the fully prevalidated
owner-only wheelhouse plus `--offline --no-index --no-cache --no-build`, with
no symlinks or extra wheels. Two separate isolated offline installs produced
the exact expected 104-distribution environment. Two independent reviewers
then issued `INSTALL-GO` for the unchanged artifact set and literal one-shot
command.

## One-shot replacement and installed result

The literal approved command had SHA-256
`a7160a5231985e542416b92bac77ad8dbccc468f08fb666124cec4809de13d39`.
It was invoked exactly once. The invocation exited zero and reported 104
packages resolved, prepared, and installed plus one installed executable,
`buoy`; its PATH warning was benign. There was no retry, rollback, uninstall,
fallback, or second invocation.

Post-install readback proved:

- `/Users/crlough/.local/bin/buoy` remains linked to
  `/Users/crlough/.local/share/uv/tools/buoy-search/bin/buoy`;
- wrapper SHA-256 remains
  `916b07b93c743dad13dbef74e47f77a8f98c36cc81012262c9f1074574486a22`;
- the runtime remains CPython `3.13.0` and the version is
  `0.5.2.dev36+g78ffbf796`;
- installed `direct_url.json` SHA-256 is
  `f3798312a88d94e2dd90732d5a72392101553c48370caeb09b9890ac0b964b1b`
  and names the retained exact-R wheel;
- actual `uv-receipt.toml` SHA-256 is
  `1f1d75eba59cbacd9d9fb942ba4ffad6e4574a219259bc7fed04384f5a7e71cc`
  and semantically binds the candidate, 103 pins, Python runtime, global
  entrypoint, local wheelhouse, no-index/keyring-disabled/copy/no-sources/
  no-build configuration;
- candidate `RECORD` SHA-256 is
  `2315e0996473e7f097927d6e3b43c4cb3f692cb069b23e2b71987b60cb674291`;
- the installed set has 104 distributions, 27,840 correctly hashed `RECORD`
  rows, 104 unhashed `RECORD` self-rows, zero bad rows, and a successful
  dependency check;
- the 104-line freeze SHA-256 is
  `de2c8512dfbfcbb07cc19a3dcd259dff43c7bd71ffd0e545bd81b40e0297d146`,
  the 103-pin SHA-256 remains
  `41acb9249e44d8056a9cdebc2eb5cc3c29687b6c3f5e9912c37ef6bc81fddce9`,
  and the normalized distribution-set SHA-256 is
  `9d11312f8b2602b976f82be3eac41a7bfc5fdb83c38b9d3a8c0a05760f1da889`;
- all 65 installed `buoy_search` files are byte-equal to the reviewed wheel;
- critical installed source SHA-256 values are CLI
  `92c49e943ed5918df7fe65294ff89717e2654a8e9d76317979b63198f1b98ee9`,
  `applied_state.py`
  `0b15d95160e6864f306a8ba163b400bd5bbbe62b6ceebb58f431b710ed47e3bd`,
  `config.py`
  `b33407002f60c6ca3429e05043f2c1451902112bf793ce2ae2ed0ae9e4da5620`,
  `local_paths.py`
  `29080764adddb916e5bd0bd18cdf6d031f90fe3b6c5407fd54ae1691d0298135`,
  and `plan_artifacts.py`
  `fc100b825fe59994b368ba13ec307c98c621f8993b3c85e9b44312314d4e6192`;
- version, top-level help, and module help passed; pure isolated-home tests from
  an unrelated working directory resolved implicit home/state/site-crawl paths
  to `$HOME/.buoy`, `$HOME/.buoy/state/<source>/<namespace>/state.duckdb`, and
  `$HOME/.buoy/artifacts/site-crawls` without creating the real application
  home;
- the other seven uv-tool directories, all eight total tool-directory names,
  the 22 non-Buoy launcher links, and all 23 total link targets were unchanged;
  and
- the real `/Users/crlough/.buoy` path remained absent.

The active routing CLI receipt intentionally remained unchanged. No `plan`,
`apply`, or `retrieve` command ran during replacement or verification.

## External effects, exclusions, and closure boundary

The governed execution caused the two authorized PR merges, the explicitly
counted dependency-package network reads into a bounded temporary wheelhouse,
and exactly one global `buoy-search` uv-tool replacement. It made zero live
provider requests or writes and performed no catalog migration, indexed-content
mutation, model inference, credential access/change, deployment, package
publication, tag or GitHub Release operation, protection/ruleset mutation,
direct/force push, old-asset scan/move/copy/backfill/delete, real `~/.buoy`
state/plan creation, other-tool mutation, or branch deletion. Publication
remained paused throughout.

This Phase-4 closure changes only its five owned logical records and may
integrate through one ordinary task PR to `develop`. Exact `main@R` necessarily
retains the earlier `accepted`, `active`, and `provisional` headers as
historical bytes. Both one-time authorities were already consumed by the main
merge and invocation boundaries, so neither those historical bytes nor this
closure grants another merge, install, retry, rollback, or publication action.
