Status: superseded before use
Created: 2026-08-19
Updated: 2026-08-19
Decision: .10x/decisions/v0-6-0-one-time-manual-github-release.md

# Buoy v0.6.0 One-Time GitHub Release

## Supersession

This specification was never executed. It is retained as historical context;
`.10x/specs/annotated-tag-triggered-github-release.md` governs the reusable
implementation and the first v0.6.0 invocation.

## Purpose and constants

This specification is the executable procedure for the single v0.6.0
exception. Define:

- `D0 = 06708ce39e9b5e8c15ce6204c2af4e9c73334ade`, the preparation base on
  `develop`;
- `M0 = caed68fdce3ef91e41c11f5d586a6166837d0392`, the frozen pre-release
  `main` baseline;
- `D1`, the later reviewed squash integration of this ticket into exact `D0`;
  and
- `M1`, the later reviewed release merge commit with ordered parents
  `[M0, D1]` and tree exactly equal to `tree(D1)`.

`M1` is unknown until the reviewed develop-to-main merge. It is the only
permitted v0.6.0 tag target. If either branch advances outside this topology,
stop and update plus independently review the bindings.

## A. Prepare and integrate release state

The task branch may change only the v0.6.0 decision/spec/ticket/evidence and
independent review, `CHANGELOG.md`, the published-wheel URL in `README.md`,
the bounded exception in the active pause decision, `SECURITY.md`,
`docs/releasing.md`, and the focused release validator and tests. It must not
change application behavior, package metadata strategy, dependencies, lock,
or workflows.

Preparation must:

1. move the current Unreleased notes unchanged under
   `## [0.6.0] - pending`, retain an empty Unreleased section, and add the
   v0.5.1-to-v0.6.0 comparison link;
2. point the end-user GitHub-wheel installation example to the exact v0.6.0
   asset name;
3. add exact `SECURITY.md` row `| 0.6.0 | Yes |` above the retained v0.5.1
   supported row without weakening the older-version warning, so the tagged
   source archive truthfully carries its released support policy;
4. document this one-time manual path while keeping automatic publication and
   all workflow permissions read-only; and
5. make source validation accept exactly the staged v0.6.0 changelog and
   security-policy state while retaining dynamic Hatch-VCS metadata and
   published history through v0.5.1.

Locked Python 3.11 and 3.13 full suites, source/ranking/C6 validators, lock
check, diagnostic distribution validation, clean-wheel CLI/tokenizer smoke,
and diff/link hygiene must pass. An independent review must bind exact paths,
blobs, validation, decision/spec coherence, and zero unapproved effects.

Before integration, freeze one private release-build bundle containing exact
`uv 0.11.7`, one exact CPython 3.13 patch version, direct build requirements
`hatchling==1.31.0` and `hatch-vcs==0.5.0`, and every transitive build wheel.
Record the complete normalized package/version inventory and every wheel name,
size, and SHA-256. Install a dedicated no-build-isolation environment only
from that verified bundle. Two independent clean rehearsal builds of the exact
reviewed task tree, with the same fixed release inputs and no network, must
produce byte-identical wheel and sdist pairs. These rehearsals prove the
procedure and do not replace the later one-shot exact-`M1` release build.

Publish only the reviewed task branch. Require exact-head `CI / Python 3.11`,
`CI / Python 3.13`, and `CI / Build distributions`, empty unresolved review
state, and a separate integration role. Squash-merge only into exact `D0` so
`D1` has sole parent `D0` and the reviewed tree. Retain the task branch.

## B. Promote the exact release tree

Open one same-repository, non-draft `develop`-to-`main` PR with exact head
`D1` and exact base `M0`. Require these exact-head readiness contexts:

- `Release readiness / Policy`;
- `Release readiness / Python 3.11`;
- `Release readiness / Python 3.13`; and
- `Release readiness / Distribution`.

A separate release role must re-read the PR identity, empty discussion state,
head/base, prospective topology/tree, and four passing checks, then use a merge
commit only. Squash, rebase, direct branch push, admin bypass, or a different
head/base is a stop. Verify `M1` has ordered parents `[M0, D1]`, exact tree
`tree(D1)`, and expected release subject. Wait for exact-`M1` ordinary CI
(Python 3.11, Python 3.13, Build distributions) and the read-only
`Release / Publication paused` job to pass. No tag or Release may yet exist.
The release PR title and merge subject must be exactly
`Release Buoy v0.6.0 (#<release-pr-number>)`.

