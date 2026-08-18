Status: pass
Created: 2026-08-17
Updated: 2026-08-17
Target: PR #131, merge result 78ffbf796d4fbe1bee8de0544fa018c8da512698, and installed buoy-search 0.5.2.dev36+g78ffbf796
Ticket: .10x/tickets/done/2026-08-17-promote-user-global-home-defaults-and-replace-tool-once.md
Evidence: .10x/evidence/2026-08-17-user-global-home-main-promotion-and-tool-replacement.md
Decision: .10x/decisions/one-time-user-global-home-main-promotion-and-tool-replacement.md
Authority-Review: .10x/reviews/2026-08-17-user-global-home-main-promotion-authority-review.md
Verdict: pass

# User-Global-Home Main Promotion and Tool Replacement Review

## Independent release readback

Independent release audit bound exact same-repository PR #131 to base
`M = 7f7ddfe245e1e5b57946eb6ac10dcc01358559fc` and head
`D = 74f80d6a32b4b9ae4556e1af4cd06b628d9474e6`. Merge base was exact
`B = e101690bc351d92cc6b24a46cb5bc30f00bd6df0`;
`tree(M) == tree(B)`, the `B..M` content diff was empty, and prospective merge
`P = c02f5d7ec88821450517a79ffa2a117b8710114f` had ordered parents `[M,D]`
and exact `tree(D) = f43548540aa203013164164648549795c49dd44b`.

The reviewed PR had the complete expected 41-path diff and empty hosted
discussion state. CI run `32061770133` passed jobs `95484432051`,
`95484431939`, and `95486769380`. Release readiness run `32061770074` passed
jobs `95484431650`, `95484431586`, `95484431674`, and `95487031177`.
Independent review found no blocker in refs, topology, path scope, check
identities, discussion state, mergeability, merge-commit-only method, or
exclusion boundary.

PR #131 merged once with the required method as exact
`R = 78ffbf796d4fbe1bee8de0544fa018c8da512698`. Fresh readback proved ordered
parents `[M,D]`, exact `tree(R) == tree(D)`, `origin/main == R`,
`origin/develop == D`, and an empty `D..R` content diff. Exact-main CI run
`32062953903` passed jobs `95488225766`, `95488225821`, and `95488813281`.
Release run `32062953919` passed read-only Publication paused job
`95488221893`. Protection remained absent by owner choice, ruleset count stayed
zero, and the six tags and five GitHub Releases were unchanged. Publication
remained paused.

## Independent install review and caveat

Two independent install reviews issued `INSTALL-GO` only after binding the
clean exact-`R` source/tree, Python `3.13.0`, the deterministic 647,944-byte
wheel SHA-256
`aca9bef7b146ae25a0557d9174c875afac0efdc936f5889171b871629c6b5ba0`,
the 103 exact dependency pins, the owner-only prevalidated wheelhouse, the
pre-install global baseline, the isolated-home smoke, and literal command
SHA-256
`a7160a5231985e542416b92bac77ad8dbccc468f08fb666124cec4809de13d39`.

The review explicitly rejects any claim that `uv 0.11.7` enforced hashes
embedded in `--with-requirements`: a negative control proved it ignored them.
The safe boundary was instead full pre-invocation checksum/ZIP/metadata/pin
validation of exactly 103 regular one-per-pin wheels in a mode-`0700` bundle,
followed by the exact `--offline --no-index --no-cache --no-build` invocation.
The package-network reads used to stage those 103 dependency wheels are
explicitly accounted in shared evidence and are not misreported as zero
network activity.

The approved command was invoked exactly once, exited zero, installed 104
packages and the `buoy` executable, and required no retry, rollback, uninstall,
or fallback. Beginning that invocation consumed installation authority.

## Independent post-install readback

Post-install audits independently confirmed:

- global version `0.5.2.dev36+g78ffbf796`, unchanged launcher target and
  wrapper SHA-256
  `916b07b93c743dad13dbef74e47f77a8f98c36cc81012262c9f1074574486a22`;
- exact-wheel `direct_url.json` SHA-256
  `f3798312a88d94e2dd90732d5a72392101553c48370caeb09b9890ac0b964b1b`;
- actual `uv-receipt.toml` SHA-256
  `1f1d75eba59cbacd9d9fb942ba4ffad6e4574a219259bc7fed04384f5a7e71cc`,
  whose semantics bind the candidate, 103 pins, runtime, entrypoint,
  wheelhouse, and reviewed install options;
- 104 distributions, a successful dependency check, 27,840 valid hashed
  `RECORD` rows, 104 unhashed `RECORD` self-rows, and zero bad rows;
- all 65 installed `buoy_search` files byte-equal to the reviewed wheel and
  the exact critical source hashes recorded in shared evidence, including the
  unchanged active routing CLI receipt;
- successful version/help/module-help and pure unrelated-working-directory
  default-path checks for `$HOME/.buoy` state and site-crawl assets;
- all other uv-tool directories and launcher links unchanged; and
- the real `/Users/crlough/.buoy` path still absent.

The verification did not run `buoy plan`, `buoy apply`, or `buoy retrieve` and
made no provider, model, credential, catalog, indexed-content, migration,
publication, deployment, tag, Release, protection, ruleset, old-asset, or
other-tool mutation.

## Final verdict

PASS for durable Phase-4 closure through one ordinary five-logical-record task
and later squash integration into `develop`. Every release and install
acceptance criterion passed. The one-time decision is superseded and both its
main-merge and installation authorities are consumed. This verdict grants no
retry, rollback, uninstall, second merge, second replacement, recurring
procedure, publication, provider operation, or other excluded action.
