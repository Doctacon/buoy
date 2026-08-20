Status: pass
Created: 2026-08-20
Updated: 2026-08-20
Ticket: .10x/tickets/done/2026-08-20-ship-buoy-v0-6-1.md
Evidence: .10x/evidence/2026-08-20-buoy-v0-6-1-github-release.md
Preparation-Review: .10x/reviews/2026-08-20-buoy-v0-6-1-release-preparation-review.md
Decision: .10x/decisions/annotated-tag-triggered-github-releases.md
Specification: .10x/specs/annotated-tag-triggered-github-release.md

# Buoy v0.6.1 Release Closure Review

## Target and bounded scope

Independent read-only review covered the complete records-only closure
candidate on `work/close-buoy-v0-6-1-release` from exact
`develop@cb718d747db582d05f52bbea436b6ee737ed5bfa`, tree
`eee7e36424dea2a80e77f35c7a6bf793541790bc`. The reviewer inspected the full
local diff, governing statuses and links, authoritative authenticated GitHub
state, and the separately observed downloaded-artifact audit. This review is
the only reviewer-authored addition.

Before this review was added, the candidate blobs were:

- `.10x/evidence/2026-08-19-buoy-v0-6-0-github-release.md`:
  `85ce022e6e847ccc6b859104690044508f225169`;
- `.10x/evidence/2026-08-20-buoy-v0-6-1-github-release.md`:
  `985b4f6777d63f96e53bb5a6f579b66afbd2c8d4`;
- `.10x/reviews/2026-08-20-buoy-v0-6-1-release-preparation-review.md`:
  `343960e6c46593d0d2d6ccfa083e182a9b31b069`;
- `.10x/tickets/cancelled/2026-08-19-ship-buoy-v0-6-0.md`:
  `c62623e1db56a42b92547f4c7e32bda0b9c827dc`; and
- `.10x/tickets/done/2026-08-20-ship-buoy-v0-6-1.md`:
  `b43d99dc1b9dc367f6a5550e8d46df585f708407`.

The active ticket blob
`c6fb2d76e6e25580f728dabcc4314cdfbdb49c6f` is removed from its active path
and replaced by the truthful terminal record above. The remaining four edits
only advance evidence from provisional to recorded and repair direct
backlinks to the done ticket and this review. No specification, decision,
workflow, release helper, test, application source, dependency, lockfile,
package configuration, changelog, README, or security-policy byte changes.

## Integration and promotion readback