The readiness `Distribution` job is a diagnostic VCS-development-version
build from the prospective merge. It proves package boundaries and smoke
behavior only; it does not build or prove stable version 0.6.0. Only the later
one-shot exact-`M1` build below is v0.6.0 artifact authority.

## C. Build and freeze the publication candidate

From a fresh clean detached checkout of exact `M1`, use the exact frozen
CPython patch, `uv 0.11.7`, verified build bundle, dedicated
no-build-isolation environment, and one fresh output directory. Network access
must be disabled for the build. Run the release build once with:

- exact `SETUPTOOLS_SCM_PRETEND_VERSION=0.6.0`;
- `SOURCE_DATE_EPOCH` equal to the exact `M1` committer timestamp;
- `PYTHONHASHSEED=0`, `TZ=UTC`, and `LC_ALL=C`; and
- the hash-verified complete build environment frozen before integration.

The sole accepted output is exactly the named wheel and sdist. Validate both
with the repository distribution validator; verify core metadata and generated
version `0.6.0`, sole `buoy` entry point, package/data/tokenizer inventory, and
absence of internal records or retired components. Build a complete
hash-manifested runtime wheelhouse from the exact locked dependency solution,
then disable network access and clean-install the candidate wheel into a fresh
isolated Python 3.13 environment from that wheelhouse. Use a fresh `HOME`,
working directory, and package/model cache roots; remove provider/cloud
credentials; set `BUOY_TELEMETRY=off`, `OTEL_SDK_DISABLED=true`,
`HF_HUB_OFFLINE=1`, and `TRANSFORMERS_OFFLINE=1`. Pass `buoy --version`, both
top-level help paths, `buoy telemetry --help`, read-only
`buoy telemetry status --json`, representative imports, and exact bundled
tokenizer smoke. The isolated home must remain empty and no provider, model,
or telemetry writer call may occur. Record each asset's byte size and SHA-256.
No rebuild may silently replace these files; a failed or changed candidate
returns to review before any hosted write.

## D. Independent prepublication GO

A read-only GitHub notes preview must first generate the exact candidate range
from previous tag `v0.5.1` through target `v0.6.0` at exact `M1`. Review the
complete title and body for accuracy and for accidental credentials, private
paths, internal records, or other sensitive egress, then freeze the exact body
bytes and SHA-256. Draft creation must supply that reviewed body; it may not
regenerate or silently change notes during the write.

A reviewer other than the builder/operator must verify and explicitly bind:

- decision, specification, and still-active ticket;
- `D0`, `M0`, `D1`, `M1`, ordered parents, tree equality, and clean checkout;
- exact-head task, readiness, and exact-main CI identities and conclusions;
- exact frozen Python/uv/build/runtime bundle inventories and hashes, two
  byte-identical rehearsal pairs, and the one exact-`M1` candidate pair;
- exact two candidate names, sizes, SHA-256 values, validation, and offline
  clean installation;
- absence of local `refs/tags/v0.6.0`, absence of the authoritative remote tag
  ref, and a complete authenticated paginated Releases listing (including
  drafts) containing no `tag_name=v0.6.0`; a published-only get-by-tag 404 is
  insufficient proof of draft absence;
- the exact reviewed release-notes title/body bytes and digest;
- exact proposed annotated-tag target/message, one draft Release creation
  using existing-tag verification and exact `target_commitish=M1`, containing
  both frozen assets, and one later numeric-ID publish PATCH; and
- no conflicting process, credential ambiguity, or unapproved effect.

GO is single-use and bound to those facts. Drift or uncertainty is STOP.

## E. Publish once

Immediately recheck all three absence surfaces from prepublication GO. Then
create one local annotated `v0.6.0` tag object for exact `M1` with message
`Buoy v0.6.0`; no local tag deletion or recreation is authorized. Verify its
object type, exact tag name/message, object SHA, and peel before the sole push
of `refs/tags/v0.6.0`. Beginning that push consumes and makes the release
procedure non-restartable. Require zero exit and authoritative remote readback
showing the remote ref points to the identical local tag-object SHA, whose type
is `tag`, name/message are exact, and commit peel is `M1`. That exact tag-only
state is the sole permitted transient; a pause, uncertainty, or drift before
draft Release creation is STOP and requires new recovery authority.

Then begin exactly one draft GitHub Release creation with title
`Buoy v0.6.0`, the exact reviewed notes body, existing-tag verification
semantics, exact `target_commitish=M1`, `draft=true`, `prerelease=false`, and
both frozen assets supplied together in that invocation. It must refuse to
create an implicit tag. Beginning it consumes Release-create authority. A
nonzero or uncertain result, incomplete asset set, or any mismatch is STOP. No
second upload, creation, replacement, clobber, deletion, or repair is allowed.

