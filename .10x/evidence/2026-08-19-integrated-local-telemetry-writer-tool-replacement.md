Status: provisional
Created: 2026-08-19
Updated: 2026-08-19
Ticket: .10x/tickets/2026-08-19-install-integrated-local-telemetry-writer-once.md
Decision: .10x/decisions/one-time-integrated-local-telemetry-writer-tool-replacement.md
Authority-Review: .10x/reviews/2026-08-19-integrated-local-telemetry-writer-install-authority-review.md

# Integrated Local Telemetry Writer Tool-Replacement Evidence

## Owner authority and integrated prerequisite

The owner explicitly directed the agent to proceed through integration and
installation of the approved private local telemetry writer. This is not
interpreted as authority for `main`, release, publication, provider, retrieval,
model, credential, namespace/catalog/content, remote telemetry, real-home, or
unrelated tool effects.

PR #134 integrated the repaired implementation through the ordinary flow:

- exact base `3787e0eabd2720732fb5c68ca168f926342ae454`;
- exact final head `fe40aadf88e6fbe8ad702225a111d2f787291689`;
- head tree `51c756d8bed8f7eee397fa5381feeb3146255180`;
- successful exact-head CI run `32305182775` with Python 3.11 job
  `96236296365`, Python 3.13 job `96236296821`, and Build distributions job
  `96236848069`;
- empty hosted comments, reviews, review requests, and discussion threads;
- squash result `D0 = e9c906ca99caa7b85d6e31e65e10221161013686`;
- `parent(D0) = 3787e0eabd2720732fb5c68ca168f926342ae454`;
- `tree(D0) = 51c756d8bed8f7eee397fa5381feeb3146255180`,
  exactly the reviewed head tree.

The prior one-time user-global-home main-promotion and tool-replacement
decision is superseded and consumed. No part of this task reuses it.

## Exact installed baseline

Fresh read-only preflight bound the existing user-global uv-managed
`buoy-search` baseline at version `0.5.2.dev36+g78ffbf796` on Python `3.13`
with 104 compatible distributions, sole `buoy_search.cli:main` entry point,
and all three OpenTelemetry distributions absent. The executable,
package-manager provenance, installed-source identity, dependency set, and
other-tool/executable inventories were internally coherent and matched the
expected prior installation.

The complete local provenance and inventory snapshot remains owner-private
outside the repository. It is pre-install evidence, not a byte-for-byte
rollback target; installing the same reviewed wheel from the rollback bundle
must record truthful new provenance. Preflight did not inspect or stat the real
`~/.buoy` path.

## Exact-D0 candidate and offline forward bundle

A clean detached exact-`D0` source and a second independent exact-`D0` source
produced byte-identical artifacts with dynamic version
`0.5.2.dev36+ge9c906ca9`:

- 697,998-byte wheel
  `buoy_search-0.5.2.dev36+ge9c906ca9-py3-none-any.whl`, SHA-256
  `9f3474d636407c2d0908bbb791ef60b43017824a76a512337caa29079f47b8d3`;
- 1,223,146-byte source distribution
  `buoy_search-0.5.2.dev36+ge9c906ca9.tar.gz`, SHA-256
  `51b3d571abc0fb9393689044eba5f19bef2a785b66f6de2cd12f66a27755a18b`.

The candidate runtime has 106 exact non-root pins at SHA-256
`2371d23c135a5495f5a8a13b779fcd339e7ea03be7dbf09df047068a80b6b43e`;
its generated requirements file has SHA-256
`788f07b6dc126da8e0c26c58b0cf5539c400961d0b8530f66464512c2e33027f`.
The 106-wheel, 360,671,505-byte candidate wheelhouse has manifest SHA-256
`7f5a20e472e5341d3bfc0a421fe22531a6e7af812fb9fe463e5214fdc920c0a8`
and checksum-list SHA-256
`96d4c3952f5819be3a2213e9f4735cf5ec8bf7e5392c5aca48aa9589cf141edf`.
Relative to the 103-wheel baseline it adds only
`opentelemetry-api==1.44.0`, `opentelemetry-sdk==1.44.0`, and
`opentelemetry-semantic-conventions==0.65b0`, whose wheel SHA-256 values are
respectively
`94b98c893a91b88657eaac1e3ba89618cdb85be6918196705354f34728b2cdef`,
`df081c4c6bcfdb1211e3e86140376792643128a25f8d72d1d27675936e7e96ad`,
and `1cacde7b0ad306f84c5ef08c3dbe1bbaf20165bba6f8bff43b670e555a086bcb`.
Two isolated offline candidate installs each contained the expected 107 total
distributions.