Authenticated GitHub inspection confirmed task PR
[#140](https://github.com/Doctacon/buoy/pull/140) targeted exact
`develop@788c377c57bc1b4f1bfd4aba05d39ad67fe48ead` from exact preparation head
`2e8e305908f704c01763d6cad071182294eb99e4`. Exact-head CI run
[32378163294](https://github.com/Doctacon/buoy/actions/runs/32378163294),
attempt 1, passed jobs `96454493792`, `96454494281`, and `96455240673`.
The PR was squash-merged as current
`develop@cb718d747db582d05f52bbea436b6ee737ed5bfa`, with sole parent
`788c377c57bc1b4f1bfd4aba05d39ad67fe48ead` and exact tree
`eee7e36424dea2a80e77f35c7a6bf793541790bc`.

Release PR [#141](https://github.com/Doctacon/buoy/pull/141) promoted that
exact develop head to then-current
`main@701d73ebbf6a8c3b2c664a0295374dcb4283283c`. Release-readiness run
[32379410852](https://github.com/Doctacon/buoy/actions/runs/32379410852) passed
Policy, Python 3.11, Python 3.13, and Distribution; ordinary PR CI run
[32379410871](https://github.com/Doctacon/buoy/actions/runs/32379410871) also
passed, both on attempt 1 at the exact develop head. The release PR was
merge-committed as current
`main@0d6f414f9f258b4f7025f95c97ba5cb58d16b8d3`, with ordered parents
`701d73ebbf6a8c3b2c664a0295374dcb4283283c` and
`cb718d747db582d05f52bbea436b6ee737ed5bfa` and the identical reviewed tree.
Exact-main CI run
[32379909011](https://github.com/Doctacon/buoy/actions/runs/32379909011),
attempt 1, passed at that exact main commit.

## Tag, workflow, and immutable Release

The repository immutable-Releases endpoint reports `enabled: true`.
Annotated v0.6.0 tag object
`1ffb70f5656f48c782defbe252dab44426134343` remains exact, has message
`Buoy v0.6.0`, and peels to
`701d73ebbf6a8c3b2c664a0295374dcb4283283c`; authenticated release listing,
including drafts, still contains no v0.6.0 Release. Failed Release run
`32329737394` remains attempt 1 at that commit with both test jobs failed,
build and publication skipped, and zero retained artifacts.

Annotated v0.6.1 tag object
`bbd3824985d1b9778def284156313a27dca6526f` has message `Buoy v0.6.1`, uses
privacy-safe tagger `Doctacon <61797492+Doctacon@users.noreply.github.com>`,
and peels to exact current main
`0d6f414f9f258b4f7025f95c97ba5cb58d16b8d3`. GitHub reports exactly one
v0.6.1 Release-workflow run:
[32380801652](https://github.com/Doctacon/buoy/actions/runs/32380801652),
attempt 1, at the exact tag peel. Jobs `96463245408` (Python 3.13),
`96463245831` (Python 3.11), `96463977009` (Build distributions), and
`96464271856` (Publish immutable GitHub release) all passed. The publisher's
attestation, frozen-draft verification, prepublication provenance
verification, publication, and immutable/latest readback steps all report
success. Retained artifact `9411013181`, `buoy-search-v0.6.1`, belongs to the
same exact run and head.

GitHub Release
[v0.6.1](https://github.com/Doctacon/buoy/releases/tag/v0.6.1), database ID
`373806097`, is the current latest Release, target
`0d6f414f9f258b4f7025f95c97ba5cb58d16b8d3`, name `Buoy v0.6.1`, published
`2026-08-20T14:36:33Z`, non-draft, non-prerelease, and immutable. Its complete
asset list contains exactly:

- asset `522371846`, `buoy_search-0.6.1-py3-none-any.whl`, 697,772 bytes,
  API digest
  `sha256:3c1b8805d39f67194dcd29c05545266356092f28cd7fd545213cfd08465d1d3a`;
- asset `522371845`, `buoy_search-0.6.1.tar.gz`, 1,227,623 bytes, API digest
  `sha256:d1fc71cfdf9968594251b8d08661a462ffa9898859847ebcc9b569de8f2fd60d`.

The GitHub attestations API returns attestations for both exact subject
digests. The independent release monitor additionally verified byte-equal
numeric asset-ID downloads, strict repository-bound `gh attestation verify`
for both files, and isolated offline installation of the downloaded wheel.
That clean smoke reported `buoy 0.6.1` and passed CLI, module, telemetry-help,
import, and packaged-tokenizer checks under a fresh empty home without
credential, provider, model, data, namespace, or real Buoy-home access.

## Governance and closure boundary

The ticket is terminal `done`, release evidence is `recorded`, preparation
review remains `pass`, every direct successor/review backlink resolves to its
terminal path, and no stale active-ticket reference remains. Diff hygiene is
clean. The closure candidate records already-completed public effects only;
it contains no executable mechanism or authority for another tag, Release,
asset, attestation, workflow, registry, PyPI, application, provider, model,
data, global-installation, user-home, protection, force-push, v0.6.0 recovery,
or unrelated hosted mutation.

## Verdict

PASS. The recorded identities and outcomes match authoritative GitHub state
and the independent downloaded-artifact audit. The ticket move, evidence
advance, and direct backlink repairs are coherent, privacy-safe, and bounded.
No correctness, provenance, release-state, governance, link, status, diff, or
scope blocker remains. This review authorizes only the records-only commit and
ordinary closure PR handoff; it does not authorize self-merge or any new
release-side effect.