## F. Verify the frozen exact draft and publish once

A reviewer other than the release operator must use the authenticated full
Releases list to find exactly one `tag_name=v0.6.0` draft, then read it through
its numeric Release ID. Bind that ID, exact tag/title/body bytes and SHA-256,
`target_commitish=M1`, `draft=true`, `prerelease=false`, and exactly two assets.
Each asset must have a unique numeric ID, expected name, `state=uploaded`, exact
size, and API `sha256:` digest matching the frozen candidate. Download each
through its authenticated numeric asset endpoint and independently require its
bytes and SHA-256 to match. Repeat the sensitive-egress scan over the exact
draft body. No verification may edit the draft, its body, or an asset.

Only an explicit single-use draft-publication GO over that frozen exact state
permits publication. Immediately before mutation, re-read the numeric Release,
both asset records, downloaded hashes, and remote tag object and require exact
equality with GO. Then make one numeric-ID PATCH whose entire request body is
`draft=false` and `make_latest=true`. Beginning it consumes publish authority.
Require zero exit, with no retry. No title, tag, target, body, prerelease flag,
asset, or other operator-controlled field may be supplied or changed; only
GitHub's publication timestamps, URL/state, and other platform-computed
publication fields may appear as consequences.

## G. Verify published state and close

Read back the remote tag object and numeric Release independently. Require the
exact annotated object SHA/peel and the same Release ID,
title/tag/target/body/prerelease flag, and asset IDs/names/uploaded
states/sizes/API digests as the frozen draft. Require `draft=false` and the
authenticated latest-Release endpoint to return the same numeric ID. Only the
authorized draft-to-published/latest state and platform-computed publication
fields may differ. Download both hosted assets by numeric ID into a second
fresh directory, verify byte sizes and SHA-256 equal the frozen candidate,
rerun distribution validation, and repeat the exact offline, credential-free,
fresh-home/cache install and version/help/telemetry-status/import/tokenizer
smoke from section C. The isolated home must remain empty.

Record all identities, results, and effects in the evidence.

## H. Close through develop and main

After successful verification, freeze then-current develop and main, expected
to be exact `D1` and `M1`. A separate closure task branch may change only the
v0.6.0 closure records, `CHANGELOG.md`, `SECURITY.md`, `docs/releasing.md`, and
the focused release validator/tests. It must date v0.6.0 from GitHub's
authoritative publication time, retain and validate `| 0.6.0 | Yes |`, require
published history through v0.6.0 with no staged target, move the active ticket
to its terminal successful location, mark evidence recorded, mark the
decision/specification superseded and authority consumed, and add an
independent final closure review. That unused manual path never reached this
step; the actual stopped reusable attempt is preserved at
`.10x/tickets/cancelled/2026-08-19-ship-buoy-v0-6-0.md`.

After independent review and exact-head ordinary CI, a separate integration
role squash-merges that closure into frozen develop as `D2`, with the frozen
develop commit as sole parent and reviewed tree. Then one same-repository
closure PR promotes exact `D2` to frozen main, expected `M1`, after the four
release-readiness contexts pass. A separate release role merge-commits it as
`M2`; under the expected bindings, `parents(M2)=[M1,D2]` and
`tree(M2)=tree(D2)`. Exact-`M2` ordinary CI and the read-only
`Release / Publication paused` job must pass. The closure performs no tag,
Release, asset, or registry write and does not imply another version.

If publication stops in partial state, the same separately reviewed branch/
PR slots must preserve hosted tag/draft/asset state exactly while carrying a
truthful failure disposition through develop and main. Restore the README
install URL to v0.5.1; move the v0.6.0 notes back under Unreleased and remove
its staged comparison link; remove the v0.6.0 supported row so v0.5.1 is again
the newest published supported release; and make docs/validator report
published history through v0.5.1 with no staged target. Record the exact
partial state, consume/supersede the decision, finalize the evidence and
ticket with a non-success disposition, and obtain an independent final review.
Do not claim v0.6.0 published or mutate any hosted state. Any hosted repair
requires a new reviewed decision.

## Permanent stops

Any pre-existing, partial, mismatched, uncertain, or changed target state is a
permanent stop under this decision, except the two exact planned transients:
the reviewed tag-only advance to draft creation and the independently verified
frozen exact draft advance to its publish-only edit. Preserve every other state
exactly and seek a new reviewed recovery decision. Never infer permission to
repair from a correct local build or from owner authorization to make the
original release.