Both clean detached sources remained at exact `D0` and its exact tree. Source
validation passed the lightweight console target, dynamic versioning, routing
receipts/canaries, and paused-publication boundary. The 157-package offline
lock check passed; 105 tracked Python files compiled in memory; both
distribution validations passed with 77 wheel files, 159 sdist files, and
`publication_occurred=false`. Every candidate and rollback bundle directory
was owner-private; every contained artifact was a regular one-link file with
the reviewed private permissions. Every wheel passed SHA-256, ZIP,
filename/metadata name/version, pin, and exact-manifest checks. Public
package-network reads were limited to the exact build requirements and the
three pinned OpenTelemetry wheels.
Uv `0.11.7` does not enforce hashes embedded in `--with-requirements`; safety
therefore rests on these fully prevalidated exact-inventory owner-private
wheelhouses plus the reviewed offline/no-index/no-cache/no-build commands.

All 72 installed `buoy_search` wheel members matched the reviewed wheel.

Both clean candidate environments passed dependency checks for all 107
distributions and reported Python `3.13.0`, version
`0.5.2.dev36+ge9c906ca9`, sole `buoy_search.entrypoint:main` entry point, and
the exact three OpenTelemetry distributions. Version, top-level help, module
help, and telemetry help exited zero. In each fresh isolated home, initial
status was healthy/absent and bounded flush returned `outcome="empty"` with
zero commits without creating `.buoy`.

Each environment then emitted one governed synthetic trace without retrieval,
provider, model, credential, or network activity. Status observed one ready
envelope; `telemetry flush --timeout 30` returned `outcome="flushed"`, one
commit, and zero pending work. Final status was healthy with an empty queue,
one receipt, compatible DuckDB schema/store v1, and one persisted run. A
read-only DuckDB query found exactly one run and one span with run kind
`explicit_single`, outcome `success`, and `hit_count = 0`. All telemetry
directories were mode `0700`, all files mode `0600`, no link or special file
existed, and both `writer-state-v1.json` files reached `stopped` after the
governed 60-second idle exit with null reason, complete accounting, no
durability degradation, zero rejections/replays, and zero write failures.
Every effect was beneath the two isolated temporary homes; the real
application home was not accessed.

## Exact rollback bundle

A retained 647,944-byte prior exact-baseline wheel is exactly version
`0.5.2.dev36+g78ffbf796`, SHA-256
`aca9bef7b146ae25a0557d9174c875afac0efdc936f5889171b871629c6b5ba0`.
That historical digest does not itself authorize rollback.

The staged rollback dependency set contains 103 exact non-root pins at
SHA-256
`41acb9249e44d8056a9cdebc2eb5cc3c29687b6c3f5e9912c37ef6bc81fddce9`;
its generated requirements file has SHA-256
`b77b91dfaf463a3fbfda795b6709eadb75893782938e222675be69d1ca425ee3`.
The 103-wheel, 360,269,621-byte rollback wheelhouse has manifest SHA-256
`3204f7fca96184a4b0053183a663517f758ec625c2548c965501f741bebe9b4d`
and checksum-list SHA-256
`e7985887706e57a809e45bfe224ee6b7ece6c46c03bdcd65c5474e428c6a1c97`.

