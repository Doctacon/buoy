Status: superseded before use
Created: 2026-08-19
Updated: 2026-08-19
Exception-To: .10x/decisions/release-publication-is-paused.md
Specification: .10x/specs/buoy-v0-6-0-one-time-github-release.md

# v0.6.0 One-Time Manual GitHub Release

## Supersession

No tag or Release was created under this draft procedure. The owner rejected
its per-version ceremony and explicitly authorized the reusable workflow in
`.10x/decisions/annotated-tag-triggered-github-releases.md`. The detailed
procedure below is retained only as audit history and grants no authority.

## Context and owner authority

Automatic release publication is paused. Buoy v0.5.1 consumed its own
one-time exception and grants no later publication authority. After merging the
current reviewed `develop` tree to `main`, the repository owner explicitly
directed execution of a new release and selected the recommended v0.6.0 minor
version. This decision records that instruction as a narrow, single-use
exception rather than reactivating the retired automatic publisher.

## Frozen pre-release baselines

The preparation branch starts from exact
`develop@06708ce39e9b5e8c15ce6204c2af4e9c73334ade`. Current
`main@caed68fdce3ef91e41c11f5d586a6166837d0392` is the pre-release main
baseline and has that develop commit as its second parent. Neither baseline is
the release commit.

The release source must be a later, separately reviewed merge commit whose
ordered parents are exact pre-release main followed by the exact
governance-bearing develop integration result, and whose tree equals that
develop result. Annotated tag `v0.6.0` must peel to that later merge commit.
The tag may not point to either baseline, a task commit, a squash commit on
develop, or an unreviewed main commit.

## Decision

Authorize one manual GitHub-only Buoy v0.6.0 publication after every gate in
`.10x/specs/buoy-v0-6-0-one-time-github-release.md` passes. The publication
creates exactly:

- one annotated tag named `v0.6.0`, with message `Buoy v0.6.0`, peeling to the
  exact reviewed release merge commit; and
- one GitHub Release object titled `Buoy v0.6.0`, identified by that tag,
  created as a draft with both assets together and made non-draft only after
  independent frozen-draft verification, containing exactly
  `buoy_search-0.6.0-py3-none-any.whl` and
  `buoy_search-0.6.0.tar.gz`.

Reaching that exact release source authorizes one ordinary reviewed task PR
with squash integration into exact develop baseline and one same-repository
release PR merge-committed from the resulting exact `develop` head into exact
pre-release `main`. After successful publication, one separately reviewed
closure task may be squash-integrated into its frozen then-current `develop`,
followed by one reviewed closure PR merge commit from that exact develop head
to its frozen then-current `main`. These four are the only protected-branch
merges authorized by this exception; they must use the identities, CI gates,
independent roles, and topology in the specification. If publication stops in
partial state, the same closure slots authorize a truthful failure disposition
that records and preserves hosted state while reverting public release-staging
surfaces to v0.5.1/Unreleased truth. It does not authorize hosted repair.

The exact-main artifacts are built once with exact version override `0.6.0`,
validated, sized, and SHA-256 hashed before either hosted write. A separate
reviewer must issue an explicit prepublication GO binding the exact main
commit/topology/tree, exact CI runs, artifact names/sizes/digests, hosted
absence, and proposed one-shot operations. Passing tests or owner direction
alone does not substitute for that gate.

The exact draft Release ID, tag/title/body, target identity, flags, and asset
IDs/names/states/sizes/digests must be independently read back. Both draft
assets must be downloaded by numeric asset ID and hash-verified before a
separate explicit draft-publication GO. Exactly one numeric-ID edit may then
set `draft=false` and `make_latest=true`; no asset or other operator-controlled
field may change. After publication, both assets
must be downloaded again into a fresh isolated environment, match the reviewed
names, sizes, and digests, pass distribution validation, and the wheel must
pass clean installation plus version, CLI, module-help, import, and tokenizer
smoke checks. The real Buoy home and global tool installation are outside this
release verification.

## One-shot and fail-closed boundary

The target tag ref and GitHub Release must both be absent immediately before
GO. Beginning the sole tag-ref push consumes tag-write authority; there is no
retry under this decision. Draft Release creation may begin only after readback
proves the pushed ref is an annotated tag peeling to the exact release commit.
Beginning the sole draft-Release-creation invocation consumes Release-create
authority; both assets must be supplied by that one invocation. It may not be
followed by an asset upload, edit, replacement, or repair.

Only a zero-exit creation followed by exact frozen draft readback and
downloaded-asset verification can reach the independent draft-publication GO.
Beginning the sole publish edit consumes publish authority; its request may
contain only `draft=false` and `make_latest=true` on the same numeric Release
ID. It cannot be retried, and no later Release or asset edit is authorized.

Any pre-existing target state, nonzero or uncertain write result, lightweight
or wrong-target tag, Release-only state, wrong identity, missing or extra
asset, digest mismatch, or other partial state stops execution. The planned
exceptions are only (1) the exact zero-exit tag-only state while advancing
under the still-current prepublication GO to draft creation and (2) the exact
zero-exit, complete, independently verified draft while advancing under its
single-use draft-publication GO to the publish-only edit. If execution pauses,
loses certainty, or observes either state outside its reviewed sequence, stop.
Do not move, overwrite, replace, delete, recreate, upload a missing asset,
edit a draft field or asset, or retry. Record the observed state and require a
new reviewed recovery decision.

## Closure and expiration

A separate reviewed closure must record the release/tag identities, exact
source and CI, local and downloaded artifact hashes/sizes, clean-install
results, frozen draft and publication transition, and all external effects.
It must date the staged changelog from the authoritative GitHub publication
time, retain and verify the v0.6.0 supported row in `SECURITY.md`, advance
read-only validation through v0.6.0, move the ticket to `tickets/done`, mark
the evidence recorded and this decision superseded/consumed, and add an
independent final closure review. Automatic publication remains paused after
closure.

If publication stops before the final public Release is verified, the closure
must instead preserve every hosted tag/draft/asset byte and field exactly,
record the partial state and consumed authority, and restore source truth:
README installs v0.5.1, v0.6.0 notes return to Unreleased with no staged link,
`SECURITY.md` again lists v0.5.1 as the newest supported published release,
and docs/validator report published history through v0.5.1 with no staged
target. The independently reviewed D2/M2 disposition may perform only those
source/record corrections. Any hosted mutation requires a new decision.

If any bound branch, commit, tree, artifact, review, or hosted-state premise
changes before its dependent action, stop and amend plus independently review
the authority before continuing. Unused authority expires at closure; consumed
authority cannot be renewed by a rerun.

## Exclusions

No PyPI or other package registry publication, reusable release automation,
workflow write permission, artifact attestation, branch-protection/ruleset
change, direct or force push to `main` or `develop`, product/provider/model
operation, Turbopuffer or namespace/catalog/content mutation, user-home
inspection, global tool replacement, credential rotation, asset repair,
release deletion, or unrelated product work is authorized. The single
annotated tag-ref push is the only direct ref creation permitted.