The exact rollback wheel is a regular file in the owner-private bundle. An
isolated rehearsal first installed the 107-distribution
candidate, then invoked the exact rollback replacement. It resolved, prepared,
and installed 104 distributions; reported Python `3.13.0`, version
`0.5.2.dev36+g78ffbf796`, and sole `buoy_search.cli:main` entry point; removed
all three OpenTelemetry distributions; passed the 104-distribution dependency
check; restored the reviewed CLI/source identity; recorded truthful new
rollback-bundle provenance; and left the rehearsal's isolated `.buoy` path
absent. The local provenance snapshot remains owner-private. Rollback
acceptance is exact package/runtime/CLI/entry-point/dependency restoration plus
reviewed new provenance, not byte-identical restoration of the entire
pre-install environment.

## Commands and independent pre-install gate

The owner-private forward-command file has opaque SHA-256
`3bad1e6871586d3714d2e70d1d9c9fbbe966f36e33a154beca4e691877ac2eed`
and the same command-text bytes with the sole terminal LF removed have opaque
SHA-256
`6747eca00bc7e0415b0588c61792d4babdc9bc884babab0d3b9dd6ab05ed4047`.
The owner-private rollback-command file has opaque SHA-256
`bcdcba229a26b87af8f529ded4e948c67ec4fee8d00b53aeb939a7b613b0aaff`
and the same command-text bytes with the sole terminal LF removed have opaque
SHA-256
`1e029f8bc606196f87afff8e04bba006d4af81ab94f87bb444b82c685f8ff865`.
Both owner-private commands bind the reviewed Python 3.13 runtime and forbid
network, indexes, caches, builds, source substitution, Python downloads,
configuration files, keyring access, and symlink-based package installation.
Rollback remains conditional on a known-terminal forward result, failure of a
required candidate acceptance check, proof that the installed tool is the
exact candidate, unchanged rollback bundle, and no active writer/replacement
process. Nonzero, interrupted, uncertain, or ambiguous forward outcomes stop
without rollback.

The accepted governing decision is the report's separately explicit
conditional rollback authority. It is dormant unless the complete predicate
above passes independent audit, is limited to the literal reviewed rollback
command once, and never applies after interruption, uncertainty, or ambiguity.

The preflight executor recorded `PREFLIGHT PASS; GLOBAL INSTALL NOT EXECUTED`
in an owner-private report with opaque SHA-256
`28600901d7dfbf9cdbd493ec1f8f4559049c12d938a0f2932f86957c2cfc7603`.
This executor verdict is not the independent `INSTALL-GO`. No invocation may
begin until the four-record authority commit integrates exactly and a separate
reviewer binds that commit, this report, both LF-terminated command-file
digests and both digests with the sole terminal LF removed, fresh
global-baseline equality, process absence, and every stop gate as `INSTALL-GO`.

The full report, literal commands, local provenance, and machine inventory
snapshots remain owner-private outside the repository. Post-integration
`INSTALL-GO` must verify them against the opaque bindings above.

## Authority-branch boundary

This branch starts at exact `D0` and adds only the accepted decision, active
ticket, this provisional evidence, and independent authority review. Its
future PR head, CI jobs, squash result `A`, and exact tree are deliberately not
invented before they exist. A dedicated integration session must collect those
facts and prove `parent(A) == D0` before installation can proceed.

## Installation and closure ledger

No forward invocation or rollback invocation has occurred at this evidence
boundary. A later records-only closure must record, without inference:

- the authority PR head, exact-head CI run/jobs, discussion state, and squash
  result `A`;
- the final fresh pre-install readback and independent `INSTALL-GO`;
- the forward command digest, start count, exit/result, and output identity;
- every post-install check and unchanged other-tool identity;
- whether the rollback predicate was false or, if true, the one exact rollback
  invocation, package/runtime restoration result, and reviewed new provenance;
  and
- all bounded temporary/package-network effects and every excluded zero-effect
  boundary.

## Effects so far

At this record boundary, durable effects are limited to PR #134's already
authorized squash integration and this isolated four-record task worktree.
Read-only inspections and bounded owner-only temporary preflight files may
exist. No user-global tool mutation, rollback, `main` change, release,
publication, provider operation, retrieval, model inference, credential
access, real `~/.buoy` access, other-tool mutation, or branch deletion has
occurred under this authority.
